"""항목 이름·키워드 편집과 중복 등록 감지 (스펙 §3.4/§5.3)."""

import io
import os

import pytest
from PIL import Image

from notro_app import fetch
from notro_app.library import Library
from notro_app.picker import window


def png_bytes(color=(255, 0, 0, 255)):
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def make_item(lib, name="old", keywords=("a",), type_="emoji"):
    d = lib.collection_dir("")
    filename = lib.new_asset_filename(".png")
    with open(os.path.join(d, filename), "wb") as f:
        f.write(png_bytes())
    return lib.add_item(type_, name, list(keywords), "local", "", filename, False)


class FakeServer:
    def url_for(self, item_id):
        return "http://assets/" + str(item_id)


# ---------- 이름·키워드 편집 ----------
def test_update_item_changes_name_and_keywords(tmp_path):
    lib = Library(str(tmp_path / "d"))
    item = make_item(lib)

    updated = lib.update_item(item["id"], name="new name", keywords=["x", "y"])

    assert updated["name"] == "new name" and updated["keywords"] == ["x", "y"]
    assert Library(str(tmp_path / "d")).get(item["id"])["name"] == "new name"


def test_update_item_keeps_name_when_blank(tmp_path):
    """빈 이름으로 저장해 항목이 이름 없이 남는 일이 없어야 한다."""
    lib = Library(str(tmp_path / "d"))
    item = make_item(lib, name="keep me")

    updated = lib.update_item(item["id"], name="   ", keywords=[])

    assert updated["name"] == "keep me" and updated["keywords"] == []


def test_update_item_ignores_unknown_and_folder_items(tmp_path):
    lib = Library(str(tmp_path / "d"))
    assert lib.update_item("nope", name="x") is None
    assert lib.update_item(r"folder:C:\x\y.png", name="x") is None


def test_api_update_item_splits_keywords(tmp_path):
    lib = Library(str(tmp_path / "d"))
    item = make_item(lib)
    api = window.PickerApi(library=lib, asset_server=FakeServer())

    res = api.update_item(item["id"], "renamed", "one, two  three")

    assert res["ok"] is True
    assert res["item"]["name"] == "renamed"
    assert lib.get(item["id"])["keywords"] == ["one", "two", "three"]


def test_api_update_item_reports_failure(tmp_path):
    api = window.PickerApi(library=Library(str(tmp_path / "d")),
                           asset_server=FakeServer())
    assert api.update_item("folder:x", "n", "")["ok"] is False


# ---------- 중복 등록 ----------
def test_register_from_file_rejects_identical_bytes(tmp_path):
    """같은 그림을 같은 탭·컬렉션에 두 번 넣으면 조용히 쌓이지 않는다."""
    lib = Library(str(tmp_path / "d"))
    src = tmp_path / "a.png"
    src.write_bytes(png_bytes())

    first = fetch.register_from_file(lib, str(src), "emoji")
    with pytest.raises(fetch.DuplicateAssetError) as excinfo:
        fetch.register_from_file(lib, str(src), "emoji")

    assert excinfo.value.item["id"] == first["id"]
    assert len(lib.items()) == 1


def test_duplicate_registration_leaves_no_orphan_file(tmp_path):
    lib = Library(str(tmp_path / "d"))
    src = tmp_path / "a.png"
    src.write_bytes(png_bytes())
    fetch.register_from_file(lib, str(src), "emoji")

    with pytest.raises(fetch.DuplicateAssetError):
        fetch.register_from_file(lib, str(src), "emoji")

    stored = os.listdir(lib.collection_dir(""))
    assert len(stored) == 1, f"중복 등록이 파일을 남겼다: {stored}"


def test_duplicate_check_is_per_tab_and_collection(tmp_path):
    """다른 탭이나 다른 컬렉션에 같은 그림을 두는 건 정상적인 사용이다."""
    lib = Library(str(tmp_path / "d"))
    src = tmp_path / "a.png"
    src.write_bytes(png_bytes())

    fetch.register_from_file(lib, str(src), "emoji")
    fetch.register_from_file(lib, str(src), "sticker")
    fetch.register_from_file(lib, str(src), "emoji", collection="other")

    assert len(lib.items()) == 3


def test_different_images_are_not_duplicates(tmp_path):
    lib = Library(str(tmp_path / "d"))
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    a.write_bytes(png_bytes((255, 0, 0, 255)))
    b.write_bytes(png_bytes((0, 0, 255, 255)))

    fetch.register_from_file(lib, str(a), "emoji")
    fetch.register_from_file(lib, str(b), "emoji")

    assert len(lib.items()) == 2


def test_register_from_url_reports_duplicate(tmp_path, monkeypatch):
    lib = Library(str(tmp_path / "d"))
    monkeypatch.setattr(fetch, "download", lambda url, dest, timeout=10:
                        open(dest, "wb").write(png_bytes()))
    api = window.PickerApi(library=lib, asset_server=FakeServer())
    url = "https://cdn.discordapp.com/emojis/123.png"

    assert api.register_url(url)["ok"] is True
    res = api.register_url(url)

    assert res["ok"] is False and res["error"] == "duplicate"
    assert len(lib.items()) == 1


def test_register_files_counts_duplicates_separately(tmp_path):
    lib = Library(str(tmp_path / "d"))
    src = tmp_path / "a.png"
    src.write_bytes(png_bytes())
    api = window.PickerApi(library=lib, asset_server=FakeServer())

    api.register_files([str(src)], "emoji")
    res = api.register_files([str(src)], "emoji")

    assert res == {"ok": True, "count": 0, "failed": 0, "duplicate": 1}


def test_capture_hash_still_wins_for_clipboard_path(tmp_path):
    """캡처 경로가 넘긴 해시(클립보드 원본 바이트)를 덮어쓰지 않아야 한다."""
    lib = Library(str(tmp_path / "d"))

    item = fetch.register_from_png_bytes(
        lib, png_bytes(), "emoji", collection="c", content_hash="caller-hash")

    assert item["content_hash"] == "caller-hash"


# ---------- 피커 창 크기 기억 ----------
@pytest.mark.parametrize("given,expected", [
    ((700, 600), (700, 600)),
    ((100, 100), (window.MIN_W, window.MIN_H)),     # 너무 작으면 하한
    ((9999, 9999), (window.MAX_W, window.MAX_H)),   # 터무니없는 값만 상한
    ((0, 0), (window.WIN_W, window.WIN_H)),         # 깨진 값이면 기본값
    (("x", None), (window.WIN_W, window.WIN_H)),
])
def test_clamp_size(given, expected):
    assert window.clamp_size(*given) == expected


def test_saved_size_reads_settings(monkeypatch):
    values = {"picker_w": 640, "picker_h": 520}
    monkeypatch.setattr(window.config, "get_setting_int",
                        lambda name, default=0: values.get(name, default))
    assert window.saved_size() == (640, 520)


def test_saved_size_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(window.config, "get_setting_int",
                        lambda name, default=0: default)
    assert window.saved_size() == (window.WIN_W, window.WIN_H)


# ---------- 자동 전송 ----------
def test_auto_send_defaults_off_and_persists(tmp_path, monkeypatch):
    """되돌릴 수 없는 동작이므로 기본 꺼짐이어야 한다."""
    values = {}
    monkeypatch.setattr(window.config, "get_setting_flag",
                        lambda key: values.get(key, False))
    monkeypatch.setattr(window.config, "set_setting_flag",
                        lambda key, value=True: values.__setitem__(key, bool(value)))
    api = window.PickerApi(library=Library(str(tmp_path / "d")),
                           asset_server=FakeServer())

    assert api.get_state()["auto_send"] is False
    assert api.set_auto_send(True) is True
    assert values["auto_send"] is True


def test_clipboard_paste_dedupes_same_image(tmp_path, monkeypatch):
    """같은 캡처를 두 번 붙여넣어도 항목이 두 개 생기지 않는다."""
    from notro_app.capture_store import CaptureReadResult
    lib = Library(str(tmp_path / "d"))
    api = window.PickerApi(library=lib, asset_server=FakeServer())
    monkeypatch.setattr(window, "read_clipboard_png",
                        lambda: CaptureReadResult(png_bytes(), None))

    assert api.register_clipboard("emoji")["ok"] is True
    second = api.register_clipboard("emoji")

    assert second == {"ok": False, "error": "duplicate"}
    assert len(lib.items()) == 1


def test_capture_store_reports_duplicate_not_failure(tmp_path):
    """자동 저장과 버튼이 동시에 같은 캡처를 저장해도 '저장 실패'가 아니다."""
    from notro_app.capture_store import CaptureStore
    lib = Library(str(tmp_path / "d"))
    store = CaptureStore(lib)
    data = png_bytes()

    first = store.save_png(data)
    second = store.save_png(data)

    assert first.ok and not first.duplicate
    assert second.ok and second.duplicate and second.item_id == first.item_id
    assert len(lib.items()) == 1


def test_auto_send_delay_defaults_and_clamps(monkeypatch):
    """QA에서 재빌드 없이 조정할 수 있어야 하지만, 오타 하나로 Enter가 즉시
    날아가거나 몇 분 뒤에 날아가면 안 된다."""
    values = {}
    monkeypatch.setattr(window.config, "get_setting_int",
                        lambda name, default=0: values.get(name, default))

    assert window.auto_send_delay() == window.AUTO_SEND_DELAY   # 미설정 → 기본값

    values["auto_send_delay_ms"] = 900
    assert window.auto_send_delay() == 0.9

    for bad in (0, -100, 10_000):        # 0.05~5초 밖은 기본값으로 되돌린다
        values["auto_send_delay_ms"] = bad
        assert window.auto_send_delay() == window.AUTO_SEND_DELAY


def test_picker_window_has_a_minimum_size():
    """WS_THICKFRAME을 켠 뒤로는 OS가 크기 조절을 맡으므로, 최소 크기를 걸지 않으면
    사용자가 레이아웃이 무너질 만큼 줄일 수 있다."""
    assert (window.MIN_W, window.MIN_H) == window.clamp_size(1, 1)


def test_large_saved_size_survives_a_reopen(tmp_path, monkeypatch):
    """넓은 모니터에서 늘려 둔 크기가 다시 열 때 조용히 줄어들면 안 된다.
    화면에 맞추는 일은 popup_geometry가 열 때 하므로, 저장값은 보존한다."""
    assert window.clamp_size(1600, 1200) == (1600, 1200)
    assert window.clamp_size(2560, 1440) == (2560, 1440)
