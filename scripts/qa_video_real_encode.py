#!/usr/bin/env python3
"""Real local ffmpeg integration QA with generated media, no Discord access.

Verifies Notro probe/plan/encode plus trim/mute on a five-second synthetic
video+audio fixture under a temporary directory. No network or user media.
Run manually on an authorized Windows QA machine with local ffmpeg.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notro_app import ffmpeg_setup, video


def _sha256(path: Path) -> str:
    import hashlib as _h
    h = _h.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(65536), b""):
            h.update(part)
    return h.hexdigest()


def main() -> int:
    ffmpeg = ffmpeg_setup.find_ffmpeg()
    if not ffmpeg:
        raise SystemExit("ffmpeg not installed: cannot perform real encoder QA")
    result = {"passed": False, "cases": []}
    with tempfile.TemporaryDirectory(prefix="notro-real-video-qa-") as directory:
        root = Path(directory)
        source = root / "한글_게임영상_원본.mp4"
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=960x540:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=550:sample_rate=44100",
            "-t", "5", "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", "3500k", "-c:a", "aac", "-b:a", "128k",
            "-shortest", str(source),
        ]
        generate = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=40)
        assert generate.returncode == 0, generate.stderr.decode(
            errors="replace")[:500]
        initial_hash = _sha256(source)
        meta = video.probe(ffmpeg, str(source))
        assert meta is not None and meta.has_audio and meta.height == 540
        for name, size_cap, trim, mute in (
            ("compress_with_audio", 850_000, None, False),
            ("trim_2sec_and_mute", 450_000, (1.0, 3.0), True),
        ):
            output = root / (name + ".mp4")
            plan = video.plan_encode(
                meta, size_cap,
                start=trim[0] if trim else None,
                end=trim[1] if trim else None,
                mute=mute,
            )
            assert plan is not None
            started = time.perf_counter()
            ok = video.encode(ffmpeg, str(source), plan, str(output))
            if ok and output.stat().st_size > size_cap:
                retry = video.retry_plan(plan)
                assert retry is not None
                ok = video.encode(ffmpeg, str(source), retry, str(output))
            assert ok and output.stat().st_size <= size_cap
            encoded = video.probe(ffmpeg, str(output))
            assert encoded is not None
            assert encoded.has_audio == (not mute)
            expected_duration = 2 if trim else meta.duration
            assert abs(encoded.duration - expected_duration) < 0.2
            assert _sha256(source) == initial_hash
            result["cases"].append({
                "name": name,
                "original_bytes": source.stat().st_size,
                "encoded_bytes": output.stat().st_size,
                "original_resolution": [meta.width, meta.height],
                "encoded_resolution": [encoded.width, encoded.height],
                "frames_per_second": encoded.fps,
                "duration_seconds": encoded.duration,
                "audio_present": encoded.has_audio,
                "original_unchanged": True,
                "encode_seconds": round(time.perf_counter() - started, 2),
            })
        result["passed"] = True
    print("NOTRO_VIDEO_REAL_QA=" + json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
