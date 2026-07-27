"""설정/임시 파일 관리 (레지스트리를 건드리지 않는 부분만)."""

import os
import time

from notro_app import config


def _age(path, days):
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def test_cleanup_temp_removes_only_old_files(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TEMP_DIR", str(tmp_path))
    old = tmp_path / "capture_old.webp"
    fresh = tmp_path / "capture_new.webp"
    old.write_bytes(b"x")
    fresh.write_bytes(b"x")
    _age(old, 3)

    config.cleanup_temp()

    assert not old.exists()
    assert fresh.exists()


def test_cleanup_temp_survives_a_directory(tmp_path, monkeypatch):
    """업데이터의 `update` 폴더 하나 때문에 정리가 통째로 멈추던 회귀를 잡는다.

    예전 구현은 루프 전체를 try 하나로 감쌌기 때문에 os.remove가 디렉터리에서
    던지는 순간 그 뒤 파일은 검사조차 되지 않았다 — 임시 폴더가 무한히 자란다.
    """
    monkeypatch.setattr(config, "TEMP_DIR", str(tmp_path))
    update_dir = tmp_path / "update"
    update_dir.mkdir()
    (update_dir / "Notro.exe").write_bytes(b"payload")
    _age(update_dir, 3)
    # 사전순으로 디렉터리 뒤에 오는 이름 — 예전 구현이면 여기까지 오지 못한다
    stale = tmp_path / "zz_old.png"
    stale.write_bytes(b"x")
    _age(stale, 3)

    config.cleanup_temp()

    assert not stale.exists(), "디렉터리 뒤의 오래된 파일도 정리돼야 한다"
    assert (update_dir / "Notro.exe").exists(), "남의 폴더는 건드리지 않는다"


def test_cleanup_temp_ignores_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TEMP_DIR", str(tmp_path / "gone"))
    config.cleanup_temp()  # 예외가 나가지 않으면 성공
