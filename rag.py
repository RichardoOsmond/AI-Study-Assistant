import fitz
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re
import hashlib
from pathlib import Path
import streamlit as st

CHROMA_PATH = "./chroma_db"
chunkSize = 400
chunkOverlap = 80

# ChromaDB Setup
@st.cache_resource
def getClient():
    return chromadb.PersistentClient(path=CHROMA_PATH)

@st.cache_resource
def getEmbedFunction():
    return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def get_collection(collectionName: str):
    return getClient().get_or_create_collection(
        name = collectionName,
        embedding_function=getEmbedFunction(),
        metadata={"hnsw:space": "cosine"}
    )

# Text Extraction
def extractFromPDF(path: str):
    pages = []
    document = fitz.open(path)
    for i, page in enumerate(document):
        text = page.get_text()
        text = re.sub(r'\s+', ' ', text) # Clean random spaces
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text) # Clean new line that are not a paragraph break
        if text:
            pages.append({"page": i + 1,
                          "text": text})
    return pages

# Work in progress (Finishing up PDF first)
def extractFromPPT(path: str):
    return path

# Overlap Chunking
def textChunk(text: str, source: str, page: int, chunkSize: int = 400, chunkOverlap: int = 80):
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunkSize
        chunk = text[start:end].strip()
        if chunk:
            uid = hashlib.md5(f"{source}:{page}:{idx}".encode()).hexdigest()
            chunks.append({
                "uid": uid,
                "text": chunk,
                "metadata": {
                    "source": source,
                    "page": page,
                    "index": idx
                }
            })
            idx += 1
        start += chunkSize - chunkOverlap
        if end >= len(text):
            break

    return chunks

# Main RAG Pipeline
def fileUpload(filepath: str, collection):
    path = Path(filepath)
    if not path.exists():
        print("File not found")
        raise FileNotFoundError

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages = extractFromPDF(str(path))
    elif suffix in (".pptx", ".ppt"):
        pages = extractFromPPT(str(path))
    else:
        print("File must be in PDF or PPTX format")
        raise ValueError

    if not pages:
        print("No text found")
        return

    all_chunks = []
    for page in pages:
        all_chunks.extend(textChunk(page["text"], path.name, page["page"]))

    collection.upsert(
        ids = [chunk["uid"] for chunk in all_chunks],
        documents = [chunk["text"] for chunk in all_chunks],
        metadatas = [chunk["metadata"] for chunk in all_chunks]
    )

    print(f"{path.name} succesfully uploaded to session collection")