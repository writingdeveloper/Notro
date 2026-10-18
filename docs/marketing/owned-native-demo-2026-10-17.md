# Owned visual demo: native Windows WebView2 (2026-10-17)

**Evidence type: actual Notro picker UI rendered by the pywebview Windows
Edge WebView2 backend in an isolated temporary test profile.**
This is not a screenshot of Discord, not an uploaded attachment, not a
demo of the packaged/installed EXE and not a test of clipboard or account
integration. No actual Notro user library, personal folders or Discord data
are read or captured.

## Reproducible assets

- Animation: docs/demo-owned-webview.gif — 9 UI scenes, 15.9 seconds,
  about 390 KB, 850x607 pixel output at the capture monitor's DPI.
- Still: docs/picker-owned-webview.png — picker gallery screenshot.
- Source: scripts/record_owned_native_demo.py
- Artwork: 18 emoji, 4 stickers and 3 animated GIFs created by the script
  with Pillow geometric primitives (suns, moons, comets, hearts, rings).
  No third-party anime characters, stock art, Discord or other proprietary
  media are imported. They are newly produced by this project's code.
- Privacy: uses CoreWebView2.CapturePreviewAsync **on our own WebView2
  control**, not desktop screenshots, screen capture or another process's UI.
- Settings: in the test subprocess all application setting reads/writes are
  isolated, never accessing Windows HKCU Notro preferences. It asserts that
  auto-send and auto-capture checkboxes are unchecked.
- Isolation: uses a temporary media library and localhost asset server.
  The window is closed, the server stopped and temporary originals removed
  after GIF/PNG creation. No global clipboard or keyboard SendInput.

## Captured scenes

1. Emoji gallery with Favorites/Recent items
2. Text input search for sun through the real JS event handler
3. Keyboard arrow-navigation through the real picker JS handler
4. Sticker tab, original icons only
5. GIF tab, original generated animations
6. Same GIFs with a later animation frame
7. Settings (auto-send and auto-capture visibly disabled)
8. Pack / JSON preferences backup controls, directory paths excluded
9. Return to gallery

Regenerate on an authorized Windows QA PC with Python, Pillow, pywebview,
Microsoft WebView2 installed:

    python scripts/record_owned_native_demo.py

The default output directory is docs, override with --output-dir.

## Public and historic media distinction

All five current README files now link ONLY the owned native WebView2 demo.
The older docs/demo.gif and docs/picker.png still contain recognizable
third-party characters. They are retained for historical development
review and must not be used in public marketing without redistribution
rights confirmed by the maintainer. They are not automatically
made distributable by being in this project.

The new demo can accurately illustrate picker UI, search, keyboard handler,
tabs and backup controls. It does not prove real Discord attachment delivery,
installed app launch, actual subscription limits or audio/video compression
in the Discord chat interface. Those require separate user-approved
unpublished-draft demonstrations and real Windows install evidence.

This is independent of Discord and makes no policy compliance or
endorsement claim. Creating these files is not authorization to post
on HN/Reddit/Discord or to publish a new public Notro release.
