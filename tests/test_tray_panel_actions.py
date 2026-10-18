"""Tray menu and About action parity with Windows native fallback.

This is a pure unit test: it constructs a pystray icon without registering
it with Windows, replaces registry/folder effects and never opens Discord.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from notro_app import config, i18n, tray, tray_panel


def make_sandbox(monkeypatch):
    settings = {"lang": "ko", "hotkey": "ctrl+shift+e",
                "limit_mb": 20, "startup": False}
    operations = []
    monitor = SimpleNamespace(
        enabled=True, history=[], history_lock=threading.RLock(),
        status_cb=None, on_history_change=None
    )
    picker = SimpleNamespace(show_at_cursor=lambda: operations.append("picker"))
    listener = SimpleNamespace(
        set_combo=lambda value: operations.append(("hotkey", value))
    )
    monkeypatch.setattr(tray, "get_setting_str",
                        lambda key, default="": settings.get(key, default))
    monkeypatch.setattr(tray, "set_setting_str",
                        lambda key, value: settings.__setitem__(key, value))
    monkeypatch.setattr(tray, "set_setting_int",
                        lambda key, value: settings.__setitem__(key, value))
    monkeypatch.setattr(tray, "is_startup_registered",
                        lambda: settings["startup"])
    monkeypatch.setattr(tray, "set_startup",
                        lambda value: settings.__setitem__("startup", value))
    monkeypatch.setattr(tray.os, "startfile",
                        lambda path: operations.append(("open", path)),
                        raising=False)
    i18n.set_language("ko")
    panel = tray_panel.TrayPanel(
        state=lambda: {}, action=lambda *_: False)
    icon = tray.build_icon(
        monitor, picker=picker, listener=listener,
        tray_panel=panel, updater=None
    )
    monkeypatch.setattr(icon, "update_menu",
                        lambda: operations.append("update-menu"))
    return panel, icon, monitor, settings, operations


def test_styled_menu_has_complete_real_state_and_five_language_copy(monkeypatch):
    panel, _, monitor, settings, _ = make_sandbox(monkeypatch)
    state = panel._api.get_state()
    assert state["about"]["version"] == "2.11.0"
    assert state["about"]["signed"] is False
    assert state["lang_resolved"] == "ko"
    assert state["monitor_enabled"]
    assert state["limit_mb"] == 20
    assert state["hotkey"] == "ctrl+shift+e"
    assert "1 GB" not in state["labels"]["limit_note"] or "1GB" in (
        state["labels"]["limit_note"])
    assert state["updater_present"] is False
    assert len(state["languages"]) == 6
    assert {x["value"] for x in state["hotkeys"]} == {
        "ctrl+shift+e", "ctrl+alt+e", "ctrl+shift+space", "off"}
    assert state["labels"]["about"] == "Notro 정보"
    for lang in i18n.SUPPORTED_LANGS:
        for key in (
            "tray_about", "tray_settings", "tray_running", "tray_paused",
            "tray_github", "tray_releases", "tray_issues", "tray_disclosure"
        ):
            assert i18n.STRINGS[lang][key]


def test_popup_real_actions_pause_limits_language_hotkey_and_startup(monkeypatch):
    panel, _, monitor, settings, events = make_sandbox(monkeypatch)
    original = config.LIMIT_MB
    try:
        assert panel._api.activate("toggle")["ok"]
        assert monitor.enabled is False
        assert panel._api.activate("toggle")["ok"]
        assert monitor.enabled is True
        assert panel._api.activate("limit", "50")["ok"]
        assert settings["limit_mb"] == config.LIMIT_MB == 50
        assert panel._api.activate("limit", "1024")["ok"]
        assert config.LIMIT_MB == 1024
        assert panel._api.activate("language", "en")["ok"]
        assert settings["lang"] == "en"
        assert i18n.current_lang == "en"
        assert panel._api.activate("hotkey", "off")["ok"]
        assert settings["hotkey"] == "off"
        assert ("hotkey", "off") in events
        assert panel._api.activate("startup")["ok"]
        assert settings["startup"] is True
        assert panel._api.activate("startup")["ok"]
        assert settings["startup"] is False
    finally:
        config.set_limit_mb(original)


def test_popup_rejects_unknown_mutation_and_unavailable_updater(monkeypatch):
    panel, _, monitor, settings, events = make_sandbox(monkeypatch)
    baseline = (monitor.enabled, dict(settings), len(events))
    for action, value in (
        ("unknown", ""), ("delete_all", ""), ("limit", "999999"),
        ("limit", "../../user"), ("language", "invalid"),
        ("hotkey", "alt+f4"), ("check_update", ""),
        ("restart_update", ""), ("auto_update", "")
    ):
        assert panel._api.activate(action, value) == {"ok": False}
    assert (monitor.enabled, settings, len(events)) == baseline


def test_rightclick_is_themed_only_when_ready_else_native_fallback(monkeypatch):
    import pystray._win32 as native

    panel, icon, _, _, _ = make_sandbox(monkeypatch)
    calls = []
    monkeypatch.setattr(native.Icon, "_on_notify",
                        lambda self, w, event: calls.append(("native", event)))
    assert panel._ready.is_set() is False
    icon._on_notify(0, tray._NotroIcon.WM_RBUTTONUP)
    assert calls == [("native", tray._NotroIcon.WM_RBUTTONUP)]

    monkeypatch.setattr(panel, "request_show",
                        lambda page: calls.append(("themed", page)) or True)
    icon._on_notify(0, tray._NotroIcon.WM_RBUTTONUP)
    assert calls[-1] == ("themed", "home")
    assert len(calls) == 2
    icon._on_notify(0, 0x0202)  # ordinary left click uses native behavior
    assert calls[-1] == ("native", 0x0202)


def test_about_has_native_fallback_without_webview(monkeypatch):
    panel, icon, *_ = make_sandbox(monkeypatch)
    assert panel.show_about() is False
    labels = [item.text for item in icon.menu if hasattr(item, "text")
              and isinstance(item.text, str)]
    assert any("Notro" in label or "정보" in label for label in labels)
    assert "종료" in labels
