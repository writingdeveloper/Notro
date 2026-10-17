# Notro v2.11.0 — Release readiness review (2026-10-17)

Decision: **NO-GO for public v2.11.0 release or broad marketing today.**
An invited, opt-in preview/beta may be offered after the actual unsigned
installer smoke, Windows GUI first-run, and Discord *non-sending draft*
tests pass. NO tag, merge, newsletter blast or external post is approved
by this review. Signed builds are out of scope by user decision.

## What was inspected

- Notro repository, source, tests and separate feature worktree;
  GitHub Draft PR #1 vs. published latest v2.10.3.
- README in EN/KO/JA/ZH/ES, SECURITY.md, CODE_SIGNING.md,
  THIRD-PARTY-NOTICES.md, CHANGELOG.md, LICENSE, .github issue template,
  GitHub Actions CI/Release, installer.iss, contributor and PR templates.
- Current Windows picker native WebView2 fixtures, file dialogues, local
  media and video compression, secure imports, stored settings and
  update-handling design.
- GitHub portfolio Draft PR #36 and public Notro portfolio page.
- Plane workspace soursea, project NOTRO (details synchronized separately).
- Discord official file attachment guidance:
  https://support.discord.com/hc/ko/articles/25444343291031-
  (free 20MB, Nitro Basic 50MB, Nitro up to 1GB, may vary by account).
- Hacker News post/comment rules:
  https://news.ycombinator.com/newsguidelines.html

## Technical evidence at review time

| Area | Evidence | Result |
| --- | --- | --- |
| Windows Python suite | 438 tests at previous HEAD, new tests for 1GB and workflows | PASS locally, recheck on CI |
| Dependency security | pip-audit 2.10.1 with resolved runtime/dev/build requirements | No *known* advisories at audit time; not a malware guarantee |
| Import ZIP and settings | 8 real native Win32 Save/Open stages, with Korean filenames, isolated profile | PASS |
| WebView2 | Actual Windows picker, 5 languages, synthetic 5k DOM, GIF compare, settings controls | PASS for synthetic fixtures |
| Media 20MB boundary | Valid synthetic padded PNGs at 19.5MB, 20MB, 20MB+1B, 24MB | PASS; not real-world photo quality |
| Real-pixel media | Deterministic synthetic 3000x3000 high-entropy PNG about 27MB | Produced ~7.55MB decoded WebP, source unchanged |
| Video | Locally generated 5-sec 960x540 video with sine-wave audio, real ffmpeg | Encoded 854x480 @30fps with audio; trim/mute case PASS |
| 1GB Nitro preset | User-configurable; legacy 500MB remains | Use conservative decimal billion-byte target with 95% safety |
| Prior installer | Source e26122b, SHA/VersionInfo 2.11.0 validated, unsigned | Compiled only, NOT evidence of running installed app |
| New installer smoke | Windows GitHub-hosted QA install/exe version/uninstall only | Pending actual workflow success |
| Portfolio landing | https://writingdeveloper.blog/projects/notro | FAIL: still says free 10MB, v2.0, absolute ToS-safe |
| Portfolio security | Draft PR #36 check failed, multiple unresolved dependency PRs | BLOCKED; do not bypass npm audit |
| Published release | latest GitHub release v2.10.3, v2.11.0 unmerged Draft PR | NOT MATCHED for advertising new features |

## Mandatory P0 gates before broad public v2.11.0 launch

- [ ] **Real Discord non-sending draft interaction** on Windows 10 and Windows
      11: PNG/JPG/GIF, focus changes, CTRL+V file attachment preview, clipboard
      contents restored when applicable; auto-send OFF by default. No public
      message may be sent by automation or without explicit consent.
- [ ] **Installer runtime**: disposable Windows 10/11 install, uninstall,
      upgrade from v2.10.3 with real user data backed up (or synthetic only),
      first run tray icon/hotkey/keyboard/multimonitor DPI, no startup surprises,
      WebView2 missing and no-network scenarios. CI installer smoke is only
      the first sub-gate.
- [ ] **Version integrity**: merge reviewed candidate to main, CI and release
      validation pass, publish a version-matched artifact and checksum **only
      after** manual maintainer authorization; test installer download. All
      distributed binaries remain UNSIGNED; Windows warnings are disclosed.
- [ ] **Landing/content**: merge content safely only after portfolio dependency
      security audit is green; deployed page H1/title/meta/OG and both EN/KO
      descriptions reflect *published* release and free 20MB, up-to-1GB Nitro.
      Remove blanket claims of guaranteed Discord Terms compliance.
- [ ] **Rights-cleared demonstrations**: do not advertise from current
      demo.gif/picker.png with recognizable third-party anime/character assets
      until distribution rights are verified. Capture authentic Notro UI with
      personally owned/rights-cleared simple assets and measure real flows.
- [ ] **User trust/support**: privacy policy, debug-log redaction, reproducible
      checksum, unsigned notice, user-run installer permissions and private
      bug-report channel all manually reviewed.

## Important but beta-tolerable gaps (P1)

- Performance/peak memory with thousands of real animated GIFs (5k synthetic
  placeholders alone do not prove this).
- Video compression speed/quality for long clips, high-resolution games and
  unusual codecs. Synthetic 5-sec success is not a gameplay benchmark.
- Full first-run usability median from at least 5 consenting people, Korean
  and English; exact completion criteria must be measured, not estimated.
- Accessibility, keyboard-only file dialogues, high-contrast themes, captions.
- Portable pack/backup import error recovery with corrupt data and data-copy
  permission variations on Windows 10 and a non-English Windows user profile.
- Third-party licensing and third-party art in released marketing screenshots
  reviewed with concrete distribution permissions.

## GitHub/documentation corrections in progress

- Contributor guide and PR template explicitly distinguish mocks vs reality.
- CI and unsigned manual Release workflow now fail when pip-audit finds known
  vulnerabilities, and run PNG/real-pixel threshold preflight.
- PyInstaller/QA audit tooling pinned independently of runtime dependencies.
- Tag-based public release restricted to commits already reachable from main.
- QA installer uses a disposable GitHub runner, verifies version, install,
  no unexpected Notro launch, removal. Does not install on the user's PC.
- Five localized docs/limit selector updated for official Nitro 1GB maximum,
  legacy 500MB option kept, upload target bounded conservatively.
- Old Show HN draft contains unsupported compression examples and claims:
  marked as reference-only; no AI-written HN submissions or auto-posting.
- Signing is explicitly NOT pursued (user decision).

## Recommended rollout

1. Stabilize code, retain Draft PR, require CI green; record all findings in Plane.
2. Pass unsigned installer smoke and actual user-driven draft flow.
3. Invite 5–10 consenting testers with an accurate warning (no production mass
   promotion). Record installation failures, time-to-first-paste, file output
   verification and opt-in privacy feedback without in-app telemetry.
4. Fix P0 failures; collect permission-cleared demo media.
5. Publish manually with checksum and caution; verify external download.
6. Update audited landing and only then try authentic manual marketing posts
   matching each community's rules. No guaranteed traction claims.

This readiness review is an engineering judgment, not a Discord or Microsoft
certification and not a recommendation to bypass Windows security warnings.
