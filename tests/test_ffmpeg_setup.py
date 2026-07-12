# -*- coding: utf-8 -*-
import os

import notro_app.ffmpeg_setup as fs


def test_prefers_downloaded_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(fs.config, "BIN_DIR", str(tmp_path))
    exe = tmp_path / "ffmpeg.exe"
    exe.write_bytes(b"x")
    monkeypatch.setattr(fs.shutil, "which", lambda _: r"C:\other\ffmpeg.exe")
    assert fs.find_ffmpeg() == str(exe)          # 내려받은 것이 우선


def test_falls_back_to_path(tmp_path, monkeypatch):
    monkeypatch.setattr(fs.config, "BIN_DIR", str(tmp_path))   # 비어 있음
    monkeypatch.setattr(fs.shutil, "which", lambda _: r"C:\sys\ffmpeg.exe")
    assert fs.find_ffmpeg() == r"C:\sys\ffmpeg.exe"


def test_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(fs.config, "BIN_DIR", str(tmp_path))
    monkeypatch.setattr(fs.shutil, "which", lambda _: None)
    assert fs.find_ffmpeg() is None


def test_pick_wheel_selects_win_amd64_with_sha():
    data = {
        "info": {"version": "0.6.0"},
        "releases": {
            "0.6.0": [
                {"filename": "imageio_ffmpeg-0.6.0-py3-none-macosx.whl",
                 "url": "https://x/mac.whl", "digests": {"sha256": "aaa"}},
                {"filename": "imageio_ffmpeg-0.6.0-py3-none-win_amd64.whl",
                 "url": "https://x/win.whl", "digests": {"sha256": "bbb"}},
            ]
        },
    }
    assert fs._pick_wheel(data) == ("https://x/win.whl", "bbb")


def test_pick_wheel_returns_none_when_no_windows_wheel():
    data = {"info": {"version": "1.0"},
            "releases": {"1.0": [{"filename": "x-1.0-py3-none-any.whl",
                                  "url": "u", "digests": {"sha256": "s"}}]}}
    assert fs._pick_wheel(data) is None


def test_pick_binary_finds_windows_exe():
    names = [
        "imageio_ffmpeg/__init__.py",
        "imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.1",
        "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe",
    ]
    assert fs._pick_binary(names) == "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"


def test_pick_binary_returns_none_when_absent():
    assert fs._pick_binary(["a.py", "b.txt"]) is None
