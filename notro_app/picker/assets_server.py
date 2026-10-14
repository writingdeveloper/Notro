# -*- coding: utf-8 -*-
"""피커 자산 로컬 HTTP 서버 (127.0.0.1 전용).

WebView2는 페이지 origin과 무관하게 file:// 서브리소스 로드를 차단하므로,
라이브러리 자산(등록 캐시 + 감시 폴더의 임의 경로 파일)을 item id 기준으로
127.0.0.1의 임의 포트에서 스트리밍한다. 경로가 URL에 노출되지 않고
resolver(id 조회)를 통해서만 파일에 접근한다.
"""

from __future__ import annotations

import mimetypes
import os
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AssetServer:
    """resolver: item_id -> 절대 경로 (모르는 id면 None)."""

    def __init__(self, resolver):
        self._resolver = resolver
        self._httpd: ThreadingHTTPServer | None = None
        self.port = 0
        # Per-server capability: a random localhost port alone is not an
        # authentication boundary. The token does not contain library data.
        self._capability = secrets.token_urlsafe(32)
        # Temporary GIF previews are in the same private localhost capability
        # namespace as library items, but never written to the user library.
        self._temporary: dict[str, str] = {}
        self._temporary_lock = threading.Lock()

    def register_temporary_asset(self, path: str) -> str:
        """Expose a generated QA/preview file without changing library.json."""
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        key = "gif-preview:" + secrets.token_urlsafe(24)
        with self._temporary_lock:
            self._temporary[key] = path
        return key

    def release_temporary_asset(self, item_id: str) -> None:
        with self._temporary_lock:
            self._temporary.pop(item_id, None)

    def start(self) -> int:
        resolver = self._resolver
        capability = self._capability
        temporary = self._temporary
        temporary_lock = self._temporary_lock

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 (http.server 규약)
                # Reject browser DNS-rebinding aliases and forged virtual
                # hosts. The picker uses the exact 127.0.0.1 URL below.
                expected_host = f"127.0.0.1:{self.server.server_port}"
                if self.headers.get("Host", "") != expected_host:
                    self.send_error(403)
                    return
                prefix = f"/asset/{capability}/"
                if not self.path.startswith(prefix):
                    self.send_error(404)
                    return
                item_id = urllib.parse.unquote(self.path[len(prefix):])
                try:
                    with temporary_lock:
                        path = temporary.get(item_id)
                    if path is None:
                        path = resolver(item_id)
                except Exception:
                    path = None
                if not path or not os.path.isfile(path):
                    self.send_error(404)
                    return
                ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
                # Open before emitting 200; watched-folder assets can be moved
                # between resolve() and open(), which must return 404 rather
                # than a partially written 200 response with invalid headers.
                try:
                    source = open(path, "rb")
                except OSError:
                    self.send_error(404)
                    return
                with source:
                    try:
                        size = os.fstat(source.fileno()).st_size
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(size))
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        remaining = size
                        # Keep per-request memory bounded for large GIFs.
                        while remaining > 0:
                            chunk = source.read(min(65536, remaining))
                            if not chunk:
                                break  # file was truncated after fstat
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    except (ConnectionAbortedError, BrokenPipeError, OSError):
                        pass

            def log_message(self, *args):  # 콘솔 소음 제거
                pass

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._httpd.server_address[1]
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        return self.port

    def url_for(self, item_id: str) -> str:
        return f"http://127.0.0.1:{self.port}/asset/{self._capability}/{urllib.parse.quote(item_id, safe='')}"

    def stop(self) -> None:
        with self._temporary_lock:
            self._temporary.clear()
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
