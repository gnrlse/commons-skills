#!/usr/bin/env python3
"""Fail if a shipped skill leaks this repo's development setup.

Skills live at plugins/<plugin>/skills/<skill>/ and are installed on their
own into other agents' environments, so each must not mention our tooling
(beads/bd), reference local paths, link to files outside itself, or carry
executable bits (installers don't preserve them consistently, and version.py
assumes none). A plugin directory ships too, so it may hold only skills/,
.claude-plugin/ (plugin.json and icon.png), README.md and LICENSE, and the
same text checks apply to those files.
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


PLUGIN_ENTRIES = {"skills", ".claude-plugin", "README.md", "LICENSE"}
MANIFEST_ENTRIES = {"plugin.json", "icon.png"}


def check_text(path, label):
    """Forbidden patterns in any shipped text file."""
    problems = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return problems
    if "\r\n" in text:
        problems.append(f"{label}: CRLF line endings")
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern, why in FORBIDDEN:
            if pattern.search(line):
                problems.append(f"{label}:{lineno}: {why}: {line.strip()[:80]}")
    return problems


def check_links(path, root, label):
    """Relative markdown links must resolve inside root, which ships on its own."""
    problems = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"[a-z][a-z0-9+.-]*:|#", target, re.I):
            continue  # URL, mailto: or in-page anchor
        dest = (path.parent / target.split("#")[0]).resolve()
        if not dest.is_relative_to(root.resolve()):
            problems.append(f"{label}: link {target!r} leaves {root.relative_to(ROOT)}")
        elif not dest.exists():
            problems.append(f"{label}: link {target!r} is broken")
    return problems


def check_plugin(plugin):
    """A plugin folder ships too: only its skills, manifest, icon, README and LICENSE."""
    problems = []
    extra = sorted(p.name for p in plugin.iterdir() if p.name not in PLUGIN_ENTRIES)
    if extra:
        problems.append(f"{plugin.name}: plugin directory may contain only {sorted(PLUGIN_ENTRIES)}, found {extra}")
    manifest_dir = plugin / ".claude-plugin"
    if manifest_dir.is_dir():
        extra = sorted(p.name for p in manifest_dir.iterdir() if p.name not in MANIFEST_ENTRIES)
        if extra:
            problems.append(f"{plugin.name}/.claude-plugin: may contain only {sorted(MANIFEST_ENTRIES)}, found {extra}")
    for rel in ("README.md", "LICENSE", ".claude-plugin/plugin.json"):
        path = plugin / rel
        if path.is_symlink():
            problems.append(f"{plugin.name}/{rel}: symlinks don't survive every installer")
        elif path.is_file():
            problems += check_text(path, f"{plugin.name}/{rel}")
    if (plugin / "README.md").is_file():
        problems += check_links(plugin / "README.md", plugin, f"{plugin.name}/README.md")
    return problems


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
        problems += check_text(path, str(rel))
        if path.suffix == ".md":
            problems += check_links(path, skill, str(rel))
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
