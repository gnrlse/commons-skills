#!/usr/bin/env python3
"""Fail if a shipped skill leaks this repo's development setup.

Each directory under skills/ is installed on its own into other agents'
environments, so it must not mention our tooling (beads/bd), reference
local paths, or link to files outside itself. Run from anywhere:

    python3 tools/check_skill_isolation.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

FORBIDDEN = [
    (re.compile(r"\bbeads?\b", re.I), "mentions beads"),
    (re.compile(r"(?<![\w-])bd\s+(ready|show|create|update|close|sync|prime|init|dolt|remember)\b"),
     "uses a bd command"),
    (re.compile(r"\.beads/|AGENTS\.md|CLAUDE\.md"), "references repo-level agent files"),
    (re.compile(r"/home/|/Users/|/tmp/claude"), "contains a local absolute path"),
]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def check_skill(skill):
    problems = []
    manifest = skill / "SKILL.md"
    if not manifest.is_file():
        return [f"{skill.name}: missing SKILL.md"]
    head = manifest.read_text(encoding="utf-8").split("---")
    front = head[1] if len(head) > 2 and not head[0].strip() else ""
    name = re.search(r"^name:\s*(\S+)", front, re.M)
    if not name or name.group(1) != skill.name:
        problems.append(f"{skill.name}/SKILL.md: frontmatter name must be {skill.name!r}")
    if not re.search(r"^description:\s*\S", front, re.M):
        problems.append(f"{skill.name}/SKILL.md: frontmatter needs a description")

    for path in sorted(skill.rglob("*")):
        rel = path.relative_to(SKILLS)
        if path.is_symlink() and not path.resolve().is_relative_to(skill.resolve()):
            problems.append(f"{rel}: symlink points outside the skill")
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern, why in FORBIDDEN:
                if pattern.search(line):
                    problems.append(f"{rel}:{lineno}: {why}: {line.strip()[:80]}")
        if path.suffix == ".md":
            for target in LINK.findall(text):
                if re.match(r"[a-z][a-z0-9+.-]*:|#", target, re.I):
                    continue  # URL, mailto: or in-page anchor
                dest = (path.parent / target.split("#")[0]).resolve()
                if not dest.is_relative_to(skill.resolve()):
                    problems.append(f"{rel}: link {target!r} leaves the skill directory")
                elif not dest.exists():
                    problems.append(f"{rel}: link {target!r} is broken")
    return problems


def main():
    skills = [p for p in sorted(SKILLS.iterdir()) if p.is_dir()] if SKILLS.is_dir() else []
    problems = [p for skill in skills for p in check_skill(skill)]
    for p in problems:
        print(f"skill isolation: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
