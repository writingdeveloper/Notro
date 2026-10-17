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
     "2026-10-17 NO-GO for broad launch: Draft PR #1 is v2.11.0 but public latest remains v2.10.3. Before any release: pass GitHub CI, ephemeral unsigned installer install/uninstall/upgrade smoke, private Discord non-sending draft, portable backup and updater checks, verified SHA256 and version-matched real download, human maintainer manual authorization. Do not create tags/merge/release or pursue signing automatically. See docs/qa/2026-10-17-release-readiness.md."),
    ("Windows 10/11 real-user GUI install, hotkey and no-network QA", "To Do", "urgent",
     "Disposable GitHub Windows 11 runner QA install/exe version/uninstall is a preliminary gate; test real human Windows 10 and 11 unsigned installer (including SmartScreen warning disclosure), tray accessibility, first-run, locale, DPI, auto-update, upgrade from v2.10.3, uninstall/data retention and offline WebView2 degradation. No active PC install without separate consent."),
    ("Rights-cleared real Notro demo and bilingual launch evidence", "To Do", "high",
     "Current README demo.gif/picker.png include identifiable third-party character images; obtain marketing redistribution rights or recapture live Notro UI using rights-cleared owned assets. Produce truthful EN/KO 10-20s examples, GIF/file/picker workflow, show attachment not native inline emoji, verify no user chats/tokens. Do NOT publish automated HN/Reddit/Discord marketing; follow community promotion rules."),
    ("Release QA audit and actual pixel/ffmpeg boundary preflight", "QA", "high",
     "2026-10-17 implemented CI dependency pip-audit build-tool checks, pinned PyInstaller, 20MB exact/off-by-one padded PNG and real 27MB high-entropy PNG to WebP, 5-sec synthetic 960x540 -> 854x480 with audio and trimmed/muted 2sec real ffmpeg. No user's clipboard/account touched. Confirm GH CI/release workflow green, check no false positives, publish no release. User opts out of signing."),
    ("Windows real-app picker and clipboard E2E smoke QA", "In Progress", "urgent",
     "Windows actual WebView2 picker smoke, Korean real Save/Open dialogs and synthetic 5000-item DOM benchmarks PASS. Remaining: safe Discord unpublished draft Ctrl+V with PNG/JPG/GIF and 19.5/24MB thresholds, focus hotkeys, manual clipboard-preservation review, per-monitor DPI and installer runtime. Do not auto-send chat or access account/private messages during automated QA."),
    ("Harden Notro main branch review/CI rules before code signing", "Backlog", "low",
     "Explicit user decision 2026-10-14: SIGNING WILL NOT BE PURSUED. This signing-dependent branch review project is deferred; do not update GitHub branch protection, request signing approval, initiate service enrollment, or spend funds. Ordinary code/QA CI remains active."),
    ("Notro trust and distribution: signing and pinned builds", "Backlog", "low",
     "Explicit user decision 2026-10-14: NO SIGNING. Do not sign, apply for certificates, connect SignPath/Azure, alter publishing settings or incur charges. Existing unsigned installer QA data is documented. Future user-approved unsigned release/distribution decisions are separate and must clearly disclose unsigned status."),
    ("First-run activation: 3-minute task-guided welcome", "QA", "high",
     "First-run Try Picker action implemented and localized. Confirm 3-minute human first-paste usability on Windows WebView2 before Done."),
    ("Shareable safe emoji pack import/export and library backup", "QA", "high",
     "Portable ZIP media packs, hashed assets, import/export UI and single-ZIP drag-and-drop with private Captures exclusion are implemented and tested (native fixture ZIP-drop PASS). Native WebView2 and Win32 ZIP dialogs PASS; standalone opt-in JSON settings backup is separate."),
    ("Oversized GIF optimization with transparent size/quality preview", "QA", "high",
     "Implemented a bounded palette-first GIF candidate engine, animated before/after UI, actual upload-ceiling trigger, original file/timing preservation, explicit approval and manual-send-only clipboard path. Native WebView2 fixture validates both animated thumbnails, cancel cleanup and mock accepted paste. Unit/regression tests pass; actual Discord private-draft delivery, large real-world GIF visual-quality acceptance and installer packaging remain to verify."),
    ("Picker 100/1k/5k assets benchmark and asset server hardening", "QA", "high",
     "Synthetic 100/1k/5k scan/search benchmarks and bounded 64KiB local media streaming with unit tests implemented. Actual Windows WebView2 synthetic 5000-cell DOM render 39ms and query ~4ms passed; genuine animated GIF decoding, peak memory and sustained scroll still need QA."),
    ("English-first landing SEO update for writingdeveloper.blog/projects/notro", "QA", "high",
     "As of 2026-10-17 live writingdeveloper.blog/projects/notro responds HTTP 200 but still serves free 10MB, v2.0 text and blanket ToS-safety metadata. Portfolio PR #36 is unmerged Draft, CI dependency audit FAILED; separate security PR #33 also failed. Do not bypass npm audit or alter other agents worktrees. On safe merge verify actual live EN/KO title, description, social OG, disclaimers and release CTA matched to published version."),
    ("Portfolio security audit blocker for Notro landing PR #36", "To Do", "urgent",
     "Portfolio content tests/translation/build pass, npm audit --audit-level=high FAILED (10 high, 1 critical on 2026-10-13): https://github.com/writingdeveloper/portfolio/actions/runs/38486167720. As of 2026-10-17, portfolio security Draft PR #33 and Notro landing Draft PR #36 both have failing CI. Do not bypass audit/merge/live deploy; coordinate separately with existing portfolio security worktrees."),
    ("3 short demos + community-friendly beta launch", "To Do", "high",
     "Real 10-20sec raw workflow clips with permission-cleared synthetic/owned assets, truthfully show clipboard, attach and size reductions, EN/KO onboarding, 5-10 consenting beta testers. HN guidelines forbid AI-generated submission/comment text and automatic posting. No public posts, promo/spam or invented metrics until P0 QA and maintainer approve."),
    ("First-month activation and privacy-respecting impact dashboard", "Backlog", "medium",
     "Track web CTA clicks, release assets, opt-in beta success rates; no clipboard, filename or account telemetry."),
    ("Full app settings and watched-folder backup/restore", "QA", "high",
     "Created independent user-selected JSON settings backup/export and two-stage review/apply. Strict 128KiB preflight, allowlisted settings, export path opt-in, optional additive restore of existing watched folders, file content digest guard; no media/Captures/Discord data, auto-send/capture OFF and startup unchanged after import. 5-language UI/docs and 438 local tests PASS. Real Windows Save/Open with Korean JSON/ZIP filenames 8 stages PASS without modifying user registry (QA intercept). Actual live user acceptance, restart and language/hotkey behavior remain QA gates. Image backup still separate ZIP pack."),
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
