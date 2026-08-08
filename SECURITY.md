# Security policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub's private vulnerability reporting](https://github.com/writingdeveloper/Notro/security/advisories/new)
rather than opening a public issue. Include the Notro version, your Windows
version, and steps to reproduce. Expect a first response within a few days; this
is a hobby project maintained by one person.

## What Notro does on your machine

Notro is a clipboard utility, so it is fair to ask exactly what it touches.

**It reads your clipboard continuously.** A background thread polls the clipboard
sequence number every 0.4 s and reads the contents only when they change. It handles
oversized images and copied video files. Images larger than the upload limit are
re-encoded to a file in `%TEMP%\Notro`, and the clipboard is replaced with that file.
For a copied video file, Notro may inspect its path, extension, and size; an oversized
video proceeds through the confirmation UI before processing. Other clipboard content
is ignored and never stored.

**It does not store clipboard contents unless you ask it to.** "Automatically save
new clipboard images" in picker settings is **off by default**. With it off, the
only images written to your library are the ones you register explicitly.

**It simulates <kbd>Ctrl</kbd>+<kbd>V</kbd>** (and <kbd>Enter</kbd>, if you turn on
auto-send) using the Windows `SendInput` API — the same mechanism as the built-in
Windows emoji panel. It does not read your keystrokes.

**It never touches the Discord client, your account, or your token.** There is no
self-bot behaviour, no injection, and no patching of any application.

## Network access

Notro contacts only the services documented below:

| Endpoint | When | Why |
|---|---|---|
| `api.github.com/repos/writingdeveloper/Notro/releases/latest` | Every 24 h (can be disabled in the tray menu) | Check for updates |
| `github.com/.../releases/download/...` | When an update is found | Download the installer, **verified against its published SHA-256 before running** |
| `cdn.discordapp.com`, `media.discordapp.net` | Only when you register an emoji or sticker by link | Download that image from Discord |
| `pypi.org/pypi/imageio-ffmpeg/json` + the wheel URL | Only the first time you compress a video, after you confirm | Obtain ffmpeg, **verified against the SHA-256 published by PyPI** |
| `go.microsoft.com/fwlink/p/?LinkId=2124703` | During installation only, if Microsoft Edge WebView2 is missing | Download Microsoft's Evergreen bootstrapper over HTTPS. The bootstrapper runs as a Microsoft-signed installer; it is not verified against a Notro-published SHA-256. |

**There is no telemetry, analytics, crash reporting, or account of any kind.** No
clipboard content, file name, or usage data is ever transmitted.

A local HTTP server binds to `127.0.0.1` on a random port while the picker is
running, so the WebView2 control can display your library images. It serves only
files already in your own library and is not reachable from outside your machine.

## Where your data lives

| Path | Contents |
|---|---|
| `%APPDATA%\Notro` | Your emoji/sticker library, `library.json`, and downloaded ffmpeg |
| `%TEMP%\Notro` | Compressed output and resized paste copies, auto-deleted after one day |
| `HKCU\Software\Notro` | Settings (hotkey, language, upload limit, paste sizes) |

Uninstalling removes the program but **deliberately keeps `%APPDATA%\Notro` and
the registry settings**, so reinstalling does not lose your library. Delete them
manually if you want them gone.

## Code signing

Releases are currently **unsigned**, so Windows SmartScreen may warn and some
antivirus products may flag the installer as a false positive. The policy that
governs how releases are built and signed is in
[CODE_SIGNING.md](CODE_SIGNING.md). Verify what you downloaded against the
`NotroSetup.exe.sha256` published with each release:

```powershell
(Get-FileHash NotroSetup.exe -Algorithm SHA256).Hash
```

Reproducing a build from source is also possible: `pip install -r requirements.txt`
then `build.bat`.
