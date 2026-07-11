import re
import json
import random
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm import get_llm


def _parse_json(raw: str):
    """Strip markdown fences and parse JSON (array or object) from LLM output."""
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


def _normalize_answer_key(answer) -> str:
    """Reduce an LLM answer like 'a.', ' B ', or 'C)' to a single uppercase letter."""
    if answer is None:
        return ""
    return re.sub(r"[^A-Za-z]", "", str(answer))[:1].upper()


def _normalizeQuestions(questions) -> list:
    """Validate and normalize LLM-generated questions, dropping malformed ones."""
    if not isinstance(questions, list):
        return []

    valid = []
    for q in questions:
        if not isinstance(q, dict) or "question" not in q:
            continue

        qtype = str(q.get("type", "")).lower()
        if qtype == "mcq" and isinstance(q.get("options"), dict):
            answer = _normalize_answer_key(q.get("answer", ""))
            if answer in q["options"]:
                q["type"] = "mcq"
                q["answer"] = answer
                valid.append(q)
        elif qtype == "short" and "model_answer" in q:
            q["type"] = "short"
            q.setdefault("key_points", [])
            valid.append(q)

    return valid


# ── Chains ────────────────────────────────────────────────────────────────────

def get_quiz_chain():
    quizPrompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert academic quiz writer.
Generate quiz questions based ONLY on the provided study material.
Return a valid JSON array with no extra text, no markdown fences.

Each MCQ object:
{{"type":"mcq","question":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"answer":"A","explanation":"..."}}

Each short answer object:
{{"type":"short","question":"...","model_answer":"...","key_points":["point1","point2"]}}"""),
        ("human", """{questions_type}

Study Material (use ONLY this):
{context}

Return a valid JSON array with no extra text.""")
    ])
    return quizPrompt | get_llm() | StrOutputParser()


def get_grading_chain():
    gradePrompt = ChatPromptTemplate.from_messages([
        ("system", """You are an academic quiz grader. Be fair and concise.
Return a single JSON object with no extra text:
{{"correct": true or false, "feedback": "one sentence feedback"}}"""),
        ("human", """Question: {question}
Model Answer: {model_answer}
Key Points: {key_points}
Student's Answer: {answer}

Return a single JSON object with no extra text.""")
    ])
    return gradePrompt | get_llm(max_tokens=300) | StrOutputParser()


def get_batch_grading_chain():
    gradePrompt = ChatPromptTemplate.from_messages([
        ("system", """You are an academic quiz grader. Be fair and concise.
You will receive {count} numbered items. Grade each one.
Return a JSON array of exactly {count} objects, in the same order as the items,
with no extra text:
[{{"correct": true or false, "feedback": "one sentence feedback"}}, ...]"""),
        ("human", """{items}

Return a JSON array of exactly {count} objects with no extra text.""")
    ])
    return gradePrompt | get_llm(max_tokens=1500) | StrOutputParser()


# ── Helpers ───────────────────────────────────────────────────────────────────

def chunkSelection(collection, n: int = 20) -> str:
    """Select up to n chunks grouped by page, in reading order within each page.

    Sampling whole pages (instead of shuffling individual chunks) gives the
    quiz writer coherent passages rather than disconnected fragments.
    """
    if collection.count() == 0:
        raise FileNotFoundError("No documents uploaded in this session.")

    data = collection.get(include=["documents", "metadatas"])
    documents = data["documents"]
    metadatas = data.get("metadatas") or [{}] * len(documents)

    # Group chunks by (source, page), keeping their in-page order
    pages = {}
    for doc, meta in zip(documents, metadatas):
        meta = meta if isinstance(meta, dict) else {}
        key = (meta.get("source", ""), meta.get("page", 0))
        pages.setdefault(key, []).append((meta.get("index", 0), doc))

    page_keys = list(pages.keys())
    random.shuffle(page_keys)

    selected = []
    for key in page_keys:
        selected.extend(doc for _, doc in sorted(pages[key]))
        if len(selected) >= n:
            break

    return "\n\n".join(selected[:n])


# ── Core functions ────────────────────────────────────────────────────────────

def generateQuiz(collection, n_questions: int = 5, question_type: str = "mixed") -> list:
    """Return a list of validated question dicts ready for the UI."""
    context = chunkSelection(collection)

    type_prompts = {
        "mcq": f"Generate exactly {n_questions} multiple choice questions (MCQ).",
        "short": f"Generate exactly {n_questions} short answer questions.",
        "mixed": f"Generate exactly {n_questions} questions mixing MCQ and short answer evenly.",
    }
    questions_type = type_prompts[question_type]

    chain = get_quiz_chain()
    raw = chain.invoke({"questions_type": questions_type, "context": context}).strip()
    questions = _normalizeQuestions(_parse_json(raw))

    if not questions:
        raise ValueError("The AI did not return any valid questions. Please try again.")
    return questions


def gradeMCQ(question: dict, answer: str) -> dict:
    correct = _normalize_answer_key(question["answer"]) == _normalize_answer_key(answer)
    return {
        "correct": correct,
        "feedback": question.get("explanation", "See the correct answer above.")
    }


def _normalizeGradeResult(result) -> dict:
    """Always hand the UI a dict with guaranteed 'correct' and 'feedback' keys."""
    if isinstance(result, list):
        result = result[0] if result and isinstance(result[0], dict) else {}
    if not isinstance(result, dict):
        result = {}
    return {
        "correct": bool(result.get("correct", False)),
        "feedback": str(result.get("feedback", "")) or "No feedback provided."
    }


def gradeShort(question: dict, answer: str) -> dict:
    chain = get_grading_chain()
    raw = chain.invoke({
        "question": question["question"],
        "model_answer": question["model_answer"],
        "key_points": ", ".join(question.get("key_points", [])),
        "answer": answer,
    }).strip()

    try:
        result = _parse_json(raw)
    except Exception:
        return {"correct": False, "feedback": raw}

    return _normalizeGradeResult(result)


def gradeShortBatch(items: list) -> list:
    """Grade all short answers in a single LLM call. items = [(question, answer), ...].

    One call instead of one per question — grading a 10-question quiz goes
    from 10 sequential round-trips to 1. Falls back to per-question grading
    if the batch response doesn't line up.
    """
    if not items:
        return []

    numbered = []
    for j, (q, answer) in enumerate(items, 1):
        numbered.append(
            f"Item {j}:\n"
            f"Question: {q['question']}\n"
            f"Model Answer: {q['model_answer']}\n"
            f"Key Points: {', '.join(q.get('key_points', []))}\n"
            f"Student's Answer: {answer}"
        )

    chain = get_batch_grading_chain()
    raw = chain.invoke({"items": "\n\n".join(numbered), "count": len(items)}).strip()

    try:
        parsed = _parse_json(raw)
    except Exception:
        parsed = None

    if isinstance(parsed, list) and len(parsed) == len(items):
        return [_normalizeGradeResult(r) for r in parsed]

    # Batch response was malformed — grade individually as a fallback
    return [gradeShort(q, answer) for q, answer in items]


def gradeQuiz(questions: list, answers: dict) -> list:
    """Grade all questions. answers = {index: answer_string}. Returns list of result dicts."""
    results = [None] * len(questions)
    short_items = []
    short_indices = []

    for i, q in enumerate(questions):
        answer = (answers.get(i) or "").strip()
        if not answer:
            results[i] = {"correct": False, "feedback": "No answer provided."}
        elif q["type"] == "mcq":
            results[i] = gradeMCQ(q, answer)
        else:
            short_items.append((q, answer))
            short_indices.append(i)

    for i, result in zip(short_indices, gradeShortBatch(short_items)):
        results[i] = result

    return results
