# -*- coding: utf-8 -*-
"""Notro's independently branded WebView2 tray popup.

The normal pystray Windows menu remains a complete, usable fallback when
WebView2 is unavailable or the themed window is not yet initialized.
No Discord application, private APIs, REA or user clipboard are accessed.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import threading
from pathlib import Path

from . import APP_NAME, __version__

WINDOW_TITLE = "Notro Tray Menu"
PANEL_W, PANEL_H = 362, 532
PROJECT_URL = "https://github.com/writingdeveloper/Notro"
LINKS = {
    "source": PROJECT_URL,
    "releases": PROJECT_URL + "/releases",
    "issues": PROJECT_URL + "/issues",
    "license": PROJECT_URL + "/blob/main/LICENSE",
}
MONITOR_DEFAULTTONEAREST = 2

# Own a private ctypes function table. Overwriting argtypes on the shared
# ctypes.windll.user32.SetWindowPos breaks pywebview's window.move(), which
# legitimately supplies None for SWP_NOSIZE arguments.
user32 = ctypes.WinDLL("user32", use_last_error=True)


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
        ("rcWork", wt.RECT), ("dwFlags", wt.DWORD),
    ]


# Native HWND/monitor APIs use process DPI physical pixels on Windows.
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.MonitorFromPoint.restype = wt.HANDLE
user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
user32.GetMonitorInfoW.argtypes = [wt.HANDLE, ctypes.POINTER(_MONITORINFO)]
user32.FindWindowW.restype = wt.HWND
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.SetWindowPos.restype = wt.BOOL
user32.SetWindowPos.argtypes = [
    wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.UINT,
]


def panel_index_path() -> str:
    """Works both in editable source and PyInstaller's bundled UI."""
    import sys

    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = str(Path(__file__).resolve().parent.parent)
    return str(Path(base) / "notro_app" / "picker" / "ui" / "tray_panel.html")


def panel_coordinates(
    px: int, py: int, width: int, height: int,
    work: tuple[int, int, int, int],
) -> tuple[int, int]:
    """Clamp to cursor's monitor work area, above taskbar if possible."""
    left, top, right, bottom = work
    width = min(max(width, 1), right - left)
    height = min(max(height, 1), bottom - top)
    x = min(max(px - width + 24, left), right - width)
    y = py - height - 9
    if y < top:
        y = min(max(py + 12, top), bottom - height)
    return x, y


def geometry_from_cursor(width: int, height: int) -> tuple[int, int, int, int]:
    cursor = wt.POINT()
    if not user32.GetCursorPos(ctypes.byref(cursor)):
        raise OSError("Windows cursor position unavailable")
    monitor = user32.MonitorFromPoint(cursor, MONITOR_DEFAULTTONEAREST)
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise OSError("Windows work area unavailable")
    work = info.rcWork
    w = min(width, work.right - work.left)
    h = min(height, work.bottom - work.top)
    x, y = panel_coordinates(
        cursor.x, cursor.y, w, h,
        (work.left, work.top, work.right, work.bottom),
    )
    return x, y, w, h


def info_payload() -> dict:
    """Product data, never account/user/profile data or a fabricated SHA."""
    return {
        "name": APP_NAME,
        "version": __version__,
        "license": "MIT",
        "platform": "Windows 10 / 11",
        "engine": "Windows · Edge WebView2",
        "publisher": "writingdeveloper",
        "url": PROJECT_URL,
        "links": dict(LINKS),
        "signed": False,
    }


def native_about_fallback() -> None:
    """Accessible About when WebView2 is missing, without altering settings."""
    detail = (
        f"{APP_NAME} v{__version__}\n"
        "Windows image, sticker & GIF picker\n\n"
        f"GitHub: {PROJECT_URL}\n"
        "License: MIT · Publisher: writingdeveloper\n"
        "Unsigned build. Not affiliated with Discord."
    )
    user32.MessageBoxW(None, detail, f"About {APP_NAME}", 0x00000040)


def open_project_link(which: str) -> bool:
    """Open only hardcoded project URLs; never a caller-controlled address."""
    import webbrowser

    url = LINKS.get(which)
    if not url:
        return False
    return bool(webbrowser.open(url))


class PanelApi:
    """Public pywebview bridge, private references never traversed as JS API."""

    def __init__(self, panel: "TrayPanel"):
        self._panel = panel

    def ready(self) -> bool:
        self._panel._ready.set()
        return True

    def get_state(self) -> dict:
        return self._panel._get_state()

    def activate(self, name: str, value: str = "") -> dict:
        return self._panel._activate(name, value)

    def hide(self) -> bool:
        self._panel.hide()
        return True


class TrayPanel:
    """Single hidden frameless popup with main/settings/about pages."""

    def __init__(self, state, action):
        self._state = state
        self._action = action
        self._window = None
        self._ready = threading.Event()
        self._lock = threading.RLock()
        self._visible = False
        self._last_error = ""
        self._last_step = ""
        self._api = PanelApi(self)

    def create_window(self):
        import webview

        self._window = webview.create_window(
            WINDOW_TITLE, url=panel_index_path(), js_api=self._api,
            width=PANEL_W, height=PANEL_H,
            hidden=True, frameless=True, easy_drag=False,
            on_top=True, resizable=False, min_size=(PANEL_W, PANEL_H),
            background_color="#17191f",
        )
        return self._window

    def _get_state(self) -> dict:
        result = self._state()
        result["about"] = info_payload()
        return result

    def _activate(self, name: str, value: str = "") -> dict:
        if name == "open_link":
            return {"ok": open_project_link(value)}
        try:
            success = bool(self._action(name, value))
        except (OSError, ValueError) as exc:
            return {"ok": False, "error": type(exc).__name__}
        return {"ok": success}

    def request_show(self, page: str = "home") -> bool:
        """Called from pystray Win32 message thread; do not block that loop."""
        if not self._ready.is_set() or self._window is None:
            return False  # native context menu remains available
        target = page if page in ("home", "about", "settings") else "home"
        threading.Thread(
            target=self._show, args=(target,),
            name="NotroTrayPopup", daemon=True,
        ).start()
        return True

    def show_about(self) -> bool:
        return self.request_show("about")

    def _show(self, page: str) -> None:
        if self._window is None:
            return
        with self._lock:
            try:
                if self._visible and page == "home":
                    self.hide()
                    return
                x, y, w, h = geometry_from_cursor(PANEL_W, PANEL_H)
                self._last_step = "show"
                self._window.show()
                # Avoid pywebview 6.x WinForms Window.move(x,y): its native
                # SetWindowPos wrapper passes None for unused size parameters
                # and fails on typed Windows APIs. Position our own HWND
                # directly using a PRIVATE user32 function table instead.
                self._last_step = "find"
                hwnd = user32.FindWindowW(None, WINDOW_TITLE)
                if hwnd:
                    self._last_step = "setpos"
                    user32.SetWindowPos(
                        hwnd, -1, x, y, w, h,
                        0x0040 | 0x4000,  # SHOWWINDOW | ASYNCWINDOWPOS
                    )
                self._visible = True
                self._last_step = "javascript"
                # JSON/state comes from the safe bridge, never interpolated
                # from untrusted item paths into executable JavaScript.
                self._window.evaluate_js(
                    f"window.notroPanelOpen && window.notroPanelOpen('{page}')"
                )
            except Exception as exc:
                self._last_error = self._last_step + ": " + type(exc).__name__ + ": " + str(exc)[:140]
                self._visible = False
                try:
                    self._window.hide()
                except Exception:
                    pass

    def hide(self) -> None:
        with self._lock:
            if self._window is not None and self._visible:
                self._visible = False
                try:
                    self._window.hide()
                except Exception:
                    pass

    def destroy(self) -> None:
        with self._lock:
            self._ready.clear()
            self._visible = False
            if self._window is not None:
                try:
                    self._window.destroy()
                except Exception:
                    pass
