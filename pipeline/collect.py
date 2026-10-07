"""RSS·Atom 수집, 정제, 중복 제거."""

import html
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from . import config, classify, util

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TRACKING = ("utm_", "fbclid", "gclid", "ref", "cmpid", "mod")


def clean_text(raw, limit=None):
    if not raw:
        return ""
    text = html.unescape(_TAG.sub(" ", html.unescape(raw)))
    text = _WS.sub(" ", text).strip()
    if limit and len(text) > limit:
        cut = text[:limit]
        space = cut.rfind(" ")
        if space > limit * 0.6:
            cut = cut[:space]
        text = cut.rstrip(" ,.·") + "…"
    return text


def normalize_url(url):
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith(_TRACKING)]
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    return urlunsplit((scheme, parts.netloc.lower(), parts.path.rstrip("/") or "/", urlencode(query), ""))


def _local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node, names):
    for child in node:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text
    return ""


def _link(node):
    for child in node:
        if _local(child.tag) == "link":
            href = child.get("href")
            if href and child.get("rel", "alternate") == "alternate":
                return href
            if (child.text or "").strip():
                return child.text.strip()
    guid = _child_text(node, ("guid",))
    return guid.strip() if guid.strip().startswith("http") else ""


def parse_feed(body):
    """피드 바이트를 [{title, url, summary, published}]로. 깨진 XML이면 정규식으로 한 번 더 시도한다."""
    items = []
    try:
        root = ET.fromstring(body)
        nodes = [n for n in root.iter() if _local(n.tag) in ("item", "entry")]
        for n in nodes:
            items.append({
                "title": _child_text(n, ("title",)),
                "url": _link(n),
                "summary": _child_text(n, ("description", "summary", "encoded", "content")),
                "published": _child_text(n, ("pubdate", "published", "updated", "date")),
            })
        return items
    except ET.ParseError:
        pass
    text = body.decode("utf-8", errors="replace")
    for block in re.findall(r"<item[\s>].*?</item>", text, re.S | re.I):
        def grab(tag):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), block, re.S | re.I)
            if not m:
                return ""
            val = m.group(1)
            cdata = re.match(r"\s*<!\[CDATA\[(.*?)\]\]>\s*$", val, re.S)
            return cdata.group(1) if cdata else val
        items.append({"title": grab("title"), "url": grab("link").strip(), "summary": grab("description"), "published": grab("pubDate")})
    return items


def _tokens(title):
    return set(re.findall(r"[\w가-힣]{2,}", title.lower()))


def is_duplicate(title, url_key, t0, existing):
    """URL이 같거나, 6시간 안에 제목 단어가 80% 이상 겹치면 중복."""
    toks = _tokens(title)
    for a in existing:
        if a["url_key"] == url_key:
            return True
        if abs(a["t0"] - t0) > 6 * 3600 or not toks:
            continue
        other = _tokens(a.get("title_orig") or a["title"])
        if other:
            inter = len(toks & other)
            if inter / max(1, min(len(toks), len(other))) >= 0.8 and inter >= 3:
                return True
    return False


def build_article(src, raw, now):
    title = clean_text(raw["title"], 220)
    url = (raw["url"] or "").strip()
    if not title or not url.startswith("http"):
        return None
    published = util.parse_time(raw.get("published"))
    estimated = False
    if published is None or published > now + 300:
        published, estimated = now, True
    t0 = min(published, now)
    if now - t0 > config.INGEST_MAX_AGE_HOURS * 3600:
        return None
    excerpt = clean_text(raw.get("summary"), 180)
    if excerpt and excerpt.startswith(title[:30]):
        excerpt = ""
    category = classify.classify(title, excerpt, src)
    if category is None:
        return None
    assets = classify.extract_assets(title, excerpt)
    etype = classify.event_type(title, excerpt, category)
    url_key = normalize_url(url)
    return {
        "id": util.kst(t0).strftime("%Y%m%d") + "-" + util.short_hash(url_key),
        "source": src["id"],
        "source_name": src["name"],
        "lang": "ko" if util.has_hangul(title) else src["lang"],
        "url": url,
        "url_key": url_key,
        "title": title,
        "title_orig": title,
        "excerpt": excerpt,
        "summary": [],
        "summary_by": None,
        "category": category,
        "assets": assets,
        "importance": classify.importance(title, excerpt, src["id"], category, assets),
        "etype": etype,
        "tags": classify.tags_for(title, assets, etype),
        "t0": t0,
        "t0_estimated": estimated,
        "collected": now,
        "impact": {},
    }


def collect(existing, health, now):
    """모든 소스를 돌며 새 기사를 돌려준다. 소스 하나가 실패해도 나머지는 계속한다."""
    fresh = []
    pool = list(existing)
    for src in config.SOURCES:
        state = health.setdefault(src["id"], {"name": src["name"], "ok": None, "error": None, "count": 0})
        try:
            items = parse_feed(util.http_get(src["url"], timeout=20, retries=1))
        except Exception as e:  # 소스 단위로 격리
            state.update({"error": str(e)[:200], "failed_at": now})
            util.log("source failed", src["id"], e)
            continue
        added = 0
        for raw in items[: config.PER_SOURCE_LIMIT]:
            art = build_article(src, raw, now)
            if art is None or is_duplicate(art["title"], art["url_key"], art["t0"], pool):
                continue
            pool.append(art)
            fresh.append(art)
            added += 1
        state.update({"ok": now, "error": None, "count": len(items), "added": added})
    return fresh
