"""Native Notro tray/About contract without mutating Windows settings.

Test the shared metadata and monitor-clamped popup geometry independently of
a live user's tray/Discord app. UI integration tests are a separate gate.
"""
from __future__ import annotations

import webbrowser

from notro_app import APP_NAME, __version__
from notro_app import tray_panel


def test_about_metadata_is_real_candidate_version_not_published_tag():
    payload = tray_panel.info_payload()
    assert payload["name"] == APP_NAME == "Notro"
    assert payload["version"] == __version__
    assert payload["signed"] is False
    assert payload["license"] == "MIT"
    assert payload["publisher"] == "writingdeveloper"
    assert "Windows" in payload["platform"]
    assert "WebView2" in payload["engine"]


def test_about_links_are_known_project_urls_only():
    origin = "https://github.com/writingdeveloper/Notro"
    expected = {
        "source": origin,
        "releases": origin + "/releases",
        "issues": origin + "/issues",
        "license": origin + "/blob/main/LICENSE",
    }
    assert tray_panel.info_payload()["links"] == expected


def test_link_handler_rejects_unknown_urls_and_external_input(monkeypatch):
    visited = []
    monkeypatch.setattr(webbrowser, "open",
                        lambda url: visited.append(url) or True)
    assert not tray_panel.open_project_link("https://evil.example/")
    assert not tray_panel.open_project_link("../tokens")
    assert not tray_panel.open_project_link("settings")
    assert visited == []
    for name, expected_url in tray_panel.LINKS.items():
        assert tray_panel.open_project_link(name)
        assert visited[-1] == expected_url


def test_popup_position_bounded_by_monitor_on_all_edges():
    work = (1920, -800, 3200, 720)
    for x, y in ((1920, -800), (3199, -799), (1921, 719),
                 (3199, 719), (2620, 100)):
        px, py = tray_panel.panel_coordinates(x, y, 362, 532, work)
        assert work[0] <= px <= work[2] - 362
        assert work[1] <= py <= work[3] - 532


def test_popup_works_on_small_monitor_work_area():
    rect = (0, 0, 330, 420)
    for point in ((0, 0), (330, 420), (170, 200)):
        x, y = tray_panel.panel_coordinates(*point, 362, 532, rect)
        assert x == 0 and y == 0


def test_themed_popup_requires_a_ready_webview_before_replacing_native_menu():
    calls = []
    panel = tray_panel.TrayPanel(
        state=lambda: {"monitor_enabled": True},
        action=lambda action, value: calls.append((action, value)) or True,
    )
    assert panel.request_show() is False
    assert panel.show_about() is False
    assert calls == []
    result = panel._api.get_state()
    assert result["about"]["version"] == __version__
    assert result["about"]["signed"] is False
    assert panel._api.activate("something", "demo") == {"ok": True}
    assert calls == [("something", "demo")]


def test_packaged_path_stays_within_bundled_ui(monkeypatch, tmp_path):
    import sys
    from pathlib import Path

    base = tmp_path / "build"
    monkeypatch.setattr(sys, "_MEIPASS", str(base), raising=False)
    expected = base / "notro_app" / "picker" / "ui" / "tray_panel.html"
    assert Path(tray_panel.panel_index_path()) == expected


def test_compact_tray_window_can_fit_small_work_areas():
    assert tray_panel.MIN_PANEL_W <= 330
    assert tray_panel.MIN_PANEL_H <= 420
    assert tray_panel.MIN_PANEL_W >= 300
    assert tray_panel.MIN_PANEL_H >= 300


def test_tiny_monitor_keeps_native_fallback_instead_of_clipping(monkeypatch):
    panel = tray_panel.TrayPanel(state=lambda: {}, action=lambda *_: True)
    panel._ready.set()
    panel._window = object()
    monkeypatch.setattr(tray_panel, "geometry_from_cursor",
                        lambda w, h: (0, 0, 250, 300))
    assert panel.request_show("home") is False
    assert panel.show_about() is False
    assert not panel._visible


def test_monitor_query_failure_keeps_native_menu(monkeypatch):
    panel = tray_panel.TrayPanel(state=lambda: {}, action=lambda *_: True)
    panel._ready.set()
    panel._window = object()
    def broken(_w, _h):
        raise OSError("no display")
    monkeypatch.setattr(tray_panel, "geometry_from_cursor", broken)
    assert not panel.request_show()


def test_native_about_localized_without_opening_real_dialog(monkeypatch):
    from notro_app import i18n
    seen = []
    monkeypatch.setattr(i18n, "current_lang", "ko")
    monkeypatch.setattr(tray_panel.user32, "MessageBoxW",
                        lambda parent, text, title, flags:
                        seen.append((text, title, flags)))
    tray_panel.native_about_fallback()
    assert len(seen) == 1
    text, title, flags = seen[0]
    assert "Notro 정보" in title
    assert "v2.11.0" in text
    assert "github.com/writingdeveloper/Notro" in text
    assert "MIT" in text and "Windows" in text
    assert "서명되지 않은" in text


def test_dpi_aware_win32_geometry_uses_physical_not_browser_css_pixels(monkeypatch):
    args = []
    monkeypatch.setattr(tray_panel.user32, "GetDpiForWindow",
                        lambda hwnd: 192)
    monkeypatch.setattr(tray_panel, "geometry_from_cursor",
                        lambda w, h: args.append((w, h)) or (20, 30, w, h))
    x, y, width, height, scale = tray_panel._scaled_panel_bounds(1234)
    assert (x, y) == (20, 30)
    assert (scale, width, height) == (2.0, 724, 1064)
    assert args == [(724, 1064)]


def test_normal_dpi_keeps_expected_browser_geometry(monkeypatch):
    monkeypatch.setattr(tray_panel.user32, "GetDpiForWindow",
                        lambda hwnd: 96)
    monkeypatch.setattr(tray_panel, "geometry_from_cursor",
                        lambda w, h: (0, 0, w, h))
    assert tray_panel._scaled_panel_bounds(12) == (0, 0, 362, 532, 1.0)


def test_scaled_bounds_clamped_by_actual_monitor(monkeypatch):
    monkeypatch.setattr(tray_panel.user32, "GetDpiForWindow",
                        lambda hwnd: 192)
    monkeypatch.setattr(tray_panel, "geometry_from_cursor",
                        lambda w, h: (10, 20, min(w, 660), min(h, 840)))
    assert tray_panel._scaled_panel_bounds(12) == (10, 20, 660, 840, 2.0)


def test_title_matched_popup_must_belong_to_this_process(monkeypatch):
    import ctypes
    import ctypes.wintypes as wt

    monkeypatch.setattr(tray_panel.user32, "FindWindowW",
                        lambda title_class, title: 4567)
    monkeypatch.setattr(tray_panel.os, "getpid", lambda: 1111)

    def pretend_owner(hwnd, target):
        assert int(hwnd) == 4567
        ctypes.cast(target, ctypes.POINTER(wt.DWORD)).contents.value = 2222
        return 1

    monkeypatch.setattr(tray_panel.user32, "GetWindowThreadProcessId",
                        pretend_owner)
    assert tray_panel._owned_popup_hwnd() == 0

    def actual_owner(hwnd, target):
        ctypes.cast(target, ctypes.POINTER(wt.DWORD)).contents.value = 1111
        return 1

    monkeypatch.setattr(tray_panel.user32, "GetWindowThreadProcessId",
                        actual_owner)
    assert tray_panel._owned_popup_hwnd() == 4567

    monkeypatch.setattr(tray_panel.user32, "FindWindowW",
                        lambda title_class, title: 0)
    assert tray_panel._owned_popup_hwnd() == 0
