# Show HN 게시용 초안

> 이 파일은 게시 준비용 메모입니다. 저장소에 남겨두기 싫으시면 게시 후 지우세요.

## 제출 폼

**URL 칸:** `https://github.com/writingdeveloper/Notro`
(GitHub 저장소를 넣습니다. 릴리스 페이지가 아니라 저장소 — README의 데모 GIF가
첫인상을 만들기 때문입니다.)

**Title 칸** (72자, 제한 80자):

```
Show HN: Notro – Discord emoji and big files without patching the client
```

대안 (골라 쓰세요):
- `Show HN: Notro – a Discord clipboard helper that doesn't patch the client` (73자)
- `Show HN: Notro – Discord emoji picker and upload compressor, no client mods` (75자)

**Text 칸:** 비워 둡니다. URL을 넣으면 본문은 못 쓰고, 대신 아래 내용을
**게시 직후 첫 댓글**로 답니다 (Show HN 관례).

---

## 첫 댓글 (게시하자마자 바로 답니다)

```
Discord's free upload limit is 10 MB, and I kept hitting it with screenshots
and game clips. The usual fix for the emoji half of this is a client mod like
BetterDiscord or Vencord, which patches the Discord client — I didn't want to
run that on my own account, let alone hand it to anyone else.

So this stays outside the app entirely. It watches the clipboard, and when
something is too big it re-encodes and puts the result back as a file, so you
just press Ctrl+V. The emoji picker works the same way: pick one, it goes on
the clipboard, and it sends a Ctrl+V — the same class of input automation as
the Windows emoji panel (Win+.). Nothing is injected, and it never sees an
account or a token.

A few things that took longer than I expected:

- Discord draws an image attachment at its native pixel size. A library with
  a 20x20 GIF next to a 1080x1080 PNG pastes one as a speck and the other as
  a full picture, which looks nothing like a real custom emoji. Emoji are now
  normalized to 48px on the longest edge just before pasting — that's the size
  Discord renders a jumbo custom emoji at.

- For video, trimming beats every encoder setting. A 30-second 1080p60 capture
  has to fall back to 1080p30 to fit 10 MB. Trimmed to the seven seconds you
  actually wanted, the same budget keeps it at 1080p60. So the confirm dialog
  takes a start/end range and re-plans as you type.

- ffmpeg isn't bundled. Builds with x264 are GPL, so it's fetched to the user's
  machine on demand, after they confirm, and checked against the SHA-256 that
  PyPI publishes.

- The bug I'm most glad I caught before anyone was using it: the updater wrote
  its helper batch file as UTF-8, but cmd.exe reads batch files in the OEM code
  page. On a Korean install the temp path contains Hangul, so the installer path
  came out as mojibake and the batch executed nothing at all. The update would
  download, verify its hash, the user would click "restart to update", the app
  would exit — and never come back, with no error. Writing the file in the code
  page cmd actually reads fixes it. 8.3 short paths don't help; Windows 10 keeps
  the Hangul in the generated short name.

Limitations, up front: Windows only (the clipboard and tray parts are Win32),
and it isn't code-signed yet, so SmartScreen will call the publisher unknown.
Every release ships a SHA-256 next to the installer and CI builds only from a
tag, so you can check what you downloaded or build it yourself. Also, the honest
trade-off of doing this from outside the client: your emoji arrive as image
attachments, not as inline emoji.

MIT, Python + PyInstaller.
```

---

## 첫 1시간 예상 질문과 답변

미리 정해두면 훨씬 편합니다. HN은 첫 30분 반응 속도로 프론트 진입이 갈립니다.

**"서명도 없는 Windows 바이너리를 왜 받아야 하나?"** ← 거의 확실히 나옵니다
> Fair. You don't have to: the source builds with `pip install -r requirements.txt`
> and `build.bat`. Releases are built by GitHub Actions from a tag, never from my
> machine, and each one ships a SHA-256 next to the installer. Code signing is the
> obvious gap — I've been putting off applying to SignPath's OSS programme until
> the project has enough of a track record to qualify.

**"Vencord/BetterDiscord와 뭐가 다른가?"**
> Those patch the Discord client, which is what makes the inline-emoji trick
> possible and also what carries the account risk. This never touches the client,
> so the cost is that emoji show up as attachments rather than inline. It's a
> real downgrade in output for a real reduction in risk.

**"Discord가 막을 수 있나?"**
> There's nothing on their side to block — from Discord's perspective it's
> indistinguishable from a person pasting a file. That's also why I'm comfortable
> recommending it.

**"클립보드를 항상 감시한다는 게 찜찜하다"**
> Reasonable. It polls the clipboard sequence number every 400 ms and only reads
> when it changes; nothing is stored unless you turn on capture saving, which is
> off by default. There's no telemetry and it contacts four endpoints total, all
> listed in SECURITY.md.

**"맥/리눅스는?"**
> Windows only. The clipboard handling, the tray, and the keystroke simulation
> are all Win32. A port would be mostly a rewrite of those layers.

**"왜 Electron/Tauri가 아니라 Python인가?"**
> The picker is a WebView2 window driven from Python (pywebview); the rest is
> ctypes against Win32. Python made the image and ffmpeg work quick to iterate
> on. The cost is a ~17 MB installer, which for a tray utility I decided was
> acceptable.

---

## 게시 직전 체크

1. **시각**: 미 동부 오전 8~10시 = **한국시간 22:00~24:00**. HN은 첫 30분이 결정적입니다
2. URL 칸에 저장소 주소, Title은 위 문구, Text 칸은 비움
3. 게시하자마자 **첫 댓글을 바로** 답니다
4. 이후 1시간은 댓글에 붙어 있습니다 — 늦은 답변은 점수에 직접 손해입니다
5. 절대 하지 말 것: 지인에게 upvote 부탁 (HN은 이걸 탐지하고 글을 죽입니다)

## 게시 후

- GitHub → Insights → Traffic → **Referring sites**에서 유입을 확인합니다
  (현재 고유 방문자 0명이라 신호가 깨끗합니다)
- 나온 피드백은 이슈로 정리해 두면 다음 릴리스 근거가 됩니다
