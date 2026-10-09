import {
  CELLS, boxRegions, colOf, rowOf, idx, orthNeighbors, kingNeighbors, knightNeighbors,
} from './util.js'

const bit = (v) => 1 << v

/**
 * Turns a puzzle description into per-cell rule data used by the solver.
 *  - units:   all-different groups (rows, columns, regions)
 *  - extra:   additional "cannot equal" peers (knight / king)
 *  - checks:  per-cell value-dependent checks. Each is {label, cells, ok(g)};
 *             `ok` sees the grid with the candidate already written, 0 = empty,
 *             and must only fail when the rule is already violated or can no
 *             longer be satisfied.
 */
export function compile(p) {
  const regions = p.regions || boxRegions()
  const units = []
  for (let r = 0; r < 9; r++)
    units.push({ kind: 'row', label: `row ${r + 1}`, cells: Array.from({ length: 9 }, (_, c) => idx(r, c)) })
  for (let c = 0; c < 9; c++)
    units.push({ kind: 'col', label: `column ${c + 1}`, cells: Array.from({ length: 9 }, (_, r) => idx(r, c)) })
  const ids = [...new Set(regions)].sort((a, b) => a - b)
  ids.forEach((id, k) => {
    units.push({
      kind: 'region',
      label: p.regions ? `region ${k + 1}` : `box ${k + 1}`,
      cells: regions.map((x, i) => (x === id ? i : -1)).filter((i) => i >= 0),
    })
  })

  const cellUnits = Array.from({ length: CELLS }, () => [])
  for (const u of units) for (const i of u.cells) cellUnits[i].push(u)

  const extra = Array.from({ length: CELLS }, () => [])
  for (let i = 0; i < CELLS; i++) {
    if (p.antiKnight)
      for (const j of knightNeighbors(i)) extra[i].push({ j, label: 'anti-knight (a knight’s move away)' })
    if (p.antiKing)
      for (const j of kingNeighbors(i)) extra[i].push({ j, label: 'anti-king (touching diagonally)' })
  }

  const checks = Array.from({ length: CELLS }, () => [])
  const add = (cells, label, ok) => {
    const chk = { label, cells, ok }
    for (const i of cells) checks[i].push(chk)
  }

  for (const cage of p.killer) {
    const { cells, sum } = cage
    const label = sum == null ? 'killer cage (no repeats)' : `killer cage (sum ${sum})`
    add(cells, label, (g) => {
      let placed = 0
      let cnt = 0
      let mask = 0
      for (const j of cells) {
        const x = g[j]
        if (!x) continue
        if (mask & bit(x)) return false
        mask |= bit(x)
        placed += x
        cnt++
      }
      if (sum == null) return true
      const rem = cells.length - cnt
      if (placed > sum) return false
      if (rem === 0) return placed === sum
      let min = 0
      let max = 0
      let c = 0
      for (let d = 1; d <= 9 && c < rem; d++) if (!(mask & bit(d))) { min += d; c++ }
      if (c < rem) return false
      c = 0
      for (let d = 9; d >= 1 && c < rem; d--) if (!(mask & bit(d))) { max += d; c++ }
      const need = sum - placed
      return need >= min && need <= max
    })
  }

  for (const line of p.thermo) {
    const L = line.length
    add(line, 'thermometer (strictly increasing from the bulb)', (g) => {
      for (let a = 0; a < L; a++) {
        const x = g[line[a]]
        if (!x) continue
        if (x < a + 1 || x > 9 - (L - 1 - a)) return false
        for (let b = a + 1; b < L; b++) {
          const y = g[line[b]]
          if (y && y - x < b - a) return false
        }
      }
      return true
    })
  }

  for (const w of p.whisper) {
    const { cells, min } = w
    add(cells, `whisper line (neighbours differ by at least ${min})`, (g) => {
      for (let a = 0; a < cells.length; a++) {
        const x = g[cells[a]]
        if (!x) continue
        if (x - min < 1 && x + min > 9) return false
        if (a + 1 < cells.length) {
          const y = g[cells[a + 1]]
          if (y && Math.abs(x - y) < min) return false
        }
      }
      return true
    })
  }

  for (const line of p.renban) {
    const L = line.length
    add(line, 'Renban line (consecutive digits, any order)', (g) => {
      let mask = 0
      let lo = 10
      let hi = 0
      for (const j of line) {
        const x = g[j]
        if (!x) continue
        if (mask & bit(x)) return false
        mask |= bit(x)
        if (x < lo) lo = x
        if (x > hi) hi = x
      }
      return hi === 0 || hi - lo <= L - 1
    })
  }

  for (const line of p.palindrome) {
    const L = line.length
    add(line, 'palindrome line (reads the same both ways)', (g) => {
      for (let k = 0; k < L >> 1; k++) {
        const x = g[line[k]]
        const y = g[line[L - 1 - k]]
        if (x && y && x !== y) return false
      }
      return true
    })
  }

  for (const a of p.arrow) {
    const { bulb, path } = a
    add([bulb, ...path], 'arrow (digits on the arrow add up to the circle)', (g) => {
      let ps = 0
      let rem = 0
      for (const j of path) {
        if (g[j]) ps += g[j]
        else rem++
      }
      const b = g[bulb]
      if (!b) return ps + rem <= 9
      if (ps + rem > b) return false
      return ps + rem * 9 >= b
    })
  }

  const dotKey = (a, b) => (a < b ? a * CELLS + b : b * CELLS + a)
  const dots = new Map()
  for (const d of p.kropki) {
    dots.set(dotKey(d.a, d.b), d.type)
    add([d.a, d.b], d.type === 'white' ? 'white dot (digits are consecutive)' : 'black dot (one digit is double the other)', (g) => {
      const x = g[d.a]
      const y = g[d.b]
      if (!x || !y) return true
      return d.type === 'white' ? Math.abs(x - y) === 1 : x === 2 * y || y === 2 * x
    })
  }
  if (p.kropkiNegative) {
    for (let i = 0; i < CELLS; i++)
      for (const j of orthNeighbors(i)) {
        if (j < i || dots.has(dotKey(i, j))) continue
        add([i, j], 'no dot here (so not consecutive and not double)', (g) => {
          const x = g[i]
          const y = g[j]
          if (!x || !y) return true
          return Math.abs(x - y) !== 1 && x !== 2 * y && y !== 2 * x
        })
      }
  }

  if (p.nonConsecutive) {
    for (let i = 0; i < CELLS; i++)
      for (const j of orthNeighbors(i)) {
        if (j < i) continue
        add([i, j], 'non-consecutive (touching cells never differ by 1)', (g) => {
          const x = g[i]
          const y = g[j]
          return !x || !y || Math.abs(x - y) !== 1
        })
      }
  }

  const regionOf = regions
  return { puzzle: p, units, cellUnits, extra, checks, regionOf }
}

/** Fast boolean test: may `v` go in cell `i` of grid `g` (g[i] is overwritten temporarily)? */
export function canPlace(c, g, i, v) {
  for (const u of c.cellUnits[i]) {
    const cells = u.cells
    for (let k = 0; k < cells.length; k++) {
      const j = cells[k]
      if (j !== i && g[j] === v) return false
    }
  }
  for (const e of c.extra[i]) if (g[e.j] === v) return false
  const list = c.checks[i]
  if (list.length === 0) return true
  const old = g[i]
  g[i] = v
  let ok = true
  for (let k = 0; k < list.length; k++) {
    if (!list[k].ok(g)) { ok = false; break }
  }
  g[i] = old
  return ok
}

/** Like canPlace but says which rule is broken: {label, cells} or null. */
export function violation(c, g, i, v) {
  for (const u of c.cellUnits[i])
    for (const j of u.cells) if (j !== i && g[j] === v) return { label: u.label, cells: [j] }
  for (const e of c.extra[i]) if (g[e.j] === v) return { label: e.label, cells: [e.j] }
  const old = g[i]
  g[i] = v
  let res = null
  for (const chk of c.checks[i]) {
    if (!chk.ok(g)) { res = { label: chk.label, cells: chk.cells }; break }
  }
  g[i] = old
  return res
}

/** Cells whose current digit breaks a rule (taking the rest of the grid as is). */
export function findConflicts(c, grid) {
  const g = Int8Array.from(grid)
  const bad = new Set()
  for (let i = 0; i < CELLS; i++) {
    if (!g[i]) continue
    const v = g[i]
    const viol = violation(c, g, i, v)
    if (viol) {
      bad.add(i)
      // only flag rule-peers that truly clash (same digit); for shape rules flag the cell itself
      for (const j of viol.cells) if (g[j]) bad.add(j)
    }
  }
  return bad
}

export { rowOf, colOf }
