#!/usr/bin/env python3
"""Copy files shared between skills from the commons skill into the others.

Each skill installs on its own, so a script two skills need must exist in
both; links don't survive installers. The commons skill holds the source of
truth. Edit files there, then run:

    python3 tools/sync_shared.py           # copy
    python3 tools/sync_shared.py --check   # fail if any copy differs (CI, pre-commit)
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "plugins/commons/skills/commons"
# skill directory -> files (relative to the skill root) copied from SOURCE
SHARED = {
    ROOT / "plugins/commons-maintainer/skills/commons-maintainer": [
        "LICENSE",
        "assets/submission.schema.json",
        "scripts/check_submission.py",
        "scripts/search.py",
        "scripts/version.py",
    ],
}


def stale():
    """(target, source) pairs whose target is missing or differs."""
    out = []
    for skill, files in SHARED.items():
        if not skill.is_dir():
            continue
        for rel in files:
            src, dst = SOURCE / rel, skill / rel
            if not dst.is_file() or dst.read_bytes() != src.read_bytes():
                out.append((dst, src))
    return out


def main():
    pairs = stale()
    if "--check" in sys.argv[1:]:
        for dst, src in pairs:
            print(f"shared file out of sync: {dst.relative_to(ROOT)} "
                  f"(run python3 tools/sync_shared.py to copy {src.relative_to(ROOT)})", file=sys.stderr)
        return 1 if pairs else 0
    for dst, src in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"copied {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
