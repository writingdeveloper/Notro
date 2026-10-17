# Code signing policy

> **Current policy (2026-10-14): no code signing planned.** The maintainer
> explicitly chose unsigned distribution. Windows SmartScreen may warn about
> an unknown publisher. See SECURITY.md for integrity checks and how to
> inspect/build from source. A SHA-256 file does not prove publisher identity.
> The historical SignPath investigation below is archived context, not an
> application or an instruction to pursue signing.

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
| Release approver — reviews unsigned binary and SHA-256 before publication | [@writingdeveloper](https://github.com/writingdeveloper) |

Enable multi-factor authentication on the GitHub maintainer account.

## Historical signing research (not in scope)

Signing is deliberately deferred. Do not initiate SignPath/Azure accounts,
request certificates or alter branch restrictions solely for code signing.
Independent CI/security QA and release authorization still matter.
The archived research note is at
docs/research/2026-10-13-notro-code-signing-readiness.md.


## How releases are built

Releases are built only by GitHub Actions from a tagged commit on `main`
([`.github/workflows/release.yml`](.github/workflows/release.yml)) — never from a
maintainer's local machine. The workflow builds `Notro.exe` with PyInstaller,
compiles the Inno Setup installer, and publishes `NotroSetup.exe` together with
`NotroSetup.exe.sha256`, so any release can be checked against the hash published
beside it. Anyone can reproduce a build from source with
`pip install -r requirements.txt` and `build.bat`.

## Binary metadata

Every unsigned release artifact still carries consistent product and version metadata:

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
