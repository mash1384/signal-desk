#!/usr/bin/env python3
"""이야기 줄기(thread): 며칠에 걸쳐 이어지는 소식을 하나의 이야기로 묶고, 바뀐 줄기만 AI(Gemma)가 요약한다.

1) 소식(story): tg_publish 와 같은 방식으로 지난 30시간 판정된 줄을 같은 소식끼리 묶는다. 소식마다 대표 벡터(멤버 임베딩 평균)를
   ~/.signal/threads/stories.npz 에 10일 동안 보관한다(판정 DB 임베딩은 72시간만 남기 때문).
2) 줄기: 평균 연결(덩어리 중심끼리 비교) + 공통 대상(회사·코인·나라 등 고유명) 필수 + 시간 간격 36시간 이내 + 크기 상한.
   '비트코인'처럼 어디에나 나오는 말은 공통 대상으로 치지 않는다(전체 소식의 4% 넘게 나오면 약한 이름).
   예전 방식(하나만 닮아도 연결)은 A-B, B-C 로 줄줄이 이어져 수백 건짜리 덩어리가 생겼다.
3) 줄기 번호는 지난 결과와 소식이 가장 많이 겹치는 것을 이어받는다(같은 줄기가 매번 새 번호가 되지 않게).
4) AI: 줄기 제목 · '지금까지' 2문장 · '새로 붙은 것' 1문장. 문장마다 근거 소식 번호를 달고, 숫자는 근거 소식에 있는 것만 허용.

결과: ~/.signal/flash-branch/daily/threads.json → tg_publish 가 flash 브랜치로 올린다.
실행: python story_threads.py [--no-ai]
설치: ~/.signal/tgvenv/bin/python tools/story_threads.py --install   (launchd com.signal.threads, 30분마다)
"""

import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~/.signal")
sys.path.insert(0, HOME)
STATE = os.path.join(HOME, "threads")
OUT = os.path.join(HOME, "flash-branch", "daily", "threads.json")
OLLAMA = os.environ.get("SIGNAL_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
KEEP = 10 * 86400
EVERY = 1800
LABEL = "com.signal.threads"

# 묶기 기준
SIM_SEED = 0.62       # 소식 둘이 이만큼 닮고 공통 대상이 있어야 후보
SIM_MERGE = 0.64      # 두 덩어리 중심이 이만큼 닮아야 합친다(평균 연결)
SIM_STRONG = 0.80     # 이만큼 닮으면 약한 이름(비트코인 등)만 겹쳐도 된다
GAP = 36 * 3600       # 두 덩어리 시간 사이 간격
CAP = 30              # 줄기 하나의 소식 수 상한
WEAK_DF = 0.02        # 전체 소식의 2% 넘게 나오는 이름(트럼프·비트코인 등)은 약한 이름

# 테마(사이트 lk.js themesOf 와 같은 기준)
RX = {
    "crypto": re.compile(r"비트코인|이더리움|코인|가상자산|암호화폐|스테이블코인|거래소|토큰|블록체인|디파이|온체인|NFT|채굴|에어드랍|ETF"),
    "nasdaq": re.compile(r"나스닥|S&P|다우|증시|주가|엔비디아|애플|테슬라|마이크로소프트|아마존|메타|알파벳|구글|반도체|기술주|실적|브로드컴|팔란티어|마이크론|TSMC|AMD"),
    "econ": re.compile(r"연준|Fed|FOMC|CPI|PPI|물가|인플레이션|금리|국채|고용|실업|GDP|PCE|소매판매|환율|재무부|파월|관세|경기|유가|원유|달러화|달러 지수|DXY|국채 금리"),
    "ai": re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|오픈AI|OpenAI|앤트로픽|Anthropic|챗GPT|ChatGPT|LLM|딥시크|제미나이|데이터센터|xAI|그록"),
}


def themes_of(it):
    ko, out = it.get("ko") or "", []
    if it.get("coins") or RX["crypto"].search(ko):
        out.append("crypto")
    if RX["nasdaq"].search(ko):
        out.append("nasdaq")
    if RX["econ"].search(ko) or (it.get("kind") == "data" and not it.get("coins")):
        out.append("econ")
    if "ai" in (it.get("sectors") or []) or RX["ai"].search(ko):
        out.append("ai")
    return out or ["world"]


# ---------- 고유명(공통 대상) ----------
KO_ENT = re.compile(r"[가-힣]{2,}(?:은행|증권|거래소|재단|그룹|랩스|캐피탈|자산운용|중앙은행|정부|의회|법원)|엔비디아|테슬라|애플|블랙록|코인베이스|바이낸스|업비트|빗썸|"
                    r"연준|일본은행|트럼프|파월|MSCI|오픈AI|앤트로픽|구글|메타|마이크로소프트|TSMC|ASML|스트래티지|마이크로스트래티지|서클|테더|리플|이란|이스라엘|"
                    r"우크라이나|러시아|중국|일본|한국|홍콩|싱가포르|유럽|호르무즈|가자|대만|사우디|베네수엘라|북한")
EN_ENT = re.compile(r"\b(?:[A-Z][a-z]+|[A-Z]{2,}[a-z]*)(?:\s+(?:of\s+|de\s+|and\s+)?(?:[A-Z][a-z]+|[A-Z]{2,}))*\b")
STOP = {"the", "a", "an", "in", "on", "at", "after", "as", "for", "with", "this", "that", "new", "first", "us", "u.s", "report", "reports", "says",
        "data", "today", "week", "month", "year", "q1", "q2", "q3", "q4", "ceo", "cfo", "etf", "etfs", "usd", "usdt", "ai", "btc", "eth", "crypto",
        "bitcoin", "ethereum", "market", "markets", "price", "prices", "stock", "stocks", "fund", "funds", "bank", "inc", "corp", "ltd",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december", "breaking", "update", "analyst", "analysts", "investors", "traders",
        "whale", "whales", "anonymous", "unknown", "wallet", "address", "treasury", "exchange", "president", "minister", "official", "officials"}
# 지갑 이체 알림(고래 이동 등)은 이야기가 아니라 잡음이라 줄기에서 뺀다
TRANSFER = re.compile(r"(이체|입금|출금|전송|이동|발행|소각)(됐|되었|했|함|돼)|미확인 지갑|알 수 없는 지갑|익명 주소|고래 지갑")


def entities(it):
    out = set()
    for e in KO_ENT.findall(it.get("ko") or ""):
        out.add(e)
    for e in EN_ENT.findall(it.get("en") or ""):
        k = e.strip().lower()
        if k not in STOP and len(k) >= 3:
            out.add(k)
    for c in it.get("coins") or []:
        out.add("$" + c)
    return out


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


# ---------- 소식 모으기 · 보관 ----------
def load_store(np):
    p = os.path.join(STATE, "stories.json")
    try:
        meta = json.load(open(p))
        vec = np.load(os.path.join(STATE, "vecs.npy"))
        if len(meta) == len(vec):
            return meta, vec
    except Exception:
        pass
    return [], np.zeros((0, 1), dtype=np.float32)


def save_store(np, meta, vec):
    os.makedirs(STATE, exist_ok=True)
    np.save(os.path.join(STATE, "vecs.tmp.npy"), vec)
    os.replace(os.path.join(STATE, "vecs.tmp.npy"), os.path.join(STATE, "vecs.npy"))
    with open(os.path.join(STATE, "stories.tmp.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False)
    os.replace(os.path.join(STATE, "stories.tmp.json"), os.path.join(STATE, "stories.json"))


def collect(np, now):
    """지난 30시간 판정된 줄 → 소식(같은 소식끼리 묶음)과 대표 벡터. 보관함에 새로 넣거나 덮어쓴다."""
    import tg_publish as P
    meta, vec = load_store(np)
    con = P.db()
    # 보관함이 비었으면(처음) 판정 DB 에 남은 만큼(72시간) 채운다
    # 라이브(tg_publish)와 같은 범위로 묶어야 소식 번호가 같아진다(다른 화면이 같은 소식을 이야기와 이어 붙인다)
    since = now - P.WINDOW - P.GAP if meta else now - 71 * 3600
    rows, vecs = P.load(con, since)
    con.close()
    if not rows:
        return meta, vec
    V = np.array(vecs, dtype=np.float32).reshape(len(rows), -1)
    by = {m["id"]: i for i, m in enumerate(meta)}
    add_m, add_v = [], []
    for g in P.cluster(rows, V @ V.T):
        it = P.merge([rows[i] for i in g])
        c = V[g].mean(0)
        c /= (np.linalg.norm(c) or 1)
        it["th"] = themes_of(it)
        it.pop("link", None)
        if it["id"] in by:
            it["_fresh"] = True
            meta[by[it["id"]]] = it
            vec[by[it["id"]]] = c
        else:
            add_m.append(it)
            add_v.append(c)
    # 다시 묶은 범위 안에서 이번 결과에 없는 옛 묶음은 지운다(묶음이 바뀌면 번호도 바뀐다 — 옛것이 남으면 같은 소식이 두 번 들어간다)
    fresh = {m["id"] for m in add_m} | {m["id"] for m in meta if m.get("_fresh")}
    keep0 = [i for i, m in enumerate(meta) if m["t"] < since + P.GAP or m["id"] in fresh]
    meta, vec = [meta[i] for i in keep0], vec[keep0] if len(vec) else vec
    for m in meta:
        m.pop("_fresh", None)
    if add_m:
        meta = meta + add_m
        vec = np.vstack([vec, np.array(add_v, dtype=np.float32)]) if len(vec) and vec.shape[1] == len(add_v[0]) else np.array(add_v, dtype=np.float32)
    keep = [i for i, m in enumerate(meta) if m["t"] >= now - KEEP]
    meta, vec = [meta[i] for i in keep], vec[keep]
    save_store(np, meta, vec)
    return meta, vec


# ---------- 줄기 묶기 ----------
def usable(m):
    return m.get("kind") in ("event", "data", "opinion") and not TRANSFER.search(m.get("ko") or "")


def build_threads(np, meta, vec):
    """평균 연결 + 공통 대상 + 시간 간격 + 크기 상한. 반환: [소식 인덱스 목록](meta 기준)."""
    import heapq
    keep = [i for i, m in enumerate(meta) if usable(m)]
    sub = build_threads_on(np, [meta[i] for i in keep], vec[keep], heapq)
    return [[keep[i] for i in g] for g in sub]


def build_threads_on(np, meta, vec, heapq):
    n = len(meta)
    if n < 3:
        return []
    ents = [entities(m) for m in meta]
    df = collections.Counter(e for s in ents for e in s)
    weak = {e for e, c in df.items() if c > max(3, WEAK_DF * n)}
    strong = [s - weak for s in ents]
    t = np.array([m["t"] for m in meta], dtype=np.float64)
    S = vec @ vec.T
    # 덩어리: 멤버, 벡터 합, 강한 이름 세기, 시간 범위
    alive = {i: {"m": [i], "sum": vec[i].copy(), "ent": collections.Counter(strong[i]), "weak": collections.Counter(ents[i] & weak), "t0": t[i], "t1": t[i]} for i in range(n)}
    heap = []
    for i in range(n):
        js = np.where(S[i, i + 1:] >= SIM_SEED)[0] + i + 1
        for j in js:
            if abs(t[i] - t[j]) <= GAP and ((strong[i] & strong[j]) or (S[i, j] >= SIM_STRONG and ents[i] & ents[j])):
                heapq.heappush(heap, (-float(S[i, j]), i, j))
    nxt = n

    def centroid(c):
        v = c["sum"]
        return v / (np.linalg.norm(v) or 1)

    def can(a, b, sim):
        if len(a["m"]) + len(b["m"]) > CAP:
            return False
        gap = max(0.0, max(a["t0"], b["t0"]) - min(a["t1"], b["t1"]))
        if gap > GAP:
            return False
        # 공통 대상: 양쪽 덩어리에서 30% 이상 나오는 강한 이름이 겹치거나, 아주 닮았으면 약한 이름도
        def core(c, key):
            k = max(1, int(len(c["m"]) * 0.3))
            return {e for e, x in c[key].items() if x >= k}
        if core(a, "ent") & core(b, "ent"):
            return True
        return sim >= SIM_STRONG and bool(core(a, "weak") & core(b, "weak"))

    owner = list(range(n))
    while heap:
        neg, i, j = heapq.heappop(heap)
        if i not in alive or j not in alive:
            continue
        a, b = alive[i], alive[j]
        sim = float(centroid(a) @ centroid(b))
        if sim < SIM_MERGE or not can(a, b, sim):
            continue
        c = {"m": a["m"] + b["m"], "sum": a["sum"] + b["sum"], "ent": a["ent"] + b["ent"], "weak": a["weak"] + b["weak"],
             "t0": min(a["t0"], b["t0"]), "t1": max(a["t1"], b["t1"])}
        del alive[i], alive[j]
        k = nxt
        nxt += 1
        alive[k] = c
        for x in c["m"]:
            owner[x] = k
        # 새 덩어리와 다른 덩어리 사이 후보(중심 유사도)
        cv = centroid(c)
        keys = list(alive.keys())
        if len(keys) > 1:
            M = np.stack([centroid(alive[q]) for q in keys])
            sims = M @ cv
            for q, s in zip(keys, sims):
                if q != k and s >= SIM_MERGE:
                    heapq.heappush(heap, (-float(s), min(k, q), max(k, q)))
    return [sorted(c["m"], key=lambda x: t[x]) for c in alive.values() if len(c["m"]) >= 3]


def summarize_thread(meta, idx, now, ents_df_weak):
    its = [meta[i] for i in idx]
    days = sorted({time.strftime("%Y-%m-%d", time.localtime(x["t"])) for x in its})
    th = collections.Counter(k for x in its for k in x["th"])
    names = collections.Counter(e for x in its for e in entities(x) - ents_df_weak)
    coins = collections.Counter(c for x in its for c in x.get("coins") or [])
    return {"ids": [x["id"] for x in its], "n": len(its), "first": its[0]["t"], "last": its[-1]["t"], "days": len(days),
            "new24": sum(1 for x in its if x["t"] >= now - 86400), "u": sum(1 for x in its if x["v"] == "호재"), "d": sum(1 for x in its if x["v"] == "악재"),
            "s": max(x["s"] for x in its), "outlets": sum(x.get("n", 1) for x in its), "th": [k for k, _ in th.most_common(3)],
            "coins": [c for c, _ in coins.most_common(4)], "names": [e for e, _ in names.most_common(5)]}


def stable_ids(threads, prev):
    """지난 결과와 소식이 가장 많이 겹치는 줄기 번호를 이어받는다(겹침 30% 이상). 없으면 첫 소식으로 새 번호."""
    used = set()
    pmap = [(p["id"], set(p["ids"])) for p in prev]
    for th in threads:
        s = set(th["ids"])
        best, bj = None, 0.0
        for pid, ps in pmap:
            if pid in used:
                continue
            j = len(s & ps) / max(1, len(s | ps))
            if j > bj:
                best, bj = pid, j
        if best and bj >= 0.3:
            th["id"] = best
        else:
            th["id"] = "t" + hashlib.sha1(th["ids"][0].encode()).hexdigest()[:8]
        used.add(th["id"])


# ---------- AI 줄기 요약 ----------
ADVICE = re.compile(r"매수하|매도하|사세요|파세요|추천|담아|비중을 늘|비중을 줄|진입하|손절|\bbuy\b|\bsell\b", re.I)
FUTURE = re.compile(r"(할|될|오를|내릴|떨어질|이어질|커질|높아질|낮아질) (것|가능성)|전망이다|전망된다|\bwill\b|\blikely\b|\bexpect(s|ed)? to\b|\bset to\b", re.I)
# 소식을 가격 움직임의 원인으로 묶는 표현(테마 요약과 같은 기준 + 영어 'influenced by' 등)
CAUSE_PX = re.compile(r"(때문에|탓에|덕분에|영향으로|여파로|에 힘입어|로 인해|으로 인해|에 따른|우려로|우려에|되며|하며|이어지며|면서|전망에)(?:[^.]|\.\d){0,30}(올랐|내렸|상승|하락|급등|급락|반등|증발|매도세|폭락)"
                      r"|\b(because of|due to|thanks to|driven by|on the back of|amid|as|following|after|influenced by|on concerns)\b(?:[^.]|\.\d){0,40}\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|tumbled|slumped)\b"
                      r"|\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|tumbled|slumped)\b(?:[^.]|\.\d){0,30}\b(amid|as|due to|after|following|on concerns)\b"
                      r"|movements? (were|was) (influenced|driven|caused)"
                      r"|(우려|하락|급락|상승|급등|부진|호조|충격|공포|기대|매도|투매)(으)?로(?:[^.]|\.\d){0,30}(올랐|내렸|상승|하락|급등|급락|폭락|반등)", re.I)
HANGUL = re.compile(r"[가-힣]")
MAX_IN = 16
# 원문에 없는 직함 바꾸기('전 대통령', 'former president' 등)를 막는다
TITLE_SWAP = re.compile(r"전 (대통령|총리|의장|총재|장관|대표|CEO)|\bformer (president|prime minister|chair(man)?|governor|minister|ceo|fed official)\b", re.I)
# 영어 원인 표현은 시장 단어(주식·가격·지수·금리 등)가 문장에 있을 때만 문제(배가 '가라앉은' 것은 가격 얘기가 아니다)
MKT_EN = re.compile(r"\b(stocks?|shares?|prices?|index|indices|nasdaq|s&p|dow|bitcoin|btc|ether|eth|yields?|markets?|futures|tokens?|coins?|crypto|bonds?|treasur(y|ies))\b", re.I)
# 남의 말을 전하는 문장('~라고 밝혔다', 'said ... will')은 우리 예측이 아니다
SAID = re.compile(r"밝혔|말했|언급|강조|경고|주장|발표|예고|예상했|전망했|이라며|라며|라고|고 했|\bsaid\b|\bsays\b|\bstated\b|\bwarned\b|\bannounced\b|\bpledged\b|\bvowed\b|\baccording to\b|\bexpects\b|\bplans?\b|\bindicated\b|\bnoted\b|\bsignal(l)?ed\b", re.I)


def _norm(n):
    n = n.replace(",", "").lstrip("+-")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n.lstrip("0") or "0"


def nums(t):
    return {_norm(n) for n in re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", t or "")}


SYS = {"ko": """너는 여러 날에 걸친 뉴스 줄기(같은 이야기의 소식들)를 처음 보는 사람에게 정리하는 편집자다. 번호 붙은 소식만 보고 JSON 하나만 낸다.
반드시 지킬 것:
- title: 이 이야기를 한눈에 알 수 있는 제목(25자 안팎, 숫자 없이, 마침표 없이).
- so_far: 처음부터 지금까지 무슨 일이 이어졌는지 2문장. 각 문장 끝에 근거 소식 번호 refs(1~3개).
- today: 가장 최근에 새로 붙은 소식이 무엇을 더했는지 1문장(자료에 '새로 붙음' 표시가 없으면 빈 문자열).
- 숫자는 근거로 단 소식에 적힌 그대로만 쓴다. 자료에 없는 사실·이름·숫자를 만들지 않는다.
- 앞으로 어떻게 될지 예측하지 않는다('~할 것', '전망' 금지). 사라·팔라는 말 금지. 가격 움직임을 소식의 결과로 묶지 않는다.
- 말투는 '~했어요/~예요'. 쉬운 말로. 근거 번호는 refs 에만 쓰고 문장 안에 [1] 같은 표시를 넣지 않는다.
- '~로 인해 하락했어요'처럼 소식을 가격 움직임의 원인으로 쓰지 않는다. 가격은 '~했어요'로 사실만.
- 출력: {"title": "...", "so_far": [{"s": "...", "refs": [1, 2]}, {"s": "...", "refs": [3]}], "today": {"s": "...", "refs": [5]}}""",
       "en": """You summarise a multi-day news thread (stories about the same unfolding event) for someone seeing it for the first time. Use only the numbered stories. Output one JSON object.
Rules:
- title: a short headline for the whole story (about 6-9 words, no figures, no full stop).
- so_far: 2 sentences on what has happened from the start until now; each ends with refs (1-3 story numbers).
- today: 1 sentence on what the newest stories (marked NEW) added; empty string if none are marked NEW.
- Figures only exactly as written in the cited stories. No invented facts, names or figures.
- No forecasts ("will", "likely"), no buy/sell advice, do not present price moves as caused by the news ("fell due to", "because of"). English only.
- Put story numbers only in refs, never inside the sentence text. Copy figures exactly (do not round 2.14% to 2%).
- Output: {"title": "...", "so_far": [{"s": "...", "refs": [1, 2]}, {"s": "...", "refs": [3]}], "today": {"s": "...", "refs": [5]}}"""}


def chat(system, user, n=900):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m", "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": n},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        t = json.loads(r.read())["message"]["content"]
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def pick_inputs(its, now):
    """AI 에 넘길 소식(최대 16개): 처음 3개 + 큰 소식 + 최근 것. 시간순."""
    idx = list(range(len(its)))
    if len(its) <= MAX_IN:
        return idx
    first = idx[:3]
    recent = idx[-7:]
    big = sorted(idx[3:-7], key=lambda i: (-its[i]["s"], -its[i].get("n", 1)))[:MAX_IN - 10]
    return sorted(set(first + big + recent))


INLINE_REF = re.compile(r"\s*[\[(]\s*(?:#?\d+\s*(?:,|·|및|and)?\s*)+[\])]\s*(?=[.。]?\s*$)")


def split_refs(s, refs):
    """문장 끝에 붙은 '[1, 5]' · '(3)' 은 근거 번호로 읽고 문장에서 뗀다. 끝에 남은 'refs:' 찌꺼기도 뗀다."""
    s = re.sub(r"\s*\brefs?\s*[:：]?\s*$", "", s.strip(), flags=re.I)
    m = INLINE_REF.search(s)
    if m:
        extra = [int(v) for v in re.findall(r"\d+", m.group(0))]
        s = (s[:m.start()] + s[m.end():]).strip()
        refs = refs or extra
    s = re.sub(r"\s*\brefs?\s*[:：]?\s*$", "", s.strip(), flags=re.I)
    return s.strip(), refs


def why_bad(s, refs, texts, lang):
    """문장이 규칙을 어긴 이유(없으면 None). 다시 쓰게 할 때 그대로 알려 준다."""
    ko = lang == "ko"
    if not s:
        return "빈 문장" if ko else "empty sentence"
    if not refs or any(r not in texts for r in refs):
        return "근거 번호가 없거나 목록에 없는 번호" if ko else "missing or unknown story numbers in refs"
    if lang == "en" and HANGUL.search(s):
        return "Korean characters in an English sentence"
    src = " ".join(texts[r] for r in refs)
    extra = nums(s) - nums(src)
    if extra:
        return ("근거 소식에 없는 숫자: " if ko else "figures not in the cited stories: ") + ", ".join(sorted(extra))
    if ADVICE.search(s):
        return "투자 권유 표현" if ko else "buy/sell advice"
    for m in TITLE_SWAP.finditer(s):
        if m.group(0).lower() not in src.lower():
            return ("원문에 없는 직함: " if ko else "title not in the stories: ") + m.group(0)
    if FUTURE.search(s) and not SAID.search(s):
        return "예측 표현(누가 말했는지 없이 '~할 것')" if ko else "a forecast not attributed to anyone"
    if CAUSE_PX.search(s) and (ko or MKT_EN.search(s)):
        return "소식을 가격 움직임의 원인으로 씀. 가격은 따로 '나스닥이 2.14% 하락했어요'처럼 사실만" if ko else "presents news as the cause of a price move; state the move on its own"
    return None


def ok_sentence(s, refs, texts, lang):
    return why_bad(s, refs, texts, lang) is None


def still_ok(a, stories):
    """저장해 둔 요약을 지금 규칙으로 다시 본다(규칙이 바뀌면 새로 쓰게). 숫자 검사는 이미 통과한 것."""
    for lang in ("ko", "en"):
        q = a.get(lang) or {}
        for x in (q.get("so_far") or []) + ([q["today"]] if q.get("today") else []):
            t = x["s"]
            src = " ".join((stories.get(i, {}).get("en") or stories.get(i, {}).get("ko") or "") if lang == "en" else stories.get(i, {}).get("ko", "") for i in x.get("refs") or [])
            if ADVICE.search(t) or (FUTURE.search(t) and not SAID.search(t)) or (CAUSE_PX.search(t) and (lang == "ko" or MKT_EN.search(t))):
                return False
            if any(m.group(0).lower() not in src.lower() for m in TITLE_SWAP.finditer(t)):
                return False
    return True


def ai_thread(th, stories, now, cache):
    key = th["id"] + ":" + hashlib.sha1(",".join(th["ids"]).encode()).hexdigest()[:10]
    if key in cache and still_ok(cache[key], stories):
        return cache[key]
    its = [dict(stories[i], id=i) for i in th["ids"]]
    sel = pick_inputs(its, now)
    out = {}
    for lang in ("ko", "en"):
        texts, lines = {}, []
        for k, i in enumerate(sel, 1):
            x = its[i]
            txt = (x.get("en") or x["ko"]) if lang == "en" else x["ko"]
            texts[k] = txt
            new = x["t"] >= now - 86400 and th["first"] < now - 86400
            lines.append("%d. [%s]%s %s" % (k, time.strftime("%m-%d %H:%M", time.localtime(x["t"])), (" NEW" if lang == "en" else " 새로 붙음") if new else "", txt))
        feedback = ""
        for attempt in range(4):
            try:
                r = chat(SYS[lang], "\n".join(lines) + feedback)
                title = str(r.get("title") or "").strip().rstrip(".")
                so = [split_refs(str(q.get("s") or "").strip(), [int(v) for v in q.get("refs") or [] if str(v).isdigit()]) for q in (r.get("so_far") or []) if isinstance(q, dict)][:2]
                td = r.get("today") or {}
                td = split_refs(str(td.get("s") or "").strip(), [int(v) for v in td.get("refs") or [] if str(v).isdigit()]) if isinstance(td, dict) else ("", [])
                bad = []
                if not title or nums(title) or (lang == "en" and HANGUL.search(title)):
                    bad.append("title " + title[:40])
                reasons = [(s, why_bad(s, refs, texts, lang)) for s, refs in so] + ([(td[0], why_bad(td[0], td[1], texts, lang))] if td[0] else [])
                reasons = [(q, w) for q, w in reasons if w]
                bad += [q[:70] for q, _ in reasons]
                if len(so) < 2:
                    reasons.append(("so_far", "so_far 는 2문장" if lang == "ko" else "so_far needs 2 sentences"))
                if len(so) == 2 and not bad:
                    m = lambda refs: [its[sel[k - 1]]["id"] for k in refs]
                    out[lang] = {"title": title, "so_far": [{"s": s, "refs": m(refs)} for s, refs in so],
                                 "today": {"s": td[0], "refs": m(td[1])} if td[0] else None}
                    break
                log("AI 거절", th["id"], lang, attempt, (bad or ["개수"])[0])
                # 다음 시도에는 거절 이유를 알려 준다
                feedback = ("\n\n이전 답에서 고칠 것:\n" if lang == "ko" else "\n\nFix these in your previous answer:\n") + "\n".join("- %s → %s" % (q[:90], w) for q, w in reasons[:4])
            except Exception as e:
                log("AI 실패", th["id"], lang, type(e).__name__, str(e)[:100])
    if len(out) < 2:
        return None
    out["at"] = now
    cache[key] = out
    return out


def run(no_ai=False):
    import numpy as np
    now = int(time.time())
    meta, vec = collect(np, now)
    log("소식 보관", len(meta), "개(10일)")
    groups = build_threads(np, meta, vec)
    ents = [entities(m) for m in meta]
    df = collections.Counter(e for s in ents for e in s)
    weak = {e for e, c in df.items() if c > max(3, WEAK_DF * len(meta))}
    threads = [summarize_thread(meta, g, now, weak) for g in groups]
    # 사이트에 보일 줄기: 최근 3일 안에 소식이 붙었고, 큰 소식이 있거나 호재·악재가 섞인 것
    threads = [x for x in threads if x["last"] >= now - 3 * 86400 and (x["s"] >= 2 or x["u"] + x["d"] >= 2)]
    try:
        prev = json.load(open(OUT)).get("threads", [])
    except Exception:
        prev = []
    stable_ids(threads, prev)
    # 순서: 최근 24시간에 움직였는지 → 점수(새 소식 + 큰 소식 + 보도 수). 세계 소식만 있는 줄기는 조금 낮춘다(독자 중심은 크립토·나스닥·경제·AI)
    def rank(x):
        sc = x["new24"] + 3 * (x["s"] >= 2) + x["outlets"] / 6 + 2 * (x["days"] >= 2)
        return sc * (0.6 if x["th"] == ["world"] else 1.0)
    threads.sort(key=lambda x: (-(x["new24"] > 0), -rank(x)))
    by = {m["id"]: m for m in meta}
    stories = {sid: {k: by[sid][k] for k in ("t", "ko", "en", "v", "s", "n", "coins", "th", "kind") if k in by[sid]} for x in threads for sid in x["ids"]}
    if not no_ai:
        cpath = os.path.join(STATE, "ai.json")
        try:
            cache = json.load(open(cpath))
        except Exception:
            cache = {}
        # 화면에 보일 앞쪽 줄기만(최대 24개), 바뀐 것만 다시 쓴다
        for x in threads[:24]:
            x["ai"] = ai_thread(x, stories, now, cache)
        live = {x["id"] for x in threads}
        cache = {k: v for k, v in cache.items() if k.split(":")[0] in live}
        with open(cpath + ".tmp", "w") as f:
            json.dump(cache, f, ensure_ascii=False)
        os.replace(cpath + ".tmp", cpath)
    doc = {"v": 1, "made": now, "next": now + EVERY, "threads": threads, "stories": stories, "model": MODEL,
           "params": {"sim_merge": SIM_MERGE, "sim_seed": SIM_SEED, "gap_h": GAP // 3600, "cap": CAP, "weak_df": WEAK_DF}}
    return doc, meta


def main():
    if "--install" in sys.argv[1:]:
        install()
        return
    doc, meta = run("--no-ai" in sys.argv)
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out + ".tmp", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(out + ".tmp", out)
    # 다른 화면(라이브·테마·내 자산)이 가볍게 읽는 색인: 소식 → 이야기(요약이 붙은 이야기만)
    idx = {"made": doc["made"], "s": {}, "t": {}}
    for x in doc["threads"]:
        if not x.get("ai"):
            continue
        idx["t"][x["id"]] = [x["ai"]["ko"]["title"], x["ai"]["en"]["title"], x["days"], x["n"]]
        for sid in x["ids"]:
            idx["s"].setdefault(sid, x["id"])
    ipath = os.path.join(os.path.dirname(out), "thread_index.json")
    with open(ipath + ".tmp", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(ipath + ".tmp", ipath)
    log("완료", out, "줄기", len(doc["threads"]), "여러 날", sum(1 for x in doc["threads"] if x["days"] >= 2), "최대", max([x["n"] for x in doc["threads"]] or [0]))


def install():
    dst = os.path.join(HOME, "story_threads.py")
    shutil.copy2(os.path.abspath(__file__), dst)
    py = os.path.join(HOME, "tgvenv", "bin", "python")
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{py}</string><string>{dst}</string></array>
  <key>StartInterval</key><integer>{EVERY}</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{HOME}/threads.log</string>
  <key>StandardErrorPath</key><string>{HOME}/threads.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist, "(30분마다)")


if __name__ == "__main__":
    main()
