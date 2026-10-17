# Show HN 게시용 초안

> 출시 전 참고 메모이며 그대로 게시하면 안 됩니다. Hacker News는 AI 생성 글과
> 자동 포스팅을 금지합니다. 실제 QA와 릴리스 후 작성자가 자신의 말로
> 제목과 첫 댓글을 작성하세요. https://news.ycombinator.com/newsguidelines.html

**작성 원칙:** 읽는 사람이 *자기 상황*을 떠올리게 만드는 것이 목적입니다. 다만 HN은
홍보 문구 냄새에 강하게 반응하므로, 어조는 담백하게 두고 **구체적인 장면과 숫자**로
설득합니다. 과장 형용사·느낌표·"revolutionary" 류는 전부 역효과입니다.

## 제출 폼

**URL 칸:** `https://github.com/writingdeveloper/Notro`
(릴리스가 아니라 저장소 — README 상단 데모 GIF가 첫인상을 만듭니다.)

**Title 칸** — 권장:

```
Show HN: Notro – custom emoji and oversized uploads on Discord, no client mods
```

78자 (제한 80자). 혜택 두 개와 차별점이 한 줄에 다 들어갑니다.

대안:
- `Show HN: Notro – use your own emoji on Discord without patching the client` (74자)
- `Show HN: Notro – Discord's 20MB limit, handled from your clipboard` (66자) — 압축 쪽만 강조

**Text 칸:** 비웁니다. 아래 내용을 **게시 직후 첫 댓글**로 답니다 (Show HN 관례).

---

## 첫 댓글

```
Discord's free upload limit is currently 20 MB (as of August 2026). If you screenshot at any real
resolution you hit it constantly, and the fix is always the same tedious
loop: find the file, open an editor, export it smaller, go back, paste
again.

Notro removes the loop. It sits in the tray and watches the clipboard, so
an image that's too big is already shrunk by the time you press Ctrl+V.
Under the limit it does nothing at all.

For oversized game clips, Notro offers a confirmation window with
estimated output size and trim controls. Encoding takes time, quality
can degrade, and some clips do not fit. Actual measured examples will
be added only after validating real output files.

The other half is a hotkey emoji picker. Ctrl+Shift+E anywhere, type to
filter, Enter to paste. If you've collected custom emoji from servers you're
no longer in, or you just want to use your own images without paying
monthly for it, that's the gap it fills.

What made me write it: some alternatives to the emoji problem modify the Discord client. I didn't want that
running on my own account, let alone hand it to anyone else. Notro stays
outside the app — it prepares your clipboard and sends a Ctrl+V, the same
class of input automation as the Windows emoji panel (Win+.). It never sees
an account or a token, and there's nothing installed inside Discord to break
the next time Discord updates.

One thing that surprised me while building it: Discord draws an attachment
at its native pixel size. So a library holding a 20x20 GIF next to a
1080x1080 PNG pastes one as a speck and the other as a full picture, which
looks nothing like an emoji. They're normalized to 48px on the longest edge
before pasting now — the size Discord renders a jumbo custom emoji at — so
they come out looking like emoji instead of like random attachments.

Limitations, up front: Windows only, and it isn't code-signed yet, so
SmartScreen will call the publisher unknown. Every release ships a SHA-256
next to the installer and CI builds only from a tag, so you can verify what
you downloaded or build it yourself. And because it works from outside the
client, your emoji arrive as image attachments rather than inline emoji —
that's the trade for not touching Discord.

No telemetry and no accounts; network endpoints are documented, including installation dependencies. MIT.
```

**분량**: HN 첫 댓글로 적당합니다. 더 줄이고 싶으면 "One thing that surprised me"
문단을 빼세요 — 가장 먼저 덜어낼 수 있는 부분입니다.

**넣지 않은 것과 그 이유**
- 업데이터 인코딩 버그 → 왜 쓰고 싶은지에 아무 답이 안 되고, 서명 없는 자동 업데이트를
  받아달라는 글에서 "내 업데이터가 앱을 조용히 죽였다"는 신뢰를 깎습니다
- ffmpeg GPL·SHA 검증, 초성 검색, 창 크기 기억 → README에 있습니다. 첫 댓글은
  "왜 필요한가"만 담고, 나머지는 질문이 나오면 답합니다

---

## 첫 1시간 예상 질문과 답변

HN은 첫 30분 반응 속도로 프론트 진입이 갈립니다. 미리 정해두세요.

**"미서명 Windows 바이너리를 왜 받아야 하나?"**
> Notro is currently unsigned by choice, so Windows can show an unknown
> publisher warning. CI-built releases include a SHA-256 alongside source
> code, but that does not substitute for verifying the publisher's identity.
> Do not disable system protections solely to use this application.

**"Vencord/BetterDiscord와 뭐가 다른가?"**
> Those patch the client, which is what makes true inline emoji possible and also
> what carries the account risk. This never touches it, so the cost is that emoji
> arrive as attachments instead of inline. A real downgrade in output for a real
> reduction in risk — that trade was the whole point for me.

**"Discord가 막을 수 있나?"**
> There is no guarantee. Notro doesn't inject into or modify the client
> and uses normal Windows clipboard/paste. Future Discord changes may
> break it; this tool isn't approved or endorsed by Discord, and
> optional auto-send needs separate compatibility and policy review.

**"클립보드를 항상 감시한다는 게 찜찜하다"**
> It polls the clipboard sequence number and reads new data as needed.
> Auto-save is off by default. Notro documents its network connections
> and does not transmit clipboard content to a remote server. See SECURITY.md.

**"맥/리눅스는?"**
> Windows only. The clipboard handling, the tray, and the keystroke simulation are
> all Win32, so a port would be mostly a rewrite of those layers.

**"왜 Python인가?"**
> The picker is a WebView2 window driven from Python; the rest is ctypes against
> Win32. Python made the image and ffmpeg work fast to iterate on. The cost is a
> ~17 MB installer, which for a tray utility I decided was fine.

**"왜 그냥 이미지를 미리 줄여두지 않나?"**
> Because the point is not having to think about it. It only acts when a copy would
> actually exceed the limit, and leaves everything else alone.

---

## 게시 시각 (LA / 태평양 시간 기준)

HN 프론트 진입은 **첫 30분 upvote 속도**로 갈립니다. 미 동부가 일하고 유럽이 아직
깨어 있는 시간이 겹치는 구간이 가장 좋습니다.

| LA (PT) | 뉴욕 (ET) | 런던 | 평가 |
|---|---|---|---|
| 05:00–06:00 | 08:00–09:00 | 13:00–14:00 | 이론상 최적, 다만 너무 이름 |
| **06:00–08:00** | **09:00–11:00** | **14:00–16:00** | **권장.** 미국 업무 시작 + 유럽 오후 |
| 08:00–09:30 | 11:00–12:30 | 16:00–17:30 | 무난. 유럽이 빠지기 시작 |
| 09:30 이후 | 12:30 이후 | 18:00 이후 | 약함. 미국 점심 + 유럽 퇴근 |

**실제 릴리스와 설치 QA 이후에만 게시.** 시간대 조언은 경험칙입니다. 가능하다면 화요일 오전 6~8시(PT)를 검토. 9시 반을 넘길 것 같으면 **수요일 아침으로
미루는 편**이 낫습니다 — Show HN은 사실상 한 번뿐이라, 약한 창에 태우는 것보다
하루 미루는 비용이 훨씬 쌉니다. 화·수·목 아무 날이나 괜찮습니다.

## 게시 직전 체크

1. URL 칸에 저장소 주소, Title은 위 문구, **Text 칸은 비움**
2. 게시하자마자 **첫 댓글 바로** 달기
3. 이후 **90분은 댓글에 붙어 있기** — 자리를 뜰 일정이 있으면 그날은 올리지 않습니다
4. **지인 upvote 부탁 금지** — HN이 탐지하고 글을 죽입니다

## 게시 후

GitHub → Insights → **Traffic → Referring sites**로 유입 확인 (현재 고유 방문자 0명이라
신호가 깨끗합니다). 나온 피드백은 이슈로 정리해 두면 다음 릴리스 근거가 됩니다.
