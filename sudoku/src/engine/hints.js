import { cellName, rowOf, colOf } from './util.js'
import { violation } from './compile.js'
import { nextStep, solveOne } from './solver.js'

/** Why can't digit d go in cell i? A short human reason, or null. */
function reason(c, g, i, d) {
  const v = violation(c, g, i, d)
  if (!v) return null
  if (v.cells.length === 1 && c.cellUnits[i].some((u) => u.label === v.label))
    return `${v.label} already has a ${d} (${cellName(v.cells[0])})`
  return v.label
}

/**
 * Produce a hint for the player's current grid `g` (givens + entered digits).
 * Returns {kind, cell, value, message, highlight}.
 */
export function makeHint(c, g, solution) {
  if (solution) {
    for (let i = 0; i < 81; i++)
      if (g[i] && g[i] !== solution[i])
        return {
          kind: 'wrong', cell: i, value: null, highlight: [i],
          message: `${cellName(i)} holds a ${g[i]}, which cannot be right. Fix that cell first.`,
        }
  }
  const step = nextStep(c, g)
  if (step && step.type === 'dead') {
    return {
      kind: 'wrong', cell: step.cell, value: null, highlight: [step.cell],
      message: `${cellName(step.cell)} has no legal digit left, so an earlier entry must be wrong.`,
    }
  }
  if (step && step.type === 'naked') {
    const { cell, value } = step
    const parts = []
    const hl = new Set([cell])
    for (let d = 1; d <= 9; d++) {
      if (d === value) continue
      const v = violation(c, g, cell, d)
      if (v) {
        v.cells.forEach((j) => hl.add(j))
        parts.push(`${d}: ${reason(c, g, cell, d)}`)
      }
    }
    return {
      kind: 'naked', cell, value, highlight: [...hl],
      message: `${cellName(cell)} can only be ${value}. Every other digit is ruled out – ${parts.join('; ')}.`,
    }
  }
  if (step && step.type === 'hidden') {
    const { cell, value, unit } = step
    return {
      kind: 'hidden', cell, value, highlight: [...new Set([cell, ...unit.cells])],
      message: `In ${unit.label}, the digit ${value} has only one place left: ${cellName(cell)}.`,
    }
  }
  const sol = solution || solveOne(c, g)
  if (!sol) return { kind: 'none', cell: null, value: null, highlight: [], message: 'No solution exists from this position.' }
  // pick an empty cell with the fewest candidates as the reveal target
  let best = -1
  let bestN = 10
  for (let i = 0; i < 81; i++) {
    if (g[i]) continue
    let n = 0
    for (let d = 1; d <= 9; d++) if (!violation(c, g, i, d)) n++
    if (n < bestN) { bestN = n; best = i }
  }
  return {
    kind: 'deep', cell: best, value: sol[best], highlight: [best],
    message: `No single is available, so this needs a deeper idea (pairs, rule interactions, or trying a digit). ${cellName(best)} has ${bestN} candidates; checking them against the whole puzzle shows it is ${sol[best]}. Look at row ${rowOf(best) + 1} / column ${colOf(best) + 1} for the clue.`,
  }
}
