# -*- coding: utf-8 -*-
"""Opt-in GIF preview bridge. Used by PickerApi; not a Discord integration."""
from __future__ import annotations

import os
import threading

from .. import config, gif_optimizer, resize


class GifPreviewMixin:
    """Keep a single candidate in a private temp file until user acts.

    The pywebview API inspects public methods on PickerApi, so these methods
    intentionally appear there through inheritance. State remains private.
    """

    def _init_gif_preview(self) -> None:
        self._gif_lock = threading.Lock()
        self._gif_preview = None

    def _drop_gif_locked(self, keep_file: bool = False) -> None:
        preview = self._gif_preview
        self._gif_preview = None
        if preview is None:
            return
        self._asset_server.release_temporary_asset(preview["token"])
        if preview.get("original_token"):
            self._asset_server.release_temporary_asset(preview["original_token"])
        if not keep_file:
            try:
                os.remove(preview["candidate_path"])
            except OSError:
                pass

    def discard_gif_preview(self, token: str = "") -> bool:
        """Cancel a generated candidate without touching the source GIF."""
        with self._gif_lock:
            if not self._gif_preview:
                return False
            if token and token != self._gif_preview["token"]:
                return False
            self._drop_gif_locked()
            return True

    def preview_gif(self, item_id: str) -> dict:
        """Prepare a bounded GIF candidate; NEVER paste on preview request."""
        with self._gif_lock:
            self._drop_gif_locked()
            item = self._library.resolve(item_id)
            if not item or item.get("type") not in ("gif", "sticker", "emoji"):
                return {"ok": False, "error": "unsupported"}
            source_path = self._library.asset_path(item)
            path = resize.normalize(
                source_path, resize.target_px_for(item["type"]), config.TEMP_DIR)
            if not path.lower().endswith(".gif"):
                return {"ok": False, "error": "unsupported"}
            try:
                source_stat = os.stat(source_path)
                prepared_stat = os.stat(path)
            except OSError:
                return {"ok": False, "error": "missing"}
            # This feature is only needed when the animation *actually*
            # exceeds the configured upload ceiling. The 95% safety target
            # applies to its output, not the prompt/preview trigger.
            if prepared_stat.st_size <= config.UPLOAD_CEILING_BYTES:
                return {"ok": False, "error": "already_fits"}
            try:
                result = gif_optimizer.optimize_gif(
                    path, config.TEMP_DIR, config.LIMIT_BYTES)
            except gif_optimizer.GIFOptimizationError as exc:
                return {"ok": False, "error": exc.code}
            original_token = None
            try:
                token = self._asset_server.register_temporary_asset(result.path)
                if path != source_path:
                    # The user sees the *prepared/normalized* source in the
                    # left preview, matching the byte count being compared.
                    original_token = self._asset_server.register_temporary_asset(path)
            except Exception:
                if "token" in locals():
                    self._asset_server.release_temporary_asset(token)
                try:
                    os.remove(result.path)
                except OSError:
                    pass
                return {"ok": False, "error": "encode"}
            self._gif_preview = {
                "token": token, "original_token": original_token,
                "item_id": item_id, "source_path": source_path,
                "source_sig": (source_stat.st_mtime_ns, source_stat.st_size),
                "prepared_path": path,
                "prepared_sig": (prepared_stat.st_mtime_ns, prepared_stat.st_size),
                "candidate_path": result.path,
                "original_limit_bytes": config.LIMIT_BYTES,
                "original_upload_ceiling_bytes": config.UPLOAD_CEILING_BYTES,
            }
            return {
                "ok": True, "token": token, "item_id": item_id,
                "original_url": self._asset_server.url_for(
                    original_token or item_id),
                "optimized_url": self._asset_server.url_for(token),
                "original_bytes": result.original_bytes,
                "optimized_bytes": result.optimized_bytes,
                "original_size": list(result.original_size),
                "optimized_size": list(result.optimized_size),
                "frames": result.frames, "duration_ms": result.duration_ms,
                "colors": result.colors,
            }

    def paste_gif_preview(self, item_id: str, token: str) -> dict:
        """Paste accepted candidate but never auto-send an unreviewed message."""
        with self._gif_lock:
            preview = self._gif_preview
            if not preview or preview["token"] != token or preview["item_id"] != item_id:
                return {"ok": False, "error": "outdated"}
            try:
                stat = os.stat(preview["source_path"])
                prepared = os.stat(preview["prepared_path"])
                valid = (
                    (stat.st_mtime_ns, stat.st_size) == preview["source_sig"]
                    and (prepared.st_mtime_ns, prepared.st_size)
                    == preview["prepared_sig"]
                    and config.LIMIT_BYTES == preview["original_limit_bytes"]
                    and config.UPLOAD_CEILING_BYTES ==
                    preview["original_upload_ceiling_bytes"]
                    and os.path.getsize(preview["candidate_path"]) <= config.LIMIT_BYTES
                    and self._library.resolve(item_id) is not None
                )
            except OSError:
                valid = False
            if not valid:
                self._drop_gif_locked()
                return {"ok": False, "error": "outdated"}
            candidate_path = preview["candidate_path"]
            self._drop_gif_locked(keep_file=True)
        if self._ctrl is None:
            return {"ok": False, "error": "outdated"}
        pasted = self._ctrl.select(
            item_id, mode="optimized", override_path=candidate_path)
        return {"ok": bool(pasted)}
