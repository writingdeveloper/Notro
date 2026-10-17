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
| Windows Python suite | 447 tests on source 167e95c | PASS local and Windows Actions CI 39057057625 |
| Dependency security | pip-audit 2.10.1 with resolved runtime/dev/build requirements | No *known* advisories at audit time; not a malware guarantee |
| Import ZIP and settings | 8 real native Win32 Save/Open stages, with Korean filenames, isolated profile | PASS |
| WebView2 | Actual Windows picker, 5 languages, synthetic 5k DOM, GIF compare, settings controls | PASS for synthetic fixtures |
| Media 20MB boundary | Valid synthetic padded PNGs at 19.5MB, 20MB, 20MB+1B, 24MB | PASS; not real-world photo quality |
| Real-pixel media | Deterministic synthetic 3000x3000 high-entropy PNG about 27MB | Produced ~7.55MB decoded WebP, source unchanged |
| Video | Locally generated 5-sec 960x540 video with sine-wave audio, real ffmpeg | Encoded 854x480 @30fps with audio; trim/mute case PASS |
| 1GB Nitro preset | User-configurable; legacy 500MB remains | Use conservative decimal billion-byte target with 95% safety |
| Prior installer | Source e26122b, SHA/VersionInfo 2.11.0 validated, unsigned | Compiled only, NOT evidence of running installed app |
| New installer smoke | Windows GitHub-hosted QA install/exe version/uninstall only | PASS on disposable runner 39057079637 (unsigned, not UI) |
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


## 2026-10-17 verified Windows Actions QA result

- Source: 167e95c (unreleased Draft PR #1).
- GitHub Actions CI run:
  https://github.com/writingdeveloper/Notro/actions/runs/39057057625
  **PASS** (dependency advisory audit, Python lint, media threshold/
  real-pixel compression preflight, 447 unit/regression tests).
- Manual unsigned installer workflow:
  https://github.com/writingdeveloper/Notro/actions/runs/39057079637
  **PASS**: Windows PyInstaller/Inno installer; separate disposable Windows
  runner installed and silently uninstalled candidate, checked EXE version,
  and prevented unwanted post-install startup. SHA-256 generated; QA artifact
  uploaded for 3 days; Publish release explicitly SKIPPED.
- @4080 downloaded the QA artifact into a disposable test location but did
  **not execute or install** it on the user's machine. Verification:
  NotroSetup.exe 17,199,976 bytes, ProductName Notro, FileVersion 2.11.0,
  SHA-256
  4f58b3ae6462d58818b9b8f0f00f85ce34b2879dc1082306c483de9b521315cc
  (matching CI checksum file), Authenticode **NotSigned** as expected.
- User explicitly opted out of signing. No certificate, issuer, tag or public
  release was created. Signed Windows reputation is not a hidden requirement
  but unsigned warning and initial install friction are still disclosure and
  human-test requirements.
- **Remaining NO-GO**: real user GUI first run, v2.10.3 upgrade, Windows 10,
  actual Discord non-sending draft Ctrl+V/focus, portfolio dependency audit +
  stale landing page, and rights-cleared authentic marketing media.


## 2026-10-17 verified public-to-candidate upgrade

Source commit 413623c, GitHub Actions CI 39058070961 **PASS** (449 tests)
and unsigned manual build 39058080501 **PASS**.

CI logs show these named checkpoints in chronological order:

- NOTRO_QA_BASELINE_VERIFIED 2.10.3
- NOTRO_QA_UPGRADING_UNSIGNED 2.11.0
- NOTRO_QA_BASELINE_TO_CANDIDATE_UPGRADE_PRESERVED_DATA
- NOTRO_QA_UPGRADE_UNINSTALL_PASSED
- NOTRO_QA_INSTALL_UNINSTALL_PASSED

The baseline public v2.10.3 installer and its released SHA-256 were downloaded
and matched on a disposable hosted Windows runner, then replaced in-place with
v2.11.0. A synthetic profile file survived upgrade and intentional uninstall;
the actual personal library was never accessed. The old installer launches
Notro even when unattended, so the QA script stops only the ephemeral
runner's Notro process. PowerShell's process-tree wait bug was fixed by
bounded waits on the installer process itself.

After the workflow succeeded, @4080 downloaded the unsigned QA artifact into
an isolated temporary folder WITHOUT executing/installing it. Evidence:
NotroSetup.exe size **17,196,309 bytes**, SHA-256
df91f3e77b7e81405511f767ef7f2f6f3a0c1f376f5c96d0b75f56680671ba73
(matched same-run checksum), Windows ProductName Notro, ProductVersion 2.11.0
and Authenticode **NotSigned**. The Publish release step was skipped as
designed and latest public is still v2.10.3.

This closes the **synthetic automated upgrade** sub-gate only. Windows 10/11
interactive GUI first-run, real installed app tray/hotkey and Discord
non-sending attachment drafts remain hard launch blockers. Exact procedure:
docs/qa/2026-10-17-manual-release-acceptance.md.


## Native WebView2 picker demo with owned art, verified 2026-10-17

- Generated 18 original geometric emoji, four original stickers and
  three original animated GIFs. Assets came only from Pillow primitives in
  scripts/record_owned_native_demo.py; no external download, Discord artwork,
  user assets or stock imagery were used.
- Recorded **nine actual WebView2-rendered UI scenes, 15.9s**, to
  docs/demo-owned-webview.gif (approximately 390KB) and native still
  docs/picker-owned-webview.png. Source window content was captured through
  CoreWebView2.CapturePreviewAsync, not by photographing the desktop.
- Scenes cover gallery/favorites, search using the real input handler,
  arrow-key JS navigation, sticker tab, animated GIF tab, settings with
  both auto-send and auto-capture OFF, and pack/settings backup controls.
- First test revealed test-only profile settings were reading the local
  Windows registry: in the initial screenshot auto-send was displayed as
  enabled. This was **a QA isolation problem, not an auto-send action**.
  Corrected the fixture to intercept registry getters/setters, required
  both safety toggles OFF before capture, and regenerated the footage.
  The user's settings were not changed. Also updated prior native WebView2
  smoke fixture to isolate registry reads/writes.
- Updated EN/KO/JA/ZH/ES README hero images/captions to the owned UI demo.
  Historical docs/demo.gif/picker.png still contain recognizable third-party
  character images and are excluded from present README promotions.
- This removes the **picker-UI owned-art sub-gate only**. Real Discord
  unpublished attachment, human Windows installer footage, large-video
  evidence, rights/metadata review for the live portfolio and external
  marketing remain NO-GO. Separate manual QA in
  docs/qa/2026-10-17-manual-release-acceptance.md is still necessary.


## Source fa3aff1: owned UI evidence and real disposable-runner clipboard QA

- Source code: fa3aff1. GitHub Windows CI run 39072813556 **PASS**,
  including 454 Python tests, Ruff, pip-audit and real-pixel media preflight.
- Manual unsigned Windows run:
  https://github.com/writingdeveloper/Notro/actions/runs/39072830662
  **PASS**. Native Win32 clipboard log includes runner_only=true,
  filesystem_unicode=true, unicode_text=true, marker=true,
  stale_guard=true, passed=true, errors=[].
  Tested actual CF_HDROP with Hangul temporary file path through
  DragQueryFileW, Unicode text, Notro marker and protection against
  overwriting a newer copy. Synthetic clipboard was cleared at end.
  No Ctrl+V/Enter or Discord client interaction took place.
- Same disposable-runner workflow again PASSED pinned PyInstaller/Inno
  build and verified public v2.10.3 -> 2.11.0 upgrade with a synthetic
  profile marker retained after upgrade and uninstall. Publish release
  step SKIPPED.
- The unsigned QA installer was downloaded for HASH/metadata validation
  into a temporary directory on @4080, not executed on the user's PC.
  NotroSetup.exe: 17,199,943 bytes; SHA256
  d8ce5174c3e5462d03cc3f524a6bf861560becaf36ef91b1e8e6f399bf0b1848,
  matching the generated manifest; ProductVersion=2.11.0 and
  Authenticode=NotSigned.
- New source-owned actual WebView2 UI animation is in five-language
  READMEs; auto-send and capture are explicitly OFF in the test fixture
  rather than inheriting registry settings. No third-party character
  media, user clipboard, chats or desktop windows are captured.
- Plane NOTRO-27 owned native UI demo and NOTRO-28 hosted Win32 clipboard
  QA are Done; NOTRO-25 full marketing evidence remains In Progress and
  NOTRO-5 real Discord unsent draft remains In Progress.
- No signing, main merge, production release/tag or public marketing post.
  Published latest GitHub release remains v2.10.3.

Critical NO-GO gates remain: actual user-approved non-sending Discord
attachment preview/focus and clipboard behavior, Windows 10/11 human GUI
first run/offline conditions, portfolio dependency-audited live landing,
and approved authentic screenshot/video attachment evidence.


## 2026-10-17 next pass: original-target paste safety and parallel growth research

- Previous PickerController.select wrote CF_HDROP before establishing that
  the original target could regain focus, risking replacing the clipboard
  even though there was nowhere safe to paste. The new code checks the target
  before clipboard mutation, compares clipboard sequence numbers (also for
  URL/text copies) to preserve newer user data, rechecks focus after commit,
  and only counts a Win32 Ctrl+V operation when SendInput accepted all keys.
  Accepting the key sequence is NOT proof of target application acceptance.
- Unit tests now cover focus failure before/after copy, newer-copy race,
  failed SendInput and bad media preparation, without touching a real user
  clipboard; five localized explanations distinguish outcomes.
- New manual GitHub-hosted Windows test scripts/qa_runner_owned_target_paste.py
  is guarded to refuse execution outside disposable runner. It exercises
  owned Tk Win32 target window -> PickerController.select -> real CF_HDROP
  -> SendInput Ctrl+V -> owned entry binding, invalid-target copy
  preservation and newer-copy race. It explicitly blocks Enter/auto-send
  and never opens Discord. Record actual remote status before marking Done.
- In parallel, segmentation, competitor alternatives, distribution ethics,
  three controlled beta tasks, 5-10 volunteer cohort thresholds and
  aggregate privacy-safe measurement are documented in
  docs/marketing/2026-10-17-research-validation-first-growth.md and
  docs/marketing/2026-10-17-beta-user-scorecard.md.
- 2026-10-17 GitHub metrics baseline: 0 stars, 0 forks, 35 public v2.10.3
  installer asset downloads (not unique users), trailing 14-day GitHub repo
  views 13 / unique visitors 8. These are NOT installed/active users.
  writingdeveloper.blog/projects/notro still has stale 10MB/v2.0 claims,
  portfolio Draft PR #36 still fails GitHub npm audit.
- Neither marketing research nor new QA triggers a release, a community post,
  a Discord message or a code-signing flow.


## 2026-10-17 source 77689d6: owned-target REAL Win32 paste QA PASS

- The first manual workflow attempt failed because the test harness depended
  on pywin32/win32gui not installed in plain GitHub-hosted Python. Replaced
  the unnecessary QA dependency with Windows native ctypes.FindWindowW;
  no runtime dependency or actual Discord client was changed.
- [GitHub Windows CI 39075255709](https://github.com/writingdeveloper/Notro/actions/runs/39075255709)
  PASSED: 465 tests, Ruff, pip-audit and real 20MB media preflight.
- [Manual QA workflow 39075263021](https://github.com/writingdeveloper/Notro/actions/runs/39075263021)
  PASSED, including real original-target Win32 focus and SendInput:
  NOTRO_OWN_WINDOW_PASTE_QA reports runner_only=true, owned_window=true,
  foreground_file_ctrl_v=true, lost_target_preserved=true,
  newer_copy_preserved=true, auto_send_called=false, errors=[],
  passed=true. Native CF_HDROP/Unicode clipboard marker/stale guard
  QA also passed. The event was delivered to a separately owned Tk window,
  **not Discord**; no message was sent or user clipboard examined.
- Same disposable runner successfully built the candidate unsigned EXE/
  Inno installer, verified a released v2.10.3 -> candidate 2.11.0
  upgrade, retained a synthetic user profile file and removed the app.
  Publish release skipped by design.
- @4080 downloaded the QA installer into a private TEMP directory
  but did not execute/install on the user's PC. It is 17,199,014 bytes
  with verified same-run SHA256:
  2529718fe90e54b28a8fc96ca03915ebc050bc033f5d9238f055e5580c8e888c.
  ProductVersion=2.11.0, Authenticode=NotSigned. Public latest still v2.10.3.
- This closes Plane's *owned-window Windows paste integration* task;
  user-approved real Discord unsent-draft attachment and human Windows10/11
  GUI, audited live landing and separate genuine full workflow marketing
  evidence remain hard public release and outreach blockers.


## Hosted Windows installed EXE first-run QA added (status pending actual run)

New script scripts/qa_runner_installed_first_run.py is gated by GITHUB_ACTIONS
and RUNNER_TEMP, invoked only after candidate Notro.exe has been installed
on the disposable Windows runner. It starts the REAL candidate executable
with isolated temporary APPDATA; runner-only registry disables update checks,
hotkey, auto-send and auto-capture. The test observes only windows belonging
to the spawned PID and requires native picker window creation, visible first
run welcome, unchanged startup registration, a live process and isolated
data folder. It terminates only that spawned process tree before uninstall.

Do not mark GUI installed-executable proof until a GitHub manual QA run
passes. This is NOT interactive human Windows10/11 use or real Discord
attachment acceptance. No signing, customer contact or release is involved.
