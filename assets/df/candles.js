export function recentLimit(earliest, step, now = Date.now() / 1000) {
  return Math.min(1000, Math.max(1, Math.ceil((now - earliest) / step) + 1));
}
export function sinceLimit(start, now = Date.now() / 1000) {
  return Math.min(1000, Math.max(1, Math.floor(now / 60) - Math.ceil(start / 60) + 1));
}
