import streamlit as st

from chat import chatWithAI
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

/* Action cards on the Home empty state */
div[data-testid="stButton"] > button.action-card {
    all: unset;
}
.action-card-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-top: 1rem;
}
/* Make Streamlit buttons look like cards */
div[data-testid="column"] div[data-testid="stButton"] > button {
    width: 100%;
    min-height: 110px;
    background: #ffffff;
    border: 1.5px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: left;
    cursor: pointer;
    transition: box-shadow 0.15s, border-color 0.15s;
    white-space: normal !important;
    line-height: 1.4 !important;
}
div[data-testid="column"] div[data-testid="stButton"] > button:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    border-color: #1370f2;
}
div[data-testid="column"] div[data-testid="stButton"] > button p {
    text-align: left !important;
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
    session = get_session(active_id) if active_id else None

    # Fallback: if no valid active session, default to the most recent one
    if session is None:
        session = sessions[0]
        st.session_state.active_session = session["session_id"]

    return session

def getCollection():
    session = getActiveSession()
    return getSessionCollection(session)

# Sidebar
_PAGES = ["Home", "Upload File", "Summarize", "Quiz"]

with st.sidebar:
    st.markdown('<div class="sidebar-title">Study Assistant</div>', unsafe_allow_html=True)

    _nav_to = st.session_state.pop("_nav_to", None)
    if _nav_to in _PAGES:
        st.session_state["page"] = _nav_to

    page = st.radio("Page Navigation",
                    _PAGES,
                    label_visibility="collapsed",
                    key="page")
    st.divider()

    # Session selector
    st.markdown("**Sessions**")

    # Ensure at least one session exists BEFORE building the lists
    active_session = getActiveSession()

    sessions_list = getSessionsList()
    session_names = [s["display_name"] for s in sessions_list]
    session_ids = [s["session_id"] for s in sessions_list]

    current_index = session_ids.index(active_session["session_id"]) if active_session[
                                                                           "session_id"] in session_ids else 0

    selected_name = st.selectbox("Select Session", session_names, index=current_index, label_visibility="collapsed")

    # Guard: if somehow nothing is selected, fall back to the active session
    if selected_name is None:
        selected_id = active_session["session_id"]
    else:
        selected_id = session_ids[session_names.index(selected_name)]

    if selected_id != st.session_state.get("active_session"):
        st.session_state.active_session = selected_id
        st.rerun()

# Home Page
# Home Page
if page == "Home":
    active_session = getActiveSession()
    collection = getCollection()

    chatHistoryKey = f"chat_history_{active_session['session_id']}"
    if chatHistoryKey not in st.session_state:
        st.session_state[chatHistoryKey] = []

    chatHistory = st.session_state[chatHistoryKey]

    # ── Empty session: show welcome + action cards ──
    if not chatHistory:
        st.markdown("### Welcome to AI Study Assistant 👋")
        st.markdown("Developed by Richardo Osmond")
        st.markdown("Get started by choosing an action below, or just type a question.")
        st.write("")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "📄 Upload File\n\nUpload a PDF and let the assistant index it so you can ask questions about its content.",
                use_container_width=True,
            ):
                st.session_state["_nav_to"] = "Upload File"
                st.rerun()
        with col2:
            if st.button(
                "📝 Summarize\n\nGet a concise summary of any uploaded document — great for quick revision before an exam.",
                use_container_width=True,
            ):
                st.session_state["_nav_to"] = "Summarize"
                st.rerun()
        with col3:
            if st.button(
                "🧠 Quiz\n\nTest your knowledge with auto-generated questions based on your study materials.",
                use_container_width=True,
            ):
                st.session_state["_nav_to"] = "Quiz"
                st.rerun()

        st.divider()

    # ── Has chat: show the conversation ──
    else:
        files = active_session.get("files", [])
        if files:
            st.caption(f"📎 Using: {', '.join(files)}")

        for msg in chatHistory:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">{msg["Content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-ai">{msg["Content"]}</div>', unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat"):
            st.session_state[chatHistoryKey] = []
            st.rerun()

    # ── Chat input (always visible, on both states) ──
    user_input = st.chat_input("Ask a question about your study materials...")
    if user_input and user_input.strip():
        chatHistory.append({"role": "user", "Content": user_input.strip()})
        with st.spinner("Thinking..."):
            try:
                response = chatWithAI(user_input.strip(), chatHistory, collection)
            except Exception as e:
                response = f"Sorry, something went wrong: {str(e)}"
        chatHistory.append({"role": "assistant", "Content": response})
        st.session_state[chatHistoryKey] = chatHistory
        st.rerun()

elif page == "Upload File":
    from rag import fileUpload
    import tempfile, os

    st.title("📄 Upload Study Material")
    active_session = getActiveSession()
    collection = getCollection()

    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if uploaded_file:
        if uploaded_file.name in active_session.get("files", []):
            st.info(f"**{uploaded_file.name}** is already uploaded in this session.")
        else:
            if st.button("📥 Process File"):
                with st.spinner("Extracting and indexing your document..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name
                    try:
                        fileUpload(tmp_path, collection)
                        addFileSession(active_session["session_id"], uploaded_file.name)
                        st.success(f"✅ **{uploaded_file.name}** uploaded successfully!")
                    except Exception as e:
                        st.error(f"Error processing file: {e}")
                    finally:
                        os.unlink(tmp_path)

    # Show uploaded files in current session
    files = active_session.get("files", [])
    if files:
        st.divider()
        st.markdown("**Files in this session:**")
        for f in files:
            st.markdown(f"- 📎 {f}")

# ── Summarize Page ────────────────────────────────────────────────────────────

elif page == "Summarize":
    st.title("📝 Summarize")
    st.info("Summarize feature coming soon!")

# ── Quiz Page ─────────────────────────────────────────────────────────────────

elif page == "Quiz":
    st.title("🧠 Quiz")
    st.info("Quiz feature coming soon!")