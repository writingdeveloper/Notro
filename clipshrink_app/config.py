# -*- coding: utf-8 -*-
"""설정(레지스트리)·경로·업로드 한도·시작 프로그램·단일 인스턴스."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import sys
import tempfile
import time

from . import APP_NAME

# ===================== 설정 =====================
LIMIT_MB = 10           # 디스코드 무료 업로드 한도 (MB)
SAFETY = 0.95           # 안전 마진 (10MB의 95% = 9.5MB 목표)
POLL_INTERVAL = 0.4     # 클립보드 확인 주기 (초)
# ================================================


def compute_limit_bytes(mb: int) -> int:
    """업로드 한도(MB)에 안전 마진을 적용한 바이트 한도."""
    return int(mb * 1024 * 1024 * SAFETY)


LIMIT_BYTES = compute_limit_bytes(LIMIT_MB)


def set_limit_mb(mb: int) -> None:
    """런타임 업로드 한도 변경 (트레이 메뉴에서 호출)."""
    global LIMIT_MB, LIMIT_BYTES
    LIMIT_MB = mb
    LIMIT_BYTES = compute_limit_bytes(mb)


TEMP_DIR = os.path.join(tempfile.gettempdir(), "ClipShrink")
os.makedirs(TEMP_DIR, exist_ok=True)

# 피커 라이브러리 영구 데이터
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ClipShrink")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
SETTINGS_KEY = r"Software\ClipShrink"


# ---------- 시작 프로그램 등록 ----------
def get_launch_command() -> str:
    """현재 실행 형태(EXE 또는 스크립트)에 맞는 실행 명령을 만든다."""
    if getattr(sys, "frozen", False):  # PyInstaller EXE
        return f'"{sys.executable}"'
    script = os.path.abspath(sys.argv[0])
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{exe}" "{script}"'


def is_startup_registered() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value == get_launch_command()
    except OSError:
        return False


def set_startup(enable: bool):
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass


def get_setting_int(name: str, default: int = 0) -> int:
    r"""HKCU\Software\ClipShrink 아래의 DWORD 값을 읽는다 (없으면 default)."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return int(value)
    except (OSError, ValueError, TypeError):
        return default


def set_setting_int(name: str, value: int):
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))
    except OSError:
        pass


def get_setting_flag(name: str) -> bool:
    return bool(get_setting_int(name, 0))


def set_setting_flag(name: str, value: bool = True):
    set_setting_int(name, 1 if value else 0)


def get_setting_str(name: str, default: str = "") -> str:
    r"""HKCU\Software\ClipShrink 아래의 문자열 값을 읽는다 (없으면 default)."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except OSError:
        return default


def set_setting_str(name: str, value: str):
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    except OSError:
        pass


def ensure_single_instance():
    """이미 실행 중이면 조용히 종료 (자동 시작 + 수동 실행 중복 방지).

    use_last_error=True 핸들로 호출해야 CreateMutexW 직후의 GetLastError가
    신뢰 가능하다. 뮤텍스는 현재 세션 범위(Local\\)로 잡아 다중 사용자 환경에서
    다른 사용자 인스턴스를 막지 않는다. 핸들은 프로세스 생명주기 동안 유지되며
    종료 시 OS가 회수한다.
    """
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = wt.HANDLE
    k32.CreateMutexW.argtypes = [wt.LPVOID, wt.BOOL, wt.LPCWSTR]
    k32.CreateMutexW(None, False, "Local\\ClipShrink_SingleInstance")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)


def cleanup_temp():
    now = time.time()
    try:
        for name in os.listdir(TEMP_DIR):
            p = os.path.join(TEMP_DIR, name)
            if now - os.path.getmtime(p) > 86400:
                os.remove(p)
    except Exception:
        pass
