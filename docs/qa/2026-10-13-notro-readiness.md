# Notro readiness QA checkpoint — 2026-10-13

Baseline: main 537c8b0, published v2.10.3. Feature work is isolated in the feat/notro-rea-product-marketing-20261013 worktree, without changing the running Discord installation or user library.

## Verified

- Official Discord upload FAQ read: free 20MB / Nitro Basic 50MB / Nitro 500MB. Variable trial limits may apply. https://support.discord.com/hc/en-us/articles/25444343291031-File-Attachments-FAQ
- Safe 20MB free default, old manually selected 10MB preserved, actual ceiling separated from 95% encode target. Regressions tested.
- Watched folder discovery includes JPG/JPEG; unit reproduction fixed.
- Opt-in portable ZIP media packs with private Capture exclusion, no source URLs, content hashes, zip entry/path/size checks and duplicate merging.
- First-run welcome has a "Try picker" action; auto-send remains off by default.
- Local media HTTP responses streamed via bounded 64 KiB chunks.
- Python test suite and ruff lint run as part of the release candidate checks.
- Browser mock smoke: Chrome headless screenshot of standalone picker, 6 tiles/3 tabs, import/export Settings buttons visible, Escape closes settings, search "miku" returned 2 tiles, 0 page JS errors. THIS IS NOT DISCORD E2E.
- Synthetic library benchmark, one sample on @4080 (cold/warm/search in milliseconds):
  - 100 files: 4.02 / 0.70 / 0.87
  - 1,000 files: 33.70 / 1.46 / 2.36
  - 5,000 files: 161.56 / 6.59 / 12.64
  Browser DOM performance and actual GIF memory still need testing.
- REA static audit: see docs/research/2026-10-13-rea-discord-audit.md.

## Still open

- Real Discord E2E image/video delivery, DPI, Korean filenames, GIF playback, chat focus and tray installation QA.
- Code-signing / SmartScreen trust: not solved; do not claim signed.
- Lossy GIF optimization needs opt-in quality preview and cancellation.
- Browser picker with 5,000 mixed-size real assets, WebView2 process memory and scrolling performance.
- Standalone media pack ZIP is NOT a full registry/settings/watched-folder backup.
- Production website metadata still needs changes in a separate deployment repository.
- No public Show HN/Reddit/Discord marketing posts performed.

## Release gate

1. Run Python test suite, ruff, release version contract on Windows 3.12 CI.
2. Test native WebView2 file dialogs, 5 languages and keyboard-only first run.
3. In an explicitly private test draft with auto-send disabled, paste 19.5MB (unchanged), 24MB (compressed), JPG, GIF and video; confirm disk originals unchanged.
4. Bump package version, build a fresh installer (never republish the old v2.10.3 tag), verify SHA256 and signing.
5. Update Plane from QA to Done only with E2E evidence. Publish only after E2E and user-approved release trust review.
