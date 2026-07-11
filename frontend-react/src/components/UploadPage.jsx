import { useState } from 'react'
import { api } from '../api'

export default function UploadPage({ session, onChanged }) {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)

  const upload = async () => {
    if (!file || busy) return
    setBusy(true)
    setMessage(null)
    try {
      await api.uploadFile(session.session_id, file)
      setMessage({ kind: 'success', text: `✅ ${file.name} uploaded successfully!` })
      setFile(null)
      await onChanged()
    } catch (e) {
      setMessage({ kind: 'error', text: `Error processing file: ${e.message}` })
    } finally {
      setBusy(false)
    }
  }

  const remove = async (filename) => {
    await api.removeFile(session.session_id, filename)
    await onChanged()
  }

  return (
    <div className="page">
      <h2>📄 Upload Study Material</h2>

      {message && <div className={`banner ${message.kind}`}>{message.text}</div>}

      <input
        type="file"
        accept=".pdf,.pptx"
        onChange={(e) => setFile(e.target.files[0] ?? null)}
      />
      {file && (
        <button onClick={upload} disabled={busy}>
          {busy ? 'Extracting and indexing…' : '📥 Process File'}
        </button>
      )}

      {session.files?.length > 0 && (
        <>
          <h3>Files in this session</h3>
          <ul className="file-list">
            {session.files.map((f) => (
              <li key={f}>
                📎 {f}
                <button className="small danger" onClick={() => remove(f)}>Remove</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
