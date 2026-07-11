import { useEffect, useState, useCallback } from 'react'
import { api } from './api'
import Sidebar from './components/Sidebar'
import ChatPage from './components/ChatPage'
import UploadPage from './components/UploadPage'
import SummarizePage from './components/SummarizePage'
import QuizPage from './components/QuizPage'

const PAGES = ['Home', 'Upload File', 'Summarize', 'Quiz']

export default function App() {
  const [sessions, setSessions] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [page, setPage] = useState('Home')
  const [error, setError] = useState(null)

  const refreshSessions = useCallback(async () => {
    try {
      let list = await api.listSessions()
      if (list.length === 0) {
        const created = await api.createSession('First Study Conversation')
        list = [created]
      }
      setSessions(list)
      setActiveId((current) =>
        list.some((s) => s.session_id === current) ? current : list[0].session_id
      )
      setError(null)
    } catch (e) {
      setError(`Could not reach the API server: ${e.message}`)
    }
  }, [])

  useEffect(() => { refreshSessions() }, [refreshSessions])

  const activeSession = sessions.find((s) => s.session_id === activeId) || null

  return (
    <div className="app">
      <Sidebar
        pages={PAGES}
        page={page}
        onNavigate={setPage}
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onSessionsChanged={refreshSessions}
      />
      <main className="main">
        {error && <div className="banner error">{error}</div>}
        {activeSession && page === 'Home' && (
          <ChatPage session={activeSession} onNavigate={setPage} />
        )}
        {activeSession && page === 'Upload File' && (
          <UploadPage session={activeSession} onChanged={refreshSessions} />
        )}
        {activeSession && page === 'Summarize' && (
          <SummarizePage session={activeSession} />
        )}
        {activeSession && page === 'Quiz' && (
          <QuizPage session={activeSession} />
        )}
      </main>
    </div>
  )
}
