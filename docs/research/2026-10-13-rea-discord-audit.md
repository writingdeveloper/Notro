# REA static audit of installed Discord (2026-10-13)

REA repository: https://github.com/morluto/rea
Engine: rea-agents 6.4.0; isolated Node 24.12.0 (the @4080 system Node 22.16.0 is below the required 22.19.0).

## Scope and evidence

The existing Discord desktop app was running version 1.0.9261. We analyzed installed local resources/app.asar and modules/discord_desktop_core-1/discord_desktop_core/core.asar **read-only**, without injecting into Discord or reading account/session/message data.

- app.asar SHA-256: 535bcb3de917fa65289519e399ea82ab93d9e4df35f7b437ae8433e5ca9d39ca. REA found 24 graph nodes (Electron main and JavaScript relationships).
- core.asar SHA-256: 396088f647b3084fc3b6efedd7c5e50eb4d7b9575b817e9b689ff739a54e0c04. REA found 585 nodes, 545 JS modules, a preload bridge and Electron main, with 1,768 edges.
- Evidence is partial. Neither analysis verifies all renderer behavior, the remote APIs, Discord upload/server limits, nor live clipboard interactions.
- Raw REA output is stored outside Git under the local Windows temporary Notro/rea-investigation folder; do not publish the original Discord code.

## Conclusions for Notro

1. Electron main/preload boundaries exist. Notro must not depend on undocumented IPC or modify Discord clients. Keep the existing OS-level clipboard + explicit user paste architecture.
2. Upload policy is better established by Discord's official File Attachments FAQ (updated Aug 13, 2026): free 20 MB, Nitro Basic 50 MB, Nitro 500 MB, subject to user experiments. https://support.discord.com/hc/en-us/articles/25444343291031-File-Attachments-FAQ
3. Change trigger and compression target were conflated: Notro now leaves 19–20MB input untouched with a free 20MB cap, and uses 95% only for output.
4. Notro posts emoji as file attachments; it must not promise native Nitro privileges.
5. Follow-up live QA must test a safe unpublished draft (not private conversations or auto-send), actual PNG/JPEG/GIF/video and focus behavior.

REA command for repeat static analysis: npx --yes --package=node@24.12.0 --package=rea-agents@6.4.0 -- rea analyze-javascript-application "PATH_TO_INSTALLED_ASAR" --json

## Limitations

Static imports and Electron API edges do not prove actual runtime flow. No bypass, interception, token retrieval, client patching or reverse-engineered proprietary code is included in Notro.
