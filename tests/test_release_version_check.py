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
    assert check_release_version.expected_tag() == "v2.11.0"


def test_validate_tag_accepts_matching_release():
    check_release_version.validate_tag("v2.11.0")


def test_validate_tag_rejects_mismatch():
    with pytest.raises(ValueError, match="expected v2.11.0"):
        check_release_version.validate_tag("v2.10.4")


def test_cli_returns_nonzero_for_mismatched_tag():
    result = subprocess.run(
        [sys.executable, "check_release_version.py", "v2.10.4"],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "expected v2.11.0" in result.stderr


def test_cli_returns_nonzero_for_shell_significant_mismatched_tag():
    result = subprocess.run(
        [sys.executable, "check_release_version.py", 'v2.10.4";exit(0);#'],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "expected v2.11.0" in result.stderr


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


def test_manual_release_run_uploads_short_lived_unsigned_qa_artifact():
    workflow = _workflow(RELEASE_WORKFLOW)
    step = _step(workflow, "Upload unsigned QA installer")
    assert "if: github.event_name == 'workflow_dispatch'" in step
    assert "actions/upload-artifact@v7" in step
    assert "NOTRO-UNSIGNED-QA-" in step
    assert "retention-days: 3" in step
    assert "if-no-files-found: error" in step
    assert "overwrite: false" in step
    assert "dist/NotroSetup.exe.sha256" in step
    assert "dist/NotroSetup.exe" in step
    assert PUSH_TAG_GUARD in _step(workflow, "Publish release")


def test_release_gates_audit_pinned_build_requirements_and_media_thresholds():
    release = _workflow(RELEASE_WORKFLOW)
    ci = _workflow(CI_WORKFLOW)
    assert "run: pip install -r requirements-build.txt" in release
    assert "python -m pip_audit -r requirements-build.txt --strict" in release
    assert "python -m pip_audit -r requirements-build.txt --strict" in ci
    assert "python scripts/qa_release_media_preflight.py" in release
    assert "python scripts/qa_release_media_preflight.py" in ci
    assert "Publish release" in release
    assert PUSH_TAG_GUARD in _step(release, "Publish release")


def test_build_tools_versions_pinned_with_no_runtime_signing():
    build_req = Path("requirements-build.txt").read_text(encoding="utf-8")
    build_script = Path("build.bat").read_text(encoding="utf-8-sig")
    assert "pyinstaller==6.21.0" in build_req
    assert "pip-audit==2.10.1" in build_req
    assert "requirements-build.txt" in build_script
    assert "signpath" not in build_req.lower()


def test_unsigned_disposable_runner_installer_smoke_is_opt_in():
    release = _workflow(RELEASE_WORKFLOW)
    stage = _step(release, "QA install and uninstall on ephemeral runner")
    assert "if: github.event_name == 'workflow_dispatch'" in stage
    assert "scripts/qa_installer_smoke.ps1" in stage
    assert PUSH_TAG_GUARD in _step(release, "Publish release")
    inno = Path("installer.iss").read_text(encoding="utf-8-sig")
    assert "Check: ShouldLaunchNotro" in inno
    assert "NOTRO_QA_SUPPRESS_AUTORUN" in inno
    assert "Result := GetEnv(" in inno
    ps = Path("scripts/qa_installer_smoke.ps1").read_text(encoding="utf-8")
    assert "GITHUB_ACTIONS" in ps and "RUNNER_TEMP" in ps
    assert "NOTRO_QA_SUPPRESS_AUTORUN" in ps
    assert "NotSigned" in ps
    assert "QA_INSTALL_UNINSTALL_PASSED" in ps
    assert "unins000.exe" in ps


def test_release_refuse_tags_not_reachable_from_origin_main():
    workflow = _workflow(RELEASE_WORKFLOW)
    ancestry = _step(workflow, "Verify release tag belongs to main")
    assert "if: startsWith(github.ref, 'refs/tags/')" in ancestry
    assert "git fetch origin main" in ancestry
    assert "git merge-base --is-ancestor $env:GITHUB_SHA origin/main" in ancestry
    assert "$LASTEXITCODE -ne 0" in ancestry
    assert "fetch-depth: 0" in workflow


def test_media_release_gate_includes_real_pixel_data_not_just_padding():
    script = Path("scripts/qa_release_media_preflight.py").read_text(
        encoding="utf-8"
    )
    assert "rng.randbytes(3000 * 3000 * 3)" in script
    assert 'summary["real_pixel_png"]' in script
    assert "sha256(noisy) == noise_digest" in script
    assert "converted.stat().st_size <= config.LIMIT_BYTES" in script


def test_qa_installer_upgrade_from_checksum_verified_public_release():
    release = _workflow(RELEASE_WORKFLOW)
    stage = _step(release, "QA install and uninstall on ephemeral runner")
    assert "GH_TOKEN:" in stage and "github.token" in stage
    script = Path("scripts/qa_installer_smoke.ps1").read_text(encoding="utf-8")
    assert "gh release download v2.10.3" in script
    assert "Get-FileHash -LiteralPath $baselineExe -Algorithm SHA256" in script
    assert "Baseline process still running before upgrade" in script
    assert "Synthetic settings/data marker" in script
    assert "NOTRO_QA_BASELINE_TO_CANDIDATE_UPGRADE_PRESERVED_DATA" in script
    assert "NOTRO_QA_UPGRADE_UNINSTALL_PASSED" in script


def test_installer_upgrade_waits_for_installer_only_not_persistent_tray_child():
    script = Path("scripts/qa_installer_smoke.ps1").read_text(
        encoding="utf-8"
    )
    assert "$Process.WaitForExit(120000)" in script
    assert "Wait-OnlyInstallerProcess -Process $baseline" in script
    assert "Wait-OnlyInstallerProcess -Process $installed" in script
    assert "Wait-OnlyInstallerProcess -Process $uninstalled" in script
    assert not any("-Wait -PassThru" in line for line in script.splitlines())


def test_runner_clipboard_contract_cannot_run_on_real_user_pc():
    release = _workflow(RELEASE_WORKFLOW)
    stage = _step(release, "QA native Win32 clipboard on disposable runner")
    assert "if: github.event_name == 'workflow_dispatch'" in stage
    assert "python scripts/qa_runner_clipboard_cf_hdrop.py" in stage
    script = Path("scripts/qa_runner_clipboard_cf_hdrop.py").read_text(
        encoding="utf-8"
    )
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    assert 'os.environ.get("RUNNER_TEMP")' in script
    assert "cb.set_clipboard_file" in script
    assert "cb.CF_HDROP" in script
    assert "cb.set_clipboard_text" in script
    assert "guard_seq=before" in script
    assert "clear_runner_clipboard()" in script
    assert "cb.send_ctrl_v" not in script and "cb.send_enter" not in script


def test_hosted_runner_own_window_paste_qa_does_not_send_discord_messages():
    workflow = _workflow(RELEASE_WORKFLOW)
    step = _step(workflow, "QA own-window Win32 Ctrl+V and focus recovery")
    assert "if: github.event_name == 'workflow_dispatch'" in step
    assert "python scripts/qa_runner_owned_target_paste.py" in step
    source = Path("scripts/qa_runner_owned_target_paste.py").read_text(
        encoding="utf-8"
    )
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in source
    assert "IsolatedLibrary" in source
    assert "PickerController" in source
    assert "cb.focus_window(hwnd)" in source
    assert "root = tk.Tk()" in source
    assert "entry.bind" in source
    assert "cb.send_enter = reject_enter" in source
    assert "window.config.get_setting_flag = lambda name: False" in source
    assert "clear_clipboard()" in source
    assert "discord.com" not in source
