# -*- coding: utf-8 -*-
"""메인 감시 루프: 클립보드의 큰 이미지를 자동 압축해 파일로 교체."""

from __future__ import annotations

import io
import os
import threading
import time
from datetime import datetime

from PIL import Image, ImageGrab

from . import APP_NAME
from . import clipboard_win as cb
from . import compress, config
from .i18n import tr


class Monitor:
    def __init__(self):
        self.enabled = True
        self.stop_flag = False
        self.last_seq = cb.get_sequence_number()
        self.status_cb = None  # 트레이 알림 콜백
        self.history = []  # 처리 내역: {time, path, orig_mb, new_mb, pct}
        self.history_lock = threading.Lock()  # 감시 스레드 ↔ 트레이 메뉴 스레드 동시 접근 보호
        self.on_history_change = None  # 트레이 메뉴 갱신 콜백
        self.on_video_oversize = None  # 한도 초과 비디오 감지 콜백 (app.py가 배선)

    def notify(self, title, msg):
        if self.status_cb:
            try:
                self.status_cb(title, msg)
            except Exception:
                pass

    def process_clipboard(self):
        if cb.clipboard_has_marker():
            return

        img = None
        orig_bytes = None

        # 1) 크로미움 계열(디스코드 등)이 넣은 PNG 원본이 있으면 그 실제 크기로 판단.
        #    디스코드는 붙여넣기 시 이 PNG를 그대로 업로드하므로 가장 정확하다.
        try:
            png = cb.get_clipboard_png()
        except Exception:
            png = None
        if png is not None:
            if len(png) <= config.LIMIT_BYTES:
                return  # 실제 PNG가 한도 이하 → 그대로 둠
            orig_bytes = len(png)
            try:
                img = Image.open(io.BytesIO(png))
                img.load()
            except Exception:
                img = None
            if img is not None:
                self._compress_and_replace(img, orig_bytes)
                return

        # 2) 일반 비트맵 / 복사된 파일 처리
        try:
            content = ImageGrab.grabclipboard()
        except Exception:
            return

        if isinstance(content, Image.Image):
            img = content
        elif isinstance(content, list):
            # 파일이 복사된 경우(CF_HDROP). 비디오는 감지만 하고 오케스트레이션에
            # 위임한다 — 인코딩은 수십 초라 감시 루프를 막으면 안 된다.
            paths = [p for p in content if isinstance(p, str)]
            if len(paths) != 1:
                return
            path = paths[0]
            ext = os.path.splitext(path)[1].lower()

            if ext in config.VIDEO_EXTS:
                try:
                    size = os.path.getsize(path)
                except OSError:
                    return
                if size > config.LIMIT_BYTES and self.on_video_oversize:
                    self.on_video_oversize(path)
                return

            if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"):
                try:
                    size = os.path.getsize(path)
                    if size > config.LIMIT_BYTES:
                        orig_bytes = size
                        img = Image.open(path)
                        img.load()
                except Exception:
                    return
            if img is None:
                return
        else:
            return

        # 비트맵이면 PNG 기준 용량으로 판단 (디스코드가 PNG로 변환해서 올리므로)
        if isinstance(content, Image.Image):
            orig_bytes = compress.estimate_png_size(img)
            if orig_bytes <= config.LIMIT_BYTES:
                return  # 한도 이하 → 그대로 둠

        self._compress_and_replace(img, orig_bytes)

    def _compress_and_replace(self, img: Image.Image, orig_bytes: int):
        result = compress.compress_image(img, config.LIMIT_BYTES)
        if result is None:
            self.notify(APP_NAME, tr("notify_compress_fail"))
            return

        data, ext = result
        out_path = os.path.join(
            config.TEMP_DIR, datetime.now().strftime("capture_%Y%m%d_%H%M%S_%f") + ext
        )
        with open(out_path, "wb") as f:
            f.write(data)

        if cb.set_clipboard_file(out_path):
            self.last_seq = cb.get_sequence_number()
            orig_mb = orig_bytes / 1024 / 1024
            new_mb = len(data) / 1024 / 1024
            pct = round((1 - new_mb / orig_mb) * 100) if orig_mb else 0
            with self.history_lock:
                self.history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "path": out_path,
                    "orig_mb": orig_mb,
                    "new_mb": new_mb,
                    "pct": pct,
                })
                del self.history[:-15]  # 최근 15개만 유지
            if self.on_history_change:
                try:
                    self.on_history_change()
                except Exception:
                    pass
            self.notify(
                APP_NAME,
                tr(
                    "notify_compress_done",
                    orig=orig_mb,
                    new=new_mb,
                    pct=pct,
                    fmt=ext[1:].upper(),
                ),
            )
        else:
            self.notify(APP_NAME, tr("notify_clipboard_fail"))

    def run(self):
        last_cleanup = time.time()
        while not self.stop_flag:
            time.sleep(config.POLL_INTERVAL)
            if time.time() - last_cleanup > 3600:  # 1시간마다 오래된 임시파일 정리
                config.cleanup_temp()
                last_cleanup = time.time()
            if not self.enabled:
                continue
            seq = cb.get_sequence_number()
            if seq != self.last_seq:
                self.last_seq = seq
                try:
                    self.process_clipboard()
                except Exception:
                    pass
        # 종료 시 임시 파일 정리 (1일 이상 지난 것)
        config.cleanup_temp()
