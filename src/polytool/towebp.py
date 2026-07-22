"""towebp — convert PNG/JPG/JPEG to WebP via cwebp."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ._utils import ensure_tool, log_green, log_red, log_yellow

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg"}


def _convert(path: Path, quality: int) -> bool:
    output = path.with_suffix(".webp")
    res = subprocess.run(["cwebp", "-q", str(quality), str(path), "-o", str(output)], capture_output=True)
    if res.returncode == 0:
        path.unlink(missing_ok=True)
        log_green("Converted:")
        log_yellow(f"{path} → {output}")
        return True
    log_red(f"Failed to convert: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="towebp",
        description="Convert PNG/JPG/JPEG to WebP (recursive by default).",
    )
    parser.add_argument(
        "-c",
        "--current-only",
        action="store_true",
        help="Process only the current folder (default: recurse into subfolders)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=75,
        help="Compression quality (0-100, default: 75)",
    )
    args = parser.parse_args(argv)

    if not ensure_tool("webp", "cwebp"):
        return 1

    root = Path.cwd()
    if args.current_only:
        candidates = [p for p in root.iterdir() if p.suffix.lower() in SUPPORTED_EXTS and p.is_file()]
    else:
        candidates = [p for p in root.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS and p.is_file()]

    if not candidates:
        print("⚠️  No PNG/JPG/JPEG files found.", file=sys.stderr)
        return 0

    for p in candidates:
        _convert(p, args.quality)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
