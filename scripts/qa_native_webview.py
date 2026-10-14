#!/usr/bin/env python3
"""Isolated *native* Windows WebView2 UI smoke for Notro.

Does not launch, patch, access, post to, or capture Discord. Uses synthetic
temporary test-library assets. It never registers Notro hotkeys or changes
global clipboard/registry. It opens a separate QA window then closes it.
"""
from __future__ import annotations

import json
import hashlib
import os
import random
import tempfile
import sys
import time
from types import SimpleNamespace
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import config, fetch, packs, resize
from notro_app.library import Library
from notro_app.i18n import set_language, tr
from notro_app.picker.assets_server import AssetServer
from notro_app.picker.window import PickerApi, ui_index_path

TIMEOUT = 20


def main() -> int:
    import webview

    with tempfile.TemporaryDirectory(prefix="notro-native-smoke-") as temp:
        root = Path(temp)
        appdata = root / "appdata"
        lib = Library(str(appdata))
        for name, ext in (("sample-notro", "png"), ("photo-demo", "jpg")):
            src = root / (name + "." + ext)
            Image.new("RGB", (48, 48), (150, 75, 200)).save(src)
            fetch.register_from_file(lib, str(src), "emoji")
        pack_path = root / "test-pack.zip"
        packs.export_pack(lib, str(pack_path))

        # A synthetic animated GIF is kept separate from the ZIP fixture.
        # No live library, clipboard contents or Discord chats are accessed.
        rng = random.Random(13)
        gif_frames = [
            Image.frombytes("RGB", (100, 90), rng.randbytes(100 * 90 * 3))
            for _ in range(14)
        ]
        gif_path = root / "synthetic-animation.gif"
        gif_frames[0].save(
            gif_path, format="GIF", save_all=True,
            append_images=gif_frames[1:], duration=80, loop=3,
        )
        gif_item = fetch.register_from_file(
            lib, str(gif_path), "gif", name="synthetic-animation")
        lib_gif_path = lib.asset_path(gif_item)
        gif_digest = hashlib.sha256(Path(lib_gif_path).read_bytes()).hexdigest()
        # Runtime-only per-process values, no registry writes.
        config.TEMP_DIR = str(root / "temporary")
        config.LIMIT_BYTES = int(os.path.getsize(lib_gif_path) * .65)
        config.UPLOAD_CEILING_BYTES = int(os.path.getsize(lib_gif_path) * .80)
        resize.target_px_for = lambda _type: 0
        server = AssetServer(
            lambda item_id: lib.asset_path(item) if (item := lib.resolve(item_id)) else None
        )
        server.start()
        api = PickerApi(library=lib, asset_server=server)
        title = "Notro QA Fixture - isolated"
        win = webview.create_window(
            title, url=ui_index_path(), js_api=api, width=540, height=460,
            hidden=False, frameless=False, on_top=False,
        )
        result = {"native_webview2": False, "items": 0, "tabs": 0,
                  "settings": False, "pack_buttons": False, "search": False,
                  "asset_images_loaded": False, "locale_labels": [],
                  "zip_drop": False, "gif_preview": False,
                  "gif_source_preserved": False, "gif_cancelled": False,
                  "gif_mock_accept": False,
                  "gallery_5k": False, "gallery_benchmarks": []}
        errors = []

        def examine():
            try:
                deadline = time.monotonic() + TIMEOUT
                while time.monotonic() < deadline:
                    try:
                        result["native_webview2"] = bool(win.evaluate_js(
                            "Boolean(window.pywebview && window.pywebview.api)"
                        ))
                        result["items"] = int(win.evaluate_js("state.items.length"))
                        result["tabs"] = int(win.evaluate_js(
                            "document.querySelectorAll('.tab').length"
                        ))
                        if result["native_webview2"] and result["items"] == 3:
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)
                if result["native_webview2"] and result["items"] == 3:
                    win.evaluate_js("document.getElementById('btn-settings').click()")
                    result["settings"] = bool(win.evaluate_js(
                        "!document.getElementById('modal-settings').classList.contains('hidden')"
                    ))
                    result["pack_buttons"] = bool(win.evaluate_js(
                        "document.getElementById('st-import-pack').offsetWidth>0 &&"
                        "document.getElementById('st-export-pack').offsetWidth>0"
                    ))
                    win.evaluate_js(
                        "document.getElementById('modal-settings').classList.add('hidden');"
                        "state.query='photo';document.getElementById('search').value='photo';render()"
                    )
                    result["search"] = bool(win.evaluate_js(
                        "document.querySelectorAll('.cell').length===1"
                    ))
                    for _ in range(15):
                        all_loaded = bool(win.evaluate_js(
                            "[...document.querySelectorAll('.cell img')].every("
                            "img => img.complete && img.naturalWidth > 0)"
                        ))
                        if all_loaded:
                            result["asset_images_loaded"] = True
                            break
                        time.sleep(0.2)
                    for lang in ("ko", "en", "ja", "zh", "es"):
                        set_language(lang)
                        win.evaluate_js("refresh()")
                        time.sleep(0.3)
                        label = win.evaluate_js(
                            "document.getElementById('search').placeholder"
                        )
                        if label == tr("picker_search"):
                            result["locale_labels"].append(lang)
                    # Dispatch an explicit ZIP drag onto the isolated picker.
                    # It should flow through the real pywebview Python bridge,
                    # validate the pack and skip the two already-owned fixtures.
                    path_literal = json.dumps(str(pack_path))
                    win.evaluate_js(
                        "(() => {"
                        "const f=new File(['fixture'],'test-pack.zip');"
                        "Object.defineProperty(f,'pywebviewFullPath',"
                        "{value:" + path_literal + "});"
                        "const dt=new DataTransfer();dt.items.add(f);"
                        "window.dispatchEvent(new DragEvent('drop',"
                        "{bubbles:true,cancelable:true,dataTransfer:dt}));"
                        "return true;})()"
                    )
                    for _ in range(30):
                        hint = win.evaluate_js(
                            "document.getElementById('hint').textContent"
                        )
                        if hint == tr(
                            "picker_pack_imported", added=0, duplicate=2,
                            failed=0,
                        ):
                            result["zip_drop"] = True
                            break
                        time.sleep(0.1)

                    # Click real GIF tab, request a candidate through pywebview
                    # JS->Python bridge, inspect both animated thumbnails, then
                    # cancel it. Never call paste_gif_preview during smoke QA.
                    win.evaluate_js(
                        "state.tab='gif';state.query='';render();"
                        "void openGifPreview(state.items.find("
                        "i => i.name === 'synthetic-animation'))"
                    )
                    for _ in range(60):
                        ready = bool(win.evaluate_js(
                            "!document.getElementById('gif-accept').disabled "
                            "&& !document.getElementById('gif-compare').classList"
                            ".contains('hidden')"
                        ))
                        if ready:
                            result["gif_preview"] = bool(win.evaluate_js(
                                "['gif-source-image','gif-result-image'].every("
                                "id => {const i=document.getElementById(id);"
                                "return i.complete && i.naturalWidth > 0})"
                            ))
                            if result["gif_preview"]:
                                break
                        time.sleep(0.25)
                    win.evaluate_js("document.getElementById('gif-cancel').click()")
                    for _ in range(25):
                        if api._gif_preview is None:
                            result["gif_cancelled"] = True
                            break
                        time.sleep(0.1)
                    result["gif_source_preserved"] = (
                        hashlib.sha256(Path(lib_gif_path).read_bytes()).hexdigest()
                        == gif_digest
                    )
                    # Explicit accept path: substitute an inert controller,
                    # never call global clipboard or send key events.
                    # The actual JS->Python bridge must accept a generated
                    # candidate and exit the dialog without touching Discord.
                    calls = []
                    api._ctrl = SimpleNamespace(
                        select=lambda id_, mode="file", override_path=None:
                        calls.append((id_, mode, override_path)) or True
                    )
                    win.evaluate_js(
                        "void openGifPreview(state.items.find("
                        "i => i.name === 'synthetic-animation'))"
                    )
                    for _ in range(60):
                        if bool(win.evaluate_js(
                            "!document.getElementById('gif-accept').disabled"
                        )):
                            break
                        time.sleep(0.25)
                    win.evaluate_js("document.getElementById('gif-accept').click()")
                    for _ in range(25):
                        if calls:
                            break
                        time.sleep(0.1)
                    result["gif_mock_accept"] = bool(
                        len(calls) == 1 and calls[0][0] == gif_item["id"]
                        and calls[0][1] == "optimized"
                        and calls[0][2] and Path(calls[0][2]).is_file()
                    )
                    # Test the real WebView2 renderer, not just the Python
                    # filesystem scanner. All 5,000 items are synthetic and
                    # use a tiny 1x1 data URL, never private media.
                    win.evaluate_js("window.__fixtureItems=state.items;")
                    for n in (100, 1000, 5000):
                        script = """(() => {
                          const n = __N__;
                          const img = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
                          state.items = Array.from({length:n}, (_,i) => ({
                            id: String(i), type: 'emoji', name: 'sample-' + i,
                            keywords: [], url: img, animated:false,
                            convert_warning:false, favorite:false,
                            collection:'', is_folder:false, can_url:false
                          }));
                          state.tab = 'emoji'; state.query = '';
                          state.collection = '__all__'; state.recent = [];
                          let t = performance.now(); render();
                          const render_ms = Math.round(performance.now()-t);
                          const displayed = document.querySelectorAll('.cell').length;
                          state.query='sample-' + Math.min(n-1, 499); t=performance.now(); render();
                          return {items:n,render_ms,
                            search_ms: Math.round(performance.now()-t),
                            dom_cells:displayed,
                            filtered_cells:document.querySelectorAll('.cell').length};
                        })()""".replace("__N__", str(n))
                        record = win.evaluate_js(script)
                        result["gallery_benchmarks"].append(record)
                    result["gallery_5k"] = all(
                        r["dom_cells"] == r["items"]
                        and r["render_ms"] < 3000
                        and r["filtered_cells"] >= 1
                        for r in result["gallery_benchmarks"]
                    )
                    win.evaluate_js(
                        "state.items=window.__fixtureItems;"
                        "state.query='';render();"
                    )
            except Exception as e:
                errors.append(type(e).__name__ + ": " + str(e)[:300])
            finally:
                try:
                    win.destroy()
                except Exception as e:
                    errors.append("Destroy: " + repr(e))
        try:
            webview.start(examine, gui="edgechromium", http_server=False, debug=False)
        except Exception as e:
            errors.append(type(e).__name__ + ": " + str(e)[:300])
        finally:
            server.stop()
        result["errors"] = errors
        result["passed"] = bool(
            result["native_webview2"] and result["items"] == 3
            and result["tabs"] == 3 and result["settings"]
            and result["pack_buttons"] and result["search"]
            and result["asset_images_loaded"]
            and len(result["locale_labels"]) == 5 and result["zip_drop"]
            and result["gif_preview"] and result["gif_cancelled"]
            and result["gif_source_preserved"] and result["gif_mock_accept"]
            and result["gallery_5k"] and not errors
        )
        print("NOTRO_NATIVE_QA=" + json.dumps(result, ensure_ascii=True), flush=True)
        return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
