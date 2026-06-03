import os
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

# Get Chain
def get_quiz_chain():
    quizPrompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert academic quiz writer.
        Generate quiz questions based only on the provided study material.
        Return a valid JSON array with no extra text.
        
        Each MCQ object:
        {{"type":"mcq","question":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"answer":"A","explanation":"..."}}
        
        Each short answer object:
        {{"type":"short","question":"...","model_answer":"...","key_points":["point1","point2"]}}"""),
        ("human", """{questions_type}
        
        Study Material (Use ONLY this for question generation)
        {context}
        
        Return a valid JSON array with no extra text.""")
    ])
    return quizPrompt | get_llm() | StrOutputParser()

def get_grading_chain(): # Change Prompt Template
    gradePrompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert academic quiz grader. Be fair, precise, and concise.
        Return a valid JSON array with no extra text.
        The JSON array should contain the given JSON array, added with a True or False under the 'correct' key and a feedback under the 'feedback' key."""),
        ("human", """Question: {question}
        Model Answer: {model_answer}
        Key Points: {keypoints}
        Student's Answer: {answer}
        Return a valid JSON array with no extra text, replacing the none under the 'correct' key with True or False and 'feedback' key with your feedback""")
    ])
    return gradePrompt | get_llm(max_tokens=500) | StrOutputParser()

# Select Random Chunks
def chunkSelection(collection, n: int = 20):
    if collection.count() == 0:
        print("No file found in this session")
        return
    chunks = collection.get(include=["text"])["text"]
    random.shuffle(chunks)
    selectedChunks = chunks[:n]
    return "\n\n".join(selectedChunks)

# Quiz Generation
def quizGeneration(chunks: str, n_questions: int, question_type: str):
    question_types = {
        "mcq": f"Generate {n_questions} multiple choice questions (MCQ).",
        "short-answer": f"Generate {n_questions} short answer questions.",
        "mixed": f"Generate {n_questions} mixed questions of multiple choice questions (MCQ) and short answer questions."
    }
    selectedType = question_types[question_type]

    chain = get_quiz_chain()
    rawResponse = chain.invoke({"questions_type": selectedType, "context": chunks}).strip()

    return rawResponse

# Grading
def mcq_grading(question: dict, answer: str):
    if question["answer"].lower() == answer.lower():
        return True
    return False

def short_grading(question:str, model_answer: str, keypoints: list, answer: str):
    chain = get_grading_chain()
    response = chain.invoke({"question": question,
                  "model_answer": model_answer,
                  "keypoints": keypoints,
                  "answer": answer})

    lines = response.split("\n")
    feedback = response[1] if len(lines) > 1 else ""
    if lines[0].lower == "correct":
        return "correct", feedback
    return "incorrect", feedback

# Main Quiz Pipeline
def runQuiz(collection, n_questions: int = 5, question_type: str = "mixed"):
    context = chunkSelection(collection)
    if not context:
        print("No file found in current session. Can't generate quiz.")
        raise FileNotFoundError

    try:
        questions = quizGeneration(context, n_questions, question_type)
    except Exception:
        print("An error has occurred")
        return

    if not questions:
        print("No questions generated")
        return

    score = 0
    total = len(questions)

    for i, q in enumerate(questions):
        if q["type"].lower() == "mcq":
            return # Learn Streamlit Before Continuing