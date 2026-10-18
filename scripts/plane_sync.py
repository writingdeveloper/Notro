#!/usr/bin/env python3
"""Idempotent Notro Plane backlog sync (never prints tokens).

Dry-run by default. --apply creates new issues and refreshes descriptions.
Existing Plane status, priority, owners and names remain authoritative;
never silently downgrade another session's QA or Done state.
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
from urllib.parse import quote

PROJECT_NAME = "Notro"
PROJECT_ID = "NOTRO"
WORKSPACE_DEFAULT = "soursea"

# Name, state, priority, outcome/acceptance criteria.
# Implementation-finished work remains in QA until actual Windows interaction testing.
ISSUES = [
    ("Malformed ZIP/settings/library startup fail-closed recovery", "Done", "urgent",
     '2026-10-18 source aeb8590 GitHub CI 39162457248 PASS (528 tests, lint, pip audit); manual unsigned Windows 39162481015 PASS. Invalid ZIP type and corrupt file safely rejected; malformed JSON settings error without mutation; local invalid library/folders backed up byte-for-byte to .bak. Actual Korean Win32 10 Save/Open QA PASS with malformed ZIP+JSON. REAL INSTALLED v2.11.0 EXE on disposable hosted Windows launched with corrupt library/folders; both invalid_library_backed_up and invalid_folders_backed_up true, welcome/picker/tray and returning user right-click PASS, safe defaults, no account/clipboard. Public v2.10.3 to candidate 2.11.0 upgrade, synthetic user data preserved/uninstall PASS. QA artifact independently SHA-verified 17,225,822 bytes f6d7c15f8fd858959123dbd34a671779dcadca3edfd0b33e915eab410368716c, unsigned. Human Windows 10/11 and Discord draft still separate. No public release/signing.'),
    ("Native Welcome and video dialog JS bridge recursion regression", "Done", "urgent",
     '2026-10-18 source aeb8590 real @4080 native Welcome/video QA found recursive WinForms AccessibilityObject introspection caused by public JS API window reference, fixed by private native window reference in both dialog APIs. Native Welcome Try Picker / dismiss and video trim/mute/replan/Confirm/finish/Close PASS, no external clipboard or encoding. Manual disposable Windows GitHub runner 39162481015 native Welcome and video QA stages PASS; source CI 39162457248 PASS 528 tests/security audit. Real installed EXE also starts, private profile corrupt library backup PASS. Actual human first 3-minute Discord unsent draft remains NOTRO-7/5 QA. No signing/tag/main/public release.'),
    ("Actual installed EXE own-tray WM_NOTIFY right-click open/close QA", "Done", "urgent",
     "2026-10-17 source c7248b3 GitHub Windows CI 39093635986 PASS (494 tests) and manually dispatched unsigned Windows runner 39093633727 PASS. Actual published v2.10.3 baseline checksum verified -> v2.11.0 upgrade; a first start showed welcome & hidden picker/tray; returning-user restart with same disposable synthetic profile showed no welcome; WM_NOTIFY(0x040B)/WM_RBUTTONUP(0x0205) delivered to own pystray Notro*SystemTrayIcon HWND and Notro Tray Menu opened then closed, real_tray_notification_open/close=true, process_alive/safe flags/data retention PASS, errors=[]; uninstall PASS. Popup now rejects unrelated same-title HWND by PID, tests/QA source included in exact packaged build. @4080 independently checked 17,222,275-byte unsigned NotroSetup.exe SHA256 c122cf31b40607faa7b5e9ff2f6075cfbc72f47ff0634cbe990cdc519240e360 matching run manifest, v2.11.0, Authenticode NotSigned; not executed on user's PC. No production release/signing or Discord/clipboard. Human physical Windows10/11 mouse, mixed DPI and Discord unsent draft remain NOTRO-24/5."),
    ("Tray popup DPI / compact work-area and localized fallback regression", "Done", "high",
     "2026-10-17 verified genuine @4080 Windows pywebview at effective 200 percent DPI: previous native SetWindowPos treated logical 362x532 as physical and clipped the popup to 310x320 after compact min-size reduction. Fixed via private user32.GetDpiForWindow scale -> physical 724x1064 before monitor work-area clamping; tiny work-area fallback uses classic menu. Native CoreWebView2 QA PASS with exact window 724x1064/362x532 CSS, five language About, keyboard GitHub focus, zoom 100/125/150 percent, compact 330x420 scrolling/link horizontal visibility, Escape and quick actions. Native fallback About localized KO and other locales. This proves the owned QA monitor and simulated text zoom, NOT mixed-DPI 2-monitor human acceptance."),
    ("Portfolio full npm-audit upstream braces advisory triage", "Done", "high",
     "2026-10-17 isolated portfolio source PR #33 in a separate temporary worktree without touching any dirty concurrent worktrees; npm audit --json showed five HIGH advisories in DEV lint eslint-config-next -> @next/eslint-plugin-next -> fast-glob -> micromatch -> braces. Latest published braces=3.0.3, affected by GHSA-vfj7-8cjw-p6xm; no patched npm release at inspection; npm audit fix --force suggests Next-incompatible eslint-config-next14 downgrade. PR #33 production-only audit/build PASS but full audit FAIL. No safe upstream patched fix yet; do not bypass full audit or change existing security PR. Removed our temporary worktree. Triage evidence docs/qa/2026-10-17-portfolio-audit-triage.md; parent NOTRO-16 remains To Do P0 and actual landing unreleased."),
    ("Notro About page: version, GitHub, Releases, MIT and disclosures", "Done", "high",
     "2026-10-17 source 461db39: About shows actual package v2.11.0, fixed allowlisted GitHub repository/Releases/Issues/MIT URLs, Windows/WebView2 platform, unsigned/no Discord endorsement disclosure in 5 languages with accessible first-view repo link; native MessageBoxW About fallback if WebView2 unavailable. @4080 actual CoreWebView2 About click/visible screenshot QA PASS, 485 local/Windows CI tests PASS run 39085969840; manual unsigned hosted Windows run 39085985603 PASS including real installed EXE first-run creates hidden Notro Tray Menu window. QA installer 17,215,650 bytes SHA256 62593f9b66f5ae6e568ef14b6b674c68934a69523e2f860d70503b8c85c23169 independently verified NotSigned. This item Done for implementation+automated QA; human Windows10/11/right-click and Discord remain separate P0. No public release/signing."),
    ("Styled Windows tray right-click popup and native menu fallback", "Done", "high",
     "2026-10-17 base source 461db39 themed native-owned WM_RBUTTONUP WebView2 popup and classic Windows fallback; real actions, five localized languages, About links and no Discord hooks. Follow-up fixed 200-percent monitor DPI window-size bug: convert CSS 362x532 DIPs to physical 724x1064 using private Win32 GetDpiForWindow, clamp monitor work area, use compact 310x320 minimum or fall back to native menu if too small; localized native About. @4080 actual native test PASS with 5 locale pages, 100/125/150 browser text zoom, keyboard focus, compact 330x420 and signed-out UI. Previous hosted install QA run 39085985603 verified hidden tray; new real pystray notification-message end-to-end in separate QA issue pending hosted runner. Human mixed-DPI Windows 10/11 acceptance still NOTRO-24; no code signing/release/user clipboard."),
    ("Discord 2026 upload-limit baseline & 19-20 MB regression", "QA", "urgent",
     "Default 20MB (free), Nitro Basic 50MB, Nitro up to 1GB; preserve custom 10MB and 500MB; skip compression within the upload ceiling, encode with 95% safety target. All tests pass. Windows Discord integration QA remains."),
    ("Watched folder JPG/JPEG support", "QA", "high",
     "Folder discovery supports JPG and JPEG consistently with explicit importer; fixture regression. Validate picker thumbnails in real UI."),
    ("Five-language README and Show HN claim refresh", "QA", "high",
     "Update EN/KO/JA/ZH/ES README, examples, official Discord limit source, and Show HN copy; multilingual proofreading."),
    ("REA 6.4.0 static audit of installed Discord Electron ASARs", "QA", "high",
     "Read-only, no account data or runtime injection. Record exact asset hashes, graph coverage/limits, and integration recommendations. Review risk/terms before experiments."),
    ("Windows OS-level paste focus and Discord-only auto-send guard", "QA", "urgent",
     "Implemented HWND focus recheck before Ctrl+V; optional Enter only to still-focused Discord.exe/PTB/Canary via public Win32 process filename APIs. Auto-send off by default; read-only current Discord HWND identity passed; unit tests passed. Live unsent Discord draft interaction remains unverified."),
    ("Native isolated WebView2 picker and five-language fixture smoke", "Done", "high",
     "Native Windows Edge WebView2 launched against temporary owned PNG/JPEG assets, with no Discord process changes or global clipboard access. 2 assets and thumbnails loaded, 3 tabs, pack buttons, safe ZIP drop deduped, search and KO/EN/JA/ZH/ES Python-to-JS bridge passed; process exited without errors."),
    ("Native Windows file-dialog export/import E2E (Korean ZIP)", "Done", "high",
     "Executed scripts/qa_native_file_dialogs.py on @4080 using real Win32 Save As/Open dialogs and isolated native WebView2 bridge. Four stages PASS: cancel export, save Hangul-named ZIP, cancel import, import into a fresh temporary library. Original digest preserved. No Discord/clipboard/user data touched. Installer and actual Discord attachment QA separate."),
    ("Native WebView2 synthetic 100/1k/5k picker DOM benchmark", "Done", "medium",
     "Executed scripts/qa_native_webview.py on @4080 using real Windows WebView2 with synthetic 1x1 placeholders. 100 items render 1ms/search 0ms; 1000 items 8ms/search 1ms; 5000 items 39ms/search 4ms. All 5000 DOM cells created, zero errors. Real mixed-size GIF/WebView2 memory QA still required."),
    ("Local library asset server host/token access protection", "QA", "high",
     "Added per-instance random capability path and exact 127.0.0.1:port Host enforcement (DNS rebinding defense in depth), bounded streaming and HTTP regression tests. Confirmed actual WebView2 thumbnails load. Extended security/disclosure documentation."),
    ("v2.11.0 unsigned release gate and download/upgrade verification", "To Do", "urgent",
     "2026-10-17 still NO-GO for broad launch: Draft PR #1 v2.11.0 vs public latest v2.10.3. Source fa3aff1 CI 39072813556 PASS (454 tests) and hosted-runner manual run 39072830662 PASS (real Win32 CF_HDROP/text/sequence; unsigned EXE/Inno; verified public v2.10.3->2.11.0 upgrade and synthetic data preservation; SHA256 verified from 17199943-byte QA artifact). Rights-cleared original native picker GIF is now in READMEs, but not real Discord attachment footage. Still required: Discord non-sending drafts, human Win10/11 first-run & real restore/updater UX, source-licensed video/screenshots and audited live portfolio landing, human-authorized published download. No signing/tag/merge/release. Manual checklist docs/qa/2026-10-17-manual-release-acceptance.md."),
    ("Disposable Windows installed Notro.exe welcome and picker GUI smoke", "Done", "urgent",
     "2026-10-17 source 0f4606c GitHub manual Windows runner run 39077002020 PASSED. After public v2.10.3 baseline checksum-verified install and v2.11.0 upgrade, ACTUAL installed Notro.exe started with disposable APPDATA and runner-only HKCU safe defaults. Logged NOTRO_INSTALLED_EXE_FIRST_RUN_QA: runner_only=true, exe_started=true, welcome_visible=true (Notro window), picker_created=true (hidden Notro Picker), auto_send_off=true, auto_capture_off=true, startup_unchanged=true, profile_isolated=true, process_alive=true, welcome_marked=true, errors=[], passed=true. Own process tree terminated, synthetic data survived uninstall; release publication skipped, no user PC/Discord interaction. SHA256 verified for 17203616-byte unsigned 2.11.0 QA installer: b6f8ac78eae51c25a77cafda6f217351d8ce58fb750629e8e771e469dbd94cb7. Human Win10/11 GUI and real Discord unsent draft remain separate P0 tasks; no signing."),
    ("Product Hunt 2026 reality check and Notro acquisition channel decision", "Done", "high",
     "2026-10-17 reviewed Product Hunt official Oct 2025 Points, March 2026 featuring guidelines (live useful novel polished; curated, not automatic), Oct 2026 launch guide, and founder self-reports: Oct 9 46 votes 20 visits 0 sales; July zero customers+agency spam; Jan #1 4500 visits 370 signups 10 teams using; Oct Top5 thousands visited yet ~10 active users. Biased anecdotes, not platform averages. Notro verdict: defer PH until working v2.11.0 public release, audited landing, human Discord/Win10/11 QA, 5-10 opt-in beta/return evidence; if worth testing only optional free 2-4hr listing, no ad spend or vote solicitation. docs/marketing/2026-10-17-research-validation-first-growth.md updated. No posts."),
    ("Windows 10/11 real-user GUI install, hotkey and no-network QA", "To Do", "urgent",
     "Disposable Windows GitHub run 39077002020 PASS: verified public v2.10.3->candidate 2.11.0 upgrade, actual installed v2.11.0 EXE launches welcome visible and native picker created (hidden), safe settings OFF, isolated APPDATA, no startup change, synthetic profile/data preserved and uninstall PASS. This is automated QA ONLY, not a human using Windows 10/11. Real interactive unsigned SmartScreen/installer, tray, keyboard, DPI, offline WebView2 and updater still UNVERIFIED, and no actual Discord draft was used. Do not install on user's active PC without explicit permission. Manual checklist docs/qa/2026-10-17-manual-release-acceptance.md."),
    ("Rights-cleared native WebView2 picker UI demo (owned geometry)", "Done", "high",
     "2026-10-17 @4080: created scripts/record_owned_native_demo.py with deterministic original Pillow geometry; 18 emoji, 4 stickers, 3 generated animated GIFs. Captured 9 genuine native CoreWebView2 UI scenes into a 15.9sec owned GIF (~390KB) and PNG still. Tested keyboard/search/tab/settings interactions; both auto-send/capture OFF. Safety isolation corrected to never read/write real HKCU settings and captured only the owned WebView2 control, not desktop/Discord. Swapped EN/KO/JA/ZH/ES README hero GIF from third-party art to owned demo; archived old media not for advertising. This is NOT installed EXE, actual Discord attachment or clipboard demo. See docs/marketing/owned-native-demo-2026-10-17.md."),
    ("Hosted-runner Win32 CF_HDROP and Unicode clipboard integration QA", "Done", "urgent",
     "2026-10-17 source fa3aff1: actual GitHub hosted disposable Windows manual QA run 39072830662 PASSED. Log NOTRO_NATIVE_CLIPBOARD_QA: runner_only=true, filesystem_unicode=true (CF_HDROP/DragQueryFileW of Hangul path), unicode_text=true, marker=true, stale_guard=true, errors=[] and passed=true. Cleared runner clipboard. Both auto-send and auto-capture isolated OFF in native WebView fixture; no user clipboard/Discord/SendInput touched. Same run built EXE/Inno/upgrade v2.10.3->2.11.0/test-data preservation and upload of UNSIGNED QA artifact; publisher step skipped. Distinct real Discord unsent-draft paste remains P0 in NOTRO-5."),
    ("Rights-cleared real Notro demo and bilingual launch evidence", "In Progress", "high",
     "One rights-cleared 15.9s native WebView2 owned-geometric-art picker demo appears in all 5 READMEs, with honest isolated UI-only provenance; old copyright-sensitive docs/demo.gif/picker.png excluded. 2026-10-17 completed competitive research (PowerToys Advanced Paste, ShareX, Vencord FakeNitro, EmojiPick) and segmentation: personal hotkey media library first, oversized screenshot compression second. 0 stars/35 public v2.10.3 installer-asset downloads are NOT installed users. Opt-in beta scorecard/EN-KO positioning at docs/marketing/2026-10-17-research-validation-first-growth.md. Still missing real approved Discord non-sending attachment and screenshot/gameclip evidence, audited live landing, 5-10 consented testers and human-only posting; no public launches."),

    ("Release QA audit and actual pixel/ffmpeg boundary preflight", "Done", "high",
     "2026-10-17 source 413623c: GitHub Windows CI 39058070961 PASS (449 tests, pip-audit, Ruff, exact/off-by-one 20MB and high-entropy 27MB PNG -> WebP); workflow 39058080501 PASS (PyInstaller, Inno, official v2.10.3 checksum+version, v2.11.0 upgrade, synthetic profile preserved, uninstall, SHA and short-lived QA artifact). @4080 independently verified unsigned candidate NotroSetup.exe SHA256 df91f3e77b7e81405511f767ef7f2f6f3a0c1f376f5c96d0b75f56680671ba73, bytes 17196309. Real ffmpeg 5sec video/audio and 2sec trim/mute passed. No user clipboard/account or code signing; no public release. Human GUI/Discord and landing P0 remain separate."),
    ("Disposable owned Win32 target Ctrl+V, focus and new-copy QA", "Done", "urgent",
     "2026-10-17 source 77689d6 actual GitHub Windows hosted runner manual workflow 39075263021 PASSED. Log NOTRO_OWN_WINDOW_PASTE_QA {runner_only:true,owned_window:true,foreground_file_ctrl_v:true,lost_target_preserved:true,newer_copy_preserved:true,auto_send_called:false,errors:[],passed:true}. Code checks target HWND BEFORE clipboard mutation, guards both CF_HDROP and URL text against newer copy, rechecks after clipboard commit and verifies SendInput accepts key sequence. Runner GUI uses independently owned Tk input and blocked Enter, never user's clipboard/chat/Discord. Same release run 465 tests and v2.10.3->2.11.0 unsigned upgrade preserve data PASS; unsigned installer bytes 17199014 SHA256 2529718fe90e54b28a8fc96ca03915ebc050bc033f5d9238f055e5580c8e888c verified. This is NOT actual Discord draft attachment acceptance, still P0 NOTRO-5."),
    ("Competition positioning and consent-led beta research", "Done", "high",
     "2026-10-17 research completed with sources Microsoft PowerToys Advanced Paste, ShareX, Vencord FakeNitro, MrLouix EmojiPick, official Product Hunt/HN rules and Reddit qualitative friction. Identified Notro differentiation: user-owned personal media library + Windows hotkey + attachment workflow; not free Nitro, not native inline emoji. GitHub observed 0 stars, 35 latest public installer asset downloads (not installs), trailing 14d views 13/uniques 8. Prepared EN/KO claims, competitor table, three personas, cautious staged zero-ad-spend user activation experiment and opt-in scorecard. See docs/marketing/2026-10-17-research-validation-first-growth.md and 2026-10-17-beta-user-scorecard.md. No user invites, commercial purchases or public marketing posts were executed."),
    ("Recruit 5-10 opt-in users for first attachment draft beta", "To Do", "high",
     "AFTER safe human Windows10/11 GUI and real non-sending Discord draft acceptance, privately invite 5-10 explicitly consenting testers with separate initial task and optional observation consent (Segment A media library, B 24MB screenshot, C privacy/unsigned install). Use repo docs/marketing/2026-10-17-beta-user-scorecard.md; gather redacted local task time, install success, attachment-not-inline understanding and voluntary followup; NEVER collect clipboard/chat tokens/IDs, do not post on public communities without permission. No automatic contact/telemetry currently."),
    ("Windows real-app picker and clipboard E2E smoke QA", "In Progress", "urgent",
     "Windows WebView2 picker, Korean file dialogs and 5000 synthetic cells PASS. Hosted-runner real Win32 CF_HDROP/text/marker/stale guard run 39072830662 PASS; owned-Tk-window *actual* Ctrl+V SendInput/foreground/file-path delivery and lost-focus/new-copy preservation run 39075263021 PASS, source 77689d6. Neither test interacts with Discord. P0 STILL requires user-authorized actual Discord private unsent PNG/JPEG/GIF attachment preview, focus switching, realistic 19.5/24MB and Windows10/11 human GUI/DPI, no private chats/tokens or sending. Optional auto-send stays OFF."),
    ("Harden Notro main branch review/CI rules before code signing", "Backlog", "low",
     "Explicit user decision 2026-10-14: SIGNING WILL NOT BE PURSUED. This signing-dependent branch review project is deferred; do not update GitHub branch protection, request signing approval, initiate service enrollment, or spend funds. Ordinary code/QA CI remains active."),
    ("Notro trust and distribution: signing and pinned builds", "Backlog", "low",
     "Explicit user decision 2026-10-14: NO SIGNING. Do not sign, apply for certificates, connect SignPath/Azure, alter publishing settings or incur charges. Existing unsigned installer QA data is documented. Future user-approved unsigned release/distribution decisions are separate and must clearly disclose unsigned status."),
    ("First-run activation: 3-minute task-guided welcome", "QA", "high",
     "First-run Try Picker action localized. 2026-10-18 actual Windows WebView2 test uncovered public WinForms window API recursively stalling JS bridge; fixed by hiding native window handle in private field. Isolated native Welcome -> Try Picker with synthetic asset, Dismiss flow PASS; same fix in video confirm UI. Hosted runner native QA pending separate new task. **Actual 3-minute human first-paste** on Windows 10/11/Discord remains unverified, so NOTRO-7 stays QA, not Done."),
    ("Shareable safe emoji pack import/export and library backup", "QA", "high",
     "Portable ZIP packs/hash/dupe rules, private Captures excluded, drag import and separate JSON settings implemented. 2026-10-18 invalid ZIP metadata type list/dict and broken container failed with internal exceptions; fixed to fail-closed PackError and outer archive size limit. Real @4080 Win32 Save/Open now 10 stages PASS (including malformed ZIP/JSON) with unchanged existing library; 528 unit tests PASS. Hosted actual EXE recovery and human UX remain separate QA; not approved for public launch."),
    ("Oversized GIF optimization with transparent size/quality preview", "QA", "high",
     "Implemented a bounded palette-first GIF candidate engine, animated before/after UI, actual upload-ceiling trigger, original file/timing preservation, explicit approval and manual-send-only clipboard path. Native WebView2 fixture validates both animated thumbnails, cancel cleanup and mock accepted paste. Unit/regression tests pass; actual Discord private-draft delivery, large real-world GIF visual-quality acceptance and installer packaging remain to verify."),
    ("Picker 100/1k/5k assets benchmark and asset server hardening", "QA", "high",
     "Synthetic 100/1k/5k scan/search benchmarks and bounded 64KiB local media streaming with unit tests implemented. Actual Windows WebView2 synthetic 5000-cell DOM render 39ms and query ~4ms passed; genuine animated GIF decoding, peak memory and sustained scroll still need QA."),
    ("English-first landing SEO update for writingdeveloper.blog/projects/notro", "QA", "high",
     "As of 2026-10-17 live writingdeveloper.blog/projects/notro responds HTTP 200 but still serves free 10MB, v2.0 text and blanket ToS-safety metadata. Portfolio PR #36 is unmerged Draft, CI dependency audit FAILED; separate security PR #33 also failed. Do not bypass npm audit or alter other agents worktrees. On safe merge verify actual live EN/KO title, description, social OG, disclaimers and release CTA matched to published version."),
    ("Portfolio security audit blocker for Notro landing PR #36", "To Do", "urgent",
     "Portfolio Draft PR #36 landing updates still unmerged; live site still outdated 10MB/v2.0. Isolated 2026-10-17 triage of portfolio security PR #33 source 2a4973e confirms production build+production-only audit PASS, but full npm audit FAIL with five HIGH DEV lint issues under eslint-config-next->fast-glob->micromatch->braces, GHSA-vfj7-8cjw-p6xm; npm latest braces 3.0.3 itself affected, no published patched version discovered. npm audit fix --force suggests incompatible eslint-config-next14 downgrade. Cannot safely declare audit green or deploy; do not disable check, replace lint without equivalent coverage, touch another agent worktree or force merge. Evidence docs/qa/2026-10-17-portfolio-audit-triage.md; remains explicit P0 To Do."),
    ("3 short demos + community-friendly beta launch", "To Do", "high",
     "Owned 15.9s actual WebView2 UI-only picker GIF recorded; research/segmentation and opt-in beta scorecard DONE (separate task), no recruitment or posts. Still need rights-cleared actual screenshot clipboard compression, game clip and consented UNsent Discord draft attachment videos, genuine English/Korean onboarding feedback from 5-10 users and safe portfolio landing/actual v2.11.0 published matching release. HN forbids generated submissions/comments and automated posts; Product Hunt forbids upvote solicitation, Reddit self-promotion moderated. Hold public promotion until P0 release and human approval."),
    ("First-month activation and privacy-respecting impact dashboard", "Backlog", "medium",
     "Track web CTA clicks, release assets, opt-in beta success rates; no clipboard, filename or account telemetry."),
    ("Full app settings and watched-folder backup/restore", "QA", "high",
     "Opt-in JSON settings backup/preview/approval with 128KiB cap and SHA, watched absolute paths excluded by default; no media/Captures/Discord account data, auto-send/capture off after import. 2026-10-18 fixed unhashable watched_folder default_type that previously triggered raw TypeError instead of safe SettingsBackupError. @4080 native Korean Save/Open 10/10 PASS including malicious JSON rejection with ZERO registry writes; 528 unit tests PASS. Real user restoration, restart and language/hotkey remain unverified, so QA stays open."),
    ("Future cross-app paste and compatibility research", "Backlog", "low",
     "Only after core Discord usage proves repeat engagement; evaluate Slack, Telegram, Teams with independent integrations."),
]


def load_env() -> None:
    default = Path.home() / ".config" / "plane-mcp" / "plane.env"
    p = Path(os.environ.get("PLANE_MCP_ENV", str(default)))
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip(" '\""))


def rows(data):
    if isinstance(data, dict):
        return data.get("results", [])
    return data or []


def sync_payload(name: str, description: str, state_id: str,
                 priority: str, exists: bool) -> dict:
    """Never overwrite a human/other-session state on existing issues."""
    payload = {"description_html": description}
    if not exists:
        payload.update({"name": name, "state": state_id, "priority": priority})
    return payload


class Plane:
    def __init__(self):
        import requests
        self._requests = requests
        self.base = os.environ["PLANE_BASE_URL"].rstrip("/")
        self.slug = os.environ.get("PLANE_WORKSPACE_SLUG", WORKSPACE_DEFAULT)
        self.headers = {
            "X-API-Key": os.environ["PLANE_API_KEY"], "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.workspaces = f"/api/v1/workspaces/{quote(self.slug)}"

    def api(self, method, path, payload=None):
        response = self._requests.request(
            method, self.base + path, headers=self.headers, json=payload, timeout=30)
        if not response.ok:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}")
        return response.json() if response.content else None

    def projects(self):
        return rows(self.api("GET", self.workspaces + "/projects/?per_page=100"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create/update Plane project and items")
    args = parser.parse_args()

    load_env()
    try:
        plane = Plane()
    except KeyError as exc:
        raise SystemExit(f"Missing Plane config environment entry: {exc.args[0]}")

    projects = plane.projects()
    project = next((x for x in projects if x.get("identifier") == PROJECT_ID
                    or x.get("name", "").casefold() == PROJECT_NAME.casefold()), None)
    if args.apply and project is None:
        project = plane.api("POST", plane.workspaces + "/projects/", {
            "name": PROJECT_NAME, "identifier": PROJECT_ID,
            "description": "Notro Windows clipboard/Discord companion: engineering QA, REA compatibility review, distribution trust, onboarding and ethical open-source launch.",
        })
        print("CREATED PROJECT", PROJECT_ID, project["id"])
    elif project:
        print("FOUND PROJECT", project.get("identifier"), project.get("id"))
    else:
        print("WOULD CREATE PROJECT", PROJECT_ID)

    if not args.apply:
        for name, state, priority, _ in ISSUES:
            print("DRY_RUN", state, priority, name)
        return

    project_path = plane.workspaces + f"/projects/{quote(project['id'])}"
    states = rows(plane.api("GET", project_path + "/states/?per_page=100"))
    by_name = {x["name"]: x for x in states}
    defaults = [
        ("Backlog", 10000, "backlog", "#64748B"),
        ("To Do", 20000, "unstarted", "#94A3B8"),
        ("In Progress", 30000, "started", "#3B82F6"),
        ("QA", 42000, "started", "#8B5CF6"),
        ("Done", 50000, "completed", "#16A34A"),
    ]
    for name, order, group, color in defaults:
        if name not in by_name:
            item = plane.api("POST", project_path + "/states/", {
                "name": name, "sequence": order, "group": group,
                "color": color, "description": "Notro release state",
            })
            by_name[name] = item
            print("CREATED STATE", name)

    previous = rows(plane.api("GET", project_path + "/work-items/?limit=100&offset=0"))
    previous_by_name = {x.get("name"): x for x in previous}
    for name, state, priority, done in ISSUES:
        description = (
            "<div><h3>Acceptance criteria</h3><p>" + html.escape(done) +
            "</p><h3>References</h3><p>Repository: " +
            "https://github.com/writingdeveloper/Notro/pull/1" +
            " · REA: https://github.com/morluto/rea</p></div>"
        )
        found = previous_by_name.get(name)
        item = sync_payload(name, description, by_name[state]["id"],
                            priority, exists=bool(found))
        if found:
            # Plane is the source of truth for existing item state and priority.
            # Sessions may have progressed an item after this script was written.
            if found.get("description_html") != description:
                plane.api("PATCH", project_path + f"/work-items/{quote(found['id'])}/", item)
                print("REFRESHED ISSUE", found.get("sequence_id"), "state-preserved", name)
            else:
                print("UNCHANGED ISSUE", found.get("sequence_id"), "state-preserved", name)
        else:
            created = plane.api("POST", project_path + "/work-items/", item)
            print("CREATED ISSUE", created.get("sequence_id"), state, name)
    print("SYNC COMPLETE", PROJECT_ID, len(ISSUES))


if __name__ == "__main__":
    main()
