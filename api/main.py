"""FastAPI layer over the study-assistant backend.

Run with:  uvicorn api.main:app --reload --port 8000
The React dev server proxies /api requests here.
"""
import os
import sys
import tempfile
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import session as sessions
from backend.rag import fileUpload, get_collection
from backend.chat import chatWithAI
from backend.summarize import summarizeDocument
from backend.quiz import generateQuiz, gradeQuiz

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Study Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response models ───────────────────────────────────────────────────

class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class SessionRename(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ChatMessage(BaseModel):
    role: str
    Content: str

class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ChatMessage] = []

class SummarizeRequest(BaseModel):
    detail_level: str = "standard"

class QuizGenerateRequest(BaseModel):
    n_questions: int = Field(default=5, ge=1, le=20)
    question_type: str = "mixed"

class QuizGradeRequest(BaseModel):
    questions: list[dict]
    answers: dict[str, str | None]  # JSON object keys are strings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_or_404(session_id: str) -> dict:
    session = sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Session endpoints ─────────────────────────────────────────────────────────

@app.get("/api/sessions")
def list_sessions():
    return sessions.getSessionsList()

@app.post("/api/sessions", status_code=201)
def create_session(body: SessionCreate):
    return sessions.createSession(body.name)

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return _session_or_404(session_id)

@app.patch("/api/sessions/{session_id}")
def rename_session(session_id: str, body: SessionRename):
    _session_or_404(session_id)
    sessions.updateSessionName(session_id, body.name.strip())
    return sessions.get_session(session_id)

@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    _session_or_404(session_id)
    sessions.deleteSession(session_id)


# ── File endpoints ────────────────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/files", status_code=201)
async def upload_file(session_id: str, file: UploadFile = File(...)):
    session = _session_or_404(session_id)

    if file.filename in session.get("files", []):
        raise HTTPException(status_code=409, detail="File already uploaded in this session")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".pptx"):
        raise HTTPException(status_code=400, detail="File must be in PDF or PPTX format")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        collection = get_collection(session["collection_name"])
        fileUpload(tmp_path, collection)
        sessions.addFileSession(session_id, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)

    return sessions.get_session(session_id)

@app.delete("/api/sessions/{session_id}/files/{filename}")
def remove_file(session_id: str, filename: str):
    session = _session_or_404(session_id)
    if filename not in session.get("files", []):
        raise HTTPException(status_code=404, detail="File not in this session")

    # Remove both the session record and the file's chunks from the index
    collection = get_collection(session["collection_name"])
    try:
        collection.delete(where={"source": filename})
    except Exception:
        logger.exception("Failed to delete chunks for %s", filename)
    sessions.removeFileSession(session_id, filename)
    return sessions.get_session(session_id)


# ── AI endpoints ──────────────────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/chat")
def chat(session_id: str, body: ChatRequest):
    session = _session_or_404(session_id)
    collection = get_collection(session["collection_name"])
    history = [m.model_dump() for m in body.history]
    try:
        answer = chatWithAI(body.question.strip(), history, collection)
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=502, detail=f"Chat failed: {e}")
    return {"answer": answer}

@app.post("/api/sessions/{session_id}/summarize")
def summarize(session_id: str, body: SummarizeRequest):
    session = _session_or_404(session_id)
    if body.detail_level not in ("brief", "standard", "detailed"):
        raise HTTPException(status_code=400, detail="detail_level must be brief, standard, or detailed")
    collection = get_collection(session["collection_name"])
    try:
        return summarizeDocument(collection, body.detail_level)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sessions/{session_id}/quiz/generate")
def quiz_generate(session_id: str, body: QuizGenerateRequest):
    session = _session_or_404(session_id)
    if body.question_type not in ("mixed", "mcq", "short"):
        raise HTTPException(status_code=400, detail="question_type must be mixed, mcq, or short")
    collection = get_collection(session["collection_name"])
    try:
        return {"questions": generateQuiz(collection, body.n_questions, body.question_type)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/api/sessions/{session_id}/quiz/grade")
def quiz_grade(session_id: str, body: QuizGradeRequest):
    _session_or_404(session_id)
    answers = {int(k): v for k, v in body.answers.items()}
    results = gradeQuiz(body.questions, answers)
    score = sum(1 for r in results if r["correct"])
    return {"results": results, "score": score, "total": len(results)}
