import os
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

def get_summary_chain():
    summaryPrompt = ChatPromptTemplate.from_messages([
        ("system", ""),
        ("human", "")
    ])
    return summaryPrompt | get_llm() | StrOutputParser()