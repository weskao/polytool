"""vcadd — Append a Chinese word with Bopomofo reading to vChewing userdata-cht.txt."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pypinyin import Style, lazy_pinyin

FILE = (
    Path.home()
    / "Library/Containers/org.atelierInmu.inputmethod.vChewing"
    / "Data/Library/Application Support/vChewing/userdata-cht.txt"
)

_RELOAD_SCRIPT = """
tell application "System Events"
    tell process "vChewing"
        set mb to menu bar item 1 of menu bar 2
        click mb
        delay 0.3
        click menu item "Reload User Phrases" of menu 1 of mb
    end tell
end tell
"""


def _to_bopomofo(word: str) -> str:
    return "-".join(lazy_pinyin(word, style=Style.BOPOMOFO))


def _reload_vchewing() -> None:
    result = subprocess.run(["osascript", "-e", _RELOAD_SCRIPT], capture_output=True, text=True)
    if result.returncode == 0:
        print("vChewing reloaded.")
    else:
        print(f"Reload failed (手動按 Reload User Phrases): {result.stderr.strip()}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        print("Usage: vcadd <Chinese word/phrase>", file=sys.stderr)
        return 1

    content = FILE.read_text(encoding="utf-8")
    existing = {
        line.split(maxsplit=1)[0]
        for line in content.splitlines()
        if line and not line.startswith("#") and not line.startswith(" ")
    }

    added: list[str] = []
    with FILE.open("a", encoding="utf-8") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        for word in args:
            if word in existing:
                print(f"Already exists: {word}")
                continue
            entry = f"{word} {_to_bopomofo(word)}"
            f.write(entry + "\n")
            existing.add(word)
            added.append(entry)
            print(f"Added: {entry}")

    if added:
        _reload_vchewing()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
