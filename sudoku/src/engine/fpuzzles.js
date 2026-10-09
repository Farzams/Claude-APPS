import LZString from 'lz-string'
import { emptyPuzzle, idx } from './util.js'

const cellIndex = (s) => {
  const m = /^R(\d+)C(\d+)$/i.exec(String(s).trim())
  if (!m) throw new Error(`Bad cell reference "${s}"`)
  return idx(+m[1] - 1, +m[2] - 1)
}
const lines = (o) => (o.lines || (o.cells ? [o.cells] : [])).map((l) => l.map(cellIndex))

function tryDecode(text) {
  const t = text.trim()
  if (t.startsWith('{')) return JSON.parse(t)
  for (const fn of [LZString.decompressFromBase64, LZString.decompressFromEncodedURIComponent]) {
    try {
      const out = fn.call(LZString, t.replace(/ /g, '+'))
      if (out && out.startsWith('{')) return JSON.parse(out)
    } catch { /* try next */ }
  }
  return null
}

/** Convert f-puzzles JSON into the app's puzzle model. Returns {puzzle, notes}. */
export function fromFPuzzles(data) {
  if (data.size && data.size !== 9) throw new Error('Only 9×9 puzzles are supported.')
  const p = emptyPuzzle()
  const notes = []
  p.name = data.title || 'Imported puzzle'
  if (data.ruleset) p.rules = String(data.ruleset)
  const regions = []
  let regionsOk = true
  ;(data.grid || []).forEach((row, r) =>
    row.forEach((cell, c) => {
      if (cell && cell.given && cell.value) p.givens[idx(r, c)] = +cell.value
      if (cell && Number.isInteger(cell.region)) regions[idx(r, c)] = cell.region
      else regionsOk = false
    }))
  if (regionsOk && regions.length === 81 && new Set(regions).size === 9) p.regions = regions
  p.antiKnight = !!data.antiknight
  p.antiKing = !!data.antiking
  p.nonConsecutive = !!data.nonconsecutive
  for (const k of data.killercage || []) {
    const cells = (k.cells || []).map(cellIndex)
    p.killer.push({ cells, sum: k.value === undefined || k.value === '' ? null : +k.value })
  }
  for (const t of data.thermometer || []) for (const l of lines(t)) p.thermo.push(l)
  for (const t of data.arrow || []) {
    const bulbs = (t.cells || []).map(cellIndex)
    for (const l of t.lines || []) {
      const cl = l.map(cellIndex)
      const bulb = bulbs[0] ?? cl[0]
      const path = cl.filter((x) => x !== bulb)
      if (path.length) p.arrow.push({ bulb, path })
    }
  }
  for (const t of data.renban || []) for (const l of lines(t)) p.renban.push(l)
  for (const t of data.whispers || []) for (const l of lines(t)) p.whisper.push({ cells: l, min: +t.value || 5 })
  for (const t of data.palindrome || []) for (const l of lines(t)) p.palindrome.push(l)
  const dot = (list, type) => {
    for (const d of list || []) {
      const [a, b] = (d.cells || []).map(cellIndex)
      if (a === undefined || b === undefined) continue
      if (type === 'white' && d.value && +d.value !== 1) { notes.push('A difference dot with a value other than 1 was skipped.'); continue }
      if (type === 'black' && d.value && +d.value !== 2) { notes.push('A ratio dot other than 1:2 was skipped.'); continue }
      p.kropki.push({ a, b, type })
    }
  }
  dot(data.difference, 'white')
  dot(data.ratio, 'black')
  const neg = data.negative || []
  if (neg.includes('difference') && neg.includes('ratio')) p.kropkiNegative = true
  else if (neg.length) notes.push('A negative-dot rule that only covers one dot type is not supported and was ignored.')

  const known = new Set([
    'size', 'title', 'author', 'ruleset', 'grid', 'antiknight', 'antiking', 'nonconsecutive', 'killercage',
    'thermometer', 'arrow', 'renban', 'whispers', 'palindrome', 'difference', 'ratio', 'negative', 'solution',
    'truecandidatesoptions', 'disabledlogic',
  ])
  const unsupported = Object.keys(data).filter((k) => !known.has(k) && data[k] && (Array.isArray(data[k]) ? data[k].length : data[k] === true))
  if (unsupported.length)
    notes.push(`These rules/features are not supported yet and were ignored: ${unsupported.join(', ')}. The puzzle may have several solutions here.`)
  return { puzzle: p, notes }
}

/** Accepts an 81-char digit string, f-puzzles link/code, or f-puzzles JSON. */
export function importPuzzle(input) {
  const text = String(input || '').trim()
  if (!text) throw new Error('Paste a puzzle first.')
  const digits = text.replace(/\s+/g, '')
  if (/^[0-9.]{81}$/.test(digits)) {
    const p = emptyPuzzle()
    p.name = 'Imported classic'
    p.givens = Array.from(digits, (ch) => (ch === '.' ? 0 : +ch))
    return { puzzle: p, notes: [] }
  }
  let token = text
  const load = /[?&]load=([^&#\s]+)/.exec(text)
  if (load) token = decodeURIComponent(load[1])
  else {
    const m = /(?:fpuzzles|fpuz)([A-Za-z0-9+/=_\-%]+)/.exec(text)
    if (m) token = decodeURIComponent(m[1])
  }
  const data = tryDecode(token)
  if (data) return fromFPuzzles(data)
  throw new Error(
    'Could not read that. Supported: an 81-character digit string, an f-puzzles link or code, or a SudokuPad link of the form sudokupad.app/fpuzzles…. Short SudokuPad IDs need SudokuPad’s server and cannot be read offline.',
  )
}
