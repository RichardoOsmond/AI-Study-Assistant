from playwright.sync_api import Page, expect


def _go_to_quiz(app: Page):
    app.get_by_text("Quiz").first.click()
    app.wait_for_load_state("networkidle")


def test_quiz_page_title(app: Page):
    """Quiz page has the correct title."""
    _go_to_quiz(app)
    expect(app.get_by_role("heading", name="Quiz")).to_be_visible()


def test_quiz_warns_without_files(app: Page):
    """Quiz page shows a warning when no files are uploaded."""
    _go_to_quiz(app)
    expect(app.get_by_text("No files uploaded yet")).to_be_visible()


def test_quiz_generate_button_hidden_without_files(app: Page):
    """Generate Quiz button is not shown when no files are uploaded."""
    _go_to_quiz(app)
    expect(app.get_by_role("button", name="🎲 Generate Quiz")).not_to_be_visible()
