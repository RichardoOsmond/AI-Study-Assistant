# AI Study Assistant
## Status
This project is still work in progress and may not work as intended.

## Overview
This is a web-based app built using streamlit, integrated with APIs with groq as the LLM and tavily for the web searching capability. It is designed to help students who are in need of a document summarizer and a study assistant. It is currently using a basic RAG pipeline that may be upgraded to advanced RAG pipeline in the future, along with better context matching algorithm. This project is developed by Richardo Osmond with the help of Claude.

## Features
- RAG pipeline for ingesting PDF
- Session isolation, each session will have its own knowledge base with its own separate memory.
- Chat with your study materials, with a web search fallback
- Auto generated quizzes, with grading done by AI

## Tech Stack
- Streamlit
- Langchain
- Groq (llama-3.3-70b-versatile)
- ChromaDB
- Tavily Search
- Sentence-Transformers (all-MiniLM-L6-v2)

## Setup
1. Clone the repo
2. Install the dependencies using, "pip install -r requirements.txt"
3. Copy .env.example to your .env and fill in with your own API keys
- Groq API Key can be found in console.groq.com (free)
- Tavily API Key can be found in tavily.com (free)
4. Run the app using "streamlit run main.py" at the terminal

## Improvements to be done
- Rewrite RAG Pipeline using Advanced RAG Pipeline, focusing on an app that is actually usable (can be used and bring benefits to users).
- Replace Streamlit with HTML, CSS, Javascript as the frontend to allow for more flexibility in design.
