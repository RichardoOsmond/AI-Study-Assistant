"""
Playwright UI tests for the Manage session expander (rename / delete).
Requires the Streamlit server to be running (handled by conftest.py).
"""
import uuid
from playwright.sync_api import Page, expect


def _wait_idle(app: Page):
    # Give the rerun a moment to start before waiting for it to finish —
    # otherwise the "spinner hidden" check can pass before the rerun begins
    # and the next click gets swallowed by the re-render
    app.wait_for_timeout(400)
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    app.wait_for_timeout(200)


def _open_manage(app: Page):
    # The expander keeps its open state across Streamlit reruns —
    # only click the header when it's actually collapsed
    rename_input = app.get_by_label("Rename session")
    if not rename_input.is_visible():
        app.get_by_text("Manage session").click()
        rename_input.wait_for(timeout=10000)


def test_manage_expander_visible(app: Page):
    """The Manage session expander is present in the sidebar."""
    expect(app.get_by_text("Manage session")).to_be_visible()


def test_rename_session(app: Page):
    """Renaming the active session updates the session selector."""
    unique = f"Renamed {uuid.uuid4().hex[:6]}"

    _open_manage(app)
    rename_input = app.get_by_label("Rename session")
    rename_input.fill(unique)
    rename_input.press("Enter")
    _wait_idle(app)

    _open_manage(app)
    app.get_by_role("button", name="✏️ Rename").click()
    _wait_idle(app)

    expect(app.locator("[data-testid='stSelectbox']").get_by_text(unique)).to_be_visible()


def test_delete_shows_confirmation(app: Page):
    """Clicking Delete session asks for confirmation instead of deleting immediately."""
    _open_manage(app)
    app.get_by_role("button", name="🗑️ Delete session").click()
    _wait_idle(app)

    expect(app.get_by_role("button", name="✅ Confirm")).to_be_visible()
    expect(app.get_by_role("button", name="❌ Cancel")).to_be_visible()


def test_delete_cancel(app: Page):
    """Cancel dismisses the confirmation without deleting."""
    _open_manage(app)
    app.get_by_role("button", name="🗑️ Delete session").click()
    _wait_idle(app)
    app.get_by_role("button", name="❌ Cancel").click()
    _wait_idle(app)

    expect(app.get_by_role("button", name="✅ Confirm")).not_to_be_visible()


def test_delete_session_removes_it(app: Page):
    """Deleting a session removes it from the selector."""
    # Create a fresh session and give it a unique name so we can track it
    app.get_by_role("button", name="＋ New").click()
    _wait_idle(app)

    unique = f"ToDelete {uuid.uuid4().hex[:6]}"
    _open_manage(app)
    rename_input = app.get_by_label("Rename session")
    rename_input.fill(unique)
    rename_input.press("Enter")
    _wait_idle(app)

    _open_manage(app)
    app.get_by_role("button", name="✏️ Rename").click()
    _wait_idle(app)
    expect(app.locator("[data-testid='stSelectbox']").get_by_text(unique)).to_be_visible()

    # Delete it with confirmation
    _open_manage(app)
    app.get_by_role("button", name="🗑️ Delete session").click()
    _wait_idle(app)
    app.get_by_role("button", name="✅ Confirm").click()
    _wait_idle(app)

    # The deleted session must no longer be the one shown in the selector
    expect(app.locator("[data-testid='stSelectbox']").get_by_text(unique)).not_to_be_visible()
