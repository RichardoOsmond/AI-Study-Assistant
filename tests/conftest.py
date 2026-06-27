import subprocess
import time
import socket
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

ROOT = Path(__file__).parent.parent
APP = ROOT / "frontend" / "main.py"
BASE_URL = "http://localhost:8501"


def _wait_for_port(host: str, port: int, timeout: float = 30):
    """
    Block until the TCP port is accepting connections.
    Using a 30 seconds timeout timer.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout}s")


@pytest.fixture(scope="session", autouse=True)
def streamlit_server():
    """Start the Streamlit app once for the whole test session."""
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    proc = subprocess.Popen(
        [str(python), "-m", "streamlit", "run", str(APP),
         "--server.headless", "true",
         "--server.port", "8501"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_port("localhost", 8501, timeout=30)
    time.sleep(6)  # extra buffer for Streamlit to finish initializing
    yield
    proc.terminate()


@pytest.fixture
def app(page: Page):
    """Navigate to the app and wait for it to fully load."""
    for attempt in range(2):
        page.goto(BASE_URL)
        try:
            page.wait_for_selector("[data-testid='stSidebar']", timeout=20000)
            # Wait for Streamlit's "Running…" spinner to disappear
            page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=20000)
            return page
        except Exception:
            if attempt == 1:
                raise
            time.sleep(4)
    return page
