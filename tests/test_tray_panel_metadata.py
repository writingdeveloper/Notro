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
