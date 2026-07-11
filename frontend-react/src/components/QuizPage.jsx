import { useState } from 'react'
import { api } from '../api'

export default function QuizPage({ session }) {
  const [nQuestions, setNQuestions] = useState(5)
  const [qType, setQType] = useState('mixed')
  const [questions, setQuestions] = useState(null)
  const [answers, setAnswers] = useState({})
  const [graded, setGraded] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const hasFiles = session.files?.length > 0

  const generate = async () => {
    setBusy(true)
    setError(null)
    try {
      const { questions } = await api.quizGenerate(session.session_id, nQuestions, qType)
      setQuestions(questions)
      setAnswers({})
      setGraded(null)
    } catch (e) {
      setError(`Error generating quiz: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      setGraded(await api.quizGrade(session.session_id, questions, answers))
    } catch (e) {
      setError(`Error grading quiz: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const reset = () => { setQuestions(null); setAnswers({}); setGraded(null) }

  return (
    <div className="page">
      <h2>🧠 Quiz</h2>

      {!hasFiles ? (
        <div className="banner warning">
          No files uploaded yet. Go to <strong>Upload File</strong> to add study material first.
        </div>
      ) : (
        <>
          <p className="caption">📎 Using: {session.files.join(', ')}</p>

          {!questions && (
            <div className="quiz-settings">
              <label>
                Number of questions
                <input type="number" min="1" max="20" value={nQuestions}
                       onChange={(e) => setNQuestions(Number(e.target.value))} />
              </label>
              <label>
                Question type
                <select value={qType} onChange={(e) => setQType(e.target.value)}>
                  <option value="mixed">mixed</option>
                  <option value="mcq">mcq</option>
                  <option value="short">short</option>
                </select>
              </label>
              <button onClick={generate} disabled={busy}>
                {busy ? 'Generating…' : '🎲 Generate Quiz'}
              </button>
            </div>
          )}

          {error && <div className="banner error">{error}</div>}

          {questions?.map((q, i) => {
            const result = graded?.results[i]
            return (
              <div key={i} className="question">
                <p><strong>Q{i + 1}. {q.question}</strong></p>

                {q.type === 'mcq' ? (
                  Object.entries(q.options).map(([key, text]) => (
                    <label key={key} className="option">
                      <input
                        type="radio"
                        name={`q${i}`}
                        checked={answers[i] === key}
                        disabled={graded !== null}
                        onChange={() => setAnswers({ ...answers, [i]: key })}
                      />
                      {key}. {text}
                    </label>
                  ))
                ) : (
                  <textarea
                    rows="3"
                    value={answers[i] ?? ''}
                    disabled={graded !== null}
                    onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })}
                  />
                )}

                {result && (
                  result.correct ? (
                    <div className="banner success">✅ Correct — {result.feedback}</div>
                  ) : (
                    <div className="banner error">
                      ❌ Incorrect — {q.type === 'mcq'
                        ? `Correct answer: ${q.answer}. ${q.options[q.answer] ?? ''}`
                        : result.feedback}
                      {q.type === 'short' && <p>Model answer: {q.model_answer}</p>}
                    </div>
                  )
                )}
              </div>
            )
          })}

          {questions && !graded && (
            <button onClick={submit} disabled={busy}>
              {busy ? 'Grading…' : '📤 Submit Quiz'}
            </button>
          )}

          {graded && (
            <div className="quiz-result">
              <h3>Result: {graded.score} / {graded.total}</h3>
              <p>
                {graded.score === graded.total ? 'Perfect score! 🎉'
                  : graded.score >= graded.total * 0.7 ? 'Good work! Keep it up.'
                  : "Keep studying — you'll get there!"}
              </p>
              <button onClick={reset}>🔄 New Quiz</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
