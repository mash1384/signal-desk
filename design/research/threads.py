# 원형: 지난 72시간 소식(묶음)을 다시 '줄기(thread)'로 — 날을 넘어 이어지는 이야기인지 본다
import sys, os, time, collections, re
sys.path.insert(0, os.path.expanduser('~/.signal'))
import numpy as np, tg_publish as P
con = P.db(); now = time.time()
rows, vecs = P.load(con, now - 72 * 3600)
V = np.array(vecs, dtype=np.float32).reshape(len(rows), -1)
groups = [g for g in P.cluster(rows, V @ V.T)]
st = []
for g in groups:
    it = P.merge([rows[i] for i in g]); c = V[g].mean(0); c /= np.linalg.norm(c) or 1
    if it['v'] == '중립' and it['s'] < 2: continue
    st.append((it, c))
print('stories (non-trivial) 72h', len(st))
# 줄기: 의미가 가깝거나(코사인) 같은 고유명사를 공유하면 같은 줄기로(단일 연결, 문턱 0.62)
ENT = re.compile(r"[A-Z][A-Za-z0-9]{2,}|[가-힣]{2,}(?:은행|증권|거래소|재단|그룹|랩스|캐피탈)|엔비디아|테슬라|애플|도이치뱅크|찰스 슈왑|비자|마스터카드|블랙록|코인베이스|바이낸스|업비트|빗썸|연준|일본은행|트럼프|SEC|MSCI|OpenAI|오픈AI|앤트로픽|구글|메타|마이크로소프트|TSMC|스트래티지|서클|테더|리플")
ents = [set(ENT.findall(it['ko'])) - {'BTC', 'ETH', 'USD', 'AI', 'ETF'} for it, _ in st]
C = np.stack([c for _, c in st]); S = C @ C.T
n = len(st); par = list(range(n))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for i in range(n):
    for j in range(i + 1, n):
        if S[i, j] >= 0.72 or (S[i, j] >= 0.55 and ents[i] & ents[j]):
            par[f(i)] = f(j)
T = collections.defaultdict(list)
for i in range(n): T[f(i)].append(i)
th = sorted([v for v in T.values() if len(v) >= 3], key=lambda v: -len(v))
print('threads with 3+ stories', len(th), '| spanning 2+ days', sum(1 for v in th if len({time.strftime('%d', time.localtime(st[i][0]['t'])) for i in v}) >= 2))
for v in th[:10]:
    its = sorted([st[i][0] for i in v], key=lambda x: x['t'])
    days = sorted({time.strftime('%m-%d', time.localtime(x['t'])) for x in its}); u = sum(x['v'] == '호재' for x in its); d = sum(x['v'] == '악재' for x in its)
    print(f"\n● {len(its)}건 · {days[0]}~{days[-1]} ({len(days)}일) · 호재{u}/악재{d}")
    for x in its[:2] + its[-2:]: print('   ', time.strftime('%m-%d %H:%M', time.localtime(x['t'])), x['ko'][:62])
