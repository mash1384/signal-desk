// 배포본 JS 주석 줄 빼기(pipeline/jsstrip.py) 검증: 원본과 결과의 토큰(주석 제외)이 모두 같아야 한다. 하나라도 다르면 exit 1.
// 사용(저장소 루트): node tests/js/strip_check.mjs
import { readFileSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import * as espree from 'espree';
const dir = 'web/assets/df', files = readdirSync(dir).filter((f) => f.endsWith('.js')).sort();
const strip = (p) => execFileSync('python3', ['-c', 'import sys; from pipeline.jsstrip import strip_line_comments as s; sys.stdout.write(s(open(sys.argv[1], encoding="utf-8").read()))', p], { encoding: 'utf8' });
const toks = (src) => espree.tokenize(src, { ecmaVersion: 'latest', sourceType: 'module' }).map((t) => t.type + ':' + t.value);
let bad = 0, saved = 0;
for (const f of files) {
  const p = `${dir}/${f}`, a = readFileSync(p, 'utf8'), b = strip(p);
  const ta = toks(a), tb = toks(b), same = ta.length === tb.length && ta.every((x, i) => x === tb[i]);
  saved += Buffer.byteLength(a) - Buffer.byteLength(b);
  if (!same) { bad++; const i = ta.findIndex((x, k) => x !== tb[k]); console.log('DIFF', f, 'token', i, ta[i], '≠', tb[i]); }
}
console.log(`files ${files.length}, token-identical ${files.length - bad}, bytes saved ${saved}`);
process.exit(bad ? 1 : 0);
