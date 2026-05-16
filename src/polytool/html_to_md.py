"""html2md — convert HTML files to Markdown via pandoc."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ._utils import ensure_brew_package, log_green, log_red


def _convert(src: Path) -> bool:
    dst = src.with_suffix(".md")
    res = subprocess.run(
        ["pandoc", str(src), "-f", "html", "-t", "markdown", "-o", str(dst), "--wrap=none"],
        capture_output=True,
    )
    if res.returncode == 0:
        log_green(f"✅ {src} → {dst}")
        return True
    log_red(f"❌ Failed: {src}")
    if res.stderr:
        print(res.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="html2md",
        description="Convert HTML files to Markdown via pandoc.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Specific HTML file to convert (defaults to *.html in the current directory). "
        "A .md filename is auto-mapped to the matching .html source.",
    )
    args = parser.parse_args(argv)

    if not ensure_brew_package("pandoc"):
        return 1

    if not args.file:
        cwd = Path.cwd()
        found = list(cwd.glob("*.html"))
        if not found:
            print("⚠️  當前目錄找不到任何 .html 檔", file=sys.stderr)
            return 0
        ok = True
        for f in found:
            ok = _convert(f) and ok
        return 0 if ok else 1

    arg = args.file
    if arg.endswith(".md"):
        arg = arg[:-3] + ".html"
    path = Path(arg)
    if not path.is_file():
        print(f"❌ 找不到檔案:{arg}", file=sys.stderr)
        return 1
    return 0 if _convert(path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
