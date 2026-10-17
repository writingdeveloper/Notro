"""Picker bridge must require explicit review before settings restoration."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from notro_app import config, settings_backup
from notro_app.library import Library
from notro_app.picker.window import PickerApi


class FakeDialog:
    def __init__(self, path):
        self.selected = path
        self.kinds = []

    def create_file_dialog(self, kind, **kwargs):
        self.kinds.append((kind, kwargs))
        return [str(self.selected)] if self.selected else None


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    source = Library(str(tmp_path / "source"))
    watched = tmp_path / "directory"
    watched.mkdir()
    source.add_folder(str(watched), "gif")
    target = Library(str(tmp_path / "target"))
    path = tmp_path / "portable.json"
    fake_settings = {
        "limit_mb": 20, "paste_px_emoji": 48, "auto_update": 1,
        "lang": "ko", "hotkey": "ctrl+shift+e",
        "auto_send": True, "auto_capture_save": True,
    }
    monkeypatch.setattr(settings_backup, "_settings_snapshot",
                        lambda: fake_settings)
    original = {}
    monkeypatch.setattr(config, "set_setting_int",
                        lambda name, value: original.__setitem__(name, value))
    monkeypatch.setattr(config, "set_setting_str",
                        lambda name, value: original.__setitem__(name, value))
    dialog = FakeDialog(path)
    source_api = PickerApi(library=source)
    source_api._ctrl = SimpleNamespace(window=dialog)
    target_api = PickerApi(library=target)
    target_api._ctrl = SimpleNamespace(window=dialog)
    return source_api, target_api, target, watched, path, original, dialog


def test_export_default_private_and_import_requires_review_and_approval(sandbox):
    source, api, target, watched, path, writes, _ = sandbox
    assert source.export_preferences() == {
        "ok": True, "settings_count": 7, "folders_count": 0}
    assert json.loads(path.read_text(encoding="utf-8"))["watched_folders"] == []
    assert writes == {}
    review = api.preview_preferences()
    assert review["ok"] and review["settings_count"] == 7
    assert review["folders_count"] == 0
    assert writes == {} and target.folders() == []
    assert api.apply_preferences("invalid-token") == {
        "ok": False, "error": "outdated"}
    assert writes == {}
    review = api.preview_preferences()
    result = api.apply_preferences(review["token"])
    assert result["ok"] is True
    assert writes["lang"] == "ko"
    assert writes["auto_send"] == 0 and writes["auto_capture_save"] == 0
    assert result["restart_required"] and target.items() == []


def test_opt_in_watched_folder_path_restore(sandbox):
    source, api, target, watched, path, writes, _ = sandbox
    assert source.export_preferences(True)["folders_count"] == 1
    assert json.loads(path.read_text(encoding="utf-8"))["watched_folders"][0]["path"] == str(watched)
    review = api.preview_preferences()
    assert review["folders_count"] == 1
    assert target.folders() == [] and writes == {}
    assert api.apply_preferences(review["token"], True)["folders_added"] == 1
    assert target.folders() == [{"path": str(watched), "default_type": "gif"}]


def test_cancel_review_clears_permission_without_mutation(sandbox):
    source, api, target, _, _, writes, _ = sandbox
    source.export_preferences()
    review = api.preview_preferences()
    assert api.discard_preferences_preview(review["token"])
    assert not api.discard_preferences_preview(review["token"])
    assert api.apply_preferences(review["token"]) == {
        "ok": False, "error": "outdated"}
    assert writes == {} and target.folders() == []


def test_modified_file_between_review_and_apply_refused(sandbox):
    source, api, target, _, path, writes, _ = sandbox
    source.export_preferences()
    review = api.preview_preferences()
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert api.apply_preferences(review["token"]) == {
        "ok": False, "error": "outdated"}
    assert not writes and target.items() == []


def test_cancel_or_invalid_dialog_does_not_write(sandbox):
    source, api, target, _, path, writes, dlg = sandbox
    dlg.selected = None
    assert source.export_preferences() == {
        "ok": False, "error": "cancelled"}
    assert api.preview_preferences() == {
        "ok": False, "error": "cancelled"}
    assert not path.exists() and writes == {} and not target.items()
    dlg.selected = path
    path.write_text("{not valid", encoding="utf-8")
    assert api.preview_preferences() == {"ok": False, "error": "settings"}
