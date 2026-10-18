"""Verify that README demo assets contain owned geometric images, not chat."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LANG_READMES = ("README.md", "README.ko.md", "README.ja.md",
                "README.zh.md", "README.es.md")


class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


def test_five_readme_heroes_use_only_rights_cleared_native_demo():
    for name in LANG_READMES:
        raw = (ROOT / name).read_text(encoding="utf-8")
        parser = ImgParser()
        parser.feed(raw)
        hero = [a for a in parser.images
                if a.get("src") == "docs/demo-owned-webview.gif"]
        assert len(hero) == 1, name
        assert hero[0].get("alt"), name
        assert 'src="docs/demo.gif"' not in raw
        # Do not imply the fixture is a real installed client upload.
        assert "docs/demo-owned-webview.gif" in raw
        assert (ROOT / "docs/marketing/owned-native-demo-2026-10-17.md").exists()


def test_native_owned_gif_has_nine_legible_frames_about_sixteen_seconds():
    demo = ROOT / "docs/demo-owned-webview.gif"
    assert 100_000 < demo.stat().st_size < 5_000_000
    with Image.open(demo) as gif:
        assert gif.format == "GIF"
        assert gif.n_frames == 9
        total = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            total += gif.info["duration"]
            assert gif.width >= 650 and gif.height >= 400
            # Images from the actual picker renderer should not be blank.
            assert len(gif.convert("RGB").resize((24, 24)).getcolors(600)
                       or []) >= 10
        assert 10_000 <= total <= 20_000
    still = ROOT / "docs/picker-owned-webview.png"
    with Image.open(still) as image:
        assert image.format == "PNG"
        assert image.width >= 650 and image.height >= 400
        image.verify()


def test_rights_cleared_demo_is_captured_from_own_webview_control():
    script = (ROOT / "scripts/record_owned_native_demo.py").read_text(
        encoding="utf-8"
    )
    assert "CoreWebView2.CapturePreviewAsync" in script
    assert "private_mode=True" in script
    assert "config.get_setting_flag = lambda name: False" in script
    assert "config.set_setting_flag = lambda *args: None" in script
    assert "auto_send_off" in script and "auto_capture_off" in script
    assert "ImageGrab" not in script
    assert "PrintWindow" not in script
    assert "SendInput" not in script
    assert "Clipboard" not in script.split("def main()", 1)[-1]
    assert "corewebview2" in script.lower()


def test_original_geometric_pillow_art_is_distinct_and_deterministic():
    from scripts.record_owned_native_demo import make_card

    a = make_card(0).tobytes()
    b = make_card(1).tobytes()
    assert a != b
    assert a == make_card(0).tobytes()
    assert make_card(0).size == (112, 112)
    assert make_card(0, landscape=True).size == (192, 144)
