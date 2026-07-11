import sys
import html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from backend.chat import chatWithAI
from backend.session import *

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
/* Make Streamlit buttons look like cards — scoped to the main area only,
   so sidebar buttons (e.g. "+ New") keep their normal size */
[data-testid="stMain"] div[data-testid="column"] div[data-testid="stButton"] > button {
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
[data-testid="stMain"] div[data-testid="column"] div[data-testid="stButton"] > button:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    border-color: #1370f2;
}
[data-testid="stMain"] div[data-testid="column"] div[data-testid="stButton"] > button p {
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
    col_label, col_btn = st.columns([3, 1])
    with col_label:
        st.markdown("**Sessions**")
    with col_btn:
        if st.button("＋ New", use_container_width=True):
            new_session = createSession("New Study Session")
            st.session_state.active_session = new_session["session_id"]
            st.rerun()

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

    # Manage session (rename / delete)
    with st.expander("⚙️ Manage session"):
        new_name = st.text_input(
            "Rename session",
            value=active_session["display_name"],
            key=f"rename_{active_session['session_id']}",
        )
        if st.button("✏️ Rename", use_container_width=True):
            if new_name and new_name.strip():
                updateSessionName(active_session["session_id"], new_name.strip())
                st.rerun()

        st.divider()

        if st.session_state.get("confirm_delete"):
            st.warning("This deletes the session, its chat history, and its indexed documents.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Confirm", use_container_width=True):
                    deleteSession(active_session["session_id"])
                    st.session_state.pop("confirm_delete", None)
                    st.session_state.pop("active_session", None)
                    st.session_state.pop(f"chat_history_{active_session['session_id']}", None)
                    st.rerun()
            with col_no:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()
        else:
            if st.button("🗑️ Delete session", use_container_width=True):
                st.session_state["confirm_delete"] = True
                st.rerun()

# Home Page
if page == "Home":
    active_session = getActiveSession()

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
            # Escape the content so HTML/scripts in messages render as plain text
            safe_content = html.escape(msg["Content"]).replace("\n", "<br>")
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">{safe_content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-ai">{safe_content}</div>', unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat"):
            st.session_state[chatHistoryKey] = []
            st.rerun()

    # ── Chat input (always visible, on both states) ──
    user_input = st.chat_input("Ask a question about your study materials...")
    if user_input and user_input.strip():
        question = user_input.strip()
        with st.spinner("Thinking..."):
            try:
                # Collection is loaded lazily here — the embedding model only
                # loads when the user actually sends a message, keeping the
                # initial page render fast
                collection = getCollection()
                # History is passed BEFORE appending, so the current question
                # isn't duplicated in the model's context
                response = chatWithAI(question, chatHistory, collection)
            except Exception as e:
                response = None
                st.error(f"Sorry, something went wrong: {e}")

        # Only save the exchange when it succeeded — errors stay out of history
        if response is not None:
            chatHistory.append({"role": "user", "Content": question})
            chatHistory.append({"role": "assistant", "Content": response})
            st.session_state[chatHistoryKey] = chatHistory
            st.rerun()

elif page == "Upload File":
    from backend.rag import fileUpload
    import tempfile, os

    st.title("📄 Upload Study Material")
    active_session = getActiveSession()

    # Show the success message from a just-completed upload (set before rerun)
    flash = st.session_state.pop("upload_flash", None)
    if flash:
        st.success(flash)

    uploaded_file = st.file_uploader("Upload a PDF or PowerPoint file", type=["pdf", "pptx"])

    if uploaded_file:
        if uploaded_file.name in active_session.get("files", []):
            st.info(f"**{uploaded_file.name}** is already uploaded in this session.")
        else:
            if st.button("📥 Process File"):
                with st.spinner("Extracting and indexing your document..."):
                    # Keep the real extension so fileUpload routes to the right extractor
                    suffix = Path(uploaded_file.name).suffix.lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name
                    success = False
                    try:
                        collection = getCollection()
                        fileUpload(tmp_path, collection)
                        addFileSession(active_session["session_id"], uploaded_file.name)
                        success = True
                    except Exception as e:
                        st.error(f"Error processing file: {e}")
                    finally:
                        os.unlink(tmp_path)
                    if success:
                        st.session_state["upload_flash"] = f"✅ **{uploaded_file.name}** uploaded successfully!"
                        st.rerun()

    # Show uploaded files in current session
    files = active_session.get("files", [])
    if files:
        st.divider()
        st.markdown("**Files in this session:**")
        for f in files:
            st.markdown(f"- 📎 {f}")

# Summarize Page
elif page == "Summarize":
    from backend.summarize import summarizeDocument

    st.title("📝 Summarize")

    active_session = getActiveSession()

    files = active_session.get("files", [])
    if not files:
        st.warning("No files uploaded yet. Go to **Upload File** to add study material first.")
    else:
        st.caption(f"📎 Using: {', '.join(files)}")

        detail_level = st.radio(
            "Detail level",
            ["brief", "standard", "detailed"],
            index=1,
            horizontal=True,
        )

        summary_key = f"summary_{active_session['session_id']}_{detail_level}"

        if st.button("✨ Generate Summary", use_container_width=True):
            with st.spinner("Summarizing your documents…"):
                try:
                    st.session_state[summary_key] = summarizeDocument(getCollection(), detail_level)
                except Exception as e:
                    st.error(f"Error generating summary: {e}")

        if summary_key in st.session_state:
            result = st.session_state[summary_key]
            st.divider()
            if result["chunks_used"] < result["total_chunks"]:
                st.caption(
                    f"ℹ️ Summarized from {result['chunks_used']} of {result['total_chunks']} "
                    f"sections, sampled evenly across your documents."
                )
            st.markdown(result["summary"])
            if st.button("🗑️ Clear Summary"):
                del st.session_state[summary_key]
                st.rerun()

# Quiz Page
elif page == "Quiz":
    from backend.quiz import generateQuiz, gradeQuiz

    st.title("🧠 Quiz")

    active_session = getActiveSession()

    files = active_session.get("files", [])
    if not files:
        st.warning("No files uploaded yet. Go to **Upload File** to add study material first.")
    else:
        st.caption(f"📎 Using: {', '.join(files)}")

        sid = active_session["session_id"]
        q_key = f"quiz_questions_{sid}"
        a_key = f"quiz_answers_{sid}"
        r_key = f"quiz_results_{sid}"

        with st.expander("Quiz settings", expanded=q_key not in st.session_state):
            col1, col2 = st.columns(2)
            with col1:
                n_questions = st.number_input("Number of questions", min_value=1, max_value=20, value=5)
            with col2:
                q_type = st.selectbox("Question type", ["mixed", "mcq", "short"], index=0)

            if st.button("🎲 Generate Quiz", use_container_width=True):
                with st.spinner("Generating questions…"):
                    try:
                        questions = generateQuiz(getCollection(), n_questions=n_questions, question_type=q_type)
                        st.session_state[q_key] = questions
                        st.session_state[a_key] = {}
                        if r_key in st.session_state:
                            del st.session_state[r_key]
                        st.rerun()
                    except FileNotFoundError:
                        st.error("No documents found in this session.")
                    except Exception as e:
                        st.error(f"Error generating quiz: {e}")

        # Quesetions
        if q_key in st.session_state:
            questions = st.session_state[q_key]
            answers = st.session_state.get(a_key, {})
            results = st.session_state.get(r_key)

            for i, q in enumerate(questions):
                with st.container(border=True):
                    st.markdown(f"**Q{i+1}. {q['question']}**")

                    if q["type"] == "mcq":
                        opts = q["options"]
                        choice = st.radio(
                            "Choose an answer",
                            options=list(opts.keys()),
                            index=None,
                            format_func=lambda k, o=opts: f"{k}. {o[k]}",
                            key=f"mcq_{sid}_{i}",
                            label_visibility="collapsed",
                            disabled=results is not None,
                        )
                        answers[i] = choice or ""
                    else:
                        user_ans = st.text_area(
                            "Your answer",
                            key=f"short_{sid}_{i}",
                            label_visibility="collapsed",
                            disabled=results is not None,
                        )
                        answers[i] = user_ans

                    if results:
                        res = results[i]
                        if res["correct"]:
                            st.success(f"✅ Correct — {res['feedback']}")
                        else:
                            if q["type"] == "mcq":
                                correct_key = q["answer"]
                                correct_text = q["options"].get(correct_key, "")
                                st.error(f"❌ Incorrect — Correct answer: **{correct_key}. {correct_text}**")
                            else:
                                st.error(f"❌ Incorrect — {res['feedback']}")
                                st.info(f"Model answer: {q['model_answer']}")

            st.session_state[a_key] = answers

            if results is None:
                if st.button("📤 Submit Quiz", use_container_width=True):
                    with st.spinner("Grading…"):
                        try:
                            st.session_state[r_key] = gradeQuiz(questions, answers)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error grading quiz: {e}")
            else:
                score = sum(1 for r in results if r["correct"])
                total = len(results)
                st.divider()
                st.markdown(f"### Result: {score} / {total}")
                if score == total:
                    st.success("Perfect score! 🎉")
                elif score >= total * 0.7:
                    st.info("Good work! Keep it up.")
                else:
                    st.warning("Keep studying — you'll get there!")

                if st.button("🔄 New Quiz", use_container_width=True):
                    for k in [q_key, a_key, r_key]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()