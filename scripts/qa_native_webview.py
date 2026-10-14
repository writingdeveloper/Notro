#!/usr/bin/env python3
"""Isolated *native* Windows WebView2 UI smoke for Notro.

Does not launch, patch, access, post to, or capture Discord. Uses synthetic
temporary test-library assets. It never registers Notro hotkeys or changes
global clipboard/registry. It opens a separate QA window then closes it.
"""
from __future__ import annotations

import json
import tempfile
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import fetch, packs
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
                  "zip_drop": False}
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
                        if result["native_webview2"] and result["items"] == 2:
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)
                if result["native_webview2"] and result["items"] == 2:
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
            result["native_webview2"] and result["items"] == 2
            and result["tabs"] == 3 and result["settings"]
            and result["pack_buttons"] and result["search"]
            and result["asset_images_loaded"]
            and len(result["locale_labels"]) == 5 and result["zip_drop"]
            and not errors
        )
        print("NOTRO_NATIVE_QA=" + json.dumps(result, ensure_ascii=True), flush=True)
        return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
