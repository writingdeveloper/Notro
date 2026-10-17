"""Standalone preferences backup: privacy, explicit restore and malformed-input guards."""
import json

import pytest

from notro_app import settings_backup as backup
from notro_app.library import Library

SNAPSHOT = {
    "limit_mb": 20, "auto_update": 1,
    "paste_px_emoji": 48, "paste_px_sticker": 160, "paste_px_gif": 0,
    "picker_w": 500, "picker_h": 420,
    "lang": "ko", "hotkey": "ctrl+shift+e",
    "auto_send": True, "auto_capture_save": True,
}


def make_profile(tmp_path, *, include_folders=False):
    lib = Library(str(tmp_path / "profile"))
    external = tmp_path / "watched 폴더"
    external.mkdir()
    lib.add_folder(str(external), "gif")
    destination = tmp_path / "settings.json"
    backup.export_settings(lib, str(destination),
                           include_folders=include_folders, snapshot=SNAPSHOT)
    return lib, external, destination


def test_export_defaults_exclude_private_watched_paths(tmp_path):
    _, external, source = make_profile(tmp_path)
    raw = source.read_text(encoding="utf-8")
    assert str(external) not in raw
    assert "Discord" not in raw and "source_url" not in raw
    assert "watched_folders" in raw and '"watched_folders": []' in raw
    assert "auto_send" in raw  # disclosed value, import safety locks it OFF


def test_preview_is_read_only_and_requires_explicit_apply(tmp_path):
    _, _, source = make_profile(tmp_path)
    doc, checksum = backup.preview_settings(str(source))
    assert len(checksum) == 64
    assert doc["settings"]["lang"] == "ko"
    assert doc["watched_folders"] == []
    assert source.exists()


def test_apply_restores_only_safe_preferences_and_disables_auto_send(tmp_path):
    _, _, source = make_profile(tmp_path)
    dest = Library(str(tmp_path / "restored"))
    doc, _ = backup.preview_settings(str(source))
    ints, strings = {}, {}
    result = backup.apply_settings(
        doc, dest, write_int=lambda k, v: ints.__setitem__(k, v),
        write_str=lambda k, v: strings.__setitem__(k, v),
    )
    assert ints["limit_mb"] == 20 and ints["paste_px_gif"] == 0
    assert ints["auto_send"] == 0 and ints["auto_capture_save"] == 0
    assert strings == {"lang": "ko", "hotkey": "ctrl+shift+e"}
    assert result["applied"] == len(SNAPSHOT) - 2
    assert result["restart_required"]
    assert dest.items() == [] and dest.folders() == []


def test_opt_in_paths_restore_only_existing_folders_without_duplication(tmp_path):
    _, external, source = make_profile(tmp_path, include_folders=True)
    doc, _ = backup.preview_settings(str(source))
    assert doc["watched_folders"] == [{"path": str(external), "default_type": "gif"}]
    dst = Library(str(tmp_path / "restored"))
    sink = {}
    def noop(k, v):
        sink[k] = v
    disabled = backup.apply_settings(doc, dst, restore_folders=False,
                                     write_int=noop, write_str=noop)
    assert disabled["folders_added"] == 0 and dst.folders() == []
    restored = backup.apply_settings(doc, dst, restore_folders=True,
                                     write_int=noop, write_str=noop)
    assert restored["folders_added"] == 1 and dst.folders()[0]["path"] == str(external)
    second = backup.apply_settings(doc, dst, restore_folders=True,
                                   write_int=noop, write_str=noop)
    assert second["folders_added"] == 0
    external.rmdir()
    third_dst = Library(str(tmp_path / "missing-target"))
    missing = backup.apply_settings(doc, third_dst, restore_folders=True,
                                    write_int=noop, write_str=noop)
    assert missing["folders_missing"] == 1
    assert third_dst.folders() == []


@pytest.mark.parametrize("key,value", [
    ("limit_mb", -1), ("limit_mb", 5), ("limit_mb", 1025),
    ("lang", "unsupported"), ("picker_w", 99),
    ("hotkey", "enter"), ("auto_send", 1), ("auto_capture_save", "yes"),
])
def test_rejects_invalid_settings_before_writing(tmp_path, key, value):
    _, _, source = make_profile(tmp_path)
    obj = json.loads(source.read_text(encoding="utf-8"))
    obj["settings"][key] = value
    source.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(backup.SettingsBackupError):
        backup.preview_settings(str(source))


@pytest.mark.parametrize("malformed", [
    {"format": "notro-settings", "version": 999, "settings": {}, "watched_folders": []},
    {"format": "notro-settings", "version": 1, "settings": {"new_secret": "X"},
     "watched_folders": []},
    {"format": "notro-settings", "version": 1, "settings": {"limit_mb": 20},
     "watched_folders": [{"path": "relative\\secret", "default_type": "gif"}]},
    {"format": "notro-settings", "version": 1, "settings": {"limit_mb": 20},
     "watched_folders": [{"path": "C:\\something", "default_type": "exe"}]},
])
def test_rejects_untrusted_docs(tmp_path, malformed):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(backup.SettingsBackupError):
        backup.preview_settings(str(path))


def test_rejects_oversized_data_before_json_decode(tmp_path):
    file = tmp_path / "too-big.json"
    with file.open("wb") as f:
        f.truncate(backup.MAX_BYTES + 1)
    with pytest.raises(backup.SettingsBackupError, match="too_large"):
        backup.preview_settings(str(file))


def test_export_is_validated_before_file_creation(tmp_path):
    lib = Library(str(tmp_path / "lib"))
    with pytest.raises(backup.SettingsBackupError):
        backup.export_settings(lib, str(tmp_path / "bad.json"),
                               snapshot={"auto_send": "yes"})
    assert not (tmp_path / "bad.json").exists()


def test_mismatched_extension_and_bad_json_are_rejected(tmp_path):
    path = tmp_path / "bad.zip"
    path.write_text("not a profile", encoding="utf-8")
    with pytest.raises(backup.SettingsBackupError):
        backup.preview_settings(str(path))
    bad = tmp_path / "bad.json"
    bad.write_text("{fail", encoding="utf-8")
    with pytest.raises(backup.SettingsBackupError, match="invalid_json"):
        backup.preview_settings(str(bad))


def test_settings_backup_preserves_optional_one_gigabyte_limit(tmp_path):
    lib = Library(str(tmp_path / "library"))
    destination = tmp_path / "nitro-profile.json"
    values = dict(SNAPSHOT, limit_mb=1024)
    backup.export_settings(lib, str(destination), snapshot=values)
    restored, _ = backup.preview_settings(str(destination))
    assert restored["settings"]["limit_mb"] == 1024
