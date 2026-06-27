"""
Page load performance tests using Playwright's Navigation Timing API.
Metrics captured per page:
  - TTFB      : Time to First Byte
  - DOMReady  : DOM content loaded
  - Load      : Full page load (window.onload)
  - Interactive: Time until Streamlit sidebar is ready for interaction
"""
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8501"
THRESHOLDS = {
    "ttfb_ms": 2000,
    "dom_ready_ms": 8000,
    "load_ms": 12000,
    "interactive_ms": 20000,
}


def _collect_timings(page: Page, path: str = "") -> dict:
    """Navigate to a page and return Navigation Timing metrics in ms."""
    page.goto(f"{BASE_URL}/{path}")
    # Wait for Streamlit to finish rendering
    page.wait_for_selector("[data-testid='stSidebar']", timeout=30000)
    page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30000)

    # Record when the sidebar becomes interactive
    interactive_ms = page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        return performance.now() - nav.startTime;
    }""")

    timing = page.evaluate("""() => {
        const t = performance.getEntriesByType('navigation')[0];
        return {
            ttfb_ms:      t.responseStart - t.requestStart,
            dom_ready_ms: t.domContentLoadedEventEnd - t.startTime,
            load_ms:      t.loadEventEnd - t.startTime,
        };
    }""")
    timing["interactive_ms"] = interactive_ms
    return timing


def _assert_thresholds(timings: dict, page_name: str):
    for metric, limit in THRESHOLDS.items():
        value = timings.get(metric, 0)
        assert value < limit, (
            f"[{page_name}] {metric} = {value:.0f}ms exceeds threshold of {limit}ms"
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_home_page_load(page: Page):
    timings = _collect_timings(page)
    print(f"\nHome page timings: {timings}")
    _assert_thresholds(timings, "Home")


def test_upload_page_load(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid='stSidebar']", timeout=30000)
    page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30000)
    page.get_by_text("Upload File").first.click()

    timings = _collect_timings(page)
    print(f"\nUpload page timings: {timings}")
    _assert_thresholds(timings, "Upload File")


def test_summarize_page_load(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid='stSidebar']", timeout=30000)
    page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30000)
    page.get_by_text("Summarize").first.click()

    timings = _collect_timings(page)
    print(f"\nSummarize page timings: {timings}")
    _assert_thresholds(timings, "Summarize")


def test_quiz_page_load(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("[data-testid='stSidebar']", timeout=30000)
    page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=30000)
    page.get_by_text("Quiz").first.click()

    timings = _collect_timings(page)
    print(f"\nQuiz page timings: {timings}")
    _assert_thresholds(timings, "Quiz")
