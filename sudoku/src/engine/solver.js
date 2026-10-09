import { CELLS, popcount, shuffle } from './util.js'
import { canPlace } from './compile.js'

const ALL = 0b1111111110

/** Bitmask of digits that may legally go in empty cell i (bit v = digit v). */
export function cellMask(c, g, i) {
  let m = 0
  for (let v = 1; v <= 9; v++) if (canPlace(c, g, i, v)) m |= 1 << v
  return m
}

export function allMasks(c, g) {
  const masks = new Uint16Array(CELLS)
  for (let i = 0; i < CELLS; i++) if (!g[i]) masks[i] = cellMask(c, g, i)
  return masks
}

/**
 * One propagation pass: place every naked single (and, with `hidden`, every
 * hidden single). Returns -1 on contradiction, otherwise the number of cells
 * placed. Placed cells are appended to `trail`.
 */
function propagatePass(c, g, hidden, trail) {
  const masks = allMasks(c, g)
  let placed = 0
  for (let i = 0; i < CELLS; i++) {
    if (g[i]) continue
    const m = masks[i]
    if (m === 0) return -1
    if ((m & (m - 1)) === 0) {
      const v = 31 - Math.clz32(m)
      if (!canPlace(c, g, i, v)) return -1
      g[i] = v
      trail.push(i)
      placed++
    }
  }
  if (hidden) {
    for (const u of c.units) {
      for (let v = 1; v <= 9; v++) {
        let where = -1
        let n = 0
        let done = false
        for (const j of u.cells) {
          if (g[j] === v) { done = true; break }
          if (!g[j] && masks[j] & (1 << v)) { n++; where = j }
        }
        if (done) continue
        if (n === 0) return -1
        if (n === 1 && !g[where]) {
          if (!canPlace(c, g, where, v)) return -1
          g[where] = v
          trail.push(where)
          placed++
        }
      }
    }
  }
  return placed
}

/**
 * Depth-first search with constraint propagation.
 * opts: limit (stop after this many solutions), rng (randomise digit order),
 * maxNodes (give up -> aborted:true).
 */
export function search(c, grid, opts = {}) {
  const { limit = 2, rng = null, maxNodes = Infinity } = opts
  const g = Int8Array.from(grid)
  const solutions = []
  let count = 0
  let nodes = 0
  let aborted = false

  const rec = () => {
    if (++nodes > maxNodes) { aborted = true; return }
    const trail = []
    for (;;) {
      const r = propagatePass(c, g, true, trail)
      if (r < 0) { for (const i of trail) g[i] = 0; return }
      if (r === 0) break
    }
    let best = -1
    let bestMask = 0
    let bestN = 10
    for (let i = 0; i < CELLS; i++) {
      if (g[i]) continue
      const m = cellMask(c, g, i)
      const n = popcount(m)
      if (n === 0) { for (const t of trail) g[t] = 0; return }
      if (n < bestN) { bestN = n; best = i; bestMask = m }
    }
    if (best < 0) {
      count++
      solutions.push(Int8Array.from(g))
    } else {
      let digits = []
      for (let v = 1; v <= 9; v++) if (bestMask & (1 << v)) digits.push(v)
      if (rng) digits = shuffle(digits, rng)
      for (const v of digits) {
        g[best] = v
        rec()
        g[best] = 0
        if (count >= limit || aborted) break
      }
    }
    for (const t of trail) g[t] = 0
  }
  rec()
  return { count, solutions, aborted, nodes }
}

export function solveOne(c, grid, rng = null, maxNodes = Infinity) {
  const r = search(c, grid, { limit: 1, rng, maxNodes })
  return r.solutions[0] || null
}

/** True iff the logic-only solver (singles) completes the grid. */
export function logicSolves(c, grid, hidden) {
  const g = Int8Array.from(grid)
  const trail = []
  for (;;) {
    const r = propagatePass(c, g, hidden, trail)
    if (r < 0) return false
    if (r === 0) break
  }
  return g.every((x) => x > 0)
}

/**
 * The next human-style step on grid g, or null. Types:
 *  - naked:  a cell with exactly one candidate left
 *  - hidden: a digit with exactly one possible cell inside a unit
 */
export function nextStep(c, g) {
  const masks = allMasks(c, g)
  let nakedCell = -1
  for (let i = 0; i < CELLS; i++) {
    if (g[i]) continue
    if (masks[i] === 0) return { type: 'dead', cell: i }
    if ((masks[i] & (masks[i] - 1)) === 0) { nakedCell = i; break }
  }
  if (nakedCell >= 0) {
    return { type: 'naked', cell: nakedCell, value: 31 - Math.clz32(masks[nakedCell]), masks }
  }
  for (const u of c.units) {
    for (let v = 1; v <= 9; v++) {
      let where = -1
      let n = 0
      let done = false
      for (const j of u.cells) {
        if (g[j] === v) { done = true; break }
        if (!g[j] && masks[j] & (1 << v)) { n++; where = j }
      }
      if (!done && n === 1) return { type: 'hidden', cell: where, value: v, unit: u, masks }
    }
  }
  return null
}

export { ALL }
