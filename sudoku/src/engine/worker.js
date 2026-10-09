import { generatePuzzle } from './generator.js'

self.onmessage = (e) => {
  try {
    self.postMessage({ ok: true, puzzle: generatePuzzle(e.data) })
  } catch (err) {
    self.postMessage({ ok: false, error: String(err.message || err) })
  }
}
