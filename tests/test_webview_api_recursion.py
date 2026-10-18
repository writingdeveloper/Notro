"""Prevent recursive pywebview JS bridge discovery on native WinForms.

Only explicitly exposed API methods may cross Python->JS. A public
window object recursively exposes WinForms AccessibilityObject and has
been observed to hang the welcome and video dialogs in real WebView2.
"""
from __future__ import annotations

from notro_app import video_window, welcome


class OwnedFakeWindow:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def test_welcome_bridge_only_contains_private_native_window():
    invoked = []
    api = welcome._Api(on_try=lambda: invoked.append("picker"))
    assert "window" not in vars(api)
    assert "_window" in vars(api)
    fake = OwnedFakeWindow()
    api._window = fake
    api.open_picker()
    assert fake.destroyed
    assert invoked == ["picker"]


def test_welcome_dismiss_only_closes_without_opening_picker():
    invoked = []
    api = welcome._Api(on_try=lambda: invoked.append("picker"))
    fake = OwnedFakeWindow()
    api._window = fake
    api.close()
    assert fake.destroyed
    assert invoked == []


def test_video_bridge_exposes_only_primitives_and_methods_not_winforms():
    window = video_window.VideoWindow(
        "Private QA", "5s · 720p", "estimated 2MB", None,
        "Confirm", trim=True
    )
    api = window._api
    assert "window" not in vars(api)
    assert "_window" in vars(api)
    assert api.choice == ("", "", False)
    dummy = OwnedFakeWindow()
    api._window = dummy
    api.cancel()
    assert dummy.destroyed
    assert window.cancelled.is_set()
    assert not window.accepted.is_set()


def test_video_confirm_retains_explicit_trim_and_mute_choice():
    window = video_window.VideoWindow(
        "Private QA", "5s · 720p", "estimated 2MB", None,
        "Confirm", trim=True,
        on_replan=lambda start, end, mute: {
            "ok": True, "estimate": "trimmed",
            "values": (start, end, mute),
        },
    )
    response = window._api.replan("0:01", "0:03", True)
    assert response["ok"] is True
    assert response["values"] == ("0:01", "0:03", True)
    window._api.accept("0:01", "0:03", True)
    assert window.accepted.is_set()
    assert not window.cancelled.is_set()
    assert window.choice == ("0:01", "0:03", True)
