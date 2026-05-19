import os
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults

load_dotenv()

model = "llama-3.3-70b-versatile"
k = 5

def get_llm():
    return ChatGroq(
        model=model,
        api_key=os.environ['GROQ_API_KEY']
    )

# Context Retrieval
def contextRetrieval(query: str, collection, k: int = k):
    if collection.count() == 0:
        return "No local study material found."

    results = collection.query(query_texts=[query], n_results=min(k, collection.count()))

    chunks = []

# Get Agent
def buildAgent():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a knowledgeable and friendly AI Study Assistant.
        
        You have 2 sources of information:
        1. Local Context - text extracted from student's uploaded documents.
        2. tavily_search_results_json tool - use this when local context provides insufficient information.
        
        Rules:
        1. Prioritize local context when it can be used to answer the question well.
        2. If slides looks incomplete (e.g. just a heading with no explanation), call the search tool.
        3. When supplementing information with web search, briefly tell them.
        4. Keep answers clear, concise, and student-friendly.
        5. Never make up facts, say "I'm not sure" if needed."""), ("human", """
        Question: {question}
        
        Local Study Material Context: 
        {context}
        
        Use the search tool if the context provides insufficient information.""")
    ])
    llm = get_llm()
    tools =[TavilySearchResults(max_results=3)]
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)

def chatWithAI(question: str, chat_history: list, collection):
    agent = buildAgent()