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
auto-send) using the Windows `SendInput` API. Paste can work in other apps,
but optional automatic `Enter` is restricted to the same still-focused Discord
desktop window. Notro checks the executable's name with public Win32 APIs,
without reading the Discord process. It cannot detect switching channels
inside the same Discord window; auto-send is therefore off by default.
It does not read your keystrokes.

**It does not modify or inject into Discord, require a Discord account
token or perform private client IPC.** Notro is an independent Windows OS-level
utility, not affiliated with or endorsed by Discord. Its behavior cannot be
guaranteed compliant with every current or future Discord policy; read the
published architecture and keep user-directed sending manual.

## Original-window focus and newer-copy protection

Before changing clipboard content for a picker paste, Notro checks that the
original target window still exists and is focused. Windows clipboard
sequence-number checks protect newer text or file copies made while image
preparation runs; if a newer copy is found, the paste is canceled without
overwriting it. Windows SendInput return values are checked so rejected
Ctrl+V injection cannot be reported as a successful paste. A successful
SendInput return is **not proof** that Discord or another application
accepted the attachment. Switching channels inside the same Discord
window is not detectable. Auto-send is OFF by default.

These checks use only public Win32 APIs, not Discord client hooks or REA.
They reduce accidental copy loss but cannot guarantee uninterrupted focus
against all external OS/clipboard interleavings.

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

A local HTTP server binds to `127.0.0.1` on a random port while the
picker is running, to serve only media already in your library to the
embedded WebView2 picker. Each start creates an unpredictable URL capability;
requests must also use the exact loopback Host header to reduce exposure to
unrelated local web pages and DNS-rebinding aliases. Raw paths are not
included in asset URLs. This does not provide a sandbox against other local
software that already has direct access to your files.

## Local preferences backup privacy

An explicit settings export creates a small local JSON file with allowlisted
preferences only; no media, private Captures, clipboard contents, tokens or
Discord source links. Watched absolute paths are excluded by default and
included only with consent. Import is verified and separately confirmed;
auto-send and auto-capture are forced OFF, and startup settings unchanged.
The image ZIP media pack is a separate workflow.

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
