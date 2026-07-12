# Video Compression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discord 무료 한도(10MB)를 넘는 비디오 파일을 클립보드에서 감지해 ffmpeg로 압축하고, 압축본을 파일로 클립보드에 되돌려 Ctrl+V 첨부가 되게 한다.

**Architecture:** 순수 계산(파싱·인코딩 계획)과 부수효과(subprocess·다운로드·GUI)를 분리한다. `monitor`는 감지만 하고 콜백으로 위임하며(감시 루프를 막으면 안 됨), 오케스트레이션은 `app.py`가 별도 스레드에서 수행한다. ffmpeg는 배포하지 않고 필요할 때 내려받는다.

**Tech Stack:** Python 3.10+, Windows, PIL(기존), pywebview(기존), ffmpeg(런타임 다운로드), 표준 라이브러리(`subprocess`/`urllib`/`zipfile`/`hashlib`).

## Global Constraints

- **새 pip 의존성 0개.** `requirements.txt`를 수정하지 않는다. (`zipfile`/`urllib`/`subprocess`/`hashlib`는 표준 라이브러리)
- **테스트는 순수 함수 위주.** Windows API·GUI·실제 ffmpeg 실행은 단위 테스트 대상이 아니다(기존 관례).
- **클립보드는 성공했을 때만 교체한다.** 실패·취소 시 원본 클립보드를 그대로 둔다.
- **ffmpeg 바이너리를 배포하지 않는다.** 사용자 승인 하에 사용자 머신이 PyPI에서 받는다(GPL 고지 의무 회피).
- **출력은 항상 `.mp4` (H.264 + AAC).** 입력이 `.mkv`/`.avi`여도 mp4로 내보낸다.
- **화질 하한: 360p / 비디오 300 kbps.** 그 아래로는 내려가지 않고 실패로 안내한다.
- **i18n은 5개 언어(en·ko·ja·zh·es) 파리티**를 유지한다(키·placeholder 일치).
- 기존 코드 스타일을 따른다: 파일 상단 `# -*- coding: utf-8 -*-`, `from __future__ import annotations`, 한국어 주석.
- 최종 버전: **v2.6.0**.

---

### Task 1: `video.py` — `parse_ffmpeg_info` (순수 함수)

**Files:**
- Create: `notro_app/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: 없음
- Produces: `VideoMeta(duration: float, width: int, height: int, fps: float, has_audio: bool)` dataclass, `parse_ffmpeg_info(stderr: str) -> VideoMeta | None`

- [ ] **Step 1: Write the failing test**

`tests/test_video.py`:

```python
# -*- coding: utf-8 -*-
from notro_app.video import VideoMeta, parse_ffmpeg_info

SAMPLE = """ffmpeg version 7.1 Copyright (c) 2000-2024
  Duration: 00:01:12.34, start: 0.000000, bitrate: 5842 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709), 1920x1080 [SAR 1:1 DAR 16:9], 5701 kb/s, 59.94 fps, 60 tbr, 60k tbn (default)
  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 128 kb/s (default)
At least one output file must be specified
"""

SILENT = """  Duration: 00:00:30.00, start: 0.000000, bitrate: 3000 kb/s
  Stream #0:0: Video: h264 (High), yuv420p, 1280x720 [SAR 1:1 DAR 16:9], 2900 kb/s, 30 fps, 30 tbr, 15360 tbn
"""


def test_parses_duration_resolution_fps_audio():
    m = parse_ffmpeg_info(SAMPLE)
    assert m == VideoMeta(duration=72.34, width=1920, height=1080, fps=59.94, has_audio=True)


def test_parses_silent_video():
    m = parse_ffmpeg_info(SILENT)
    assert m.has_audio is False
    assert (m.width, m.height, m.fps) == (1280, 720, 30.0)


def test_returns_none_when_not_a_video():
    assert parse_ffmpeg_info("some random text") is None
    assert parse_ffmpeg_info("  Duration: 00:00:05.00\n  Stream #0:0: Audio: aac") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notro_app.video'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video.py`:

```python
# -*- coding: utf-8 -*-
"""비디오 압축: ffmpeg 출력 파싱 · 인코딩 계획(순수 함수) · 실행.

순수 계산(파싱·계획)과 부수효과(subprocess)를 분리한다 — compress.py와 같은 관례.
ffprobe는 쓰지 않는다: 내려받는 imageio-ffmpeg wheel에는 ffmpeg만 들어 있고,
ffprobe 하나 때문에 100MB+ 빌드를 받을 이유가 없어 `ffmpeg -i`의 stderr를 파싱한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VideoMeta:
    duration: float   # 초
    width: int
    height: int
    fps: float
    has_audio: bool


_DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO_RE = re.compile(r"Video:[^\n]*?\b(\d{2,5})x(\d{2,5})\b")
_FPS_RE = re.compile(r"([\d.]+)\s*fps")
_AUDIO_RE = re.compile(r"Stream #\d+:\d+[^\n]*: Audio:")


def parse_ffmpeg_info(stderr: str) -> VideoMeta | None:
    """`ffmpeg -i <file>`이 stderr로 뱉는 정보에서 메타데이터를 뽑는다.
    비디오 스트림이나 길이를 못 찾으면 None(비디오가 아니거나 손상)."""
    d = _DUR_RE.search(stderr)
    if not d:
        return None
    duration = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))
    if duration <= 0:
        return None

    v = _VIDEO_RE.search(stderr)
    if not v:
        return None
    width, height = int(v.group(1)), int(v.group(2))

    # fps는 비디오 스트림 줄 안에서만 찾는다 (다른 줄의 숫자와 섞이지 않게)
    line_end = stderr.find("\n", v.start())
    line = stderr[v.start():line_end if line_end != -1 else len(stderr)]
    f = _FPS_RE.search(line)
    fps = float(f.group(1)) if f else 30.0

    return VideoMeta(duration, width, height, fps, bool(_AUDIO_RE.search(stderr)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video.py tests/test_video.py
git commit -m "feat(video): parse ffmpeg -i output into VideoMeta"
```

---

### Task 2: `video.py` — `plan_encode` (순수 함수, 핵심 알고리즘)

**Files:**
- Modify: `notro_app/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: `VideoMeta` (Task 1)
- Produces: `EncodePlan(height: int, fps: int, video_kbps: int, audio_kbps: int, warn: bool)`, `plan_encode(meta: VideoMeta, limit_bytes: int) -> EncodePlan | None`, 상수 `AUDIO_KBPS = 96`, `MIN_VIDEO_KBPS = 300`

- [ ] **Step 1: Write the failing test**

`tests/test_video.py`에 추가:

```python
from notro_app.video import EncodePlan, plan_encode

MB = 1024 * 1024
LIMIT = int(10 * MB * 0.95)   # config.LIMIT_BYTES와 동일 (SAFETY 0.95)


def _meta(dur, w=1920, h=1080, fps=60.0, audio=True):
    return VideoMeta(duration=dur, width=w, height=h, fps=fps, has_audio=audio)


def test_short_clip_keeps_1080p():
    p = plan_encode(_meta(20), LIMIT)          # 20초 → 비디오 여유 충분
    assert p.height == 1080
    assert p.video_kbps >= 2500


def test_one_minute_clip_drops_to_720p30():
    p = plan_encode(_meta(60), LIMIT)          # 60초 → 약 1230kbps
    assert p.height == 720
    assert p.fps == 30                         # 60fps를 감당할 여유(1000*1.5)가 없다
    assert p.warn is False                     # 경고는 480p 이하로 떨어질 때만


def test_long_clip_drops_to_480p():
    p = plan_encode(_meta(120), LIMIT)         # 2분 → 약 568kbps
    assert p.height == 480
    assert p.warn is True


def test_too_long_returns_none():
    assert plan_encode(_meta(600), LIMIT) is None   # 10분 → 하한 미달


def test_never_upscales_beyond_source():
    p = plan_encode(_meta(20, w=640, h=360, fps=30.0), LIMIT)
    assert p.height == 360                     # 원본이 360p면 그대로
    assert p.warn is False                     # 축소가 아니므로 경고 없음


def test_silent_video_has_no_audio_budget():
    p = plan_encode(_meta(60, audio=False), LIMIT)
    assert p.audio_kbps == 0


def test_zero_duration_returns_none():
    assert plan_encode(_meta(0), LIMIT) is None
```

> **주의(경고 규칙):** `warn`은 **원본보다 작아졌고 480p 이하일 때만** True다. 위 `test_one_minute_clip_drops_to_720p30`은 720p이므로 `warn is False`가 되어야 한다 — 테스트를 다음과 같이 고쳐 쓴다:
> ```python
> def test_one_minute_clip_drops_to_720p30():
>     p = plan_encode(_meta(60), LIMIT)
>     assert p.height == 720
>     assert p.fps == 30
>     assert p.warn is False        # 720p는 경고 대상 아님(480p 이하만)
> ```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py -v`
Expected: FAIL — `ImportError: cannot import name 'EncodePlan'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video.py`에 추가:

```python
AUDIO_KBPS = 96          # AAC 고정
MIN_VIDEO_KBPS = 300     # 이 아래로는 내려가지 않는다 (360p 하한)

# 해상도 사다리: (높이, 30fps 기준 최소 비디오 kbps)
_LADDER = ((1080, 2500), (720, 1000), (480, 500), (360, MIN_VIDEO_KBPS))


@dataclass
class EncodePlan:
    height: int
    fps: int
    video_kbps: int
    audio_kbps: int
    warn: bool        # 원본보다 작아졌고 480p 이하 → 화질 저하 경고


def plan_encode(meta: VideoMeta, limit_bytes: int) -> EncodePlan | None:
    """목표 용량에 맞는 인코딩 계획. 하한(360p/300kbps) 밑이면 None = '못 줄임'.

    60fps는 같은 체감 화질에 약 1.5배 비트레이트를 먹는다 — 여유가 없으면 30fps로 낮춘다.
    원본보다 해상도를 키우지 않는다.
    """
    if meta.duration <= 0:
        return None
    audio = AUDIO_KBPS if meta.has_audio else 0
    total_kbps = limit_bytes * 8 / meta.duration / 1000
    video_kbps = int(total_kbps - audio)
    if video_kbps < MIN_VIDEO_KBPS:
        return None

    for height, need in _LADDER:
        if height > meta.height:      # 원본보다 키우지 않는다
            continue
        if video_kbps >= need:
            fps = int(round(meta.fps))
            if meta.fps > 30 and video_kbps < need * 1.5:
                fps = 30              # 60fps를 감당할 여유가 없다
            warn = height < meta.height and height <= 480
            return EncodePlan(height, fps, video_kbps, audio, warn)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video.py tests/test_video.py
git commit -m "feat(video): plan_encode — resolution ladder, fps cut, 360p/300kbps floor"
```

---

### Task 3: `video.py` — `parse_progress` + `build_args` (순수 함수)

**Files:**
- Modify: `notro_app/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: `EncodePlan` (Task 2)
- Produces: `parse_progress(line: str) -> float | None`, `build_args(ffmpeg: str, src: str, plan: EncodePlan, dest: str) -> list[str]`

- [ ] **Step 1: Write the failing test**

`tests/test_video.py`에 추가:

```python
from notro_app.video import build_args, parse_progress


def test_parse_progress_reads_time():
    line = "frame=  360 fps= 30 q=28.0 size=    2048KiB time=00:00:12.34 bitrate=1360.0kbits/s"
    assert parse_progress(line) == 12.34


def test_parse_progress_ignores_other_lines():
    assert parse_progress("Stream mapping:") is None


def test_build_args_uses_plan_and_outputs_mp4():
    plan = EncodePlan(height=720, fps=30, video_kbps=1200, audio_kbps=96, warn=False)
    args = build_args("ffmpeg.exe", "in.mkv", plan, "out.mp4")
    joined = " ".join(args)
    assert args[0] == "ffmpeg.exe"
    assert "-c:v libx264" in joined
    assert "-b:v 1200k" in joined
    assert "-maxrate 1440k" in joined          # 1200 * 1.2
    assert "-bufsize 2400k" in joined          # 1200 * 2
    assert "scale=-2:720" in joined
    assert "-r 30" in joined
    assert "-b:a 96k" in joined
    assert "+faststart" in joined
    assert args[-1] == "out.mp4"


def test_build_args_drops_audio_when_silent():
    plan = EncodePlan(height=480, fps=30, video_kbps=600, audio_kbps=0, warn=True)
    args = build_args("ffmpeg.exe", "in.mp4", plan, "out.mp4")
    assert "-an" in args
    assert "-c:a" not in args
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_args'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video.py`에 추가:

```python
_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def parse_progress(line: str) -> float | None:
    """ffmpeg 진행 로그의 `time=00:00:12.34` → 12.34초. 없으면 None."""
    m = _TIME_RE.search(line)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def build_args(ffmpeg: str, src: str, plan: EncodePlan, dest: str) -> list[str]:
    """ffmpeg 인자 조립 (순수 함수 — 테스트 가능).

    출력은 항상 mp4(H.264+AAC): Discord 인라인 재생·미리보기 호환이 가장 좋다.
    scale=-2:{h}로 가로를 짝수로 맞추고, +faststart로 미리보기를 살린다.
    """
    v = plan.video_kbps
    args = [
        ffmpeg, "-hide_banner", "-y", "-i", src,
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", f"{v}k", "-maxrate", f"{int(v * 1.2)}k", "-bufsize", f"{v * 2}k",
        "-vf", f"scale=-2:{plan.height}",
        "-r", str(plan.fps),
    ]
    if plan.audio_kbps:
        args += ["-c:a", "aac", "-b:a", f"{plan.audio_kbps}k"]
    else:
        args += ["-an"]
    args += ["-movflags", "+faststart", dest]
    return args
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video.py tests/test_video.py
git commit -m "feat(video): parse_progress and build_args (pure)"
```

---

### Task 4: `video.py` — `probe` + `encode` (subprocess)

**Files:**
- Modify: `notro_app/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: `parse_ffmpeg_info`, `parse_progress`, `build_args`
- Produces: `probe(ffmpeg: str, path: str) -> VideoMeta | None`, `encode(ffmpeg: str, src: str, plan: EncodePlan, dest: str, on_progress=None, should_cancel=None) -> bool`

- [ ] **Step 1: Write the failing test**

`tests/test_video.py`에 추가 (실제 ffmpeg 없이 subprocess를 가짜로 주입):

```python
import notro_app.video as video_mod


def test_probe_parses_stderr_from_subprocess(monkeypatch):
    class FakeCompleted:
        stderr = SAMPLE

    monkeypatch.setattr(video_mod.subprocess, "run", lambda *a, **k: FakeCompleted())
    m = video_mod.probe("ffmpeg.exe", "clip.mp4")
    assert m.height == 1080 and m.has_audio is True


def test_probe_returns_none_when_ffmpeg_missing(monkeypatch):
    def boom(*a, **k):
        raise OSError("not found")

    monkeypatch.setattr(video_mod.subprocess, "run", boom)
    assert video_mod.probe("ffmpeg.exe", "clip.mp4") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py -v`
Expected: FAIL — `AttributeError: module 'notro_app.video' has no attribute 'subprocess'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video.py` 상단 import에 추가하고 함수를 덧붙인다:

```python
import os
import subprocess
```

```python
CREATE_NO_WINDOW = 0x08000000   # 콘솔 창이 뜨지 않게


def probe(ffmpeg: str, path: str) -> VideoMeta | None:
    """`ffmpeg -i`로 메타데이터를 읽는다. 출력 파일이 없어 종료 코드는 항상 1이지만,
    필요한 정보는 stderr에 이미 다 나와 있다."""
    try:
        p = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path],
            capture_output=True, text=True, errors="replace",
            creationflags=CREATE_NO_WINDOW, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_ffmpeg_info(p.stderr or "")


def encode(ffmpeg: str, src: str, plan: EncodePlan, dest: str,
           on_progress=None, should_cancel=None) -> bool:
    """한 번의 인코딩만 책임진다 (재시도 판단은 호출자 몫).
    on_progress(seconds_done) 콜백, should_cancel() -> True면 즉시 중단."""
    try:
        proc = subprocess.Popen(
            build_args(ffmpeg, src, plan, dest),
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, errors="replace", creationflags=CREATE_NO_WINDOW,
        )
    except OSError:
        return False
    try:
        for line in proc.stderr:
            if should_cancel and should_cancel():
                proc.terminate()
                return False
            t = parse_progress(line)
            if t is not None and on_progress:
                on_progress(t)
        return proc.wait() == 0 and os.path.exists(dest)
    finally:
        if proc.poll() is None:
            proc.terminate()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (16 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video.py tests/test_video.py
git commit -m "feat(video): probe and encode via ffmpeg subprocess"
```

---

### Task 4b: `video.py` — 실행 중인 ffmpeg 추적 (앱 종료 시 고아 프로세스 방지)

**Files:**
- Modify: `notro_app/video.py`
- Test: `tests/test_video.py`

**Interfaces:**
- Consumes: 없음
- Produces: `terminate_all() -> None` — 실행 중인 모든 ffmpeg를 종료한다 (app.py의 `on_quit_extra`가 호출)

> **왜 필요한가:** 인코딩 스레드는 daemon이라 앱 종료 시 그냥 죽지만, **ffmpeg 프로세스는 부모가 죽어도 계속 돈다**(고아 프로세스). 사용자가 인코딩 중 Notro를 종료하면 CPU를 계속 먹는 ffmpeg가 남는다. spec §5의 "인코딩 중 앱 종료 → 프로세스 종료" 요구사항이다.

- [ ] **Step 1: Write the failing test**

`tests/test_video.py`에 추가:

```python
def test_terminate_all_kills_tracked_processes():
    class FakeProc:
        def __init__(self):
            self.killed = False

        def poll(self):
            return None            # 아직 살아 있다

        def terminate(self):
            self.killed = True

    p = FakeProc()
    video_mod._ACTIVE.add(p)
    try:
        video_mod.terminate_all()
        assert p.killed is True
        assert p not in video_mod._ACTIVE
    finally:
        video_mod._ACTIVE.discard(p)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py::test_terminate_all_kills_tracked_processes -v`
Expected: FAIL — `AttributeError: module 'notro_app.video' has no attribute '_ACTIVE'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video.py`에 추가하고, `encode()`가 프로세스를 등록·해제하도록 고친다:

```python
import threading

_ACTIVE = set()            # 실행 중인 ffmpeg 프로세스
_ACTIVE_LOCK = threading.Lock()


def terminate_all() -> None:
    """앱 종료 시 호출 — 인코딩 중이던 ffmpeg가 고아 프로세스로 남지 않게 한다."""
    with _ACTIVE_LOCK:
        procs = list(_ACTIVE)
        _ACTIVE.clear()
    for p in procs:
        try:
            if p.poll() is None:
                p.terminate()
        except Exception:
            pass
```

`encode()`의 `try:` 블록을 다음으로 교체한다 (등록/해제 추가):

```python
    with _ACTIVE_LOCK:
        _ACTIVE.add(proc)
    try:
        for line in proc.stderr:
            if should_cancel and should_cancel():
                proc.terminate()
                return False
            t = parse_progress(line)
            if t is not None and on_progress:
                on_progress(t)
        return proc.wait() == 0 and os.path.exists(dest)
    finally:
        if proc.poll() is None:
            proc.terminate()
        with _ACTIVE_LOCK:
            _ACTIVE.discard(proc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (17 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video.py tests/test_video.py
git commit -m "fix(video): track running ffmpeg so app quit doesn't leave orphans"
```

---

### Task 5: `config.py` + `ffmpeg_setup.py` — `find_ffmpeg`

**Files:**
- Modify: `notro_app/config.py` (상수 추가)
- Create: `notro_app/ffmpeg_setup.py`
- Test: `tests/test_ffmpeg_setup.py`

**Interfaces:**
- Consumes: 없음
- Produces: `config.VIDEO_EXTS: tuple[str, ...]`, `config.BIN_DIR: str`, `ffmpeg_setup.find_ffmpeg() -> str | None`

- [ ] **Step 1: Write the failing test**

`tests/test_ffmpeg_setup.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ffmpeg_setup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notro_app.ffmpeg_setup'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/config.py`에 추가 (`DATA_DIR` 정의 아래):

```python
# 비디오 압축 대상 확장자 (출력은 항상 mp4)
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")

# 내려받은 ffmpeg 보관 위치 (배포물에 포함하지 않는다)
BIN_DIR = os.path.join(DATA_DIR, "bin")
```

`notro_app/ffmpeg_setup.py`:

```python
# -*- coding: utf-8 -*-
"""ffmpeg 조달.

ffmpeg를 배포물에 넣지 않는다: (1) 설치 크기를 30MB 늘릴 이유가 없고,
(2) x264가 들어간 빌드는 GPL이라 배포 시 고지 의무가 생긴다. 사용자의 승인 아래
사용자 머신이 PyPI에서 받게 하면 두 문제가 모두 사라진다 — WebView2 부트스트래퍼와 같은 구조.
"""

from __future__ import annotations

import os
import shutil

from . import config


def find_ffmpeg() -> str | None:
    """내려받은 것 → 시스템 PATH 순으로 찾는다. 없으면 None."""
    local = os.path.join(config.BIN_DIR, "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    return shutil.which("ffmpeg")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ffmpeg_setup.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/config.py notro_app/ffmpeg_setup.py tests/test_ffmpeg_setup.py
git commit -m "feat(video): VIDEO_EXTS/BIN_DIR config and find_ffmpeg"
```

---

### Task 6: `ffmpeg_setup.py` — `download_ffmpeg`

**Files:**
- Modify: `notro_app/ffmpeg_setup.py`
- Test: `tests/test_ffmpeg_setup.py`

**Interfaces:**
- Consumes: `config.BIN_DIR`
- Produces: `_pick_wheel(data: dict) -> tuple[str, str] | None`, `_pick_binary(names: list[str]) -> str | None`, `download_ffmpeg(on_progress=None) -> str | None`

- [ ] **Step 1: Write the failing test**

`tests/test_ffmpeg_setup.py`에 추가:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ffmpeg_setup.py -v`
Expected: FAIL — `AttributeError: module 'notro_app.ffmpeg_setup' has no attribute '_pick_wheel'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/ffmpeg_setup.py`에 추가 (import도 함께):

```python
import hashlib
import json
import urllib.request

PYPI_JSON = "https://pypi.org/pypi/imageio-ffmpeg/json"
DOWNLOAD_MB = 30      # 사용자에게 보여줄 대략적인 크기


def _pick_wheel(data: dict) -> tuple[str, str] | None:
    """PyPI JSON에서 최신 win_amd64 wheel의 (url, sha256)."""
    ver = data.get("info", {}).get("version")
    for f in data.get("releases", {}).get(ver, []):
        name = f.get("filename", "")
        if name.endswith(".whl") and "win_amd64" in name:
            return f["url"], f["digests"]["sha256"]
    return None


def _pick_binary(names: list[str]) -> str | None:
    """wheel(zip) 안에서 Windows용 ffmpeg 실행 파일 경로."""
    for n in names:
        if "/binaries/ffmpeg-win" in n and n.endswith(".exe"):
            return n
    return None


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: str, on_progress=None) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Notro"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if on_progress and total:
                on_progress(done / total)


def download_ffmpeg(on_progress=None) -> str | None:
    """PyPI의 imageio-ffmpeg wheel을 받아 SHA256을 검증하고 ffmpeg.exe만 꺼낸다.
    실패하면 None (치명적이지 않다 — 압축 기능만 못 쓴다)."""
    import zipfile

    try:
        with urllib.request.urlopen(PYPI_JSON, timeout=15) as r:
            data = json.load(r)
    except Exception:
        return None
    picked = _pick_wheel(data)
    if not picked:
        return None
    url, sha = picked

    os.makedirs(config.BIN_DIR, exist_ok=True)
    tmp = os.path.join(config.BIN_DIR, "_ffmpeg_wheel.zip")
    try:
        _download(url, tmp, on_progress)
        if _sha256(tmp).lower() != sha.lower():
            return None
        with zipfile.ZipFile(tmp) as z:
            member = _pick_binary(z.namelist())
            if not member:
                return None
            out = os.path.join(config.BIN_DIR, "ffmpeg.exe")
            with z.open(member) as src, open(out, "wb") as f:
                shutil.copyfileobj(src, f)
        return out
    except Exception:
        return None
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ffmpeg_setup.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add notro_app/ffmpeg_setup.py tests/test_ffmpeg_setup.py
git commit -m "feat(video): download ffmpeg from PyPI wheel with SHA256 verification"
```

---

### Task 7: `monitor.py` — 비디오 감지 → 콜백

**Files:**
- Modify: `notro_app/monitor.py`
- Test: `tests/test_monitor_video.py`

**Interfaces:**
- Consumes: `config.VIDEO_EXTS`, `config.LIMIT_BYTES`
- Produces: `Monitor.on_video_oversize: callable(path) | None` — 한도 초과 비디오 파일이 복사되면 호출된다

- [ ] **Step 1: Write the failing test**

`tests/test_monitor_video.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_monitor_video.py -v`
Expected: FAIL — `AttributeError: 'Monitor' object has no attribute 'on_video_oversize'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/monitor.py`의 `Monitor.__init__`에 한 줄 추가:

```python
        self.on_video_oversize = None  # 한도 초과 비디오 감지 콜백 (app.py가 배선)
```

그리고 `process_clipboard()`의 파일 분기(`elif isinstance(content, list):`)를 다음으로 교체한다:

```python
        elif isinstance(content, list):
            # 파일이 복사된 경우(CF_HDROP). 비디오는 감지만 하고 오케스트레이션에
            # 위임한다 — 인코딩은 수십 초라 감시 루프를 막으면 안 된다.
            paths = [p for p in content if isinstance(p, str)]
            if len(paths) != 1:
                return
            path = paths[0]
            ext = os.path.splitext(path)[1].lower()

            if ext in config.VIDEO_EXTS:
                try:
                    size = os.path.getsize(path)
                except OSError:
                    return
                if size > config.LIMIT_BYTES and self.on_video_oversize:
                    self.on_video_oversize(path)
                return

            if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"):
                try:
                    size = os.path.getsize(path)
                    if size > config.LIMIT_BYTES:
                        orig_bytes = size
                        img = Image.open(path)
                        img.load()
                except Exception:
                    return
            if img is None:
                return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_monitor_video.py tests/test_compress.py -v`
Expected: PASS (기존 이미지 테스트 회귀 없음)

- [ ] **Step 5: Commit**

```bash
git add notro_app/monitor.py tests/test_monitor_video.py
git commit -m "feat(video): detect oversized video in clipboard and hand off via callback"
```

---

### Task 8: i18n — 5개 언어 문자열

**Files:**
- Modify: `notro_app/i18n.py`
- Test: `tests/test_i18n.py`

**Interfaces:**
- Consumes: 없음
- Produces: 키 `video_confirm_title`, `video_meta`, `video_estimate`, `video_warn_quality`, `video_need_ffmpeg`, `video_btn_compress`, `video_btn_cancel`, `video_btn_close`, `video_downloading`, `video_encoding`, `video_done`, `video_fail_toobig`, `video_fail_download`, `video_fail_encode`

- [ ] **Step 1: Write the failing test**

`tests/test_i18n.py`에 추가:

```python
def test_video_keys_exist_in_all_languages():
    keys = ["video_confirm_title", "video_meta", "video_estimate", "video_warn_quality",
            "video_need_ffmpeg", "video_btn_compress", "video_btn_cancel", "video_btn_close",
            "video_downloading", "video_encoding", "video_done",
            "video_fail_toobig", "video_fail_download", "video_fail_encode"]
    for lang in i18n.SUPPORTED_LANGS:
        for k in keys:
            assert k in i18n.STRINGS[lang], f"{lang} missing {k}"


def test_video_placeholders_match_across_languages():
    import re
    def ph(s):
        return set(re.findall(r"\{(\w+)", s))
    for k in ("video_meta", "video_estimate", "video_need_ffmpeg",
              "video_downloading", "video_encoding", "video_done", "video_fail_toobig"):
        ref = ph(i18n.STRINGS["en"][k])
        for lang in i18n.SUPPORTED_LANGS:
            assert ph(i18n.STRINGS[lang][k]) == ref, f"{lang}/{k}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_i18n.py -v`
Expected: FAIL — `KeyError`/assert "en missing video_confirm_title"

- [ ] **Step 3: Write minimal implementation**

`notro_app/i18n.py`의 `current_lang = "en"` 바로 위에 추가:

```python
# ---------- 비디오 압축 (v2.6) ----------
_VIDEO_STRINGS = {
    "en": {
        "video_confirm_title": "Compress this video?",
        "video_meta": "{name} · {size} · {dur} · {res}",
        "video_estimate": "Estimate: about {size} · {res}",
        "video_warn_quality": "Quality will drop noticeably at this length.",
        "video_need_ffmpeg": "Video compression needs ffmpeg (about {mb} MB). Download it?",
        "video_btn_compress": "Compress",
        "video_btn_cancel": "Cancel",
        "video_btn_close": "Close",
        "video_downloading": "Downloading ffmpeg… {pct}%",
        "video_encoding": "Encoding… {pct}%",
        "video_done": "Compressed to {size} — press Ctrl+V in Discord.",
        "video_fail_toobig": "This video can't be squeezed under {limit}. Trim it shorter, or you'd need Nitro.",
        "video_fail_download": "Couldn't download ffmpeg.",
        "video_fail_encode": "Encoding failed.",
    },
    "ko": {
        "video_confirm_title": "이 영상을 압축할까요?",
        "video_meta": "{name} · {size} · {dur} · {res}",
        "video_estimate": "예상: 약 {size} · {res}",
        "video_warn_quality": "이 길이에서는 화질이 크게 떨어져요.",
        "video_need_ffmpeg": "비디오 압축에는 ffmpeg(약 {mb}MB)가 필요해요. 받을까요?",
        "video_btn_compress": "압축하기",
        "video_btn_cancel": "취소",
        "video_btn_close": "닫기",
        "video_downloading": "ffmpeg 다운로드 중… {pct}%",
        "video_encoding": "인코딩 중… {pct}%",
        "video_done": "{size}로 압축했어요 — 디스코드에서 Ctrl+V 하세요.",
        "video_fail_toobig": "이 영상은 {limit} 이하로 줄일 수 없어요. 더 짧게 자르거나 Nitro가 필요해요.",
        "video_fail_download": "ffmpeg를 받지 못했어요.",
        "video_fail_encode": "인코딩에 실패했어요.",
    },
    "ja": {
        "video_confirm_title": "この動画を圧縮しますか？",
        "video_meta": "{name} · {size} · {dur} · {res}",
        "video_estimate": "予想: 約 {size} · {res}",
        "video_warn_quality": "この長さでは画質がかなり低下します。",
        "video_need_ffmpeg": "動画の圧縮には ffmpeg（約 {mb}MB）が必要です。ダウンロードしますか？",
        "video_btn_compress": "圧縮する",
        "video_btn_cancel": "キャンセル",
        "video_btn_close": "閉じる",
        "video_downloading": "ffmpeg をダウンロード中… {pct}%",
        "video_encoding": "エンコード中… {pct}%",
        "video_done": "{size} に圧縮しました — Discord で Ctrl+V してください。",
        "video_fail_toobig": "この動画は {limit} 以下にできません。短く切るか、Nitro が必要です。",
        "video_fail_download": "ffmpeg をダウンロードできませんでした。",
        "video_fail_encode": "エンコードに失敗しました。",
    },
    "zh": {
        "video_confirm_title": "要压缩这个视频吗？",
        "video_meta": "{name} · {size} · {dur} · {res}",
        "video_estimate": "预计: 约 {size} · {res}",
        "video_warn_quality": "这个长度下画质会明显下降。",
        "video_need_ffmpeg": "视频压缩需要 ffmpeg（约 {mb}MB）。要下载吗？",
        "video_btn_compress": "压缩",
        "video_btn_cancel": "取消",
        "video_btn_close": "关闭",
        "video_downloading": "正在下载 ffmpeg… {pct}%",
        "video_encoding": "正在编码… {pct}%",
        "video_done": "已压缩到 {size} — 在 Discord 中按 Ctrl+V。",
        "video_fail_toobig": "这个视频无法压到 {limit} 以下。请剪短一些，否则需要 Nitro。",
        "video_fail_download": "无法下载 ffmpeg。",
        "video_fail_encode": "编码失败。",
    },
    "es": {
        "video_confirm_title": "¿Comprimir este vídeo?",
        "video_meta": "{name} · {size} · {dur} · {res}",
        "video_estimate": "Estimado: unos {size} · {res}",
        "video_warn_quality": "Con esta duración la calidad bajará notablemente.",
        "video_need_ffmpeg": "La compresión de vídeo necesita ffmpeg (unos {mb} MB). ¿Descargarlo?",
        "video_btn_compress": "Comprimir",
        "video_btn_cancel": "Cancelar",
        "video_btn_close": "Cerrar",
        "video_downloading": "Descargando ffmpeg… {pct}%",
        "video_encoding": "Codificando… {pct}%",
        "video_done": "Comprimido a {size}: pulsa Ctrl+V en Discord.",
        "video_fail_toobig": "Este vídeo no cabe en {limit}. Recórtalo o necesitarás Nitro.",
        "video_fail_download": "No se pudo descargar ffmpeg.",
        "video_fail_encode": "Error al codificar.",
    },
}
for _lang, _table in _VIDEO_STRINGS.items():
    STRINGS[_lang].update(_table)
del _VIDEO_STRINGS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_i18n.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notro_app/i18n.py tests/test_i18n.py
git commit -m "feat(video): i18n strings for the video compression flow (5 languages)"
```

---

### Task 9: `video_window.py` — 확인·진행 창

**Files:**
- Create: `notro_app/video_window.py`
- Test: 없음 (GUI — 기존 관례상 단위 테스트 제외. `welcome.py`도 테스트가 없다)

**Interfaces:**
- Consumes: `i18n.tr`, `video.VideoMeta`, `video.EncodePlan`
- Produces: `fmt_size(bytes) -> str`, `fmt_dur(seconds) -> str`, `VideoWindow(...)` — `.show()`, `.set_progress(text, pct)`, `.set_done(text)`, `.set_failed(text)`, `.accepted: threading.Event`, `.cancelled: threading.Event`

- [ ] **Step 1: Write the failing test** (포매터만 순수 함수로 테스트한다)

`tests/test_video.py`에 추가:

```python
from notro_app.video_window import fmt_dur, fmt_size


def test_fmt_size():
    assert fmt_size(9_961_472) == "9.5MB"
    assert fmt_size(512) == "0.0MB"


def test_fmt_dur():
    assert fmt_dur(72.34) == "1:12"
    assert fmt_dur(5) == "0:05"
    assert fmt_dur(3661) == "61:01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_video.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notro_app.video_window'`

- [ ] **Step 3: Write minimal implementation**

`notro_app/video_window.py`:

```python
# -*- coding: utf-8 -*-
"""비디오 압축 확인·진행 창.

토스트가 아니라 창인 이유: 알림을 끈 사용자에게 토스트는 도달하지 못한다(v2.5.5에서
확인한 문제). 인코딩은 수십 초 CPU를 쓰므로 사용자 승인 없이 시작하지 않는다.
welcome.py와 같은 방식(pywebview + Python에서 HTML 생성 + js_api)을 쓴다.
"""

from __future__ import annotations

import html as _html
import threading

from . import APP_NAME
from .i18n import tr

WIN_W, WIN_H = 480, 380

_CSS = """
  * { box-sizing: border-box; }
  body { margin:0; padding:22px 26px; background:#313338; color:#dbdee1;
         font-family:"Segoe UI",system-ui,sans-serif; -webkit-user-select:none; user-select:none; }
  h1 { margin:0 0 12px; font-size:17px; color:#fff; }
  .row { font-size:13px; line-height:1.6; color:#b5bac1; }
  .est { margin-top:8px; font-size:13.5px; color:#fff; }
  .warn { margin-top:10px; padding:9px 12px; border-left:3px solid #f0b232;
          background:#2b2d31; border-radius:6px; font-size:12.5px; }
  .bar { margin-top:16px; height:8px; background:#1e1f22; border-radius:4px; overflow:hidden; }
  .bar > i { display:block; height:100%; width:0%; background:#5865f2; transition:width .2s; }
  .status { margin-top:10px; font-size:13px; }
  .btns { margin-top:18px; display:flex; gap:8px; }
  button { flex:1; padding:10px; border:none; border-radius:6px; font-size:13.5px;
           font-weight:600; cursor:pointer; background:#4e5058; color:#fff; }
  button.primary { background:#5865f2; }
  button:hover { filter:brightness(1.1); }
  .hidden { display:none; }
"""


def fmt_size(n: int) -> str:
    """9961472 → '9.5MB'"""
    return f"{n / 1024 / 1024:.1f}MB"


def fmt_dur(sec: float) -> str:
    """72.34 → '1:12'"""
    total = int(sec)
    return f"{total // 60}:{total % 60:02d}"


class _Api:
    def __init__(self, accepted: threading.Event, cancelled: threading.Event):
        self.window = None
        self._accepted = accepted
        self._cancelled = cancelled

    def accept(self):
        self._accepted.set()

    def cancel(self):
        self._cancelled.set()
        self.close()

    def close(self):
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass


class VideoWindow:
    """확인 → 진행 → 완료/실패를 한 창에서 전환한다."""

    def __init__(self, headline: str, meta_line: str, estimate: str,
                 warn: str | None, accept_label: str):
        self.accepted = threading.Event()
        self.cancelled = threading.Event()
        self._api = _Api(self.accepted, self.cancelled)
        self._headline = headline
        self._meta_line = meta_line
        self._estimate = estimate
        self._warn = warn
        self._accept_label = accept_label
        self._win = None

    def _html(self) -> str:
        e = _html.escape
        warn = f'<div class="warn">{e(self._warn)}</div>' if self._warn else ""
        return (
            '<!doctype html><html><head><meta charset="utf-8">'
            f"<title>{e(APP_NAME)}</title><style>{_CSS}</style></head><body>"
            f"<h1>{e(self._headline)}</h1>"
            f'<div class="row">{e(self._meta_line)}</div>'
            f'<div class="est">{e(self._estimate)}</div>'
            f"{warn}"
            '<div id="prog" class="hidden">'
            '  <div class="bar"><i id="fill"></i></div>'
            '  <div class="status" id="status"></div>'
            "</div>"
            '<div class="btns" id="btns">'
            f'  <button class="primary" id="ok">{e(self._accept_label)}</button>'
            f'  <button id="no">{e(tr("video_btn_cancel"))}</button>'
            "</div>"
            "<script>"
            'document.getElementById("ok").onclick = function () {'
            '  document.getElementById("btns").classList.add("hidden");'
            '  document.getElementById("prog").classList.remove("hidden");'
            "  window.pywebview.api.accept();"
            "};"
            'document.getElementById("no").onclick = function () {'
            "  window.pywebview.api.cancel();"
            "};"
            "function notroProgress(text, pct) {"
            '  document.getElementById("status").textContent = text;'
            '  document.getElementById("fill").style.width = pct + "%";'
            "}"
            "function notroFinish(text) {"
            '  document.getElementById("prog").classList.add("hidden");'
            '  document.getElementById("btns").classList.remove("hidden");'
            '  document.getElementById("ok").classList.add("hidden");'
            '  document.getElementById("no").textContent = ' + f'"{e(tr("video_btn_close"))}";'
            '  document.querySelector(".est").textContent = text;'
            '  document.querySelector(".row").textContent = "";'
            "}"
            "</script></body></html>"
        )

    def show(self):
        import webview

        self._win = webview.create_window(
            APP_NAME, html=self._html(), js_api=self._api,
            width=WIN_W, height=WIN_H, resizable=False,
        )
        self._api.window = self._win
        return self._win

    def set_progress(self, text: str, pct: int):
        if self._win is None:
            return
        try:
            self._win.evaluate_js(f"notroProgress({_js(text)}, {int(pct)})")
        except Exception:
            pass

    def finish(self, text: str):
        """완료·실패 공통: 메시지를 보여주고 [닫기]만 남긴다."""
        if self._win is None:
            return
        try:
            self._win.evaluate_js(f"notroFinish({_js(text)})")
        except Exception:
            pass

    def close(self):
        self._api.close()


def _js(s: str) -> str:
    """JS 문자열 리터럴로 안전하게 감싼다."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_video.py -v`
Expected: PASS (fmt_size/fmt_dur 테스트 통과)

- [ ] **Step 5: Commit**

```bash
git add notro_app/video_window.py tests/test_video.py
git commit -m "feat(video): confirm/progress window (pywebview)"
```

---

### Task 10: `app.py` — 오케스트레이션 + 재시도

**Files:**
- Modify: `notro_app/app.py`
- Test: 없음 (스레드·GUI 오케스트레이션 — 기존 관례상 단위 테스트 제외)

**Interfaces:**
- Consumes: `monitor.on_video_oversize`, `ffmpeg_setup.find_ffmpeg/download_ffmpeg`, `video.probe/plan_encode/encode`, `video_window.VideoWindow`, `clipboard_win.set_clipboard_file`
- Produces: 없음 (최종 배선)

- [ ] **Step 1: 코드 작성** (오케스트레이션은 TDD 대상이 아니라 배선이다)

`notro_app/app.py`의 v2(피커) 분기에서 `picker.create_window()` 직전에 다음을 추가한다:

```python
    def _handle_video(path: str):
        """한도 초과 비디오: 확인 창 → (필요시 ffmpeg 다운로드) → 인코딩 → 클립보드 교체.
        monitor 스레드를 막지 않도록 별도 스레드에서 돈다. 클립보드는 성공했을 때만 바꾼다."""
        import os as _os

        from . import ffmpeg_setup, video
        from . import clipboard_win as _cb
        from .video_window import VideoWindow, fmt_dur, fmt_size

        ff = ffmpeg_setup.find_ffmpeg()
        name = _os.path.basename(path)
        try:
            src_size = _os.path.getsize(path)
        except OSError:
            return

        meta = video.probe(ff, path) if ff else None
        if ff and meta is None:
            # ffmpeg는 있는데 읽지 못했다 = 비디오가 아니거나 손상됐다.
            # 창도 띄우지 않고 조용히 무시한다 (spec §5) — 오탐으로 사용자를 방해하지 않는다.
            return
        plan = video.plan_encode(meta, config.LIMIT_BYTES) if meta else None

        if meta and not plan:                       # 하한 미달 — 정직하게 실패
            limit = fmt_size(config.LIMIT_BYTES)
            w = VideoWindow(tr("video_confirm_title"),
                            tr("video_meta", name=name, size=fmt_size(src_size),
                               dur=fmt_dur(meta.duration), res=f"{meta.height}p"),
                            tr("video_fail_toobig", limit=limit), None,
                            tr("video_btn_close"))
            w.show()
            return

        if ff and meta and plan:
            est = tr("video_estimate", size=fmt_size(config.LIMIT_BYTES),
                     res=f"{plan.height}p{plan.fps}")
            meta_line = tr("video_meta", name=name, size=fmt_size(src_size),
                           dur=fmt_dur(meta.duration), res=f"{meta.height}p{int(meta.fps)}")
            warn = tr("video_warn_quality") if plan.warn else None
            accept = tr("video_btn_compress")
        else:                                       # ffmpeg가 없다 — 먼저 받아야 한다
            est = tr("video_need_ffmpeg", mb=ffmpeg_setup.DOWNLOAD_MB)
            meta_line = tr("video_meta", name=name, size=fmt_size(src_size), dur="-", res="-")
            warn = None
            accept = tr("video_btn_compress")

        w = VideoWindow(tr("video_confirm_title"), meta_line, est, warn, accept)
        w.show()

        def _work():
            if not w.accepted.wait(timeout=300):    # 5분 내 응답 없으면 포기
                return
            nonlocal ff, meta, plan
            if not ff:
                ff = ffmpeg_setup.download_ffmpeg(
                    on_progress=lambda frac: w.set_progress(
                        tr("video_downloading", pct=int(frac * 100)), int(frac * 100)))
                if not ff:
                    w.finish(tr("video_fail_download"))
                    return
                meta = video.probe(ff, path)
                plan = video.plan_encode(meta, config.LIMIT_BYTES) if meta else None
                if not plan:
                    w.finish(tr("video_fail_toobig", limit=fmt_size(config.LIMIT_BYTES)))
                    return

            out = _os.path.join(config.TEMP_DIR,
                                _os.path.splitext(name)[0] + "_notro.mp4")
            for attempt in range(2):                # 1-pass 오차 → 1회만 재시도
                ok = video.encode(
                    ff, path, plan, out,
                    on_progress=lambda done: w.set_progress(
                        tr("video_encoding", pct=int(done / meta.duration * 100)),
                        int(done / meta.duration * 100)),
                    should_cancel=w.cancelled.is_set)
                if w.cancelled.is_set():
                    if _os.path.exists(out):
                        _os.remove(out)
                    return
                if not ok:
                    w.finish(tr("video_fail_encode"))
                    return
                if _os.path.getsize(out) <= config.LIMIT_BYTES:
                    break
                if attempt == 0:                    # 여전히 크다 — 비트레이트를 낮춰 한 번 더
                    plan = video.EncodePlan(plan.height, plan.fps,
                                            int(plan.video_kbps * 0.8),
                                            plan.audio_kbps, plan.warn)
                else:
                    w.finish(tr("video_fail_encode"))
                    return

            if _cb.set_clipboard_file(out):
                monitor.last_seq = _cb.get_sequence_number()   # 자기 출력 재처리 방지
                w.finish(tr("video_done", size=fmt_size(_os.path.getsize(out))))
            else:
                w.finish(tr("notify_clipboard_fail"))

        threading.Thread(target=_work, daemon=True).start()

    monitor.on_video_oversize = lambda p: threading.Thread(
        target=_handle_video, args=(p,), daemon=True).start()
```

그리고 **종료 시 ffmpeg 정리**를 배선한다. `icon = tray.build_icon(...)`의 `on_quit_extra`를 다음으로 교체한다:

```python
    from . import video as _video

    icon = tray.build_icon(
        monitor, picker=picker, listener=listener, updater=upd,
        on_quit_extra=lambda: (listener.stop(), asset_server.stop(), picker.destroy(),
                               _video.terminate_all(),   # 인코딩 중이면 ffmpeg를 죽인다
                               upd.stop() if upd else None),
    )
```

- [ ] **Step 2: 회귀 확인**

Run: `python -m pytest -q`
Expected: 기존 테스트 전부 PASS (신규 테스트 포함)

- [ ] **Step 3: 문법 검증**

Run: `python -m py_compile notro_app/app.py notro_app/video.py notro_app/video_window.py notro_app/ffmpeg_setup.py`
Expected: 출력 없음(성공)

- [ ] **Step 4: Commit**

```bash
git add notro_app/app.py
git commit -m "feat(video): wire clipboard detection to confirm window, download, encode, and clipboard swap"
```

---

### Task 11: 버전 · CHANGELOG · 최종 검증

**Files:**
- Modify: `notro_app/__init__.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`, `README.ko.md`, `README.ja.md`, `README.zh.md`, `README.es.md`

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: 버전 올리기**

`notro_app/__init__.py`:

```python
__version__ = "2.6.0"
```

- [ ] **Step 2: CHANGELOG 항목 추가**

`CHANGELOG.md`의 최상단 릴리스 위에 추가:

```markdown
## [2.6.0] - 2026-07-12

### Added
- **Video compression.** Copy a game clip that is too big for Discord (the free limit is
  **10 MB**, lowered from 25 MB in 2024) and Notro offers to shrink it: it reads the file
  with ffmpeg, picks a resolution/bitrate/fps that fits, encodes, and puts the compressed
  `.mp4` back on the clipboard so <kbd>Ctrl</kbd>+<kbd>V</kbd> attaches it in Discord.
  - Notro **asks first** in a window (not a toast — toasts never reach users who turned
    notifications off) and shows what to expect: `52MB · 1:12 · 1080p60 → about 9.5MB · 480p30`.
  - If a clip simply cannot fit — the floor is **360p / 300 kbps** — Notro says so instead
    of producing an unwatchable mosaic.
  - **ffmpeg is not bundled.** It is downloaded on demand (about 30 MB, SHA256-verified)
    the first time you compress a video, or taken from PATH if you already have it. Notro
    never ships the binary, so nothing changes for people who don't compress video.
```

- [ ] **Step 3: README 5개 언어에 비디오 섹션 추가**

각 README에서 **다운로드 섹션 헤딩 바로 앞**에 아래 섹션을 삽입한다(피커 설명 뒤에 오도록).

`README.md` — `## Download & run (recommended)` 앞:

```markdown
## Video clips (v2.6)

Copy a game clip that's too big for Discord and Notro **asks whether to compress it**,
showing what to expect: `52MB · 1:12 · 1080p60 → about 9.5MB · 480p30`. It encodes with
ffmpeg and puts the compressed `.mp4` back on the clipboard, so <kbd>Ctrl</kbd>+<kbd>V</kbd>
attaches it in Discord.

**ffmpeg is never bundled** — it's downloaded on demand (~30 MB, checksum-verified) the
first time you compress a video, or taken from your PATH if you already have it. If a clip
can't fit under the limit even at 360p, Notro tells you instead of producing a mosaic.
```

`README.ko.md` — `## 내려받기 & 실행 (권장)` 앞:

```markdown
## 비디오 클립 (v2.6)

디스코드에 올리기엔 큰 게임 클립을 복사하면 Notro가 **압축할지 물어봅니다**. 예상 결과도
함께 보여줍니다: `52MB · 1:12 · 1080p60 → 약 9.5MB · 480p30`. ffmpeg로 인코딩한 뒤 압축된
`.mp4`를 클립보드에 넣어 주므로, 디스코드에서 <kbd>Ctrl</kbd>+<kbd>V</kbd>만 하면 첨부됩니다.

**ffmpeg는 앱에 포함하지 않습니다** — 처음 비디오를 압축할 때 필요한 만큼만 내려받고
(약 30MB, 체크섬 검증), PATH에 이미 있으면 그걸 씁니다. 360p로 낮춰도 한도에 못 맞추는
영상이면 모자이크를 만드는 대신 "줄일 수 없다"고 알려 줍니다.
```

`README.ja.md` — `## ダウンロードと実行（推奨）` 앞:

```markdown
## 動画クリップ（v2.6）

Discord には大きすぎるゲームクリップをコピーすると、Notro が**圧縮するかどうか尋ねます**。
予想結果も表示します: `52MB · 1:12 · 1080p60 → 約 9.5MB · 480p30`。ffmpeg でエンコードし、
圧縮した `.mp4` をクリップボードに戻すので、Discord で <kbd>Ctrl</kbd>+<kbd>V</kbd> すれば
添付されます。

**ffmpeg は同梱しません** — 初めて動画を圧縮するときに必要な分だけダウンロードし
（約 30MB、チェックサム検証）、PATH にあればそれを使います。360p まで下げても上限に収まらない
場合は、モザイクを作る代わりに「縮められません」と伝えます。
```

`README.zh.md` — `## 下载与运行（推荐）` 앞:

```markdown
## 视频剪辑（v2.6）

复制一段对 Discord 来说过大的游戏剪辑，Notro 会**询问是否压缩**，并显示预计结果:
`52MB · 1:12 · 1080p60 → 约 9.5MB · 480p30`。它用 ffmpeg 编码，并把压缩后的 `.mp4`
放回剪贴板，因此在 Discord 中按 <kbd>Ctrl</kbd>+<kbd>V</kbd> 即可作为附件上传。

**ffmpeg 不会随应用打包** — 首次压缩视频时才按需下载（约 30MB，带校验和验证），
如果 PATH 中已有则直接使用。若剪辑即使降到 360p 也放不下，Notro 会直接告诉你，
而不是生成马赛克。
```

`README.es.md` — `## Descargar y ejecutar (recomendado)` 앞:

```markdown
## Clips de vídeo (v2.6)

Copia un clip de juego demasiado grande para Discord y Notro **te pregunta si comprimirlo**,
mostrando qué esperar: `52MB · 1:12 · 1080p60 → unos 9.5MB · 480p30`. Codifica con ffmpeg y
deja el `.mp4` comprimido en el portapapeles, así que con <kbd>Ctrl</kbd>+<kbd>V</kbd> se
adjunta en Discord.

**ffmpeg no se incluye en la aplicación**: se descarga solo cuando hace falta (unos 30 MB,
con verificación de checksum), o se usa el de tu PATH si ya lo tienes. Si un clip no cabe
bajo el límite ni siquiera a 360p, Notro te lo dice en vez de generar un mosaico.
```

- [ ] **Step 4: 전체 검증**

Run: `python -m pytest -q`
Expected: 전부 PASS

Run: `PYTHONIOENCODING=utf-8 python -c "from notro_app import i18n; import re; base=set(i18n.STRINGS['en']); print('parity:', all(set(i18n.STRINGS[l])==base for l in i18n.SUPPORTED_LANGS))"`
Expected: `parity: True`

- [ ] **Step 5: Commit**

```bash
git add notro_app/__init__.py CHANGELOG.md README.md README.ko.md README.ja.md README.zh.md README.es.md
git commit -m "feat(video): v2.6.0 — video compression for Discord's 10MB limit"
```

---

## 완료 기준

- `pytest` 전부 통과 (신규: `test_video.py`, `test_ffmpeg_setup.py`, `test_monitor_video.py`)
- i18n 5개 언어 키·placeholder 파리티 유지
- `requirements.txt` 무변경 (새 pip 의존성 0개)
- 실제 게임 클립으로 수동 검증: 탐색기에서 Ctrl+C → 확인 창 → 압축 → Discord에서 Ctrl+V로 첨부되는지
