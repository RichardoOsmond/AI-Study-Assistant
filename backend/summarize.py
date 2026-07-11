from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm import get_llm

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


def summarizeDocument(collection, detail_level: str = "standard", max_chunks: int = 40) -> dict:
    """Summarize the session's documents.

    Returns {"summary": str, "chunks_used": int, "total_chunks": int} so the
    UI can tell the user when the material was sampled rather than fully read.
    """
    if collection.count() == 0:
        raise FileNotFoundError("No documents uploaded in this session.")

    all_chunks = collection.get(include=["documents"])["documents"]

    if len(all_chunks) > max_chunks:
        # Sample evenly across the whole document instead of only the start,
        # so the summary is not biased toward the first pages
        step = len(all_chunks) / max_chunks
        selected = [all_chunks[int(i * step)] for i in range(max_chunks)]
    else:
        selected = all_chunks

    context = "\n\n".join(selected)

    chain = get_summary_chain()
    summary = chain.invoke({"context": context, "detail_level": detail_level})

    return {
        "summary": summary,
        "chunks_used": len(selected),
        "total_chunks": len(all_chunks),
    }
