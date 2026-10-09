export const N = 9
export const CELLS = 81

export const rowOf = (i) => (i / 9) | 0
export const colOf = (i) => i % 9
export const idx = (r, c) => r * 9 + c
export const cellName = (i) => `R${rowOf(i) + 1}C${colOf(i) + 1}`

export const boxRegions = () =>
  Array.from({ length: CELLS }, (_, i) => ((rowOf(i) / 3) | 0) * 3 + ((colOf(i) / 3) | 0))

export function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function shuffle(arr, rng = Math.random) {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export const popcount = (m) => {
  let n = 0
  while (m) {
    m &= m - 1
    n++
  }
  return n
}

export const orthNeighbors = (i) => {
  const r = rowOf(i)
  const c = colOf(i)
  const out = []
  if (r > 0) out.push(i - 9)
  if (r < 8) out.push(i + 9)
  if (c > 0) out.push(i - 1)
  if (c < 8) out.push(i + 1)
  return out
}

export const kingNeighbors = (i) => {
  const r = rowOf(i)
  const c = colOf(i)
  const out = []
  for (let dr = -1; dr <= 1; dr++)
    for (let dc = -1; dc <= 1; dc++) {
      if (!dr && !dc) continue
      const rr = r + dr
      const cc = c + dc
      if (rr >= 0 && rr < 9 && cc >= 0 && cc < 9) out.push(idx(rr, cc))
    }
  return out
}

const KNIGHT = [
  [1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1],
]
export const knightNeighbors = (i) => {
  const r = rowOf(i)
  const c = colOf(i)
  const out = []
  for (const [dr, dc] of KNIGHT) {
    const rr = r + dr
    const cc = c + dc
    if (rr >= 0 && rr < 9 && cc >= 0 && cc < 9) out.push(idx(rr, cc))
  }
  return out
}

export const emptyPuzzle = () => ({
  name: 'Puzzle',
  givens: new Array(CELLS).fill(0),
  regions: null,
  antiKnight: false,
  antiKing: false,
  nonConsecutive: false,
  kropkiNegative: false,
  killer: [], // {cells, sum|null}
  thermo: [], // [cells]
  arrow: [], // {bulb, path:[cells]}
  renban: [], // [cells]
  whisper: [], // {cells, min}
  palindrome: [], // [cells]
  kropki: [], // {a, b, type:'white'|'black'}
})
