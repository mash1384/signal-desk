"""키워드 기반 분류. LLM 키가 없을 때의 기본 분류이고, LLM 결과가 있으면 그걸 우선한다."""

import re

from . import config

_ASCII = re.compile(r"^[a-z0-9&.\- ]+$")
_cache = {}


def _pattern(keyword):
    pat = _cache.get(keyword)
    if pat is None:
        if _ASCII.match(keyword):
            # 영어 키워드는 단어 경계를 지켜 'ai'가 'said'에 걸리지 않게 한다
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])")
        else:
            pat = re.compile(re.escape(keyword))
        _cache[keyword] = pat
    return pat


def count_hits(text, keywords):
    return sum(1 for k in keywords if _pattern(k).search(text))


def has_any(text, keywords):
    return any(_pattern(k).search(text) for k in keywords)


def classify(title, excerpt, source):
    """카테고리를 고른다. 어느 쪽에도 맞지 않고 소스가 키워드를 요구하면 None(버림)."""
    if any(title.startswith(p) for p in config.TITLE_BLOCK_PREFIX):
        return None
    text = (title + " " + (excerpt or "")).lower()
    title_l = title.lower()
    scores = {}
    for cat, words in config.CATEGORY_KEYWORDS.items():
        # 제목에서 맞은 키워드는 두 배로 센다
        scores[cat] = count_hits(text, words) + count_hits(title_l, words)
    hint = source.get("hint")
    best = max(scores, key=lambda c: scores[c])
    if scores[best] == 0:
        if source.get("require") or not hint:
            return None
        return hint
    if hint and scores.get(hint, 0) > 0 and scores[hint] >= scores[best] - 1:
        best = hint
    if source.get("require"):
        # 종합 경제지는 제목에 분야 키워드가 있고 신호가 충분한 기사만 남긴다
        # 서로 다른 키워드 2개 이상 + 제목에 1개 이상
        if count_hits(text, config.CATEGORY_KEYWORDS[best]) < 2 or count_hits(title_l, config.CATEGORY_KEYWORDS[best]) == 0:
            return None
    return best


def extract_assets(title, excerpt):
    text = (title + " " + (excerpt or "")).lower()
    found = []
    for sym, info in config.ASSETS.items():
        if has_any(text, info["names"]) or re.search(r"(?<![A-Z0-9])" + sym + r"(?![A-Z0-9])", title + " " + (excerpt or "")):
            found.append(sym)
    return found[: config.MAX_ASSETS_PER_ARTICLE]


def importance(title, excerpt, source_id, category, assets):
    text = (title + " " + (excerpt or "")).lower()
    score = 1
    if has_any(text, config.HIGH_KEYWORDS) or (category == "crypto" and has_any(text, config.HIGH_KEYWORDS_CRYPTO)):
        score = 3
    elif category == "crypto" and ("BTC" in assets or "ETH" in assets):
        score = 2
    elif category == "macro" and has_any(text, ["fed", "연준", "금리", "환율", "물가", "inflation", "treasury", "국채"]):
        score = 2
    score += config.SOURCE_WEIGHT.get(source_id, 0) if score < 3 else 0
    return max(1, min(3, score))


def event_type(title, excerpt, category):
    # 발췌는 곁가지 내용이 많아 제목만 본다
    text = title.lower()
    for key, _label, words in config.EVENT_TYPES:
        if (key == "ai-model" and category != "ai") or (key == "listing" and category != "crypto"):
            continue
        if has_any(text, words):
            return key
    return "other"


def tags_for(title, assets, etype):
    tags = list(assets)
    labels = {k: label for k, label, _ in config.EVENT_TYPES}
    if etype in labels:
        tags.append(labels[etype])
    return tags[:5]
