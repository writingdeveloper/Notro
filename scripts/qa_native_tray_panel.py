#!/usr/bin/env python3
"""Isolated real WebView2 QA for the Notro styled tray menu and About view.

No real Notro registry writes, global hotkeys, clipboard, Discord, remote
navigation or production tray notifications. The Win32 right-click path is
invoked directly on an unregistered test icon; the real native popup UI is
rendered and clicked in a private WebView2 window. Captures only this own
WebView2 surface, not desktop pixels.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import config, i18n, tray, tray_panel
from scripts.record_owned_native_demo import native_capture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Optionally retain screenshots of this owned WebView2 window")
    args = parser.parse_args()
    import webview
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    i18n.set_language("ko")
    settings = {
        "hotkey": "ctrl+shift+e", "lang": "ko",
        "limit_mb": 20, "startup": False,
    }
    calls = []
    state = {"picker_open": 0}
    orig_getstr = tray.get_setting_str
    orig_getint = config.get_setting_int
    orig_setint = tray.set_setting_int
    orig_setstr = tray.set_setting_str
    orig_isstartup = tray.is_startup_registered
    orig_setstartup = tray.set_startup
    orig_open = tray_panel.open_project_link

    tray.get_setting_str = lambda key, default="": settings.get(key, default)
    config.get_setting_int = lambda key, default=0: default
    tray.set_setting_int = lambda key, value: settings.__setitem__(key, value)
    tray.set_setting_str = lambda key, value: settings.__setitem__(key, value)
    tray.is_startup_registered = lambda: settings["startup"]
    tray.set_startup = lambda value: settings.__setitem__("startup", bool(value))
    tray_panel.open_project_link = lambda name: calls.append(name) or True

    class DummyPicker:
        def show_at_cursor(self):
            state["picker_open"] += 1

    class DummyListener:
        def set_combo(self, value):
            settings["hotkey"] = value

    class DummyMonitor:
        enabled = True
        history_lock = threading.Lock()
        history = []

    monitor = DummyMonitor()
    picker = DummyPicker()
    panel = tray_panel.TrayPanel(state=lambda: {}, action=lambda *_: False)
    window = panel.create_window()
    icon = tray.build_icon(monitor, picker=picker, listener=DummyListener(),
                           tray_panel=panel, updater=None)
    result = {"native_webview2": False, "about_version": False,
              "about_github": False, "about_unsigned": False,
              "native_rightclick": False, "settings_actions": False,
              "fallback_ready_gate": False, "picker_action": False,
              "esc_close": False, "language_layout": False,
              "keyboard_focus": False, "zoom_scroll_accessible": False,
              "compact_window_accessible": False,
              "screenshots": [], "errors": [], "passed": False}

    try:
        result["fallback_ready_gate"] = bool(
            not panel.request_show("home") and panel._window is not None)

        def until(check, timeout=14):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                try:
                    if check():
                        return True
                except Exception:
                    pass
                time.sleep(.15)
            return False

        def smoke():
            stage = "ready"
            try:
                if not panel._ready.wait(timeout=17):
                    raise AssertionError("WebView2 tray bridge never ready")
                stage = "native_rightclick"
                icon._on_notify(0, 0x0205)
                assert until(lambda: panel._visible), (
                    "rightclick callback failed " + panel._last_error)
                stage = "home_webview"
                assert until(lambda: window.evaluate_js(
                    "!document.getElementById('page-home').classList.contains('hidden')"
                    " && document.getElementById('txt-picker').textContent.length > 3"
                ))
                result["native_rightclick"] = True
                result["native_webview2"] = True
                import ctypes
                from ctypes import wintypes as wt
                hwnd_diag = tray_panel.user32.FindWindowW(
                    None, tray_panel.WINDOW_TITLE)
                rect_diag = wt.RECT()
                tray_panel.user32.GetWindowRect(
                    hwnd_diag, ctypes.byref(rect_diag))
                result["startup_geometry"] = {
                    "hwnd_width": rect_diag.right-rect_diag.left,
                    "hwnd_height": rect_diag.bottom-rect_diag.top,
                    "browser_width": window.evaluate_js(
                        "document.documentElement.clientWidth"),
                    "browser_height": window.evaluate_js(
                        "document.documentElement.clientHeight"),
                    "device_pixel_ratio": window.evaluate_js(
                        "window.devicePixelRatio"),
                    "windows_dpi": tray_panel.user32.GetDpiForWindow(hwnd_diag),
                }
                measured = result["startup_geometry"]
                assert abs(measured["browser_width"] - tray_panel.PANEL_W) <= 2
                assert abs(measured["browser_height"] - tray_panel.PANEL_H) <= 2
                assert abs(measured["hwnd_width"] -
                           round(tray_panel.PANEL_W *
                                 measured["windows_dpi"] / 96)) <= 4
                assert abs(measured["hwnd_height"] -
                           round(tray_panel.PANEL_H *
                                 measured["windows_dpi"] / 96)) <= 4
                with tempfile.TemporaryDirectory(prefix="notro-tray-capture-") as root:
                    root = Path(root)
                    img = native_capture(window, root / "home.png")
                    result["screenshots"].append({
                        "page": "home", "width": img.width, "height": img.height
                    })
                    target = Path(os.environ.get("TEMP", str(root))) / "notro-tray-ui-home-qa.png"
                    img.save(target)
                    result["home_preview_temp"] = str(target)
                    if args.output_dir:
                        img.save(args.output_dir / "tray-menu-native-preview.png")

                    window.evaluate_js(
                        "document.getElementById('btn-about').click()"
                    )
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-about').classList.contains('hidden')"
                    ))
                    result["about_version"] = window.evaluate_js(
                        "document.getElementById('about-version').textContent"
                    ) == "v2.11.0"
                    result["about_github"] = bool(
                        window.evaluate_js(
                            "document.getElementById('txt-github').textContent.length>2"
                        ))
                    result["about_unsigned"] = bool(
                        window.evaluate_js(
                            "document.getElementById('about-disclosure').textContent.length>25"
                        ))
                    assert window.evaluate_js(
                        "document.getElementById('about-quick-github')"
                        ".textContent.includes('github.com/writingdeveloper/Notro')"
                    ), "Quick GitHub link missing from the About hero"
                    image = native_capture(window, root / "about.png")
                    result["screenshots"].append({
                        "page": "about", "width": image.width, "height": image.height
                    })
                    target = Path(os.environ.get("TEMP", str(root))) / "notro-tray-ui-about-qa.png"
                    image.save(target)
                    result["about_preview_temp"] = str(target)
                    if args.output_dir:
                        image.save(args.output_dir / "tray-about-native-preview.png")

                    window.evaluate_js(
                        "document.getElementById('link-github').click()"
                    )
                    assert until(lambda: "source" in calls)

                    window.evaluate_js(
                        "document.querySelector('[data-nav=home]').click()"
                    )
                    window.evaluate_js(
                        "document.getElementById('btn-settings').click()"
                    )
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-settings').classList.contains('hidden')"
                    ))
                    window.evaluate_js(
                        "document.getElementById('select-limit').value='50';"
                        "document.getElementById('select-limit').dispatchEvent("
                        "new Event('change',{bubbles:true}))"
                    )
                    assert until(lambda: settings.get("limit_mb")==50)
                    result["settings_actions"] = True

                    # Same actual Windows WebView2 UI, independent local
                    # language values. Never read user locale/registry.
                    for lang in ("en", "ko", "ja", "zh", "es"):
                        settings["lang"] = lang
                        i18n.set_language(lang)
                        window.evaluate_js("window.notroPanelOpen('about')")
                        assert until(lambda lang=lang: window.evaluate_js(
                            "document.documentElement.lang"
                        ) == lang), "Missing localized About page: " + lang
                        expected = i18n.STRINGS[lang]["tray_about"]
                        assert window.evaluate_js(
                            "document.getElementById('txt-about').textContent"
                        ) == expected, "Incorrect translation: " + lang
                        assert window.evaluate_js(
                            "document.getElementById('about-quick-github')"
                            ".getAttribute('aria-label').length > 2"
                        )
                    result["language_layout"] = True

                    # Keyboard-only access to the visible, actual About
                    # GitHub link: focus navigation must never invoke the
                    # link or launch a browser on its own.
                    window.evaluate_js(
                        "document.getElementById('about-quick-github').focus()"
                    )
                    result["keyboard_focus"] = bool(window.evaluate_js(
                        "document.activeElement.id === 'about-quick-github'"
                    ))

                    # Simulated in-browser text zoom is NOT proof of real
                    # 125/150% physical monitor DPI. It ensures that a
                    # scroll container and links remain keyboard accessible.
                    for zoom in ("1.0", "1.25", "1.5"):
                        window.evaluate_js(
                            f"document.documentElement.style.zoom='{zoom}';"
                            "document.getElementById('link-license')"
                            ".scrollIntoView({block:'nearest'})"
                        )
                        assert window.evaluate_js(
                            "document.activeElement.id === 'about-quick-github'"
                        )
                        assert bool(window.evaluate_js(
                            "document.getElementById('link-license').offsetWidth > 0"
                            " && document.getElementById('page-about').scrollHeight > 0"
                        )), "About links inaccessible at zoom " + zoom
                    window.evaluate_js(
                        "document.documentElement.style.zoom='1.0';"
                        "window.notroPanelOpen('settings')"
                    )
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-settings').classList.contains('hidden')"
                    ))
                    result["zoom_scroll_accessible"] = True

                    # Exercise the actual Win32/WebView2 compact-window
                    # layout, accounting for device physical pixel scale.
                    # This is not a substitute for a real second monitor.
                    native_hwnd = tray_panel.user32.FindWindowW(
                        None, tray_panel.WINDOW_TITLE
                    )
                    dpi_scale = float(window.evaluate_js(
                        "window.devicePixelRatio") or 1)
                    scaled_w = int(330 * dpi_scale)
                    scaled_h = int(420 * dpi_scale)
                    if not tray_panel.user32.SetWindowPos(
                            native_hwnd, 0, 100, 90,
                            scaled_w, scaled_h, 0x0004):
                        raise AssertionError("cannot resize owned QA popup")
                    assert until(lambda: 300 <= int(window.evaluate_js(
                        "document.documentElement.clientWidth")) <= 370), (
                        "compact WebView2 width not applied")
                    window.evaluate_js("window.notroPanelOpen('about')")
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-about').classList.contains('hidden')"
                    ))
                    window.evaluate_js(
                        "document.getElementById('link-license')"
                        ".scrollIntoView({block:'nearest'})"
                    )
                    result["compact_window_accessible"] = bool(
                        window.evaluate_js(
                            "(() => { const link=document.getElementById('link-license');"
                            "const rect=link.getBoundingClientRect();"
                            "return link.offsetHeight>0 && rect.left>=-2"
                            " && rect.right<=window.innerWidth+2"
                            " && document.documentElement.clientWidth<=340;"
                            "})()"
                        ))
                    assert result["compact_window_accessible"], (
                        "Narrow WebView2 popup clipped the About license link")
                    tray_panel.user32.SetWindowPos(
                        native_hwnd, 0, 100, 90,
                        int(tray_panel.PANEL_W*dpi_scale),
                        int(tray_panel.PANEL_H*dpi_scale), 0x0004,
                    )
                    window.evaluate_js("window.notroPanelOpen('settings')")
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-settings').classList.contains('hidden')"
                    ))

                    window.evaluate_js(
                        "document.dispatchEvent(new KeyboardEvent("
                        "'keydown',{key:'Escape',bubbles:true}))"
                    )
                    assert until(lambda: window.evaluate_js(
                        "!document.getElementById('page-home').classList.contains('hidden')"
                    ))
                    window.evaluate_js(
                        "document.dispatchEvent(new KeyboardEvent("
                        "'keydown',{key:'Escape',bubbles:true}))"
                    )
                    assert until(lambda: not panel._visible)
                    result["esc_close"] = True

                    # Reopen from Win32 icon notification and use actual
                    # shared tray action without sending any keyboard keys.
                    icon._on_notify(0,0x0205)
                    assert until(lambda: panel._visible)
                    window.evaluate_js(
                        "document.getElementById('btn-picker').click()"
                    )
                    result["picker_action"] = until(
                        lambda: state["picker_open"] == 1
                        and not panel._visible
                    )

                result["passed"] = all(
                    v for k,v in result.items()
                    if isinstance(v,bool) and k != "passed"
                ) and not result["errors"]
            except Exception as exc:
                result["errors"].append(stage + ": " + type(exc).__name__
                                        + ": " + str(exc)[:300])
                result["native_error"] = panel._last_error
                result["panel_ready"] = panel._ready.is_set()
                result["panel_visible"] = panel._visible
            finally:
                panel.destroy()

        webview.start(smoke, gui="edgechromium", http_server=False,
                      private_mode=True)
    except Exception as exc:
        result["errors"].append(type(exc).__name__+": "+str(exc)[:340])
    finally:
        panel.destroy()
        config.set_limit_mb(20)
        tray.get_setting_str = orig_getstr
        config.get_setting_int = orig_getint
        tray.set_setting_int = orig_setint
        tray.set_setting_str = orig_setstr
        tray.is_startup_registered = orig_isstartup
        tray.set_startup = orig_setstartup
        tray_panel.open_project_link = orig_open

    print("NOTRO_TRAY_NATIVE_QA="+json.dumps(result,ensure_ascii=True),flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
