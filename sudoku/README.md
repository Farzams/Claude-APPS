# Sudoku (variants)

A React + Vite Sudoku app with the constraint types used in Cracking the Cryptic puzzles.

```
npm install
npm run dev      # play at http://localhost:5173
npm test         # solver / generator / import tests
npm run build    # static site in dist/
npm run library  # regenerate src/data/library.json (ready-to-play puzzles)
```

## Variants
Classic, Killer, Thermometer, Arrow, Renban, German whisper, Palindrome, Kropki (with the "no dot means no relation" rule),
Anti-knight, Anti-king, Non-consecutive. Any combination can be generated at once.

## Features
- Digit / corner / centre marks, multi-select (drag or Ctrl), undo/redo, timer, autosave in the browser
- Check (against the unique solution), live rule-conflict highlighting
- Hints with explanations: naked single, hidden single, or a deeper reveal
- Generator (in a Web Worker) with easy / medium / hard: easy needs only naked singles, medium adds hidden singles, hard is
  merely unique. Every generated puzzle is verified to have exactly one solution.
- Import: 81-digit strings, f-puzzles links/codes, SudokuPad `.../fpuzzles<data>` links.

## Layout
`src/engine/compile.js` turns rules into per-cell checks; `solver.js` is a propagating DFS; `generator.js`, `hints.js` and
`fpuzzles.js` build on it. To add a variant: data field in `util.js`, a check in `compile.js`, drawing in
`components/Board.jsx`, geometry in `generator.js`.

## Known limits
- 9x9 only. Not yet supported: sandwich, little killer, skyscraper, X-sum, jigsaw generation (jigsaw import works),
  multi-cell arrow bulbs.
- Short SudokuPad IDs live on SudokuPad's servers and can't be fetched from here.
- The f-puzzles import follows the format from memory and is tested only against self-made data, not a live CTC link.
