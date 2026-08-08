import re
import subprocess
import sys
from pathlib import Path

import pytest

import check_release_version
from notro_app import __version__


RELEASE_WORKFLOW = Path(".github/workflows/release.yml")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
PUSH_TAG_GUARD = (
    "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')"
)


def _workflow(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _step(workflow: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(.*?)(?=^      - (?:name:|uses:)|\Z)",
        workflow,
    )
    assert match is not None, f"workflow step not found: {name}"
    return match.group(0)


def _run_commands(workflow: str) -> list[str]:
    commands = []
    lines = workflow.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("        run:"):
            index += 1
            continue

        command = line.removeprefix("        run:").strip()
        if command in {"|", "|-", "|+", ">", ">-", ">+"}:
            block = []
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith("          ")
            ):
                block.append(lines[index])
                index += 1
            commands.append("\n".join(block))
            continue

        commands.append(command)
        index += 1
    return commands


def test_expected_tag_uses_app_version():
    assert check_release_version.expected_tag() == "v2.10.3"


def test_validate_tag_accepts_matching_release():
    check_release_version.validate_tag("v2.10.3")


def test_validate_tag_rejects_mismatch():
    with pytest.raises(ValueError, match="expected v2.10.3"):
        check_release_version.validate_tag("v2.10.4")


def test_cli_returns_nonzero_for_mismatched_tag():
    result = subprocess.run(
        [sys.executable, "check_release_version.py", "v2.10.4"],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "expected v2.10.3" in result.stderr


def test_cli_returns_nonzero_for_shell_significant_mismatched_tag():
    result = subprocess.run(
        [sys.executable, "check_release_version.py", 'v2.10.4";exit(0);#'],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "expected v2.10.3" in result.stderr


def test_release_workflow_passes_tag_by_environment_variable():
    workflow = _workflow(RELEASE_WORKFLOW)

    assert 'run: python check_release_version.py "$env:GITHUB_REF_NAME"' in workflow
    assert 'run: python check_release_version.py "${{ github.ref_name }}"' not in workflow


def test_release_workflow_keeps_github_expressions_out_of_commands():
    commands = _run_commands(_workflow(RELEASE_WORKFLOW))

    assert commands
    assert all("${{" not in command for command in commands)


def test_installer_version_is_numeric_and_derived_from_app_version():
    workflow = _workflow(RELEASE_WORKFLOW)
    export_version = _step(workflow, "Export app version")
    build_installer = _step(workflow, "Build installer")

    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert "if:" not in export_version
    assert "from notro_app import __version__" in export_version
    assert "^\\d+\\.\\d+\\.\\d+$" in export_version
    assert '"APP_VERSION=$version"' in export_version
    assert "$env:GITHUB_ENV" in export_version
    assert "if:" not in build_installer
    assert "/DAppVersion=$env:APP_VERSION" in build_installer
    assert "github.ref_name" not in build_installer


def test_release_mutations_require_a_push_event_and_tag_ref():
    workflow = _workflow(RELEASE_WORKFLOW)

    assert PUSH_TAG_GUARD in _step(workflow, "Reject an existing release")
    assert PUSH_TAG_GUARD in _step(workflow, "Publish release")


def test_tag_reruns_check_for_an_existing_release_with_authenticated_api():
    guard = _step(_workflow(RELEASE_WORKFLOW), "Reject an existing release")

    assert "GH_TOKEN: ${{ github.token }}" in guard
    assert "RELEASE_TAG: ${{ github.ref_name }}" in guard
    assert "gh api" in guard
    assert "releases/tags/" in guard
    assert "$LASTEXITCODE" in guard
    assert "404" in guard


@pytest.mark.parametrize(
    ("api_status", "api_output", "expected_status"),
    [
        pytest.param(1, "gh: Not Found (HTTP 404)", 0, id="missing-release"),
        pytest.param(0, '{"id":123}', 1, id="existing-release"),
        pytest.param(
            1,
            "gh: Internal Server Error (HTTP 500)",
            1,
            id="api-error",
        ),
    ],
)
def test_existing_release_guard_exit_contract(api_status, api_output, expected_status):
    guard = _step(_workflow(RELEASE_WORKFLOW), "Reject an existing release")
    [command] = _run_commands(guard)
    api_call = (
        '          $output = gh api '
        '"repos/{owner}/{repo}/releases/tags/$encodedTag" 2>&1'
    )
    simulated_api = (
        f"          $output = '{api_output}'\n"
        f"          $global:LASTEXITCODE = {api_status}"
    )
    assert api_call in command
    command = command.replace(api_call, simulated_api)
    command += """
if ((Test-Path -LiteralPath variable:\\LASTEXITCODE)) {
  exit $LASTEXITCODE
}
"""

    result = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        text=True,
        capture_output=True,
    )

    assert result.returncode == expected_status, result.stderr


def test_release_assets_cannot_overwrite_existing_files():
    publish = _step(_workflow(RELEASE_WORKFLOW), "Publish release")

    assert "overwrite_files: false" in publish


@pytest.mark.parametrize("workflow_path", [RELEASE_WORKFLOW, CI_WORKFLOW])
def test_workflows_use_node_24_action_majors(workflow_path):
    workflow = _workflow(workflow_path)

    assert re.findall(r"actions/checkout@\S+", workflow) == ["actions/checkout@v7"]
    assert re.findall(r"actions/setup-python@\S+", workflow) == [
        "actions/setup-python@v7"
    ]


def test_release_workflow_uses_node_24_release_action_major():
    workflow = _workflow(RELEASE_WORKFLOW)

    assert re.findall(r"softprops/action-gh-release@\S+", workflow) == [
        "softprops/action-gh-release@v3"
    ]
