// Thin client for the FastAPI backend. All calls go through the Vite proxy in
// dev (see vite.config.js) so URLs are relative.

async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...options,
  })
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed (${response.status})`)
  }
  return data
}

export const api = {
  listSessions: () => request('/sessions'),
  createSession: (name) => request('/sessions', { method: 'POST', body: JSON.stringify({ name }) }),
  renameSession: (id, name) => request(`/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) }),
  deleteSession: (id) => request(`/sessions/${id}`, { method: 'DELETE' }),

  uploadFile: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/sessions/${id}/files`, { method: 'POST', body: form })
  },
  removeFile: (id, filename) =>
    request(`/sessions/${id}/files/${encodeURIComponent(filename)}`, { method: 'DELETE' }),

  chat: (id, question, history) =>
    request(`/sessions/${id}/chat`, { method: 'POST', body: JSON.stringify({ question, history }) }),
  summarize: (id, detailLevel) =>
    request(`/sessions/${id}/summarize`, { method: 'POST', body: JSON.stringify({ detail_level: detailLevel }) }),
  quizGenerate: (id, nQuestions, questionType) =>
    request(`/sessions/${id}/quiz/generate`, {
      method: 'POST',
      body: JSON.stringify({ n_questions: nQuestions, question_type: questionType }),
    }),
  quizGrade: (id, questions, answers) =>
    request(`/sessions/${id}/quiz/grade`, { method: 'POST', body: JSON.stringify({ questions, answers }) }),
}
