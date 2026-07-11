import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

def requireKey(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Add it to your .env file (see .env.example)."
        )
    return value

def get_llm(max_tokens: int = 2048):
    return ChatGroq(
        model=MODEL,
        api_key=requireKey("GROQ_API_KEY"),
        max_tokens=max_tokens
    )
