#!/usr/bin/env python3
"""Build dist/<skill>.zip for uploading a skill to claude.ai or Claude Desktop.

The zip holds one top-level <skill>/ folder with SKILL.md inside, which is
the layout the upload expects. Refuses to build if the isolation check fails.

    python3 tools/build_zip.py [SKILL]     # default: commons
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_skill_isolation import ROOT, SKILLS, check_skill  # noqa: E402

SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {".DS_Store"}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "commons"
    skill = SKILLS / name
    problems = check_skill(skill)
    if problems:
        for p in problems:
            print(f"skill isolation: {p}", file=sys.stderr)
        return 1

    out = ROOT / "dist" / f"{name}.zip"
    out.parent.mkdir(exist_ok=True)
    files = [p for p in sorted(skill.rglob("*"))
             if p.is_file() and p.name not in SKIP_FILES and p.suffix != ".pyc"
             and not SKIP_DIRS & set(p.relative_to(skill).parts)]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path(name) / p.relative_to(skill))
    print(f"{out.relative_to(ROOT)}: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
