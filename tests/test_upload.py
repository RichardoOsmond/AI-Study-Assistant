from playwright.sync_api import Page, expect


def _go_to_upload(app: Page):
    app.get_by_text("Upload File").first.click()
    app.wait_for_load_state("networkidle")


def test_upload_page_title(app: Page):
    """Upload File page has the correct title."""
    _go_to_upload(app)
    expect(app.get_by_text("Upload Study Material")).to_be_visible()


def test_upload_file_input_visible(app: Page):
    """File uploader widget is rendered on the Upload File page."""
    _go_to_upload(app)
    expect(app.get_by_text("Upload a PDF file")).to_be_visible()


def test_no_process_button_without_file(app: Page):
    """Process File button is not shown when no file is selected."""
    _go_to_upload(app)
    expect(app.get_by_role("button", name="📥 Process File")).not_to_be_visible()
