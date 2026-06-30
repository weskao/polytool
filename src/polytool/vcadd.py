"""vcadd — Append a Chinese word with Bopomofo reading to vChewing userdata-cht.txt."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pypinyin import Style, lazy_pinyin

from polytool._utils import git_sync, is_git_repo

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

# When vChewing is not the active input source, open the IM picker menu, click
# the vChewing entry to activate it, then reload.  Direct menu items of the
# picker are the installed input sources listed by name.
_SWITCH_AND_RELOAD_SCRIPT = """
tell application "System Events"
    tell process "TextInputMenuAgent"
        set mb2 to menu bar 2
        set mbItem to (first menu bar item of mb2)
        click mbItem
        delay 0.4
        set didSwitch to false
        repeat with mi in (menu items of menu 1 of mbItem)
            try
                if (name of mi) contains "vChewing" then
                    click mi
                    set didSwitch to true
                    exit repeat
                end if
            end try
        end repeat
        if not didSwitch then
            key code 53
            error "vChewing not found in input source list"
        end if
        set didActivate to false
        repeat 6 times
            delay 0.4
            set imItems to (menu bar items of mb2 whose description contains "vChewing")
            if imItems is not {} then
                set didActivate to true
                exit repeat
            end if
        end repeat
        if not didActivate then error "vChewing did not become active after switching"
        set mb to item 1 of imItems
        click mb
        delay 0.3
        try
            click menu item "Reload User Phrases" of menu 1 of mb
        on error errMsg
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
        print("⚠️  Reload failed (manually press Reload User Phrases): osascript timed out")
        return
    if result.returncode == 0:
        print("🔄 vChewing reloaded.")
        return
    if "not the active input source" not in result.stderr:
        print(f"⚠️  Reload failed (manually press Reload User Phrases): {result.stderr.strip()}")
        return
    # vChewing is not active — switch to it via the IM picker menu, then reload.
    try:
        result2 = subprocess.run(
            ["osascript", "-e", _SWITCH_AND_RELOAD_SCRIPT],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        print("⚠️  Reload failed (manually press Reload User Phrases): osascript timed out")
        return
    if result2.returncode == 0:
        print("🔄 vChewing reloaded.")
    else:
        print(f"⚠️  Reload failed (manually press Reload User Phrases): {result2.stderr.strip()}")


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
                print(f"⏭️  Already exists: {word}")
                continue
            entry = f"{word} {_to_bopomofo(word)}"
            f.write(entry + "\n")
            existing.add(word)
            added.append(entry)
            print(f"✅ Added: {entry}")

    if added:
        _reload_vchewing()
        repo_dir = FILE.parent
        if is_git_repo(repo_dir):
            words = ", ".join(w.split()[0] for w in added)
            git_steps = git_sync(repo_dir, FILE, f"vcadd: {words}")
            if git_steps:
                print("📦 Git: " + " → ".join(git_steps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
