import json
import uuid
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rag import CHROMA_PATH
from datetime import datetime

sessionsFile = Path("./sessions.json")

embed_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Sessions Load and Save
def loadSessions():
    if sessionsFile.exists():
        try:
            return json.loads(sessionsFile.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def saveSessions(session: dict):
    sessionsFile.write_text(json.dumps(session, indent=2), encoding="utf-8")

# CRUD Operations
def createSession(name: str):
    session_id = uuid.uuid4().hex[:10]
    collectionName = f"session_{session_id}"
    displayName = name.strip()
    session = {
        "session_id": session_id,
        "collection_name": collectionName,
        "display_name": displayName,
        "created":datetime.now().isoformat(),
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
            from rag import getClient
            client = getClient()
            client.delete_collection(session["collection_name"])
            return
        except Exception:
            print("An error has occurred")
            pass

def addFileSession(session_id: str, filename: str):
    sessions = loadSessions()
    if session_id in sessions:
        if filename not in sessions[session_id]["files"]:
            sessions[session_id]["files"].append(filename)
    saveSessions(sessions)
    return

def removeFileSession(session_id:str, filename: str):
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
    from rag import get_collection
    return get_collection(session["collection_name"])