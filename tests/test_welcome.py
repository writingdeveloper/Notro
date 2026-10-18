"""First-run guidance can open the real picker without automatic pasting."""
from notro_app import welcome


def test_first_run_has_explicit_try_picker_and_dismiss_actions():
    html = welcome.build_html("Ctrl+Shift+E")
    assert 'id="try"' in html and 'id="ok"' in html
    assert "api.open_picker()" in html
    assert "Ctrl+Shift+E" in html


def test_try_picker_callback_only_runs_on_user_action():
    called = []
    api = welcome._Api(on_try=lambda: called.append(True))
    api.open_picker()
    assert called == [True]
