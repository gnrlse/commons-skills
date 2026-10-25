#!/usr/bin/env python3
"""Fail if a shipped skill leaks this repo's development setup.

Skills live at plugins/<plugin>/skills/<skill>/ and are installed on their
own into other agents' environments, so each must not mention our tooling
(beads/bd), reference local paths, link to files outside itself, or carry
executable bits (installers don't preserve them consistently, and version.py
assumes none). Each plugin directory may contain only its skills/ folder.
Run from anywhere:

    python3 tools/check_skill_isolation.py
"""
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

FORBIDDEN = [
    (re.compile(r"\bbeads?\b", re.I), "mentions beads"),
    (re.compile(r"(?<![\w-])bd\s+(ready|show|create|update|close|sync|prime|init|dolt|remember)\b"),
     "uses a bd command"),
    (re.compile(r"\.beads/|AGENTS\.md|CLAUDE\.md"), "references repo-level agent files"),
    (re.compile(r"/home/|/Users/|/tmp/claude"), "contains a local absolute path"),
]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def skill_dirs():
    """Every shipped skill directory, as plugins/<plugin>/skills/<skill>/."""
    return sorted(p.parent for p in PLUGINS.glob("*/skills/*/SKILL.md"))


def check_plugin(plugin):
    extra = sorted(p.name for p in plugin.iterdir() if p.name != "skills")
    return [f"{plugin.name}: plugin directory may contain only skills/, found {extra}"] if extra else []


def check_skill(skill):
    problems = []
    label = skill.relative_to(PLUGINS)
    manifest = skill / "SKILL.md"
    if not manifest.is_file():
        return [f"{label}: missing SKILL.md"]
    head = manifest.read_text(encoding="utf-8").split("---")
    front = head[1] if len(head) > 2 and not head[0].strip() else ""
    name = re.search(r"^name:\s*(\S+)", front, re.M)
    if not name or name.group(1) != skill.name:
        problems.append(f"{label}/SKILL.md: frontmatter name must be {skill.name!r}")
    if not re.search(r"^description:\s*\S", front, re.M):
        problems.append(f"{label}/SKILL.md: frontmatter needs a description")
    if not (skill / "LICENSE").is_file():
        problems.append(f"{label}: needs its own LICENSE (it is installed without the repo)")

    for path in sorted(skill.rglob("*")):
        rel = path.relative_to(PLUGINS)
        if path.is_symlink():
            problems.append(f"{rel}: symlinks don't survive every installer")
            continue
        if "__pycache__" in path.parts or not path.is_file():
            continue
        if path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            problems.append(f"{rel}: executable bit set; run scripts with python3 instead")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "\r\n" in text:
            problems.append(f"{rel}: CRLF line endings")
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
    plugins = sorted(p for p in PLUGINS.iterdir() if p.is_dir()) if PLUGINS.is_dir() else []
    problems = [p for plugin in plugins for p in check_plugin(plugin)]
    problems += [p for skill in skill_dirs() for p in check_skill(skill)]
    if not skill_dirs():
        problems.append("no skills found under plugins/*/skills/")
    for p in problems:
        print(f"skill isolation: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
