#!/usr/bin/env python3
"""Synthetic library benchmark (never touches actual %APPDATA%/Notro assets).

Use: python scripts/benchmark_library.py
Measures warmed/cold file scanning and Python search only. JS DOM rendering,
Discord interaction and memory footprint need independent Windows UI QA.
"""
from __future__ import annotations

import json
import tempfile
import time
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notro_app.library import Library


def measure(n: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="notro-bench-") as temp:
        root = Path(temp)
        watched = root / "watched"
        watched.mkdir()
        pic = root / "sample.png"
        Image.new("RGB", (1, 1), (100, 170, 210)).save(pic)
        data = pic.read_bytes()
        for index in range(n):
            (watched / f"item_{index:05d}.png").write_bytes(data)
        library = Library(str(root / "appdata"))
        library.add_folder(str(watched), "emoji")
        before = time.perf_counter()
        items = library.scan_folders()
        cold_ms = (time.perf_counter() - before) * 1000
        before = time.perf_counter()
        second = library.scan_folders()
        warm_ms = (time.perf_counter() - before) * 1000
        before = time.perf_counter()
        found = library.search(f"item_{n-1:05d}", "emoji")
        search_ms = (time.perf_counter() - before) * 1000
        assert len(items) == n and len(second) == n and len(found) == 1
        return {
            "items": n, "cold_scan_ms": round(cold_ms, 2),
            "warm_scan_ms": round(warm_ms, 2),
            "search_ms": round(search_ms, 2),
        }


if __name__ == "__main__":
    print(json.dumps([measure(n) for n in (100, 1000, 5000)]))
