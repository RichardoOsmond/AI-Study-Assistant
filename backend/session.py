import json
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from .config import SESSIONS_FILE

# Module-level so tests can patch it; sourced from config for the DATA_DIR seam
sessionsFile = SESSIONS_FILE

# Sessions Load and Save
def loadSessions():
    if sessionsFile.exists():
        try:
            return json.loads(sessionsFile.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Preserve the corrupt file for recovery instead of silently wiping it
            backup = sessionsFile.with_suffix(".json.corrupt")
            logger.warning("sessions.json is corrupt — backing it up to %s", backup)
            try:
                sessionsFile.replace(backup)
            except OSError:
                pass
            return {}
    return {}

def saveSessions(sessions: dict):
    # Atomic write: write to a temp file, then rename over the original,
    # so a crash mid-write can never corrupt sessions.json
    tmp = sessionsFile.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    os.replace(tmp, sessionsFile)

# CRUD Operations
def createSession(name: str):
    session_id = uuid.uuid4().hex[:10]
    collectionName = f"session_{session_id}"
    displayName = name.strip()
    session = {
        "session_id": session_id,
        "collection_name": collectionName,
        "display_name": displayName,
        "created": datetime.now(timezone.utc).isoformat(),
        "files": []
    }

    sessions = loadSessions()
    sessions[session_id] = session
    saveSessions(sessions)
    return session

def get_session(session_id: str):
    return loadSessions().get(session_id)

def updateSessionName(session_id: str, name: str):
    sessions = loadSessions()
    if session_id in sessions:
        sessions[session_id]["display_name"] = name
        saveSessions(sessions)
    return

def deleteSession(session_id: str):
    sessions = loadSessions()
    session = sessions.pop(session_id, None)
    saveSessions(sessions)

    if session:
        try:
            from .rag import getClient
            client = getClient()
            client.delete_collection(session["collection_name"])
        except Exception:
            logger.exception("Failed to delete collection %s", session["collection_name"])

def addFileSession(session_id: str, filename: str):
    sessions = loadSessions()
    if session_id in sessions:
        if filename not in sessions[session_id]["files"]:
            sessions[session_id]["files"].append(filename)
    saveSessions(sessions)
    return

def removeFileSession(session_id: str, filename: str):
    sessions = loadSessions()
    if session_id in sessions:
        if filename in sessions[session_id]["files"]:
            sessions[session_id]["files"].remove(filename)
    saveSessions(sessions)
    return

def getSessionsList():
    sessions = loadSessions()
    return sorted(sessions.values(), key=lambda session: session["created"], reverse=True)

# Get Session Collection
def getSessionCollection(session: dict):
    from .rag import get_collection
    return get_collection(session["collection_name"])
