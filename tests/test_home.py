from playwright.sync_api import Page, expect


def test_welcome_heading_visible(app: Page):
    """Home page shows the welcome heading on a fresh session."""
    expect(app.get_by_text("Welcome to AI Study Assistant")).to_be_visible()


def test_action_cards_visible(app: Page):
    """All three action cards are rendered on the empty home state."""
    expect(app.get_by_role("button", name="📄 Upload File")).to_be_visible()
    expect(app.get_by_role("button", name="📝 Summarize")).to_be_visible()
    expect(app.get_by_role("button", name="🧠 Quiz")).to_be_visible()


def test_upload_file_card_navigates(app: Page):
    """Clicking Upload File card switches to the Upload File page."""
    app.get_by_role("button", name="📄 Upload File").click()
    app.wait_for_load_state("networkidle")
    expect(app.get_by_text("Upload Study Material")).to_be_visible()


def test_summarize_card_navigates(app: Page):
    """Clicking Summarize card switches to the Summarize page."""
    app.get_by_role("button", name="📝 Summarize").click()
    app.wait_for_load_state("networkidle")
    expect(app.get_by_role("heading", name="Summarize")).to_be_visible()


def test_quiz_card_navigates(app: Page):
    """Clicking Quiz card switches to the Quiz page."""
    app.get_by_role("button", name="🧠 Quiz").click()
    app.wait_for_load_state("networkidle")
    expect(app.get_by_role("heading", name="Quiz")).to_be_visible()


def test_chat_input_visible(app: Page):
    """Chat input is always visible on the Home page."""
    expect(app.get_by_placeholder("Ask a question about your study materials...")).to_be_visible()


def test_sidebar_navigation_visible(app: Page):
    """Sidebar contains all four navigation options."""
    for label in ["Home", "Upload File", "Summarize", "Quiz"]:
        expect(app.get_by_text(label).first).to_be_visible()
