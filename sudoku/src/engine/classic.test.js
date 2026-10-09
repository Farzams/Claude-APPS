import { describe, it, expect } from 'vitest'
import { emptyPuzzle } from './util.js'
import { compile } from './compile.js'
import { search } from './solver.js'

const parse = (s) => Array.from(s, (ch) => (ch === '.' || ch === '0' ? 0 : +ch))

describe('classic solver', () => {
  it('solves a known puzzle uniquely', () => {
    const p = emptyPuzzle()
    p.givens = parse('53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79')
    const r = search(compile(p), p.givens, { limit: 2 })
    expect(r.count).toBe(1)
    expect(Array.from(r.solutions[0]).join('')).toBe(
      '534678912672195348198342567859761423426853791713924856961537284287419635345286179',
    )
  })

  it('finds many solutions on an empty grid (limited)', () => {
    const p = emptyPuzzle()
    const r = search(compile(p), p.givens, { limit: 2 })
    expect(r.count).toBe(2)
  })
})
