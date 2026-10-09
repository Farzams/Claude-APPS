import {
  CELLS, emptyPuzzle, mulberry32, shuffle, orthNeighbors, kingNeighbors, rowOf, colOf, boxRegions,
} from './util.js'
import { compile } from './compile.js'
import { search, solveOne, logicSolves } from './solver.js'

export const VARIANTS = [
  { id: 'killer', name: 'Killer', blurb: 'Cages with a sum; no repeats inside a cage.' },
  { id: 'thermo', name: 'Thermometer', blurb: 'Digits strictly increase from the bulb.' },
  { id: 'arrow', name: 'Arrow', blurb: 'Digits on an arrow add up to the circle.' },
  { id: 'renban', name: 'Renban', blurb: 'A purple line holds consecutive digits in any order.' },
  { id: 'whisper', name: 'German whisper', blurb: 'Neighbours on a green line differ by 5 or more.' },
  { id: 'palindrome', name: 'Palindrome', blurb: 'A grey line reads the same in both directions.' },
  { id: 'kropki', name: 'Kropki', blurb: 'White: consecutive. Black: one is double the other. No dot: neither.' },
  { id: 'antiKnight', name: 'Anti-knight', blurb: 'Cells a chess knight’s move apart differ.' },
  { id: 'antiKing', name: 'Anti-king', blurb: 'Diagonally touching cells differ.' },
  { id: 'nonConsecutive', name: 'Non-consecutive', blurb: 'Orthogonal neighbours never differ by 1.' },
]

export const DIFFICULTIES = ['easy', 'medium', 'hard']

function randomWalk(len, used, rng, diag, validate) {
  for (let attempt = 0; attempt < 40; attempt++) {
    const free = []
    for (let i = 0; i < CELLS; i++) if (!used.has(i)) free.push(i)
    if (!free.length) return null
    const path = [free[Math.floor(rng() * free.length)]]
    while (path.length < len) {
      const last = path[path.length - 1]
      const opts = (diag ? kingNeighbors(last) : orthNeighbors(last)).filter(
        (j) => !used.has(j) && !path.includes(j),
      )
      if (!opts.length) break
      path.push(opts[Math.floor(rng() * opts.length)])
    }
    if (path.length >= Math.min(len, 3) && (!validate || validate(path))) return path
  }
  return null
}

const sharesUnit = (a, b) =>
  rowOf(a) === rowOf(b) || colOf(a) === colOf(b) || boxRegions()[a] === boxRegions()[b]

function addLines(count, lenRange, used, rng, diag, validate, push) {
  for (let k = 0; k < count; k++) {
    const len = lenRange[0] + Math.floor(rng() * (lenRange[1] - lenRange[0] + 1))
    const path = randomWalk(len, used, rng, diag, validate)
    if (!path) continue
    path.forEach((i) => used.add(i))
    push(path)
  }
}

function makeCages(rng) {
  const owner = new Array(CELLS).fill(-1)
  const cages = []
  for (const start of shuffle([...Array(CELLS).keys()], rng)) {
    if (owner[start] >= 0) continue
    const target = 2 + Math.floor(rng() * 3) // 2..4
    const cells = [start]
    owner[start] = cages.length
    while (cells.length < target) {
      const opts = cells.flatMap(orthNeighbors).filter((j) => owner[j] < 0)
      if (!opts.length) break
      const j = opts[Math.floor(rng() * opts.length)]
      owner[j] = cages.length
      cells.push(j)
    }
    cages.push(cells)
  }
  // merge singletons into a neighbouring cage when that keeps it small
  for (let k = 0; k < cages.length; k++) {
    if (cages[k].length !== 1) continue
    const i = cages[k][0]
    const nb = orthNeighbors(i).map((j) => owner[j]).filter((o) => o !== k && cages[o].length < 5)
    if (!nb.length) continue
    const o = nb[Math.floor(rng() * nb.length)]
    cages[o].push(i)
    owner[i] = o
    cages[k] = []
  }
  return cages.filter((c) => c.length).map((cells) => ({ cells, sum: null }))
}

function buildGeometry(variants, rng) {
  const p = emptyPuzzle()
  const has = (v) => variants.includes(v)
  p.antiKnight = has('antiKnight')
  p.antiKing = has('antiKing')
  p.nonConsecutive = has('nonConsecutive')
  const used = new Set()
  if (has('palindrome'))
    addLines(2 + Math.floor(rng() * 2), [5, 7], used, rng, false,
      (path) => {
        const L = path.length
        for (let k = 0; k < L >> 1; k++) if (sharesUnit(path[k], path[L - 1 - k])) return false
        return true
      },
      (path) => p.palindrome.push(path))
  if (has('whisper'))
    addLines(3 + Math.floor(rng() * 2), [4, 7], used, rng, false, null,
      (path) => p.whisper.push({ cells: path, min: 5 }))
  if (has('renban'))
    addLines(3 + Math.floor(rng() * 2), [3, 5], used, rng, false, null, (path) => p.renban.push(path))
  if (has('thermo'))
    addLines(4 + Math.floor(rng() * 3), [3, 7], used, rng, false, null, (path) => p.thermo.push(path))
  if (has('arrow'))
    addLines(3 + Math.floor(rng() * 2), [3, 5], used, rng, true, null,
      (path) => p.arrow.push({ bulb: path[0], path: path.slice(1) }))
  if (has('killer')) p.killer = makeCages(rng)
  return p
}

/** Fill in the value-derived parts (cage sums, kropki dots) from a solution. */
function finalize(p, sol, variants) {
  for (const cage of p.killer) cage.sum = cage.cells.reduce((s, i) => s + sol[i], 0)
  if (variants.includes('kropki')) {
    p.kropkiNegative = true
    p.kropki = []
    for (let i = 0; i < CELLS; i++)
      for (const j of orthNeighbors(i)) {
        if (j < i) continue
        const x = sol[i]
        const y = sol[j]
        if (Math.abs(x - y) === 1) p.kropki.push({ a: i, b: j, type: 'white' })
        else if (x === 2 * y || y === 2 * x) p.kropki.push({ a: i, b: j, type: 'black' })
      }
  }
}

function carve(c, sol, difficulty, rng) {
  const givens = Int8Array.from(sol)
  const pairs = []
  const seen = new Set()
  for (const i of shuffle([...Array(CELLS).keys()], rng)) {
    if (seen.has(i)) continue
    const j = CELLS - 1 - i
    seen.add(i)
    seen.add(j)
    pairs.push(i === j ? [i] : [i, j])
  }
  const ok = (g) => {
    if (difficulty === 'easy') return logicSolves(c, g, false)
    if (difficulty === 'medium') return logicSolves(c, g, true)
    if (logicSolves(c, g, true)) return true
    const r = search(c, g, { limit: 2, maxNodes: 4000 })
    return !r.aborted && r.count === 1
  }
  for (const cells of pairs) {
    const saved = cells.map((i) => givens[i])
    cells.forEach((i) => (givens[i] = 0))
    if (!ok(givens)) cells.forEach((i, k) => (givens[i] = saved[k]))
  }
  return givens
}

/**
 * Build a puzzle with the chosen variant rules. Always has exactly one
 * solution under the rules the app understands.
 */
export function generatePuzzle({ variants = [], difficulty = 'medium', seed = Date.now() } = {}) {
  const rng = mulberry32(seed)
  for (let attempt = 0; attempt < 60; attempt++) {
    const p = buildGeometry(variants, rng)
    const sol = solveOne(compile(p), p.givens, rng, 20000)
    if (!sol) continue
    finalize(p, sol, variants)
    const c = compile(p)
    p.givens = Array.from(carve(c, sol, difficulty, rng))
    p.solution = Array.from(sol)
    p.unique = true
    p.variants = variants.slice()
    p.difficulty = difficulty
    p.seed = seed
    p.name = describeName(variants, difficulty)
    return p
  }
  throw new Error('Could not build a puzzle for that combination; try fewer variants.')
}

export function describeName(variants, difficulty) {
  const names = variants.map((v) => VARIANTS.find((x) => x.id === v)?.name).filter(Boolean)
  const base = names.length ? names.join(' + ') : 'Classic'
  return `${base} (${difficulty})`
}
