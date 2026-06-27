"""
Playwright UI tests for the New Session button in the sidebar.
Requires the Streamlit server to be running (handled by conftest.py).
"""
from playwright.sync_api import Page, expect


def test_new_session_button_visible(app: Page):
    """The '＋ New' button is visible in the sidebar."""
    expect(app.get_by_role("button", name="＋ New")).to_be_visible()


def test_new_session_button_creates_session(app: Page):
    """Clicking '＋ New' switches to a fresh session showing the welcome screen."""
    app.get_by_role("button", name="＋ New").click()
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    expect(app.get_by_text("Welcome to AI Study Assistant")).to_be_visible()


def test_new_session_shows_action_cards(app: Page):
    """A newly created session shows all three action cards."""
    app.get_by_role("button", name="＋ New").click()
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    expect(app.get_by_role("button", name="📄 Upload File")).to_be_visible()
    expect(app.get_by_role("button", name="📝 Summarize")).to_be_visible()
    expect(app.get_by_role("button", name="🧠 Quiz")).to_be_visible()


def test_new_session_appears_in_selector(app: Page):
    """After creating a new session, the selectbox shows it as the active session."""
    app.get_by_role("button", name="＋ New").click()
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    expect(app.locator("[data-testid='stSelectbox']").get_by_text("New Study Session")).to_be_visible()


def test_multiple_new_sessions(app: Page):
    """Creating two sessions back-to-back both work correctly."""
    app.get_by_role("button", name="＋ New").click()
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    expect(app.get_by_text("Welcome to AI Study Assistant")).to_be_visible()

    app.get_by_role("button", name="＋ New").click()
    app.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
    expect(app.get_by_text("Welcome to AI Study Assistant")).to_be_visible()
