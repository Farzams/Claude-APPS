import { useEffect, useMemo, useReducer, useRef, useState, useCallback } from 'react'
import Board from './components/Board.jsx'
import NewGameDialog from './components/NewGameDialog.jsx'
import ImportDialog from './components/ImportDialog.jsx'
import { reducer, newGame } from './game.js'
import { compile, findConflicts } from './engine/compile.js'
import { search } from './engine/solver.js'
import { makeHint } from './engine/hints.js'
import { describeRules } from './engine/rules.js'
import library from './data/library.json'

const NONE = new Set()
const SAVE_KEY = 'sudoku-save-v1'

const readSave = () => {
  try {
    const raw = localStorage.getItem(SAVE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const fmt = (s) => `${String((s / 60) | 0).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

/** Make sure imported puzzles have a solution (or flag that they don't). */
function prepare(puzzle) {
  if (puzzle.solution) return puzzle
  const c = compile(puzzle)
  const r = search(c, puzzle.givens, { limit: 2, maxNodes: 300000 })
  return {
    ...puzzle,
    solution: r.solutions[0] ? Array.from(r.solutions[0]) : null,
    unique: r.count === 1 && !r.aborted,
    unsolvable: r.count === 0 && !r.aborted,
  }
}

function initial() {
  const saved = readSave()
  if (saved?.puzzle) return newGame(saved.puzzle, saved)
  return newGame(library[0])
}

export default function App() {
  const [g, dispatch] = useReducer(reducer, null, initial)
  const [dialog, setDialog] = useState(null)
  const [msg, setMsg] = useState(null)
  const [fb, setFb] = useState(null) // feedback tied to the grid it was computed for
  const [busy, setBusy] = useState(false)
  const [showConflicts, setShowConflicts] = useState(true)
  const worker = useRef(null)

  const compiled = useMemo(() => compile(g.puzzle), [g.puzzle])
  const conflicts = useMemo(
    () => (showConflicts ? findConflicts(compiled, g.values) : new Set()),
    [compiled, g.values, showConflicts],
  )
  const filled = g.values.every((x) => x > 0)
  const solved = filled && findConflicts(compiled, g.values).size === 0

  const fresh = fb && fb.values === g.values
  const wrong = fresh ? fb.wrong : NONE
  const hint = fresh ? fb.hint : null
  const checkMsg = fresh ? fb.msg : null

  useEffect(() => {
    if (solved) return undefined
    const t = setInterval(() => dispatch({ type: 'tick' }), 1000)
    return () => clearInterval(t)
  }, [solved, g.puzzle])

  useEffect(() => {
    try {
      localStorage.setItem(
        SAVE_KEY,
        JSON.stringify({ puzzle: g.puzzle, values: g.values, corner: g.corner, center: g.center, elapsed: g.elapsed }),
      )
    } catch { /* storage unavailable */ }
  }, [g.puzzle, g.values, g.corner, g.center, g.elapsed])

  const enter = useCallback((digit, mode) => dispatch({ type: 'enter', digit, mode }), [])

  useEffect(() => {
    const onKey = (e) => {
      if (dialog || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return
      const m = /^(?:Digit|Numpad)([1-9])$/.exec(e.code)
      if (m) {
        e.preventDefault()
        const mode = e.shiftKey ? 'corner' : e.ctrlKey || e.altKey || e.metaKey ? 'center' : undefined
        enter(+m[1], mode)
        return
      }
      const key = e.key
      if (key === 'Backspace' || key === 'Delete' || key === '0') { e.preventDefault(); dispatch({ type: 'erase' }) }
      else if ((e.ctrlKey || e.metaKey) && key.toLowerCase() === 'z') { e.preventDefault(); dispatch({ type: e.shiftKey ? 'redo' : 'undo' }) }
      else if ((e.ctrlKey || e.metaKey) && key.toLowerCase() === 'y') { e.preventDefault(); dispatch({ type: 'redo' }) }
      else if (key === ' ') {
        e.preventDefault()
        const order = ['digit', 'corner', 'center']
        dispatch({ type: 'mode', mode: order[(order.indexOf(g.mode) + 1) % 3] })
      } else if (key.startsWith('Arrow')) {
        e.preventDefault()
        const cur = g.selected.length ? g.selected[g.selected.length - 1] : 40
        const r = (cur / 9) | 0
        const c = cur % 9
        const nr = Math.max(0, Math.min(8, r + (key === 'ArrowDown') - (key === 'ArrowUp')))
        const nc = Math.max(0, Math.min(8, c + (key === 'ArrowRight') - (key === 'ArrowLeft')))
        const n = nr * 9 + nc
        dispatch({ type: 'select', cells: e.shiftKey ? [...new Set([...g.selected, n])] : [n] })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [dialog, g.mode, g.selected, enter])

  const startPuzzle = (puzzle) => {
    dispatch({ type: 'load', puzzle: prepare(puzzle) })
    setMsg(null)
    setDialog(null)
  }

  const generate = (opts) => {
    setBusy(true)
    setMsg(null)
    worker.current?.terminate()
    const w = new Worker(new URL('./engine/worker.js', import.meta.url), { type: 'module' })
    worker.current = w
    w.onmessage = (e) => {
      setBusy(false)
      w.terminate()
      if (e.data.ok) startPuzzle(e.data.puzzle)
      else setMsg({ kind: 'bad', text: e.data.error })
    }
    w.onerror = () => { setBusy(false); setMsg({ kind: 'bad', text: 'Puzzle generator failed.' }) }
    w.postMessage({ ...opts, seed: Date.now() })
    setDialog(null)
  }

  const check = () => {
    const p = g.puzzle
    const bad = new Set()
    if (p.solution && p.unique) {
      g.values.forEach((v, i) => { if (v && v !== p.solution[i]) bad.add(i) })
    } else {
      for (const i of findConflicts(compiled, g.values)) if (!p.givens[i]) bad.add(i)
    }
    setFb({
      values: g.values,
      wrong: bad,
      hint: null,
      msg: bad.size
        ? { kind: 'bad', text: `${bad.size} cell${bad.size > 1 ? 's are' : ' is'} wrong (marked red).` }
        : { kind: 'good', text: 'Everything entered so far is correct.' },
    })
  }

  const giveHint = () => {
    const h = makeHint(compiled, Int8Array.from(g.values), g.puzzle.unique ? g.puzzle.solution : null)
    setFb({ values: g.values, wrong: NONE, hint: h, msg: null })
    if (h.cell != null) dispatch({ type: 'select', cells: [h.cell] })
  }

  const applyHint = () => {
    if (hint?.value) dispatch({ type: 'set', cell: hint.cell, digit: hint.value })
  }

  const reveal = () => {
    if (!g.puzzle.solution) return
    if (!window.confirm('Reveal the whole solution? This ends the attempt.')) return
    g.puzzle.solution.forEach((v, i) => dispatch({ type: 'set', cell: i, digit: v }))
  }

  const rules = describeRules(g.puzzle)
  const counts = useMemo(() => {
    const n = new Array(10).fill(0)
    g.values.forEach((v) => { n[v]++ })
    return n
  }, [g.values])

  return (
    <div className="app">
      <header>
        <h1>Sudoku</h1>
        <div className="title">
          <strong>{g.puzzle.name}</strong>
          <span className="timer" aria-label="elapsed time">{fmt(g.elapsed)}</span>
        </div>
        <div className="top-actions">
          <button onClick={() => setDialog('new')} disabled={busy}>New puzzle</button>
          <button onClick={() => setDialog('import')}>Import</button>
        </div>
      </header>

      <main>
        <div className="board-wrap">
          <Board
            puzzle={g.puzzle}
            values={g.values}
            corner={g.corner}
            center={g.center}
            selected={g.selected}
            conflicts={conflicts}
            wrong={wrong}
            hint={hint}
            onSelect={(cells) => dispatch({ type: 'select', cells })}
          />
          {busy && <div className="overlay">Building a puzzle…</div>}
          {solved && (
            <div className="overlay win">
              <div>
                <h2>Solved!</h2>
                <p>Time {fmt(g.elapsed)}</p>
                <button onClick={() => setDialog('new')}>Next puzzle</button>
              </div>
            </div>
          )}
        </div>

        <aside>
          <div className="modes" role="group" aria-label="Entry mode">
            {[['digit', 'Digit'], ['corner', 'Corner'], ['center', 'Centre']].map(([m, label]) => (
              <button key={m} className={g.mode === m ? 'on' : ''} onClick={() => dispatch({ type: 'mode', mode: m })}>
                {label}
              </button>
            ))}
          </div>

          <div className="pad">
            {Array.from({ length: 9 }, (_, k) => k + 1).map((d) => (
              <button key={d} className={counts[d] >= 9 ? 'done' : ''} onClick={() => enter(d)}>
                {d}
              </button>
            ))}
          </div>

          <div className="row">
            <button onClick={() => dispatch({ type: 'undo' })} disabled={!g.past.length}>Undo</button>
            <button onClick={() => dispatch({ type: 'redo' })} disabled={!g.future.length}>Redo</button>
            <button onClick={() => dispatch({ type: 'erase' })}>Erase</button>
          </div>
          <div className="row">
            <button onClick={check}>Check</button>
            <button onClick={giveHint}>Hint</button>
            <button onClick={reveal} disabled={!g.puzzle.solution}>Reveal</button>
          </div>

          {hint && (
            <div className="hint">
              <p>{hint.message}</p>
              {hint.value && <button onClick={applyHint}>Fill {hint.value} in</button>}
            </div>
          )}
          {(msg || checkMsg) && <p className={`msg ${(msg || checkMsg).kind}`}>{(msg || checkMsg).text}</p>}
          {g.puzzle.unsolvable && <p className="msg bad">This puzzle has no solution under the rules the app understands.</p>}
          {g.puzzle.solution && !g.puzzle.unique && !g.puzzle.unsolvable && (
            <p className="msg warn">
              This puzzle has more than one solution here (an imported rule may be unsupported), so Check only
              looks for rule violations.
            </p>
          )}

          <label className="toggle">
            <input type="checkbox" checked={showConflicts} onChange={(e) => setShowConflicts(e.target.checked)} />
            Highlight rule conflicts as I play
          </label>

          <details open>
            <summary>Rules</summary>
            <ul className="rules">
              {rules.map((r) => <li key={r}>{r}</li>)}
              {g.puzzle.rules && <li className="custom">{g.puzzle.rules}</li>}
            </ul>
          </details>
          <details>
            <summary>Keys</summary>
            <p className="keys">
              Digits 1–9 fill the selection. <kbd>Shift</kbd>+digit = corner mark, <kbd>Ctrl</kbd>/<kbd>Alt</kbd>+digit =
              centre mark. <kbd>Space</kbd> cycles the mode. Arrows move; hold <kbd>Shift</kbd> to extend. Drag or
              hold <kbd>Ctrl</kbd> to select several cells. <kbd>Backspace</kbd> erases, <kbd>Ctrl</kbd>+<kbd>Z</kbd> /
              <kbd>Y</kbd> undo / redo.
            </p>
          </details>
        </aside>
      </main>

      {dialog === 'new' && (
        <NewGameDialog library={library} onClose={() => setDialog(null)} onPlay={startPuzzle} onGenerate={generate} />
      )}
      {dialog === 'import' && <ImportDialog onClose={() => setDialog(null)} onPlay={startPuzzle} />}
    </div>
  )
}
