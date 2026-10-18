"""Static tray/About UI boundaries; real Win32 WebView2 is tested separately."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "notro_app" / "picker" / "ui"


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.images: list[dict] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag, attrs):
        info = dict(attrs)
        if info.get("id"):
            self.ids.append(info["id"])
        if tag == "img":
            self.images.append(info)
        if tag == "script" and info.get("src"):
            self.scripts.append(info["src"])
        if tag == "link" and info.get("href"):
            self.styles.append(info["href"])


def test_tray_popup_has_home_settings_about_with_unique_accessible_ids():
    source = (UI / "tray_panel.html").read_text(encoding="utf-8")
    parser = Elements()
    parser.feed(source)
    assert len(parser.ids) == len(set(parser.ids))
    required = {
        "page-home", "page-settings", "page-about", "header-version",
        "about-version", "about-platform", "about-engine", "about-license",
        "about-disclosure", "about-quick-github", "link-github",
        "link-releases", "link-issues", "link-license", "btn-picker",
        "btn-toggle", "btn-settings", "btn-about", "btn-quit",
        "select-limit", "select-language", "select-hotkey",
        "toggle-startup", "toggle-auto-update", "toast"
    }
    assert required <= set(parser.ids)
    assert parser.scripts == ["tray_panel.js"]
    assert parser.styles == ["tray_panel.css"]
    assert not parser.images
    assert "http://" not in source and "https://" not in source


def test_tray_theme_dark_discord_inspired_but_only_local_assets():
    css = (UI / "tray_panel.css").read_text(encoding="utf-8")
    assert "--bg: #17191f;" in css
    assert "--accent: #5865f2;" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert ".about-source-link" in css
    assert "url(http" not in css and "@import" not in css


def test_native_ui_actions_are_bridge_only_and_escape_closes():
    js = (UI / "tray_panel.js").read_text(encoding="utf-8")
    assert "window.notroPanelOpen = page =>" in js
    assert "api().get_state()" in js
    assert "api().activate(String(action), String(value))" in js
    assert "api().hide()" in js
    assert 'e.key === "Escape"' in js
    assert 'window.addEventListener("blur"' in js
    assert "option.textContent" in js  # no untrusted innerHTML
    assert "innerHTML" not in js
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
    assert "send_ctrl_v" not in js and "send_enter" not in js


def test_five_readme_localizations_document_unreleased_about_and_preview():
    docs = ("README.md", "README.ko.md", "README.ja.md",
            "README.zh.md", "README.es.md")
    for filename in docs:
        raw = (ROOT / filename).read_text(encoding="utf-8")
        assert "v2.11.0" in raw and "v2.10.3" in raw
        assert "tray-menu-native-preview.png" in raw
        assert "tray-about-native-preview.png" in raw
        assert "GitHub" in raw
        assert "WebView2" in raw


def test_bundled_tray_qa_images_are_native_viewport_not_user_desktop():
    for item in ("tray-menu-native-preview.png",
                 "tray-about-native-preview.png"):
        with Image.open(ROOT / "docs/qa" / item) as image:
            assert image.format == "PNG"
            assert image.width >= 330 and image.height >= 430
            assert len(image.convert("RGB").resize((25, 25)).getcolors(1000)
                       or []) > 10


def test_no_about_version_is_hardcoded_in_html_or_js():
    html = (UI / "tray_panel.html").read_text(encoding="utf-8")
    js = (UI / "tray_panel.js").read_text(encoding="utf-8")
    assert "v2.11.0" not in html and "v2.11.0" not in js
    assert "about.version" in js
    assert "header-version" in html
