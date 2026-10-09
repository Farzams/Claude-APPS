import { describe, it, expect } from 'vitest'
import LZString from 'lz-string'
import { importPuzzle } from './fpuzzles.js'
import { compile } from './compile.js'
import { search } from './solver.js'
import { makeHint } from './hints.js'
import { generatePuzzle } from './generator.js'

describe('import', () => {
  it('reads an 81 char string', () => {
    const { puzzle } = importPuzzle('53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79')
    expect(puzzle.givens[0]).toBe(5)
  })
  it('reads an f-puzzles style link', () => {
    const data = {
      size: 9, title: 'T',
      grid: Array.from({ length: 9 }, () => Array.from({ length: 9 }, () => ({}))),
      thermometer: [{ lines: [['R1C1', 'R1C2', 'R1C3']] }],
      killercage: [{ cells: ['R2C1', 'R2C2'], value: '5' }],
      antiknight: true,
    }
    const link = 'https://sudokupad.app/fpuzzles' + LZString.compressToBase64(JSON.stringify(data))
    const { puzzle } = importPuzzle(link)
    expect(puzzle.thermo).toEqual([[0, 1, 2]])
    expect(puzzle.killer[0].sum).toBe(5)
    expect(puzzle.antiKnight).toBe(true)
    const link2 = 'https://f-puzzles.com/?load=' + encodeURIComponent(LZString.compressToBase64(JSON.stringify(data)))
    expect(importPuzzle(link2).puzzle.thermo.length).toBe(1)
  })
})

describe('hints', () => {
  it('gives a valid hint on a generated puzzle', () => {
    const p = generatePuzzle({ variants: ['thermo'], difficulty: 'easy', seed: 5 })
    const c = compile(p)
    const g = Int8Array.from(p.givens)
    let n = 0
    while (g.some((x) => !x) && n++ < 100) {
      const h = makeHint(c, g, p.solution)
      expect(h.value).toBe(p.solution[h.cell])
      g[h.cell] = h.value
    }
    expect(Array.from(g)).toEqual(p.solution)
    expect(search(c, g).count).toBe(1)
  })
})
