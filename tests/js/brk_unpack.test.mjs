// 브리핑 첫 자료(threads-pack.json): brk.js unpack() 이 파이썬 pack_threads 결과를 threads-core.json 모양(줄기 names 만 빠짐)으로 되돌리는지.
// brk.js 는 브라우저 모듈(lk.js 를 부른다)이라 unpack 함수만 떼어 실행한다. 정답: tests/fixtures/threads_pack_case.json(tests/unit/test_threads_pack.py --write)
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const src = fs.readFileSync(new URL('../../web/assets/df/brk.js', import.meta.url), 'utf8');
const m = src.match(/export function unpack\(d\) \{[\s\S]*?\n\}/);
const unpack = m && new Function(m[0].replace('export ', '') + '\nreturn unpack;')();
const { core, pack } = JSON.parse(fs.readFileSync(new URL('../fixtures/threads_pack_case.json', import.meta.url), 'utf8'));

test('brk.js has unpack()', () => assert.ok(unpack));
test('unpack(pack) equals core without thread names', () => {
  const want = { ...core, threads: core.threads.map(({ names, ...t }) => t) };
  assert.deepEqual(unpack(pack), want);
});
test('unpack leaves the old shapes (threads-core.json · threads.json) alone', () => assert.deepEqual(unpack(core), core));
