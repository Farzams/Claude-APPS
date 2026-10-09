import { useState } from 'react'
import { importPuzzle } from '../engine/fpuzzles.js'

export default function ImportDialog({ onClose, onPlay }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [notes, setNotes] = useState([])
  const [result, setResult] = useState(null)

  const parse = () => {
    try {
      const r = importPuzzle(text)
      setResult(r.puzzle)
      setNotes(r.notes)
      setError('')
    } catch (e) {
      setResult(null)
      setNotes([])
      setError(e.message)
    }
  }

  return (
    <div className="modal" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="card" onClick={(e) => e.stopPropagation()}>
        <h2>Import a puzzle</h2>
        <p className="muted">
          Paste an 81-character digit string (use 0 or . for blanks), an f-puzzles link or code, or a SudokuPad link
          of the form <code>sudokupad.app/fpuzzles…</code>. Short SudokuPad IDs (e.g. <code>sudokupad.app/abc123</code>)
          are stored on SudokuPad&rsquo;s servers and can&rsquo;t be read here.
        </p>
        <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste here" />
        {error && <p className="msg bad">{error}</p>}
        {notes.map((n) => <p key={n} className="msg warn">{n}</p>)}
        {result && <p className="msg good">Read &ldquo;{result.name}&rdquo; successfully.</p>}
        <div className="row end">
          <button onClick={onClose}>Cancel</button>
          <button onClick={parse}>Read</button>
          <button className="primary" disabled={!result} onClick={() => onPlay(result)}>Play</button>
        </div>
      </div>
    </div>
  )
}
