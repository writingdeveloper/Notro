#!/usr/bin/env python3
"""Idempotent Notro Plane backlog sync (never prints tokens).

Dry-run by default. --apply creates/updates NOTRO project and named work items.
Run after git/QA review, adjust STATUSES below to reflect verified progress.
"""
from __future__ import annotations

import argparse
import html
import json
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
     "Default 20MB (free), Nitro Basic 50MB, Nitro 500MB; preserve custom 10MB; skip compression within the upload ceiling, encode with 95% safety target. All tests pass. Windows Discord integration QA remains."),
    ("Watched folder JPG/JPEG support", "QA", "high",
     "Folder discovery supports JPG and JPEG consistently with explicit importer; fixture regression. Validate picker thumbnails in real UI."),
    ("Five-language README and Show HN claim refresh", "QA", "high",
     "Update EN/KO/JA/ZH/ES README, examples, official Discord limit source, and Show HN copy; multilingual proofreading."),
    ("REA 6.4.0 static audit of installed Discord Electron ASARs", "QA", "high",
     "Read-only, no account data or runtime injection. Record exact asset hashes, graph coverage/limits, and integration recommendations. Review risk/terms before experiments."),
    ("Windows real-app picker and clipboard E2E smoke QA", "To Do", "urgent",
     "Run Discord test in a private draft (no unwanted message sent), exercise PNG/JPEG/GIF, hotkeys, source file preservation, auto-send off, keyboard use, DPI/multi-monitor, failure recovery."),
    ("Notro trust and distribution: signing and pinned builds", "To Do", "high",
     "Evaluate OSS signing routes, build provenance/attestation, SHA256 consistency, dependency pinned build and vulnerability checks, installer SmartScreen experience."),
    ("First-run activation: 3-minute task-guided welcome", "QA", "high",
     "First-run Try Picker action implemented and localized. Confirm 3-minute human first-paste usability on Windows WebView2 before Done."),
    ("Shareable safe emoji pack import/export and library backup", "QA", "high",
     "Portable ZIP media packs, hashed assets, import/export UI and exclusion of private Captures are implemented and tested. WebView2 dialogs require QA. Full app settings backup is separate."),
    ("Oversized GIF optimization with transparent size/quality preview", "To Do", "high",
     "Optimize oversized GIFs only with explicit consent; prefer loss-minimized frame and scale strategies, preserve original file, surface result quality and failure."),
    ("Picker 100/1k/5k assets benchmark and asset server hardening", "QA", "high",
     "Synthetic 100/1k/5k scan/search benchmarks and bounded 64KiB local media streaming with unit tests implemented. Real WebView2 DOM/RAM and GIF scrolling still require QA."),
    ("English-first landing SEO update for writingdeveloper.blog/projects/notro", "QA", "high",
     "Source metadata updated in portfolio PR #36 (not merged/deployed). Existing npm audit on that PR found 10 high + 1 critical dependency vulnerabilities (next/sharp/braces/etc); must coordinate with existing portfolio security branch, not bypass CI; QA SEO/OG/CTA after secure merge and deployment."),
    ("Portfolio security audit blocker for Notro landing PR #36", "To Do", "urgent",
     "Portfolio content tests, translation and build pass, but npm audit --audit-level=high reports 11 vulnerable dependencies (10 high, 1 critical) on 2026-10-13: https://github.com/writingdeveloper/portfolio/actions/runs/38486167720. Existing security worktrees/branches must be preserved; coordinate dependency fixes before merging or deploying #36."),
    ("3 short demos + community-friendly beta launch", "To Do", "high",
     "Create truthful 10-20s raw workflow clips (not staged outcomes), EN/KO community messaging, opt-in testers, allowed Reddit/HN posts. Public posting only with account/venue review."),
    ("First-month activation and privacy-respecting impact dashboard", "Backlog", "medium",
     "Track web CTA clicks, release assets, opt-in beta success rates; no clipboard, filename or account telemetry."),
    ("Full app settings and watched-folder backup/restore", "To Do", "medium",
     "ZIP media pack does not include registry settings, external watched-folder paths or private Captures. Design explicit full-backup scope, restore validation and consent before implementing."),
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
        item = {
            "name": name, "description_html": description,
            "state": by_name[state]["id"], "priority": priority,
        }
        found = previous_by_name.get(name)
        if found:
            plane.api("PATCH", project_path + f"/work-items/{quote(found['id'])}/", item)
            print("UPDATED ISSUE", found.get("sequence_id"), state, name)
        else:
            created = plane.api("POST", project_path + "/work-items/", item)
            print("CREATED ISSUE", created.get("sequence_id"), state, name)
    print("SYNC COMPLETE", PROJECT_ID, len(ISSUES))


if __name__ == "__main__":
    main()
