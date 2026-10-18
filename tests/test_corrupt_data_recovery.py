"""Untrusted malformed library/ZIP/preferences files must fail closed.

All fixtures live in tmp_path: never read or write the user's Notro library,
clipboard, registry or Discord process.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from notro_app import packs, settings_backup
from notro_app.library import Library


def make_pack(path: Path, patch: dict | None = None) -> Path:
    content = io.BytesIO()
    Image.new("RGB", (8, 8), "#87bdff").save(content, format="PNG")
    data = content.getvalue()
    item = {
        "file": "assets/00001.png",
        "name": "Synthetic safe PNG",
        "type": "emoji",
        "keywords": [],
        "collection": "public",
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    item.update(patch or {})
    manifest = {"format": "notro-media-pack", "version": 1, "items": [item]}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr(item["file"], data)
    return path


@pytest.mark.parametrize("bad_kind", [[], {}, ["gif"], {"x": "y"}, 100, None])
def test_malformed_media_pack_kind_fails_closed(tmp_path, bad_kind):
    lib = Library(str(tmp_path / "target"))
    original = make_pack(tmp_path / "malformed.zip", {"type": bad_kind})
    with pytest.raises(packs.PackError):
        packs.import_pack(lib, str(original))
    assert lib.items() == []
    assert not list(Path(lib.assets_dir).rglob("*.png"))


@pytest.mark.parametrize("raw", [b"", b"not a zip", b"PK\x03\x04" + b"oops" * 18])
def test_invalid_zip_archive_is_a_safe_pack_error(tmp_path, raw):
    lib = Library(str(tmp_path / "target"))
    archive = tmp_path / "invalid.zip"
    archive.write_bytes(raw)
    with pytest.raises(packs.PackError):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_oversized_sparse_zip_rejected_without_parsing(tmp_path):
    lib = Library(str(tmp_path / "target"))
    archive = tmp_path / "oversized.zip"
    with archive.open("wb") as stream:
        stream.truncate(packs.MAX_TOTAL_SIZE + 17 * 1024 * 1024)
    with pytest.raises(packs.PackError):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


@pytest.mark.parametrize("bad_kind", [[], {}, ["gif"], {"x": "y"}, None, 5])
def test_malformed_settings_folder_kind_does_not_crash_or_restore(
        tmp_path, bad_kind):
    lib = Library(str(tmp_path / "target"))
    settings = {
        "format": "notro-settings",
        "version": 1,
        "settings": {"lang": "ko"},
        "watched_folders": [{
            "path": str(tmp_path),
            "default_type": bad_kind,
        }],
    }
    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(settings), encoding="utf-8")
    with pytest.raises(settings_backup.SettingsBackupError):
        settings_backup.preview_settings(str(path))
    assert lib.folders() == []
    assert lib.items() == []


@pytest.mark.parametrize("payload", [
    [],
    7,
    {"items": {"not": "a list"}},
    {"items": [None]},
    {"items": ["bad entry"]},
    {"items": [{"id": "x", "type": "emoji", "filename": []}]},
    {"items": [{"id": "x", "type": "emoji", "filename": "../escape.png"}]},
])
def test_malformed_library_json_is_backed_up_and_does_not_crash_start(
        tmp_path, payload):
    data_dir = tmp_path / "local"
    data_dir.mkdir()
    filename = data_dir / "library.json"
    raw = json.dumps(payload, ensure_ascii=False)
    filename.write_text(raw, encoding="utf-8")
    library = Library(str(data_dir))
    assert library.items() == []
    backup = data_dir / "library.json.bak"
    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == raw
    assert not filename.exists()


@pytest.mark.parametrize("payload", [
    [],
    "bad",
    {"folders": {"path": "bad"}},
    {"folders": [None]},
    {"folders": [{"path": [], "default_type": "emoji"}]},
])
def test_malformed_watched_folders_json_is_backed_up(tmp_path, payload):
    lib = Library(str(tmp_path / "target"))
    path = Path(lib.data_dir) / "folders.json"
    raw = json.dumps(payload, ensure_ascii=False)
    path.write_text(raw, encoding="utf-8")
    recovered = Library(lib.data_dir)
    assert recovered.folders() == []
    assert (path.with_name("folders.json.bak")).read_text(
        encoding="utf-8") == raw
    assert not path.exists()
