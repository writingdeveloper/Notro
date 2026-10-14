"""Opt-in GIF compression: animation, timing, no originals mutated and bounds."""
from __future__ import annotations

import hashlib
import os
import random
from pathlib import Path

import pytest
from PIL import Image, ImageSequence

from notro_app.gif_optimizer import (
    GIFOptimizationError, MAX_FRAMES, MAX_SOURCE_BYTES, optimize_gif,
)


def make_gif(tmp_path, frames=14, size=(100, 90)):
    rnd = random.Random(7)
    images = [
        Image.frombytes("RGB", size, rnd.randbytes(size[0] * size[1] * 3))
        for _ in range(frames)
    ]
    path = tmp_path / "original.gif"
    images[0].save(
        path, format="GIF", save_all=True, append_images=images[1:],
        duration=70, loop=2,
    )
    return path


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_optimized_gif_is_new_file_preserving_timing_and_loop(tmp_path):
    source = make_gif(tmp_path)
    before = checksum(source)
    candidate = optimize_gif(str(source), str(tmp_path / "temporary"),
                             int(source.stat().st_size * .65))
    assert os.path.exists(candidate.path) and candidate.path != str(source)
    assert candidate.optimized_bytes < candidate.original_bytes * .65
    assert candidate.colors <= 128
    assert checksum(source) == before

    with Image.open(source) as old, Image.open(candidate.path) as optimized:
        assert optimized.format == "GIF" and optimized.n_frames == old.n_frames
        assert optimized.info["loop"] == old.info["loop"] == 2
        assert optimized.size == candidate.optimized_size
        duration_old = sum(frame.info.get("duration", 0)
                           for frame in ImageSequence.Iterator(old))
        duration_new = sum(frame.info.get("duration", 0)
                           for frame in ImageSequence.Iterator(optimized))
        assert duration_old == duration_new == 980


def test_optimized_gif_may_downscale_only_after_palette_trials(tmp_path):
    source = make_gif(tmp_path)
    candidate = optimize_gif(str(source), str(tmp_path / "candidate"),
                             int(source.stat().st_size * .4))
    assert candidate.scale < 1.0
    assert max(candidate.optimized_size) < max(candidate.original_size)
    assert candidate.optimized_bytes < candidate.original_bytes * .4


def test_no_encode_for_already_fitting_source(tmp_path):
    source = make_gif(tmp_path)
    with pytest.raises(GIFOptimizationError) as exc:
        optimize_gif(str(source), str(tmp_path / "out"),
                     source.stat().st_size * 2)
    assert exc.value.code == "already_fits"
    assert not (tmp_path / "out").exists()


def test_gif_frame_count_limit_without_output(tmp_path):
    source = make_gif(tmp_path, frames=MAX_FRAMES + 1, size=(28, 28))
    with pytest.raises(GIFOptimizationError) as exc:
        optimize_gif(str(source), str(tmp_path / "out"), 1_000)
    assert exc.value.code == "too_complex"
    assert not (tmp_path / "out").exists()


def test_not_an_animated_gif_rejected(tmp_path):
    path = tmp_path / "still.gif"
    Image.new("RGB", (30, 30), "red").save(path, format="GIF")
    with pytest.raises(GIFOptimizationError) as exc:
        optimize_gif(str(path), str(tmp_path), 1)
    assert exc.value.code == "not_animated"


def test_invalid_gif_does_not_write_candidate(tmp_path):
    path = tmp_path / "bad.gif"
    path.write_bytes(b"GIF89a" + b"x" * 5000)
    with pytest.raises(GIFOptimizationError) as exc:
        optimize_gif(str(path), str(tmp_path / "tmp"), 100)
    assert exc.value.code == "invalid"
    assert not (tmp_path / "tmp").exists()


def test_oversized_gif_rejected_pre_decode(tmp_path):
    # Sparse test fixture: preflight must stop it before opening/allocating.
    path = tmp_path / "huge.gif"
    with open(path, "wb") as f:
        f.truncate(MAX_SOURCE_BYTES + 1)
    with pytest.raises(GIFOptimizationError) as exc:
        optimize_gif(str(path), str(tmp_path / "tmp"), 100)
    assert exc.value.code == "too_complex"
    assert not (tmp_path / "tmp").exists()
