import { useState } from 'react'
import { api } from '../api'

export default function Sidebar({ pages, page, onNavigate, sessions, activeId, onSelect, onSessionsChanged }) {
  const [renaming, setRenaming] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const active = sessions.find((s) => s.session_id === activeId)

  const createSession = async () => {
    const created = await api.createSession('New Study Session')
    await onSessionsChanged()
    onSelect(created.session_id)
  }

  const rename = async () => {
    if (renaming.trim()) {
      await api.renameSession(activeId, renaming.trim())
      setRenaming('')
      await onSessionsChanged()
    }
  }

  const remove = async () => {
    await api.deleteSession(activeId)
    setConfirmDelete(false)
    await onSessionsChanged()
  }

  return (
    <aside className="sidebar">
      <h1 className="sidebar-title">Study Assistant</h1>

      <nav className="nav">
        {pages.map((p) => (
          <button
            key={p}
            className={`nav-item ${p === page ? 'active' : ''}`}
            onClick={() => onNavigate(p)}
          >
            {p}
          </button>
        ))}
      </nav>

      <div className="sessions-header">
        <span>Sessions</span>
        <button className="small" onClick={createSession}>＋ New</button>
      </div>

      <select
        className="session-select"
        value={activeId ?? ''}
        onChange={(e) => onSelect(e.target.value)}
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>{s.display_name}</option>
        ))}
      </select>

      {active && (
        <details className="manage">
          <summary>⚙️ Manage session</summary>
          <input
            placeholder={active.display_name}
            value={renaming}
            onChange={(e) => setRenaming(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && rename()}
          />
          <button className="small" onClick={rename}>✏️ Rename</button>

          {confirmDelete ? (
            <div className="confirm">
              <p>Delete this session and its documents?</p>
              <button className="small danger" onClick={remove}>✅ Confirm</button>
              <button className="small" onClick={() => setConfirmDelete(false)}>❌ Cancel</button>
            </div>
          ) : (
            <button className="small danger" onClick={() => setConfirmDelete(true)}>
              🗑️ Delete session
            </button>
          )}
        </details>
      )}
    </aside>
  )
}
