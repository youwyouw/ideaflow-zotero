#!/usr/bin/env python3
"""Export references from one Zotero collection as Markdown and BibTeX."""

import argparse
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


BASE = "http://127.0.0.1:23119/api/users/0"
KEY = re.compile(r"[A-Z0-9]{8}")
DOI = re.compile(r"10\.\d{4,9}/[^\s{}\\]+", re.I)
YEAR = re.compile(r"(?<!\d)\d{4}(?!\d)")
SKIP_TYPES = {"attachment", "note", "annotation"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalLibrary:
    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.server_id = None

    def get(self, path):
        headers = {"Zotero-API-Version": "3", "Accept": "application/json"}
        if self.server_id:
            headers["Zotero-Server-ID"] = self.server_id
        try:
            with self.opener.open(Request(BASE + path, headers=headers), timeout=30) as response:
                server_id = response.headers.get("Zotero-Server-ID")
                if self.server_id and self.server_id != server_id:
                    raise ValueError("Zotero changed during the export. Try again.")
                self.server_id = server_id
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 403:
                raise ValueError("Enable the local API in Zotero under Settings > Advanced.") from exc
            if exc.code == 404:
                raise ValueError("The collection or item key was not found in My Library.") from exc
            raise ValueError(f"Zotero returned HTTP {exc.code} for {path}.") from exc
        except URLError as exc:
            raise ValueError("Could not connect to Zotero at 127.0.0.1:23119. Open Zotero and try again.") from exc


def one_line(value):
    return " ".join(str(value or "").split())


def markdown_text(value):
    return re.sub(r"([\\`*_{}\[\]()#+\-!|<>~&])", r"\\\1", one_line(value))


def public_url(value):
    """Omit non-web, local, credential-bearing, and query-token links."""
    try:
        parts = urlsplit(one_line(value))
        host = parts.hostname or ""
        if parts.scheme not in {"http", "https"} or parts.username or parts.password or not host:
            return ""
        if host.lower().rstrip(".").endswith((".local", ".internal", ".localhost")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            suffix = host.rstrip(".").rsplit(".", 1)[-1]
            if "." not in host or not re.fullmatch(r"[a-zA-Z0-9.-]+", host) or not suffix[:1].isalpha():
                return ""
        port = parts.port
        netloc = f"[{host}]" if ":" in host else host
        if port is not None:
            netloc += f":{port}"
    except ValueError:
        return ""
    query = ""
    if host == "openreview.net":
        identifier = parse_qs(parts.query).get("id", [""])[0]
        if re.fullmatch(r"[a-zA-Z0-9_-]+", identifier):
            query = urlencode({"id": identifier})
    path = quote(parts.path, safe="/:@!$&'*+,;=-._~%")
    return urlunsplit((parts.scheme, netloc, path, query, ""))


def doi_for(data):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", one_line(data.get("DOI")), flags=re.I)
    return value if DOI.fullmatch(value) else ""


def creator_names(data):
    creators = data.get("creators", [])
    primary = [entry for entry in creators if entry.get("creatorType") in {"author", "bookAuthor", "presenter", "programmer"}]
    editors = [entry for entry in creators if entry.get("creatorType") == "editor"]
    return primary, editors


def display_name(creator):
    return one_line(creator.get("name") or " ".join(filter(None, (creator.get("firstName"), creator.get("lastName")))))


class CardText(HTMLParser):
    blocks = {"p", "div", "section", "li", "br", "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__()
        self.lines = []
        self.current = []
        self.hidden = False

    def flush(self):
        line = one_line("".join(self.current))
        if line:
            self.lines.append(markdown_text(line))
        self.current.clear()

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.hidden = True
        if tag in self.blocks:
            self.flush()

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.hidden = False
        if tag in self.blocks:
            self.flush()

    def handle_data(self, data):
        if not self.hidden:
            self.current.append(data)


def included_cards(library, key):
    for item in library.get(f"/items/{key}/children"):
        data = item.get("data", {})
        tags = {tag["tag"] for tag in data.get("tags", [])}
        if data.get("itemType") != "note" or not {"IdeaFlow", "Memory Card"} <= tags:
            continue
        card = CardText()
        card.feed(data.get("note", ""))
        card.flush()
        if card.lines:
            yield "\n\n".join(card.lines)


def render_markdown(name, items, library=None):
    sections = [f"# {markdown_text(name)}"]
    for item in items:
        data = item["data"]
        title = markdown_text(data.get("title") or "Untitled")
        primary, editors = creator_names(data)
        creators = ", ".join(filter(None, (display_name(c) for c in primary or editors)))
        venue = data.get("publicationTitle") or data.get("proceedingsTitle") or data.get("repository") or data.get("blogTitle")
        year = YEAR.search(one_line(data.get("date")))
        metadata = " · ".join(markdown_text(value) for value in (creators, venue, year.group() if year else "") if value)
        doi = doi_for(data)
        url = "https://doi.org/" + quote(doi, safe="/-._~") if doi else public_url(data.get("url"))
        section = [f"## {title}"]
        if metadata:
            section.append(metadata)
        if url:
            section.append(f"[Source](<{url}>)")
        if library is not None:
            for card in included_cards(library, item["key"]):
                section.extend(("### Memory Card", card))
        sections.append("\n\n".join(section))
    return "\n\n".join(sections) + "\n"


TEX_ESCAPE = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&",
    "#": r"\#", "_": r"\_", "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def tex(value):
    return "".join(TEX_ESCAPE.get(char, char) for char in one_line(value))


def bibtex_names(creators):
    names = []
    for creator in creators:
        if creator.get("name"):
            names.append("{" + tex(creator["name"]) + "}")
        else:
            name = ", ".join(filter(None, (tex(creator.get("lastName")), tex(creator.get("firstName")))))
            if name:
                names.append(name)
    return " and ".join(names)


def render_bibtex(items):
    records = []
    for item in items:
        data = item["data"]
        year = YEAR.search(one_line(data.get("date")))
        primary, editors = creator_names(data)
        primary_names, editor_names = bibtex_names(primary), bibtex_names(editors)
        kind, context = "misc", {}
        match data.get("itemType"):
            case "journalArticle" if primary_names and year and data.get("publicationTitle"):
                kind, context = "article", {"journal": data["publicationTitle"]}
            case "conferencePaper" if primary_names and year and data.get("proceedingsTitle"):
                kind, context = "inproceedings", {"booktitle": data["proceedingsTitle"]}
            case "book" if (primary_names or editor_names) and year and data.get("publisher"):
                kind = "book"
            case "bookSection" if primary_names and year and data.get("bookTitle") and data.get("publisher"):
                kind, context = "incollection", {"booktitle": data["bookTitle"]}
            case _:
                context = {"howpublished": data.get("repository") or data.get("publicationTitle") or data.get("proceedingsTitle") or data.get("blogTitle")}

        fields = {
            "title": "{" + tex(data.get("title") or "Untitled") + "}",
            "author": primary_names,
            "editor": editor_names,
            "year": year.group() if year else "",
            **{name: tex(value) for name, value in context.items()},
            "publisher": tex(data.get("publisher")),
            "volume": tex(data.get("volume")),
            "number": tex(data.get("issue")),
            "pages": tex(data.get("pages")),
            "doi": doi_for(data),
            "url": public_url(data.get("url")),
        }
        lines = [f"@{kind}{{zotero_{item['key']},"]
        lines.extend(f"  {name} = {{{value}}}," for name, value in fields.items() if value)
        records.append("\n".join([*lines, "}"]))
    return "\n\n".join(records) + ("\n" if records else "")


def export(key, output_dir, include_cards):
    if not KEY.fullmatch(key):
        raise ValueError("Enter an 8-character Zotero collection key.")
    paths = (output_dir / "reading-list.md", output_dir / "references.bib")
    if any(path.exists() for path in paths):
        raise ValueError("Choose a fresh output directory. Existing exports are left in place.")
    library = LocalLibrary()
    collection = library.get(f"/collections/{key}")["data"]
    items = []
    for item in library.get(f"/collections/{key}/items/top"):
        data = item.get("data", {})
        if data.get("itemType") in SKIP_TYPES or data.get("deleted"):
            continue
        if not KEY.fullmatch(item.get("key", "")):
            raise ValueError("Zotero returned an invalid item key.")
        items.append(item)
    items.sort(key=lambda item: (one_line(item["data"].get("title")).casefold(), item["key"]))
    contents = (
        render_markdown(collection["name"], items, library if include_cards else None),
        render_bibtex(items),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, contents):
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(content)
    return len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection_key", help="Key of a collection in My Library")
    parser.add_argument("--output-dir", type=Path, required=True, help="Destination for reading-list.md and references.bib")
    parser.add_argument("--include-cards", action="store_true", help="Include IdeaFlow Memory Card text in the Markdown file")
    args = parser.parse_args()
    try:
        count = export(args.collection_key, args.output_dir, args.include_cards)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Exported {count} references to {args.output_dir}.")
    if args.include_cards:
        print("Review the exported Memory Cards before sharing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
