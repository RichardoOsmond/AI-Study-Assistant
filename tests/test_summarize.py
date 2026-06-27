from playwright.sync_api import Page, expect


def _go_to_summarize(app: Page):
    app.get_by_text("Summarize").first.click()
    app.wait_for_load_state("networkidle")


def test_summarize_page_title(app: Page):
    """Summarize page has the correct title."""
    _go_to_summarize(app)
    expect(app.get_by_role("heading", name="Summarize")).to_be_visible()


def test_summarize_warns_without_files(app: Page):
    """Summarize page shows a warning when no files are uploaded."""
    _go_to_summarize(app)
    expect(app.get_by_text("No files uploaded yet")).to_be_visible()


def test_summarize_generate_button_hidden_without_files(app: Page):
    """Generate Summary button is not shown when no files are uploaded."""
    _go_to_summarize(app)
    expect(app.get_by_role("button", name="✨ Generate Summary")).not_to_be_visible()
