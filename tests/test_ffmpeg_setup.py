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
