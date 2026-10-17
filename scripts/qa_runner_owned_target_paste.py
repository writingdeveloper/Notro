#!/usr/bin/env python3
"""Own-window native Ctrl+V E2E on disposable GitHub Windows runner only.

Creates a temporary Notro PNG, an owned Tk Win32 foreground text window,
runs the actual PickerController.select -> Win32 clipboard CF_HDROP ->
SendInput Ctrl+V -> Tk event handler, and validates real file path delivery.
Also checks lost-target and newer-copy guards without issuing Enter.

This is NOT Discord's attachment UI and does not open, modify or send
anything to Discord. Never run on a user's real desktop/clipboard.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

if (os.environ.get("GITHUB_ACTIONS") != "true"
        or not os.environ.get("RUNNER_TEMP")):
    raise SystemExit("Refusing Win32 keyboard/clipboard QA outside a disposable runner")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tkinter as tk

import win32gui
from PIL import Image

from notro_app import clipboard_win as cb
from notro_app.picker import window

shell32 = ctypes.windll.shell32
shell32.DragQueryFileW.restype = wt.UINT
shell32.DragQueryFileW.argtypes = [wt.HANDLE, wt.UINT, wt.LPWSTR, wt.UINT]


def file_paths_from_clipboard() -> list[str]:
    if not cb._open_clipboard_retry():
        raise RuntimeError("Own runner clipboard unavailable")
    try:
        hdrop = cb.user32.GetClipboardData(cb.CF_HDROP)
        if not hdrop:
            return []
        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        paths = []
        for i in range(count):
            length = shell32.DragQueryFileW(hdrop, i, None, 0)
            buffer = ctypes.create_unicode_buffer(length+1)
            shell32.DragQueryFileW(hdrop, i, buffer, len(buffer))
            paths.append(buffer.value)
        return paths
    finally:
        cb.user32.CloseClipboard()


def text_from_clipboard() -> str:
    if not cb._open_clipboard_retry():
        raise RuntimeError("Own runner clipboard unavailable")
    try:
        handle = cb.user32.GetClipboardData(cb.CF_UNICODETEXT)
        if not handle:
            return ""
        address = cb.kernel32.GlobalLock(handle)
        if not address:
            raise RuntimeError("Cannot GlobalLock clipboard text")
        try:
            return ctypes.wstring_at(address)
        finally:
            cb.kernel32.GlobalUnlock(handle)
    finally:
        cb.user32.CloseClipboard()


def clear_clipboard() -> None:
    if cb._open_clipboard_retry():
        try:
            cb.user32.EmptyClipboard()
        finally:
            cb.user32.CloseClipboard()


class IsolatedLibrary:
    def __init__(self, path: str):
        self.path = path
        self.used: list[str] = []

    def resolve(self, item_id: str):
        if item_id == "owned-test-file":
            return {"id": item_id, "name": "QA asset", "type": "emoji",
                    "source_url": ""}
        return None

    def asset_path(self, item):
        return self.path

    def touch(self, item_id: str):
        self.used.append(item_id)


def main() -> int:
    outcome = {"runner_only": True, "owned_window": False,
               "foreground_file_ctrl_v": False, "lost_target_preserved": False,
               "newer_copy_preserved": False, "auto_send_called": False,
               "errors": [], "passed": False}
    root = None
    real_prepare = window.prepare_for_paste
    real_get_setting_flag = window.config.get_setting_flag
    real_send_enter = cb.send_enter
    try:
        with tempfile.TemporaryDirectory(prefix="notro-own-target-") as folder:
            original = Path(folder)/"한글_도형_QA.png"
            Image.new("RGB", (48, 48), (48, 152, 201)).save(original,format="PNG")
            library = IsolatedLibrary(str(original))
            events: list[list[str]] = []
            title = "Notro PRIVATE QA Own Win32 Paste Target"
            root = tk.Tk()
            root.title(title)
            root.geometry("480x160+100+100")
            caption = tk.Label(root, text="Isolated QA test only. NO Discord.")
            caption.pack(padx=6,pady=3)
            entry = tk.Entry(root,width=60)
            entry.pack(padx=6,pady=4)
            entry.insert(0,"NO MESSAGE WILL BE SENT")
            def on_paste(_event):
                events.append(file_paths_from_clipboard())
                return "break"
            entry.bind("<Control-v>", on_paste)
            root.attributes("-topmost",True)
            root.update_idletasks()
            root.lift()
            entry.focus_force()
            root.update()
            time.sleep(.08)

            hwnd = int(win32gui.FindWindow(None,title))
            if not hwnd:
                raise RuntimeError("Owned QA HWND not visible")
            outcome["owned_window"] = True
            picker = window.PickerController(library=library)
            picker.window = SimpleNamespace(hide=lambda: None)
            picker._remember_size = lambda: None
            picker.prev_hwnd = hwnd
            picker.on_notify = lambda _msg: None
            window.prepare_for_paste = lambda *args, **kwargs: (str(original),False)
            window.config.get_setting_flag = lambda name: False
            # Never issue Enter even if production guard is somehow bypassed.
            def reject_enter():
                outcome["auto_send_called"] = True
                raise RuntimeError("NO automatic Enter permitted in QA")
            cb.send_enter = reject_enter

            root.update()
            if not cb.focus_window(hwnd):
                raise RuntimeError("Hosted-runner owned Win32 window cannot get focus")
            entry.focus_force()
            root.update()
            if not cb.is_window_focused(hwnd):
                raise RuntimeError("Owned Win32 window not foreground")
            assert picker.select("owned-test-file") is True
            deadline = time.monotonic()+2.5
            while not events and time.monotonic()<deadline:
                root.update()
                time.sleep(.025)
            outcome["foreground_file_ctrl_v"] = (
                events == [[str(original)]]
                and library.used == ["owned-test-file"]
                and cb.clipboard_has_files()
            )
            if not outcome["foreground_file_ctrl_v"]:
                raise RuntimeError(
                    "Real Ctrl+V did not reach own Tk event with file path"
                    + f": {events!r}"
                )

            # A closed/invalid target must never alter the current copy.
            assert cb.set_clipboard_text("User copy before lost target")
            picker.prev_hwnd=0
            assert picker.select("owned-test-file") is False
            outcome["lost_target_preserved"] = (
                text_from_clipboard()=="User copy before lost target"
                and events == [[str(original)]]
            )

            # Simulate a user copying something else WHILE the selected
            # media is being processed, after the initial sequence capture.
            picker.prev_hwnd=hwnd
            def newer_copy(*_a,**_kw):
                assert cb.set_clipboard_text("User newer copy while preparing")
                return str(original),False
            window.prepare_for_paste=newer_copy
            assert picker.select("owned-test-file") is False
            outcome["newer_copy_preserved"] = (
                text_from_clipboard()=="User newer copy while preparing"
                and events == [[str(original)]]
                and library.used == ["owned-test-file"]
            )
            outcome["passed"] = bool(
                outcome["owned_window"]
                and outcome["foreground_file_ctrl_v"]
                and outcome["lost_target_preserved"]
                and outcome["newer_copy_preserved"]
                and not outcome["auto_send_called"]
            )
    except Exception as exc:
        outcome["errors"].append(type(exc).__name__+": "+str(exc)[:300])
    finally:
        window.prepare_for_paste = real_prepare
        window.config.get_setting_flag = real_get_setting_flag
        cb.send_enter = real_send_enter
        clear_clipboard()
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
    print("NOTRO_OWN_WINDOW_PASTE_QA="+json.dumps(outcome,ensure_ascii=True),
          flush=True)
    return 0 if outcome["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
