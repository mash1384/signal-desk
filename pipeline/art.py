"""소식 그림(점묘화) 고르기 — 그림 사전(web/assets/df/art.json)에서 제목에 맞는 그림 하나.
브라우저(web/assets/df/artm.js)와 같은 규칙이다. 두 쪽이 같은 답을 내는지 tests/unit/test_art.py 가 같은 예시로 확인한다.

규칙
- 우선순위: 주제 먼저(해킹 등, 3) > 이름(인물 · 회사 · 코인, 2) > 기관 · 장소 · 나라 · 물건(1) > 넓은 주제(물가 · 증시 등, 0).
  같은 순위면 한국어 제목에서 먼저 나온 것, 같은 자리면 긴 이름. 한국어에 없으면 영어 제목.
- 한글 이름이 두 글자 이하면 앞이 한글이 아니어야 하고(자금 ≠ 금), 뒤도 한글이면 조사 · 꼬리(은 · 는 · 값 · 산 …)만 허용(금리 ≠ 금, 인도네시아 ≠ 인도).
- 영문 이름은 앞뒤가 영문 · 숫자가 아니어야 한다. 대문자 이름(AI · SEC)은 대소문자까지 같아야 한다.
- 제목에 없으면 소식의 코인(coins) → 그래도 없으면 지구(fb).
- 한 대상에 그림이 여러 장이면 소식 id 로 돌려 쓴다(같은 소식은 늘 같은 그림)."""
import json
import os
import re

INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "assets", "df", "art.json")
TAIL = set("은는이가을를의에와과도만로서까부엔값산발측")
_HAN = re.compile(r"[가-힣]")


def load(path=None):
    try:
        with open(path or INDEX, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _han(c):
    return bool(c) and bool(_HAN.match(c))


def find(text, name, nots=()):
    """text 안에서 name 이 규칙에 맞게 처음 나오는 자리(없으면 -1). nots: 바로 뒤(빈칸 건너)에 오면 아닌 말."""
    if not text or not name:
        return -1
    ascii_ = name.isascii()
    rx = re.compile(re.escape(name), 0 if (not ascii_ or name.upper() == name) else re.I)
    pos = 0
    while True:   # 겹쳐서도 찾는다(브라우저 쪽과 같게)
        m = rx.search(text, pos)
        if not m:
            return -1
        a, b = m.start(), m.end()
        pos = a + 1
        prev, nxt = text[a - 1] if a else "", text[b] if b < len(text) else ""
        if ascii_:
            if (prev and (prev.isascii() and prev.isalnum())) or (nxt and (nxt.isascii() and nxt.isalnum())):
                continue
        elif len(name) <= 2:
            if _han(prev) or (_han(nxt) and nxt not in TAIL):
                continue
        if any(text[b:].lstrip().startswith(w) for w in nots):
            continue
        return a


def entity(ix, ko, en):
    """제목에 걸리는 사전 항목 번호(없으면 None)."""
    best = None   # (우선순위 큰 것, 자리 작은 것, 이름 긴 것)
    ko, en = ko or "", en or ""
    for i, e in enumerate(ix["e"]):
        kos, ens, pr, nots = e[1], e[2], e[3], e[5] if len(e) > 5 else ()
        for name in kos + ens:
            p = find(ko, name, nots)
            if p < 0:
                p = find(en, name, nots)
                p = p + len(ko) + 1 if p >= 0 else -1
            if p < 0:
                continue
            key = (-pr, p, -len(name))
            if best is None or key < best[0]:
                best = (key, i)
    return best[1] if best else None


def seed(sid):
    """소식 id → 돌려쓰기 번호(브라우저와 같은 FNV-1a 32비트)."""
    h = 2166136261
    for ch in str(sid).encode("utf-8"):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


def _coin(ix, coins):
    for c in coins or ():
        j = ix.get("sym", {}).get(str(c).upper())
        if j is not None:
            return j
    return None


def choose(ids, sid, avoid=()):
    """돌려쓰기: 소식 id 로 정한 자리부터, avoid 에 없는 첫 장(다 겹치면 그 자리)."""
    n, s = len(ids), seed(sid)
    for k in range(n):
        x = ids[(s + k) % n]
        if x not in avoid:
            return x
    return ids[s % n]


def pick(ix, ko, en="", coins=(), sid="", avoid=()):
    """그림 id(브라우저 artm.js pick 과 같다): 제목 → 코인 → 지구."""
    if not ix:
        return None
    i = entity(ix, ko, en)
    if i is None:
        i = _coin(ix, coins)
    ids = ix["e"][i][4] if i is not None and ix["e"][i][4] else ix["fb"]
    return choose(ids, sid, avoid)


def pick_from(ix, sources, sid, avoid=()):
    """브리핑: sources = [(한국어, 영어, 코인)] 앞에서부터 사전에 걸리고 아직 안 쓴 그림이 있는 첫 것. 없으면 지구."""
    if not ix:
        return None
    for ko, en, coins in sources:
        i = entity(ix, ko, en)
        if i is None:
            i = _coin(ix, coins)
        if i is not None and ix["e"][i][4]:
            x = choose(ix["e"][i][4], sid, avoid)
            if x not in avoid:
                return x
    return choose(ix["fb"], sid, avoid)


def matched(ix, ko, en="", coins=()):
    """사전 항목 이름(시험 · 진단용). 지구면 None."""
    i = entity(ix, ko, en)
    if i is None:
        i = _coin(ix, coins)
    return ix["e"][i][0] if i is not None else None
