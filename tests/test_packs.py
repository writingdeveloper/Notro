"""Portable pack export/import; no Discord client or clipboard required."""
import hashlib
import io
import json
import zipfile

import pytest
from PIL import Image

from notro_app import fetch, packs
from notro_app.capture_store import CAPTURE_COLLECTION_ID
from notro_app.library import Library


def image_file(tmp_path, name="p.png"):
    p = tmp_path / name
    Image.new("RGB", (20, 20), (60, 100, 140)).save(p)
    return p


def test_pack_round_trip_merges_without_duplicates_or_private_captures(tmp_path):
    origin = Library(str(tmp_path / "old"))
    src = image_file(tmp_path)
    original = fetch.register_from_file(
        origin, str(src), "emoji", name="hello", keywords=["wave"],
        collection="friends")
    fetch.register_from_file(
        origin, str(src), "emoji", name="private",
        collection=CAPTURE_COLLECTION_ID)
    pack = tmp_path / "pack.zip"
    result = packs.export_pack(origin, str(pack))
    assert result["count"] == 1

    with zipfile.ZipFile(pack) as z:
        names = z.namelist()
        assert set(names) == {"manifest.json", "assets/00001.png"}
        manifest = json.loads(z.read("manifest.json"))
        assert len(manifest["items"]) == 1
        assert manifest["items"][0]["name"] == "hello"
        assert manifest["items"][0]["keywords"] == ["wave"]
        assert "source_url" not in manifest["items"][0]
        assert "private" not in str(manifest)

    dst = Library(str(tmp_path / "new"))
    assert packs.import_pack(dst, str(pack)) == {
        "added": 1, "duplicate": 0, "failed": 0,
    }
    assert packs.import_pack(dst, str(pack)) == {
        "added": 0, "duplicate": 1, "failed": 0,
    }
    assert len(dst.items()) == 1
    assert dst.items()[0]["collection"] == "friends"
    assert dst.items()[0]["name"] == original["name"]
    assert dst.items()[0]["keywords"] == original["keywords"]


def _crafted_pack(path, file="assets/00001.png", data=None, sha=None,
                  collection="friends", extra=None):
    if data is None:
        buf = io.BytesIO()
        Image.new("RGB", (5, 5), (25, 50, 75)).save(buf, format="PNG")
        data = buf.getvalue()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(file, data)
        if extra:
            z.writestr(extra, b"junk")
        z.writestr("manifest.json", json.dumps({
            "format": "notro-media-pack", "version": 1,
            "items": [{
                "file": file, "name": "safe", "type": "emoji",
                "keywords": [], "collection": collection,
                "sha256": sha or hashlib.sha256(data).hexdigest(),
            }],
        }))


@pytest.mark.parametrize("bad_path", [
    "../assets/00001.png", "assets/../../bad.png", "/assets/00001.png",
    "assets/private.txt",
])
def test_rejects_zip_path_traversal_and_unapproved_entries(tmp_path, bad_path):
    lib = Library(str(tmp_path / "app"))
    archive = tmp_path / "malformed.zip"
    _crafted_pack(archive, file=bad_path)
    with pytest.raises(packs.PackError):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_rejects_extra_zip_member_without_extracting(tmp_path):
    lib = Library(str(tmp_path / "app"))
    archive = tmp_path / "malformed.zip"
    _crafted_pack(archive, extra="assets/not-listed.png")
    with pytest.raises(packs.PackError, match="unrecognized|extra"):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_rejects_corrupt_media_before_any_registration(tmp_path):
    lib = Library(str(tmp_path / "app"))
    archive = tmp_path / "corrupted.zip"
    _crafted_pack(archive, sha="0" * 64)
    with pytest.raises(packs.PackError, match="SHA-256"):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_rejects_unsafe_collection(tmp_path):
    lib = Library(str(tmp_path / "app"))
    archive = tmp_path / "unsafe.zip"
    _crafted_pack(archive, collection="..")
    with pytest.raises(packs.PackError, match="unsafe"):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_rejects_fake_png(tmp_path):
    lib = Library(str(tmp_path / "app"))
    archive = tmp_path / "fake.zip"
    _crafted_pack(archive, data=b"not a png", sha=hashlib.sha256(b"not a png").hexdigest())
    with pytest.raises(packs.PackError, match="invalid image"):
        packs.import_pack(lib, str(archive))
    assert lib.items() == []


def test_picker_api_pack_dialog_round_trip(tmp_path):
    """The actual Python UI bridge exposes explicit import/export dialogs."""
    from types import SimpleNamespace
    from notro_app.picker.window import PickerApi

    src = Library(str(tmp_path / "pack-source"))
    fetch.register_from_file(src, str(image_file(tmp_path)), "emoji", name="example")
    archive = tmp_path / "bridge.zip"
    class FakeWindow:
        def __init__(self, selection):
            self.selection = selection
        def create_file_dialog(self, *args, **kwargs):
            return [str(self.selection)]

    api = PickerApi(library=src)
    api._ctrl = SimpleNamespace(window=FakeWindow(archive))
    assert api.export_pack() == {"ok": True, "count": 1}
    assert archive.exists()

    dest = Library(str(tmp_path / "pack-target"))
    api2 = PickerApi(library=dest)
    api2._ctrl = SimpleNamespace(window=FakeWindow(archive))
    assert api2.import_pack() == {"ok": True, "added": 1, "duplicate": 0, "failed": 0}
    assert dest.items()[0]["name"] == "example"


def test_cancel_pack_dialog_is_noop(tmp_path):
    from types import SimpleNamespace
    from notro_app.picker.window import PickerApi

    lib = Library(str(tmp_path / "nothing"))
    window = SimpleNamespace(create_file_dialog=lambda *a, **kw: None)
    api = PickerApi(library=lib)
    api._ctrl = SimpleNamespace(window=window)
    assert api.export_pack() == {"ok": False, "error": "cancelled"}
    assert api.import_pack() == {"ok": False, "error": "cancelled"}
    assert lib.items() == []

def test_drag_drop_pack_reuses_same_safe_import_bridge(tmp_path):
    """A manually dropped ZIP uses the importer; arbitrary archives still fail."""
    from notro_app.picker.window import PickerApi

    origin = Library(str(tmp_path / "origin"))
    fetch.register_from_file(origin, str(image_file(tmp_path)), "emoji")
    pack_path = tmp_path / "my-pack.zip"
    packs.export_pack(origin, str(pack_path))
    target = Library(str(tmp_path / "target"))
    api = PickerApi(library=target)
    assert api.import_pack_path(str(pack_path)) == {
        "ok": True, "added": 1, "duplicate": 0, "failed": 0,
    }
    assert len(target.items()) == 1
    assert api.import_pack_path(str(pack_path))["duplicate"] == 1
    assert api.import_pack_path(str(tmp_path / "not-a-pack.txt")) == {
        "ok": False, "error": "pack",
    }


def test_dialog_type_prefers_modern_enum_without_touching_deprecated_alias():
    from types import SimpleNamespace
    from notro_app.picker.window import _native_dialog_kind

    class ModernOnly:
        FileDialog = SimpleNamespace(OPEN=10, SAVE=30, FOLDER=20)

        def __getattr__(self, key):
            raise AssertionError("unexpected deprecated enum attribute: " + key)

    m = ModernOnly()
    assert _native_dialog_kind("OPEN", m) == 10
    assert _native_dialog_kind("SAVE", m) == 30
    assert _native_dialog_kind("FOLDER", m) == 20


def test_dialog_type_accepts_old_pywebview_without_modern_enum():
    from types import SimpleNamespace
    from notro_app.picker.window import _native_dialog_kind

    legacy = SimpleNamespace(OPEN_DIALOG=10, SAVE_DIALOG=30, FOLDER_DIALOG=20)
    for name, value in (("OPEN", 10), ("SAVE", 30), ("FOLDER", 20)):
        assert _native_dialog_kind(name, legacy) == value
