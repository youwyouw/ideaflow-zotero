#!/usr/bin/env python3
"""Generate or check the Claude Code copy of the shared skill."""

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills" / "ideaflow-zotero"
DESTINATION = ROOT / ".claude" / "skills" / "ideaflow-zotero"


def skill_files(directory):
    return {
        path.relative_to(directory): path
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare both folders without writing")
    args = parser.parse_args()
    source = skill_files(SOURCE)
    if Path("SKILL.md") not in source:
        parser.exit(1, "Shared SKILL.md is missing.\n")
    destination = skill_files(DESTINATION)
    extra = sorted(destination.keys() - source.keys())
    if extra:
        parser.exit(1, f"Review extra files in the Claude Code copy: {', '.join(map(str, extra))}\n")
    changed = [
        relative for relative, path in sorted(source.items())
        if relative not in destination or path.read_bytes() != destination[relative].read_bytes()
    ]
    if args.check and changed:
        parser.exit(1, f"Skill copies differ: {', '.join(map(str, changed))}\n")
    for relative in changed:
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source[relative], target)
    print("Claude Code and Codex skill files match.")


if __name__ == "__main__":
    main()
