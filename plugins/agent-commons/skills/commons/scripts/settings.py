#!/usr/bin/env python3
"""Read or change the user's standing choice about searching Commons. Standard library only.

Usage: settings.py [get]
       settings.py set ask|always|never
       settings.py reset

  ask     (default) ask once per session before the first search
  always  search without asking
  never   don't search, and don't ask

The choice is kept in one small JSON file, and nothing else is stored:
$COMMONS_SETTINGS if set; otherwise commons/settings.json under
$XDG_CONFIG_HOME (default ~/.config), or %APPDATA% on Windows. If the file
can't be written, as in many sandboxes, the choice lasts only for the session.
"""
import json
import os
import sys
from pathlib import Path

VALUES = ("ask", "always", "never")


def settings_path():
    if os.environ.get("COMMONS_SETTINGS"):
        return Path(os.environ["COMMONS_SETTINGS"])
    if os.name == "nt" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "commons" / "settings.json"


def read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("search", "ask")
    except (OSError, ValueError, AttributeError):
        return "ask"
    return value if value in VALUES else "ask"


def main():
    args = sys.argv[1:] or ["get"]
    path = settings_path()
    if args == ["get"]:
        print(f"search={read(path)}")
        print(f"file: {path}{'' if path.exists() else ' (not created yet; default applies)'}")
        return 0
    if args == ["reset"]:
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            print(f"couldn't remove {path}: {e}", file=sys.stderr)
            return 1
        print("search=ask (reset to the default)")
        return 0
    if len(args) == 2 and args[0] == "set" and args[1] in VALUES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"search": args[1]}) + "\n", encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            print(f"couldn't save to {path} ({e}); treat search={args[1]} as this session's choice only",
                  file=sys.stderr)
            return 1
        print(f"search={args[1]} (saved to {path})")
        return 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
