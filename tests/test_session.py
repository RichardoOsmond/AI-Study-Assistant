"""
Unit tests for session CRUD in backend/session.py.
All tests use a temporary sessions.json so they never touch the real data file.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import backend.session as session_module


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path):
    """Redirect sessionsFile to a temp path for every test."""
    tmp_file = tmp_path / "sessions.json"
    with patch.object(session_module, "sessionsFile", tmp_file):
        yield tmp_file


# Create Session
def test_create_session_returns_dict():
    s = session_module.createSession("Test Session")
    assert isinstance(s, dict)


def test_create_session_has_required_keys():
    s = session_module.createSession("Test Session")
    for key in ("session_id", "collection_name", "display_name", "created", "files"):
        assert key in s


def test_create_session_display_name():
    s = session_module.createSession("  My Notes  ")
    assert s["display_name"] == "My Notes"


def test_create_session_empty_files():
    s = session_module.createSession("Test")
    assert s["files"] == []


def test_create_session_collection_name_format():
    s = session_module.createSession("Test")
    assert s["collection_name"].startswith("session_")


def test_create_session_unique_ids():
    s1 = session_module.createSession("A")
    s2 = session_module.createSession("B")
    assert s1["session_id"] != s2["session_id"]


def test_create_session_persisted():
    s = session_module.createSession("Persisted")
    sessions = session_module.loadSessions()
    assert s["session_id"] in sessions


# Get Session List
def test_get_sessions_list_empty():
    assert session_module.getSessionsList() == []


def test_get_sessions_list_returns_all():
    session_module.createSession("A")
    session_module.createSession("B")
    session_module.createSession("C")
    assert len(session_module.getSessionsList()) == 3


def test_get_sessions_list_sorted_newest_first():
    import time
    session_module.createSession("First")
    time.sleep(0.01)
    session_module.createSession("Second")
    sessions = session_module.getSessionsList()
    assert sessions[0]["display_name"] == "Second"


# Get Session
def test_get_session_returns_correct():
    s = session_module.createSession("Lookup")
    result = session_module.get_session(s["session_id"])
    assert result["display_name"] == "Lookup"


def test_get_session_missing_returns_none():
    assert session_module.get_session("nonexistent_id") is None


# Add File to Session
def test_add_file_session():
    s = session_module.createSession("File Test")
    session_module.addFileSession(s["session_id"], "lecture.pdf")
    updated = session_module.get_session(s["session_id"])
    assert "lecture.pdf" in updated["files"]


def test_add_file_session_no_duplicates():
    s = session_module.createSession("File Test")
    session_module.addFileSession(s["session_id"], "lecture.pdf")
    session_module.addFileSession(s["session_id"], "lecture.pdf")
    updated = session_module.get_session(s["session_id"])
    assert updated["files"].count("lecture.pdf") == 1


# Delete Session
def test_delete_session_removes_it():
    s = session_module.createSession("To Delete")
    session_module.deleteSession(s["session_id"])
    assert session_module.get_session(s["session_id"]) is None


def test_delete_session_others_unaffected():
    s1 = session_module.createSession("Keep")
    s2 = session_module.createSession("Delete")
    session_module.deleteSession(s2["session_id"])
    assert session_module.get_session(s1["session_id"]) is not None


# Update Session Name
def test_update_session_name():
    s = session_module.createSession("Old Name")
    session_module.updateSessionName(s["session_id"], "New Name")
    updated = session_module.get_session(s["session_id"])
    assert updated["display_name"] == "New Name"
