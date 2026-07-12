# -*- coding: utf-8 -*-
import notro_app.monitor as mon
from notro_app import config
from notro_app.monitor import Monitor


def test_oversize_video_triggers_callback(tmp_path, monkeypatch):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\x00" * (config.LIMIT_BYTES + 1))

    monkeypatch.setattr(mon.cb, "clipboard_has_marker", lambda: False)
    monkeypatch.setattr(mon.cb, "get_clipboard_png", lambda: None)
    monkeypatch.setattr(mon.ImageGrab, "grabclipboard", lambda: [str(clip)])

    m = Monitor()
    seen = []
    m.on_video_oversize = seen.append
    m.process_clipboard()
    assert seen == [str(clip)]


def test_small_video_is_ignored(tmp_path, monkeypatch):
    clip = tmp_path / "small.mp4"
    clip.write_bytes(b"\x00" * 1024)

    monkeypatch.setattr(mon.cb, "clipboard_has_marker", lambda: False)
    monkeypatch.setattr(mon.cb, "get_clipboard_png", lambda: None)
    monkeypatch.setattr(mon.ImageGrab, "grabclipboard", lambda: [str(clip)])

    m = Monitor()
    seen = []
    m.on_video_oversize = seen.append
    m.process_clipboard()
    assert seen == []


def test_image_path_still_uses_image_pipeline(tmp_path, monkeypatch):
    """비디오 분기가 기존 이미지 경로를 깨지 않는다."""
    png = tmp_path / "big.png"
    png.write_bytes(b"\x00" * (config.LIMIT_BYTES + 1))

    monkeypatch.setattr(mon.cb, "clipboard_has_marker", lambda: False)
    monkeypatch.setattr(mon.cb, "get_clipboard_png", lambda: None)
    monkeypatch.setattr(mon.ImageGrab, "grabclipboard", lambda: [str(png)])

    m = Monitor()
    called = []
    m.on_video_oversize = called.append
    m.process_clipboard()          # PIL이 열지 못해 조용히 반환되면 충분
    assert called == []            # 비디오 콜백은 호출되지 않아야 한다
