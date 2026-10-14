"""Safety regression tests for OS-level paste and optional Discord auto-send.

All window identity and paste calls are mocks; never interact with live chat.
"""
from __future__ import annotations

from types import SimpleNamespace
import time

import pytest

from notro_app import clipboard_win as cb
from notro_app.picker import window


class FakeLibrary:
    def __init__(self):
        self.used = []
        self.item = {"id": "fixture", "type": "emoji", "source_url": ""}

    def resolve(self, item_id):
        return self.item if item_id == "fixture" else None

    def asset_path(self, item):
        return "C:\\fixture\\emoji.png"

    def touch(self, item_id):
        self.used.append(item_id)


def prepare(monkeypatch, *, autosend, target_is_discord, focused=(True, True),
            focus_restore=True, clipboard_ok=True):
    lib = FakeLibrary()
    picker = window.PickerController(library=lib)
    picker.prev_hwnd = 4242
    picker.window = SimpleNamespace(hide=lambda: None)
    monkeypatch.setattr(picker, "_remember_size", lambda: None)
    monkeypatch.setattr(window, "prepare_for_paste",
                        lambda *args, **kwargs: ("C:\\fixture\\emoji.png", False))
    monkeypatch.setattr(window.config, "get_setting_flag",
                        lambda key: autosend if key == "auto_send" else False)
    monkeypatch.setattr(window, "auto_send_delay", lambda: 0.1)
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setattr(cb, "set_clipboard_file", lambda *_: clipboard_ok)
    monkeypatch.setattr(cb, "focus_window", lambda hwnd: focus_restore)
    focused_state = iter(focused)
    monkeypatch.setattr(cb, "is_window_focused",
                        lambda hwnd: next(focused_state))
    monkeypatch.setattr(cb, "is_discord_desktop_window",
                        lambda hwnd: target_is_discord)
    calls = []
    msgs = []
    picker.on_notify = msgs.append
    monkeypatch.setattr(cb, "send_ctrl_v", lambda: calls.append("paste"))
    monkeypatch.setattr(cb, "send_enter", lambda: calls.append("send"))
    return picker, lib, calls, msgs


@pytest.mark.parametrize("app,allowed", [
    ("Discord.exe", True),
    ("DiscordPTB.exe", True),
    ("DiscordCanary.exe", True),
    ("DISCORD.EXE", True),
    ("chrome.exe", False),
    ("Discord.exe.bak", False),
    ("", False),
])
def test_auto_send_process_allowlist(monkeypatch, app, allowed):
    monkeypatch.setattr(cb, "window_process_name", lambda hwnd: app.casefold())
    assert cb.is_discord_desktop_window(77) is allowed


def test_select_pastes_and_auto_sends_if_discord_keeps_focus(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True)
    picker.select("fixture")
    assert calls == ["paste", "send"]
    assert lib.used == ["fixture"]
    assert not msgs


def test_select_does_not_paste_into_a_newly_focused_window(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True,
        focused=(False,))
    picker.select("fixture")
    assert calls == []
    assert lib.used == []
    assert msgs


def test_auto_send_does_not_enter_after_focus_switch(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True,
        focused=(True, False))
    picker.select("fixture")
    assert calls == ["paste"]
    assert lib.used == ["fixture"]
    assert msgs and "window" in msgs[0].lower() or "창" in msgs[0]


def test_auto_send_never_sends_in_other_application(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=False, focused=(True,))
    picker.select("fixture")
    assert calls == ["paste"]
    assert lib.used == ["fixture"]
    assert msgs


def test_auto_send_off_pastes_without_sending(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=False, target_is_discord=True, focused=(True,))
    picker.select("fixture")
    assert calls == ["paste"]
    assert lib.used == ["fixture"]
    assert not msgs


def test_focus_restore_failure_keeps_clipboard_for_manual_paste(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True, focus_restore=False,
        focused=())
    picker.select("fixture")
    assert calls == []
    assert lib.used == []
    assert msgs


def test_clipboard_failure_never_pastes(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True,
        clipboard_ok=False, focused=())
    picker.select("fixture")
    assert calls == []
    assert lib.used == []
    assert msgs


def test_link_mode_pastes_but_never_auto_sends(monkeypatch):
    picker, lib, calls, msgs = prepare(
        monkeypatch, autosend=True, target_is_discord=True, focused=(True,))
    picker.library.item["source_url"] = "https://cdn.discordapp.com/emojis/123.png"
    monkeypatch.setattr(cb, "set_clipboard_text", lambda *_: True)
    picker.select("fixture", mode="url")
    assert calls == ["paste"]
    assert lib.used == ["fixture"]
    assert not msgs
