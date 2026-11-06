#!/usr/bin/env python3
"""Preview and apply IdeaFlow import plans against Zotero Desktop."""

import argparse
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid


LIBRARY = "/users/0"
APP_NAME = "ideaflow-zotero"
CARD_TAG = "IdeaFlow"
ITEM_TYPES_EXCLUDED = {"attachment", "annotation", "note"}
PROTECTED_FIELDS = {
    "key", "version", "library", "collections", "parentItem", "deleted",
    "relations", "dateAdded", "dateModified", "linkMode", "path", "filename",
}
ARXIV = re.compile(r"^(\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?$", re.I)
ALLOWED_HTML = {
    "p", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol",
    "li", "strong", "b", "em", "i", "code", "pre", "blockquote", "a", "br",
    "hr", "table", "thead", "tbody", "tr", "th", "td", "sub", "sup",
}


class IdeaFlowError(Exception):
    """A validation error or a local Zotero operation that could not finish."""


class ZoteroHTTPError(IdeaFlowError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalZotero:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}/api"
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.server_id = None
        self.key = None
        self.reusable = False

    def request(self, path, *, method="GET", body=None, headers=None, timeout=30):
        request_headers = {"Zotero-API-Version": "3"}
        if self.server_id:
            request_headers["Zotero-Server-ID"] = self.server_id
        if headers:
            request_headers.update(headers)
        payload = None
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            request_headers["Content-Type"] = "application/json; charset=utf-8"
        req = Request(self.base + path, data=payload, method=method, headers=request_headers)
        try:
            with self.opener.open(req, timeout=timeout) as response:
                return response.headers, response.read()
        except HTTPError as exc:
            messages = {
                403: "Enable the local API in Zotero Settings → Advanced and allow any pending write prompt.",
                409: "The Zotero library is busy. Re-run the plan after it finishes.",
                412: "The Zotero library or record changed. Preview the plan again before retrying.",
                429: "Zotero limited authorization prompts. Wait before re-running the plan.",
            }
            suffix = messages.get(exc.code, "")
            # A server error may include library data or credentials. Keep it off the console.
            raise ZoteroHTTPError(exc.code, f"Zotero returned HTTP {exc.code} for {method} {path}. {suffix}".strip()) from None
        except (URLError, OSError):
            raise IdeaFlowError(
                f"Could not complete {method} {path}. Keep Zotero open and check that its local API is enabled."
            ) from None

    def status(self):
        headers, _ = self.request("/")
        version = headers.get("X-Zotero-Version", "")
        api_version = headers.get("Zotero-API-Version", "")
        self.server_id = headers.get("Zotero-Server-ID")
        return {
            "reachable": True,
            "zotero_version": version or None,
            "api_version": api_version or None,
            "write_api_supported": bool(
                self.server_id and api_version == "3"
                and (not version or int(version.split(".")[0]) >= 10)
            ),
        }

    def get(self, path):
        _, raw = self.request(path)
        return json.loads(raw)

    def authorize(self):
        print("Allow the ideaflow-zotero write request in Zotero.", file=sys.stderr, flush=True)
        try:
            _, raw = self.request(
                "/local/authorize", method="POST", body={"appName": APP_NAME}, timeout=120
            )
        except ZoteroHTTPError as exc:
            if exc.status == 403:
                raise IdeaFlowError("Zotero did not grant write authorization.") from None
            raise
        result = json.loads(raw)
        self.key = result.get("key")
        self.reusable = result.get("remember") is True
        if not isinstance(self.key, str) or not self.key:
            raise IdeaFlowError("Zotero did not return a local write authorization.")

    def write(self, path, records):
        for offset in range(0, len(records), 50):
            batch = records[offset : offset + 50]
            write_headers = (
                {} if any("version" in record for record in batch)
                else {"Zotero-Write-Token": uuid.uuid4().hex}
            )
            for attempt in range(2):
                if self.key is None:
                    self.authorize()
                try:
                    _, raw = self.request(
                        path, method="POST", body=batch,
                        headers={**write_headers, "Zotero-API-Key": self.key},
                    )
                    break
                except ZoteroHTTPError as exc:
                    if exc.status != 401 or attempt:
                        raise
                    self.key = None
                finally:
                    if not self.reusable:
                        self.key = None
            result = json.loads(raw)
            failed = result.get("failed", {})
            if failed:
                details = "; ".join(
                    f"row {offset + int(index) + 1}: HTTP {error.get('code', '?')}"
                    for index, error in failed.items()
                )
                raise IdeaFlowError(f"Zotero rejected part of the batch ({details}). Review the plan before re-running it.")
            expected = len(result.get("successful", {})) + len(result.get("unchanged", {}))
            if expected != len(batch):
                raise IdeaFlowError("Zotero did not confirm each record in the batch. Preview the plan again.")


class NoteHTML(HTMLParser):
    def __init__(self, *, strict=False):
        super().__init__(convert_charrefs=True)
        self.strict = strict
        self.words = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if self.strict and tag not in ALLOWED_HTML:
            raise IdeaFlowError(f"Unsupported element in note HTML: <{tag}>.")
        for name, value in attrs:
            if name == "href" and tag == "a" and value:
                if self.strict:
                    parsed = urlsplit(value)
                    if parsed.scheme not in {"http", "https", "zotero"} or not parsed.netloc:
                        raise IdeaFlowError("Note links must be absolute HTTP, HTTPS, or Zotero links.")
                self.links.append(value)
            elif self.strict:
                raise IdeaFlowError(f"Unsupported attribute in note HTML: {name}.")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li", "td", "th", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.words.append(" ")

    def handle_data(self, data):
        self.words.append(data)

    def fingerprint(self):
        return (" ".join("".join(self.words).split()), tuple(self.links))


def note_fingerprint(value, *, strict=False):
    parser = NoteHTML(strict=strict)
    parser.feed(value)
    parser.close()
    return parser.fingerprint()


def note_value(value, label):
    if not isinstance(value, str) or not value.strip():
        raise IdeaFlowError(f"{label} must be nonempty HTML.")
    if not note_fingerprint(value, strict=True)[0]:
        raise IdeaFlowError(f"{label} must contain readable text.")
    return value


def checked_tags(value, label):
    if not isinstance(value, list) or any(
        not isinstance(tag, dict) or set(tag) != {"tag"}
        or not isinstance(tag["tag"], str) or not tag["tag"].strip() for tag in value
    ):
        raise IdeaFlowError(f"{label} must be an array of objects with a nonempty tag string.")
    if len({tag["tag"].casefold() for tag in value}) != len(value):
        raise IdeaFlowError(f"{label} contains duplicate tags.")


def load_plan(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise IdeaFlowError("The plan must be a JSON object.")
    unknown = set(data) - {"collection", "items", "collection_note", "update_collection_note"}
    if unknown:
        raise IdeaFlowError(f"Unknown plan field(s): {', '.join(sorted(unknown))}.")
    collection = data.get("collection")
    if not isinstance(collection, list) or not collection or any(
        not isinstance(name, str) or not name.strip() or name != name.strip() for name in collection
    ):
        raise IdeaFlowError("collection must be a nonempty array of names without surrounding whitespace.")
    items = data.setdefault("items", [])
    if not isinstance(items, list):
        raise IdeaFlowError("items must be an array.")
    if "update_collection_note" in data and not isinstance(data["update_collection_note"], bool):
        raise IdeaFlowError("update_collection_note must be true or false.")
    if data.get("update_collection_note") and "collection_note" not in data:
        raise IdeaFlowError("update_collection_note requires collection_note.")
    if "collection_note" in data:
        note_value(data["collection_note"], "collection_note")
    titles = set()
    identifiers = set()
    for row, entry in enumerate(items, 1):
        label = f"items[{row - 1}]"
        if not isinstance(entry, dict) or set(entry) - {"item", "note", "update_note"}:
            raise IdeaFlowError(f"{label} must contain an item and optional note and update_note fields.")
        item = entry.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
            raise IdeaFlowError(f"{label}.item must have a nonempty title.")
        if PROTECTED_FIELDS.intersection(item):
            raise IdeaFlowError(f"{label}.item contains fields reserved for the writer.")
        if not isinstance(item.get("itemType"), str) or not item["itemType"] or item["itemType"] in ITEM_TYPES_EXCLUDED:
            raise IdeaFlowError(f"{label}.item must describe a bibliographic item type.")
        if "DOI" in item and not isinstance(item["DOI"], str):
            raise IdeaFlowError(f"{label}.item.DOI must be a string.")
        if "url" in item:
            if not isinstance(item["url"], str):
                raise IdeaFlowError(f"{label}.item.url must be a string.")
            url = urlsplit(item["url"])
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise IdeaFlowError(f"{label}.item.url must be a public HTTP(S) source URL.")
        if "tags" in item:
            checked_tags(item["tags"], f"{label}.item.tags")
        if "update_note" in entry and not isinstance(entry["update_note"], bool):
            raise IdeaFlowError(f"{label}.update_note must be true or false.")
        if entry.get("update_note") and "note" not in entry:
            raise IdeaFlowError(f"{label}.update_note requires note.")
        if "note" in entry:
            note_value(entry["note"], f"{label}.note")
        title = normal_title(item["title"])
        ids = item_ids(item)
        if not title or title in titles or identifiers.intersection(ids):
            raise IdeaFlowError(f"Repeated or unusable source identity at {label}. Merge duplicates in the plan.")
        titles.add(title)
        identifiers.update(ids)
    return data


def normal_title(title):
    normalized = unicodedata.normalize("NFKC", unescape(title)).casefold()
    return "".join(char for char in normalized if char.isalnum())


def item_ids(item):
    result = set()
    doi = re.sub(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", "", item.get("DOI", "").strip(), flags=re.I).lower()
    if doi:
        result.add(("doi", doi))
        if doi.startswith("10.48550/arxiv."):
            arxiv_id = doi.removeprefix("10.48550/arxiv.")
            if match := ARXIV.fullmatch(arxiv_id):
                result.add(("arxiv", match[1].lower()))
    url = urlsplit(item.get("url", "").strip())
    if url.hostname:
        host = url.hostname.lower().removeprefix("www.")
        path = unquote(url.path).rstrip("/")
        if host == "doi.org":
            result.add(("doi", path.lstrip("/").lower()))
        if host == "arxiv.org":
            arxiv_id = re.sub(r"^/(?:abs|pdf|html)/", "", path).removesuffix(".pdf")
            if match := ARXIV.fullmatch(arxiv_id):
                result.add(("arxiv", match[1].lower()))
        query = sorted((key, value) for key, value in parse_qsl(url.query) if not key.lower().startswith("utm_"))
        authority = host if url.port is None or (url.scheme, url.port) in {("http", 80), ("https", 443)} else f"{host}:{url.port}"
        result.add(("url", authority + path + ("?" + urlencode(query) if query else "")))
    return result


def editable(records):
    return [record["data"] for record in records if not record["data"].get("deleted")]


class ItemIndex:
    def __init__(self, records):
        self.by_id = {}
        self.by_title = {}
        self.by_key = {}
        for item in editable(records):
            if item.get("itemType") in ITEM_TYPES_EXCLUDED or not item.get("title"):
                continue
            self.by_key[item["key"]] = item
            for ident in item_ids(item):
                self.by_id.setdefault(ident, set()).add(item["key"])
            self.by_title.setdefault(normal_title(item["title"]), set()).add(item["key"])

    def match(self, requested):
        ids = item_ids(requested)
        keys = set().union(*(self.by_id.get(ident, set()) for ident in ids))
        if not keys:
            keys = self.by_title.get(normal_title(requested["title"]), set())
            if len(keys) == 1:
                existing_ids = item_ids(self.by_key[next(iter(keys))])
                requested_ids = {i for i in ids if i[0] in {"doi", "arxiv"}}
                known_ids = {i for i in existing_ids if i[0] in {"doi", "arxiv"}}
                if requested_ids and known_ids and not requested_ids.intersection(known_ids):
                    raise IdeaFlowError(f"Conflicting identifiers for title {requested['title']!r}. Review the Zotero record.")
        if len(keys) > 1:
            raise IdeaFlowError(f"More than one Zotero record matches {requested['title']!r}. Resolve the ambiguity before applying.")
        return self.by_key[next(iter(keys))] if keys else None


def resolve_collection(path, all_collections):
    parent = None
    for index, name in enumerate(path):
        matches = [
            record for record in all_collections
            if record["name"].casefold() == name.casefold() and (record.get("parentCollection") or None) == parent
        ]
        if len(matches) > 1:
            raise IdeaFlowError(f"More than one Zotero collection matches {' / '.join(path[:index + 1])!r}.")
        if not matches:
            return parent, path[index:]
        parent = matches[0]["key"]
    return parent, []


def tagged(existing, additions):
    present = {entry["tag"].casefold() for entry in existing}
    return existing + [entry for entry in additions if entry["tag"].casefold() not in present]


def cards_with_role(records, role):
    def recognized(note):
        if note.get("itemType") != "note":
            return False
        if any(tag["tag"].casefold() == role.casefold() for tag in note.get("tags", [])):
            return True
        heading = re.search(r"<(?:h[1-6]|p)\b[^>]*>(.*?)</(?:h[1-6]|p)>", note.get("note", ""), re.I | re.S)
        return bool(heading and note_fingerprint(heading[1])[0].casefold().startswith(role.casefold()))

    return [note for note in editable(records) if recognized(note)]


def card_plan(existing, desired, update, role, **location):
    if desired is None:
        return "none", None
    if len(existing) > 1 and update:
        raise IdeaFlowError(f"More than one {role} matches the target. Resolve the ambiguity before updating.")
    if existing:
        prior = existing[0]
        if update and note_fingerprint(prior.get("note", "")) != note_fingerprint(desired):
            tags = {tag["tag"].casefold() for tag in prior.get("tags", [])}
            if not {CARD_TAG.casefold(), role.casefold()} <= tags:
                raise IdeaFlowError(
                    f"The existing {role} is not managed by IdeaFlow and will stay as it is. "
                    "Review it manually or preview again with the refresh option disabled."
                )
            return "update", {
                "key": prior["key"], "version": prior["version"], "note": desired,
            }
        return "reuse", None
    return "create", {
        "itemType": "note", "note": desired, **location,
        "tags": [{"tag": CARD_TAG}, {"tag": role}],
    }


@dataclass
class Snapshot:
    collection_key: str | None
    missing_collections: list
    rows: list
    idea_action: str
    idea_mutation: dict | None

    def summary(self, path):
        return {
            "collection": path,
            "collection_key": self.collection_key if not self.missing_collections else None,
            "create_collections": self.missing_collections,
            "collection_note": self.idea_action,
            "items": [row["summary"] for row in self.rows],
        }


def child_notes(zotero, key):
    return zotero.get(f"{LIBRARY}/items/{key}/children?itemType=note")


def snapshot(zotero, plan):
    collection, missing = resolve_collection(plan["collection"], editable(zotero.get(f"{LIBRARY}/collections")))
    target = None if missing else collection
    rows = []
    if plan["items"]:
        index = ItemIndex(zotero.get(f"{LIBRARY}/items/top"))
        matched_keys = set()
        for entry in plan["items"]:
            item = entry["item"]
            existing = index.match(item)
            key = existing["key"] if existing else None
            if key and key in matched_keys:
                raise IdeaFlowError("Two planned sources match the same Zotero record. Merge them before applying.")
            if key:
                matched_keys.add(key)
            needs_membership = bool(existing and target not in existing.get("collections", []))
            tags = tagged(existing.get("tags", []), item.get("tags", [])) if existing else item.get("tags", [])
            tags_changed = bool(existing and tags != existing.get("tags", []))
            note_candidates = (
                cards_with_role(child_notes(zotero, key), "Memory Card")
                if key and "note" in entry else []
            )
            note_action, note = card_plan(
                note_candidates, entry.get("note"), entry.get("update_note", False), "Memory Card", parentItem=key
            )
            summary = {
                "title": item["title"], "item_key": key, "reference": "reuse" if key else "create",
                "add_to_collection": not key or needs_membership,
                "add_tags": [tag["tag"] for tag in item.get("tags", []) if not existing or tag["tag"].casefold() not in {t["tag"].casefold() for t in existing.get("tags", [])}],
                "memory_card": note_action,
            }
            mutation = None
            if not key:
                mutation = {**item, "collections": [target]}
            elif needs_membership or tags_changed:
                mutation = {"key": key, "version": existing["version"]}
                if needs_membership:
                    mutation["collections"] = existing.get("collections", []) + [target]
                if tags_changed:
                    mutation["tags"] = tags
            rows.append({"summary": summary, "item": mutation, "note": note})
    candidates = []
    if target and "collection_note" in plan:
        candidates = cards_with_role(
            zotero.get(f"{LIBRARY}/collections/{target}/items/top?itemType=note"), "Idea Card"
        )
    idea_action, idea = card_plan(
        candidates, plan.get("collection_note"), plan.get("update_collection_note", False),
        "Idea Card", collections=[target],
    )
    return Snapshot(collection, missing, rows, idea_action, idea)


def apply(zotero, plan):
    state = snapshot(zotero, plan)
    if state.missing_collections:
        parent = state.collection_key
        for index, name in enumerate(state.missing_collections, len(plan["collection"]) - len(state.missing_collections)):
            zotero.write(f"{LIBRARY}/collections", [{"name": name, "parentCollection": parent or False}])
            parent, still_missing = resolve_collection(
                plan["collection"][:index + 1], editable(zotero.get(f"{LIBRARY}/collections"))
            )
            if still_missing:
                raise IdeaFlowError(f"Zotero did not return the new collection {name!r}.")
        state = snapshot(zotero, plan)
    items = [row["item"] for row in state.rows if row["item"]]
    if items:
        zotero.write(f"{LIBRARY}/items", items)
        state = snapshot(zotero, plan)
    if state.missing_collections or any(row["item"] for row in state.rows):
        raise IdeaFlowError("References or collection memberships could not be verified. Preview the plan again.")
    notes = [row["note"] for row in state.rows if row["note"]]
    if state.idea_mutation:
        notes.append(state.idea_mutation)
    if notes:
        zotero.write(f"{LIBRARY}/items", notes)
        state = snapshot(zotero, plan)
    if state.missing_collections or state.idea_mutation or any(row["item"] or row["note"] for row in state.rows):
        raise IdeaFlowError("A requested change could not be verified. Preview the plan again.")
    return {"verified": True, "reference_writes": len(items), "card_writes": len(notes), **state.summary(plan["collection"])}


def search(zotero, query, limit):
    params = urlencode({"q": query, "limit": limit})
    return [
        {field: item.get(field) for field in ("key", "title", "itemType", "date", "DOI", "url", "collections")}
        for item in editable(zotero.get(f"{LIBRARY}/items/top?{params}"))
        if item.get("itemType") not in ITEM_TYPES_EXCLUDED
    ]


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=23119, type=int, help="local Zotero API port (default: 23119)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="check whether Zotero Desktop's local API is reachable")
    commands.add_parser("collections", help="list collection names and keys without making changes")
    lookup = commands.add_parser("search", help="search for existing Zotero references")
    lookup.add_argument("query", help="Zotero search query")
    lookup.add_argument("--limit", type=int, default=20)
    commands.add_parser("plan", help="preview changes without writing").add_argument("input", type=Path)
    commands.add_parser("apply", help="apply changes using Zotero's write authorization").add_argument("input", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.command == "search" and (not args.query.strip() or not 1 <= args.limit <= 100):
        parser.error("search requires a nonempty query and --limit between 1 and 100")
    try:
        plan = load_plan(args.input) if args.command in {"plan", "apply"} else None
        zotero = LocalZotero(args.port)
        status = zotero.status()
        if args.command == "status":
            result = status
        elif args.command == "collections":
            result = [
                {field: collection.get(field) for field in ("key", "name", "parentCollection")}
                for collection in editable(zotero.get(f"{LIBRARY}/collections"))
            ]
        elif args.command == "search":
            result = search(zotero, args.query, args.limit)
        elif args.command == "plan":
            result = snapshot(zotero, plan).summary(plan["collection"])
        else:
            if not status["write_api_supported"]:
                raise IdeaFlowError("Writing requires Zotero Desktop 10 or newer with Local API v3 enabled.")
            result = apply(zotero, plan)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (IdeaFlowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ideaflow-zotero: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
