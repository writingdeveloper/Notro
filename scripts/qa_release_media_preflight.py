#!/usr/bin/env python3
"""Release gate: deterministic real-byte media preflight without Discord access.

Creates synthetically padded, valid PNGs in a private temporary directory
and verifies free-account 20MiB upload threshold behavior. No global clipboard,
foreground application, or user library is read or written.
"""
from __future__ import annotations

import hashlib
import json
import random
import struct
import time
import sys
import tempfile
import zlib
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import config
from notro_app.picker.window import prepare_for_paste

MiB = 1024 * 1024


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_png_with_safe_ancillary_chunk(path: Path, target: int) -> None:
    """Put a valid private PNG ancillary chunk before IEND."""
    import io

    image = Image.new("RGB", (256, 256), (35, 105, 205))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    raw = buf.getvalue()
    assert raw.endswith(bytes.fromhex("0000000049454e44ae426082"))
    pad = target - len(raw) - 12
    assert pad > 0
    kind = b"npAD"
    data = b"\0" * pad
    crc = zlib.crc32(kind + data) & 0xffffffff
    chunk = struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
    path.write_bytes(raw[:-12] + chunk + raw[-12:])
    assert path.stat().st_size == target
    with Image.open(path) as parsed:
        parsed.verify()


def run() -> int:
    baseline_limit = config.LIMIT_MB
    summary = {"cases": [], "passed": False}
    try:
        config.set_limit_mb(20)
        with tempfile.TemporaryDirectory(prefix="notro-threshold-qa-") as tmp:
            root = Path(tmp)
            for label, size, unchanged in (
                ("under_19_5MiB", int(19.5 * MiB), True),
                ("exact_20MiB", 20 * MiB, True),
                ("over_20MiB_by_1_byte", 20 * MiB + 1, False),
                ("over_24MiB", 24 * MiB, False),
            ):
                source = root / ("한글 QA_" + label + ".png")
                make_png_with_safe_ancillary_chunk(source, size)
                before = sha256(source)
                prepared, warn = prepare_for_paste(
                    str(source), config.LIMIT_BYTES, str(root),
                    target_px=0,
                    upload_ceiling_bytes=config.UPLOAD_CEILING_BYTES,
                )
                result = Path(prepared)
                original_intact = sha256(source) == before
                assert original_intact
                if unchanged:
                    assert result == source and not warn
                else:
                    assert result != source and not warn
                    assert result.is_file()
                    assert result.stat().st_size <= config.LIMIT_BYTES
                    with Image.open(result) as decoded:
                        decoded.verify()
                summary["cases"].append({
                    "name": label, "size": size,
                    "path_preserved": result == source, "warn": warn,
                    "output_size": result.stat().st_size,
                    "source_hash_preserved": original_intact,
                })

            # Real image-pixel compression, not just a metadata-padded PNG.
            # Synthetic high-entropy RGB pixels remain local in this temp dir.
            # 3000x3000 noise PNG is ~27MB and must yield a decodable result.
            started = time.perf_counter()
            noisy = root / "한글_실제픽셀_27MB.png"
            rng = random.Random(44)
            pixels = rng.randbytes(3000 * 3000 * 3)
            bitmap = Image.frombytes("RGB", (3000, 3000), pixels)
            del pixels
            bitmap.save(noisy, format="PNG", compress_level=4)
            del bitmap
            assert noisy.stat().st_size > 24 * MiB
            noise_digest = sha256(noisy)
            result, warning = prepare_for_paste(
                str(noisy), config.LIMIT_BYTES, str(root),
                target_px=0, upload_ceiling_bytes=config.UPLOAD_CEILING_BYTES,
            )
            converted = Path(result)
            assert converted != noisy and not warning
            assert converted.stat().st_size <= config.LIMIT_BYTES
            assert sha256(noisy) == noise_digest
            with Image.open(converted) as generated:
                generated.verify()
            summary["real_pixel_png"] = {
                "input_bytes": noisy.stat().st_size,
                "output_bytes": converted.stat().st_size,
                "output_extension": converted.suffix.lower(),
                "source_hash_preserved": True,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
            }

            frames = [
                Image.new("RGB", (84, 84), c)
                for c in ((235, 20, 30), (20, 215, 100), (45, 55, 220))
            ]
            gif = root / "한글_애니메이션.gif"
            frames[0].save(gif, save_all=True,
                           append_images=frames[1:],
                           format="GIF", duration=80, loop=0)
            before = sha256(gif)
            path, warn = prepare_for_paste(
                str(gif), limit_bytes=100, temp_dir=str(root),
                target_px=0, upload_ceiling_bytes=120,
            )
            assert path == str(gif) and warn is True and sha256(gif) == before
            summary["oversized_gif"] = "warn_original_kept"
            summary["passed"] = True
    finally:
        config.set_limit_mb(baseline_limit)
    print("NOTRO_RELEASE_MEDIA_QA="+json.dumps(summary, ensure_ascii=True), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
