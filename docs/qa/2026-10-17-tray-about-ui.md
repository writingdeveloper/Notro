# Notro v2.11.0 — native tray menu and About QA (2026-10-17)

## Purpose and release state

The user requested an About view showing program version, GitHub, releases,
MIT license and environment; and a Discord-inspired dark menu when
right-clicking Notro's Windows notification-area icon.

This is an independent Notro WebView2 popup, NOT a modification of the Discord
client. v2.11.0 remains an unmerged Draft PR; v2.10.3 remains latest publicly
available. No code signing, public release, marketing post or user data changes.

## Implementation

- notro_app/tray_panel.py: About payload uses notro_app.__version__ and
  fixed source, release, issue and MIT-license URLs. Private ctypes Win32
  functions position only the owned popup on the active monitor. Fallback
  is a native About dialog when WebView2 is absent.
- notro_app/picker/ui/tray_panel.{html,css,js}: independent Notro logo,
  Discord-inspired #17191f dark background, #5865f2 accent, current
  version, live status, picker shortcut, monitoring toggle, library,
  upload limit, language, keyboard shortcut, startup, updates, About
  navigation and links. No remote assets or third-party data.
- notro_app/tray.py: intercepts WM_RBUTTONUP for Notro's OWN pystray
  notification-area icon when a working WebView2 bridge exists; otherwise
  the classic native Windows context menu still appears, including About.
  Shares existing menu handlers and validates action names and values.
- notro_app/app.py: constructs and later destroys the new hidden panel
  alongside the existing picker. The no-WebView2 branch keeps the
  original native notification-area UI.
- notro_app/i18n.py: full copy in English, Korean, Japanese,
  Simplified Chinese and Spanish.
- The packaged UI is included by existing PyInstaller add-data settings;
  the About version and links come from local code, not network requests.

## Native screen captures

- tray-menu-native-preview.png: actual Windows pywebview/Edge WebView2
  home panel, captured with the own CoreWebView2.CapturePreviewAsync API.
- tray-about-native-preview.png: actual About panel, including
  visible version, Windows/WebView2/MIT, unsigned/independent disclosure
  and GitHub repository link near the top.

These are isolated QA-process screenshots with synthetic state, NOT an
installed user app screenshot or Discord chat evidence. The capture
method does not record the desktop or any other process.

## QA commands and verified scope

On an authorized Windows test PC:

    python scripts/qa_native_tray_panel.py --output-dir docs/qa

The native QA fixture creates its own unregistered test icon, simulates its
WM_RBUTTONUP handler, checks fallback before bridge readiness, opens a real
native WebView2 popup, navigates to About, verifies v2.11.0/GitHub/unsigned
information, changes a test-only upload setting, handles Escape navigation
and closing, and invokes the picker quick action through a fake controller.
The fixture never reads or changes actual user registry/clipboard/Discord.

Additional source and UI regression suites:
- tests/test_tray_panel_metadata.py
- tests/test_tray_panel_actions.py
- tests/test_tray_panel_ui_contract.py
- tests/test_i18n.py

## Real bug found and fixed

The draft used pywebview.Window.move(x, y) after window.show().
On the installed WinForms/pywebview backend, that path passed None for
unused Win32 SetWindowPos size parameters and raised an ArgumentError.
The popup now moves via its own private WinDLL user32 function table, using
the exact owned Notro popup HWND. No global API prototypes are overwritten.
A fresh native QA run confirms normal open, About, settings and close.

## Still not proven by this QA

- The actual packaged EXE creation of its hidden popup must pass on a
  disposable Windows GitHub Actions runner before marking packaging done.
- Human Windows 10/11 right-click experience, SmartScreen warning, DPI,
  multiple monitors and keyboard accessibility need human acceptance.
- A Discord-approved non-sending draft attachment still needs separate
  user-authorized testing (Plane NOTRO-5).
- The portfolio landing security audit, version-matched public download
  and human release authorization remain P0.
- The user opted out of signing. Do not apply for certificates or bypass
  Windows protections.


## Successful Windows CI and packaged EXE check

- GitHub CI source commit 461db39:
  https://github.com/writingdeveloper/Notro/actions/runs/39085969840
  PASSED, 485 unit/regression tests, Ruff and dependency audit.
- Manual unsigned candidate workflow:
  https://github.com/writingdeveloper/Notro/actions/runs/39085985603
  PASSED, actual public v2.10.3 -> candidate 2.11.0 upgrade, synthetic
  APPDATA preserved, real installed EXE launched. Its own process window
  enumeration includes a **hidden Notro Tray Menu** window alongside
  the hidden Notro Picker and the visible first-run Notro welcome.
  Auto-send and capture OFF, Windows startup unchanged. Uninstaller
  succeeded, public release publishing SKIPPED.
- Same-run unsigned NotroSetup.exe was downloaded for checksum inspection
  without executing on the user's active PC. Size 17,215,650 bytes; SHA256
  62593f9b66f5ae6e568ef14b6b674c68934a69523e2f860d70503b8c85c23169,
  matching official QA run manifest; file ProductVersion 2.11.0, publisher
  signature NotSigned (expected by user decision). Candidate still Draft PR.
- Plane NOTRO-34 About and NOTRO-35 styled tray are Done for source/native
  QA and packaged hidden-window smoke; a person's actual Windows 10/11
  right-click accessibility/DPI/SmartScreen review is separate NOTRO-24.
  Real Discord unsent-file attachment is separate NOTRO-5.
