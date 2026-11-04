// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
// Lumen Restaurants 0.1.0-r14: the floor plan's drawing, as the owner approved
// it in the mockup "مخطط الصالة" (2026-10-01): the shapes and their chairs, the
// walls, doors and the rest, and where a table nobody placed yet stands.
//
// The drawing is 1000 by 648 units. The floor runs from 30 to 970 across and
// from 30 to 590 down; tables and the rest snap to 10.

export const VIEWBOX = '0 -8 1000 648'
export const FLOOR = { x: 30, y: 30, w: 940, h: 560 }
export const SHAPES = ['round', 'square', 'rect', 'booth']
export const SEAT_RANGE = { round: [1, 12], square: [1, 8], rect: [2, 12], booth: [2, 8] }
export const NEW_SEATS = { round: 4, square: 4, rect: 6, booth: 4 }
// Everything drawn that is not a table, and how big a new one starts.
export const KINDS = ['wall', 'door', 'window', 'fence', 'plant', 'cashier', 'kitchen', 'bar', 'wc', 'sink']
export const BOXES = new Set(['cashier', 'kitchen', 'bar', 'wc', 'sink'])
export const FX_NEW = {
  wall: { w: 200, h: 10 },
  door: { w: 94, h: 0 },
  window: { w: 120, h: 10 },
  fence: { w: 200, h: 0 },
  plant: { w: 0, h: 0 },
  cashier: { w: 140, h: 50 },
  kitchen: { w: 200, h: 140 },
  bar: { w: 180, h: 80 },
  wc: { w: 100, h: 90 },
  sink: { w: 150, h: 50 },
}

export const snap = (v) => Math.round(v / 10) * 10
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v))
export const norm = (deg) => ((Math.round(deg) % 360) + 360) % 360
const r1 = (n) => Math.round(n * 10) / 10

let seq = 0
export const newKey = (prefix) => `${prefix}${Date.now().toString(36)}${(seq += 1)}`

// Half the height of a shape turned by `rot`: where the badge sits above it.
function rotHalf(w, h, rot) {
  const a = (rot * Math.PI) / 180
  return (Math.abs(w * Math.sin(a)) + Math.abs(h * Math.cos(a))) / 2
}

const chair = (x, y, rot) => ({ x: r1(x), y: r1(y), rot: r1(rot) })

// A table's parts: its top, its chairs (or a booth's benches), the ring that
// lights up when it is chosen, and how far above its middle the badge goes.
export function geom(table) {
  const n = table.seats
  const chairs = []
  const benches = []
  let top
  let ring
  let hh
  if (table.shape === 'round') {
    const r = n <= 2 ? 26 : Math.round(22 + n * 3.2)
    for (let i = 0; i < n; i++) {
      const deg = -90 + (i * 360) / n
      const a = (deg * Math.PI) / 180
      chairs.push(chair(Math.cos(a) * (r + 11), Math.sin(a) * (r + 11), deg + 90))
    }
    top = { circle: true, r }
    ring = { circle: true, r: r + 24 }
    hh = r
  } else if (table.shape === 'booth') {
    const per = Math.ceil(n / 2)
    const bw = 64
    const bh = Math.max(80, 22 + 32 * per)
    const bx = bw / 2 + 17
    benches.push({ x: -bx - 11, y: -bh / 2 - 4, w: 22, h: bh + 8, rx: 7 })
    benches.push({ x: bx - 11, y: -bh / 2 - 4, w: 22, h: bh + 8, rx: 7 })
    benches.push({ x: -bx - 11, y: -bh / 2 - 13, w: 2 * bx + 22, h: 8, rx: 3 })
    top = { x: -bw / 2, y: -bh / 2, w: bw, h: bh, rx: 8 }
    const ex = bx + 16
    const eyT = bh / 2 + 18
    const eyB = bh / 2 + 9
    ring = { x: -ex, y: -eyT, w: 2 * ex, h: eyT + eyB, rx: 14 }
    hh = rotHalf(bw, bh, table.rot)
  } else {
    let counts
    let w
    let h
    let sp
    if (table.shape === 'square') {
      counts = [0, 0, 0, 0]
      for (let k = 0; k < n; k++) counts[k % 4] += 1
      w = h = Math.max(64, 30 + 30 * Math.max(...counts))
      sp = 30
    } else {
      const ends = n >= 6 ? 2 : 0
      const long = n - ends
      counts = [Math.ceil(long / 2), Math.floor(long / 2), ends / 2, ends / 2]
      w = Math.max(90, 26 + 32 * counts[0])
      h = 60
      sp = 32
    }
    const along = (c) => Array.from({ length: c }, (_, j) => (j - (c - 1) / 2) * sp)
    along(counts[0]).forEach((x) => chairs.push(chair(x, -h / 2 - 9, 0)))
    along(counts[1]).forEach((x) => chairs.push(chair(x, h / 2 + 9, 0)))
    along(counts[2]).forEach((y) => chairs.push(chair(-w / 2 - 9, y, 90)))
    along(counts[3]).forEach((y) => chairs.push(chair(w / 2 + 9, y, 90)))
    top = { x: -w / 2, y: -h / 2, w, h, rx: 10 }
    const rx = w / 2 + 20
    const ry = h / 2 + 20
    ring = { x: -rx, y: -ry, w: 2 * rx, h: 2 * ry, rx: 16 }
    hh = rotHalf(w, h, table.rot)
  }
  return { chairs, benches, top, ring, hh }
}

// The box a thing on the plan is picked up by in edit mode.
export function fxBounds(f) {
  if (f.kind === 'plant') return [44, 44]
  if (f.kind === 'door') return [f.w + 8, f.w / 2 + 16]
  if (f.kind === 'fence') return [f.w + 8, 16]
  if (BOXES.has(f.kind)) return [f.w + 6, f.h + 6]
  return [f.w + 8, f.h + 12]
}

// The walls of a new area: three sides and the bottom split by a door.
export function roomWalls(doorLabel = '') {
  const fx = (kind, x, y, w, h, rot = 0, label = '') => ({ key: newKey('x'), kind, x, y, w, h, rot, label })
  return [
    fx('wall', 500, 30, 950, 10),
    fx('wall', 30, 310, 570, 10, 90),
    fx('wall', 970, 310, 570, 10, 90),
    fx('wall', 230, 590, 410, 10),
    fx('wall', 752, 590, 446, 10),
    fx('door', 482, 590, 94, 0, 0, doorLabel),
  ]
}

// Tables nobody has placed yet (0, 0) get a place on a grid over the floor,
// in the cells no placed table stands in, in the order of their numbers.
export function autoPlace(tables) {
  const loose = tables.filter((t) => !t.x && !t.y)
  if (!loose.length) return
  const n = tables.length
  const cols = Math.max(1, Math.ceil(Math.sqrt((n * FLOOR.w) / FLOOR.h)))
  const rows = Math.max(1, Math.ceil(n / cols))
  const cw = FLOOR.w / cols
  const ch = FLOOR.h / rows
  const taken = new Set()
  for (const t of tables) {
    if (!t.x && !t.y) continue
    const c = Math.floor((t.x - FLOOR.x) / cw)
    const r = Math.floor((t.y - FLOOR.y) / ch)
    taken.add(`${c},${r}`)
  }
  const cells = []
  for (let r = 0; r < rows + 2; r++) {
    for (let c = 0; c < cols; c++) if (!taken.has(`${c},${r}`)) cells.push([c, r])
  }
  loose.forEach((t, i) => {
    const [c, r] = cells[i] || [i % cols, rows + Math.floor(i / cols)]
    t.x = clamp(snap(FLOOR.x + cw * (c + 0.5)), 60, 940)
    t.y = clamp(snap(FLOOR.y + ch * (r + 0.5)), 60, 600)
  })
}

// "21:05" as the guests read it, 9:05 م.
export function clockOf(hhmm, t) {
  const [h, m] = String(hhmm || '0:0').split(':').map(Number)
  const h12 = h % 12 || 12
  return `${h12}:${String(m || 0).padStart(2, '0')} ${h >= 12 ? t('PM') : t('AM')}`
}

// A table number sorts as a number when it is one: 2 before 10.
export function byNumber(a, b) {
  return (parseFloat(a.table_no) || 0) - (parseFloat(b.table_no) || 0) || String(a.table_no).localeCompare(String(b.table_no))
}
