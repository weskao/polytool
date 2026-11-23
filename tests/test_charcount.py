"""Tests for charcount input resolution, warnings, limits and exit codes."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from polytool import charcount


def _run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = charcount.main(list(argv))
    return code, out.getvalue().strip(), err.getvalue()


class _TempDirMixin:
    def make_file(self, name: str, content: str) -> Path:
        if not isinstance(self, unittest.TestCase):
            raise TypeError("temp dir mixin requires unittest.TestCase")
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class FileInputTests(_TempDirMixin, unittest.TestCase):
    def test_positional_file_counts_contents_not_name(self):
        path = self.make_file("report.md", "héllo\n世界")
        self.assertEqual(_run(str(path)), (0, "📝 Character count: 8", ""))

    def test_positional_and_flag_give_same_result(self):
        path = self.make_file("report-plain.html", "<p>hi</p>")
        self.assertEqual(_run(str(path)), _run("-f", str(path)))

    def test_path_with_spaces(self):
        path = self.make_file("dir with space/my notes.txt", "hello")
        self.assertEqual(_run(str(path)), (0, "📝 Character count: 5", ""))
        self.assertEqual(_run("-f", str(path)), (0, "📝 Character count: 5", ""))

    def test_relative_path_resolves_against_cwd(self):
        path = self.make_file("notes.txt", "abc")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(path.parent)
        self.assertEqual(_run("notes.txt"), (0, "📝 Character count: 3", ""))
        self.assertEqual(_run("-f", "notes.txt"), (0, "📝 Character count: 3", ""))

    def test_multiple_positionals_are_text_even_if_first_is_a_file(self):
        path = self.make_file("a.txt", "x" * 100)
        code, out, _ = _run(str(path), "more")
        self.assertEqual(code, 0)
        self.assertEqual(out, f"📝 Character count: {len(str(path)) + 5}")

    def test_flag_missing_file_errors(self):
        code, out, err = _run("-f", "no-such-file.md")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("❌ File not found", err)


class MissingFileHintTests(unittest.TestCase):
    def test_path_like_missing_arg_warns_then_counts_text(self):
        for arg in ("no-such-file.md", "my notes.txt", "dir with space/x"):
            with self.subTest(arg=arg):
                code, out, err = _run(arg)
                self.assertEqual((code, out), (0, f"📝 Character count: {len(arg)}"))
                self.assertIn("⚠️  File not found", err)
                self.assertIn("use -f", err)

    def test_plain_text_has_no_warning(self):
        for argv in (
            ("Hello", "world"),
            ("Hello",),
            ("Hello world",),
            ("Hello world. Bye",),
        ):
            with self.subTest(argv=argv):
                code, out, err = _run(*argv)
                self.assertEqual(
                    (code, out, err),
                    (0, f"📝 Character count: {len(' '.join(argv))}", ""),
                )


class LimitAndEmptyTests(unittest.TestCase):
    def test_within_limit(self):
        self.assertEqual(
            _run("-l", "5", "Hello"),
            (0, "📝 Character count: 5 / 5\n✅ Within limit", ""),
        )

    def test_exceeds_limit(self):
        code, out, _ = _run("-l", "3", "Hello")
        self.assertEqual(code, 1)
        self.assertIn("Exceeded by 2 characters", out)

    def test_no_input_prints_help_and_fails(self):
        code, out, err = _run()
        self.assertEqual((code, out), (1, ""))
        self.assertIn("usage: charcount", err)


if __name__ == "__main__":
    unittest.main()
