#!/usr/bin/env python3
"""Static check that every install route can find every shipped skill, and that
each plugin folder meets the directory's mechanical submission rules.

The discovery rules were read from each client's source or docs on 2026-10-25,
and the directory rules from claude.com/docs/plugins/pre-submission-checklist
on 2026-11-02. This is a regression check on our layout, not a substitute for
installing in a real client or running Validate in the developer portal:

- Claude Code reads .claude-plugin/marketplace.json; a plugin's skills are
  <plugin>/skills/<name>/SKILL.md.
- Codex reads the first of .agents/plugins/marketplace.json and
  .claude-plugin/marketplace.json. With no skills path in a manifest it scans
  <plugin>/skills/, and only <plugin>/skills/<name>/SKILL.md counts. A plugin
  root that is itself a skill is not found (openai/codex 970111f6,
  core-plugins/src/loader.rs default_skill_roots, ext/skills discovery.rs).
- The skills CLI (vercel-labs/skills 1.7.4, src/plugin-manifest.ts) searches
  <source>/skills/ for each local entry in .claude-plugin/marketplace.json.
- The directory submits one plugin folder at a time. It needs
  .claude-plugin/plugin.json to list a plugin beyond Claude Code, a README of
  at least 40 words outside code blocks, and a license. The icon is a square
  PNG of 512-2048 px under 2 MB, captured once at the first portal save.

    python3 tools/check_packaging.py
"""
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_shared import stale  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude-plugin/marketplace.json"
CODEX = ROOT / ".agents/plugins/marketplace.json"
MANIFEST_FIELDS = ["name", "displayName", "description", "author", "homepage", "repository", "license",
                   "icon", "documentationUrl", "supportUrl", "privacyPolicyUrl"]
URL_FIELDS = ["homepage", "repository", "documentationUrl", "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl"]
OS_JUNK = {".DS_Store", "Thumbs.db", "desktop.ini", "__MACOSX"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def entries(path, codex):
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for e in data.get("plugins", []):
        src = e.get("source")
        if codex and isinstance(src, dict):
            src = src.get("path") if src.get("source") == "local" else None
        out[e["name"]] = src
    return data.get("name"), out


def png_size(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def readme_words(path):
    text = re.sub(r"```.*?```", " ", path.read_text(encoding="utf-8"), flags=re.S)
    return len(re.findall(r"\w+", text))


def check_directory_rules(name, root):
    problems = []
    manifest_path = root / ".claude-plugin/plugin.json"
    if not manifest_path.is_file():
        return [f"{name}: no .claude-plugin/plugin.json; the directory would list it for Claude Code only"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("name") != name:
        problems.append(f"{name}: plugin.json name {manifest.get('name')!r} must equal the marketplace entry name")
    for field in MANIFEST_FIELDS:
        if not manifest.get(field):
            problems.append(f"{name}: plugin.json is missing {field}")
    for field in URL_FIELDS:
        if field in manifest and not str(manifest[field]).startswith("https://"):
            problems.append(f"{name}: plugin.json {field} must be an https URL")
    icon = root / str(manifest.get("icon", "./.claude-plugin/icon.png"))
    size = png_size(icon) if icon.is_file() else None
    if not size:
        problems.append(f"{name}: icon {icon.relative_to(ROOT)} must be a PNG")
    elif size[0] != size[1] or not 512 <= size[0] <= 2048 or icon.stat().st_size >= 2 * 1024 * 1024:
        problems.append(f"{name}: icon must be square, 512-2048 px and under 2 MB; it is {size} "
                        f"and {icon.stat().st_size} bytes")
    readme = root / "README.md"
    if not readme.is_file() or readme_words(readme) < 40:
        problems.append(f"{name}: needs a README.md of at least 40 words outside code blocks")
    if not (root / "LICENSE").is_file():
        problems.append(f"{name}: needs a LICENSE file in the plugin folder")
    files = [p for p in root.rglob("*") if p.is_file()]
    if len(files) > 512:
        problems.append(f"{name}: {len(files)} files; the directory holds plugins over 512 for a reviewer")
    for p in root.rglob("*"):
        rel = p.relative_to(ROOT)
        if p.name in OS_JUNK:
            problems.append(f"{rel}: OS file; the directory blocks it")
        elif p.is_file() and p.suffix.lower() not in IMAGE_SUFFIXES and p.stat().st_size >= 256 * 1024:
            problems.append(f"{rel}: non-image files of 256 KiB or more are held for a reviewer")
    return problems


def main():
    problems = []
    claude_name, claude = entries(CLAUDE, codex=False)
    codex_name, codex = entries(CODEX, codex=True)
    if claude_name != codex_name:
        problems.append(f"marketplace names differ: {claude_name!r} vs {codex_name!r}")
    if claude != codex:
        problems.append(f"marketplaces list different plugins or sources: {claude} vs {codex}")

    shipped = {p.parent.name for p in ROOT.glob("plugins/*/skills/*/SKILL.md")}
    listed = set()
    for name, src in sorted(claude.items()):
        if not isinstance(src, str) or not src.startswith("./plugins/"):
            problems.append(f"{name}: source must be a local ./plugins/<name> path, got {src!r}")
            continue
        root = (ROOT / src).resolve()
        if not root.is_relative_to(ROOT) or not root.is_dir():
            problems.append(f"{name}: source {src} is missing or outside the repo")
            continue
        if (root / "SKILL.md").exists():
            problems.append(f"{name}: SKILL.md at the plugin root; Codex won't find it. Use skills/<name>/SKILL.md")
        skills = sorted(p.parent.name for p in (root / "skills").glob("*/SKILL.md"))
        if not skills:
            problems.append(f"{name}: no skills/<name>/SKILL.md under {src}")
        listed.update(skills)
        problems += check_directory_rules(name, root)
    for orphan in sorted(shipped - listed):
        problems.append(f"skill {orphan} is in plugins/ but no marketplace lists its plugin")

    for dst, _ in stale():
        problems.append(f"shared file out of sync: {dst.relative_to(ROOT)} (run tools/sync_shared.py)")

    for p in problems:
        print(f"packaging: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
