"""Library: JSON 영속·CRUD·recent·폴더 스캔 (순수 파일시스템 — tmp_path)."""

import os
import time

import pytest
from PIL import Image

from notro_app.library import Library, SUPPORTED_EXTS


def make_lib(tmp_path):
    return Library(str(tmp_path / "data"))


def put_asset(lib, name="a.png", collection=""):
    from notro_app.library import _slug
    d = os.path.join(lib.assets_dir, _slug(collection))
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    Image.new("RGB", (4, 4), (255, 0, 0)).save(p)
    return name


def make_lib_at(data_dir):
    from notro_app.library import Library
    return Library(data_dir)


def test_supported_exts_contract():
    assert set(SUPPORTED_EXTS) == {".png", ".gif", ".webp"}


def test_add_get_persist_roundtrip(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib)
    item = lib.add_item("emoji", "smile", ["happy"], "discord-cdn",
                        "https://cdn.discordapp.com/emojis/1.png", fn, False)
    assert item["id"] and item["use_count"] == 0
    lib2 = Library(lib.data_dir)  # 재로드
    got = lib2.get(item["id"])
    assert got["name"] == "smile" and got["keywords"] == ["happy"]


def test_remove_item_deletes_asset(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib)
    item = lib.add_item("gif", "g", [], "local", "", fn, True)
    path = lib.asset_path(item)
    assert os.path.exists(path)
    lib.remove_item(item["id"])
    assert not os.path.exists(path)
    assert lib.get(item["id"]) is None


def test_touch_updates_recent_order(tmp_path):
    lib = make_lib(tmp_path)
    a = lib.add_item("emoji", "a", [], "local", "", put_asset(lib, "a.png"), False)
    b = lib.add_item("emoji", "b", [], "local", "", put_asset(lib, "b.png"), False)
    lib.touch(a["id"])
    time.sleep(0.01)
    lib.touch(b["id"])
    rec = lib.recent()
    assert [i["name"] for i in rec[:2]] == ["b", "a"]
    assert lib.get(a["id"])["use_count"] == 1


def test_recent_excludes_never_used(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "never", [], "local", "", put_asset(lib), False)
    assert lib.recent() == []


def test_folder_scan_lists_supported_exts_only(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "gifs"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "x.png")
    Image.new("RGB", (4, 4)).save(folder / "y.gif")
    (folder / "note.txt").write_text("no")
    lib.add_folder(str(folder), "gif")
    items = lib.scan_folders()
    names = sorted(i["name"] for i in items)
    assert names == ["x", "y"]
    gif = next(i for i in items if i["name"] == "y")
    assert gif["id"].startswith("folder:") and gif["animated"] is True
    assert os.path.samefile(lib.asset_path(gif), folder / "y.gif")


def test_folder_scan_missing_folder_is_skipped(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_folder(str(tmp_path / "ghost"), "gif")
    assert lib.scan_folders() == []


def test_folder_scan_cache_invalidates_on_new_file(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "f"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "1.png")
    lib.add_folder(str(folder), "sticker")
    assert len(lib.scan_folders()) == 1
    Image.new("RGB", (4, 4)).save(folder / "2.png")
    assert len(lib.scan_folders()) == 2


def test_corrupt_json_recovers_empty(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "a", [], "local", "", put_asset(lib), False)
    with open(os.path.join(lib.data_dir, "library.json"), "w") as f:
        f.write("{broken")
    lib2 = Library(lib.data_dir)
    assert lib2.items() == []
    assert os.path.exists(os.path.join(lib.data_dir, "library.json.bak"))


def test_all_display_items_merges(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "reg", [], "local", "", put_asset(lib), False)
    folder = tmp_path / "f"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "z.webp")
    lib.add_folder(str(folder), "gif")
    kinds = {i["source_kind"] for i in lib.all_display_items()}
    assert kinds == {"local", "folder"}


def test_touch_folder_item_is_noop(tmp_path):
    lib = make_lib(tmp_path)
    lib.touch("folder:C:/nope/x.gif")  # 예외 없이 무시


def test_remove_folder_stops_scanning(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "f"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "1.png")
    lib.add_folder(str(folder), "gif")
    assert len(lib.scan_folders()) == 1
    lib.remove_folder(str(folder))
    assert lib.scan_folders() == []
    assert lib.folders() == []


# ---------- search (스펙 §3: 검색 책임은 library.py) ----------
def test_search_matches_name(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "smile", [], "local", "", put_asset(lib, "a.png"), False)
    lib.add_item("emoji", "frown", [], "local", "", put_asset(lib, "b.png"), False)
    assert [i["name"] for i in lib.search("smi")] == ["smile"]


def test_search_matches_keyword(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "a", ["happy", "joy"], "local", "",
                 put_asset(lib, "a.png"), False)
    lib.add_item("emoji", "b", ["sad"], "local", "", put_asset(lib, "b.png"), False)
    assert [i["name"] for i in lib.search("joy")] == ["a"]


def test_search_is_case_insensitive(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "Smile", ["Happy"], "local", "",
                 put_asset(lib, "a.png"), False)
    assert [i["name"] for i in lib.search("smile")] == ["Smile"]
    assert [i["name"] for i in lib.search("HAP")] == ["Smile"]


def test_search_empty_query_returns_all(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "a", [], "local", "", put_asset(lib, "a.png"), False)
    folder = tmp_path / "f"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "z.gif")
    lib.add_folder(str(folder), "gif")
    assert len(lib.search("")) == 2  # all_display_items() 전체
    assert len(lib.search("   ")) == 2  # 공백만인 쿼리도 빈 쿼리로 취급


def test_search_type_filter(tmp_path):
    lib = make_lib(tmp_path)
    lib.add_item("emoji", "e", ["x"], "local", "", put_asset(lib, "a.png"), False)
    lib.add_item("gif", "g", ["x"], "local", "", put_asset(lib, "b.png"), False)
    assert [i["name"] for i in lib.search("", "emoji")] == ["e"]  # 빈 쿼리 + 타입
    assert [i["name"] for i in lib.search("x", "gif")] == ["g"]  # 쿼리 + 타입 동시


# ---------- favorites / collections (v2.4) ----------
def test_toggle_favorite_and_list(tmp_path):
    lib = make_lib(tmp_path)
    it = lib.add_item("emoji", "a", [], "local", "", put_asset(lib, "a.png"), False)
    assert lib.toggle_favorite(it["id"]) is True
    assert [i["id"] for i in lib.favorites()] == [it["id"]]
    assert lib.toggle_favorite(it["id"]) is False
    assert lib.favorites() == []


def test_apply_lib_backfills_new_fields(tmp_path):
    from notro_app.library import Library
    lib = make_lib(tmp_path)
    it = lib.add_item("emoji", "a", [], "local", "", put_asset(lib, "a.png"), False)
    del it["favorite"]
    del it["collection"]
    lib._save()
    lib2 = Library(lib.data_dir)
    r = lib2.get(it["id"])
    assert r["favorite"] is False and r["collection"] == ""


def test_content_hash_persists_and_is_searchable(tmp_path):
    """해시 필드나 타입·컬렉션 필터가 빠지는 회귀를 잡는다."""
    lib = make_lib(tmp_path)
    item = lib.add_item(
        "emoji", "cap", [], "local", "",
        put_asset(lib, "cap.png", "__notro_captures__"), False,
        collection="__notro_captures__", content_hash="abc123")

    lib2 = Library(lib.data_dir)
    found = lib2.find_by_content_hash(
        "abc123", "emoji", "__notro_captures__")

    assert lib2.get(item["id"])["content_hash"] == "abc123"
    assert found["id"] == item["id"]
    assert lib2.find_by_content_hash(
        "abc123", "sticker", "__notro_captures__") is None


def test_apply_lib_backfills_content_hash(tmp_path):
    """구버전 library.json에서 신규 필드 KeyError가 나는 회귀를 잡는다."""
    lib = make_lib(tmp_path)
    item = lib.add_item(
        "emoji", "old", [], "local", "", put_asset(lib), False)
    item.pop("content_hash", None)
    lib._save()

    assert Library(lib.data_dir).get(item["id"])["content_hash"] == ""


def test_add_item_rolls_back_memory_when_save_fails(tmp_path, monkeypatch):
    """JSON 저장 실패 후 메모리에 유령 항목이 남는 회귀를 잡는다."""
    lib = make_lib(tmp_path)
    monkeypatch.setattr(
        lib, "_save", lambda: (_ for _ in ()).throw(OSError("disk")))

    with pytest.raises(OSError):
        lib.add_item("emoji", "x", [], "local", "", "x.png", False)

    assert lib.items() == []


def test_set_collection_moves_file_on_disk(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False)
    old_path = lib.asset_path(item)
    assert os.path.exists(old_path)

    lib.set_collection(item["id"], "miku")

    new_path = lib.asset_path(lib.get(item["id"]))
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)
    assert "miku" in new_path


def test_set_collection_move_failure_leaves_state_unchanged(tmp_path, monkeypatch):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False)
    old_path = lib.asset_path(item)

    def boom(*a, **k):
        raise OSError("locked")
    monkeypatch.setattr(os, "replace", boom)

    lib.set_collection(item["id"], "miku")

    assert lib.get(item["id"])["collection"] == ""
    assert os.path.exists(old_path)


def test_set_collection_noop_when_same_name(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png", "miku")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False, collection="miku")
    old_path = lib.asset_path(item)
    lib.set_collection(item["id"], "miku")
    assert lib.asset_path(lib.get(item["id"])) == old_path
    assert os.path.exists(old_path)


def test_set_collection_and_list(tmp_path):
    lib = make_lib(tmp_path)
    a = lib.add_item("emoji", "a", ["miku"], "local", "", put_asset(lib, "a.png"), False)
    lib.add_item("emoji", "b", [], "local", "", put_asset(lib, "b.png"), False)
    lib.set_collection(a["id"], "miku")
    assert lib.get(a["id"])["collection"] == "miku"
    assert "miku" in lib.collections()


def test_remove_item_deletes_asset_in_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "g.gif", "miku")
    item = lib.add_item("gif", "g", [], "local", "", fn, True, collection="miku")
    path = lib.asset_path(item)
    assert os.path.exists(path)
    lib.remove_item(item["id"])
    assert not os.path.exists(path)


def test_migration_moves_flat_legacy_files_on_load(tmp_path):
    d = str(tmp_path / "data")
    lib = make_lib_at(d)
    fn = put_asset(lib, "old.png", "miku")
    item = lib.add_item("emoji", "old", [], "local", "", fn, False, collection="miku")
    nested = lib.asset_path(item)
    flat = os.path.join(lib.assets_dir, fn)
    os.replace(nested, flat)
    assert os.path.exists(flat) and not os.path.exists(nested)

    lib2 = make_lib_at(d)

    assert os.path.exists(nested)
    assert not os.path.exists(flat)
    lib3 = make_lib_at(d)  # 멱등
    assert os.path.exists(nested)


def test_slug_sanitizes_and_defaults(tmp_path):
    from notro_app.library import _slug
    assert _slug("") == "_uncategorized"
    assert _slug("  ") == "_uncategorized"
    assert _slug("miku") == "miku"
    assert _slug('a/b\\c:d') == "a_b_c_d"


def test_asset_path_uses_collection_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png", "miku")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False, collection="miku")
    path = lib.asset_path(item)
    assert os.path.normpath(path) == os.path.normpath(
        os.path.join(lib.assets_dir, "miku", fn))


def test_asset_path_uncategorized_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "b.png")
    item = lib.add_item("emoji", "b", [], "local", "", fn, False)
    path = lib.asset_path(item)
    assert os.path.normpath(path) == os.path.normpath(
        os.path.join(lib.assets_dir, "_uncategorized", fn))


def test_collection_icon_returns_first_registered_item(tmp_path):
    lib = make_lib(tmp_path)
    a = lib.add_item("emoji", "a", [], "local", "",
                     put_asset(lib, "a.png", "miku"), False, collection="miku")
    lib.add_item("emoji", "b", [], "local", "",
                 put_asset(lib, "b.png", "miku"), False, collection="miku")
    assert lib.collection_icon("miku") == a["id"]


def test_collection_icon_covers_folder_scanned_items(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "gifs"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "x.gif")
    lib.add_folder(str(folder), "gif")
    icon_id = lib.collection_icon("gifs")
    assert icon_id == "folder:" + str(folder / "x.gif")


def test_collection_icon_none_when_empty(tmp_path):
    lib = make_lib(tmp_path)
    assert lib.collection_icon("nope") is None


def test_folder_items_collection_is_basename(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "gifs"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "x.gif")
    lib.add_folder(str(folder), "gif")
    items = lib.scan_folders()
    assert items and items[0]["collection"] == "gifs"
    assert "gifs" in lib.collections()
