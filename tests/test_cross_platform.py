"""Cross-platform tests for shared utility dispatch."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from unittest import mock

from polytool import _utils as u
from polytool import vcadd


class _PlatformMixin:
    def force_platform(self, *, macos=False, windows=False, linux=False):
        if not isinstance(self, unittest.TestCase):
            raise TypeError("platform mixin requires unittest.TestCase")
        for patcher in (
            mock.patch.object(u, "IS_MACOS", macos),
            mock.patch.object(u, "IS_WINDOWS", windows),
            mock.patch.object(u, "IS_LINUX", linux),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)


class ClipboardDispatchTests(_PlatformMixin, unittest.TestCase):
    def _record_pipe(self):
        calls = []

        def fake_pipe(cmd, data):
            calls.append((list(cmd), data))
            return True

        patcher = mock.patch.object(u, "_pipe_to", side_effect=fake_pipe)
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls

    def test_macos_uses_pbcopy(self):
        self.force_platform(macos=True)
        calls = self._record_pipe()
        self.assertTrue(u.copy_to_clipboard("héllo 你好"))
        self.assertEqual(calls[0], (["pbcopy"], "héllo 你好".encode()))

    def test_windows_prefers_win32_api(self):
        self.force_platform(windows=True)
        with mock.patch.object(u, "_windows_set_clipboard", return_value=True) as win:
            self.assertTrue(u.copy_to_clipboard("你好"))
        win.assert_called_once_with("你好")

    def test_linux_prefers_wayland(self):
        self.force_platform(linux=True)
        calls = self._record_pipe()
        with mock.patch.object(u, "have", side_effect=lambda cmd: cmd == "wl-copy"), mock.patch.dict(
            "os.environ", {"WAYLAND_DISPLAY": "wayland-0"}, clear=True
        ):
            self.assertTrue(u.copy_to_clipboard("text"))
        self.assertEqual(calls[0][0], ["wl-copy"])

    def test_linux_without_clipboard_tool_fails_cleanly(self):
        self.force_platform(linux=True)
        with mock.patch.object(u, "have", return_value=False), mock.patch.dict(
            "os.environ", {}, clear=True
        ):
            self.assertFalse(u.copy_to_clipboard("text"))


class EnsureToolTests(_PlatformMixin, unittest.TestCase):
    def test_present_tool_returns_true(self):
        with mock.patch.object(u, "have", return_value=True):
            self.assertTrue(u.ensure_tool("pandoc"))

    def test_linux_missing_tool_prints_hint(self):
        self.force_platform(linux=True)
        error = io.StringIO()
        with mock.patch.object(u, "have", return_value=False), redirect_stderr(error):
            self.assertFalse(u.ensure_tool("pandoc"))
        self.assertIn("apt install pandoc", error.getvalue())

    def test_windows_missing_tool_prints_hint(self):
        self.force_platform(windows=True)
        error = io.StringIO()
        with mock.patch.object(u, "have", return_value=False), redirect_stderr(error):
            self.assertFalse(u.ensure_tool("imagemagick", "magick"))
        self.assertIn("winget", error.getvalue())

    def test_macos_without_brew_fails_cleanly(self):
        self.force_platform(macos=True)
        error = io.StringIO()
        with mock.patch.object(u, "have", return_value=False), redirect_stderr(error):
            self.assertFalse(u.ensure_tool("pngquant"))
        self.assertIn("Homebrew", error.getvalue())


class VcaddPlatformTests(unittest.TestCase):
    def test_fails_cleanly_outside_macos(self):
        error = io.StringIO()
        with mock.patch.object(vcadd.sys, "platform", "win32"), redirect_stderr(error):
            self.assertEqual(vcadd.main(["測試"]), 1)
        self.assertIn("requires macOS", error.getvalue())

    def test_help_remains_available_outside_macos(self):
        with mock.patch.object(vcadd.sys, "platform", "win32"):
            self.assertEqual(vcadd.main(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
