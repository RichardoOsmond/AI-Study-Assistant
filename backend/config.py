import os
from pathlib import Path

# Data directory seam: tests and deployments can point the app at a different
# data location via the STUDY_ASSISTANT_DATA env var without touching code.
DATA_DIR = Path(os.environ.get(
    "STUDY_ASSISTANT_DATA",
    Path(__file__).parent.parent / "data"
))

CHROMA_PATH = str(DATA_DIR / "chroma_db")
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Model / RAG tuning
LLM_MODEL = "llama-3.3-70b-versatile"
EMBED_MODEL = "all-MiniLM-L6-v2"
RETRIEVAL_K = 5
DISTANCE_THRESHOLD = 0.65
CHUNK_MAX_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150
