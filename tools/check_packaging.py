#!/usr/bin/env python3
"""Static check that every install route can find every shipped skill.

These rules were read from each client's source or docs on 2026-10-25. They
are a regression check on our layout, not a substitute for installing in a
real client:

- Claude Code reads .claude-plugin/marketplace.json; a plugin's skills are
  <plugin>/skills/<name>/SKILL.md.
- Codex reads the first of .agents/plugins/marketplace.json and
  .claude-plugin/marketplace.json. With no skills path in a manifest it scans
  <plugin>/skills/, and only <plugin>/skills/<name>/SKILL.md counts. A plugin
  root that is itself a skill is not found (openai/codex 970111f6,
  core-plugins/src/loader.rs default_skill_roots, ext/skills discovery.rs).
- The skills CLI (vercel-labs/skills 1.7.4, src/plugin-manifest.ts) searches
  <source>/skills/ for each local entry in .claude-plugin/marketplace.json.

    python3 tools/check_packaging.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_shared import stale  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude-plugin/marketplace.json"
CODEX = ROOT / ".agents/plugins/marketplace.json"


def entries(path, codex):
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for e in data.get("plugins", []):
        src = e.get("source")
        if codex and isinstance(src, dict):
            src = src.get("path") if src.get("source") == "local" else None
        out[e["name"]] = src
    return data.get("name"), out


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
        if name not in skills:
            problems.append(f"{name}: plugin should ship a skill of the same name, found {skills}")
        listed.update(skills)
    for orphan in sorted(shipped - listed):
        problems.append(f"skill {orphan} is in plugins/ but no marketplace lists its plugin")

    for dst, _ in stale():
        problems.append(f"shared file out of sync: {dst.relative_to(ROOT)} (run tools/sync_shared.py)")

    for p in problems:
        print(f"packaging: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
