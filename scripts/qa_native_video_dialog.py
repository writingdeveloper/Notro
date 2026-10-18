#!/usr/bin/env python3
"""Native WebView2 test for actual Notro video confirmation/trim UI.

Launches isolated HTML+API windows only. No real ffmpeg encoding, clipboard,
Discord client, update setting, private media or other application windows.
Verifies visible buttons route through the real pywebview JavaScript bridge.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import video_window


def main() -> int:
    import webview

    replans: list[tuple[str, str, bool]] = []

    def replan(start: str, end: str, mute: bool):
        replans.append((start, end, bool(mute)))
        return {"ok": True, "estimate": "2s clip (mute)"}

    confirm = video_window.VideoWindow(
        headline="Notro QA: confirm video",
        meta_line="5.0s · synthetic 960×540",
        estimate="5s clip",
        warn=None,
        accept_label="Start",
        trim=True,
        on_replan=replan,
        has_audio=True,
    )
    info = video_window.VideoWindow.info(
        "Notro QA: video too large",
        "Synthetic clip · 50 MB",
        "Cannot fit the configured limit",
        "Close",
    )
    confirm_win = confirm.show()
    info_win = info.show()
    result = {
        "native_webview2": False,
        "trim_controls": False,
        "replan_bridge": False,
        "confirm_bridge": False,
        "choice_preserved": False,
        "close_after_finish": False,
        "info_close_button": False,
        "no_encoding_or_paste": True,
        "errors": [],
        "passed": False,
    }

    def until(predicate, seconds=14):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(.12)
        return False

    def examine():
        try:
            result["native_webview2"] = until(
                lambda: (
                    confirm_win.evaluate_js(
                        "Boolean(window.pywebview && window.pywebview.api)"
                    )
                    and info_win.evaluate_js(
                        "Boolean(window.pywebview && window.pywebview.api)"
                    )
                )
            )
            assert result["native_webview2"], "Video UI JavaScript bridge unavailable"
            result["trim_controls"] = bool(confirm_win.evaluate_js(
                "document.getElementById('t-start') !== null"
                " && document.getElementById('t-end') !== null"
                " && document.getElementById('t-mute') !== null"
                " && document.getElementById('ok') !== null"
            ))
            assert result["trim_controls"], "Video trim controls missing"

            confirm_win.evaluate_js(
                "(() => {"
                "document.getElementById('t-start').value='0:01';"
                "document.getElementById('t-end').value='0:03';"
                "document.getElementById('t-mute').checked=true;"
                "document.getElementById('t-end').dispatchEvent("
                "new Event('input',{bubbles:true}));"
                "})()"
            )
            result["replan_bridge"] = until(
                lambda: (
                    replans
                    and replans[-1] == ("0:01", "0:03", True)
                    and confirm_win.evaluate_js(
                        "document.querySelector('.est').textContent"
                    ) == "2s clip (mute)"
                )
            )
            assert result["replan_bridge"], "Video trim bridge did not replan"

            confirm_win.evaluate_js("document.getElementById('ok').click()")
            result["confirm_bridge"] = until(confirm.accepted.is_set)
            result["choice_preserved"] = (
                confirm.choice == ("0:01", "0:03", True)
                and not confirm.cancelled.is_set()
            )
            assert result["confirm_bridge"] and result["choice_preserved"]

            confirm.finish("Done (synthetic)")
            assert until(lambda: confirm_win.evaluate_js(
                "document.getElementById('no').textContent.length>0"
            ))
            confirm_win.evaluate_js("document.getElementById('no').click()")
            result["close_after_finish"] = until(confirm.cancelled.is_set)

            assert info_win.evaluate_js(
                "document.querySelectorAll('#btns button').length"
            ) == 1
            info_win.evaluate_js("document.getElementById('ok').click()")
            result["info_close_button"] = until(info.cancelled.is_set)

            result["passed"] = all(
                value for key, value in result.items()
                if isinstance(value, bool) and key != "passed"
            ) and not result["errors"]
        except Exception as exc:
            result["errors"].append(type(exc).__name__ + ": " + str(exc)[:320])
        finally:
            video_window.destroy_all()

    try:
        webview.start(examine, gui="edgechromium", http_server=False,
                      private_mode=True)
    except Exception as exc:
        result["errors"].append(type(exc).__name__ + ": " + str(exc)[:320])
    finally:
        video_window.destroy_all()

    print("NOTRO_NATIVE_VIDEO_DIALOG_QA=" + json.dumps(
        result, ensure_ascii=True), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
