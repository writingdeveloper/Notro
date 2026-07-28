<p align="center">
  <img src="docs/icon.png" width="88" alt="Notro">
</p>

<h1 align="center">Notro</h1>

<p align="center">
  <b>니트로 없이 커스텀 이모지와 큰 파일을 — 디스코드 클라이언트는 건드리지 않고.</b>
</p>

<p align="center">
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/writingdeveloper/Notro?label=download&color=5865F2" alt="최신 릴리스"></a>
  <a href="../../releases"><img src="https://img.shields.io/github/downloads/writingdeveloper/Notro/total?color=57F287" alt="다운로드 수"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4" alt="Windows 10 또는 11">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

<p align="center"><a href="README.md">English</a> | <b>한국어</b> | <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a></p>

---

디스코드가 돈을 받는 두 가지를, 앱 바깥에서 해결합니다.

- **이미지가 14MB인데 무료 한도는 10MB입니다.** 복사하는 순간 Notro가 알아서 줄여
  클립보드에 되돌려 놓습니다. <kbd>Ctrl</kbd>+<kbd>V</kbd>만 누르면 됩니다.
- **커스텀 이모지를 어디서든 쓰고 싶습니다.** <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd>를
  누르고 고르면 입력창에 들어갑니다.

**패치도, 인젝션도, 로그인도 하지 않습니다.** Notro는 클립보드를 준비해 두고
<kbd>Ctrl</kbd>+<kbd>V</kbd>를 대신 눌러 주는 트레이 앱입니다 — Windows 이모지
패널(<kbd>Win</kbd>+<kbd>.</kbd>)과 같은 부류의 입력 자동화입니다. 디스코드 클라이언트를
수정하지 않고, 계정이나 토큰은 아예 보지 않습니다. 정직한 한계는 이것입니다: 받는 사람에게는
네이티브 인라인 이모지가 아니라 이미지 첨부로 보입니다.

<p align="center">
  <img src="docs/picker.png" width="420" alt="Notro 피커: 이모지/스티커/GIF 탭, 왼쪽 컬렉션 바, 상단 검색">
</p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ NotroSetup.exe 내려받기</b></a><br>
  <sub>관리자 권한 불필요. 사용자 폴더에 설치되고, 설정 → 앱에서 제거합니다.</sub>
</p>

---

## 피커

어디서든 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd>를 누르면 커서 옆에 어두운 팝업이
열립니다. **이모지 / 스티커 / GIF** 세 탭입니다.

**진짜 이모지 크기로 나갑니다.** 디스코드는 첨부 이미지를 원본 픽셀 크기 그대로 그립니다.
그래서 20×20 GIF와 1080×1080 PNG가 섞인 라이브러리는 하나는 먼지처럼, 하나는 사진만 하게
붙습니다. Notro는 붙여넣기 직전에 긴 변을 맞춥니다 — 이모지 **48px**(점보 커스텀 이모지와
같은 크기), 스티커 **160px**, GIF는 원본. **라이브러리 원본 파일은 건드리지 않고**
클립보드에 올라가는 사본만 조정합니다.

**이모지 넣기** — *"링크 복사"* URL을 붙여넣거나, 메시지에서 이모지를 그대로 복사했을 때
나오는 `<:이름:id>` 텍스트를 넣거나, 이미지 파일을 끌어다 놓거나, **감시 폴더**를 지정하거나,
아니면 `%APPDATA%\Notro\assets` 아래에 폴더를 하나 만들어 넣기만 해도 등록 절차 없이
컬렉션이 됩니다.

**다시 찾기** — 이름·키워드 검색에 **한글 초성**이 됩니다 (`ㅁㅋ` → `미쿠`). 즐겨찾기와
최근 사용 항목이 위에 남습니다.

**마우스 없이** — 방향키로 이동, <kbd>Enter</kbd>로 붙여넣기, <kbd>Esc</kbd>로 닫기.
핫키를 누른 뒤로는 키보드에서 손을 뗄 일이 없습니다.

<details>
<summary>피커 세부 동작</summary>

- 항목 우클릭 → 이름·키워드 수정, 컬렉션 이동, 링크로 붙여넣기(URL로 등록한 항목), 삭제.
- 같은 탭·컬렉션에 이미 있는 그림을 다시 넣으면 조용히 쌓이지 않고 알려줍니다.
- 움직이는 APNG 스티커는 등록 시 GIF로 변환됩니다 — 디스코드가 업로드된 APNG를 재생하지
  않기 때문입니다.
- 클립보드 버튼을 누르면 현재 클립보드 이미지가 **캡처** 컬렉션에 바로 저장됩니다. 피커
  설정에서 새 클립보드 이미지를 자동 저장할 수도 있고, 기본값은 꺼짐입니다.
- 창 크기를 조절할 수 있고 그 크기를 기억합니다(모니터 배율까지 감안).
- 한도를 넘는 항목: 정지 이미지는 자동 압축, 초과 GIF는 경고와 함께 원본 전송.
- 붙여넣은 뒤 <kbd>Enter</kbd>까지 대신 누르는 자동 전송 옵션이 있습니다 — 기본 꺼짐.

</details>

## 자동 압축

Notro는 클립보드를 지켜봅니다. 새 이미지가 들어오면 **디스코드가 실제로 만들어 낼 PNG
용량**을 계산하고, 한도 안이면 아무 일도 하지 않습니다. 넘으면 WebP → JPEG 순으로
다시 인코딩하며 품질을, 그래도 안 되면 해상도를 낮춰 ~9.5MB 아래로 맞춘 뒤, 결과를
**파일로** 클립보드에 올려 <kbd>Ctrl</kbd>+<kbd>V</kbd>가 첨부로 올라가게 합니다.

> 디스크의 원본 파일은 절대 건드리지 않습니다 — 클립보드만 교체합니다.

한도는 트레이에서 **10 / 50 / 500MB**(무료·니트로 베이직·니트로)로 바꿀 수 있습니다.

## 비디오 클립

너무 큰 게임 클립을 복사하면 Notro가 먼저 물어보면서, 어떻게 될지를 보여줍니다:

```
52MB · 1:12 · 1080p60  →  약 9.5MB · 480p30
```

같은 창에서 **구간을 자르고**(`시작 – 끝`) **오디오를 뺄** 수 있으며, 입력하는 대로 예상치가
갱신됩니다. 이게 어떤 인코더 설정보다 중요합니다: 30초짜리 1080p60 영상은 통째로는
**1080p30**으로 떨어지지만, 실제로 원했던 7초만 남기면 **1080p60**을 그대로 유지합니다.

**ffmpeg는 앱에 넣지 않습니다.** 처음 비디오를 압축할 때 필요한 만큼만 내려받고(~30MB,
SHA-256 검증), `PATH`에 이미 있으면 그것을 씁니다. 360p로도 한도에 못 들어가는 클립은
모자이크를 만드는 대신 정직하게 안 된다고 알려줍니다.

## 설치

**[`NotroSetup.exe`](../../releases/latest)**를 받아 실행하세요. 관리자 권한이 필요 없고
`%LOCALAPPDATA%\Programs\Notro`에 설치됩니다.

> ⚠️ 아직 **코드 서명이 없어서** SmartScreen이 "게시자를 알 수 없음"이라고 경고합니다 —
> *추가 정보 → 실행*을 누르시면 됩니다. 릴리스마다 `NotroSetup.exe.sha256`을 함께 올리므로
> 받은 파일을 정확히 검증할 수 있고, [소스에서 직접 빌드](#소스에서-실행빌드설정)해도 됩니다.
> 자세한 내용은 [SECURITY.md](SECURITY.md#code-signing)와
> [코드 서명 정책](CODE_SIGNING.md)에 있습니다.

**Windows 10 사용자:** 피커에는 Microsoft Edge WebView2 런타임이 필요합니다(Windows 11은
기본 내장). 없으면 설치 프로그램이 받아서 설치합니다. 없어도 피커만 비활성화되고 압축은
그대로 동작합니다.

### 어디로 갔나요?

Notro에는 **메인 창이 없습니다** — 시계 옆 트레이에서 실행됩니다. **Windows 11은 새 트레이
아이콘을 기본으로 숨기므로**, 안 보이면 **`^`** 화살표를 누르고 Notro 아이콘을 작업 표시줄로
끌어다 놓으세요.

<p align="center">
  <img src="docs/welcome.png" width="360" alt="Notro 첫 실행 안내 창">
</p>

나머지는 전부 트레이 아이콘 우클릭에 있습니다: 피커 단축키, 일시정지, 최근 처리 내역,
업로드 한도, 언어, 출력 폴더, 그리고 Windows 시작 시 자동 실행(**기본 꺼짐**).

## 개인정보

Notro는 클립보드를 감시하므로, 그 내용을 어떻게 다루는지 밝혀 둡니다.

- **복사한 내용은 어디로도 전송되지 않습니다.** 텔레메트리·분석·크래시 리포트·계정,
  어느 것도 없습니다.
- **요청하지 않으면 저장하지도 않습니다.** 캡처 자동 저장은 기본 꺼짐입니다.
- 외부 통신은 정확히 **네 곳**뿐이고 전부 문서화돼 있습니다: GitHub(업데이트 확인과
  인스톨러, SHA-256 검증), `cdn.discordapp.com`(링크로 이모지를 등록할 때만),
  PyPI(비디오를 처음 압축할 때 ffmpeg 조달, 역시 SHA-256 검증).
- 제거해도 **라이브러리는 일부러 남깁니다**(`%APPDATA%\Notro`). 재설치해도 이모지를
  잃지 않게 하려는 것입니다.

파일이 정확히 어디에 저장되는지까지 [SECURITY.md](SECURITY.md)에 있습니다.

## 언어

English, 한국어, 日本語, 中文(简体), Español — Windows 언어를 자동 감지하고 트레이에서
언제든 바꿀 수 있습니다.

<details>
<summary><a id="소스에서-실행빌드설정"></a>소스에서 실행·빌드·설정</summary>

```sh
pip install -r requirements.txt
pythonw notro.py           # 실행
build.bat                  # dist\Notro.exe 빌드
```

Windows + Python 3.10 이상이 필요합니다.

압축 동작은 `notro_app/config.py`와 `notro_app/compress.py`에 있습니다:

| 설정 | 기본값 | 설명 |
|---|---|---|
| `LIMIT_MB` | 10 | 업로드 한도 — 트레이 메뉴에서 10/50/500 선택 가능 |
| `SAFETY` | 0.95 | 안전 마진 (약 9.5MB 목표) |
| `WEBP_QUALITIES` | 90–50 | WebP 품질 단계 |
| `MIN_SCALE` | 0.4 | 해상도 축소 하한 |

테스트:

```sh
pip install -r requirements-dev.txt
pytest
```

</details>

## 라이선스

[MIT](LICENSE). 배포물에 포함된 서드파티 구성요소와 각각의 라이선스는 — LGPL-3.0인
pystray를 포함해 — [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)에 정리해 두었습니다.

> Notro는 Discord와 무관한 비공식 도구이며, **Discord Inc.가 제휴/후원/승인한 프로젝트가
> 아닙니다.** "Discord"는 Discord Inc.의 상표입니다.
