"""imgmin — visually-lossless image compression toolkit.

Faithful port of the zsh ``imgmin`` / ``imgmin_dir`` family. Originals are never
modified — outputs go into a sibling ``imgmin-out/`` directory.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

from ._utils import ensure_tool, have, log_red

SUPPORTED_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif",
    ".heic", ".heif", ".tiff", ".tif", ".bmp", ".avif",
}

HELP = """imgmin — image compression toolkit (non-destructive)

USAGE
  imgmin <file> [1|2]           Compress a single file → <dir>/imgmin-out/<basename>
  imgmin <file> --to-png        Convert to PNG then compress
  imgmin <dir>  [1|2]           Compress every image in <dir> (top level by default)
  imgmin <dir>  -r              Recurse into sub-folders
  imgmin <dir>  --to-png        Force every output to PNG
  imgmin .                      Shortcut for the current directory
  imgmin -h | --help            Show this help

MODE
  1            Convert ALL formats to .jpeg at quality 70 (TinyPNG-style).
  2 (default)  Format-aware "visually lossless" compression.

OUTPUT POLICY
  • Originals are never modified.
  • Results go into a sibling ``imgmin-out/`` directory.
  • Re-running overwrites previous outputs in imgmin-out/ but not originals.
"""


# ── helpers ────────────────────────────────────────────────────────────────

def _file_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def _human(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    return f"{n / (1024 * 1024):.1f}MB"


def _resolve_sharp() -> str | None:
    """Find sharp-cli binary, auto-installing via npm on first use."""
    s = shutil.which("sharp")
    if s:
        return s
    nvm = Path.home() / ".nvm/versions/node"
    if nvm.is_dir():
        candidates = sorted(nvm.glob("*/bin/sharp"), key=os.path.getmtime, reverse=True)
        if candidates:
            return str(candidates[0])
    if not shutil.which("npm"):
        log_red("❌ npm not found; sharp-cli requires Node.js — please install Node.js first")
        return None
    print("⚠️  sharp-cli not detected, attempting to install via npm...", file=sys.stderr)
    res = subprocess.run(["npm", "install", "-g", "sharp-cli"])
    if res.returncode != 0:
        return None
    return shutil.which("sharp") or (
        str(sorted((Path.home() / ".nvm/versions/node").glob("*/bin/sharp"))[-1])
        if (Path.home() / ".nvm/versions/node").is_dir()
        else None
    )


def _report(buffer: list, src: Path, before: int, dst: Path, after: int) -> None:
    if before == 0 or after == 0:
        return
    pct = (before - after) * 100 // before
    if pct > 0:
        color = "\033[32m"  # green
    elif pct < 0:
        color = "\033[38;5;208m"  # orange
    else:
        color = "\033[2m"  # dim

    label = str(src)
    if src.suffix.lower() != dst.suffix.lower():
        label = f"{src} → {dst.name}"

    if buffer is not None:
        buffer.append((color, pct, _human(before), _human(after), label))
    else:
        reset = "\033[0m"
        print(f"  {color}{pct:3d}%{reset}   {_human(before):>8} → {_human(after):<8}   {label}")


def _print_table(rows: list) -> None:
    if not rows:
        return
    max_pct = max(5, max(len(f"{r[1]}%") for r in rows))
    max_bef = max(6, max(len(r[2]) for r in rows))
    max_aft = max(5, max(len(r[3]) for r in rows))
    max_file = max(4, max(len(r[4]) for r in rows))

    def div(c):
        return f"{c}" * (max_pct + 2) + "┬" + f"{c}" * (max_bef + 2) + "┬" + f"{c}" * (max_aft + 2) + "┬" + f"{c}" * (max_file + 2)

    bold, reset = "\033[1m", "\033[0m"
    top = "  ┌" + "─" * (max_pct + 2) + "┬" + "─" * (max_bef + 2) + "┬" + "─" * (max_aft + 2) + "┬" + "─" * (max_file + 2) + "┐"
    mid = "  ├" + "─" * (max_pct + 2) + "┼" + "─" * (max_bef + 2) + "┼" + "─" * (max_aft + 2) + "┼" + "─" * (max_file + 2) + "┤"
    bot = "  └" + "─" * (max_pct + 2) + "┴" + "─" * (max_bef + 2) + "┴" + "─" * (max_aft + 2) + "┴" + "─" * (max_file + 2) + "┘"

    print(top)
    print(f"  │ {bold}{'Saved':>{max_pct}}{reset} │ {bold}{'Before':>{max_bef}}{reset} │ {bold}{'After':>{max_aft}}{reset} │ {bold}{'File':<{max_file}}{reset} │")
    print(mid)
    for color, pct, before, after, label in rows:
        print(f"  │ {color}{f'{pct}%':>{max_pct}}{reset} │ {before:>{max_bef}} │ {after:>{max_aft}} │ {label:<{max_file}} │")
    print(bot)


# ── compressors per format ────────────────────────────────────────────────

def _pngquant_compress(target: Path) -> bool:
    if not ensure_tool("pngquant") or not ensure_tool("oxipng"):
        return False
    tmp = target.with_name(target.stem + ".__pq.tmp.png")
    res = subprocess.run(
        ["pngquant", "--quality=80-95", "--speed", "1", "--strip", "--force",
         "--output", str(tmp), str(target)],
        capture_output=True,
    )
    if res.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 0 and tmp.stat().st_size < target.stat().st_size:
        tmp.replace(target)
    else:
        tmp.unlink(missing_ok=True)
    subprocess.run(["oxipng", "-o", "max", "--strip", "safe", "--quiet", str(target)], capture_output=True)
    return True


def _compress_jpeg(file: Path, target: Path, max_q: int = 85) -> bool:
    if not ensure_tool("jpegoptim"):
        return False
    shutil.copy2(file, target)
    subprocess.run(
        ["jpegoptim", f"--max={max_q}", "--strip-all", "--all-progressive", "--quiet", str(target)],
        capture_output=True,
    )
    return True


def _compress_webp(file: Path, target: Path) -> bool:
    if not ensure_tool("webp", "cwebp"):
        return False
    tmp = target.with_name(target.name + ".tmp.webp")
    res = subprocess.run(
        ["cwebp", "-q", "82", "-m", "6", "-mt", "-af", "-sharp_yuv", "-pass", "10", "-quiet",
         str(file), "-o", str(tmp)],
        capture_output=True,
    )
    sz_orig = file.stat().st_size
    sz_new = tmp.stat().st_size if tmp.is_file() else 0
    if res.returncode == 0 and sz_new > 0 and sz_new < sz_orig:
        tmp.replace(target)
    else:
        tmp.unlink(missing_ok=True)
        shutil.copy2(file, target)
    return True


def _compress_svg(file: Path, target: Path) -> bool:
    if not ensure_tool("svgo"):
        return False
    subprocess.run(["svgo", "--multipass", "--quiet", str(file), "-o", str(target)], capture_output=True)
    return True


def _compress_gif(file: Path, target: Path) -> bool:
    if not ensure_tool("gifsicle"):
        return False
    shutil.copy2(file, target)
    subprocess.run(["gifsicle", "-O3", "--lossy=30", "--batch", str(target)], capture_output=True)
    return True


def _compress_heic(file: Path, target: Path) -> bool:
    if not have("sips"):
        # Re-encoding HEIC→HEIC needs macOS 'sips'; there is no portable
        # same-format encoder. Point users at the cross-platform --to-png path.
        log_red(
            "imgmin: HEIC re-compression requires macOS 'sips'. "
            "On Windows/Linux, convert instead with:  imgmin <file> --to-png"
        )
        return False
    tmp = target.with_name(target.name + ".tmp.heic")
    res = subprocess.run(
        ["sips", "-s", "format", "heic", "-s", "formatOptions", "70", str(file), "--out", str(tmp)],
        capture_output=True,
    )
    if res.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 0 and tmp.stat().st_size < file.stat().st_size:
        tmp.replace(target)
    else:
        tmp.unlink(missing_ok=True)
        shutil.copy2(file, target)
    return True


def _sharp_to_png(file: Path, target: Path) -> bool:
    sharp = _resolve_sharp()
    if not sharp:
        return False
    with tempfile.TemporaryDirectory(prefix="imgmin-sharp.") as tmp:
        res = subprocess.run([sharp, "-i", str(file), "-o", tmp, "-f", "png"], capture_output=True)
        if res.returncode != 0:
            log_red(f"imgmin: sharp conversion failed for {file}")
            return False
        produced = sorted(Path(tmp).glob("*.png"))
        if not produced or produced[0].stat().st_size == 0:
            log_red(f"imgmin: sharp produced no output for {file}")
            return False
        shutil.move(produced[0], target)
    return _pngquant_compress(target)


def _to_jpeg(file: Path, target: Path, ext: str) -> bool:
    if not ensure_tool("jpegoptim"):
        return False
    if ext in ("jpg", "jpeg"):
        shutil.copy2(file, target)
    elif ext == "heic":
        if have("sips"):
            res = subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70",
                 str(file), "--out", str(target)],
                capture_output=True,
            )
            if res.returncode != 0:
                log_red(f"imgmin: sips HEIC→JPEG failed for {file}")
                return False
        else:
            # Non-macOS: route through sharp (works if libvips has libheif).
            sharp = _resolve_sharp()
            if not sharp:
                log_red("imgmin: HEIC→JPEG needs macOS 'sips' or sharp-cli with libheif support")
                return False
            with tempfile.TemporaryDirectory(prefix="imgmin-sharp.") as tmp:
                res = subprocess.run([sharp, "-i", str(file), "-o", tmp, "-f", "jpeg"], capture_output=True)
                produced = sorted(Path(tmp).glob("*.jpeg")) + sorted(Path(tmp).glob("*.jpg"))
                if res.returncode == 0 and produced and produced[0].stat().st_size > 0:
                    shutil.move(produced[0], target)
                else:
                    log_red(f"imgmin: sharp HEIC→JPEG failed for {file} (libheif support required)")
                    return False
    elif ext in ("png", "webp", "heif", "tiff", "tif", "bmp", "avif", "raw", "gif"):
        sharp = _resolve_sharp()
        if sharp:
            with tempfile.TemporaryDirectory(prefix="imgmin-sharp.") as tmp:
                res = subprocess.run([sharp, "-i", str(file), "-o", tmp, "-f", "jpeg"], capture_output=True)
                produced = sorted(Path(tmp).glob("*.jpeg")) + sorted(Path(tmp).glob("*.jpg"))
                if res.returncode == 0 and produced and produced[0].stat().st_size > 0:
                    shutil.move(produced[0], target)
                elif have("sips"):
                    subprocess.run(
                        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70",
                         str(file), "--out", str(target)],
                        capture_output=True,
                    )
                else:
                    log_red(f"imgmin: failed to convert {file} to JPEG")
                    return False
        elif have("sips"):
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70",
                 str(file), "--out", str(target)],
                capture_output=True,
            )
        else:
            return False
    elif ext == "svg":
        log_red("imgmin: mode 1 skips SVG (vector format)")
        return False
    else:
        log_red(f"imgmin: unsupported format .{ext} ({file})")
        return False
    subprocess.run(
        ["jpegoptim", "--max=70", "--strip-all", "--all-progressive", "--quiet", str(target)],
        capture_output=True,
    )
    return True


# ── single-file driver ────────────────────────────────────────────────────

def _compress_one(
    file: Path,
    target: Path,
    ext: str,
    mode: str,
    convert_to_png: bool,
) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)

    if convert_to_png:
        if ext == "png":
            shutil.copy2(file, target)
        elif ext == "heic":
            if have("sips"):
                res = subprocess.run(["sips", "-s", "format", "png", str(file), "--out", str(target)], capture_output=True)
                if res.returncode != 0:
                    log_red(f"imgmin: sips HEIC→PNG failed for {file}")
                    return False
            else:
                # Non-macOS: route through sharp (works if libvips has libheif).
                if not _sharp_to_png(file, target):
                    log_red(f"imgmin: HEIC→PNG needs macOS 'sips' or sharp-cli with libheif support ({file})")
                    return False
                return True  # _sharp_to_png already ran pngquant
        else:
            if not _sharp_to_png(file, target):
                return False
            return True
        return _pngquant_compress(target)

    if mode == "1":
        return _to_jpeg(file, target, ext)

    # Mode 2 (format-aware)
    if ext == "png":
        shutil.copy2(file, target)
        return _pngquant_compress(target)
    if ext in ("jpg", "jpeg"):
        return _compress_jpeg(file, target, max_q=85)
    if ext == "webp":
        return _compress_webp(file, target)
    if ext == "svg":
        return _compress_svg(file, target)
    if ext == "gif":
        return _compress_gif(file, target)
    if ext == "heic":
        return _compress_heic(file, target)
    if ext in ("heif", "tiff", "tif", "bmp", "avif", "raw"):
        return _sharp_to_png(file, target)
    log_red(f"imgmin: unsupported format .{ext} ({file})")
    return False


# ── batch driver ──────────────────────────────────────────────────────────

def _collect_files(root: Path, recursive: bool, out_root: Path) -> list[Path]:
    iterator: Iterable[Path]
    iterator = root.rglob("*") if recursive else root.iterdir()
    out: list[Path] = []
    for p in iterator:
        if not p.is_file():
            continue
        try:
            if out_root in p.parents:
                continue
        except ValueError:
            pass
        if p.suffix.lower() in SUPPORTED_EXTS:
            out.append(p)
    return out


def _output_ext(in_ext: str, mode: str, convert_to_png: bool) -> str:
    if mode == "1":
        return "svg" if in_ext == "svg" else "jpeg"
    if convert_to_png:
        return "png"
    if in_ext in ("heif", "tiff", "tif", "bmp", "avif", "raw"):
        return "png"
    return in_ext


def _pick_mode() -> str | None:
    print("[1] Convert to JPEG  [2] Format-aware compression", file=sys.stderr)
    print("Please enter your choice (1-2): ", end="", flush=True, file=sys.stderr)
    try:
        ch = input().strip()
    except EOFError:
        return None
    return ch if ch in ("1", "2") else None


def _run_dir(target_dir: Path, recursive: bool, mode: str | None, convert_to_png: bool) -> int:
    if not target_dir.is_dir():
        log_red(f"imgmin_dir: directory not found: {target_dir}")
        return 1

    if not mode:
        mode = "2" if convert_to_png else _pick_mode()
        if not mode:
            return 1

    out_root = target_dir / "imgmin-out"
    out_root.mkdir(parents=True, exist_ok=True)

    files = _collect_files(target_dir, recursive, out_root)
    if not files:
        print(f"imgmin_dir: no images found in {target_dir}", file=sys.stderr)
        try:
            out_root.rmdir()
        except OSError:
            pass
        return 0

    rows: list = []
    total_before = total_after = ok = fail = 0
    for i, f in enumerate(files, 1):
        in_ext = f.suffix.lower().lstrip(".")
        out_ext = _output_ext(in_ext, mode, convert_to_png)
        rel = f.relative_to(target_dir)
        out_path = out_root / rel.with_suffix("." + out_ext)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        before = _file_size(f)
        if _compress_one(f, out_path, in_ext, mode, convert_to_png):
            after = _file_size(out_path)
            _report(rows, f, before, out_path, after)
            total_before += before
            total_after += after
            ok += 1
        else:
            fail += 1

    _print_table(rows)
    saved = total_before - total_after
    pct = (saved * 100 // total_before) if total_before else 0
    if ok:
        print(
            f"\n\033[1m✓ {ok} images   {_human(total_before)} → {_human(total_after)}   "
            f"saved {_human(saved)} ({pct}%)\033[0m"
        )
    if fail:
        print(f"\033[33m⚠ {fail} skipped (error)\033[0m")
    print(f"Output folder: {out_root}/")
    if ok == 0:
        try:
            out_root.rmdir()
        except OSError:
            pass
    return 0


# ── entry point ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(HELP)
        return 0

    parser = argparse.ArgumentParser(prog="imgmin", add_help=False)
    parser.add_argument("target")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--to-png", action="store_true")
    parser.add_argument("mode_or_extra", nargs="*")
    args = parser.parse_args(argv)

    mode: str | None = None
    for x in args.mode_or_extra:
        if x in ("1", "2"):
            mode = x

    target = Path(args.target)
    if target.is_dir():
        return _run_dir(target, args.recursive, mode, args.to_png)

    if not target.is_file():
        log_red(f"imgmin: file not found: {target}")
        return 1

    if not mode:
        mode = "2" if args.to_png else _pick_mode()
        if not mode:
            return 1

    in_ext = target.suffix.lower().lstrip(".")
    out_ext = _output_ext(in_ext, mode, args.to_png)
    out_dir = target.parent / "imgmin-out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (target.stem + "." + out_ext)

    before = _file_size(target)
    if not _compress_one(target, out_path, in_ext, mode, args.to_png):
        return 1
    after = _file_size(out_path)
    _report(None, target, before, out_path, after)
    print(f"Output folder: {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
