import logging
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults

from .llm import get_llm, requireKey
from .config import RETRIEVAL_K as k
# Chroma cosine distance (0 = identical, 2 = opposite). Above this threshold
# the local match is considered too weak and we fall back to web search.
from .config import DISTANCE_THRESHOLD

logger = logging.getLogger(__name__)

# ── History ───────────────────────────────────────────────────────────────────

def formatHistory(chat_history: list, limit: int = 6) -> str:
    lines = []
    for message in chat_history[-limit:]:
        role = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"{role}: {message['Content']}")
    return "\n".join(lines)

# ── Query rewriting ───────────────────────────────────────────────────────────

def rewriteQuery(question: str, chat_history: list) -> str:
    """Rewrite a follow-up question into a self-contained one for retrieval.

    'why does that happen?' embeds poorly on its own — rewritten with history
    context it becomes something retrievable. Skipped when there is no history.
    """
    if not chat_history:
        return question

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Rewrite the user's question so it is fully self-contained,
using the chat history to resolve references like "it", "that", or "the second one".
Return ONLY the rewritten question, nothing else.
If the question is already self-contained, return it unchanged."""),
        ("human", """Chat History:
{history}

Question: {question}""")
    ])
    chain = prompt | get_llm(max_tokens=150) | StrOutputParser()

    try:
        rewritten = chain.invoke({
            "history": formatHistory(chat_history),
            "question": question
        }).strip()
        return rewritten or question
    except Exception:
        logger.warning("Query rewriting failed; using the original question", exc_info=True)
        return question

# ── Retrieval ─────────────────────────────────────────────────────────────────

def contextRetrieval(query: str, collection, k: int = k):
    """Return (context, best_distance). best_distance is None when nothing is indexed."""
    if collection.count() == 0:
        return "", None

    results = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "distances", "metadatas"],
    )

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = (results.get("metadatas") or [[]])[0] or [{}] * len(documents)
    if not documents:
        return "", None

    # Label each chunk with its origin so the model can cite sources
    labeled = []
    for doc, meta in zip(documents, metadatas):
        meta = meta if isinstance(meta, dict) else {}
        source = meta.get("source", "unknown")
        page = meta.get("page", "?")
        labeled.append(f"[{source}, p.{page}]\n{doc}")

    return "\n\n".join(labeled), min(distances)

# ── Web search fallback ───────────────────────────────────────────────────────

def webSearch(query: str) -> str:
    requireKey("TAVILY_API_KEY")
    tool = TavilySearchResults(max_results=3)
    results = tool.invoke(query)

    parts = []
    for r in results:
        if isinstance(r, dict):
            parts.append(f"[{r.get('url', 'unknown source')}]\n{r.get('content', '')}")
    return "\n\n".join(parts)

# ── Answer generation ─────────────────────────────────────────────────────────

def get_answer_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a knowledgeable and friendly AI Study Assistant.

Rules:
1. Answer based on the provided context.
2. Keep answers clear, concise, and student-friendly.
3. Never make up facts — say "I'm not sure" if the context doesn't cover it.
4. When context passages are labeled like [file, p.N], cite them in your answer,
   e.g. "...as explained in [lecture2.pdf, p.14]".
5. {source_note}"""),
        ("human", """Chat History:
{chat_history}

Question: {question}

Context:
{context}""")
    ])
    return prompt | get_llm() | StrOutputParser()

def chatWithAI(question: str, chat_history: list, collection):
    search_query = rewriteQuery(question, chat_history)
    context, distance = contextRetrieval(search_query, collection)

    # Deterministic routing: strong local match answers locally; otherwise
    # fetch web results directly — no agent loop deciding on every message
    if context and distance is not None and distance <= DISTANCE_THRESHOLD:
        source_note = "The context comes from the student's own study materials."
    else:
        logger.info("Local context weak (distance=%s); falling back to web search", distance)
        context = webSearch(search_query)
        source_note = ("The context comes from a web search, not the student's documents. "
                       "Briefly mention that this answer is based on a web search.")
        if not context:
            context = "No information found."

    chain = get_answer_chain()
    return chain.invoke({
        "question": question,
        "context": context,
        "chat_history": formatHistory(chat_history),
        "source_note": source_note,
    })
