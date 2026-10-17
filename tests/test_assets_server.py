"""Local media server must stream registered media, without leaking other paths."""
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from notro_app.picker.assets_server import AssetServer


def test_asset_server_streams_large_payload_and_rejects_unknown_id(tmp_path):
    data = (b"GIF89a" + b"x" * (250 * 1024))
    path = tmp_path / "asset.gif"
    path.write_bytes(data)
    server = AssetServer(lambda item_id: str(path) if item_id == "ok-id" else None)
    try:
        assert server.start() > 0
        with urlopen(server.url_for("ok-id"), timeout=5) as result:
            assert result.headers["Content-Length"] == str(len(data))
            assert result.read() == data
        with pytest.raises(HTTPError) as error:
            urlopen(server.url_for("not-found"), timeout=5)
        assert error.value.code == 404
    finally:
        server.stop()


def test_asset_requires_unknown_random_capability_and_own_host(tmp_path):
    path = tmp_path / "pic.png"
    path.write_bytes(b"png-fixture")
    server = AssetServer(lambda item_id: str(path) if item_id == "safe-id" else None)
    try:
        server.start()
        authorized = server.url_for("safe-id")
        assert "/asset/" in authorized and authorized.endswith("/safe-id")

        with pytest.raises(HTTPError) as missing:
            urlopen(f"http://127.0.0.1:{server.port}/asset/safe-id", timeout=5)
        assert missing.value.code == 404

        request = Request(authorized, headers={"Host": "untrusted.example"})
        with pytest.raises(HTTPError) as forged:
            urlopen(request, timeout=5)
        assert forged.value.code == 403

        with urlopen(authorized, timeout=5) as response:
            assert response.read() == path.read_bytes()
    finally:
        server.stop()


def test_asset_capability_is_per_server_instance():
    first = AssetServer(lambda item_id: None)
    second = AssetServer(lambda item_id: None)
    assert first._capability != second._capability
    assert len(first._capability) >= 32
