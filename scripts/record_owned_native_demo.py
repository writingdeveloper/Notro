#!/usr/bin/env python3
"""Capture a genuine Notro native WebView2 UI demo using owned test assets.

Privacy: captures ONLY this process's own CoreWebView2 control via its
CapturePreview API, never the desktop, Discord, real library or clipboard.
All artwork is deterministic geometric shapes generated here (no imported
third-party characters or proprietary art). This is UI evidence, NOT a
Discord attachment/send or installed-executable demonstration.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import config, fetch
from notro_app.i18n import set_language
from notro_app.library import Library
from notro_app.picker.assets_server import AssetServer
from notro_app.picker.window import PickerApi, ui_index_path

COLORS = [
    "#6D82E8", "#E87F91", "#6DC7B7", "#F2B768",
    "#BD89E7", "#62ADEB", "#BBDD70", "#F38565",
    "#4FC5D4", "#E59D57", "#A6A0F5", "#E6D46D",
]
EMOJI_NAMES = [
    "sunrise", "moonrise", "comet", "coral-heart",
    "violet-orbit", "bubble", "mint-leaf", "ember-bolt",
    "ocean-wave", "gold-star", "soft-cloud", "sunbeam",
    "sun-drift", "aurora", "nova", "citrus",
    "skyline", "sunflower",
]


def make_card(index: int, size: int = 112, phase: int = 0,
              landscape: bool = False) -> Image.Image:
    """New original graphic: geometries, circles and colored shapes."""
    w, h = (192, 144) if landscape else (size, size)
    color = COLORS[index % len(COLORS)]
    img = Image.new("RGBA", (w, h), (22, 27, 40, 0))
    draw = ImageDraw.Draw(img)
    outer = (8, 8, w - 8, h - 8)
    draw.rounded_rectangle(outer, radius=25, fill=color)
    draw.ellipse((w*.23, h*.20, w*.77, h*.74), fill="#23334D")
    if index % 5 == 0:  # sun
        for k in range(8):
            angle = math.pi * k / 4 + phase * .10
            x = w*.5 + math.cos(angle) * w*.29
            y = h*.47 + math.sin(angle) * h*.29
            draw.line((w*.5, h*.47, x, y), fill="#F9E79D", width=5)
        draw.ellipse((w*.38, h*.33, w*.62, h*.58), fill="#FFF4B8")
    elif index % 5 == 1:  # moon
        draw.ellipse((w*.32, h*.26, w*.67, h*.65), fill="#FFF0D3")
        draw.ellipse((w*.43, h*.21, w*.73, h*.58), fill="#23334D")
    elif index % 5 == 2:  # comet
        draw.line((w*.25, h*.65, w*.69, h*.27), fill="#E8FFF8", width=10)
        draw.ellipse((w*.54, h*.19, w*.82, h*.49), fill="#FBF9C5")
    elif index % 5 == 3:  # heart using overlapping circles
        draw.ellipse((w*.24, h*.30, w*.52, h*.57), fill="#FFDBE0")
        draw.ellipse((w*.48, h*.30, w*.76, h*.57), fill="#FFDBE0")
        draw.polygon([(w*.24, h*.47), (w*.76, h*.47), (w*.5, h*.77)],
                     fill="#FFDBE0")
    else:  # orbit
        draw.ellipse((w*.27, h*.23, w*.74, h*.73),
                     outline="#F0E9FF", width=7)
        x=w*.5+math.cos(phase*.25)*w*.24
        y=h*.48+math.sin(phase*.25)*h*.23
        draw.ellipse((x-9, y-9, x+9, y+9), fill="#FFF8BF")
    return img


def seed_owned_media(root: Path, library: Library) -> dict:
    outputs = {"emoji": [], "sticker": [], "gif": []}
    for index, name in enumerate(EMOJI_NAMES):
        path = root / ("owned-" + name + ".png")
        make_card(index).save(path)
        obj = fetch.register_from_file(
            library, str(path), "emoji", name=name,
            keywords=["made-for-notro", "original-artwork"],
            collection="Owned Demo"
        )
        outputs["emoji"].append(obj)
    for index, name in enumerate(("sunrise-sticker", "nebula-sticker",
                                  "moonlight-sticker", "coral-sticker")):
        path = root / (name + ".png")
        make_card(index+1, landscape=True).save(path)
        outputs["sticker"].append(fetch.register_from_file(
            library, str(path), "sticker", name=name,
            keywords=["owned", "demo"], collection="Owned Demo"
        ))
    for index, name in enumerate(("sun-orbit-animation",
                                  "comet-animation", "moon-animation")):
        frames = [make_card(index, size=128, phase=f) for f in range(9)]
        path = root / (name+".gif")
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=105, loop=0, disposal=2)
        outputs["gif"].append(fetch.register_from_file(
            library, str(path), "gif", name=name,
            keywords=["original", "animation"], collection="Owned Demo"
        ))
    library.toggle_favorite(outputs["emoji"][0]["id"])
    library.toggle_favorite(outputs["emoji"][4]["id"])
    library.touch(outputs["emoji"][7]["id"])
    return outputs


def native_capture(window, path: Path) -> Image.Image:
    """Capture ONLY the browser surface, not other windows/desktop data."""
    from Microsoft.Web.WebView2.Core import CoreWebView2CapturePreviewImageFormat
    from System import Action
    from System.IO import FileAccess, FileMode, FileStream

    control = window.native.webview
    job: dict = {}

    def on_ui_thread() -> None:
        try:
            job["stream"] = FileStream(str(path), FileMode.Create, FileAccess.Write)
            job["task"] = control.CoreWebView2.CapturePreviewAsync(
                CoreWebView2CapturePreviewImageFormat.Png, job["stream"])
        except Exception as exc:
            job["error"] = str(exc)

    control.BeginInvoke(Action(on_ui_thread))
    deadline = time.monotonic() + 15
    while "task" not in job and "error" not in job and time.monotonic() < deadline:
        time.sleep(.04)
    if "error" in job or "task" not in job:
        raise RuntimeError("WebView2 UI capture could not start: " + str(job.get("error")))
    try:
        if not job["task"].Wait(12000):
            raise RuntimeError("WebView2 UI capture timed out")
        if str(job["task"].Status) != "RanToCompletion":
            raise RuntimeError("WebView2 capture did not complete successfully")
    finally:
        job["stream"].Dispose()

    with Image.open(path) as frame:
        rgba = frame.convert("RGB")
        # Reject browser-white or blank rendering as non-evidence.
        sample = rgba.resize((32, 32)).convert("L")
        if len(sample.getcolors(1024) or []) < 5:
            raise RuntimeError("WebView2 capture seems blank")
        return rgba.copy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    import webview

    # The demo is an independent QA process, NOT the user's Notro app.
    # Block all OS-registry preference reads/writes before PickerApi exists.
    config.get_setting_flag = lambda name: False
    config.get_setting_int = lambda name, default=0: default
    config.get_setting_str = lambda name, default="": default
    config.set_setting_flag = lambda *args: None
    config.set_setting_int = lambda *args: None
    config.set_setting_str = lambda *args: None

    with tempfile.TemporaryDirectory(prefix="notro-owned-ui-qa-") as temporary:
        root = Path(temporary)
        set_language("en")
        lib = Library(str(root / "private-demo-library"))
        sources = seed_owned_media(root, lib)
        assets = AssetServer(
            lambda item_id: lib.asset_path(item)
            if (item := lib.resolve(item_id)) else None
        )
        assets.start()
        api = PickerApi(library=lib, asset_server=assets)
        win = webview.create_window(
            "Notro Native WebView2 — rights-cleared demo",
            url=ui_index_path(), js_api=api,
            width=650, height=490, frameless=False, on_top=False,
            resizable=True, focus=False
        )
        evidence: dict = {"status": "pending", "screens": [], "errors": [],
                          "source": "actual pywebview CoreWebView2",
                          "third_party_art": False, "discord_touched": False}
        captures: list[Image.Image] = []
        durations: list[int] = []
        frames_dir = root / "frames"
        frames_dir.mkdir()

        def capture_phase(name: str, seconds: float) -> None:
            time.sleep(.32)  # lazy-loaded images become ready
            item = native_capture(win, frames_dir / (name+".png"))
            target = (850, 625)
            ratio = min(target[0]/item.width, target[1]/item.height)
            if ratio < 1:
                item = item.resize((int(item.width*ratio), int(item.height*ratio)),
                                   Image.Resampling.LANCZOS)
            # Keep full native picker visible without any desktop pixels.
            captures.append(item)
            durations.append(round(seconds*1000))
            evidence["screens"].append({
                "phase": name, "source_pixels": list(item.size)
            })

        def on_ui_ready() -> None:
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        count = win.evaluate_js("state.items.length")
                        if count == len(EMOJI_NAMES)+7 and win.native:
                            break
                    except Exception:
                        pass
                    time.sleep(.15)
                assert win.evaluate_js("state.items.length") == len(EMOJI_NAMES)+7
                assert win.evaluate_js(
                    "document.querySelectorAll('.cell img').length") >= 18
                assert win.evaluate_js("state.autoSend") is False
                assert win.evaluate_js("state.autoCaptureSave") is False
                capture_phase("01_gallery", 1.8)

                # Use exactly the app's real search input listener.
                win.evaluate_js(
                    "(() => { const q=document.getElementById('search');"
                    "q.value='sun';q.dispatchEvent(new Event('input',{bubbles:true}));"
                    "})()"
                )
                assert win.evaluate_js("state.query") == "sun"
                assert win.evaluate_js(
                    "document.querySelectorAll('.cell').length") >= 3
                capture_phase("02_search_sun", 1.8)

                # Clear search and navigate using the real keyboard handler.
                win.evaluate_js(
                    "(() => { const q=document.getElementById('search');"
                    "q.value='';q.dispatchEvent(new Event('input',{bubbles:true}));"
                    "window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));"
                    "})()"
                )
                assert win.evaluate_js(
                    "document.querySelectorAll('.cell.cursor').length") == 1
                capture_phase("03_keyboard_cursor", 1.7)

                win.evaluate_js(
                    "document.querySelector('[data-tab=sticker]').click()")
                assert win.evaluate_js("state.tab") == "sticker"
                capture_phase("04_sticker_tab", 1.9)

                win.evaluate_js("document.querySelector('[data-tab=gif]').click()")
                assert win.evaluate_js("state.tab") == "gif"
                assert win.evaluate_js(
                    "document.querySelectorAll('.cell img').length") == 3
                capture_phase("05_animated_gif_tab", 1.9)
                capture_phase("06_animated_gif_frames", 1.3)

                win.evaluate_js("document.getElementById('btn-settings').click()")
                assert win.evaluate_js(
                    "!document.getElementById('modal-settings').classList.contains('hidden')")
                assert win.evaluate_js(
                    "!document.getElementById('st-auto-send').checked"
                    " && !document.getElementById('st-auto-capture').checked")
                capture_phase("07_settings", 1.9)

                # Show import/export options without invoking OS file dialogs.
                win.evaluate_js(
                    "document.querySelector('#modal-settings .modal-box').scrollTop=900;"
                )
                capture_phase("08_private_backup_options", 1.9)

                win.evaluate_js(
                    "document.getElementById('st-close').click();"
                    "document.querySelector('[data-tab=emoji]').click()"
                )
                capture_phase("09_final_gallery", 1.7)
                assert len(captures) == len(durations) == 9
                assert all(img.size[0] > 650 and img.size[1] > 400
                           for img in captures)

                # Frame 0 is a still from an actual native WebView2 surface.
                screenshot = args.output_dir / "picker-owned-webview.png"
                captures[0].save(screenshot, optimize=True)
                movie = args.output_dir / "demo-owned-webview.gif"
                captures[0].save(
                    movie, save_all=True, append_images=captures[1:],
                    duration=durations, loop=0, optimize=True,
                    disposal=2, color=256
                )
                evidence["status"] = "passed"
                evidence["png"] = screenshot.name
                evidence["gif"] = movie.name
                evidence["gif_seconds"] = round(sum(durations)/1000, 1)
                evidence["gif_bytes"] = movie.stat().st_size
                evidence["png_bytes"] = screenshot.stat().st_size
                evidence["isolated_settings"] = True
                evidence["auto_send_off"] = True
                evidence["auto_capture_off"] = True
                evidence["items"] = {key:len(val) for key,val in sources.items()}
            except Exception as exc:
                evidence["errors"].append(type(exc).__name__ + ": " + str(exc)[:300])
                evidence["status"] = "failed"
            finally:
                win.destroy()

        try:
            webview.start(on_ui_ready, gui="edgechromium", private_mode=True,
                          http_server=False, debug=False)
        except Exception as exc:
            evidence["status"] = "failed"
            evidence["errors"].append(type(exc).__name__ + ": " + str(exc)[:300])
        finally:
            assets.stop()
            for frame in captures:
                frame.close()

    print("NOTRO_OWNED_NATIVE_DEMO="+json.dumps(evidence, ensure_ascii=True),
          flush=True)
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
