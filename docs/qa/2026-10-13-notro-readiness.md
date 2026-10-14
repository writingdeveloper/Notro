# Notro readiness QA checkpoint — 2026-10-13

Baseline: main 537c8b0, published v2.10.3. Feature work is isolated in the feat/notro-rea-product-marketing-20261013 worktree, without changing the running Discord installation or user library.

## Verified

- Official Discord upload FAQ read: free 20MB / Nitro Basic 50MB / Nitro 500MB. Variable trial limits may apply. https://support.discord.com/hc/en-us/articles/25444343291031-File-Attachments-FAQ
- Safe 20MB free default, old manually selected 10MB preserved, actual ceiling separated from 95% encode target. Regressions tested.
- Watched folder discovery includes JPG/JPEG; unit reproduction fixed.
- Opt-in portable ZIP media packs with private Capture exclusion, no source URLs, content hashes, zip entry/path/size checks and duplicate merging.
- First-run welcome has a "Try picker" action; auto-send remains off by default.
- Local media HTTP responses streamed via bounded 64 KiB chunks.
- Python: 370 tests passed locally; Ruff 0.15.21 passed (0 issues). GitHub CI initially failed after floating Ruff resolved to 0.16.10 with expanded default rules; pinned the validated version and requires a second remote CI pass.
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

Follow-up draft PRs: Notro https://github.com/writingdeveloper/Notro/pull/1 ; portfolio SEO metadata https://github.com/writingdeveloper/portfolio/pull/36 (neither merged or deployed).

## Release candidate prepared

Source version has been advanced to **2.11.0**, with an unreleased CHANGELOG entry. No v2.11.0 tag or installer release was created. The feature branch candidate 5b14eba passed GitHub Actions CI and the manual Release workflow_dispatch build: EXE, Inno Setup installer and SHA256 (https://github.com/writingdeveloper/Notro/actions/runs/38486869698). Publishing was correctly skipped. GUI installation and code signing have not been validated.

Portfolio PR #36 passes type/lint/build/tests but the dependency audit fails with 11 findings (10 high, 1 critical); see https://github.com/writingdeveloper/portfolio/actions/runs/38486167720. Do not bypass audit or deploy; coordination with existing portfolio security work is required.


## Follow-up: OS-only compatibility and isolated native Windows QA

- REA is an offline developer investigation aid only, not bundled in or
  launched by Notro. Added architecture regression tests against runtime
  imports of REA/Discord private modules. No Discord process memory, IPC,
  message history or tokens were accessed.
- Win32 process-window identity enumeration detected one visible Discord
  desktop top-level window, matching the Discord.exe executable already
  running. Read-only verification; no keys were sent to that window.
- Optional auto-send is now guarded by the saved HWND and a public
  QueryFullProcessImageNameW process-name check. The target must still be
  focused before pasting and immediately before Enter. Paste still works in
  non-Discord Windows applications but they never receive automated Enter.
  Channel switches inside the same Discord window cannot be detected.
  Auto-send remains off by default.
- Actual Edge WebView2 smoke: a separate fixture window using two temporary
  PNG/JPEG items displayed both thumbnails, three tabs, pack import/export
  buttons, correct search results, KO/EN/JA/ZH/ES UI language updates, zero
  errors, closed normally. The fixture does not register global hotkeys, alter
  clipboard/registry, or invoke Discord.
- Asset URL server now uses a per-run bearer capability in the local URL
  path and a strict loopback Host check; regression tests cover
  unauthenticated asset URLs and spoofed Host. Runtime thumbnail loading
  verified in native WebView2.
- Imported pack manifests are now read through a bounded decompression path.
- Unverified: actual Discord file-attachment draft send, simultaneous
  channel changes, WebView2 native file-open/save dialogs with the user's
  profile, full installer installation or SmartScreen. Do not call
  these verified or publish yet.


## Verified continuation: standalone file-sharing UX

- A single ZIP file dropped into the picker now routes through the same Python
  validation method as the Settings Import button. Mixed multiple files retain
  the existing media-add flow.
- The native WebView2 fixture exported its two owned media assets, then
  simulated a ZIP drop through the real Python JS bridge. The importer safely
  skipped both duplicates, updated the on-screen status hint, and no JavaScript
  or WebView errors occurred. Five localized search labels and both actual
  thumbnails remained functional.
- Current local regression suite: **393 passed**, Ruff 0.15.21 clean,
  Python compileall passed and source version remains **2.11.0 unreleased**.
- This test does **not** simulate a real user's native Windows file-open
  dialog or Discord account; those acceptance criteria remain open in Plane.
