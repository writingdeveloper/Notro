# Notro v2.11.0 — malformed-data recovery and first-use GUI QA

Date: 2026-10-18
Status: isolated Windows source QA and hosted unsigned EXE recovery QA PASSED. The user's live v2.10.3
app is unchanged; no user library was loaded into this QA.

## Real defects reproduced before fixes

1. A ZIP media pack manifest with a list or object as type caused an
   unhashable TypeError instead of a predictable media pack error.
2. A truncated or damaged ZIP raised raw zipfile.BadZipFile.
3. Settings JSON with a list/dict as watched-folder default_type caused
   TypeError instead of returning a safe settings error.
4. library.json/folders.json with valid JSON but malformed nested types
   could crash startup or break the in-memory collections.
5. Native pywebview Welcome exposed its WinForms window object through
   a public js_api field. JavaScript bridge inspection recursively
   traversed WinForms AccessibilityObject.Bounds.Empty indefinitely,
   preventing the actual Try Picker button from initializing.
6. The same public native window reference existed in video confirmation,
   trim and cancellation API.

All issues were reproduced with temporary data and separate Windows QA
WebView2 processes, not Discord or user media. Focused tests failed
before the fix and passed afterward.

## Code changes

- notro_app/packs.py: type validation, archive byte-size preflight and
  uniform PackError conversion for corrupt/unsupported ZIP input.
- notro_app/settings_backup.py: reject watched-folder kind values that
  aren't one of the supported strings.
- notro_app/library.py: validate stored item/folder schemas, back up
  malformed JSON byte-for-byte to local .bak, safely start empty without
  deleting cached media assets.
- notro_app/welcome.py and notro_app/video_window.py: keep WinForms Window
  objects in private js_api fields rather than publicly traversable ones.
- scripts/qa_native_file_dialogs.py: 10 actual Windows Open/Save scenarios
  (8 prior + 2 malformed import), stable error and no user data mutations.
- scripts/qa_native_welcome_flow.py: real Try Picker click opens own
  native picker with synthetic image, independent Dismiss closes only.
- scripts/qa_native_video_dialog.py: actual trim/mute/replan, Confirm and
  Close buttons work via native WebView2 bridge; no encoding/clipboard.
- tests/test_corrupt_data_recovery.py plus
  tests/test_webview_api_recursion.py: regression coverage.

## Completed Windows QA

Full local Python suite: 528 passed, Ruff clean.
Native Windows file dialogs: 10/10 stages PASS, no errors.
Native Welcome/Try Picker/Dismiss: all true, no errors.
Native video confirmation/trim/mute/close: all true, no errors.

Reproduce with:
  python -m pytest -q
  ruff check notro_app tests scripts
  python scripts/qa_native_file_dialogs.py
  python scripts/qa_native_welcome_flow.py
  python scripts/qa_native_video_dialog.py

## Verified hosted GitHub Windows QA

- Source commit aeb8590 (unreleased Draft PR).
- GitHub CI: https://github.com/writingdeveloper/Notro/actions/runs/39162457248
  PASS: 528 tests, lint, pip-audit and image preflight.
- Manual unsigned Windows QA run:
  https://github.com/writingdeveloper/Notro/actions/runs/39162481015
  PASS: real Welcome/Try Picker/dismiss and video trim/confirm/cancel stages,
  native clipboard and isolated Ctrl+V, compiled EXE/Inno installer,
  v2.10.3 -> v2.11.0 upgrade and synthetic data retention/uninstall.
- Actual installed EXE started with invalid temporary library.json and
  folders.json, preserved both source files byte-for-byte as .bak:
  invalid_library_backed_up=true, invalid_folders_backed_up=true.
  Live process, Welcome, Picker, hidden Tray and systray right-click
  verified; automatic send/capture remain OFF.
- @4080 downloaded the same-run unsigned installer for integrity validation
  but did NOT execute/install it on the user's active PC:
  NotroSetup.exe 17,225,822 bytes, SHA-256
  f6d7c15f8fd858959123dbd34a671779dcadca3edfd0b33e915eab410368716c
  matches generated manifest, ProductVersion 2.11.0, NotSigned.
- GitHub release publish step was skipped. Public latest remains v2.10.3.
- NOTRO-39 and NOTRO-40 engineering QA can be Done. Human Win10/11 GUI,
  actual Discord unsent attachment, and measured three-minute human
  first paste remain unverified separate P0 tasks.
