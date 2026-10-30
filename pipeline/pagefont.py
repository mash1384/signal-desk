"""페이지 글꼴(2026-10-30): 한 페이지에 실제로 나오는 글자만 담은 Pretendard 한 파일.

왜: 일정 페이지는 화면 글자에 따라 CDN 의 한글 조각(하나 20~29KB)을 골라 받는다. 매시간 AI 가 새로 쓰는
경제 요약에 드문 글자 하나('안팎'의 '팎')만 들어가도 조각이 하나 더 받아져 용량이 흔들렸고, 게시 검사가
11시간 막혔다(10-30 장애). 빌드 때 '페이지 HTML + 그 페이지가 읽는 자료 + 그 페이지 스크립트'의 글자로
한 파일(약 100KB, CDN 조각 13개 334KB 대신)을 만들고 unicode-range 로 그 글자만 맡긴다.
미리 알 수 없는 글자(실시간으로 들어온 새 단어 등)는 지금처럼 CDN 조각이 맡는다.

원본: Pretendard 1.3.9 가변(pipeline/fonts — tests/e2e/vendor 의 QA 고정본과 같은 바이트, SHA 로 확인). 수정본 이름은
'DF Page Text'(OFL 예약 이름 규칙, tests/perf/font_names). 같은 글자 묶음이면 같은 파일 이름 · 같은 바이트.
"""
import hashlib
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "pipeline", "fonts", "pretendard-1.3.9-variable.woff2")
SOURCE_SHA = "9599f12fd42fc0bce1cd50b47a0c022e108d7aa64dd0d1bb0ed44f3282d900b4"
FAMILY = "DF Page Text"
ASCII = "".join(map(chr, range(32, 127)))
_cmap = None


def strings(obj):
    """자료(JSON) 안의 모든 글자열."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def page_text(page_html):
    return html.unescape(re.sub(r"<[^>]+>", " ", page_html)) + page_html   # 보이는 글자 + 속성 · 스크립트 안 글자


def unicode_range(cps):
    out, start, prev = [], None, None
    for c in cps:
        if start is None:
            start = prev = c
        elif c == prev + 1:
            prev = c
        else:
            out.append((start, prev))
            start = prev = c
    if start is not None:
        out.append((start, prev))
    return ",".join("U+%X" % a if a == b else "U+%X-%X" % (a, b) for a, b in out)


def codepoints(text):
    global _cmap
    if _cmap is None:
        from fontTools.ttLib import TTFont
        with TTFont(SOURCE, lazy=True) as f:
            _cmap = set(f.getBestCmap())
    return sorted(c for c in set(map(ord, text + ASCII)) if c in _cmap)


def build(out, name, text, base):
    """out/assets/fonts/page/<name>-<글자 해시>.woff2 를 만들고 @font-face CSS · 미리 읽기 태그를 돌려준다."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from tests.perf.font_names import rename_pretendard, reserved_names
    cps = codepoints(text)
    key = hashlib.sha1(",".join(map(str, cps)).encode()).hexdigest()[:12]
    rel = "assets/fonts/page/%s-%s.woff2" % (name, key)
    path = os.path.join(out, rel)
    if not os.path.exists(path):
        with open(SOURCE, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != SOURCE_SHA:
                raise RuntimeError("Pretendard 원본이 바뀜")
        with TTFont(SOURCE, recalcTimestamp=False) as font:
            opts = subset.Options()
            opts.recalc_timestamp = False
            opts.layout_features = list(dict.fromkeys(opts.layout_features + ["tnum"]))
            sub = subset.Subsetter(options=opts)
            sub.populate(unicodes=cps)
            sub.subset(font)
            rename_pretendard(font, FAMILY)
            if reserved_names(font):
                raise RuntimeError("예약 글꼴 이름이 남음")
            font.flavor = "woff2"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            font.save(path)
    url = base + rel
    css = ('@font-face{font-family:"%s";font-style:normal;font-weight:100 900;font-display:swap;src:url("%s") format("woff2");unicode-range:%s}'
           ':root,:lang(ko){--sans:"%s","Pretendard Variable",Pretendard,"PF Fallback",system-ui,sans-serif}') % (FAMILY, url, unicode_range(cps), FAMILY)
    head = '<link rel="preload" as="font" type="font/woff2" crossorigin href="%s">\n<style>%s</style>\n' % (url, css)
    return head, {"file": rel, "codepoints": len(cps), "bytes": os.path.getsize(path)}


JS = re.compile(r"""assets/df/([a-z0-9]+\.js)\?v=|(?:from|import)\s*\(?\s*['"]\./([a-z0-9]+\.js)(?:\?v=[^'"]*)?['"]""")


def scripts(out, page_html):
    """페이지가 부르는 우리 스크립트와 그 스크립트가 불러오는 모듈(import ... from './x.js')까지 전부."""
    seen, todo = [], [a or b for a, b in JS.findall(page_html)]
    while todo:
        name = todo.pop()
        p = os.path.join(out, "assets", "df", name)
        if name in seen or not os.path.isfile(p):
            continue
        seen.append(name)
        with open(p, encoding="utf-8") as f:
            todo += [a or b for a, b in JS.findall(f.read())]
    return [os.path.join(out, "assets", "df", n) for n in seen]


def calendar(out, page_html, base, econ_path):
    """일정 페이지: HTML + econ.json(브라우저가 그리는 문장) + 이 페이지가 부르는 우리 스크립트(배포본, 주석 뺀 것)."""
    text = page_text(page_html)
    if os.path.isfile(econ_path):
        with open(econ_path, encoding="utf-8") as f:
            text += "".join(strings(json.load(f)))
    for p in scripts(out, page_html):
        with open(p, encoding="utf-8") as f:
            text += f.read()
    head, info = build(out, "calendar", text, base)
    return page_html.replace("</head>", head + "</head>", 1), info
