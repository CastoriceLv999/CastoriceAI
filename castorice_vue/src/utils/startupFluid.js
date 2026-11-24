import { sweepEdges } from './startupTransition.js'

const clamp = value => Math.max(0, Math.min(1, value))
const smooth = value => { const t = clamp(value); return t * t * (3 - 2 * t) }

// A moving, uneven edge keeps the painted wipe continuous across different aspect ratios.
function edgePath(ctx, edge, width, height, time, reverse = false) {
  const wave = (y) => Math.sin(y * 8 + time * .0012) * width * .025 + Math.sin(y * 17 - time * .0008) * width * .012
  ctx.beginPath()
  ctx.moveTo(reverse ? 0 : width, 0)
  for (let i = 0; i <= 32; i++) {
    const y = i / 32
    ctx.lineTo(edge + wave(y), y * height)
  }
  ctx.lineTo(reverse ? 0 : width, height)
  ctx.closePath()
}

// Rounded, tapered crescents evoke the concentric hand-painted swirl in the reference.
function ribbon(ctx, cx, cy, radiusX, radiusY, angle, length, thickness, color) {
  const steps = 40
  const point = (u, outer) => {
    const a = angle + u * length
    const taper = Math.pow(Math.sin(Math.PI * u), .65)
    const r = 1 + (outer ? 1 : -1) * thickness * taper
    return [cx + Math.cos(a) * radiusX * r, cy + Math.sin(a) * radiusY * r]
  }
  ctx.beginPath()
  for (let i = 0; i <= steps; i++) {
    const [x, y] = point(i / steps, true)
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
  }
  for (let i = steps; i >= 0; i--) {
    const [x, y] = point(i / steps, false)
    ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
}

export function paintFluidTransition(ctx, progress, width, height, time) {
  const { front, tail } = sweepEdges(progress, width)
  ctx.clearRect(0, 0, width, height)

  // Cover the old video completely during the handoff, then uncover from the left.
  const base = ctx.createLinearGradient(0, 0, width, height)
  base.addColorStop(0, '#382352')
  base.addColorStop(.55, '#704a94')
  base.addColorStop(1, '#9c73b5')
  ctx.fillStyle = base
  ctx.fillRect(0, 0, width, height)
  ctx.globalCompositeOperation = 'destination-out'
  ctx.fillStyle = '#fff'
  edgePath(ctx, front, width, height, time); ctx.fill()
  edgePath(ctx, tail, width, height, time, true); ctx.fill()
  ctx.globalCompositeOperation = 'source-over'

  const visible = smooth(progress / .09) * (1 - smooth((progress - .74) / .26))
  if (!visible) return
  const motion = smooth(progress / .95)
  const cx = width * (-.30 + 1.58 * motion)
  const cy = height * .53
  const scale = Math.max(width, height * 1.25)
  const rotation = -.65 + progress * 3.8
  ctx.save()
  ctx.globalAlpha = visible
  const ribbons = [
    [1.05, .60, -.35, 4.7, .16, '#b891d5'],
    [.84, .48, .95, 4.5, .13, '#e8d4f5'],
    [.69, .39, 2.15, 4.2, .13, '#9068b6'],
    [.53, .30, -.15, 4.6, .14, '#f7edf9'],
    [.38, .22, 1.5, 4.1, .13, '#c9a3e3'],
    [.26, .15, 2.8, 3.8, .11, '#77549e'],
  ]
  for (const [rx, ry, offset, length, thickness, color] of ribbons) {
    ribbon(ctx, cx, cy, scale * rx, scale * ry, rotation + offset, length, thickness, color)
  }
  // Small tapered accents make the broad shapes feel brushed, without emoji or sprites.
  for (let i = 0; i < 7; i++) {
    const a = rotation + i * .88
    ribbon(ctx, cx, cy, scale * (.30 + i * .095), scale * (.17 + i * .055), a, .34 + (i % 3) * .12, .025, i % 2 ? '#f5e9fa' : '#d8b6ee')
  }
  ctx.restore()
}
