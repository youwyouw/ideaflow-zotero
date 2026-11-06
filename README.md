# ideaflow-zotero

[简体中文](README.zh-CN.md)

A skill for Codex and Claude Code that turns a research idea into a Zotero reading collection. Give it a question, a set of links, or a meeting PDF. It checks your library, identifies what is worth adding, and prepares a Zotero record and Memory Card for each source. Cards can be written in English or in English and Simplified Chinese.

## What you need

| | Requirement | How to check |
| --- | --- | --- |
| Zotero | **Zotero Desktop 10 or later**, installed on the same computer. [Download Zotero](https://www.zotero.org/download/) | In Zotero, open **Help → About Zotero**. |
| Python | **Python 3.10 or later**. [Download Python](https://www.python.org/downloads/) | Run `python --version` in a terminal. On macOS, run `python3 --version`. |
| Assistant | **Codex** (desktop app or CLI) or **Claude Code** (desktop app or CLI), running on your computer. | The skill runs local scripts. Web chat versions of ChatGPT and Claude cannot reach Zotero on your computer. |

On Windows, select **Add python.exe to PATH** in the Python installer. If `python --version` opens the Microsoft Store instead, install Python from python.org and open a new terminal.

## One-time setup

### 1. Allow other applications to communicate with Zotero

By default, other programs cannot read or change your Zotero library. Turn on Zotero's local API once:

1. Open Zotero Desktop.
2. Open settings. On Windows and Linux, choose **Edit → Settings**. On macOS, choose **Zotero → Settings**.
3. Open the **Advanced** tab and select **Allow other applications on this computer to communicate with Zotero**.

This setting only accepts connections from programs on the same computer. Keep Zotero open whenever you use the skill.

### 2. Get the project

On GitHub, choose **Code → Download ZIP** and extract the ZIP. Use the extracted folder, not the folder inside the ZIP preview. You can also clone the repository with Git.

### 3. Open the folder in your assistant

- **Codex:** open the extracted `ideaflow-zotero` folder as a workspace or project. If Codex asks whether to trust the folder, choose to trust it so it can run the included scripts.
- **Claude Code desktop:** choose the extracted `ideaflow-zotero` folder as the working folder.
- **Claude Code CLI:** open a terminal, move into the folder and start Claude Code:

  ```sh
  cd path/to/ideaflow-zotero
  claude
  ```

The skill is included in `.agents/skills` for Codex and `.claude/skills` for Claude Code. Restart the assistant if it does not list `ideaflow-zotero`.

### 4. Check the connection

Ask the assistant:

```text
Use ideaflow-zotero to check whether Zotero is reachable. Do not change anything.
```

The assistant runs the status command. You can also run it yourself from the project folder:

```sh
python .agents/skills/ideaflow-zotero/scripts/zotero.py status
```

A working setup reports `"reachable": true` and `"write_api_supported": true`. If not, see [Troubleshooting](#troubleshooting).

## First run

Invoke `$ideaflow-zotero` in Codex or `/ideaflow-zotero` in Claude Code, followed by a request like this one:

```text
I want to study whether AI assistants are less likely to
retract a recommendation after they helped a user form the original plan.
Check my Zotero library first, then suggest up to five papers that could
inform the experimental design. Show me the plan before writing anything.
```

Expect three kinds of prompts:

1. **Your assistant asks to run a command.** The skill runs `python …/zotero.py` to read or write Zotero. Review the command and approve it.
2. **The assistant shows a plan.** It lists the target collection and each source it would create, reuse or annotate. Nothing has been written yet. Ask for changes or tell it to apply the plan.
3. **Zotero asks whether to allow `ideaflow-zotero` to write.** Choose **Allow** in the Zotero window. Zotero may ask again later or during a larger import.

To try it safely the first time, ask for one or two papers in a new collection. The skill adds records, collection memberships, tags and its own cards. It keeps your existing notes and does not delete items.

## Use it in other projects

Copy the entire `ideaflow-zotero` skill folder, including `scripts` and `references`, into `~/.agents/skills` for Codex or `~/.claude/skills` for Claude Code. Restart the assistant afterward. [Codex skills](https://learn.chatgpt.com/docs/build-skills) · [Claude Code skills](https://code.claude.com/docs/en/skills)

## Where things go

| Input | Zotero destination | What the skill prepares |
| --- | --- | --- |
| A research question or an evolving project | **Research Ideas → <Idea>** | An Idea Card with the current question, evidence, gap, and next test. Selected sources are filed by what they contribute to the idea. |
| A meeting PDF, survey, or bibliography | **Research Directions → <Source or topic>** | A collection of individually openable references, each with its own Memory Card. |
| Papers you want to read later | **To Read** | One record per source, with an optional Reading Guide for where to start. |

Collection names and tags default to English. Ask for **English and Simplified Chinese** to get one complete English block followed by the Chinese version for each paper. You can also name a destination explicitly, such as `待读`, or specify another note language.

A **Memory Card** covers the takeaway, background, method, conclusion, and gap. It separates the source's findings from your interpretation and makes clear whether the summary draws on the full text, an abstract, or a secondary source. A **Reading Guide** can add a reading order, figure or section pointers, and links to the original. [Card formats](.agents/skills/ideaflow-zotero/references/cards.md)

Zotero items can belong to several collections. The writer can add a collection membership or tag to an existing record and keeps existing notes. When the same plan is applied again, the writer checks for already imported records and cards.

## Share a reading collection

Ask your assistant to export a selected collection as a Markdown reading list and a BibTeX file. By default, the export includes bibliographic information and source links. Ask explicitly to include IdeaFlow Memory Cards, and review the files before sharing. Exports use a fresh output directory to avoid overwriting earlier copies.

## Command line

The skill can prepare a [JSON plan](.agents/skills/ideaflow-zotero/references/import-plan.md) from a reading request. From the repository root, you can inspect a plan yourself. The bundled [example](examples/persona-mechanisms.json) uses public sources.

```sh
python .agents/skills/ideaflow-zotero/scripts/zotero.py status
python .agents/skills/ideaflow-zotero/scripts/zotero.py search "persona vectors" --limit 10
python .agents/skills/ideaflow-zotero/scripts/zotero.py plan examples/persona-mechanisms.json
python .agents/skills/ideaflow-zotero/scripts/zotero.py apply examples/persona-mechanisms.json
python .agents/skills/ideaflow-zotero/scripts/zotero.py collections
python .agents/skills/ideaflow-zotero/scripts/share.py COLLECTION_KEY --output-dir share
```

`plan` reads your library and previews proposed changes. Run `apply` when you want to make those changes through Zotero's own write authorization. Look up `COLLECTION_KEY` in the `collections` output. `share.py` writes `reading-list.md` and `references.bib`. Pass `--include-cards` to include IdeaFlow Memory Cards. If your Python installation uses the `python3` command, substitute it for `python`.

## Local access and source material

The Python scripts communicate with Zotero Desktop on `127.0.0.1`. Use your existing Codex or Claude Code access. The skill itself requires no separate model API key. Your assistant can use its available tools to read materials you provide and look up public sources. Zotero changes may sync if you have enabled Zotero Sync. [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api)

The workflow stores source links and reading notes. Full text is subject to the publisher's access terms. A paper can remain in the collection with an abstract-based card when its full text is unavailable.

## Troubleshooting

| Message or symptom | What to do |
| --- | --- |
| `Could not complete GET /. Keep Zotero open and check that its local API is enabled.` | Open Zotero Desktop and turn on the setting in [step 1](#1-allow-other-applications-to-communicate-with-zotero). If Zotero is open and the setting is on, your assistant's sandbox may block local network access. Approve the command when asked, or allow the assistant to run it with local network access. |
| `HTTP 403` or `Zotero did not grant write authorization.` | Check the setting in step 1, then run the request again and choose **Allow** in Zotero's prompt. |
| `"write_api_supported": false` | Update Zotero to version 10 or later from **Help → Check for Updates**. |
| `HTTP 429` | Zotero limited repeated authorization prompts. Wait a minute before trying again. |
| `HTTP 409` or `HTTP 412` | Zotero was busy or the library changed. Ask the assistant to preview the plan again. |
| `python` is not recognized, or the Microsoft Store opens | Install Python from python.org with **Add python.exe to PATH** selected, then open a new terminal. On macOS, use `python3`. |
| The assistant does not know `ideaflow-zotero` | Check that you opened the project folder itself, not its parent folder. Restart the assistant. |
| The assistant cannot find `zotero.py` | The scripts are in `.agents/skills/ideaflow-zotero/scripts` and `.claude/skills/ideaflow-zotero/scripts`. Tell the assistant this path. |

## Related work

For broader Zotero operations from an agent, see the [OpenAI Zotero skill](https://github.com/openai/plugins/tree/main/plugins/zotero) or [zotero-native-mcp](https://github.com/dvdsosa/zotero-native-mcp). [Zotivity](https://github.com/avibecoder42/Zotivity) is a standalone application with screening and literature-review workflows.

## Maintaining the shared skill

Edit `.agents/skills/ideaflow-zotero`, then run `python tools/sync_skills.py` to update the Claude Code copy. Run `python tools/sync_skills.py --check` to verify that the two copies match.

## License

[MIT](LICENSE)
