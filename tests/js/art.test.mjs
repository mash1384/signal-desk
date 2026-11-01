// 소식 그림 고르기: 브라우저 쪽(web/assets/df/artm.js)이 파이썬(pipeline/art.py)과 같은 답을 내는지 — 정답은 tests/fixtures/art_cases.json(파이썬이 만든다)
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as M from '../../web/assets/df/artm.js';

const ix = JSON.parse(fs.readFileSync(new URL('../../web/assets/df/art.json', import.meta.url), 'utf8'));
const rows = JSON.parse(fs.readFileSync(new URL('../fixtures/art_cases.json', import.meta.url), 'utf8'));
test('artm.js picks the same subject and picture as pipeline/art.py', () => {
  assert.ok(rows.length > 100);
  for (const [ko, en, coins, id, name, pic] of rows) {
    let i = M.entity(ix, ko, en);
    if (i == null) for (const c of coins) { const j = ix.sym[String(c).toUpperCase()]; if (j != null) { i = j; break; } }
    assert.equal(i == null ? null : ix.e[i][0], name, ko || en);
    assert.equal(M.pick(ix, ko, en, coins, id), pic, ko || en);
  }
});
