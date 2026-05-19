import streamlit as st
from session import *

st.set_page_config(
    page_title="AI Study Assistant",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.chat-ai {
    background: #f0f0ec;
    color: #1a1a1a;
    border-style: outset;
    border-width: 2px;
    border-radius: 10px 10px 10px 2px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    max-width: 85%;
    font-size: 1rem;
    line-height: 1;
}

.chat-user {
    background: #1370f2;
    color: #FFFFFF;
    border-style: outset;
    border-width: 2px;
    border-radius: 10px 10px 2px 10px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    max-width: 85%;
    font-size: 1rem;
    margin-left: auto;
    line-height: 1;
}
</style>
""", unsafe_allow_html=True)

# Session Management
def getActiveSession():
    sessions = getSessionsList()
    if not sessions:
        currSession = createSession("First Study Conversation")
        st.session_state.active_session = currSession["session_id"]
        return currSession

    active_id = st.session_state.get("active_session")
    return get_session(active_id)

def getCollection():
    session = getActiveSession()
    return getSessionCollection(session)

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-title">Study Assistant</div>', unsafe_allow_html=True)

    page = st.radio("Page Navigation",
                    ["Home", "Upload File", "Summarize", "Chat", "Quiz"],
                    label_visibility="collapsed")

# Home Page
if "Home" in page:
    st.markdown("Welcome to AI Study Assistant Web Application")
    st.markdown("Developed by Richardo Osmond")
    active_session = getActiveSession()
    chatHistoryKey = f"chat_history_{active_session['session_id']}"
    if not chatHistoryKey in st.session_state:
        st.session_state[chatHistoryKey] = []

    chatHistory = st.session_state[chatHistoryKey]

    for chat in chatHistory:
        if chat["role"] == "user":
            st.markdown(f'<div class="chat-user">{chat["Content"]}</div>')
        else:
            st.markdown(f'<div class="chat-ai">{chat["Content"]}</div>')