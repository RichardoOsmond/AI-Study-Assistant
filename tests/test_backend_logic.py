"""
Unit tests for the pure-logic parts of the backend that were fixed:
- chat history formatting (the 'Role' KeyError bug)
- quiz question normalization and MCQ grading robustness
- JSON parsing of LLM output
No LLM calls, no network, no Streamlit.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.chat import formatHistory, rewriteQuery, contextRetrieval
from backend.rag import textChunk, _splitSentences
from backend.quiz import (
    _parse_json,
    _normalize_answer_key,
    _normalizeQuestions,
    _normalizeGradeResult,
    chunkSelection,
    gradeMCQ,
    gradeQuiz,
)


# ── formatHistory (regression for the 'Role' KeyError bug) ────────────────────

def test_format_history_lowercase_role_keys():
    """History stored with lowercase 'role' keys must not raise KeyError."""
    history = [
        {"role": "user", "Content": "What is AI?"},
        {"role": "assistant", "Content": "AI is..."},
    ]
    result = formatHistory(history)
    assert "User: What is AI?" in result
    assert "Assistant: AI is..." in result


def test_format_history_empty():
    assert formatHistory([]) == ""


def test_format_history_respects_limit():
    history = [{"role": "user", "Content": f"msg {i}"} for i in range(10)]
    result = formatHistory(history, limit=6)
    assert "msg 3" not in result
    assert "msg 4" in result
    assert "msg 9" in result


# ── _normalize_answer_key ─────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("A", "A"),
    ("a", "A"),
    (" B ", "B"),
    ("c.", "C"),
    ("D)", "D"),
    ("Answer: A", "A"),
    ("", ""),
    (None, ""),
])
def test_normalize_answer_key(raw, expected):
    assert _normalize_answer_key(raw) == expected


# ── _normalizeQuestions ───────────────────────────────────────────────────────

def _mcq(answer="A"):
    return {
        "type": "mcq",
        "question": "Q?",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "answer": answer,
        "explanation": "because",
    }


def test_normalize_keeps_valid_mcq():
    assert len(_normalizeQuestions([_mcq()])) == 1


def test_normalize_fixes_messy_answer_key():
    result = _normalizeQuestions([_mcq(answer="a.")])
    assert result[0]["answer"] == "A"


def test_normalize_drops_mcq_with_invalid_answer():
    """Answer key that is not one of the options is dropped, not crashed on."""
    assert _normalizeQuestions([_mcq(answer="Z")]) == []


def test_normalize_drops_non_dict_entries():
    assert _normalizeQuestions(["garbage", 42, None]) == []


def test_normalize_drops_missing_question():
    assert _normalizeQuestions([{"type": "mcq", "options": {"A": "1"}, "answer": "A"}]) == []


def test_normalize_short_defaults_key_points():
    q = {"type": "short", "question": "Q?", "model_answer": "A."}
    result = _normalizeQuestions([q])
    assert result[0]["key_points"] == []


def test_normalize_non_list_input():
    assert _normalizeQuestions({"not": "a list"}) == []


# ── gradeMCQ ──────────────────────────────────────────────────────────────────

def test_grade_mcq_correct():
    assert gradeMCQ(_mcq(), "A")["correct"] is True


def test_grade_mcq_incorrect():
    assert gradeMCQ(_mcq(), "B")["correct"] is False


def test_grade_mcq_case_and_punctuation_insensitive():
    assert gradeMCQ(_mcq(), "a.")["correct"] is True


def test_grade_mcq_includes_explanation():
    assert gradeMCQ(_mcq(), "A")["feedback"] == "because"


# ── gradeQuiz ─────────────────────────────────────────────────────────────────

def test_grade_quiz_unanswered_mcq():
    """A skipped MCQ (None from st.radio with index=None) is 'No answer provided'."""
    results = gradeQuiz([_mcq()], {0: None})
    assert results[0]["correct"] is False
    assert results[0]["feedback"] == "No answer provided."


def test_grade_quiz_missing_index():
    results = gradeQuiz([_mcq()], {})
    assert results[0]["correct"] is False


def test_grade_quiz_mixed_answers():
    questions = [_mcq(), _mcq(answer="B")]
    results = gradeQuiz(questions, {0: "A", 1: "C"})
    assert results[0]["correct"] is True
    assert results[1]["correct"] is False


# ── _parse_json ───────────────────────────────────────────────────────────────

def test_parse_json_clean_array():
    assert _parse_json('[{"a": 1}]') == [{"a": 1}]


def test_parse_json_with_fences():
    assert _parse_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]


def test_parse_json_object():
    assert _parse_json('{"correct": true, "feedback": "ok"}') == {"correct": True, "feedback": "ok"}


def test_parse_json_invalid_raises():
    with pytest.raises(Exception):
        _parse_json("not json at all")


# ── Sentence-aware chunking ───────────────────────────────────────────────────

SENTENCES_TEXT = ("Artificial intelligence is a field of computer science. "
                  "It focuses on building intelligent systems. "
                  "Machine learning is a major subfield of AI. "
                  "Deep learning uses neural networks with many layers. ") * 10


def test_chunk_respects_max_size():
    chunks = textChunk(SENTENCES_TEXT, "test.pdf", 1, maxChars=500)
    for chunk in chunks:
        # Small tolerance: overlap sentences + joins can push slightly past max
        assert len(chunk["text"]) <= 500 + 200


def test_chunks_end_on_sentence_boundaries():
    chunks = textChunk(SENTENCES_TEXT, "test.pdf", 1, maxChars=500)
    for chunk in chunks[:-1]:
        assert chunk["text"].rstrip().endswith((".", "!", "?"))


def test_chunk_no_mid_sentence_cuts():
    """Every sentence must appear whole in at least one chunk."""
    chunks = textChunk(SENTENCES_TEXT, "test.pdf", 1, maxChars=500)
    joined = " ".join(c["text"] for c in chunks)
    assert "Artificial intelligence is a field of computer science." in joined
    assert "Deep learning uses neural networks with many layers." in joined


def test_chunk_title_prefix():
    chunks = textChunk("Some content about backpropagation.", "deck.pptx", 3,
                       title="Neural Networks")
    assert chunks[0]["text"].startswith("Neural Networks: ")


def test_chunk_no_title_no_prefix():
    chunks = textChunk("Some content.", "doc.pdf", 1)
    assert not chunks[0]["text"].startswith(": ")


def test_chunk_handles_unpunctuated_text():
    """Text with no sentence punctuation (e.g. slide bullets) must still chunk."""
    text = "word " * 500  # 2500 chars, no punctuation
    chunks = textChunk(text.strip(), "deck.pptx", 1, maxChars=1000)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk["text"]) <= 1200


def test_chunk_keeps_uid_and_metadata_format():
    chunks = textChunk(SENTENCES_TEXT, "test.pdf", 4, maxChars=500)
    for i, chunk in enumerate(chunks):
        assert chunk["metadata"] == {"source": "test.pdf", "page": 4, "index": i}
        assert len(chunk["uid"]) == 32


def test_split_sentences_hard_splits_long_ones():
    long_sentence = "a" * 2500
    parts = _splitSentences(long_sentence, maxChars=1000)
    assert all(len(p) <= 1000 for p in parts)
    assert sum(len(p) for p in parts) == 2500


# ── Page-based chunk selection ────────────────────────────────────────────────

def _mock_collection_with_pages():
    collection = MagicMock()
    collection.count.return_value = 6
    collection.get.return_value = {
        "documents": ["p1-c0", "p1-c1", "p2-c0", "p2-c1", "p3-c0", "p3-c1"],
        "metadatas": [
            {"source": "a.pdf", "page": 1, "index": 0},
            {"source": "a.pdf", "page": 1, "index": 1},
            {"source": "a.pdf", "page": 2, "index": 0},
            {"source": "a.pdf", "page": 2, "index": 1},
            {"source": "a.pdf", "page": 3, "index": 0},
            {"source": "a.pdf", "page": 3, "index": 1},
        ],
    }
    return collection


def test_chunk_selection_keeps_pages_contiguous():
    """Chunks from the same page stay together and in reading order."""
    result = chunkSelection(_mock_collection_with_pages(), n=6)
    parts = result.split("\n\n")
    # Wherever a page starts, its second chunk must come right after its first
    for page in ("p1", "p2", "p3"):
        idx0 = parts.index(f"{page}-c0")
        assert parts[idx0 + 1] == f"{page}-c1"


def test_chunk_selection_respects_limit():
    result = chunkSelection(_mock_collection_with_pages(), n=3)
    assert len(result.split("\n\n")) == 3


def test_chunk_selection_works_without_metadata():
    """Collections mocked without metadatas (or None entries) must not crash."""
    collection = MagicMock()
    collection.count.return_value = 2
    collection.get.return_value = {"documents": ["c1", "c2"], "metadatas": None}
    result = chunkSelection(collection, n=2)
    assert "c1" in result and "c2" in result


def test_chunk_selection_empty_collection_raises():
    collection = MagicMock()
    collection.count.return_value = 0
    with pytest.raises(FileNotFoundError):
        chunkSelection(collection, n=5)


# ── Grade result normalization ────────────────────────────────────────────────

def test_normalize_grade_result_dict():
    result = _normalizeGradeResult({"correct": True, "feedback": "Good"})
    assert result == {"correct": True, "feedback": "Good"}


def test_normalize_grade_result_wrapped_in_list():
    result = _normalizeGradeResult([{"correct": True, "feedback": "ok"}])
    assert result["correct"] is True


def test_normalize_grade_result_garbage():
    result = _normalizeGradeResult("not a dict")
    assert result == {"correct": False, "feedback": "No feedback provided."}


def test_normalize_grade_result_missing_keys():
    result = _normalizeGradeResult({})
    assert result["correct"] is False
    assert result["feedback"] == "No feedback provided."


# ── gradeQuiz batching ────────────────────────────────────────────────────────

def _short(question="Explain X."):
    return {"type": "short", "question": question, "model_answer": "X is...", "key_points": []}


def test_grade_quiz_batches_short_answers():
    """All short answers go to gradeShortBatch in ONE call, results map back correctly."""
    questions = [_mcq(), _short("Q one?"), _mcq(answer="B"), _short("Q two?")]
    answers = {0: "A", 1: "answer one", 2: "B", 3: "answer two"}

    batch_results = [
        {"correct": True, "feedback": "first"},
        {"correct": False, "feedback": "second"},
    ]
    with patch("backend.quiz.gradeShortBatch", return_value=batch_results) as mock_batch:
        results = gradeQuiz(questions, answers)

    mock_batch.assert_called_once()
    items = mock_batch.call_args[0][0]
    assert len(items) == 2
    assert items[0][1] == "answer one"

    assert results[0]["correct"] is True        # MCQ correct
    assert results[1]["feedback"] == "first"    # 1st short result → index 1
    assert results[2]["correct"] is True        # MCQ correct
    assert results[3]["feedback"] == "second"   # 2nd short result → index 3


def test_grade_quiz_unanswered_short_not_sent_to_batch():
    questions = [_short()]
    with patch("backend.quiz.gradeShortBatch", return_value=[]) as mock_batch:
        results = gradeQuiz(questions, {0: ""})
    assert mock_batch.call_args[0][0] == []
    assert results[0]["feedback"] == "No answer provided."


# ── Chat routing logic ────────────────────────────────────────────────────────

def test_rewrite_query_no_history_passthrough():
    """With no history there's nothing to resolve — no LLM call is made."""
    assert rewriteQuery("What is AI?", []) == "What is AI?"


def test_context_retrieval_empty_collection():
    collection = MagicMock()
    collection.count.return_value = 0
    context, distance = contextRetrieval("query", collection)
    assert context == ""
    assert distance is None


def test_context_retrieval_returns_best_distance():
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        "documents": [["chunk a", "chunk b"]],
        "distances": [[0.42, 0.71]],
    }
    context, distance = contextRetrieval("query", collection)
    assert "chunk a" in context and "chunk b" in context
    assert distance == 0.42


def test_context_retrieval_labels_chunks_with_citations():
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        "documents": [["chunk a", "chunk b"]],
        "distances": [[0.3, 0.5]],
        "metadatas": [[{"source": "lec2.pdf", "page": 14}, {"source": "deck.pptx", "page": 3}]],
    }
    context, _ = contextRetrieval("query", collection)
    assert "[lec2.pdf, p.14]" in context
    assert "[deck.pptx, p.3]" in context


def test_context_retrieval_survives_missing_metadata():
    collection = MagicMock()
    collection.count.return_value = 5
    collection.query.return_value = {
        "documents": [["chunk a"]],
        "distances": [[0.4]],
        "metadatas": [[None]],
    }
    context, _ = contextRetrieval("query", collection)
    assert "[unknown, p.?]" in context
