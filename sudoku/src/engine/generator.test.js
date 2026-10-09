import { describe, it, expect } from 'vitest'
import { generatePuzzle, VARIANTS } from './generator.js'
import { compile } from './compile.js'
import { search } from './solver.js'

const check = (p) => {
  const r = search(compile(p), p.givens, { limit: 2 })
  expect(r.count).toBe(1)
  expect(Array.from(r.solutions[0])).toEqual(p.solution)
}

describe('generator', () => {
  it('classic, three levels', { timeout: 60000 }, () => {
    for (const d of ['easy', 'medium', 'hard']) {
      const t = Date.now()
      const p = generatePuzzle({ variants: [], difficulty: d, seed: 7 })
      console.log('classic', d, p.givens.filter(Boolean).length, 'givens', Date.now() - t, 'ms')
      check(p)
    }
  })

  for (const v of VARIANTS) {
    it(`variant ${v.id}`, { timeout: 120000 }, () => {
      const t = Date.now()
      const p = generatePuzzle({ variants: [v.id], difficulty: 'medium', seed: 11 })
      console.log(v.id, p.givens.filter(Boolean).length, 'givens', Date.now() - t, 'ms')
      check(p)
    })
  }

  it('combo', { timeout: 120000 }, () => {
    const t = Date.now()
    const p = generatePuzzle({ variants: ['thermo', 'antiKnight', 'kropki'], difficulty: 'hard', seed: 3 })
    console.log('combo', p.givens.filter(Boolean).length, 'givens', Date.now() - t, 'ms')
    check(p)
  })
})
