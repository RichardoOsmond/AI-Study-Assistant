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
        ("system", """You are an expert academic summarizer.
Create clear, well-structured summaries of study material.
Use markdown: headers (##/###), bullet points, and bold key terms.
Be concise but thorough — do not omit important concepts."""),
        ("human", """Summarize the following study material.
Detail level: {detail_level}
- brief: 3-5 key takeaways only
- standard: main concepts with supporting detail
- detailed: comprehensive coverage of all topics

Study Material:
{context}""")
    ])
    return summaryPrompt | get_llm(max_tokens=2048) | StrOutputParser()


def summarizeDocument(collection, detail_level: str = "standard") -> str:
    if collection.count() == 0:
        raise FileNotFoundError("No documents uploaded in this session.")

    all_chunks = collection.get(include=["documents"])["documents"]
    # Cap at 40 chunks
    context = "\n\n".join(all_chunks[:40])

    chain = get_summary_chain()
    return chain.invoke({"context": context, "detail_level": detail_level})
