"""Local media server must stream registered media, without leaking other paths."""
from urllib.error import HTTPError
from urllib.request import urlopen

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
