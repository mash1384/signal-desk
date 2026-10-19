// Binance klines use UTC open times, inclusive start/end, at most 1000 rows.
// Keep the old horizon: recent charts used the last 1000; story detail used
// the first 1000 after t-60. Only discard rows the renderer cannot display.
export function recentLimit(earliest, step, now = Date.now() / 1000) {
  return Math.min(1000, Math.max(1, Math.ceil((now - earliest) / step) + 1));
}
export function sinceLimit(start, now = Date.now() / 1000) {
  return Math.min(1000, Math.max(1, Math.floor(now / 60) - Math.ceil(start / 60) + 1));
}
