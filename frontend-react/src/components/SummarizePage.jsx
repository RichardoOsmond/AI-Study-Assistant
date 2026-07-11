import { useState } from 'react'
import { api } from '../api'

const LEVELS = ['brief', 'standard', 'detailed']

export default function SummarizePage({ session }) {
  const [level, setLevel] = useState('standard')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const hasFiles = session.files?.length > 0

  const generate = async () => {
    setBusy(true)
    setError(null)
    try {
      setResult(await api.summarize(session.session_id, level))
    } catch (e) {
      setError(`Error generating summary: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <h2>📝 Summarize</h2>

      {!hasFiles ? (
        <div className="banner warning">
          No files uploaded yet. Go to <strong>Upload File</strong> to add study material first.
        </div>
      ) : (
        <>
          <p className="caption">📎 Using: {session.files.join(', ')}</p>

          <div className="radio-row">
            {LEVELS.map((l) => (
              <label key={l}>
                <input type="radio" checked={level === l} onChange={() => setLevel(l)} />
                {l}
              </label>
            ))}
          </div>

          <button onClick={generate} disabled={busy}>
            {busy ? 'Summarizing…' : '✨ Generate Summary'}
          </button>

          {error && <div className="banner error">{error}</div>}

          {result && (
            <div className="summary">
              {result.chunks_used < result.total_chunks && (
                <p className="caption">
                  ℹ️ Summarized from {result.chunks_used} of {result.total_chunks} sections,
                  sampled evenly across your documents.
                </p>
              )}
              <pre className="summary-text">{result.summary}</pre>
              <button className="small" onClick={() => setResult(null)}>🗑️ Clear Summary</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
