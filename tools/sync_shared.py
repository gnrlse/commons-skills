#!/usr/bin/env python3
"""Copy files that must exist in several shipped places from their single source.

Each plugin, and each skill inside it, installs without the rest of the repo,
so a file two of them need must exist in both; links don't survive installers.
Sources of truth: the root LICENSE, and the commons skill for shared scripts.
Edit the source, then run:

    python3 tools/sync_shared.py           # copy
    python3 tools/sync_shared.py --check   # fail if any copy differs (CI, pre-commit)
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMONS = ROOT / "plugins/agent-commons/skills/commons"
MAINTAINER = ROOT / "plugins/agent-commons-maintainer/skills/commons-maintainer"

# (source, copy) pairs; a copy whose plugin or skill doesn't exist yet is skipped
SHARED = [(ROOT / "LICENSE", ROOT / "plugins" / p / "LICENSE") for p in ("agent-commons", "agent-commons-maintainer")]
SHARED += [(ROOT / "LICENSE", skill / "LICENSE") for skill in (COMMONS, MAINTAINER)]
SHARED += [(COMMONS / rel, MAINTAINER / rel) for rel in (
    "assets/submission.schema.json",
    "scripts/check_submission.py",
    "scripts/search.py",
    "scripts/version.py",
)]


def stale():
    """(copy, source) pairs whose copy is missing or differs."""
    return [(dst, src) for src, dst in SHARED
            if dst.parent.parent.is_dir() and (not dst.is_file() or dst.read_bytes() != src.read_bytes())]


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
