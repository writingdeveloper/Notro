# Auto-Updater Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notro가 GitHub Releases를 확인해 새 버전을 반자동(감지·다운로드 자동, 교체·재시작은 사용자 동의)으로 설치한다.

**Architecture:** 신규 `notro_app/updater.py`가 GitHub Releases API 폴링, SHA256 검증 다운로드, 배치 헬퍼 자기교체를 담당한다. `UpdateChecker`(daemon 스레드)가 시작 시 + 24h 주기로 확인하고, 준비되면 콜백으로 트레이 알림/메뉴를 갱신한다. frozen(exe)일 때만 활성.

**Tech Stack:** Python 표준 라이브러리만 (urllib, hashlib, json, threading, subprocess). 신규 의존성 없음.

## Global Constraints

- 신규 서드파티 의존성 금지 — `urllib`, `hashlib`, `json`, `threading`, `subprocess`, `os`, `sys`만 사용.
- frozen(`getattr(sys, "frozen", False)`)일 때만 실제 동작. 개발 실행(`pythonw notro.py`)에선 UpdateChecker 미기동.
- 릴리스 자산 파일명 정확히: `Notro.exe`, `Notro.exe.sha256`.
- SHA256 자산이 없는 릴리스는 자동 설치하지 않는다(검증 불가 → 강등).
- i18n 신규 문자열은 5개 언어(en/ko/ja/zh/es) 전부 + `PICKER_STRING_KEYS`가 아닌 트레이용이므로 `tr()`로 직접 사용.
- 기존 pytest 62개가 회귀 없이 통과해야 한다.
- 레포: `writingdeveloper/Notro`.

---

### Task 1: 버전 파싱·비교

**Files:**
- Create: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `parse_version(s: str) -> tuple[int, ...]`, `is_newer(latest_tag: str, current: str) -> bool`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_updater.py`

```python
from notro_app import updater


def test_parse_version_strips_v_and_suffix():
    assert updater.parse_version("v2.1.0") == (2, 1, 0)
    assert updater.parse_version("2.2.0-beta1") == (2, 2, 0)


def test_is_newer_true_when_latest_greater():
    assert updater.is_newer("v2.2.0", "2.1.0") is True


def test_is_newer_false_when_equal_or_older():
    assert updater.is_newer("v2.1.0", "2.1.0") is False
    assert updater.is_newer("v2.0.0", "2.1.0") is False
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -q` → FAIL (`ModuleNotFoundError: notro_app.updater`)

- [ ] **Step 3: 구현** — `notro_app/updater.py`

```python
# -*- coding: utf-8 -*-
"""반자동 자동 업데이터 (GitHub Releases + SHA256 + 배치 자기교체)."""
from __future__ import annotations

from . import __version__

REPO = "writingdeveloper/Notro"


def parse_version(s: str) -> tuple[int, ...]:
    """'v2.1.0' / '2.2.0-beta' → (2,1,0). 접두 v와 pre-release 접미사 무시."""
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): semver parse and compare"
```

---

### Task 2: GitHub Releases API 조회

**Files:**
- Modify: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `check_latest(opener=urllib.request.urlopen, timeout=10) -> dict | None` → `{"tag", "exe_url", "sha256_url"}` (sha256_url은 없으면 None)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_updater.py`에 추가

```python
import io
import json


def _fake_opener(payload):
    def _open(req, timeout=10):
        return io.BytesIO(json.dumps(payload).encode())
    return _open


def test_check_latest_parses_assets():
    payload = {
        "tag_name": "v2.2.0",
        "assets": [
            {"name": "Notro.exe", "browser_download_url": "https://x/Notro.exe"},
            {"name": "Notro.exe.sha256", "browser_download_url": "https://x/Notro.exe.sha256"},
        ],
    }
    rel = updater.check_latest(opener=_fake_opener(payload))
    assert rel == {"tag": "v2.2.0", "exe_url": "https://x/Notro.exe",
                   "sha256_url": "https://x/Notro.exe.sha256"}


def test_check_latest_none_when_no_exe():
    payload = {"tag_name": "v2.2.0", "assets": []}
    assert updater.check_latest(opener=_fake_opener(payload)) is None
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k check_latest -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/updater.py`에 추가

```python
import json
import urllib.request

API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"


def check_latest(opener=urllib.request.urlopen, timeout: int = 10) -> dict | None:
    req = urllib.request.Request(
        API_LATEST,
        headers={"User-Agent": f"Notro/{__version__}",
                 "Accept": "application/vnd.github+json"})
    with opener(req, timeout=timeout) as r:
        data = json.load(r)
    tag = data.get("tag_name", "")
    exe_url = sha_url = None
    for a in data.get("assets", []):
        n = (a.get("name") or "").lower()
        if n == "notro.exe":
            exe_url = a.get("browser_download_url")
        elif n == "notro.exe.sha256":
            sha_url = a.get("browser_download_url")
    if not tag or not exe_url:
        return None
    return {"tag": tag, "exe_url": exe_url, "sha256_url": sha_url}
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -k check_latest -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): parse latest release from GitHub API"
```

---

### Task 3: 다운로드 + SHA256 검증

**Files:**
- Modify: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `_sha256(path) -> str`, `download_and_verify(release: dict, dest_dir: str, downloader=<internal>) -> str | None`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_updater.py`에 추가

```python
import hashlib
import os


def test_download_and_verify_ok(tmp_path):
    exe_bytes = b"MZ fake exe payload"
    digest = hashlib.sha256(exe_bytes).hexdigest()

    def fake_dl(url, dest, timeout=60):
        data = exe_bytes if url.endswith(".exe") else (digest + "  Notro.exe").encode()
        with open(dest, "wb") as f:
            f.write(data)

    rel = {"tag": "v2.2.0", "exe_url": "https://x/Notro.exe",
           "sha256_url": "https://x/Notro.exe.sha256"}
    out = updater.download_and_verify(rel, str(tmp_path), downloader=fake_dl)
    assert out and os.path.exists(out)


def test_download_and_verify_rejects_bad_hash(tmp_path):
    def fake_dl(url, dest, timeout=60):
        data = b"real" if url.endswith(".exe") else (hashlib.sha256(b"WRONG").hexdigest()).encode()
        with open(dest, "wb") as f:
            f.write(data)

    rel = {"tag": "v2.2.0", "exe_url": "https://x/Notro.exe",
           "sha256_url": "https://x/Notro.exe.sha256"}
    assert updater.download_and_verify(rel, str(tmp_path), downloader=fake_dl) is None


def test_download_and_verify_none_without_sha(tmp_path):
    rel = {"tag": "v2.2.0", "exe_url": "https://x/Notro.exe", "sha256_url": None}
    assert updater.download_and_verify(rel, str(tmp_path), downloader=lambda *a, **k: None) is None
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k download -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/updater.py`에 추가

```python
import hashlib
import os


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


def download_and_verify(release: dict, dest_dir: str, downloader=_download) -> str | None:
    if not release.get("sha256_url"):
        return None  # 검증 불가 → 자동 설치 안 함
    os.makedirs(dest_dir, exist_ok=True)
    exe_path = os.path.join(dest_dir, "Notro.exe")
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -k download -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): SHA256-verified download"
```

---

### Task 4: 배치 헬퍼 자기교체

**Files:**
- Modify: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `build_bat(pid: int, new_exe: str, target_exe: str) -> str`, `apply_and_restart(new_exe: str, bat_dir: str) -> None`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_updater.py`에 추가

```python
def test_build_bat_contains_pid_and_paths():
    bat = updater.build_bat(4321, r"C:\tmp\Notro.exe", r"C:\app\Notro.exe")
    assert "4321" in bat
    assert r"C:\tmp\Notro.exe" in bat
    assert r"C:\app\Notro.exe" in bat
    assert ".bak" in bat  # 백업/롤백 포함
    assert "start" in bat.lower()  # 재시작 포함
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k build_bat -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/updater.py`에 추가

```python
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000


def build_bat(pid: int, new_exe: str, target_exe: str) -> str:
    """실행 중 프로세스(pid) 종료 대기 → 백업 → 교체 → 재시작. 실패 시 .bak 롤백."""
    return f'''@echo off
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  timeout /t 1 /nobreak >NUL
  goto wait
)
copy /Y "{target_exe}" "{target_exe}.bak" >NUL
move /Y "{new_exe}" "{target_exe}" >NUL
if errorlevel 1 (
  move /Y "{target_exe}.bak" "{target_exe}" >NUL
) else (
  del "{target_exe}.bak" >NUL 2>&1
)
start "" "{target_exe}"
del "%~f0"
'''


def apply_and_restart(new_exe: str, bat_dir: str) -> None:
    """배치 헬퍼를 만들어 실행하고 즉시 반환한다. 호출자가 앱을 종료하면
    배치가 종료를 감지해 교체·재시작한다."""
    os.makedirs(bat_dir, exist_ok=True)
    target = sys.executable
    bat = os.path.join(bat_dir, "apply_update.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write(build_bat(os.getpid(), new_exe, target))
    subprocess.Popen(["cmd", "/c", bat], creationflags=CREATE_NO_WINDOW,
                     close_fds=True)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -k build_bat -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): batch self-replace helper"
```

---

### Task 5: UpdateChecker 백그라운드 스레드

**Files:**
- Modify: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Consumes: `check_latest`, `is_newer`, `download_and_verify`
- Produces: `UpdateChecker(dest_dir, on_ready, is_enabled=..., interval=..., _check=..., _download=...)` with `.check_once()`, `.run()`, `.stop()`, attrs `.ready_exe`, `.ready_tag`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_updater.py`에 추가

```python
def test_check_once_calls_on_ready_when_newer(tmp_path, monkeypatch):
    calls = []
    rel = {"tag": "v9.9.9", "exe_url": "u", "sha256_url": "s"}
    uc = updater.UpdateChecker(
        str(tmp_path), on_ready=lambda tag, exe: calls.append((tag, exe)),
        _check=lambda: rel,
        _download=lambda release, dest: os.path.join(dest, "Notro.exe"))
    uc.check_once()
    assert calls == [("v9.9.9", os.path.join(str(tmp_path), "Notro.exe"))]
    assert uc.ready_tag == "v9.9.9"


def test_check_once_skips_when_not_newer(tmp_path):
    uc = updater.UpdateChecker(
        str(tmp_path), on_ready=lambda *a: (_ for _ in ()).throw(AssertionError("should not fire")),
        _check=lambda: {"tag": "v0.0.1", "exe_url": "u", "sha256_url": "s"},
        _download=lambda *a, **k: None)
    uc.check_once()
    assert uc.ready_exe is None


def test_check_once_disabled_is_noop(tmp_path):
    uc = updater.UpdateChecker(
        str(tmp_path), on_ready=lambda *a: (_ for _ in ()).throw(AssertionError()),
        is_enabled=lambda: False,
        _check=lambda: (_ for _ in ()).throw(AssertionError("should not check")))
    uc.check_once()  # 아무 일도 없어야
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k check_once -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/updater.py`에 추가

```python
import threading

CHECK_INTERVAL = 24 * 3600


class UpdateChecker(threading.Thread):
    def __init__(self, dest_dir, on_ready, is_enabled=lambda: True,
                 interval=CHECK_INTERVAL, _check=None, _download=None):
        super().__init__(daemon=True)
        self.dest_dir = dest_dir
        self.on_ready = on_ready
        self.is_enabled = is_enabled
        self.interval = interval
        self._check = _check or check_latest
        self._download = _download or (
            lambda release, dest: download_and_verify(release, dest))
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -q` → PASS (전체 updater 테스트)

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): background UpdateChecker with check/download loop"
```

---

### Task 6: i18n 업데이트 문자열 (5개 언어)

**Files:**
- Modify: `notro_app/i18n.py`
- Test: `tests/test_i18n.py`

**Interfaces:**
- Produces: 트레이/알림용 키 `update_check`, `update_checking`, `update_none`, `update_ready`, `update_restart`, `update_auto`, `update_failed` — 5개 언어 전부.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_i18n.py`에 추가 (기존 키 완전성 테스트가 있으면 그 방식에 맞춘다)

```python
def test_updater_keys_in_all_languages():
    from notro_app import i18n
    keys = ["update_check", "update_checking", "update_none", "update_ready",
            "update_restart", "update_auto", "update_failed"]
    for lang in i18n.SUPPORTED_LANGS:
        for k in keys:
            assert k in i18n.STRINGS[lang], f"{lang} missing {k}"
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_i18n.py -k updater -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/i18n.py`의 각 언어 STRINGS(또는 별도 `_UPDATER_STRINGS` dict를 만들어 `_PICKER_STRINGS`처럼 merge)에 추가. 값 예시(en/ko만 표기, ja·zh·es도 반드시 채운다):

```python
# en
"update_check": "Check for updates",
"update_checking": "Checking for updates…",
"update_none": "You're on the latest version.",
"update_ready": "Notro {ver} is ready — restart to update.",
"update_restart": "Restart to update now",
"update_auto": "Automatic update checks",
"update_failed": "Update check failed. Will retry later.",
# ko
"update_check": "업데이트 확인",
"update_checking": "업데이트 확인 중…",
"update_none": "최신 버전입니다.",
"update_ready": "Notro {ver} 준비됨 — 재시작하면 적용됩니다.",
"update_restart": "지금 재시작해 업데이트",
"update_auto": "자동 업데이트 확인",
"update_failed": "업데이트 확인 실패. 나중에 다시 시도합니다.",
```

(ja/zh/es 동일 키를 자연스러운 번역으로 채운다. 스펙 §7 참조.)

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_i18n.py -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/i18n.py tests/test_i18n.py
git commit -m "feat(i18n): updater strings in all 5 languages"
```

---

### Task 7: 트레이 메뉴 통합

**Files:**
- Modify: `notro_app/tray.py`

**Interfaces:**
- Consumes: `updater.UpdateChecker` (준비된 업데이트 상태), `i18n.tr`
- `build_icon(...)`에 `updater=None` 매개변수 추가 — 주어지면 업데이트 메뉴 항목 노출.

- [ ] **Step 1: 구현** — `notro_app/tray.py`의 `build_icon`에 매개변수 `updater=None` 추가하고 메뉴 구성에 아래를 삽입한다. "지금 재시작해 업데이트"는 `updater.ready_exe`가 있을 때만 표시(pystray `visible=lambda`).

```python
# build_icon(monitor, picker=None, listener=None, on_quit_extra=None, updater=None)
from . import config, updater as _updater_mod  # 필요 시

def on_check_update(icon, item):
    if updater:
        icon.notify(tr("update_checking"), APP_NAME)
        import threading
        def _bg():
            updater.check_once()
            if not updater.ready_exe:
                icon.notify(tr("update_none"), APP_NAME)
        threading.Thread(target=_bg, daemon=True).start()

def on_restart_update(icon, item):
    if updater and updater.ready_exe:
        import os
        from . import updater as um
        um.apply_and_restart(updater.ready_exe, os.path.dirname(updater.ready_exe))
        # 앱 종료 → 배치가 교체·재시작
        on_quit(icon, item)

def on_toggle_auto(icon, item):
    cur = config.get_setting_flag("auto_update")
    config.set_setting_flag("auto_update", not (cur or config.get_setting_str("auto_update", "1") == "1"))
```

메뉴 항목(피커 메뉴가 있는 분기와 v1 분기 양쪽에 동일하게 `updater`가 not None일 때):

```python
pystray.MenuItem(tr("update_restart"), on_restart_update,
                 visible=lambda item: bool(updater and updater.ready_exe)),
pystray.MenuItem(tr("update_check"), on_check_update),
pystray.MenuItem(tr("update_auto"), on_toggle_auto,
                 checked=lambda item: config.get_setting_flag("auto_update")
                         if config.get_setting_str("auto_update", "") else True),
```

- [ ] **Step 2: 스모크** — Run: `python -c "from notro_app.tray import build_icon; print('ok')"` → `ok` (import·문법 확인)

- [ ] **Step 3: 회귀** — Run: `python -m pytest -q` → 전체 PASS

- [ ] **Step 4: 커밋**

```bash
git add notro_app/tray.py
git commit -m "feat(tray): update-check / restart-to-update / auto-update menu"
```

---

### Task 8: app 통합 (frozen 시 기동)

**Files:**
- Modify: `notro_app/app.py`

**Interfaces:**
- Consumes: `updater.UpdateChecker`, `tray.build_icon(..., updater=...)`

- [ ] **Step 1: 구현** — `notro_app/app.py`의 `main()`에서, frozen이고 `auto_update` 설정이 켜져 있을 때 `UpdateChecker`를 만들어 `build_icon`에 넘기고 스레드를 시작한다. 트레이 아이콘 핸들이 필요하므로 `on_ready` 콜백은 아이콘 생성 후 배선한다.

```python
import sys, os
# main() 내부, tray.build_icon 직전:
upd = None
if getattr(sys, "frozen", False):
    from .updater import UpdateChecker
    upd_dir = os.path.join(config.TEMP_DIR, "update")
    upd = UpdateChecker(
        upd_dir, on_ready=lambda tag, exe: None,  # 아이콘 생성 후 재배선
        is_enabled=lambda: config.get_setting_flag("auto_update")
                    or not config.get_setting_str("auto_update", ""))

# tray.build_icon(...) 호출에 updater=upd 추가.
# 아이콘 생성 후:
if upd:
    upd.on_ready = lambda tag, exe: icon.notify(tr("update_ready", ver=tag), APP_NAME)
    upd.start()
# on_quit_extra에 upd.stop() 추가.
```

(v1 분기와 피커 분기 양쪽 `build_icon` 호출에 `updater=upd` 전달. `auto_update` 미설정 시 기본 on.)

- [ ] **Step 2: 스모크** — Run: `python -c "from notro_app.app import main; print('ok')"` → `ok`

- [ ] **Step 3: 회귀** — Run: `python -m pytest -q` → 전체 PASS

- [ ] **Step 4: 커밋**

```bash
git add notro_app/app.py
git commit -m "feat(app): start UpdateChecker on frozen builds, wire tray notify"
```

---

### Task 9: release.yml SHA256 자산

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: 구현** — EXE 빌드 스텝 뒤, 릴리스 publish 전에 체크섬 생성 스텝 추가. Publish 스텝의 `files:`에 `dist/Notro.exe.sha256` 포함.

```yaml
      - name: Generate SHA256
        run: |
          cd dist
          certutil -hashfile Notro.exe SHA256 | findstr /v ":" | findstr /r "^[0-9a-fA-F]" > Notro.exe.sha256.tmp
          for /f %%h in (Notro.exe.sha256.tmp) do echo %%h  Notro.exe> Notro.exe.sha256
          del Notro.exe.sha256.tmp
        shell: cmd
```

Publish 스텝:

```yaml
        with:
          files: |
            dist/Notro.exe
            dist/Notro.exe.sha256
```

- [ ] **Step 2: 검증(로컬 모사)** — Run(로컬 확인용, Git Bash): `python -c "import hashlib;print(hashlib.sha256(b'x').hexdigest())"` 로 sha256 형식 확인. 실제 검증은 다음 릴리스에서.

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/release.yml
git commit -m "ci: attach Notro.exe.sha256 to releases for updater verification"
```

---

## 최종 통합 검증

- [ ] `python -m pytest -q` → 전체 PASS (기존 62 + updater 신규, 회귀 0)
- [ ] `python -c "from notro_app.app import main; from notro_app import updater; print('import ok')"`
- [ ] `__init__.py`의 `__version__`을 `2.2.0`으로 올린다 → 커밋 `chore: bump version to 2.2.0`
- [ ] CHANGELOG.md에 `[2.2.0]` 항목 추가 (자동 업데이터) → 커밋
- [ ] 수동 QA 체크리스트(릴리스 전): 트레이 "업데이트 확인" 동작, frozen exe에서 v2.1.0→테스트 릴리스 교체·재시작, `.bak` 롤백, `auto_update` 토글.
