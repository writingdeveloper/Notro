"""피커 클립보드 이미지 붙여넣기 등록 경로 (스펙 §5).

백엔드: PNG 바이트 → 라이브러리 등록(fetch.register_from_png_bytes)과
PickerApi.register_clipboard. 실제 클립보드/GUI는 건드리지 않고 monkeypatch로
클립보드 PNG 판독만 대체한다.
"""

import io
import os
from unittest.mock import Mock

import pytest
from PIL import Image

from notro_app import fetch, i18n
from notro_app.capture_store import (CAPTURE_COLLECTION_ID,
                                     CaptureReadResult, CaptureSaveResult)
from notro_app.library import Library
from notro_app.picker import window


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (0, 200, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


def apng_bytes():
    f1 = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    f2 = Image.new("RGBA", (8, 8), (0, 0, 255, 255))
    buf = io.BytesIO()
    f1.save(buf, format="PNG", save_all=True, append_images=[f2],
            duration=100, loop=0)
    return buf.getvalue()


# ---------- fetch.register_from_png_bytes ----------
def test_register_from_png_bytes_still_image(tmp_path):
    lib = Library(str(tmp_path / "d"))
    item = fetch.register_from_png_bytes(lib, png_bytes(), "sticker")
    assert item["type"] == "sticker"
    assert item["animated"] is False
    assert item["convert_warning"] is False
    assert item["source_kind"] == "local"
    path = lib.asset_path(item)
    assert os.path.exists(path)
    with Image.open(path) as im:
        assert im.format == "PNG"


def test_register_from_png_bytes_apng_becomes_gif(tmp_path):
    lib = Library(str(tmp_path / "d"))
    item = fetch.register_from_png_bytes(lib, apng_bytes(), "sticker")
    assert item["animated"] is True
    assert item["filename"].endswith(".gif")
    with Image.open(lib.asset_path(item)) as im:
        assert im.format == "GIF" and im.n_frames > 1


def test_register_from_png_bytes_keywords_and_type(tmp_path):
    lib = Library(str(tmp_path / "d"))
    item = fetch.register_from_png_bytes(lib, png_bytes(), "emoji",
                                         name="hi", keywords=["a", "b"])
    assert item["type"] == "emoji" and item["name"] == "hi"
    assert item["keywords"] == ["a", "b"]


# ---------- PickerApi.register_clipboard ----------
def test_register_clipboard_registers_png(tmp_path, monkeypatch):
    lib = Library(str(tmp_path / "d"))
    api = window.PickerApi(library=lib)
    monkeypatch.setattr(
        window, "read_clipboard_png",
        lambda: CaptureReadResult(png_bytes(), None))
    res = api.register_clipboard("sticker")
    assert res["ok"] is True
    items = lib.items()
    assert len(items) == 1 and items[0]["type"] == "sticker"
    assert os.path.exists(lib.asset_path(items[0]))


def test_register_clipboard_no_image_returns_error(tmp_path, monkeypatch):
    lib = Library(str(tmp_path / "d"))
    api = window.PickerApi(library=lib)
    monkeypatch.setattr(
        window, "read_clipboard_png",
        lambda: CaptureReadResult(None, "no_image"))
    res = api.register_clipboard("emoji")
    assert res["ok"] is False
    assert res.get("error")
    assert lib.items() == []


class FakeServer:
    def url_for(self, item_id):
        return "http://assets/" + str(item_id)


def test_register_capture_returns_new_item(tmp_path):
    """전용 버튼 API가 신규 항목 ID와 예약 컬렉션을 잃는 회귀를 잡는다."""
    lib = Library(str(tmp_path / "d"))
    store = Mock()
    store.read_and_save.return_value = CaptureSaveResult(
        True, False, "item1", None)
    api = window.PickerApi(
        library=lib, asset_server=FakeServer(), capture_store=store)

    assert api.register_capture() == {
        "ok": True, "duplicate": False, "item_id": "item1",
        "collection": CAPTURE_COLLECTION_ID,
    }


@pytest.mark.parametrize("error", ["no_image", "read", "register"])
def test_register_capture_preserves_error(tmp_path, error):
    """읽기·부재·저장 실패가 하나의 모호한 오류로 합쳐지는 회귀를 잡는다."""
    store = Mock()
    store.read_and_save.return_value = CaptureSaveResult(False, error=error)
    api = window.PickerApi(
        library=Library(str(tmp_path / "d")), asset_server=FakeServer(),
        capture_store=store)

    assert api.register_capture() == {"ok": False, "error": error}


def test_auto_capture_setting_defaults_off_and_persists(tmp_path, monkeypatch):
    """자동 저장이 기본 켜짐이거나 스위치 변경이 영속되지 않는 회귀를 잡는다."""
    values = {}
    monkeypatch.setattr(
        window.config, "get_setting_flag", lambda key: values.get(key, False),
        raising=False)
    monkeypatch.setattr(
        window.config, "set_setting_flag",
        lambda key, value=True: values.__setitem__(key, bool(value)),
        raising=False)
    api = window.PickerApi(
        library=Library(str(tmp_path / "d")), asset_server=FakeServer())

    assert api.get_state()["auto_capture_save"] is False
    assert api.set_auto_capture_save(True) is True
    assert values["auto_capture_save"] is True


def test_register_files_reports_failures(tmp_path, monkeypatch):
    """전부/일부 파일 등록 실패가 성공으로 숨겨지는 회귀를 잡는다."""
    api = window.PickerApi(library=Library(str(tmp_path / "d")))
    monkeypatch.setattr(
        fetch, "register_from_file",
        lambda lib, path, type_, collection="":
        (_ for _ in ()).throw(ValueError(path))
        if path == "bad" else {"id": path})

    assert api.register_files(["good", "bad"], "emoji") == {
        "ok": True, "count": 1, "failed": 1,
    }


def test_register_files_routes_to_selected_collection(tmp_path, monkeypatch):
    """드롭한 파일이 보고 있던 컬렉션 대신 미분류로 새는 회귀를 잡는다."""
    api = window.PickerApi(library=Library(str(tmp_path / "d")))
    seen = []
    monkeypatch.setattr(
        fetch, "register_from_file",
        lambda lib, path, type_, collection="": seen.append(collection))

    api.register_files(["a"], "emoji", "MyBeers")
    api.register_files(["b"], "emoji", "__all__")  # 가상 항목은 미분류

    assert seen == ["MyBeers", ""]


def test_register_url_routes_to_selected_collection(tmp_path, monkeypatch):
    lib = Library(str(tmp_path / "d"))
    api = window.PickerApi(library=lib, asset_server=FakeServer())
    seen = []

    def fake(library, url, name, keywords, collection, type_):
        seen.append((collection, type_))
        return library.add_item(type_ or "emoji", "x", [], "discord-cdn", url,
                                "x.png", False, collection=collection)

    monkeypatch.setattr(fetch, "register_from_url", fake)

    res = api.register_url("https://cdn.discordapp.com/emojis/1.png",
                           collection="MyBeers", type_="gif")

    assert seen == [("MyBeers", "gif")] and res["ok"] is True
    assert res["item"]["collection"] == "MyBeers"
    assert res["item"]["type"] == "gif"  # 보고 있던 탭에 등록


def test_register_clipboard_uses_bitmap_fallback(tmp_path, monkeypatch):
    """기존 Ctrl+V 경로가 CF_DIB 전용 캡처를 놓치는 회귀를 잡는다."""
    lib = Library(str(tmp_path / "d"))
    api = window.PickerApi(library=lib)
    monkeypatch.setattr(
        window, "read_clipboard_png",
        lambda: CaptureReadResult(png_bytes(), None), raising=False)

    result = api.register_clipboard("sticker")

    assert result["ok"] is True
    assert lib.items()[0]["type"] == "sticker"


# ---------- i18n 계약 (신규 문자열) ----------
def test_paste_no_image_string_registered_all_langs():
    assert "picker_paste_no_image" in window.PICKER_STRING_KEYS
    for lang in i18n.SUPPORTED_LANGS:
        assert i18n.STRINGS[lang].get("picker_paste_no_image")


def test_settings_tooltip_string_is_exposed_to_picker():
    """설정 버튼 툴팁이 번역 키 이름 그대로 노출되는 회귀를 잡는다."""
    assert "picker_settings" in window.PICKER_STRING_KEYS


# ---------- 붙여넣기 표시 크기 (스펙 §6.8) ----------
def test_get_state_exposes_paste_sizes(tmp_path, monkeypatch):
    """UI가 현재 크기 설정을 못 읽어 항상 기본값으로 되돌아가는 회귀를 잡는다."""
    monkeypatch.setattr(window.config, "get_setting_int",
                        lambda name, default=0: default, raising=False)
    api = window.PickerApi(
        library=Library(str(tmp_path / "d")), asset_server=FakeServer())

    state = api.get_state()

    assert state["paste_sizes"] == {"emoji": 48, "sticker": 160, "gif": 0}
    assert 48 in state["paste_size_choices"] and 0 in state["paste_size_choices"]


def test_set_paste_size_persists_per_tab(tmp_path, monkeypatch):
    from notro_app import config as real_config
    saved = {}
    monkeypatch.setattr(real_config, "set_setting_int",
                        lambda name, value: saved.__setitem__(name, value))
    api = window.PickerApi(
        library=Library(str(tmp_path / "d")), asset_server=FakeServer())

    assert api.set_paste_size("sticker", 96) == {
        "ok": True, "type": "sticker", "px": 96}
    assert saved == {"paste_px_sticker": 96}


def test_paste_size_strings_registered_all_langs():
    for key in ("picker_paste_size", "picker_paste_size_note",
                "picker_size_original"):
        assert key in window.PICKER_STRING_KEYS
        for lang in i18n.SUPPORTED_LANGS:
            assert i18n.STRINGS[lang].get(key), f"{lang} missing {key}"
