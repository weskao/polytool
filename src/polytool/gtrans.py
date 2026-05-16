"""gtrans — Google Translate CLI with clipboard support and chunked translation.

Faithful port of the zsh ``gtrans`` / ``ge`` function.
Default: English (en) → Traditional Chinese (zh-TW).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ._utils import copy_to_clipboard

CHAR_LIMIT = 4500
API_URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t"


def _translate_chunk(text: str, sl: str, tl: str) -> str:
    """POST a single chunk to the unofficial Google Translate endpoint."""
    body = urllib.parse.urlencode({"q": text}).encode("utf-8")
    url = API_URL.format(sl=sl, tl=tl)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    return "".join(item[0] for item in data[0] if item and item[0])


def _split_chunks(text: str, limit: int = CHAR_LIMIT) -> list[str]:
    """Split text into chunks ≤ limit, preferring line boundaries."""
    chunks: list[str] = []
    buf = ""
    for line in text.splitlines(keepends=True):
        if len(buf) + len(line) > limit:
            if buf:
                chunks.append(buf)
                buf = ""
            if len(line) > limit:
                for i in range(0, len(line), limit):
                    chunks.append(line[i : i + limit])
                continue
        buf += line
    if buf:
        chunks.append(buf)
    return chunks


def _translate(text: str, sl: str, tl: str) -> str:
    if len(text) <= CHAR_LIMIT:
        return _translate_chunk(text, sl, tl)

    chunks = _split_chunks(text)
    total = len(chunks)
    print(
        f"✂️  Splitting into {total} chunks ({len(text)} characters total)...",
        file=sys.stderr,
    )
    print("─────────────────────────────────────────", file=sys.stderr)
    out: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        print(
            f"🔄 Translating chunk {i} / {total} ({len(chunk)} chars)...",
            end="",
            file=sys.stderr,
            flush=True,
        )
        try:
            out.append(_translate_chunk(chunk, sl, tl))
        except Exception as exc:  # network / parse failure on this chunk
            print("", file=sys.stderr)
            print(f"❌ Failed on chunk {i}: {exc}", file=sys.stderr)
            sys.exit(1)
        print(" ✅", file=sys.stderr)
        if i < total:
            time.sleep(0.5)
    return "".join(out)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gtrans",
        description="Google Translate CLI (default: auto → ZH-TW). Result is copied to clipboard.",
    )
    p.add_argument("-e", action="store_true", help="Translate to English (auto → en)")
    p.add_argument("-s", "--source", default="en", help="Source language code (default: en)")
    p.add_argument("-t", "--target", default="zh-TW", help="Target language code (default: zh-TW)")
    p.add_argument("-f", "--file", help="Read text from file")
    p.add_argument(
        "-w", "--write-back", action="store_true", help="Write translation back to the input file (requires -f)"
    )
    p.add_argument("text", nargs=argparse.REMAINDER, help="Text to translate")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Strip a single leading "--" if present (argparse REMAINDER includes it otherwise).
    if "--" in argv:
        argv.remove("--")

    parser = _build_parser()
    args = parser.parse_args(argv)

    sl = args.source
    tl = args.target
    if args.e:
        sl, tl = "auto", "en"

    if args.write_back and not args.file:
        print("❌ -w requires -f <file> (cannot write back without an input file)", file=sys.stderr)
        return 1

    text: str
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / args.file
        if not path.is_file():
            print(f"❌ File not found: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
        if not text:
            print(f"❌ File is empty: {path}", file=sys.stderr)
            return 1
        print(f"📄 Translating file: {path}", file=sys.stderr)
        print("─────────────────────────────────────────", file=sys.stderr)
    else:
        # argparse REMAINDER preserves order; strip the literal "-e" if it leaked
        # through positionally on systems where flag parsing stops at the first
        # non-flag (the zsh wrapper also tolerates flag-after-positional).
        positional = [a for a in args.text if not a.startswith("-")]
        text = " ".join(positional)

    if not text:
        parser.print_help(sys.stderr)
        return 1

    print(f"📝 Character count: {len(text)} [{sl} → {tl}]", file=sys.stderr)
    if len(text) > CHAR_LIMIT:
        print("⚠️  Content exceeds limit, will translate in chunks...", file=sys.stderr)
        print("─────────────────────────────────────────", file=sys.stderr)

    try:
        result = _translate(text, sl, tl)
    except Exception as exc:
        print(f"❌ Translation failed: {exc}", file=sys.stderr)
        return 1

    if not result:
        print("❌ Translation returned empty result.", file=sys.stderr)
        return 1

    if args.write_back and args.file:
        path = Path(args.file).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / args.file
        path.write_text(result, encoding="utf-8")
        print(f"💾 Wrote translation back to: {path}", file=sys.stderr)

    print(result)
    if copy_to_clipboard(result):
        print("\n✅ Copied to clipboard", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
