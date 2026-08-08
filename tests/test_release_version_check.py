import subprocess
import sys

import pytest

import check_release_version


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
