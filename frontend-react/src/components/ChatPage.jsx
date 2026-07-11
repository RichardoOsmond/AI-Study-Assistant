import { useState, useRef, useEffect } from 'react'
import { api } from '../api'

const ACTIONS = [
  { page: 'Upload File', icon: '📄', title: 'Upload File',
    text: 'Upload a PDF or PowerPoint and let the assistant index it so you can ask questions about its content.' },
  { page: 'Summarize', icon: '📝', title: 'Summarize',
    text: 'Get a concise summary of any uploaded document — great for quick revision before an exam.' },
  { page: 'Quiz', icon: '🧠', title: 'Quiz',
    text: 'Test your knowledge with auto-generated questions based on your study materials.' },
]

export default function ChatPage({ session, onNavigate }) {
  const [historyBySession, setHistoryBySession] = useState({})
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  const history = historyBySession[session.session_id] ?? []
  const setHistory = (h) =>
    setHistoryBySession((prev) => ({ ...prev, [session.session_id]: h }))

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [history])

  const send = async () => {
    const question = input.trim()
    if (!question || busy) return
    setBusy(true)
    setError(null)
    try {
      const { answer } = await api.chat(session.session_id, question, history)
      setHistory([...history,
        { role: 'user', Content: question },
        { role: 'assistant', Content: answer }])
      setInput('')
    } catch (e) {
      setError(`Sorry, something went wrong: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page chat-page">
      {history.length === 0 ? (
        <div className="welcome">
          <h2>Welcome to AI Study Assistant 👋</h2>
          <p>Developed by Richardo Osmond</p>
          <p>Get started by choosing an action below, or just type a question.</p>
          <div className="cards">
            {ACTIONS.map((a) => (
              <button key={a.page} className="card" onClick={() => onNavigate(a.page)}>
                <strong>{a.icon} {a.title}</strong>
                <span>{a.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="messages">
          {session.files?.length > 0 && (
            <p className="caption">📎 Using: {session.files.join(', ')}</p>
          )}
          {history.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'bubble user' : 'bubble ai'}>
              {m.Content}
            </div>
          ))}
          <button className="small" onClick={() => setHistory([])}>🗑️ Clear Chat</button>
          <div ref={bottomRef} />
        </div>
      )}

      {error && <div className="banner error">{error}</div>}

      <div className="chat-input">
        <input
          placeholder="Ask a question about your study materials..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          {busy ? 'Thinking…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
