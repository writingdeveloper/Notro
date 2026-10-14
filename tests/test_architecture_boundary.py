"""REA is a developer's offline investigation tool, NEVER a Notro runtime dependency.

Discourage future accidental use of Discord's proprietary internal interfaces,
user tokens, client injection modules, or REA startup from the product process.
This is a lightweight architecture policy, not a complete source-security scan.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_rea_or_discord_client_runtime_dependency():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    normalized = [x.strip().lower() for x in requirements.splitlines()]
    assert not any(x.startswith(("rea-", "discord.py", "betterdiscord"))
                   for x in normalized)

    forbidden = {"rea", "rea_agents", "discord", "betterdiscord",
                 "vencord", "frida"}
    for source in (ROOT / "notro_app").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = (alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert name.split(".")[0].casefold() not in forbidden, (
                    f"External Discord/REA internals imported at {source}: {name}"
                )


def test_rea_findings_are_documented_but_not_bundled_with_notro():
    assert (ROOT / "docs/research/2026-10-13-rea-discord-audit.md").is_file()
    assert not (ROOT / "notro_app/rea").exists()
    assert not (ROOT / "notro_app/discord").exists()
