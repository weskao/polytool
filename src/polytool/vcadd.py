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

# The "Reload User Phrases" command lives in vChewing's input-method status
# menu, which on modern macOS is hosted by the TextInputMenuAgent process (not
# the vChewing process itself). The status item only exposes vChewing's menu
# when vChewing is the active input source, so we filter by description and
# fail with a clear message otherwise.
_RELOAD_SCRIPT = """
tell application "System Events"
    tell process "TextInputMenuAgent"
        set imItems to (menu bar items of menu bar 2 whose description contains "vChewing")
        if imItems is {} then error "vChewing is not the active input source"
        set mb to item 1 of imItems
        click mb
        delay 0.3
        try
            click menu item "Reload User Phrases" of menu 1 of mb
        on error errMsg
            -- Dismiss the menu we just opened so it is not left hanging on screen.
            key code 53
            error errMsg
        end try
    end tell
end tell
"""


def _to_bopomofo(word: str) -> str:
    return "-".join(lazy_pinyin(word, style=Style.BOPOMOFO))


def _reload_vchewing() -> None:
    # A bounded timeout keeps osascript from hanging indefinitely on the UI; on
    # timeout subprocess.run kills the child and reaps it, so no process is left
    # behind.
    try:
        result = subprocess.run(
            ["osascript", "-e", _RELOAD_SCRIPT],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        print("Reload failed (manually press Reload User Phrases): osascript timed out")
        return
    if result.returncode == 0:
        print("vChewing reloaded.")
    else:
        print(f"Reload failed (manually press Reload User Phrases): {result.stderr.strip()}")


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
