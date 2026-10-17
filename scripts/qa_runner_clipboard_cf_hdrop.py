#!/usr/bin/env python3
"""Real Win32 clipboard contract check on a disposable GitHub Windows runner.

Writes ONLY a generated test file/text to that runner's clipboard. Checks
CF_HDROP, Unicode, marker, and stale-sequence protection via native Win32
APIs. Never runs on a user's interactive/main PC; never sends key input or
touches Discord. No claim of a real app/Discord paste is made.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import tempfile
from pathlib import Path

if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("RUNNER_TEMP"):
    raise SystemExit("Refusing to touch clipboard outside an isolated GitHub QA runner.")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import clipboard_win as cb

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

shell32.DragQueryFileW.restype = wt.UINT
shell32.DragQueryFileW.argtypes = [wt.HANDLE, wt.UINT, wt.LPWSTR, wt.UINT]
user32.OpenClipboard.restype = wt.BOOL
user32.OpenClipboard.argtypes = [wt.HWND]
user32.CloseClipboard.restype = wt.BOOL
user32.GetClipboardData.restype = wt.HANDLE
user32.GetClipboardData.argtypes = [wt.UINT]


def inspect_native_clipboard() -> dict:
    if not cb._open_clipboard_retry():
        raise RuntimeError("Cannot open runner clipboard for readback")
    try:
        if user32.IsClipboardFormatAvailable(cb.CF_HDROP):
            hdrop = user32.GetClipboardData(cb.CF_HDROP)
            if not hdrop:
                raise RuntimeError("CF_HDROP available but missing data")
            count = int(shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0))
            paths = []
            for index in range(count):
                n = int(shell32.DragQueryFileW(hdrop, index, None, 0))
                buffer = ctypes.create_unicode_buffer(n + 1)
                shell32.DragQueryFileW(hdrop, index, buffer, len(buffer))
                paths.append(buffer.value)
            return {"format": "files", "paths": paths}

        if user32.IsClipboardFormatAvailable(cb.CF_UNICODETEXT):
            handle = user32.GetClipboardData(cb.CF_UNICODETEXT)
            address = kernel32.GlobalLock(handle)
            if not address:
                raise RuntimeError("Cannot lock copied Unicode text")
            try:
                return {"format": "text", "text": ctypes.wstring_at(address)}
            finally:
                kernel32.GlobalUnlock(handle)
        return {"format": "empty"}
    finally:
        user32.CloseClipboard()


def clear_runner_clipboard() -> None:
    if cb._open_clipboard_retry():
        try:
            user32.EmptyClipboard()
        finally:
            user32.CloseClipboard()


def main() -> int:
    result = {"runner_only": True, "filesystem_unicode": False,
              "unicode_text": False, "marker": False, "stale_guard": False,
              "passed": False, "errors": []}
    try:
        with tempfile.TemporaryDirectory(prefix="notro-cfhdrop-qa-") as temp:
            filename = Path(temp) / "한글 Notro 테스트 이미지.png"
            filename.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"qa")
            assert cb.set_clipboard_file(str(filename)) is True
            stored = inspect_native_clipboard()
            assert stored == {"format": "files", "paths": [str(filename)]}, stored
            assert cb.clipboard_has_files()
            result["filesystem_unicode"] = True

            text = "Notro QA — 한글 β, no Discord"
            assert cb.set_clipboard_text(text)
            stored = inspect_native_clipboard()
            assert stored == {"format": "text", "text": text}, stored
            result["unicode_text"] = True
            assert cb.clipboard_has_marker()
            result["marker"] = True

            # Race check: preserve newer user copy instead of replacing it.
            before = cb.get_sequence_number()
            updated_text = "Notro QA newer clipboard value"
            assert cb.set_clipboard_text(updated_text)
            after = cb.get_sequence_number()
            if before and after and before != after:
                assert cb.set_clipboard_file(str(filename), guard_seq=before) is None
                assert inspect_native_clipboard() == {
                    "format": "text", "text": updated_text,
                }
                result["stale_guard"] = True
            else:
                result["stale_guard"] = "not_observable_in_runner_session"
            result["passed"] = (
                result["filesystem_unicode"] and result["unicode_text"]
                and result["marker"] and result["stale_guard"] is True
            )
    except Exception as exc:
        result["errors"].append(type(exc).__name__ + ": " + str(exc)[:300])
    finally:
        # Disposable runner ONLY; synthetic clipboard data must not remain.
        clear_runner_clipboard()
    print("NOTRO_NATIVE_CLIPBOARD_QA="+json.dumps(result,ensure_ascii=True),
          flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
