"""Tests for charcount input resolution."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from polytool import charcount


def _run(*argv: str) -> str:
    out = io.StringIO()
    with redirect_stdout(out):
        charcount.main(list(argv))
    return out.getvalue().strip()


class CharcountTests(unittest.TestCase):
    def test_positional_file_counts_contents_not_name(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "report.md"
            path.write_text("héllo\n世界", encoding="utf-8")
            self.assertEqual(_run(str(path)), "📝 Character count: 8")

    def test_positional_text_still_counts_text(self):
        self.assertEqual(_run("no-such-file.md"), "📝 Character count: 15")
        self.assertEqual(_run("Hello", "world"), "📝 Character count: 11")


if __name__ == "__main__":
    unittest.main()
