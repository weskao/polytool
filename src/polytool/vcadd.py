"""vcadd — Append a Chinese word with Bopomofo reading to vChewing userdata-cht.txt."""

from __future__ import annotations

import sys
from pathlib import Path

from pypinyin import Style, lazy_pinyin

from polytool._utils import git_sync, is_git_repo

FILE = (
    Path.home()
    / "Library/Containers/org.atelierInmu.inputmethod.vChewing"
    / "Data/Library/Application Support/vChewing/userdata-cht.txt"
)


def _to_bopomofo(word: str) -> str:
    return "-".join(lazy_pinyin(word, style=Style.BOPOMOFO))


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
        repo_dir = FILE.parent
        if is_git_repo(repo_dir):
            words = ", ".join(w.split()[0] for w in added)
            git_steps = git_sync(repo_dir, FILE, f"vcadd: {words}")
            if git_steps:
                print("📦 Git: " + " → ".join(git_steps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
