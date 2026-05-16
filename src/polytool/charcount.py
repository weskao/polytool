"""charcount — count characters in text or file, with optional limit check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="charcount",
        description="Count characters in text or file, with optional limit check.",
    )
    parser.add_argument("-f", "--file", help="Read input from a file")
    parser.add_argument(
        "-l", "--limit", type=int, default=0, help="Character limit; report overflow"
    )
    parser.add_argument("text", nargs="*", help="Text to count (positional)")
    args = parser.parse_args(argv)

    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / args.file
        if not path.is_file():
            print(f"❌ File not found: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
    else:
        text = " ".join(args.text)

    if not text:
        parser.print_help(sys.stderr)
        return 1

    count = len(text)
    if args.limit > 0:
        print(f"📝 Character count: {count} / {args.limit}")
        if count > args.limit:
            print(f"⚠️  Exceeded by {count - args.limit} characters")
            return 1
        print("✅ Within limit")
    else:
        print(f"📝 Character count: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
