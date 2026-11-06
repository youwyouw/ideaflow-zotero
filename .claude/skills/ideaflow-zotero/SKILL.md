---
name: ideaflow-zotero
description: Develop a research idea into a focused literature search, turn a meeting document's references into individual Zotero entries, or organize a reading queue with source-grounded Memory Cards. Use for research intake and literature organization in Zotero Desktop.
---

# ideaflow-zotero

Use the research question to decide what belongs in Zotero and what each source contributes. Treat Zotero as the library of record.

## Choose the destination

| User's input | Default destination | Result |
| --- | --- | --- |
| A research question, hypothesis or proposal | `Research Ideas / <short topic>` | One Idea Card and a selective set of references |
| Meeting slides, a review or a bibliography whose references the user wants to read | `Research Directions / <source or topic>` | One library entry and one Memory Card per identifiable reference |
| A batch of papers the user wants to read | `To Read` | Individual entries and cards, with Reading Guides when requested |

Explicit destination paths, scope and language override the defaults. List existing collections before inventing a name. Reuse a clear topic match even if it includes an idea number or a longer label. A request to put a bibliography in Research Directions uses a child collection named for the source unless the user asks to file directly in the root. Include every identifiable reference in scope unless the user requests screening. A meeting PDF can remain a separate source document.

## Research and prepare

1. For an idea, identify the question, proposed comparison and outcome. Derive search terms from the mechanism and experimental design. Check the local collection and relevant library matches before searching for missing work.
2. Verify the title, authors, year and identifier against a publisher, repository or original post. Follow embedded links in PDFs and distinguish formal references from works mentioned in passing. If a news item points to a paper, prefer the paper as the bibliographic record and retain the news link in its card. Mark ambiguous references for review.
3. Explain what each selected source contributes to the question. Useful reasons include a baseline, a manipulation, an outcome measure, conflicting evidence and a boundary condition. For a novelty check, report the search scope and distinguish observed overlap from hypotheses about what remains open.
4. Write one Memory Card per source. Separate findings from the user's notes and your interpretation. Use English by default. For bilingual cards, write the entire English card first and the entire Chinese card second. See [card formats](references/cards.md).

## Apply to Zotero

Use [the import plan reference](references/import-plan.md) for the JSON shape and commands. The helper scripts are in `scripts/` next to this file. Resolve that path from this skill's location, because the shell usually starts in the user's project. Run the local writer's `status` and `plan` before `apply`. The writer discovers the collection and existing matches. Resolve ambiguous matches before writing. Use the user's requested destination and leave existing user-authored notes intact. For an idea revision, read the existing card and preserve decisions still in effect before preparing a replacement for a card managed by this skill.

Apply when the user has requested Zotero changes. If they asked only for suggestions, return the selection and its rationale. Zotero may show a local authorization dialog. Keep authorization keys out of chat, plan files and exports. Avoid editing the database directly. If `status` cannot reach Zotero, ask the user to open Zotero Desktop 10 or later and select Settings → Advanced → Allow other applications on this computer to communicate with Zotero. If Zotero is open with that setting enabled, the assistant's sandbox may be blocking local network access, so request permission to run the command with local network access. If Zotero is still unavailable, provide the plan or notes for review and state what was saved locally.

After writing, check the collection path, records reused or created, card coverage and unresolved citations. When reusing a card, check that it has the requested language coverage. Update a managed card when needed, preserve other notes, and disclose any remaining gaps. Label full-text links separately from abstract pages and report access gaps. Report attached PDFs separately when requested.

## Share a reading list

Use the share helper for the collection the user names. Export Markdown and BibTeX with titles, citation metadata and original links by default. Include card text only when the user requests it, and let the user review the files before sharing or publishing them.
