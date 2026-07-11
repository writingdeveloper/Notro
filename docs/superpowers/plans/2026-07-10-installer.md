# Installer Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** portable exe를 Inno Setup 인스톨러(`NotroSetup.exe`)로 전환하고, 자동 업데이터를 배치 자기교체에서 silent 인스톨러 실행으로 바꾼다.

**Architecture:** 신규 `installer.iss`(Inno Setup)가 `%LOCALAPPDATA%\Programs\Notro`에 설치·바로가기·언인스톨러를 만든다. `release.yml`이 PyInstaller exe를 만든 뒤 Inno로 `NotroSetup.exe`를 빌드해 릴리스에 첨부한다. `updater.py`는 자산 이름을 `NotroSetup.exe`로 바꾸고 `apply_and_restart`가 `/VERYSILENT`로 인스톨러를 실행한다.

**Tech Stack:** Inno Setup (빌드 타임), Python 표준 라이브러리(updater). 신규 런타임 의존성 없음.

## Global Constraints

- 설치 위치: `%LOCALAPPDATA%\Programs\Notro` — `PrivilegesRequired=lowest`(관리자 불필요).
- 릴리스 자산: `NotroSetup.exe` + `NotroSetup.exe.sha256`만. portable `Notro.exe`는 첨부하지 않는다.
- updater 자산 상수: `ASSET_NAME = "NotroSetup.exe"`, `ASSET_SHA = "NotroSetup.exe.sha256"`.
- silent install 인자: `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`.
- 자동 시작 레지스트리: HKCU `...\Run` 값 이름 `Notro` (config.py와 동일 — 중복 없음).
- 기존 pytest는 `build_bat` 테스트 제거를 반영해 회귀 없이 통과.
- 데이터(`%APPDATA%\Notro`)·설정(HKCU `Software\Notro`)은 설치/업데이트/언인스톨과 무관하게 보존.

---

### Task 1: updater 자산 이름을 NotroSetup.exe로

**Files:**
- Modify: `notro_app/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: 상수 `ASSET_NAME`, `ASSET_SHA`. `check_latest`가 `NotroSetup.exe`/`NotroSetup.exe.sha256`을 파싱. `download_and_verify`가 `NotroSetup.exe`로 저장.

- [ ] **Step 1: 기존 테스트를 NotroSetup.exe로 수정** — `tests/test_updater.py`의 `test_check_latest_parses_assets`를 아래로 교체하고, `test_download_and_verify_ok`/`_rejects_bad_hash`의 자산 이름도 `NotroSetup.exe`로 바꾼다.

```python
def test_check_latest_parses_setup_asset():
    payload = {
        "tag_name": "v2.3.0",
        "assets": [
            {"name": "NotroSetup.exe", "browser_download_url": "https://x/NotroSetup.exe"},
            {"name": "NotroSetup.exe.sha256", "browser_download_url": "https://x/NotroSetup.exe.sha256"},
        ],
    }
    rel = updater.check_latest(opener=_fake_opener(payload))
    assert rel == {"tag": "v2.3.0", "exe_url": "https://x/NotroSetup.exe",
                   "sha256_url": "https://x/NotroSetup.exe.sha256"}
```

`test_download_and_verify_ok`의 fake_dl 조건 `url.endswith(".exe")`는 `NotroSetup.exe`에도 참이므로 그대로 두고, `rel`의 url만 `NotroSetup.exe`로 바꾼다. 검증은 `os.path.exists(out)` 그대로.

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k "check_latest or download" -q` → FAIL (`Notro.exe` 매칭)

- [ ] **Step 3: 구현** — `notro_app/updater.py`

`check_latest` 위에 상수 추가:

```python
ASSET_NAME = "NotroSetup.exe"
ASSET_SHA = ASSET_NAME + ".sha256"
```

`check_latest`의 매칭 루프 교체:

```python
    for a in data.get("assets", []):
        n = a.get("name") or ""
        if n == ASSET_NAME:
            exe_url = a.get("browser_download_url")
        elif n == ASSET_SHA:
            sha_url = a.get("browser_download_url")
```

`download_and_verify`의 저장 파일명 교체:

```python
    exe_path = os.path.join(dest_dir, ASSET_NAME)
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_updater.py -k "setup or download" -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/updater.py tests/test_updater.py
git commit -m "feat(updater): target NotroSetup.exe release asset"
```

---

### Task 2: apply_and_restart를 silent 인스톨러 실행으로 (배치 제거)

**Files:**
- Modify: `notro_app/updater.py`, `notro_app/tray.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Produces: `apply_and_restart(setup_path: str, _spawn=subprocess.Popen) -> None` — `/VERYSILENT`로 인스톨러 실행. `build_bat` 삭제.
- Consumes(tray): `apply_and_restart(updater.ready_exe)` (2번째 인자 제거).

- [ ] **Step 1: build_bat 테스트 제거 + silent 테스트 작성** — `tests/test_updater.py`의 `test_build_bat_contains_pid_and_paths`를 삭제하고 아래를 추가.

```python
def test_apply_and_restart_runs_silent_installer():
    calls = []
    updater.apply_and_restart(r"C:\tmp\NotroSetup.exe",
                              _spawn=lambda args, **k: calls.append(args))
    assert calls, "installer should be spawned"
    assert calls[0][0] == r"C:\tmp\NotroSetup.exe"
    assert "/VERYSILENT" in calls[0]
    assert "/SUPPRESSMSGBOXES" in calls[0]
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_updater.py -k apply_and_restart -q` → FAIL (`_spawn` 미지원 / 배치 방식)

- [ ] **Step 3: 구현** — `notro_app/updater.py`에서 `build_bat` 함수를 통째로 삭제하고 `apply_and_restart`를 교체:

```python
def apply_and_restart(setup_path, _spawn=None):
    """다운로드한 NotroSetup.exe를 silent로 실행한다. Inno의 CloseApplications가
    실행 중 앱을 종료·교체하고 [Run] 항목이 앱을 재실행한다. 호출자는 이 함수
    직후 앱을 종료해야 한다(트레이 on_quit)."""
    spawn = _spawn or subprocess.Popen
    spawn([setup_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
          creationflags=CREATE_NO_WINDOW, close_fds=True)
```

- [ ] **Step 4: tray 호출 수정** — `notro_app/tray.py`의 `on_restart_update`에서 `apply_and_restart` 호출을 2-인자 → 1-인자로:

```python
        def on_restart_update(icon, item):
            if updater.ready_exe:
                from . import updater as um
                um.apply_and_restart(updater.ready_exe)
                on_quit(icon, item)
```

- [ ] **Step 5: 통과 확인** — Run: `python -m pytest tests/test_updater.py -q` → PASS, 그리고 `python -c "from notro_app.tray import build_icon; print('ok')"` → `ok`

- [ ] **Step 6: 커밋**

```bash
git add notro_app/updater.py notro_app/tray.py tests/test_updater.py
git commit -m "feat(updater): silent-installer apply, drop batch self-replace"
```

---

### Task 3: Inno Setup 스크립트

**Files:**
- Create: `installer.iss`

- [ ] **Step 1: 작성** — 프로젝트 루트에 `installer.iss` 생성. `AppId` GUID는 아래 값 고정(재설치·업데이트 동일성 보장).

```iss
; Notro installer (Inno Setup). Build: iscc installer.iss /DAppVersion=X.Y.Z
#define AppName "Notro"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5F8A1E2B-3C4D-4E5F-A6B7-C8D9E0F1A2B3}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=writingdeveloper
DefaultDirName={localappdata}\Programs\Notro
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=NotroSetup
UninstallDisplayIcon={app}\Notro.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=Notro.exe
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startupicon"; Description: "Run Notro at Windows startup"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\Notro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Notro"; Filename: "{app}\Notro.exe"
Name: "{autodesktop}\Notro"; Filename: "{app}\Notro.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Notro"; ValueData: """{app}\Notro.exe"""; Tasks: startupicon; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Notro.exe"; Description: "Launch Notro"; Flags: nowait postinstall
```

`[Run]`에 `skipifsilent`를 두지 않아 silent 업데이트 후에도 앱이 재실행된다.

- [ ] **Step 2: 문법 확인(로컬 Inno 있을 때만; 없으면 CI가 검증)** — `installer.iss`가 존재하고 GUID·경로가 올바른지 육안 확인. (로컬 pytest 대상 아님.)

- [ ] **Step 3: 커밋**

```bash
git add installer.iss
git commit -m "feat(installer): Inno Setup script — LOCALAPPDATA install, shortcuts, uninstaller"
```

---

### Task 4: release.yml 인스톨러 빌드

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: 수정** — 기존 "Generate SHA256"/"Publish" 스텝을 인스톨러 흐름으로 교체. Build EXE 스텝은 유지(내부 산출물).

Build EXE 스텝 다음에 삽입, 기존 SHA256/Publish 교체:

```yaml
      - name: Install Inno Setup
        run: choco install innosetup -y

      - name: Build installer
        shell: pwsh
        run: |
          $ver = "${{ github.ref_name }}" -replace '^v',''
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss /DAppVersion=$ver

      - name: Generate SHA256
        shell: pwsh
        run: |
          $hash = (Get-FileHash dist/NotroSetup.exe -Algorithm SHA256).Hash.ToLower()
          "$hash  NotroSetup.exe" | Out-File -FilePath dist/NotroSetup.exe.sha256 -Encoding ascii -NoNewline

      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/NotroSetup.exe
            dist/NotroSetup.exe.sha256
          generate_release_notes: true
```

- [ ] **Step 2: 커밋**

```bash
git add .github/workflows/release.yml
git commit -m "ci: build NotroSetup.exe with Inno Setup, attach it + sha256"
```

---

### Task 5: 문서 + 버전

**Files:**
- Modify: `README.md`, `README.ko.md`, `CHANGELOG.md`, `notro_app/__init__.py`

- [ ] **Step 1: README (en) 설치 안내** — `README.md`의 "Download & run" 섹션 본문을 교체(제목 유지 가능):

```markdown
Grab the latest `NotroSetup.exe` from the [**Releases**](../../releases) page and run it.
It installs to `%LOCALAPPDATA%\Programs\Notro` (no admin rights needed) and adds Start
Menu / Desktop shortcuts. Uninstall from **Settings → Apps** or the Start Menu.
```

(기존 portable 실행 문구·경고는 SmartScreen 안내만 남기고 정리.)

- [ ] **Step 2: README (ko) 설치 안내** — `README.ko.md`의 "내려받기 & 실행" 섹션 본문 교체:

```markdown
[**Releases**](../../releases) 페이지에서 최신 `NotroSetup.exe`를 받아 실행하면 됩니다.
`%LOCALAPPDATA%\Programs\Notro`에 설치되며(관리자 권한 불필요) 시작 메뉴·바탕화면
바로가기가 생성됩니다. 제거는 **설정 → 앱** 또는 시작 메뉴에서 합니다.
```

- [ ] **Step 3: CHANGELOG [2.3.0]** — 최상단 `## [2.2.0]` 앞에 삽입:

```markdown
## [2.3.0] - 2026-07-10

### Changed
- **Now ships as an installer (`NotroSetup.exe`)** instead of a portable exe.
  Installs to `%LOCALAPPDATA%\Programs\Notro` (no admin rights), adds Start Menu
  and optional Desktop shortcuts, an optional "run at startup" step, and a proper
  uninstaller (Settings → Apps). Fixes the "lost the file / must remember where it
  is" problem of the portable build.
- The auto-updater now downloads `NotroSetup.exe` and runs it silently
  (`/VERYSILENT`) to update in place, replacing the batch self-replace.

### Migration
- **v2.2.0 → v2.3.0 must be done manually once:** the v2.2.0 updater looks for a
  `Notro.exe` asset, which v2.3.0 no longer publishes. Download and run
  `NotroSetup.exe` once; your library (`%APPDATA%\Notro`) and settings carry over.
  From v2.3.0 onward, updates are automatic again.
```

- [ ] **Step 4: 버전 bump** — `notro_app/__init__.py`: `__version__ = "2.2.0"` → `"2.3.0"`.

- [ ] **Step 5: 회귀 + 커밋**

```bash
python -m pytest -q   # 전체 PASS
git add README.md README.ko.md CHANGELOG.md notro_app/__init__.py
git commit -m "docs: installer README + CHANGELOG [2.3.0], bump to 2.3.0"
```

---

## 최종 통합 검증

- [ ] `python -m pytest -q` → 전체 PASS (build_bat 테스트 제거 반영, updater 테스트는 NotroSetup 기준)
- [ ] `python -c "from notro_app.app import main; from notro_app import updater; import notro_app; print('v'+notro_app.__version__)"` → `v2.3.0`
- [ ] `installer.iss` 존재, `release.yml`이 `NotroSetup.exe` 첨부
- [ ] 수동 QA(릴리스 후): `NotroSetup.exe` 실행 → `%LOCALAPPDATA%\Programs\Notro` 설치 → 바로가기·트레이 동작 → 언인스톨 → 데이터 보존 확인. 자동 업데이트는 v2.3.0→다음 버전에서 검증.
