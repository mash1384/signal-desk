import sys, os, time, statistics, collections
sys.path.insert(0, os.path.expanduser('~/.signal'))
import numpy as np, tg_publish as P, tg_collect as C
LANG = {n: l for n, _, l in C.CHANNELS}
con = P.db(); now = time.time()
rows, vecs = P.load(con, now - 72 * 3600)
V = np.array(vecs, dtype=np.float32).reshape(len(rows), -1)
groups = [[rows[i] for i in g] for g in P.cluster(rows, V @ V.T)]
groups = [g for g in groups if g[0]['t'] >= now - 72 * 3600]
lead, asia_only = [], []
for g in groups:
    by = collections.defaultdict(list)
    for m in g: by[LANG.get(m['ch'], '?')].append(m['t'])
    en = min(by['en']) if by.get('en') else None; asia = min([t for l in ('zh', 'ko') for t in by.get(l, [])], default=None)
    s = max(m['strength'] for m in g)
    if en and asia and asia < en: lead.append(((en - asia) / 60, g))
    if asia and not en and s >= 2: asia_only.append(g)
both = sum(1 for g in groups if any(LANG.get(m['ch']) == 'en' for m in g) and any(LANG.get(m['ch']) in ('zh', 'ko') for m in g))
print('72h stories', len(groups), '| covered by EN and Asian channels', both)
print('Asian channel first, English later: %d (median lead %.0f min)' % (len(lead), statistics.median([x[0] for x in lead]) if lead else 0))
for mins, g in sorted(lead, key=lambda x: -x[0])[:6]:
    first = min(g, key=lambda m: m['t']); print(f'  {mins:5.0f} min ahead · first {first["ch"]} ({LANG.get(first["ch"])}) | {g[0]["ko"][:58]}')
print('strength>=2 stories ONLY in Asian channels (no English channel at all): %d' % len(asia_only))
for g in sorted(asia_only, key=lambda g: -max(m['strength'] for m in g))[:6]:
    print('  ', sorted({m["ch"] for m in g}), g[0]['ko'][:60])
print('by channel (stories first-seen there, 72h):', collections.Counter(min(g, key=lambda m: m['t'])['ch'] for g in groups).most_common(8))
