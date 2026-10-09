import { CELLS, rowOf, colOf } from './engine/util.js'

export const MODES = ['digit', 'corner', 'center']

const sameBox = (a, b) =>
  ((rowOf(a) / 3) | 0) === ((rowOf(b) / 3) | 0) && ((colOf(a) / 3) | 0) === ((colOf(b) / 3) | 0)
const isPeer = (a, b) => a !== b && (rowOf(a) === rowOf(b) || colOf(a) === colOf(b) || sameBox(a, b))

export function newGame(puzzle, saved = null) {
  const values = saved?.values ? saved.values.slice() : puzzle.givens.slice()
  return {
    puzzle,
    values,
    corner: saved?.corner ? saved.corner.slice() : new Array(CELLS).fill(0),
    center: saved?.center ? saved.center.slice() : new Array(CELLS).fill(0),
    selected: [],
    mode: 'digit',
    past: [],
    future: [],
    elapsed: saved?.elapsed || 0,
  }
}

const snapshot = (s) => ({ values: s.values, corner: s.corner, center: s.center })
const commit = (s, patch) => ({
  ...s,
  ...patch,
  past: [...s.past.slice(-300), snapshot(s)],
  future: [],
})

const editable = (s, i) => !s.puzzle.givens[i]

export function reducer(s, a) {
  switch (a.type) {
    case 'load':
      return newGame(a.puzzle, a.saved)
    case 'select':
      return { ...s, selected: a.cells }
    case 'mode':
      return { ...s, mode: a.mode }
    case 'tick':
      return { ...s, elapsed: s.elapsed + 1 }
    case 'enter': {
      const cells = s.selected.filter((i) => editable(s, i))
      if (!cells.length) return s
      const d = a.digit
      const mode = a.mode || s.mode
      const values = s.values.slice()
      const corner = s.corner.slice()
      const center = s.center.slice()
      const bit = 1 << d
      if (mode === 'digit') {
        const allHave = cells.every((i) => values[i] === d)
        for (const i of cells) {
          values[i] = allHave ? 0 : d
          if (!allHave) { corner[i] = 0; center[i] = 0 }
        }
        if (!allHave && a.autoClear !== false)
          for (let j = 0; j < CELLS; j++)
            if (!values[j] && cells.some((i) => isPeer(i, j))) { corner[j] &= ~bit; center[j] &= ~bit }
      } else {
        const targets = cells.filter((i) => !values[i])
        if (!targets.length) return s
        const arr = mode === 'corner' ? corner : center
        const allHave = targets.every((i) => arr[i] & bit)
        for (const i of targets) arr[i] = allHave ? arr[i] & ~bit : arr[i] | bit
      }
      return commit(s, { values, corner, center })
    }
    case 'erase': {
      const cells = s.selected.filter((i) => editable(s, i))
      if (!cells.some((i) => s.values[i] || s.corner[i] || s.center[i])) return s
      const values = s.values.slice()
      const corner = s.corner.slice()
      const center = s.center.slice()
      // first press clears digits; if there are none, clears marks
      const hasDigit = cells.some((i) => values[i])
      for (const i of cells) {
        if (hasDigit) values[i] = 0
        else { corner[i] = 0; center[i] = 0 }
      }
      return commit(s, { values, corner, center })
    }
    case 'set': {
      if (!editable(s, a.cell)) return s
      const values = s.values.slice()
      values[a.cell] = a.digit
      const corner = s.corner.slice()
      const center = s.center.slice()
      corner[a.cell] = 0
      center[a.cell] = 0
      return commit(s, { values, corner, center })
    }
    case 'undo': {
      if (!s.past.length) return s
      const prev = s.past[s.past.length - 1]
      return { ...s, ...prev, past: s.past.slice(0, -1), future: [snapshot(s), ...s.future] }
    }
    case 'redo': {
      if (!s.future.length) return s
      const [next, ...rest] = s.future
      return { ...s, ...next, past: [...s.past, snapshot(s)], future: rest }
    }
    case 'restart':
      return { ...newGame(s.puzzle), elapsed: 0 }
    default:
      return s
  }
}
