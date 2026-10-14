"""Explicit GIF preview bridge with temporary files and source integrity guards."""
from __future__ import annotations

import hashlib
import os
import random
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from PIL import Image

from notro_app import config, fetch, resize
from notro_app.library import Library
from notro_app.picker.assets_server import AssetServer
from notro_app.picker.window import PickerApi


def gif_item(tmp_path):
    rnd = random.Random(8)
    src = tmp_path / "gif-source.gif"
    frames = [
        Image.frombytes("RGB", (100, 90), rnd.randbytes(100 * 90 * 3))
        for _ in range(14)
    ]
    frames[0].save(src, format="GIF", save_all=True,
                   append_images=frames[1:], duration=80, loop=2)
    library = Library(str(tmp_path / "library"))
    item = fetch.register_from_file(
        library, str(src), "gif", name="GIF before and after")
    return library, item


def setup(tmp_path, monkeypatch):
    library, item = gif_item(tmp_path)
    source = Path(library.asset_path(item))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(config, "LIMIT_BYTES", int(source.stat().st_size * .65))
    monkeypatch.setattr(config, "UPLOAD_CEILING_BYTES",
                        int(source.stat().st_size * .80))
    monkeypatch.setattr(config, "TEMP_DIR", str(tmp_path / "temporary"))
    monkeypatch.setattr(resize, "target_px_for", lambda t: 0)
    server = AssetServer(
        lambda id_: library.asset_path(found)
        if (found := library.resolve(id_)) else None,
    )
    server.start()
    api = PickerApi(library=library, asset_server=server)
    return library, item, source, digest, server, api


def test_preview_is_animated_private_and_never_writes_library(tmp_path, monkeypatch):
    library, item, source, digest, server, api = setup(tmp_path, monkeypatch)
    try:
        result = api.preview_gif(item["id"])
        assert result["ok"] and result["optimized_bytes"] < config.LIMIT_BYTES
        assert result["frames"] == 14
        assert result["original_size"] == [100, 90]
        assert len(library.items()) == 1
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
        with urlopen(result["optimized_url"], timeout=5) as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"].startswith("image/gif")
            assert len(resp.read()) == result["optimized_bytes"]
        assert api.discard_gif_preview(result["token"])
        assert len(server._temporary) == 0
        with pytest.raises(HTTPError):
            urlopen(result["optimized_url"], timeout=5)
    finally:
        server.stop()


def test_accept_pastes_prepared_candidate_without_library_change(tmp_path, monkeypatch):
    library, item, source, digest, server, api = setup(tmp_path, monkeypatch)
    calls = []
    api._ctrl = SimpleNamespace(
        select=lambda item_id, mode="file", override_path=None:
        calls.append((item_id, mode, override_path)) or True
    )
    try:
        result = api.preview_gif(item["id"])
        assert api.paste_gif_preview(item["id"], result["token"]) == {"ok": True}
        assert len(calls) == 1
        assert calls[0][:2] == (item["id"], "optimized")
        candidate_path = Path(calls[0][2])
        assert candidate_path.exists()
        assert candidate_path.stat().st_size == result["optimized_bytes"]
        assert len(library.items()) == 1
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
        assert not api.discard_gif_preview(result["token"])
        assert api.paste_gif_preview(item["id"], result["token"]) == {
            "ok": False, "error": "outdated",
        }
    finally:
        server.stop()


def test_mutated_original_blocks_accept_and_cleans_candidate(tmp_path, monkeypatch):
    _, item, source, _, server, api = setup(tmp_path, monkeypatch)
    try:
        result = api.preview_gif(item["id"])
        candidate_path = Path(server._temporary[result["token"]])
        source.write_bytes(source.read_bytes() + b"x")
        assert api.paste_gif_preview(item["id"], result["token"]) == {
            "ok": False, "error": "outdated",
        }
        assert not candidate_path.exists()
    finally:
        server.stop()


def test_changed_limit_blocks_accept(tmp_path, monkeypatch):
    _, item, _, _, server, api = setup(tmp_path, monkeypatch)
    try:
        result = api.preview_gif(item["id"])
        monkeypatch.setattr(config, "LIMIT_BYTES", config.LIMIT_BYTES + 1)
        assert api.paste_gif_preview(item["id"], result["token"]) == {
            "ok": False, "error": "outdated",
        }
    finally:
        server.stop()


def test_cancellation_does_not_remove_original_or_enter_clipboard(tmp_path, monkeypatch):
    _, item, source, digest, server, api = setup(tmp_path, monkeypatch)
    try:
        result = api.preview_gif(item["id"])
        candidate = Path(server._temporary[result["token"]])
        assert api.discard_gif_preview(result["token"])
        assert not candidate.exists()
        assert source.exists()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    finally:
        server.stop()


def test_unsupported_and_fitting_gif_are_safe(tmp_path, monkeypatch):
    _, item, source, _, server, api = setup(tmp_path, monkeypatch)
    try:
        assert api.preview_gif("not-an-item") == {
            "ok": False, "error": "unsupported",
        }
        monkeypatch.setattr(config, "LIMIT_BYTES", os.stat(source).st_size * 2)
        assert api.preview_gif(item["id"]) == {
            "ok": False, "error": "already_fits",
        }
    finally:
        server.stop()


def test_gif_between_safety_target_and_actual_ceiling_needs_no_preview(
        tmp_path, monkeypatch):
    _, item, source, _, server, api = setup(tmp_path, monkeypatch)
    try:
        # Between compression target and maximum upload threshold.
        monkeypatch.setattr(config, "LIMIT_BYTES",
                            int(source.stat().st_size * .65))
        monkeypatch.setattr(config, "UPLOAD_CEILING_BYTES",
                            source.stat().st_size + 10)
        assert api.preview_gif(item["id"]) == {
            "ok": False, "error": "already_fits",
        }
        assert not server._temporary
    finally:
        server.stop()
