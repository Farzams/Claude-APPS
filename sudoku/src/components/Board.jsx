import { useRef } from 'react'
import { rowOf, colOf, boxRegions } from '../engine/util.js'

const S = 100 // cell size in SVG units
const PAD = 14
const cx = (i) => colOf(i) * S + S / 2
const cy = (i) => rowOf(i) * S + S / 2

const CORNER_SPOTS = [
  [0.2, 0.22], [0.8, 0.22], [0.2, 0.8], [0.8, 0.8], [0.5, 0.2], [0.5, 0.82], [0.2, 0.5], [0.8, 0.5], [0.5, 0.5],
]

function pointsOf(cells) {
  return cells.map((i) => `${cx(i)},${cy(i)}`).join(' ')
}

/** Dashed inset outline for a killer cage, built edge by edge. */
function cageSegments(cells) {
  const set = new Set(cells.map((i) => rowOf(i) * 9 + colOf(i)))
  const has = (r, c) => r >= 0 && r < 9 && c >= 0 && c < 9 && set.has(r * 9 + c)
  const e = 8
  const segs = []
  for (const i of cells) {
    const r = rowOf(i)
    const c = colOf(i)
    for (const [nr, nc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      if (has(r + nr, c + nc)) continue
      // tangent directions
      const [tr, tc] = nr === 0 ? [1, 0] : [0, 1]
      const ends = [-1, 1].map((sgn) => {
        const along = has(r + tr * sgn, c + tc * sgn)
        const diag = has(r + tr * sgn + nr, c + tc * sgn + nc)
        let off = S / 2 - e
        if (along) off = diag ? S / 2 + e : S / 2
        const x = c * S + S / 2 + nc * (S / 2 - e) + tc * sgn * off
        const y = r * S + S / 2 + nr * (S / 2 - e) + tr * sgn * off
        return [x, y]
      })
      segs.push(`M${ends[0][0]} ${ends[0][1]}L${ends[1][0]} ${ends[1][1]}`)
    }
  }
  return segs.join('')
}

function Arrow({ a }) {
  const pts = [a.bulb, ...a.path]
  const R = 36
  const b = pts[1]
  const dx = cx(b) - cx(a.bulb)
  const dy = cy(b) - cy(a.bulb)
  const len = Math.hypot(dx, dy)
  const sx = cx(a.bulb) + (dx / len) * R
  const sy = cy(a.bulb) + (dy / len) * R
  const end = pts[pts.length - 1]
  const prev = pts[pts.length - 2]
  const ex = cx(end)
  const ey = cy(end)
  const ang = Math.atan2(ey - cy(prev), ex - cx(prev))
  const h = 20
  const p1 = [ex - h * Math.cos(ang - 0.5), ey - h * Math.sin(ang - 0.5)]
  const p2 = [ex - h * Math.cos(ang + 0.5), ey - h * Math.sin(ang + 0.5)]
  const d = `M${sx} ${sy}` + pts.slice(1).map((i) => `L${cx(i)} ${cy(i)}`).join('')
  return (
    <g className="arrow">
      <circle cx={cx(a.bulb)} cy={cy(a.bulb)} r={R} />
      <path d={d} fill="none" />
      <path d={`M${p1[0]} ${p1[1]}L${ex} ${ey}L${p2[0]} ${p2[1]}`} fill="none" />
    </g>
  )
}

export default function Board({ puzzle, values, corner, center, selected, conflicts, wrong, hint, onSelect }) {
  const svgRef = useRef(null)
  const dragging = useRef(false)
  const regions = puzzle.regions || boxRegions()
  const sel = new Set(selected)
  const focusVal = selected.length === 1 ? values[selected[0]] : 0

  const cellAt = (e) => {
    const rect = svgRef.current.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * (9 * S + 2 * PAD) - PAD
    const y = ((e.clientY - rect.top) / rect.height) * (9 * S + 2 * PAD) - PAD
    const c = Math.floor(x / S)
    const r = Math.floor(y / S)
    return r < 0 || r > 8 || c < 0 || c > 8 ? -1 : r * 9 + c
  }

  const down = (e) => {
    const i = cellAt(e)
    if (i < 0) return
    svgRef.current.setPointerCapture?.(e.pointerId)
    dragging.current = true
    const additive = e.ctrlKey || e.metaKey || e.shiftKey
    if (additive) onSelect(sel.has(i) ? selected.filter((x) => x !== i) : [...selected, i])
    else onSelect([i])
  }
  const move = (e) => {
    if (!dragging.current) return
    const i = cellAt(e)
    if (i >= 0 && !sel.has(i)) onSelect([...selected, i])
  }
  const up = () => { dragging.current = false }

  const edges = []
  for (let i = 0; i < 81; i++) {
    const r = rowOf(i)
    const c = colOf(i)
    if (c < 8 && regions[i] !== regions[i + 1]) edges.push(`M${(c + 1) * S} ${r * S}v${S}`)
    if (r < 8 && regions[i] !== regions[i + 9]) edges.push(`M${c * S} ${(r + 1) * S}h${S}`)
  }

  return (
    <svg
      ref={svgRef}
      className="board"
      viewBox={`${-PAD} ${-PAD} ${9 * S + 2 * PAD} ${9 * S + 2 * PAD}`}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      role="grid"
      aria-label="Sudoku board"
    >
      {Array.from({ length: 81 }, (_, i) => {
        let cls = 'cell'
        if (sel.has(i)) cls += ' sel'
        else if (focusVal && values[i] === focusVal) cls += ' same'
        if (conflicts.has(i)) cls += ' conflict'
        if (wrong.has(i)) cls += ' wrong'
        if (hint?.highlight?.includes(i)) cls += ' hinted'
        return <rect key={i} className={cls} x={colOf(i) * S} y={rowOf(i) * S} width={S} height={S} />
      })}

      <g className="lines">
        {puzzle.renban.map((l, k) => <polyline key={`rb${k}`} className="renban" points={pointsOf(l)} />)}
        {puzzle.whisper.map((w, k) => <polyline key={`wh${k}`} className="whisper" points={pointsOf(w.cells)} />)}
        {puzzle.palindrome.map((l, k) => <polyline key={`pa${k}`} className="palin" points={pointsOf(l)} />)}
        {puzzle.thermo.map((l, k) => (
          <g key={`th${k}`} className="thermo">
            <polyline points={pointsOf(l)} />
            <circle cx={cx(l[0])} cy={cy(l[0])} r={34} />
          </g>
        ))}
        {puzzle.arrow.map((a, k) => <Arrow key={`ar${k}`} a={a} />)}
      </g>

      <g className="gridlines">
        {Array.from({ length: 8 }, (_, k) => (
          <g key={k}>
            <line x1={(k + 1) * S} y1={0} x2={(k + 1) * S} y2={9 * S} />
            <line x1={0} y1={(k + 1) * S} x2={9 * S} y2={(k + 1) * S} />
          </g>
        ))}
        <path className="regions" d={edges.join('')} />
        <rect className="frame" x={0} y={0} width={9 * S} height={9 * S} />
      </g>

      {puzzle.killer.map((cage, k) => {
        const top = [...cage.cells].sort((a, b) => a - b)[0]
        return (
          <g key={`k${k}`} className="cage">
            <path d={cageSegments(cage.cells)} />
            {cage.sum != null && (
              <>
                <rect x={colOf(top) * S + 5} y={rowOf(top) * S + 5} width={String(cage.sum).length * 13 + 8} height={22} />
                <text x={colOf(top) * S + 9} y={rowOf(top) * S + 22}>{cage.sum}</text>
              </>
            )}
          </g>
        )
      })}

      <g className="dots">
        {puzzle.kropki.map((d, k) => (
          <circle
            key={k}
            className={d.type}
            cx={(cx(d.a) + cx(d.b)) / 2}
            cy={(cy(d.a) + cy(d.b)) / 2}
            r={13}
          />
        ))}
      </g>

      {Array.from({ length: 81 }, (_, i) => {
        const v = values[i]
        const given = puzzle.givens[i] > 0
        if (v) {
          return (
            <text
              key={i}
              className={`digit ${given ? 'given' : 'entry'}${wrong.has(i) ? ' bad' : ''}`}
              x={cx(i)}
              y={cy(i) + 4}
            >
              {v}
            </text>
          )
        }
        const cm = []
        for (let d = 1; d <= 9; d++) if (corner[i] & (1 << d)) cm.push(d)
        const cen = []
        for (let d = 1; d <= 9; d++) if (center[i] & (1 << d)) cen.push(d)
        return (
          <g key={i}>
            {cm.map((d, k) => (
              <text
                key={d}
                className="corner"
                x={colOf(i) * S + CORNER_SPOTS[k][0] * S}
                y={rowOf(i) * S + CORNER_SPOTS[k][1] * S + 1}
              >
                {d}
              </text>
            ))}
            {cen.length > 0 && (
              <text className={`center${cen.length > 5 ? ' tiny' : ''}`} x={cx(i)} y={cy(i) + 1}>
                {cen.join('')}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
