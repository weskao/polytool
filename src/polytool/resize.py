"""resize-image — resize images (JPG/PNG/WebP) via ImageMagick."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ._utils import ensure_tool, log_green, log_red, log_yellow

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _resize(path: Path, width: int, height: int, force: bool) -> bool:
    size = f"{width}x{height}{'!' if force else ''}"
    ext = path.suffix.lower()
    output = path.with_name(f"{path.stem}_{width}x{height}{ext}")
    res = subprocess.run(["magick", str(path), "-resize", size, str(output)], capture_output=True)
    if res.returncode == 0:
        log_green("Resized:")
        log_yellow(f"{path} → {output}")
        return True
    log_red(f"Failed to resize: {path}")
    if res.stderr:
        print(res.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resize-image",
        description="Resize images (JPG/PNG/WebP) with optional recursive and force-aspect.",
    )
    parser.add_argument("-r", "--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("-f", "--force", action="store_true", help="Force aspect (use !)")
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("files", nargs="*", help="Specific files (default: all in current folder)")
    args = parser.parse_args(argv)

    if not ensure_tool("imagemagick", "magick"):
        return 1

    cwd = Path.cwd()
    targets: list[Path] = []
    if args.files:
        for name in args.files:
            if args.recursive:
                targets.extend(p for p in cwd.rglob(name) if p.is_file())
            else:
                p = cwd / name
                if p.is_file():
                    targets.append(p)
    else:
        if args.recursive:
            targets = [p for p in cwd.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
        else:
            targets = [p for p in cwd.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]

    if not targets:
        print("⚠️  No matching files.", file=sys.stderr)
        return 0

    for p in targets:
        _resize(p, args.width, args.height, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
