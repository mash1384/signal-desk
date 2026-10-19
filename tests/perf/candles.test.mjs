import assert from 'node:assert/strict';
import {test} from 'node:test';
import {recentLimit, sinceLimit} from '../../web/assets/df/candles.js';

test('every previously visible recent candle survives the smaller request', () => {
  const now = 1792342109;
  for (const step of [60, 300]) for (const ago of [0, 31, 600, 3600, 21600, 86400, 400000]) {
    const cutoff = now - ago - (step === 60 ? 1800 : 3600);
    const original = Array.from({length: 1000}, (_, i) => Math.floor(now / step) * step - (999 - i) * step);
    const limit = recentLimit(cutoff, step, now);
    assert.deepEqual(original.slice(-limit).filter(t => t >= cutoff), original.filter(t => t >= cutoff));
    assert.ok(limit >= 1 && limit <= 1000);
  }
  assert.ok(recentLimit(now - 1800, 60, now) < 1000);
});
test('story detail preserves the first-1000 cap and never needs future rows', () => {
  const now = 1792342109;
  for (const ago of [0, 59, 60, 3600, 59999, 86400]) {
    const start = now - ago - 60, first = Math.ceil(start / 60) * 60;
    const real = Array.from({length: 1000}, (_, i) => first + i * 60).filter(t => t <= now);
    assert.equal(sinceLimit(start, now), real.length);
  }
});
