#!/usr/bin/env python3
"""Real Windows file-dialog E2E for Notro's own isolated WebView2 test window.

Covers Unicode ZIP export/import, JSON settings export/restore, cancel
flows, and two malformed files rejected via real native Open dialogs. Dialog automation touches ONLY the
#32770 window of this exact Python process, never Discord, real clipboard,
registry, settings or personal Notro libraries.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import fetch, settings_backup
from notro_app.library import Library
from notro_app.picker.window import PickerApi

DIALOG_TIMEOUT = 16
BRIDGE_TIMEOUT = 20


def find_owned_dialog() -> int | None:
    """Exactly process-owned, visible common dialog; never inspect other apps."""
    import win32gui
    import win32process

    own = []

    def callback(hwnd, _):
        if (
            win32process.GetWindowThreadProcessId(hwnd)[1] == os.getpid()
            and win32gui.IsWindowVisible(hwnd)
            and win32gui.GetClassName(hwnd) == "#32770"
        ):
            own.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return own[0] if len(own) == 1 else None


def act_on_dialog(action: str, path: str | None, result: dict) -> None:
    """Drive Win32 file dialog without changing keyboard focus globally."""
    import win32con
    import win32gui
    from pywinauto import Desktop

    deadline = time.monotonic() + DIALOG_TIMEOUT
    while time.monotonic() < deadline:
        hwnd = find_owned_dialog()
        if hwnd is not None:
            result["seen"] = True
            dlg = Desktop(backend="win32").window(handle=hwnd)
            try:
                if action == "cancel":
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    result["action"] = "cancelled"
                    return
                assert path, "path required for file dialog accept"
                edits = dlg.descendants(class_name="Edit")
                # Native Windows dialogs may expose a second Edit field for
                # search/address; the filename Edit is the one with the
                # ordinary FileNameEdit / COMDLG32 edit class and at the
                # beginning of the standard dialog content hierarchy.
                if not edits:
                    raise RuntimeError("no native filename edit control")
                filename_edits = [e for e in edits if e.window_text().startswith(
                    ("notro-pack", "한글 파일", "테스트", "*.zip"))]
                file_edit = filename_edits[0] if filename_edits else edits[0]
                result["edits"] = [(e.window_text()[:35],e.control_id())
                                    for e in edits[:5]]
                file_edit.set_edit_text(path)
                buttons = dlg.descendants(class_name="Button")
                matches = [
                    button for button in buttons
                    if button.window_text().casefold().startswith(
                        ("save", "open", "저장", "열기")
                    )
                ]
                if len(matches) != 1:
                    raise RuntimeError(
                        "expected one Save/Open button, got " + repr(
                            [b.window_text() for b in buttons][:14]
                        )
                    )
                matches[0].click()
                result["action"] = "confirmed"
                return
            except Exception as exc:
                result["error"] = repr(exc)[:300]
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return
        time.sleep(0.15)
    result["error"] = "no own native file dialog within timeout"


def main() -> int:
    import webview

    with tempfile.TemporaryDirectory(prefix="notro-real-dialog-") as temp:
        root = Path(temp)
        source = root / "테스트 이미지.png"
        Image.new("RGBA", (20, 20), (50, 125, 200, 255)).save(source)
        original_library = Library(str(root / "original"))
        fetch.register_from_file(
            original_library, str(source), "emoji", name="테스트 이미지"
        )
        original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        dest_pack = root / "한글 파일 이름 테스트.zip"
        dest_preferences = root / "한글 환경설정 백업.json"
        corrupt_zip = root / "손상된 미디어팩.zip"
        corrupt_zip.write_bytes(b"PK" + b"not actually a ZIP")
        corrupt_preferences = root / "손상된 환경설정.json"
        corrupt_preferences.write_text(json.dumps({
            "format": "notro-settings", "version": 1,
            "settings": {"lang": "ko"},
            "watched_folders": [
                {"path": str(root), "default_type": ["gif"]}
            ],
        }), encoding="utf-8")

        # Synthetic settings only: the QA process must NOT read/write real
        # HKCU settings or the user's watched-folder paths.
        settings_backup._settings_snapshot = lambda: {
            "lang": "ko", "hotkey": "ctrl+shift+e",
            "limit_mb": 20, "paste_px_emoji": 48,
            "auto_update": 1, "auto_send": True,
            "auto_capture_save": True,
        }
        captured_settings = {}
        settings_backup.config.set_setting_int = (
            lambda k, v: captured_settings.__setitem__(k, v))
        settings_backup.config.set_setting_str = (
            lambda k, v: captured_settings.__setitem__(k, v))

        api = PickerApi(library=original_library)
        win = webview.create_window(
            "Notro QA native file dialog isolated",
            html="<html><body>Notro native dialog QA</body></html>",
            js_api=api, width=470, height=260, on_top=False,
        )
        api._ctrl = SimpleNamespace(window=win)
        final = {"stages": {}, "source_preserved": False,
                 "imported": False, "profile_applied": False,
                 "profile_bytes": 0, "errors": []}

        def run_stage(stage: str, api_method: str,
                      action: str, file_path: str | None):
            result = {"seen": False, "action": None}
            watcher = threading.Thread(
                target=act_on_dialog, args=(action, file_path, result), daemon=True
            )
            watcher.start()
            # JS calls the real Python bridge. No mocked file-dialog output.
            js = (
                "document.body.textContent='pending';"
                f"window.pywebview.api.{api_method}()"
                ".then(r=>document.body.textContent=JSON.stringify(r))"
                ".catch(e=>document.body.textContent=JSON.stringify({error:String(e)}))"
            )
            win.evaluate_js(js)
            answer = None
            deadline = time.monotonic() + BRIDGE_TIMEOUT
            while time.monotonic() < deadline:
                value = win.evaluate_js("document.body.textContent").strip()
                if value.startswith("{"):
                    answer = json.loads(value)
                    break
                time.sleep(0.15)
            watcher.join(timeout=1)
            if watcher.is_alive():
                result["error"] = "dialog watcher still running"
            result["reply"] = answer
            final["stages"][stage] = result
            return answer

        def execute():
            try:
                for _ in range(40):
                    if win.evaluate_js(
                        "Boolean(window.pywebview && window.pywebview.api)"
                    ):
                        break
                    time.sleep(0.15)

                cancel_export = run_stage("save_cancel", "export_pack", "cancel", None)
                assert cancel_export == {"ok": False, "error": "cancelled"}, cancel_export
                assert not dest_pack.exists()

                exported = run_stage(
                    "save_unicode", "export_pack", "confirm", str(dest_pack)
                )
                assert exported == {"ok": True, "count": 1}, exported
                assert dest_pack.is_file()
                final["pack_bytes"] = dest_pack.stat().st_size

                target_library = Library(str(root / "imported"))
                api._library = target_library
                cancel_import = run_stage("open_cancel", "import_pack", "cancel", None)
                assert cancel_import == {"ok": False, "error": "cancelled"}, cancel_import
                assert target_library.items() == []

                imported = run_stage(
                    "open_unicode", "import_pack", "confirm", str(dest_pack)
                )
                assert imported == {
                    "ok": True, "added": 1, "duplicate": 0, "failed": 0
                }, imported
                final["imported"] = (
                    len(target_library.items()) == 1
                    and target_library.items()[0]["name"] == "테스트 이미지"
                )
                final["source_preserved"] = (
                    hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
                )
                # A user choosing a malformed ZIP in the *real Windows Open
                # dialog* must receive a stable error and must not mutate
                # the existing imported library or crash the WebView bridge.
                before_items = len(target_library.items())
                corrupted_pack_reply = run_stage(
                    "open_corrupt_zip", "import_pack", "confirm",
                    str(corrupt_zip),
                )
                assert corrupted_pack_reply == {
                    "ok": False, "error": "pack",
                }, corrupted_pack_reply
                assert len(target_library.items()) == before_items

                cancelled = run_stage(
                    "profile_save_cancel", "export_preferences", "cancel", None
                )
                assert cancelled == {"ok": False, "error": "cancelled"}
                exported_profile = run_stage(
                    "profile_save_unicode", "export_preferences",
                    "confirm", str(dest_preferences)
                )
                assert exported_profile == {
                    "ok": True, "settings_count": 7, "folders_count": 0
                }, exported_profile
                assert dest_preferences.is_file()
                final["profile_bytes"] = dest_preferences.stat().st_size
                assert "source_url" not in dest_preferences.read_text(encoding="utf-8")
                assert not captured_settings, "setting writes before explicit approval"

                invalid_settings_reply = run_stage(
                    "profile_open_malformed", "preview_preferences",
                    "confirm", str(corrupt_preferences),
                )
                assert invalid_settings_reply == {
                    "ok": False, "error": "settings",
                }, invalid_settings_reply
                assert not captured_settings
                assert target_library.folders() == []

                cancelled_profile_open = run_stage(
                    "profile_open_cancel", "preview_preferences", "cancel", None
                )
                assert cancelled_profile_open == {"ok": False, "error": "cancelled"}
                reviewed = run_stage(
                    "profile_open_unicode", "preview_preferences",
                    "confirm", str(dest_preferences)
                )
                assert reviewed["ok"] is True and reviewed["settings_count"] == 7
                assert reviewed["folders_count"] == 0
                assert not captured_settings
                # Explicit second approval via the real bridge; setting
                # writes are intercepted in THIS isolated QA process.
                token = json.dumps(reviewed["token"])
                win.evaluate_js(
                    "document.body.textContent='pending';"
                    "window.pywebview.api.apply_preferences(" + token + ", false)"
                    ".then(r=>document.body.textContent=JSON.stringify(r))"
                )
                answer = None
                until = time.monotonic() + BRIDGE_TIMEOUT
                while time.monotonic() < until:
                    value = win.evaluate_js("document.body.textContent").strip()
                    if value.startswith("{"):
                        answer = json.loads(value)
                        break
                    time.sleep(0.15)
                final["profile_applied"] = bool(
                    answer and answer.get("ok")
                    and captured_settings.get("lang") == "ko"
                    and captured_settings.get("auto_send") == 0
                    and captured_settings.get("auto_capture_save") == 0
                )
                assert final["profile_applied"], answer
            except Exception as exc:
                final["errors"].append(type(exc).__name__ + ": " + str(exc)[:300])
            finally:
                hwnd = find_owned_dialog()
                if hwnd is not None:
                    import win32con
                    import win32gui
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                win.destroy()

        webview.start(execute, gui="edgechromium", http_server=False)
        final["passed"] = (
            not final["errors"]
            and final["source_preserved"] and final["imported"]
            and final["profile_applied"]
            and all(
                stage.get("seen") and not stage.get("error")
                for stage in final["stages"].values()
            )
            and len(final["stages"]) == 10
        )
        print(
            "NOTRO_NATIVE_FILE_DIALOG_QA=" + json.dumps(final, ensure_ascii=True),
            flush=True
        )
        return 0 if final["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
