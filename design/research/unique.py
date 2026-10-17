import sys, os, time, statistics, collections
sys.path.insert(0, os.path.expanduser('~/.signal'))
import numpy as np, tg_publish as P, tg_collect as C
LANG = {n: l for n, _, l in C.CHANNELS}
con = P.db(); now = time.time()
rows, vecs = P.load(con, now - 86400 - 3600)
V = np.array(vecs, dtype=np.float32).reshape(len(rows), -1)
groups = [[rows[i] for i in g] for g in P.cluster(rows, V @ V.T)]
groups = [g for g in groups if g[0]['t'] >= now - 86400]
multi = [g for g in groups if len({m['ch'] for m in g}) >= 2]
print('stories', len(groups), 'covered by 2+ channels', len(multi), '| lang mix', collections.Counter(LANG.get(m['ch'], '?') for g in groups for m in g))
lead, notko, spread, contested = [], [], [], []
for g in multi:
    by = collections.defaultdict(list)
    for m in g: by[LANG.get(m['ch'], '?')].append(m['t'])
    ko = min(by['ko']) if by.get('ko') else None; fo = min(t for l, ts in by.items() if l != 'ko' for t in ts) if any(l != 'ko' for l in by) else None
    if ko and fo and fo < ko: lead.append(((ko - fo) / 60, g))
    t0 = min(m['t'] for m in g); n5 = sorted(m['t'] for m in g)
    spread.append((len({m['ch'] for m in g}), (n5[-1] - t0) / 60, g))
    vs = {m['verdict'] for m in g if m['verdict'] != '중립'}
    if len(vs) == 2: contested.append(g)
for g in groups:
    ls = {LANG.get(m['ch'], '?') for m in g}
    if 'ko' not in ls and max(m['strength'] for m in g) >= 2: notko.append(g)
print('\n[해외가 먼저, 한국 채널은 나중] %d건, 앞선 시간 중앙값 %.0f분' % (len(lead), statistics.median([x[0] for x in lead]) if lead else 0))
for mins, g in sorted(lead, key=lambda x: -x[0] * (max(m['strength'] for m in x[1]) + 1))[:4]: print(f'  {mins:.0f}분 앞섬 | {g[0]["ko"][:60]}')
print('\n[세기 2+인데 한국 채널엔 아직 없음] %d건' % len(notko))
for g in sorted(notko, key=lambda g: -max(m['strength'] for m in g))[:4]: print('  ', sorted({LANG.get(m["ch"]) for m in g}), g[0]['ko'][:60])
print('\n[가장 넓게 퍼진 소식] (채널 수, 첫 보도→마지막 보도 분)')
for n, mins, g in sorted(spread, key=lambda x: -x[0])[:4]: print(f'  {n}곳 · {mins:.0f}분 | {g[0]["ko"][:60]}')
print('\n[채널마다 판정이 엇갈린 소식] %d건' % len(contested))
for g in contested[:4]: print('  ', collections.Counter(m['verdict'] for m in g), g[0]['ko'][:60])
