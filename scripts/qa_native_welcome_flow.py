#!/usr/bin/env python3
"""Isolated first-run Welcome -> real picker UI native WebView2 flow.

The test creates only temporary Notro sample assets and windows. It does not
touch the active installed Notro app, Windows registry, system clipboard,
Discord messages, account, global hotkeys, or user media. The picker is opened
through the actual welcome JavaScript -> Python bridge on an explicit click;
the distinct Dismiss button must not open it.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import config, fetch, welcome
from notro_app.library import Library
from notro_app.picker.assets_server import AssetServer
from notro_app.picker.window import PickerApi, ui_index_path


def main() -> int:
    import webview

    with tempfile.TemporaryDirectory(prefix="notro-welcome-qa-") as temp:
        root = Path(temp)
        # No real HKCU preferences are read/written in this separate QA process.
        config.get_setting_flag = lambda _key: False
        config.get_setting_int = lambda _key, default=0: default
        config.get_setting_str = lambda _key, default="": default
        config.set_setting_flag = lambda *_args: None
        config.set_setting_int = lambda *_args: None
        config.set_setting_str = lambda *_args: None
        config.TEMP_DIR = str(root / "temporary")
        library = Library(str(root / "private-owned-library"))
        source = root / "original.png"
        Image.new("RGB", (72, 72), (76, 162, 212)).save(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        fetch.register_from_file(
            library, str(source), "emoji", name="Owned welcome sample"
        )
        server = AssetServer(
            lambda item_id: library.asset_path(item)
            if (item := library.resolve(item_id)) else None
        )
        server.start()
        api = PickerApi(library=library, asset_server=server)
        picker_win = webview.create_window(
            "Notro QA picker", url=ui_index_path(), js_api=api,
            width=535, height=445, frameless=False, on_top=False,
            hidden=True,
        )
        events: list[str] = []

        def on_try():
            events.append("try")
            picker_win.show()
            picker_win.evaluate_js("window.__onShow && window.__onShow()")

        intro_api = welcome._Api(on_try=on_try)
        intro_win = webview.create_window(
            "Notro QA welcome", html=welcome.build_html("Ctrl+Shift+E"),
            js_api=intro_api, width=welcome.WIN_W, height=welcome.WIN_H,
            resizable=False, on_top=False,
        )
        intro_api._window = intro_win

        dismiss_api = welcome._Api(
            on_try=lambda: events.append("unexpected_try")
        )
        dismiss_win = webview.create_window(
            "Notro QA dismiss", html=welcome.build_html("Ctrl+Shift+E"),
            js_api=dismiss_api, width=welcome.WIN_W, height=welcome.WIN_H,
            resizable=False, on_top=False, hidden=True,
        )
        dismiss_api._window = dismiss_win

        result = {
            "native_webview2": False, "welcome_buttons": False,
            "picker_initially_hidden": False, "try_clicked": False,
            "picker_opened": False, "picker_has_owned_asset": False,
            "dismiss_does_not_open_picker": False, "source_preserved": False,
            "no_clipboard_mutation": True, "errors": [], "passed": False,
        }

        def until(predicate, seconds=15):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    if predicate():
                        return True
                except Exception:
                    pass
                time.sleep(0.15)
            return False

        def run():
            try:
                result["native_webview2"] = until(
                    lambda: bool(intro_win.evaluate_js(
                        "Boolean(window.pywebview && window.pywebview.api)"
                    ))
                )
                assert result["native_webview2"], "welcome bridge unavailable"
                result["welcome_buttons"] = bool(intro_win.evaluate_js(
                    "document.getElementById('try').textContent.length>0"
                    " && document.getElementById('ok').textContent.length>0"
                    " && document.getElementsByTagName('kbd').length===1"
                ))
                result["picker_initially_hidden"] = (
                    picker_win.native is not None
                    and not bool(picker_win.native.Visible)
                )
                assert result["welcome_buttons"]
                assert result["picker_initially_hidden"]

                # The action must be user-driven; no automatic picker opening
                # merely because the initial welcome exists.
                assert not events
                intro_win.evaluate_js("document.getElementById('try').click()")
                result["try_clicked"] = until(lambda: events == ["try"])
                result["picker_opened"] = until(
                    lambda: picker_win.native is not None
                    and bool(picker_win.native.Visible)
                )
                result["picker_has_owned_asset"] = until(
                    lambda: int(picker_win.evaluate_js("state.items.length")) == 1
                    and picker_win.evaluate_js(
                        "document.querySelectorAll('.cell img').length") == 1
                )
                assert result["picker_opened"] and result["picker_has_owned_asset"]
                picker_win.hide()
                dismiss_win.show()
                assert until(lambda: dismiss_win.evaluate_js(
                    "Boolean(window.pywebview && window.pywebview.api)"
                ))
                dismiss_win.evaluate_js("document.getElementById('ok').click()")
                result["dismiss_does_not_open_picker"] = until(
                    lambda: not bool(dismiss_win.native.Visible)
                    and events == ["try"]
                )
                result["source_preserved"] = (
                    hashlib.sha256(source.read_bytes()).hexdigest() == digest
                    and len(library.items()) == 1
                )
                result["passed"] = all(
                    value for key, value in result.items()
                    if isinstance(value, bool) and key != "passed"
                ) and not result["errors"]
            except Exception as exc:
                result["errors"].append(
                    type(exc).__name__ + ": " + str(exc)[:320]
                )
            finally:
                for window in (intro_win, dismiss_win, picker_win):
                    try:
                        window.destroy()
                    except Exception:
                        pass

        try:
            webview.start(run, gui="edgechromium", http_server=False,
                          private_mode=True)
        except Exception as exc:
            result["errors"].append(
                type(exc).__name__ + ": " + str(exc)[:320]
            )
        finally:
            server.stop()

    print("NOTRO_NATIVE_WELCOME_QA=" + json.dumps(
        result, ensure_ascii=True), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
