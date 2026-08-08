# Code signing policy

> **Status: not signed yet.** Releases of Notro are currently unsigned, so Windows
> SmartScreen warns that the publisher is unknown. See
> [SECURITY.md](SECURITY.md#code-signing) for how to verify a download in the
> meantime. This document states the policy that governs signing, and is a
> prerequisite for applying to the [SignPath Foundation](https://signpath.org/)
> free certificate programme for open source projects.

## Project

- **Name:** Notro
- **Repository:** <https://github.com/writingdeveloper/Notro> — the code signing
  team owns this repository and is the same team that develops the software.
- **License:** [MIT](LICENSE), no commercial dual-licensing.
- **Proprietary components:** none. Bundled third-party components and their
  licenses are listed in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
  ffmpeg is **not** distributed; it is fetched to the user's machine on demand
  with their consent.

## Roles

Notro is maintained by one person, who therefore holds all three roles:

| Role | Who |
|---|---|
| Author — writes and modifies code | [@writingdeveloper](https://github.com/writingdeveloper) |
| Reviewer — approves changes before they reach `main` | [@writingdeveloper](https://github.com/writingdeveloper) |
| Approver — authorises a release to be signed | [@writingdeveloper](https://github.com/writingdeveloper) |

Multi-factor authentication is required on the GitHub account and on the signing
service account.

## How releases are built

Releases are built only by GitHub Actions from a tagged commit on `main`
([`.github/workflows/release.yml`](.github/workflows/release.yml)) — never from a
maintainer's local machine. The workflow builds `Notro.exe` with PyInstaller,
compiles the Inno Setup installer, and publishes `NotroSetup.exe` together with
`NotroSetup.exe.sha256`, so any release can be checked against the hash published
beside it. Anyone can reproduce a build from source with
`pip install -r requirements.txt` and `build.bat`.

## Binary metadata

Every signed artifact carries consistent product and version metadata:

- `Notro.exe` — `ProductName: Notro`, `ProductVersion`/`FileVersion` generated from
  `notro_app.__version__` by [`build_version_file.py`](build_version_file.py).
- `NotroSetup.exe` — `VersionInfoProductName: Notro`, `VersionInfoVersion` set from
  `notro_app.__version__` by the release workflow and passed to
  [`installer.iss`](installer.iss).

Versions follow [Semantic Versioning](https://semver.org/) and every release is
documented in [CHANGELOG.md](CHANGELOG.md).

## Privacy

Notro transmits no clipboard or other user content. It has no telemetry, analytics,
crash reporting, or accounts. It performs update checks by default (they can be
disabled from the tray menu). The network services used by Notro and its installer,
and what triggers each, are documented in [SECURITY.md](SECURITY.md#network-access)
and summarised in the README. This includes the installer's conditional Microsoft
WebView2 download when the runtime is missing.

## Scope

Notro does not identify or exploit security vulnerabilities and does not
circumvent any security measure. It prepares the Windows clipboard and simulates a
local <kbd>Ctrl</kbd>+<kbd>V</kbd> — the same class of input automation as the
built-in Windows emoji panel. It does not modify, patch, or inject into the Discord
client, and never accesses an account or token.

<!--
Once a certificate is granted, add here:

## Attribution

Free code signing is provided by [SignPath.io](https://signpath.io/), certificate
by [SignPath Foundation](https://signpath.org/).
-->
