# -*- coding: utf-8 -*-
"""Opt-in, size-bounded GIF optimization for Notro's preview/paste flow.

Never rewrites source/library files or runs unattended. The caller must show
an animated side-by-side preview and wait for explicit user acceptance before
the optimized file is placed on the clipboard.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageSequence, UnidentifiedImageError

from .resize import save_gif

MAX_SOURCE_BYTES = 60 * 1024 * 1024
MAX_FRAMES = 180
MAX_TOTAL_PIXELS = 25_000_000
MAX_DIMENSION = 4096

# Conservative first: color reduction at source dimensions before downscaling.
# The preview clearly discloses both palette and resolution changes.
_TRIALS = (
    (1.00, 128), (1.00, 64), (0.85, 128), (0.85, 64),
    (0.70, 64), (0.60, 48), (0.50, 32), (0.40, 24),
)


class GIFOptimizationError(ValueError):
    """Safe, user-displayable category; underlying paths stay private."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GIFCandidate:
    path: str
    original_bytes: int
    optimized_bytes: int
    original_size: tuple[int, int]
    optimized_size: tuple[int, int]
    frames: int
    duration_ms: int
    colors: int
    scale: float


def optimize_gif(source: str, output_dir: str, target_bytes: int) -> GIFCandidate:
    """Return a *new* GIF below the encoding target, or fail without mutation.

    The whole animation is decoded only for bounded inputs to avoid pathological
    frame counts / decompression bombs. Each candidate is animated, maintains
    the sum of frame delays and preserves the source loop policy.
    """
    try:
        stat = os.stat(source)
    except OSError as exc:
        raise GIFOptimizationError("missing") from exc
    if not source.lower().endswith(".gif"):
        raise GIFOptimizationError("unsupported")
    if stat.st_size <= target_bytes:
        raise GIFOptimizationError("already_fits")
    if stat.st_size > MAX_SOURCE_BYTES or target_bytes <= 0:
        raise GIFOptimizationError("too_complex")

    frames: list[Image.Image] = []
    durations: list[int] = []
    try:
        with Image.open(source) as im:
            if im.format != "GIF" or getattr(im, "n_frames", 1) < 2:
                raise GIFOptimizationError("not_animated")
            count = im.n_frames
            w, h = im.size
            if (count > MAX_FRAMES or w > MAX_DIMENSION or h > MAX_DIMENSION
                    or w * h * count > MAX_TOTAL_PIXELS):
                raise GIFOptimizationError("too_complex")
            loop = im.info.get("loop", 0)
            loop = int(loop) if isinstance(loop, int) and 0 <= loop <= 65535 else 0
            for frame in ImageSequence.Iterator(im):
                frames.append(frame.convert("RGBA").copy())
                durations.append(max(20, int(frame.info.get("duration", 50) or 50)))
    except (OSError, UnidentifiedImageError, ValueError, MemoryError) as exc:
        if isinstance(exc, GIFOptimizationError):
            raise
        raise GIFOptimizationError("invalid") from exc

    if len(frames) < 2:
        raise GIFOptimizationError("not_animated")

    os.makedirs(output_dir, exist_ok=True)
    candidates: list[str] = []
    selected: GIFCandidate | None = None
    success = False
    try:
        for scale, colors in _TRIALS:
            size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
            if size[0] < 24 or size[1] < 24:
                break  # never aggressively shrink to an unusable thumbnail
            fd, path = tempfile.mkstemp(
                prefix="notro_gif_preview_", suffix=".gif", dir=output_dir)
            os.close(fd)
            candidates.append(path)
            if scale == 1.0:
                resized = frames
            else:
                resized = [f.resize(size, Image.Resampling.LANCZOS) for f in frames]
            save_gif(resized, durations, path, colors=colors,
                     loop=loop, optimize=True)
            actual_bytes = os.path.getsize(path)
            if actual_bytes >= stat.st_size or actual_bytes > target_bytes:
                continue
            with Image.open(path) as rendered:
                if not getattr(rendered, "is_animated", False):
                    continue
                if (rendered.width != size[0] or rendered.height != size[1]
                        or rendered.n_frames < 2):
                    continue
                rendered_duration = sum(
                    max(20, int(frame.info.get("duration", 50) or 50))
                    for frame in ImageSequence.Iterator(rendered))
                if abs(rendered_duration - sum(durations)) > 20 * len(durations):
                    continue
            selected = GIFCandidate(
                path=path, original_bytes=stat.st_size,
                optimized_bytes=actual_bytes, original_size=(w, h),
                optimized_size=size, frames=count,
                duration_ms=sum(durations), colors=colors, scale=scale,
            )
            break
        if selected is None:
            raise GIFOptimizationError("cannot_fit")
        after = os.stat(source)
        if after.st_size != stat.st_size or after.st_mtime_ns != stat.st_mtime_ns:
            raise GIFOptimizationError("source_changed")
        success = True
        return selected
    except GIFOptimizationError:
        raise
    except (OSError, MemoryError, ValueError) as exc:
        raise GIFOptimizationError("encode") from exc
    finally:
        for path in candidates:
            if not success or selected is None or path != selected.path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
