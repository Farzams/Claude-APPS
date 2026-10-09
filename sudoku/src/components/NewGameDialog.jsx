import { useState } from 'react'
import { VARIANTS, DIFFICULTIES } from '../engine/generator.js'

export default function NewGameDialog({ library, onClose, onPlay, onGenerate }) {
  const [picked, setPicked] = useState([])
  const [difficulty, setDifficulty] = useState('medium')
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]))

  return (
    <div className="modal" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="card" onClick={(e) => e.stopPropagation()}>
        <h2>New puzzle</h2>
        <h3>Build one</h3>
        <p className="muted">Tick any rules to combine; none ticked gives a classic Sudoku.</p>
        <div className="variants">
          {VARIANTS.map((v) => (
            <label key={v.id} title={v.blurb}>
              <input type="checkbox" checked={picked.includes(v.id)} onChange={() => toggle(v.id)} />
              <span><b>{v.name}</b><small>{v.blurb}</small></span>
            </label>
          ))}
        </div>
        <div className="row">
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} aria-label="Difficulty">
            {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <button className="primary" onClick={() => onGenerate({ variants: picked, difficulty })}>Generate</button>
        </div>

        <h3>Ready to play</h3>
        <div className="library">
          {library.map((p, i) => (
            <button key={i} onClick={() => onPlay(p)}>{p.name}</button>
          ))}
        </div>
        <div className="row end"><button onClick={onClose}>Close</button></div>
      </div>
    </div>
  )
}
