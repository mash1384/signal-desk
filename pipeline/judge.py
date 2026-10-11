"""로컬 AI 판정 붙이기.

운영자 Mac의 로컬 모델(Gemma 4)이 15분마다 새 기사를 판정해 `llm` 브랜치의 judgments.json에 올린다(tools/judge_live.py).
파이프라인은 그 파일을 읽어 기사에 `ai`를 붙인다: 사건인지, 어느 코인을 직접 다루는지, 시장 전체 사건인지, 사건 종류, 호재/악재, 강도.
판정이 있는 기사는 그 판정으로 반응을 잴 대상을 정하고, 없는 기사(Mac이 꺼져 있을 때 등)는 지금까지의 키워드 규칙을 쓴다.
"""

import os
import re

from . import util

VERSION = 2
KINDS = {"event", "price_recap", "opinion", "promo", "unrelated"}
TYPES = {"listing", "hack", "etf", "legal", "regulation", "treasury", "flow", "partnership", "development", "macro", "other"}
KIND_KO = {"event": "사건", "price_recap": "가격 정리·전망", "opinion": "의견·해설", "promo": "홍보", "unrelated": "코인과 무관"}
TYPE_KO = {"listing": "상장", "hack": "해킹", "etf": "ETF", "legal": "소송·법집행", "regulation": "규제·정책", "treasury": "기업·정부 매수",
           "flow": "대량 이동·매도", "partnership": "제휴·채택", "development": "개발·출시", "macro": "미국 거시", "other": "기타"}
DIR_KO = {"bullish": "호재", "bearish": "악재", "neutral": "중립"}
# 시장 전체 사건은 미국 쪽(연준·물가·고용, 미국 정부·의회·규제기관)일 때만 인정한다. 모델이 다른 나라 규제도 true로 내는 일이 있다
US = re.compile(r"\b(SEC|CFTC|Fed|FOMC|OCC|FDIC|DOJ|FinCEN|US|USA|U\.S\.|CPI|PPI|PCE)\b|\b(?i:powell|treasury|white house|biden|trump|congress|senate|house|"
                r"united states|american|inflation|jobs report|payrolls|nonfarm|interest rates?|rate (?:hike|cut))\b|미국|美|미 |연준|파월|트럼프|백악관|의회|상원|하원|고용|비농업|물가")


def load(path=None):
    """{기사 id: 판정}. 파일이 없거나 형식이 다르면 {}."""
    path = path or os.environ.get("SIGNAL_JUDGMENTS") or os.path.join("llm", "judgments.json")
    doc = util.read_json(path, None)
    if not isinstance(doc, dict) or doc.get("v") != VERSION or not isinstance(doc.get("j"), dict):
        return {}
    return doc["j"]


def normalize(j, assets, title=""):
    """모델 출력을 검증해 저장 형식으로. 코인은 키워드로도 찾은 코인(제목·발췌에 실제로 나온 것)만 남긴다."""
    if not isinstance(j, dict) or j.get("kind") not in KINDS:
        return None
    ev = j["kind"] == "event"
    coins = [c for c in (j.get("coins") or []) if c in (assets or [])][:3] if ev else []
    try:
        st = max(0, min(3, int(j.get("strength") or 0))) if ev else 0
    except (TypeError, ValueError):
        st = 0
    return {"kind": j["kind"], "coins": coins, "mw": bool(j.get("market_wide")) and ev and not coins and bool(US.search(title or "")),
            "type": (j.get("type") if j.get("type") in TYPES else "other") if ev else "",
            "dir": j.get("direction") if ev and j.get("direction") in DIR_KO else "neutral", "str": st,
            "m": str(j.get("model") or "")[:40]}


def apply(articles, judgments, reset):
    """판정을 기사에 붙인다. 반응을 잴 대상이 바뀐 기사는 reset(a)로 처음부터 다시 잰다. 붙인 수를 돌려준다."""
    from .impact import subjects
    n = 0
    for a in articles:
        j = judgments.get(a["id"])
        if not j or a.get("source") in ("upbit-notice", "calendar"):
            continue
        ai = normalize(j, a.get("assets"), a.get("title_orig") or a.get("title") or "")
        if not ai or ai == a.get("ai"):
            continue
        before = subjects(a)
        a["ai"] = ai
        if subjects(a) != before:
            reset(a)
        n += 1
    return n


def label(ai):
    """사람이 읽는 한 줄: '사건 · 상장 · 호재 · 강도 2'."""
    if not ai:
        return ""
    if ai["kind"] != "event":
        return KIND_KO.get(ai["kind"], "")
    parts = ["사건", TYPE_KO.get(ai.get("type"), "기타")]
    if ai.get("dir") in ("bullish", "bearish"):
        parts.append(DIR_KO[ai["dir"]])
    if ai.get("str"):
        parts.append("강도 %d" % ai["str"])
    return " · ".join(parts)
