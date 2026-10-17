## Problem and user impact

Explain what is broken or missing, including a concrete scenario.

## Implementation

Describe the changed files, API/UI behavior and whether this changes
clipboard/Windows settings, network calls, user data or installed artifacts.

## Evidence (do not invent results)

- [ ] Python tests and Ruff passed on Windows
- [ ] Python dependency audit completed
- [ ] Media threshold preflight passed (if relevant)
- [ ] Native WebView2 test passed (if UI changed)
- [ ] Real Windows file dialogs tested (if dialog changed)
- [ ] Privacy, keyboard and accessibility reviewed
- [ ] All five languages and README instructions updated, or N/A
- [ ] Public Discord integration tested in a non-sending draft, or
      **clearly marked NOT TESTED**
- [ ] Installer runtime/upgrade/uninstall checked, or clearly marked NOT TESTED
- [ ] No Discord client code modified, injected or bundled; no REA runtime use
- [ ] No sensitive user files, tokens or private media in commits/screenshots

## Release impact and known gaps

State what users can actually download now versus unreleased code.
Do not use CI success as a proxy for successful installation, Discord
account-policy compliance or permission to reuse marketing media.

**Release/public marketing is a separate maintainer action.**
Installers are unsigned by project decision; do not start signing workflows.
