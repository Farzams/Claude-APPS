export function describeRules(p) {
  const out = ['Fill the grid so every row, column and ' + (p.regions ? 'region' : '3×3 box') + ' contains 1–9 once.']
  if (p.killer.length) out.push('Killer cages (dashed): digits do not repeat in a cage and add up to the small number.')
  if (p.thermo.length) out.push('Thermometers: digits strictly increase from the round bulb along the line.')
  if (p.arrow.length) out.push('Arrows: the digits along an arrow add up to the number in its circle.')
  if (p.renban.length) out.push('Purple Renban lines: digits form a set of consecutive numbers in any order, no repeats.')
  if (p.whisper.some((w) => w.min === 5)) out.push('Green whisper lines: neighbouring digits differ by at least 5.')
  if (p.whisper.some((w) => w.min !== 5)) out.push('Whisper lines: neighbouring digits differ by at least the stated amount.')
  if (p.palindrome.length) out.push('Grey palindrome lines: the digits read the same from either end.')
  if (p.kropki.length)
    out.push(
      'Kropki dots: white = consecutive digits, black = one is double the other.' +
        (p.kropkiNegative ? ' Every such pair is marked: no dot means neither.' : ''),
    )
  if (p.antiKnight) out.push('Anti-knight: cells a chess knight’s move apart cannot hold the same digit.')
  if (p.antiKing) out.push('Anti-king: cells touching diagonally cannot hold the same digit.')
  if (p.nonConsecutive) out.push('Non-consecutive: orthogonally adjacent cells never differ by 1.')
  return out
}
