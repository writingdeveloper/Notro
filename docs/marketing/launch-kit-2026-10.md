# Notro launch kit (2026-10)

## What it is

Independent Windows companion for Discord desktop: organize personal emoji/sticker/GIF media, paste with a hotkey, and prepare oversized screenshots and video. Nothing injects into Discord and no account token is needed. Images are attached as files, **not native Nitro emoji**. Not affiliated with Discord. Windows-only; current installer is unsigned.

EN headline: **Your emoji library. Your game clips. One Windows tray app.**
KO headline: **내 이모지와 게임 클립을, Windows 트레이에서 바로.**

EN supporting: "Paste your emoji as attachments, organize your GIFs, and prepare oversized media for Discord without modifying the client."
KO supporting: "개인 이모지·스티커·GIF를 라이브러리로 관리해 첨부파일로 붙여넣고, 큰 미디어를 업로드 한도에 맞게 준비합니다."

## Core audiences

1. Discord gamers with oversized screenshots and gameplay captures.
2. Users maintaining an owned/reusable personal emoji, sticker and GIF library.
3. Windows/open-source users preferring a standalone utility to client modifications.

## Three genuine 10–20s demo concepts

A. Big screenshot: use a real 24MB screenshot, show copy → size-aware compression → paste into an unpublished test draft. No fabricated comparisons.
B. Emoji hotkey: Ctrl+Shift+E → search → image attachment preview. On-screen subtitle: "Attachment, not native inline emoji."
C. Personal pack: user-owned assets → export ZIP → import into a clean test profile → find the saved sticker. Never redistribute copyrighted assets without rights.

Record the actual UI; do not represent the picker browser mock as a finished Discord integration demo.

## Manual promotion ladder

1. Finish real installer and Discord-draft E2E QA; if release is approved, publish a checksum-verified unsigned installer with a clear Windows warning.
2. Invite 10–20 volunteers, measure first-use task completion with consent, gather concrete UX bugs.
3. Publish concise EN/KO demos to relevant video channels, with a direct verified download link.
4. Contact moderators or check each community's promotion policy before Reddit/Discord posts. No mass spam, bought reactions or misleading claims.
5. Reuse and update existing docs/show-hn-draft.md for Show HN; answer with limitations and technical specifics, not invented numbers.
6. Product Hunt only after early-user evidence suggests value beyond developer communities.

## Privacy-respecting measurement

Landing-page visit and download CTA clicks, GitHub release counts, opt-in human testers' first-paste time and self-reported follow-up use. No application clipboard telemetry, account data or file-name analytics.

Illustrative 30-day experiment goals (not forecasts): 20 testers, 80% first-paste completion, median <=3 minutes to first success, >=10 actionable user reports.

The website https://writingdeveloper.blog/projects/notro still has outdated 10MB metadata. Replace in the separate website repository before broad promotion. Do not post publicly before real release QA.


## October 17, 2026 launch holds

- Published v2.10.3 differs from unreleased Draft PR v2.11.0. The releases/latest
  CTA must not advertise features that are not downloadable.
- Live writingdeveloper.blog/projects/notro still claims free 10MB, v2.0 and
  blanket Terms-safety. Portfolio Draft PR #36 fails npm security audit.
- Native synthetic QA is not real Windows user install or Discord paste proof.
- Docs demo.gif and picker.png have identifiable third-party character images.
  Verify marketing rights or replace with rights-cleared demonstration assets.
- Do not promise Discord endorsement, Terms compliance or that Discord cannot
  break/block future functionality. Auto-send remains off by default.
- Hacker News bans AI-generated submission text and automated posting.
  Reddit promotions must follow community rules, without unsolicited mass posts.
- User has explicitly excluded code signing. Disclose the unsigned status;
  do not request certificates or enable signing infrastructure.
- Complete limited opt-in beta QA and accurate releases/landing first, then
  human-managed public marketing with authentic demos.
