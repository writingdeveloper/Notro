# Notro v2.6 — 비디오 압축 설계

- 날짜: 2026-07-12
- 상태: 사용자 승인 완료
- 스코프: Discord 무료 업로드 한도(10MB)를 넘는 **비디오 파일**(게임 클립)을 클립보드에서 감지해 ffmpeg로 압축하고, 압축본을 파일로 클립보드에 되돌려 <kbd>Ctrl</kbd>+<kbd>V</kbd> 첨부가 되게 한다.

## 1. 배경

Notro는 이모지·스티커·GIF 피커와 **이미지** 자동 압축으로 Nitro의 유료 기능을 대체해 왔다. 그러나 Discord에서 "파일이 너무 큼"이 가장 자주 터지는 상황은 **게임 클립(mp4)** 이고, `monitor.py`는 이미지 확장자만 처리해 비디오는 손도 대지 않는다. 무료 한도는 2024년에 25MB → **10MB로 낮아져** 영상 수십 초도 담기 어렵다.

Nitro 혜택을 전수 검토한 결과, ToS-안전 제약(클라이언트 미수정 · 계정/토큰 미사용 · 클립보드 준비 + 로컬 Ctrl+V만) 안에서 대체 가능한 것은 **비디오 압축**과 **긴 메시지(2000자)** 둘뿐이다. 나머지(사운드보드, Super Reactions, 프로필 커스터마이징, HD 스트리밍, 앱 테마, 서버 부스트, Nitro Rewards)는 **계정 API(토큰) 또는 클라이언트 수정**이 필요해 설계상 불가능하다. 긴 메시지는 별도 스펙으로 다룬다.

### 1.1 성립성 검증 (필수 전제)

비디오 *데이터* 자체는 클립보드에 담기지 않지만, **파일 참조(CF_HDROP)** 는 담긴다. Notro는 **이미 CF_HDROP를 읽고 쓰고 있다**:

- 읽기: `ImageGrab.grabclipboard()` → 파일이 복사된 경우 **경로 리스트** 반환 (`monitor.py`가 이미 이 분기를 처리하며, 이미지 확장자만 거를 뿐이다)
- 쓰기: `cb.set_clipboard_file()` → CF_HDROP. **이미지조차 압축 후엔 "파일"로 붙여넣고 있다.**

12MB 더미 `.mp4`로 왕복을 실증했다: `set_clipboard_file()` → `grabclipboard()`가 `['...fake_clip.mp4']`를 반환하고 확장자·크기 판정이 정상 동작했다. 따라서 비디오는 **확장자만 추가하면 기존 파이프라인을 그대로 탄다.** 클립보드 계층은 수정하지 않는다.

유일한 차이는 진입 방식이다: 이미지는 스크린샷이 자동으로 클립보드에 들어오지만, 비디오는 사용자가 **파일을 Ctrl+C** 해야 한다(녹화 클립은 어차피 디스크 파일이므로 자연스럽다).

## 2. 확정 요구사항

| 항목 | 결정 |
|---|---|
| 트리거 | 한도 초과 비디오 감지 → **확인 창을 띄우고 사용자가 승인해야** 시작. 자동 시작 아님 — 인코딩은 수십 초 CPU를 쓴다 |
| 확인 신호 | **창**(pywebview). 토스트가 아니라 창인 이유: 알림을 끈 사용자에게 토스트는 도달하지 못한다(v2.5.5에서 확인한 문제) |
| 화질/속도 | **균형**: 1-pass 목표 비트레이트, 필요시 720p/480p로 축소, 60→30fps. 1분 클립 기준 20~40초 |
| 화질 하한 | **360p / 비디오 300 kbps**. 그 밑으로는 내려가지 않고 "10MB로 줄일 수 없습니다"라고 **정직하게 실패** |
| 예상 표시 | 확인 창에 `52MB · 1분12초 · 1080p60 → 약 9.5MB · 480p30` + 화질 저하 경고 |
| ffmpeg 조달 | **필요할 때 다운로드**(PyPI `imageio-ffmpeg` wheel ≈30MB, SHA256 검증) + 시스템 PATH 폴백. 기본 설치 크기 유지, **바이너리를 배포하지 않으므로 GPL 고지 의무가 발생하지 않는다** |
| 클립보드 | **성공했을 때만** `set_clipboard_file()`로 교체. 실패·취소 시 원본 유지 |
| 새 pip 의존성 | **없음** (`zipfile`/`urllib`/`subprocess`는 표준 라이브러리) |

## 3. 모듈 구성

### 3.1 `notro_app/video.py` (신규)

순수 계산과 부수효과를 분리한다(`compress.py`의 관례).

- `VideoMeta(duration, width, height, fps, has_audio)` / `EncodePlan(height, fps, video_kbps, audio_kbps, warn)` — dataclass
- **`parse_ffmpeg_info(stderr) -> VideoMeta | None`** — **순수 함수**. `ffmpeg -i`가 stderr로 뱉는 `Duration:`, `Stream ... Video: ... WxH ... N fps`, `Audio:`를 파싱. fps 분수형(`60000/1001`) 처리.
- **`plan_encode(meta, limit_bytes) -> EncodePlan | None`** — **순수 함수**. §4 알고리즘.
- **`parse_progress(line) -> float | None`** — **순수 함수**. `time=00:00:12.34` → `12.34`.
- `probe(ffmpeg, path) -> VideoMeta | None` — `ffmpeg -i` 실행 → `parse_ffmpeg_info`.
- `encode(ffmpeg, src, plan, dest, on_progress, should_cancel) -> bool` — ffmpeg 실행, stderr 스트리밍 → `parse_progress` → 진행률 콜백. 취소 시 `terminate()`.

**ffprobe를 쓰지 않는 이유**: `imageio-ffmpeg` wheel에는 `ffmpeg`만 들어 있다. ffprobe 하나를 위해 100MB+ 빌드를 받을 이유가 없으므로 `ffmpeg -i`의 stderr를 파싱한다.

### 3.2 `notro_app/ffmpeg_setup.py` (신규)

- `find_ffmpeg() -> str | None`: `config.BIN_DIR/ffmpeg.exe` → `shutil.which("ffmpeg")` → `None`
- `download_ffmpeg(on_progress) -> str | None`: PyPI JSON API로 `imageio-ffmpeg`의 최신 `win_amd64` wheel URL과 sha256을 조회 → 다운로드(진행률 콜백) → **SHA256 검증** → wheel(zip)에서 `imageio_ffmpeg/binaries/ffmpeg-win-*.exe` 추출 → `BIN_DIR/ffmpeg.exe`로 저장

`updater.py`의 "다운로드 → 해시 검증 → 적용" 패턴을 그대로 따른다.

### 3.3 `notro_app/video_window.py` (신규)

`welcome.py` 패턴(pywebview + Python에서 HTML 생성 + `js_api`)을 재사용한다. 한 창에서 4단계로 전환:

| 단계 | 내용 |
|---|---|
| 확인 | 원본 정보 → 예상 결과, 화질 경고, (ffmpeg 없으면) "약 30MB를 받아야 합니다". **[압축하기] [취소]** |
| 진행 | `ffmpeg 다운로드 중… 45%` → `인코딩 중… 62%` + **[취소]** |
| 완료 | `9.4MB로 압축됐어요 — Discord에서 Ctrl+V로 붙여넣으세요` **[닫기]** |
| 실패 | 사유 안내(하한 미달 / 다운로드 실패 / 인코딩 실패) **[닫기]** |

### 3.4 `notro_app/monitor.py` (수정)

파일 분기(`isinstance(content, list)`)에 비디오 확장자를 추가한다. **감지만 하고 콜백으로 위임**한다 — 감시 루프를 수십 초 막으면 클립보드 감시가 멈춘다.

```python
self.on_video_oversize = None      # app.py가 배선

if ext in config.VIDEO_EXTS and size > config.LIMIT_BYTES:
    if self.on_video_oversize:
        self.on_video_oversize(path)   # 별도 스레드에서 처리
    return
```

### 3.5 `notro_app/config.py` (수정)

- `VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")`
- `BIN_DIR = os.path.join(DATA_DIR, "bin")` — 내려받은 ffmpeg 보관 위치

### 3.6 `notro_app/app.py` (수정)

`monitor.on_video_oversize`를 배선한다. 별도 스레드에서: `probe` → `plan_encode` → 창 표시 → 사용자 승인 시 (필요하면 `download_ffmpeg` →) `encode` → `set_clipboard_file`.

**재시도 판단은 이 오케스트레이션이 맡는다.** 결과 파일이 여전히 한도를 넘으면(1-pass의 비트레이트 오차·컨테이너 오버헤드) 비디오 비트레이트를 ×0.8로 낮춰 **1회만** 재인코딩한다. `encode()`는 "한 번의 인코딩"만 책임지고 재시도를 알지 못한다.

## 4. 인코딩 알고리즘 (`plan_encode` — 순수 함수)

1. 목표 = `config.LIMIT_BYTES` (이미 `SAFETY=0.95`가 반영된 값이라 그대로 재사용)
2. 오디오 = **96 kbps** 고정 (무음이면 0)
3. `총 kbps = 목표bytes × 8 ÷ duration`, `비디오 kbps = 총 − 오디오`
4. 해상도 사다리 — 감당 가능한 최대를 고르되 **원본보다 키우지 않는다**:

| 해상도 | 필요 비디오 kbps |
|---|---|
| 1080p | ≥ 2500 |
| 720p | ≥ 1000 |
| 480p | ≥ 500 |
| **360p** | **≥ 300 (하한)** |

5. fps: 원본이 30을 넘고, 비디오 kbps가 **선택된 해상도의 60fps 요구치(= 위 표의 값 × 1.5)** 에 미달하면 **30fps로 낮춘다**. (60fps는 같은 체감 화질에 약 1.5배 비트레이트가 필요하다.) 원본이 30 이하면 그대로 둔다.
6. 비디오 kbps < 300 → **`None`** (압축 불가 → "10MB로 줄일 수 없습니다")
7. 480p 이하로 떨어지면 `warn=True` → 확인 창에 화질 저하 경고

ffmpeg 인자:

```
-c:v libx264 -preset veryfast -b:v {v}k -maxrate {v*1.2}k -bufsize {v*2}k
-vf scale=-2:{h} [-r 30] -c:a aac -b:a 96k (무음이면 -an) -movflags +faststart
```

`scale=-2:{h}`로 가로를 짝수로 맞추고, `-movflags +faststart`로 Discord 미리보기를 살린다.

**출력은 항상 `.mp4`(H.264 + AAC)로 통일한다.** 입력이 `.mkv`/`.webm`/`.avi`여도 mp4로 내보낸다 — Discord의 인라인 재생·미리보기 호환이 가장 좋기 때문이다.

## 5. 예외 처리

**원칙: 클립보드는 성공했을 때만 교체한다.** 실패·취소 시 원본 파일 참조를 그대로 두어 사용자가 다른 방법을 시도할 수 있게 한다.

| 상황 | 처리 |
|---|---|
| ffmpeg 없음 + 사용자가 다운로드 거부 | 창만 닫고 아무것도 하지 않음. 원본 유지 |
| ffmpeg 다운로드 실패(네트워크/해시 불일치) | 실패 안내 + 원본 유지. 다음에 재시도 가능 |
| `probe` 실패(비디오 아님/손상) | **조용히 무시** — 창도 띄우지 않음(오탐으로 사용자를 방해하지 않는다) |
| `plan_encode → None`(하한 미달) | "이 영상은 10MB로 줄일 수 없습니다" 안내 + 원본 유지 |
| 인코딩 실패(ffmpeg 오류) | 실패 안내 + 임시 파일 정리 + 원본 유지 |
| 인코딩 결과가 여전히 한도 초과 | 비트레이트 ×0.8로 **1회 재시도** → 그래도 초과면 실패 안내 |
| 사용자 취소 | `terminate()` + 임시 파일 삭제 + 원본 유지 |
| 인코딩 중 앱 종료 | `on_quit_extra`에서 프로세스 종료 |

## 6. 테스트

기존 관례대로 **순수 함수 위주**로 테스트한다(Windows API·GUI·실제 인코딩은 제외).

- `parse_ffmpeg_info()`: 정상 mp4, fps 분수형(`60000/1001`), **무음 영상**, 손상/비디오 아님 → `None`
- `plan_encode()`: 짧은 클립 → 1080p 유지 / 중간 → 720p30 / 긴 영상 → 480p·360p / 너무 긴 영상 → `None` / **원본보다 업스케일하지 않음** / 무음 → `audio_kbps == 0` / 경계값(정확히 300kbps)
- `parse_progress()`: `time=00:00:12.34` → `12.34`, 무관한 줄 → `None`
- `find_ffmpeg()`: 로컬 `BIN_DIR` 우선 → PATH 폴백 → 없으면 `None` (monkeypatch)
- `monitor`: 비디오 확장자 + 한도 초과 시 `on_video_oversize` 콜백이 호출되고, **이미지 경로는 기존 동작이 그대로 유지**되는지

실제 ffmpeg 실행은 통합 테스트로 두되 CI에 ffmpeg가 없으므로 `skipif`로 건너뛴다.

## 7. i18n

확인/진행/완료/실패 문자열을 5개 언어(en·ko·ja·zh·es)에 추가한다. 기존 파리티 검증(키·placeholder 일치)을 통과해야 한다.

## 8. MVP 제외 (P2+)

피커에 비디오 드래그앤드롭 → 압축 / 비디오 자동 압축 설정(확인 없이) / 하드웨어 인코딩(NVENC·QSV) / 2-pass 인코딩 / GIF 압축 / 여러 파일 동시 처리 / 오디오 비트레이트 조절 UI.

## 9. 버전

v2.6.0 (기능 추가).
