"""JSON Schema definitions grounded in consumers; export with python -m tests.schema.contracts.
Optional fields remain optional where JS has a fallback. Present fields still
have their type checked. No schema is inferred from a single production sample.
"""
import json
from pathlib import Path


def obj(props, required=None, comment=""):
    return {"type": "object", "properties": props, "required": list(props if required is None else required), "$comment": comment}


S = {"type": "string"}
N = {"type": "number"}
B = {"type": "boolean"}
I = {"type": "integer"}
NULLNUM = {"type": ["number", "null"]}


def arr(item):
    return {"type": "array", "items": item}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def mapping(value):
    return {"type": "object", "additionalProperties": value}


STRINGS = arr(S)
BI = obj({"ko": S, "en": S})
AI_LINE = obj({"s": S, "refs": STRINGS})
THREAD_AI = obj({"title": S, "so_far": arr(AI_LINE), "today": nullable(AI_LINE)}, ["title", "so_far"])
STORY = obj({"id": S, "t": N, "ko": S, "en": S, "v": {"enum": ["호재", "악재", "중립"]}, "s": I, "kind": S, "coins": STRINGS, "sectors": STRINGS, "mw": B, "n": I, "link": S, "th": STRINGS}, ["t", "ko", "en", "v", "s", "kind", "coins", "n"], "web/assets/df/lk.js pull, detailHTML; brk.js stripHTML, cardHTML")
THEME_STORY = dict(STORY, required=[k for k in STORY["required"] if k != "coins"], **{"$comment": "theme_brief.compact article rows omit coins; lk.js chips/detailHTML use (it.coins || [])"})
RELEASE_VALUE = obj({"disp": arr(nullable(S)), "disp_prev": arr(nullable(S)), "v": NULLNUM, "prev": NULLNUM, "fc": nullable(S), "vs": nullable(S)}, ["disp", "disp_prev"])
RELEASE_AI = obj({"head": S, "s": STRINGS, "next": S, "by": S, "checked": B}, ["head", "s", "by"])
def tuple_of(*items):
    return {"type": "array", "prefixItems": list(items), "items": False, "minItems": len(items), "maxItems": len(items)}


PAIR = tuple_of(N, N)
MONTH = {"type": "string", "pattern": r"^\d{4}-(?:0[1-9]|1[0-2])$"}
QUAD = {"enum": ["hot", "stag", "gold", "slow"]}
PROB = {"type": "number", "minimum": 0, "maximum": 1}
FLAG = {"enum": [0, 1]}
PATH13 = dict(arr(N), minItems=13, maxItems=13)
BAND13 = obj({"n": I, "p25": PATH13, "p50": PATH13, "p75": PATH13})
AFTER = obj({"spx": N, "ff": N, "rec": FLAG}, comment="ek.js insightHTML analog after: pctS(spx), ff / 100, rec")
STAT = obj({"med": N, "up": PROB, "n": I})
AFTER_STATS = obj(dict({"n": I, "rec": PROB}, **{k: nullable(STAT) for k in ("spx", "y10", "ff", "cpi")}), ["n", "rec"], "ek.js table checks individual stats before rendering")
CURRENT = obj({"ym": MONTH, "q": QUAD, "cpi": N, "dcpi": N, "nfp3": N, "nfp3p": N, "ff": NULLNUM}, ["q", "cpi", "dcpi", "nfp3", "nfp3p"], "ek.js insightHTML directly formats cpi and momentum; ff has a null fallback")
REGIME = obj({
    "current": CURRENT,
    "quads": arr(obj({"k": QUAD, "ko": S, "en": S})),
    "months": dict(arr(tuple_of(MONTH, nullable(QUAD), FLAG, NULLNUM, NULLNUM, NULLNUM, NULLNUM)), minItems=1,
                   contains={"prefixItems": [{}, {}, {}, N], "minItems": 4}),
    "analogs": arr(obj({"ym": MONTH, "q": QUAD, "cpi": N, "nfp3": N, "un": N, "after": nullable(AFTER)}, ["ym", "q", "cpi", "nfp3", "un"])),
    "paths": nullable(obj({"analogs": mapping(PATH13), "like": nullable(BAND13), "typical": nullable(BAND13)}, ["analogs"])),
    "rare": nullable(obj({"episodes": arr(obj({"from": MONTH, "to": MONTH})), "after": nullable(AFTER_STATS)}, [])),
    "after_all": nullable(AFTER_STATS),
}, ["current", "quads", "months"], "ek.js insightHTML/drawRegime/drawTimeline require current/quads/months. Historical null values are filtered; at least one numeric CPI is needed for ms[n-1]. Optional analogs/paths/rare have explicit JS fallbacks; present internals are strict. drawPaths accesses all 13 monthly samples.")
FOMC = obj({"now": nullable(obj({"outcomes": arr(obj({"k": S, "p": nullable(PROB), "ko": S, "en": S}))})),
            "days": mapping(arr(tuple_of(N, PROB)))}, [], "ek.js insightHTML and drawFomc: now can be absent/null; outcomes are filtered with (p || 0); days indexed by outcome k")
FOMC["allOf"] = [{"if": {"required": ["now"], "properties": {"now": {"type": "object"}}}, "then": {"required": ["days"]}}]
RELEASE_MARKET = obj({"ko": S, "en": S, "base": {"type": "number", "exclusiveMinimum": 0}, "pts": arr(PAIR), "d15": NULLNUM, "d60": NULLNUM},
                     ["ko", "en", "base", "pts"], "tools/release_watch.py reaction emits base and pairs; ek.js drawRelease maps pts and divides by base; short series are explicitly filtered")
RELEASE = obj({"ts": N, "ko": S, "en": S, "values": mapping(RELEASE_VALUE), "ai": obj({"ko": RELEASE_AI, "en": RELEASE_AI}), "market": mapping(RELEASE_MARKET), "odds": nullable(obj({"rows": arr(obj({"ko": S, "en": S, "before": N, "after": NULLNUM}))}, ["rows"]))}, ["ts", "ko", "en", "values", "ai"], "web/assets/df/ek.js loadRelease, recent, releaseHTML")
LATEST = obj({"d": S, "ts": N, "period": S, "v": NULLNUM, "prev": NULLNUM, "sub": NULLNUM, "fc": nullable(S), "vs": nullable(S)}, ["d", "ts", "period", "v", "prev"])
INDICATOR = obj({"k": S, "en": S, "ko": S, "unit": S, "grp": S, "dec": I, "hot": N, "latest": LATEST, "sit": obj({"dir": S, "chg": N, "trend": nullable(S), "rank10y": NULLNUM, "vs_avg12": NULLNUM}), "rows": arr(obj({"d": S, "ts": N, "v": NULLNUM}, ["d", "ts", "v"])), "long": arr(arr({"type": ["string", "number", "null"]})), "similar": arr({"type": "object"}), "stats": {"type": "object"}, "paths": {"type": "object"}, "ai": nullable(obj({"ko": STRINGS, "en": STRINGS})), "disp": obj({"v": arr(nullable(S)), "prev": arr(nullable(S)), "chg": arr(nullable(S))})}, ["k", "en", "ko", "unit", "grp", "dec", "hot", "latest", "sit", "rows", "long", "similar", "stats", "paths"], "web/assets/df/ck.js loadEcon, fv, overviewHTML, indicator cards/details")
THEME = obj({"k": S, "n": I, "u": I, "d": I, "ko": S, "en": S, "s_ko": STRINGS, "s_en": STRINGS, "refs": arr(nullable(S)), "hours": arr(arr(N)), "sectors": arr({"type": "object"}), "mentions": mapping({"type": "object"}), "top": arr(STORY), "latest": arr(STORY), "more": arr(STORY), "changes": arr({"type": "object"})}, ["k", "n", "u", "d", "s_ko", "s_en", "hours", "sectors", "mentions", "top", "latest"], "web/assets/df/tk.js loadThemes, themeOf, loadAssets; t2.js summary and asset panels")

SCHEMAS = {
    "feed": obj({"at": N, "items": arr(obj({"id": S, "t0": N, "title": S, "src": S, "lang": S, "cat": S, "assets": STRINGS, "imp": I, "etype": S, "sum": STRINGS, "ex": S, "llm": B, "url": S, "st": S, "h": nullable({"type": "object"}), "rx": nullable({"type": "object"}), "ai": nullable({"type": "object"})}))}, comment="pipeline/build.py feed_item public build contract; current df consumers fetch related.json rather than feed.json"),
    "related": obj({"at": N, "items": arr(obj({"t0": N, "title": S, "src": S, "assets": STRINGS, "url": S}))}, comment="web/assets/df/lk.js start, related, detailHTML"),
    "flash": obj({"v": I, "at": N, "last_got": N, "items": arr(dict(STORY, required=STORY["required"] + ["id", "sectors", "mw", "link"])), "release": obj({"made": N, "items": arr(RELEASE)}, ["items"])}, ["at", "items"], "web/assets/df/data.js flash; lk.js pull; ek.js d.release.items is optional"),
    "econ": obj({"v": I, "made": N, "next": N, "groups": arr(obj({"k": S, "en": S, "ko": S})), "assets": arr(obj({"sym": S, "en": S, "ko": S, "kind": S})), "horizons": STRINGS, "indicators": arr(INDICATOR), "upcoming": arr(obj({"ts": N, "keys": STRINGS, "en": S, "ko": S, "impact": S, "items": arr({"type": "object"})}, ["ts", "keys", "en", "ko", "impact"])), "regime": nullable(REGIME), "insight": nullable(obj({"at": N, "ko": obj({"head": S, "s": STRINGS}), "en": obj({"head": S, "s": STRINGS})}, comment="ek.js insightHTML formats insight.at as a date")), "overview": nullable(obj({"ko": obj({"head": S, "s": STRINGS}), "en": obj({"head": S, "s": STRINGS})})), "fomc": nullable(FOMC)}, ["made", "groups", "assets", "horizons", "indicators", "upcoming"], "web/assets/df/ck.js loadEcon, overviewHTML, nextEvent; ek.js regime and insight"),
    "threads": obj({"v": I, "made": N, "next": N, "daily_latest": nullable(S), "stories": mapping(STORY), "threads": arr(obj({"id": S, "ids": STRINGS, "n": I, "first": N, "last": N, "days": I, "new24": I, "u": I, "d": I, "th": STRINGS, "ai": nullable(obj({"ko": THREAD_AI, "en": THREAD_AI}))}))}, ["made", "stories", "threads"], "web/assets/df/brk.js loadThreads, stripHTML, axisOf, cardHTML"),
    "themes": obj({"v": I, "made": N, "next": N, "themes": arr(THEME), "themes_x": arr(THEME), "headline": BI}, ["made", "themes"], "web/assets/df/tk.js loadThemes and themeOf; globe.js load; yk.js headlines"),
    "daily": obj({"v": I, "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}, "made": N, "headline": S, "review": S, "insights": arr(obj({"t": S, "s": S})), "counts": obj({"stories": I}, ["stories"]), "balance": obj({"호재": I, "악재": I, "중립": I}), "market": obj({"btc": nullable(obj({"chg": N, "close": N})), "eth": nullable(obj({"chg": N, "close": N}))}, []), "sections": {"type": "object"}}, ["date", "made", "headline", "review", "counts", "balance", "market", "sections"], "web/assets/df/brk.js dailyHTML; yk.js dailyHTML; pipeline/build.py page_daily"),
}

# brk.js loadThreads explicitly filters threads without AI; absence is valid.
SCHEMAS["threads"]["properties"]["threads"]["items"]["required"].remove("ai")
for name in ("top", "latest", "more"):
    THEME["properties"][name] = arr(THEME_STORY)


def export():
    root = Path(__file__).parent
    for name, schema in SCHEMAS.items():
        doc = dict(schema, **{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://delfona.example/schemas/" + name})
        (root / (name + ".schema.json")).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    export()
