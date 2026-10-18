# Notro v2.11.0 — manual Windows release acceptance

Status: NOT EXECUTED YET. This is the exact human QA that remains after
the passing synthetic tests and disposable Windows GitHub runner upgrade.
The user decided NOT to sign code. Never misrepresent an unsigned installer
as having trusted publisher verification.

## Test environment and privacy

Record Windows 10/11 build, GPU/display DPI, Windows language, Discord
desktop version, Notro version and whether WebView2 Runtime is installed.
Use a spare Windows user profile or VM where practical, not the main
development profile with personal working media.

Before an install/upgrade, make a private local backup of any existing
Notro data and settings; do not attach it to public issues. Do not upload
real chat screenshots, private messages, account tokens, clipboard history,
photos of people or contact information to QA reports.

Use an approved, deliberately **unsent** private Discord draft, or simply
a separate harmless file-editing application for initial clipboard tests.
Do not send a Discord message automatically or click Send for this test.
Keep optional auto-send switched OFF throughout the release acceptance.

The only candidate artifact for this checklist is from the named, reviewed
GitHub Actions run; download it afresh and verify its released SHA-256
against the manifest. If Windows warns of an unknown publisher or blocks
the unsigned binary, **record the result and stop**. Do not disable
SmartScreen/Defender just to make the test green.

## Checklist (mark only after observing the real behavior)

### A. Installer, lifecycle, ownership

- [ ] A1: Obtain explicit QA permission to run the unsigned candidate.
      Verify SHA256, ProductName Notro and 2.11.0 file version.
- [ ] A2: Start installer normally on Windows 11. Screenshot the actual
      warning/setup experience without private desktop data.
- [ ] A3: Start installer normally on Windows 10, with WebView2 present.
      Record no-network/WebView2-missing fallback separately.
- [ ] A4: With Notro running from a fresh profile, find the tray icon,
      open its menu, check Pause/Resume, selected upload preset, and language.
- [ ] A5: From an existing v2.10.3 installation, upgrade to 2.11.0.
      Verify preserved personal library, categories/favorites and settings.
      Note the disposable hosted-runner synthetic upgrade already PASSED.
- [ ] A6: Uninstall and check executable removal but intentionally retained
      local library/preferences; ensure no orphan tray/ffmpeg processes.
- [ ] A7: Confirm Windows startup is opt-in and stays disabled until selected.
      Do not change the user's real startup tasks without permission.

### B. Picker/clipboard behavior (no public Discord messages)

- [ ] B1: Use the hotkey to show the native picker and close with Escape.
      Keyboard search, arrow keys, Enter selection and focus restore work.
- [ ] B2: Switch to a dedicated empty *unsent* Discord draft without
      exposing existing chats to QA. Use a rights-cleared PNG, JPG and GIF.
      Confirm the attachment preview appears after user-directed paste.
      **Do not press Send.**
- [ ] B3: Test 19.5MB, exactly 20MB, 20MB+1 byte and 24MB files.
      Actual Discord subscription/experiment limits may differ.
      Inspect pasted filename/size, the pre-attach UI and original integrity.
- [ ] B4: Switch target window during the picker closing/focus restore.
      Notro must never send Enter to the wrong window; auto-send stays OFF.
- [ ] B5: Verify GIF comparison and manual approval/cancel. The library
      original stays unchanged and preview temp file is cleaned.
- [ ] B6: Check disabled/hotkey conflict, clipboard-busy application,
      missing watched folder, and a 5,000-item mixed media library.
      Collect private performance/RAM evidence with consent.

### C. Backup, media, updater, localization

- [ ] C1: Save and import rights-cleared emoji/sticker/GIF ZIP media pack;
      corruption and duplicates behave as described.
- [ ] C2: Save JSON settings backup with paths unchecked, review counts,
      cancel once, then explicitly apply to an isolated profile; confirm
      auto-send and auto-capture remain disabled and startup untouched.
- [ ] C3: Confirm non-ASCII filename and Windows profile path behavior.
- [ ] C4: Validate English, Korean, Japanese, Simplified Chinese and Spanish
      text; note any clipped buttons at small window size, 125/150/200% DPI.
- [ ] C5: With update check explicitly enabled, confirm update notices
      don't silently install, downgrade or transmit private user data.
- [ ] C6: Confirm user-readable unsigned/SHA disclosure and an accurate
      privacy/debug logging procedure, with log path redaction.

## Beta exit thresholds

To invite 5–10 opt-in early testers, require successful clean install/
uninstall on at least one machine, a working unsent Discord attachment
preview and no unexpected clipboard loss or background message sending.
For unrestricted v2.11.0 announcement, require **all mandatory P0
items A/B and the documented critical C items**, an audited live landing
page and owned/rights-cleared demos. Record each failing step as a Plane
NOTRO issue linked to the observed environment and reproduction.

No human step may be marked PASS based only on synthetic WebView2, unit
tests, CI building an installer, or a GitHub-hosted Windows service session.
No release tag, merger, public download or marketing post is authorized
by this checklist alone.
