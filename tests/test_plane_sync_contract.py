"""Plane sync is repeatable across sessions without resetting human QA states."""
from scripts.plane_sync import sync_payload


def test_existing_plane_issue_preserves_status_priority_and_owner():
    result = sync_payload(
        "QA", "<p>new evidence</p>", "a-plane-state-uuid",
        "urgent", exists=True,
    )
    assert result == {"description_html": "<p>new evidence</p>"}
    assert "state" not in result
    assert "priority" not in result
    assert "name" not in result


def test_new_plane_issue_starts_in_desired_state():
    result = sync_payload(
        "Independent WebView QA", "<p>verified</p>", "done-state",
        "high", exists=False,
    )
    assert result == {
        "name": "Independent WebView QA",
        "state": "done-state",
        "priority": "high",
        "description_html": "<p>verified</p>",
    }
