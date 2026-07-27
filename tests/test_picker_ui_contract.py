"""피커의 캡처 저장 UI 구조 계약."""

from html.parser import HTMLParser
from pathlib import Path


UI_DIR = Path(__file__).parents[1] / "notro_app" / "picker" / "ui"


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def elements():
    parser = ElementCollector()
    parser.feed((UI_DIR / "index.html").read_text(encoding="utf-8"))
    return parser.elements


def test_capture_button_precedes_other_header_actions():
    """승인된 A안의 원클릭 버튼이 추가 메뉴 뒤로 숨는 회귀를 잡는다."""
    ids = [attrs.get("id") for tag, attrs in elements() if tag == "button"]
    capture = ids.index("btn-capture")
    assert capture < ids.index("btn-add") < ids.index("btn-settings")


def test_auto_capture_uses_native_checkbox_with_description():
    """설정이 접근 불가능한 커스텀 토글로 바뀌거나 설명이 빠지는 회귀를 잡는다."""
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    tag, attrs = by_id["st-auto-capture"]
    assert tag == "input" and attrs.get("type") == "checkbox"
    assert by_id["st-auto-capture-note"][0] == "p"
    assert by_id["st-folders-subtitle"][0] in {"h4", "p"}


def test_add_modal_has_collection_picker():
    """URL 등록 시 저장할 컬렉션을 고를 수 없게 되는 회귀를 잡는다.
    목록에서 고르는 select와, 새 이름을 적는 입력칸이 함께 있어야 한다."""
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    assert by_id["add-collection-select"][0] == "select"
    assert by_id["add-collection"][0] == "input"
    label_tag, label_attrs = by_id["add-collection-label"]
    assert label_tag == "label"
    assert label_attrs.get("for") == "add-collection-select"


def test_settings_has_paste_size_section():
    """붙여넣기 크기 설정이 사라지거나 설명 없이 노출되는 회귀를 잡는다."""
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    assert by_id["st-size-subtitle"][0] in {"h4", "p"}
    assert by_id["st-size-note"][0] == "p"
    assert "st-sizes" in by_id


def test_edit_modal_has_name_and_keyword_fields():
    """이름·키워드를 고칠 수 없게 되는 회귀를 잡는다."""
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    assert by_id["edit-name"][0] == "input" and by_id["edit-kw"][0] == "input"
    assert by_id["edit-name-label"][1].get("for") == "edit-name"
    assert by_id["edit-kw-label"][1].get("for") == "edit-kw"
    assert "edit-submit" in by_id and "edit-cancel" in by_id


def test_auto_send_uses_native_checkbox_with_description():
    """되돌릴 수 없는 동작이므로 설명 없이 노출되면 안 된다."""
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    tag, attrs = by_id["st-auto-send"]
    assert tag == "input" and attrs.get("type") == "checkbox"
    assert by_id["st-auto-send-note"][0] == "p"
    assert by_id["st-auto-send-label"][1].get("for") == "st-auto-send"


def test_capture_button_is_a_real_button():
    by_id = {attrs.get("id"): (tag, attrs) for tag, attrs in elements()
             if attrs.get("id")}
    tag, attrs = by_id["btn-capture"]
    assert tag == "button"
    assert attrs.get("type") == "button"
