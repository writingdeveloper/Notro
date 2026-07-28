# -*- coding: utf-8 -*-
"""반자동 자동 업데이터 (GitHub Releases + SHA256 검증 + 인스톨러 silent 실행).

frozen(exe)일 때만 실제 의미가 있다. 개발 실행에서는 app.py가 기동하지 않는다.
신규 의존성 없이 표준 라이브러리만 사용한다."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import threading
import urllib.request

from . import __version__

REPO = "writingdeveloper/Notro"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_NAME = "NotroSetup.exe"
ASSET_SHA = ASSET_NAME + ".sha256"
CHECK_INTERVAL = 24 * 3600
CREATE_NO_WINDOW = 0x08000000


def parse_version(s: str) -> tuple[int, ...]:
    """'v2.1.0' / '2.2.0-beta' → (2,1,0). 접두 v와 pre-release/build 접미사 무시."""
    s = s.lstrip("vV").split("-")[0].split("+")[0]
    out = []
    for p in s.split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out)


def is_newer(latest_tag: str, current: str) -> bool:
    return parse_version(latest_tag) > parse_version(current)


def check_latest(opener=urllib.request.urlopen, timeout: int = 10):
    """GitHub Releases 최신본 조회 → {tag, exe_url, sha256_url} 또는 None.
    exe_url은 인스톨러(NotroSetup.exe) 자산을 가리킨다."""
    req = urllib.request.Request(
        API_LATEST,
        headers={"User-Agent": f"Notro/{__version__}",
                 "Accept": "application/vnd.github+json"})
    with opener(req, timeout=timeout) as r:
        data = json.load(r)
    tag = data.get("tag_name", "")
    exe_url = sha_url = None
    for a in data.get("assets", []):
        n = a.get("name") or ""
        if n == ASSET_NAME:
            exe_url = a.get("browser_download_url")
        elif n == ASSET_SHA:
            sha_url = a.get("browser_download_url")
    if not tag or not exe_url:
        return None
    return {"tag": tag, "exe_url": exe_url, "sha256_url": sha_url}


def _download(url: str, dest: str, timeout: int = 60) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": f"Notro/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_and_verify(release: dict, dest_dir: str, downloader=_download):
    """NotroSetup.exe를 내려받아 SHA256을 검증한다. 성공 시 경로, 아니면 None.
    sha256 자산이 없으면(구버전 릴리스) 자동 설치하지 않는다."""
    if not release.get("sha256_url"):
        return None
    os.makedirs(dest_dir, exist_ok=True)
    exe_path = os.path.join(dest_dir, ASSET_NAME)
    sha_path = exe_path + ".sha256"
    downloader(release["exe_url"], exe_path)
    downloader(release["sha256_url"], sha_path)
    with open(sha_path, "r", encoding="utf-8", errors="ignore") as f:
        expected = f.read().split()[0].strip().lower()
    if _sha256(exe_path).lower() != expected:
        try:
            os.remove(exe_path)
        except OSError:
            pass
        return None
    return exe_path


def build_apply_bat(pid: int, setup_path: str) -> str:
    """앱(pid) 종료 대기 → NotroSetup.exe를 silent 설치. **재실행은 하지 않는다.**

    재실행은 인스톨러의 `[Run]` 항목(postinstall 플래그 없음)이 설치가 완전히
    끝난 직후 담당한다. 이전에는 이 배치가 설치 명령 직후 곧바로 앱을 재실행했는데,
    Inno Setup은 실행 시 자신을 임시 폴더로 복사해 재실행하므로 원본 프로세스가
    **설치 도중 조기 반환**하고, 배치가 아직 교체 중인 exe를 실행해 onefile 부트로더의
    Python DLL 압축 해제가 실패했다("Failed to load Python DLL ... LoadLibrary").
    설치 완료 시점을 정확히 아는 Inno에게 재실행을 맡겨 이 경합을 제거한다."""
    return f'''@echo off
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  timeout /t 1 /nobreak >NUL
  goto wait
)
"{setup_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
del "%~f0"
'''


def oem_encoding() -> str:
    r"""cmd.exe가 **배치 파일 내용을 읽을 때** 쓰는 코드페이지 이름.

    배치를 UTF-8로 쓰면 경로에 ASCII 밖 문자가 있는 순간 cmd가 그 줄을 통째로
    잘못 읽는다. 한국어 Windows에서 계정명이 한글이면 `%TEMP%`가
    `C:\Users\홍길동\AppData\Local\Temp\...`가 되므로 실제로 흔한 경우다
    (재현 확인: UTF-8 배치는 아무 줄도 실행되지 않고, cp949 배치는 정상).

    ANSI(mbcs)가 아니라 **OEM**을 쓴다 — 한중일은 둘이 같지만 서유럽은
    ANSI 1252 / OEM 850으로 갈린다.
    """
    try:
        return "cp" + str(ctypes.windll.kernel32.GetOEMCP())
    except Exception:
        return "mbcs"


def apply_and_restart(setup_path: str, _spawn=None) -> None:
    """헬퍼 배치를 만들어 실행하고 즉시 반환한다. 배치가 현재 앱(pid) 종료를 기다린
    뒤 NotroSetup.exe를 silent 설치한다. 재실행은 인스톨러 `[Run]`(설치 완료 직후)이
    담당하므로 배치는 설치만 트리거한다 — 배치가 교체 중 exe를 조기 실행하던 경합을
    없앤다. 호출자는 이 함수 직후 앱을 종료해야 한다(트레이 on_quit). _spawn은 테스트용.

    배치는 cmd가 읽는 코드페이지로 쓴다. 경로에 그 코드페이지로 표현할 수 없는
    문자가 있으면(예: 계정명에 이모지) 배치를 포기하고 인스톨러를 직접 실행한다 —
    installer.iss의 CloseApplications=yes가 실행 중인 Notro.exe를 알아서 닫는다.
    조용히 아무 일도 일어나지 않는 것보다 낫다.
    """
    spawn = _spawn or subprocess.Popen
    bat_dir = os.path.dirname(os.path.abspath(setup_path))
    bat = os.path.join(bat_dir, "apply_update.bat")
    body = build_apply_bat(os.getpid(), setup_path)
    try:
        with open(bat, "w", encoding=oem_encoding()) as f:
            f.write(body)
    except (UnicodeEncodeError, LookupError, OSError):
        spawn([setup_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
              creationflags=CREATE_NO_WINDOW, close_fds=True)
        return
    spawn(["cmd", "/c", bat], creationflags=CREATE_NO_WINDOW, close_fds=True)


class UpdateChecker(threading.Thread):
    """백그라운드로 시작 시 + interval마다 확인. 준비되면 on_ready(tag, setup) 호출.

    _check/_download는 테스트 주입용. 실제로는 check_latest / download_and_verify."""

    def __init__(self, dest_dir, on_ready, is_enabled=lambda: True,
                 interval=CHECK_INTERVAL, _check=None, _download=None):
        super().__init__(daemon=True)
        self.dest_dir = dest_dir
        self.on_ready = on_ready
        self.is_enabled = is_enabled
        self.interval = interval
        self._check = _check or check_latest
        self._download = _download or (lambda release, dest: download_and_verify(release, dest))
        self._stop = threading.Event()
        self.ready_exe = None
        self.ready_tag = None

    def check_once(self):
        if not self.is_enabled():
            return
        try:
            rel = self._check()
        except Exception:
            return
        if not rel or not is_newer(rel["tag"], __version__):
            return
        try:
            exe = self._download(rel, self.dest_dir)
        except Exception:
            exe = None
        if exe:
            self.ready_exe, self.ready_tag = exe, rel["tag"]
            self.on_ready(rel["tag"], exe)

    def run(self):
        while not self._stop.is_set():
            self.check_once()
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
