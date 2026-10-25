#!/usr/bin/env python3
"""Identify exactly which version of this skill is running. Standard library only.

Usage: version.py [--json]

Prints the git tree hash of this skill's directory. That's the value
`git rev-parse <commit>:<path to this skill>` gives for the commit it came
from, so anyone with the repository can find that commit, even though an
installed copy has no git metadata. If no commit matches, the copy was
modified. Inside a git checkout it also prints the commit, and whether the
skill has uncommitted changes.

Tag Commons feedback about this skill with the suggested labels it prints.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

UPSTREAM = "https://github.com/gnrlse/commons-skills"
SKILL_DIR = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__"}


def blob_hash(data):
    if b"\0" not in data:  # text: hash it as git stores it, with LF line endings
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree_hash(directory):
    """Git's SHA-1 tree hash of a directory, every file as mode 100644. None if empty."""
    entries = []
    for child in directory.iterdir():
        if child.name.startswith(".") or child.name in SKIP_DIRS or child.suffix == ".pyc" or child.is_symlink():
            continue
        if child.is_dir():
            sub = tree_hash(child)
            if sub:
                entries.append((child.name.encode() + b"/", b"40000 " + child.name.encode(), sub))
        elif child.is_file():
            entries.append((child.name.encode(), b"100644 " + child.name.encode(), blob_hash(child.read_bytes())))
    if not entries:
        return None
    body = b"".join(head + b"\0" + bytes.fromhex(sha) for _, head, sha in sorted(entries))
    return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()


def git(*args):
    try:
        out = subprocess.run(["git", "-C", str(SKILL_DIR), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def checkout_info():
    top = git("rev-parse", "--show-toplevel")
    commit = top and git("rev-parse", "HEAD")
    if not commit:
        return None
    path = SKILL_DIR.relative_to(Path(top).resolve()).as_posix()
    dirty = bool(git("status", "--porcelain", "--", "."))
    return {"commit": commit, "path": path, "uncommitted_changes": dirty}


def plugin_cache_info():
    """Claude Code and Codex install plugins under .../plugins/cache/<marketplace>/<plugin>/<version>/."""
    parts = SKILL_DIR.parts
    for i in range(1, len(parts) - 3):
        if parts[i] == "cache" and parts[i - 1] == "plugins":
            client = "Codex" if ".codex" in parts[:i] else "Claude Code" if ".claude" in parts[:i] else "a plugin host"
            return {"client": client, "plugin": f"{parts[i + 2]}@{parts[i + 1]}", "cache_version": parts[i + 3]}
    return None


def main():
    info = {"skill": SKILL_DIR.name, "upstream": UPSTREAM, "git_tree": tree_hash(SKILL_DIR)}
    checkout, cache = checkout_info(), plugin_cache_info()
    if checkout:
        info["checkout"] = checkout
    if cache:
        info["installed"] = cache
    if checkout and not checkout["uncommitted_changes"]:
        tags = [f"software={UPSTREAM}", f"git-commit={checkout['commit']}"]
    else:
        tags = [f"software={UPSTREAM}", f"git-tree={info['git_tree']}"]
    info["suggested_tags"] = tags

    if "--json" in sys.argv[1:]:
        print(json.dumps(info, indent=2))
        return 0
    print(f"skill: {info['skill']}")
    print(f"git-tree: {info['git_tree']}  (git tree hash of this skill directory)")
    if checkout:
        state = "with uncommitted changes" if checkout["uncommitted_changes"] else "clean"
        print(f"git-commit: {checkout['commit']}  ({checkout['path']} in this checkout, {state})")
    if cache:
        print(f"installed: {cache['client']} plugin {cache['plugin']}, cache version {cache['cache_version']}")
    print(f"upstream: {UPSTREAM}")
    print("tags for Commons feedback about this skill: " + " ".join(tags))
    return 0


if __name__ == "__main__":
    sys.exit(main())
