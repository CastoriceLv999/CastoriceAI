export const TRANSITION_DURATION = 3200
const clamp = value => Math.min(1, Math.max(0, value))
export function sweepEdges(progress,width){
  const ease=value=>{value=clamp(value);return value*value*(3-2*value)}
  const feather=width*.16
  return {feather,front:-feather+(width+2*feather)*ease(progress/.4),tail:-feather+(width+2*feather)*ease((progress-.58)/.42)}
}
export function startupFrame(elapsed, reduced = false) {
  const duration = reduced ? 500 : TRANSITION_DURATION
  const t = clamp(elapsed / duration)
  const smooth = x => { x=clamp(x); return x*x*(3-2*x) }
  // Both layers are opaque at the swap. Never reveal the underlying page early.
  return {
    progress: t,
    cover: t < .48 ? smooth(t/.40) : 1-smooth((t-.58)/.42),
    introOpacity: 1-smooth((t-.43)/.14),
    interfaceOpacity: smooth((t-.70)/.30),
    done: t >= 1,
  }
}
