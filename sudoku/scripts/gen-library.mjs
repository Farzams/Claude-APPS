// Builds src/data/library.json: ready-to-play puzzles so the app starts instantly.
// Usage: node scripts/gen-library.mjs
import { writeFileSync, mkdirSync } from 'node:fs'
import { generatePuzzle, VARIANTS } from '../src/engine/generator.js'

const sets = [
  { variants: [], difficulty: 'easy' },
  { variants: [], difficulty: 'hard' },
  ...VARIANTS.map((v) => ({ variants: [v.id], difficulty: 'medium' })),
  { variants: ['thermo', 'antiKnight'], difficulty: 'medium' },
  { variants: ['killer', 'nonConsecutive'], difficulty: 'medium' },
  { variants: ['arrow', 'renban'], difficulty: 'medium' },
  { variants: ['whisper', 'antiKing'], difficulty: 'medium' },
]
const out = []
let seed = 20261009
for (const s of sets) {
  const p = generatePuzzle({ ...s, seed: seed++ })
  out.push(p)
  console.log(p.name, p.givens.filter(Boolean).length, 'givens')
}
mkdirSync('src/data', { recursive: true })
writeFileSync('src/data/library.json', JSON.stringify(out))
