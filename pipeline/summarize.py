"""Claude로 한국어 제목·3줄 요약·분류를 만든다. ANTHROPIC_API_KEY가 없으면 아무것도 하지 않는다.

안전장치
- 요약에 나온 숫자가 원문(제목+발췌)에 없으면 요약을 버린다.
- 매수·매도 권유 표현이 있으면 버린다.
- 실패하면 원문 발췌를 그대로 쓰고 다음 실행에서 다시 시도한다.
"""

import json
import os
import re

from . import config, util

SYSTEM = (
    "You write Korean news briefs for a crypto, AI and macro news site. "
    "Work only from the title and excerpt you are given. Never add facts, numbers, names or dates that are not in them. "
    "Do not give investment advice, price predictions, or buy/sell language. "
    "Return Korean text in plain, neutral news style (다/이다 체)."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "title_ko": {"type": "string"},
        "summary": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string", "enum": ["crypto", "ai", "macro"]},
        "assets": {"type": "array", "items": {"type": "string"}},
        "importance": {"type": "integer", "enum": [1, 2, 3]},
    },
    "required": ["title_ko", "summary", "category", "assets", "importance"],
    "additionalProperties": False,
}

_ADVICE = re.compile(r"(매수|매도|사라|팔아라|추천 ?종목|목표가|강력 ?추천)")
_NUM = re.compile(r"\d[\d,.]*")


def enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _numbers(text):
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text or "")}


def _valid(result, source_text):
    lines = result.get("summary") or []
    if len(lines) != 3 or not result.get("title_ko"):
        return False
    allowed = _numbers(source_text)
    produced = _numbers(" ".join(lines) + " " + result["title_ko"])
    if not produced <= allowed:
        return False
    joined = result["title_ko"] + " " + " ".join(lines)
    return not _ADVICE.search(joined)


def _prompt(a):
    return (
        "Source: %s\nTitle: %s\nExcerpt: %s\n\n"
        "Write: title_ko (Korean headline, under 60 characters), summary (exactly 3 Korean sentences, each under 70 characters), "
        "category (crypto, ai or macro), assets (tickers from this list only if the text mentions them: %s), "
        "importance (3 = likely to move markets broadly, 2 = notable, 1 = minor). "
        "Copy every number exactly as it appears in the source, with the same digits (write 83K as 83K, not 8만3천)."
        % (a["source_name"], a["title_orig"], a.get("excerpt") or "(none)", ", ".join(config.ASSETS))
    )


def summarize(articles):
    """요약이 없는 최신 기사부터 LLM_MAX_PER_RUN건까지 처리한다."""
    if not enabled():
        return 0
    try:
        import anthropic
    except ImportError:
        util.log("anthropic SDK missing; skip summaries")
        return 0
    client = anthropic.Anthropic()
    todo = [a for a in articles if not a.get("summary") and a.get("llm_tries", 0) < 3]
    todo.sort(key=lambda a: -a["t0"])
    done = 0
    for a in todo[: config.LLM_MAX_PER_RUN]:
        a["llm_tries"] = a.get("llm_tries", 0) + 1
        try:
            res = client.beta.messages.create(
                model=config.LLM_MODEL,
                max_tokens=2000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                system=SYSTEM,
                output_config={"effort": config.LLM_EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": _prompt(a)}],
            )
        except anthropic.RateLimitError:
            util.log("LLM rate limited; stop this run")
            break
        except anthropic.APIStatusError as e:
            util.log("LLM status error", e.status_code)
            if e.status_code < 500:
                break
            continue
        except anthropic.APIConnectionError:
            util.log("LLM connection error")
            break
        if res.stop_reason == "refusal":
            continue
        text = next((b.text for b in res.content if b.type == "text"), "")
        try:
            out = json.loads(text)
        except ValueError:
            continue
        source_text = a["title_orig"] + " " + (a.get("excerpt") or "")
        if not _valid(out, source_text):
            util.log("summary rejected", a["id"])
            continue
        a["title"] = out["title_ko"].strip()
        a["summary"] = [s.strip() for s in out["summary"]]
        a["summary_by"] = "llm"
        a["category"] = out["category"]
        known = [s for s in out["assets"] if s in config.ASSETS]
        if known:
            a["assets"] = known[: config.MAX_ASSETS_PER_ARTICLE]
        a["importance"] = max(a.get("importance", 1), int(out["importance"]))
        done += 1
    return done
