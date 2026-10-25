#!/usr/bin/env python3
"""Build dist/<skill>.zip for uploading skills to claude.ai or Claude Desktop.

Each zip holds one top-level <skill>/ folder with SKILL.md inside, which is
the layout the upload expects. Refuses to build if the isolation check fails.

    python3 tools/build_zip.py [SKILL ...]     # default: every shipped skill
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_skill_isolation import ROOT, check_skill, skill_dirs  # noqa: E402

SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {".DS_Store"}


def build(skill):
    out = ROOT / "dist" / f"{skill.name}.zip"
    out.parent.mkdir(exist_ok=True)
    files = [p for p in sorted(skill.rglob("*"))
             if p.is_file() and p.name not in SKIP_FILES and p.suffix != ".pyc"
             and not SKIP_DIRS & set(p.relative_to(skill).parts)]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path(skill.name) / p.relative_to(skill))
    print(f"{out.relative_to(ROOT)}: {len(files)} files")


def main():
    skills = {s.name: s for s in skill_dirs()}
    wanted = sys.argv[1:] or sorted(skills)
    unknown = [n for n in wanted if n not in skills]
    if unknown:
        print(f"unknown skill(s): {unknown}; have {sorted(skills)}", file=sys.stderr)
        return 1
    problems = [p for n in wanted for p in check_skill(skills[n])]
    if problems:
        for p in problems:
            print(f"skill isolation: {p}", file=sys.stderr)
        return 1
    for n in wanted:
        build(skills[n])
    return 0


if __name__ == "__main__":
    sys.exit(main())
