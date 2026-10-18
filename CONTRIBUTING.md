# Contributing to Notro

Notro is a small, community-maintained **Windows-only clipboard utility**. It
is **not affiliated with or endorsed by Discord**, and its emoji are image
attachments rather than native Nitro emoji.

## Start here

Read [README.md](README.md), [SECURITY.md](SECURITY.md),
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and
[CHANGELOG.md](CHANGELOG.md) before changing Windows hooks or distribution.

The repo has no GITHUB.md or AGENTS.md instruction file. This document and
the source/tests are the current contributor entry points.

## Working on a change

- Use a feature branch or Git worktree. Do not overwrite someone else's
  uncommitted changes or modify their running Discord installation.
- **Never bundle, embed, launch or inject REA into Notro.** REA may be used
  by developers for independent compatibility research where lawful; Notro
  itself must use public Windows APIs and user-directed clipboard/paste.
  Do not ship proprietary Discord code or captured account content.
- Never access authentication tokens, private messages, user library
  directories, or the global clipboard in automated tests without explicit
  isolation/consent.
- Add a focused regression test before marking a behavioral bug complete.
- Keep English, Korean, Japanese, Chinese, and Spanish UI strings aligned;
  update corresponding README files when the public behavior changes.
- Treat auto-send, auto-capture, startup, backup/import, downloader and
  updater behaviors as high-risk. Keep unsafe operations opt-in and never
  silently turn them on while importing settings.

## Reproduce the engineering checks

Run from a supported Windows 10/11 development environment with Python 3.12+
and Microsoft Edge WebView2:

1. Install project dependencies: pip install -r requirements-build.txt
2. Check Python style: ruff check notro_app tests scripts
3. Run unit tests: python -m pytest -q
4. Test real-byte synthetic threshold behavior:
   python scripts/qa_release_media_preflight.py
5. When a change touches the picker, run the isolated, non-Discord
   Windows WebView2 UI harness: python scripts/qa_native_webview.py
6. If file dialogs changed, run the separate synthetic native dialog harness:
   python scripts/qa_native_file_dialogs.py
7. When Welcome, video dialog, ZIP or settings import changes, run
   isolated native Windows WebView2 UI tests:
   python scripts/qa_native_welcome_flow.py
   python scripts/qa_native_video_dialog.py
   python scripts/qa_native_file_dialogs.py
   The last test opens 10 real Windows file dialogs (including malformed
   ZIP and JSON), never using real Notro settings or Discord data.
8. Run dependency audit: python -m pip_audit -r requirements-build.txt --strict

The browser/WebView2 harness uses synthetic inputs and must not be
described as proof of live Discord integration. Actual user-driven
attachment draft tests, installer runtime, Windows DPI, accessibility
and updated OS versions require separate test evidence.

## Reporting bugs and security issues

Use [the bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
**Never attach Discord tokens, private chat screenshots, private media,
unredacted logs, or personal local file paths** to a public report.
For vulnerabilities, use [private security reporting](SECURITY.md).

## Proposed pull requests

Submit a short purpose statement, implementation overview, Windows
test evidence, privacy/network/storage effects, localized UI changes
and remaining unsolved cases. Use the PR template to separate actual
test results from simulations.

Do **not** merge, tag, publish a release, auto-update user installations,
post public promotions, or sign installers merely because CI is green.
A human maintainer must approve each release. The project is explicitly
not pursuing code signing; any published unsigned installer must be
prominently labeled and treated as a trust limitation.
