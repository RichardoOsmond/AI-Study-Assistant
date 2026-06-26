import os
import re
import json
import random
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

model = "llama-3.3-70b-versatile"

def get_llm(max_tokens: int = 2048):
    return ChatGroq(
        model=model,
        api_key=os.environ['GROQ_API_KEY'],
        max_tokens=max_tokens
    )


def _parse_json(raw: str) -> list:
    """Strip markdown fences and parse JSON array from LLM output."""
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


# Chains

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

def chunkSelection(collection, n: int = 20) -> str:
    if collection.count() == 0:
        raise FileNotFoundError("No documents uploaded in this session.")
    chunks = collection.get(include=["documents"])["documents"]
    random.shuffle(chunks)
    return "\n\n".join(chunks[:n])


# Core Quiz Functions
def generateQuiz(collection, n_questions: int = 5, question_type: str = "mixed") -> list:
    """Return a list of question dicts ready for the UI."""
    context = chunkSelection(collection)

    type_prompts = {
        "mcq": f"Generate exactly {n_questions} multiple choice questions (MCQ).",
        "short": f"Generate exactly {n_questions} short answer questions.",
        "mixed": f"Generate exactly {n_questions} questions mixing MCQ and short answer evenly.",
    }
    questions_type = type_prompts[question_type]

    chain = get_quiz_chain()
    raw = chain.invoke({"questions_type": questions_type, "context": context}).strip()
    return _parse_json(raw)


def gradeMCQ(question: dict, answer: str) -> dict:
    correct = question["answer"].strip().upper() == answer.strip().upper()
    return {
        "correct": correct,
        "feedback": question.get("explanation", "See the correct answer above.")
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
        return _parse_json(raw)
    except Exception:
        return {"correct": False, "feedback": raw}


def gradeQuiz(questions: list, answers: dict) -> list:
    """Grade all questions. answers = {index: answer_string}. Returns list of result dicts."""
    results = []
    for i, q in enumerate(questions):
        answer = answers.get(i, "").strip()
        if not answer:
            results.append({"correct": False, "feedback": "No answer provided."})
        elif q["type"] == "mcq":
            results.append(gradeMCQ(q, answer))
        else:
            results.append(gradeShort(q, answer))
    return results
