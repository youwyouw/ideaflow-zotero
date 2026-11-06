# Import plan

The local Zotero writer accepts a UTF-8 JSON plan. Use the destination as a list of collection names, from root to leaf. Each entry contains Zotero item fields and a single optional HTML note. The optional `collection_note` is a standalone Idea Card in the target collection.

```json
{
  "collection": ["Research Ideas", "Persona Mechanisms"],
  "items": [
    {
      "item": {
        "itemType": "preprint",
        "title": "Persona Vectors: Monitoring and Controlling Character Traits in Language Models",
        "url": "https://arxiv.org/abs/2507.21509",
        "DOI": "10.48550/arXiv.2507.21509",
        "repository": "arXiv",
        "date": "2025",
        "tags": [{"tag": "Persona Vectors"}]
      },
      "note": "<h2>Memory Card</h2><p>Activation directions track trait expression during prompting and fine-tuning. Read Sections 3 and 4 to compare the two settings.</p><p><a href=\"https://arxiv.org/abs/2507.21509\">Original source</a></p>"
    }
  ],
  "collection_note": "<h2>Idea Card</h2><p>Do prompting and fine-tuning produce similar persona shifts through the same causal mechanism?</p>"
}
```

The scripts live in the `scripts/` folder next to this skill's `SKILL.md`. Below, `SKILL_DIR` stands for that folder. Your shell usually starts in the user's project, not in the skill folder, so substitute the real path, for example:

- Project skill: `.agents/skills/ideaflow-zotero` (Codex) or `.claude/skills/ideaflow-zotero` (Claude Code)
- User skill: `~/.agents/skills/ideaflow-zotero` (Codex) or `~/.claude/skills/ideaflow-zotero` (Claude Code)

Quote the path if it contains spaces. Use `python3` if `python` is not available.

```sh
python SKILL_DIR/scripts/zotero.py status
python SKILL_DIR/scripts/zotero.py collections
python SKILL_DIR/scripts/zotero.py search "persona vectors" --limit 10
python SKILL_DIR/scripts/zotero.py plan path/to/plan.json
python SKILL_DIR/scripts/zotero.py apply path/to/plan.json
```

Plan and export paths are relative to the current working directory, not to `SKILL_DIR`.

For separate destination folders, create a plan per folder. Matching the same DOI or source across plans should add collection membership to one Zotero item. Use bibliographic item types that match the source. Store an article URL in the record, with a full-text PDF link in the card where available. Escape text and link attributes when constructing HTML.

Check the plan before applying it. A read-only preview is also useful for resolving ambiguous titles and showing the user a proposed selection. Keep private plans outside the public repository or use the ignored `local/` directory.

The default is to preserve existing cards. Set `update_collection_note` at the top level to refresh the Idea Card or `update_note` on an individual entry to refresh its Memory Card. These flags apply to notes managed by this skill.

To share a collection, use its key from `collections` and a new export directory.

```sh
python SKILL_DIR/scripts/share.py COLLECTION_KEY --output-dir share
```

The helper writes `reading-list.md` and `references.bib` from direct collection members. Add `--include-cards` only when the user requests the text of IdeaFlow Memory Cards. The user can review both files before sharing them.
