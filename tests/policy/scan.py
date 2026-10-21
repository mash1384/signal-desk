"""Public artifact policy. Reports locations, never the matching secret value."""
import base64
import binascii
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import importlib.util
import os
import re
import struct
from urllib.parse import unquote
import zlib

ROOT = Path(__file__).resolve().parents[2]
EXCERPT_LIMIT = 180  # measured feed/articles maximum; pipeline/collect.py clean_text(..., 180)
# Prefixes identify credentials even inside URLs. Unlabelled hashes are public data.
SECRETS = re.compile(r"\bsk-(?:proj-|ant-[a-z0-9]+-)?[A-Za-z0-9_]{20,}|\bghp_[A-Za-z0-9_]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|(?<!\d)\d{6,12}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])|\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I)
URL = re.compile(r"https?://[^\s\"'<>]+", re.I)
URL_SECRET = re.compile(r"[?&](?:api_?key|key|token|access_token|secret|auth)=[^&#\s\"']{8,}", re.I)


def normalize(text):
    return unquote(unescape(text))


def field_name(name):
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower().replace("-", "_")


def secret_field(name):
    name = field_name(name)
    return name in {"api_hash", "api_key", "access_token", "token", "secret", "password", "authorization"} or name.endswith(("_token", "_secret"))


def secret_in(text, field=""):
    text = normalize(text)
    if SECRETS.search(text) or any(URL_SECRET.search(u) for u in URL.findall(text)):
        return True
    # URL-valued fields (including url_key) use the URL checks above only.
    if secret_field(field) and not URL.fullmatch(text):
        if re.fullmatch(r"[A-Za-z0-9_+/=-]{16,}", text):
            return True
        try:
            decoded = base64.b64decode(text, validate=True).decode("utf-8")
        except (ValueError, UnicodeError, binascii.Error):
            return False
        return bool(SECRETS.search(normalize(decoded)))
    return False


def png_text(path):
    """Read only PNG textual metadata, including compressed/international chunks."""
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG signature: " + str(path))
    offset, texts = 8, []
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG data")
        chunk = data[offset + 8:end - 4]
        if kind == b"tEXt":
            texts.append(chunk.replace(b"\0", b" ").decode("latin-1"))
        elif kind == b"zTXt":
            key, rest = chunk.split(b"\0", 1)
            if rest[:1] != b"\0":
                raise ValueError("unsupported PNG text compression")
            texts.append(key.decode("latin-1") + " " + zlib.decompress(rest[1:]).decode("latin-1"))
        elif kind == b"iTXt":
            key, rest = chunk.split(b"\0", 1)
            flag, method = rest[:2]
            if flag not in (0, 1) or method != 0:
                raise ValueError("unsupported PNG international text compression")
            language, translated, content = rest[2:].split(b"\0", 2)
            if flag:
                content = zlib.decompress(content)
            texts.extend((key.decode("latin-1"), translated.decode("utf-8"), content.decode("utf-8")))
        offset = end
        if kind == b"IEND":
            break
    return "\n".join(texts)


AI_KEYS = {"ko", "s_ko", "headline", "review", "say", "summary", "sum", "insights", "so_far", "today", "insight", "ai"}


def names_pattern():
    """막을 이름(정규식 조각을 | 로 이은 것). 공개 저장소에는 목록이 없다 — 어디서 받는지 순서대로:
    1) 환경변수 SIGNAL_POLICY_NAMES (GitHub 비밀값 · 운영자 Mac)
    2) 비공개 저장소의 tools/policy_names.py
    3) 운영자 Mac 의 ~/.signal/policy_names.txt
    셋 다 없으면 멈춘다(목록 없이 '통과'시키지 않는다)."""
    env = os.environ.get("SIGNAL_POLICY_NAMES", "").strip()
    if env:
        return env
    private = ROOT / "tools" / "policy_names.py"
    if private.is_file():
        spec = importlib.util.spec_from_file_location("policy_names", private)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return "|".join(mod.fragments())
    local = Path.home() / ".signal" / "policy_names.txt"
    if local.is_file() and local.read_text().strip():
        return local.read_text().strip()
    raise ValueError("source-name policy list missing: set SIGNAL_POLICY_NAMES (GitHub secret) or ~/.signal/policy_names.txt")


# 텔레그램을 '우리 출처'로 드러내는 것만 위반: 링크 · '출처: 텔레그램' 같은 표기는 어디서든,
# 채널 · 매체 이름은 출처 칸(src · source_name · outlets 등)에 들어갔을 때만. 다른 언론 기사 발췌가
# 그 언론을 인용하는 것은 그 언론의 본문이라 허용한다. 이름 목록은 비공개(names_pattern).
SOURCE = re.compile(r"t\.me/|telegram\.(?:me|org)/|tg://|(?:출처|source)\s*[:：]?\s*(?:텔레그램|telegram)|(?:텔레그램|telegram)\s*[:：]?\s*(?:채널|출처|channel|source)", re.I)
NAMES = re.compile(names_pattern(), re.I)
SOURCE_KEYS = {"src", "source", "source_name", "source_title", "sourcename", "sourcetitle", "sources", "outlet", "outlets", "via", "by", "from", "publisher", "channel", "author"}


def strings(doc, path=()):
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from strings(v, path + (str(k),))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from strings(v, path + (str(i),))
    elif isinstance(doc, str):
        yield path, doc


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.visible = []
        self.quotes = []
        self.quote_depth = 0
        self.current = []
        self.source_stack = []
        self.source_text = []
        self.has_meta = False
        self.source_markers = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        meta = "meta" in a.get("class", "").split()
        marker = "data-source-name" in a
        self.has_meta = self.has_meta or meta
        self.source_markers += int(marker)
        if marker:
            self.source_text.append(a["data-source-name"] or "")
        active = bool(meta or marker or (self.source_stack and self.source_stack[-1][1]))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.source_stack.append((tag, active))
        if tag in ("script", "style"):
            self.hidden += 1
        if self.quote_depth:
            self.quote_depth += 1
        elif "quote2" in a.get("class", "").split():
            self.quote_depth = 1
            self.current = []
        for key, val in attrs:
            if key in ("href", "src", "title", "aria-label") and val:
                self.visible.append(val)

    def handle_endtag(self, tag):
        for i in range(len(self.source_stack) - 1, -1, -1):
            if self.source_stack[i][0] == tag:
                del self.source_stack[i:]
                break
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if self.quote_depth:
            self.quote_depth -= 1
            if not self.quote_depth:
                self.quotes.append("".join(self.current))

    def handle_data(self, data):
        if not self.hidden and self.source_stack and self.source_stack[-1][1]:
            self.source_text.append(data)
        if not self.hidden:
            self.visible.append(data)
        if self.quote_depth:
            self.current.append(data)


def scan(root):
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError("policy input directory missing: " + str(root))
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".html", ".js", ".css", ".xml", ".txt", ".svg", ".png")]
    if not files:
        raise ValueError("policy input has no inspectable artifacts")
    errors = []
    excerpts = []
    for file in sorted(files):
        name = str(file.relative_to(root))
        raw = png_text(file) if file.suffix.lower() == ".png" else file.read_text(encoding="utf-8")
        raw_secret = secret_in(raw)
        if raw_secret:
            errors.append({"file": name, "rule": "secret-pattern", "path": "$", "message": "possible credential (value redacted)"})
        if file.suffix == ".json":
            doc = json.loads(raw)  # malformed JSON is fatal, not a clean scan
            for path, value in strings(doc):
                loc = "/" + "/".join(path)
                if not raw_secret and secret_in(value, path[-1] if path else ""):
                    errors.append({"file": name, "rule": "secret-pattern", "path": loc, "message": "possible encoded credential (value redacted)"})
                if SOURCE.search(normalize(value)) or (SOURCE_KEYS.intersection(field_name(p) for p in path) and NAMES.search(normalize(value))):
                    errors.append({"file": name, "rule": "telegram-source", "path": loc})
                if path and path[-1] in {"ex", "excerpt", "body", "full_text", "article_body"}:
                    excerpts.append(len(value))
                    if len(value) > EXCERPT_LIMIT:
                        errors.append({"file": name, "rule": "excerpt-length", "path": loc, "length": len(value), "limit": EXCERPT_LIMIT})
                if AI_KEYS.intersection(path) and "en" not in path and "s_en" not in path and re.search("[가-힣]", value):
                    if re.search(r"\s쪽|;", value):
                        errors.append({"file": name, "rule": "ai-korean-style", "path": loc})
        elif file.suffix == ".html":
            html = PublicHTML()
            html.feed(raw)
            if re.fullmatch(r"a/[^/]+/index\.html", name) and html.has_meta and not html.source_markers:
                errors.append({"file": name, "rule": "missing-source-marker", "path": ".meta"})
            if not raw_secret and secret_in(" ".join(html.visible)):
                errors.append({"file": name, "rule": "secret-pattern", "path": "visible HTML/attributes", "message": "possible encoded credential (value redacted)"})
            # 링크·'출처: 텔레그램' 표기는 '어디서든' 위반이므로 보이는 글자뿐 아니라 HTML 원문 전체(인라인 script, data-* · meta 속성)도 본다
            if SOURCE.search(normalize(" ".join(html.visible))) or SOURCE.search(normalize(raw)) or NAMES.search(normalize(" ".join(html.source_text))):
                errors.append({"file": name, "rule": "telegram-source", "path": "visible HTML/attributes"})
            for i, quote in enumerate(html.quotes):
                excerpts.append(len(quote))
                if len(quote) > EXCERPT_LIMIT:
                    errors.append({"file": name, "rule": "excerpt-length", "path": ".quote2[%d]" % i, "length": len(quote), "limit": EXCERPT_LIMIT})
        elif SOURCE.search(normalize(raw)):
            errors.append({"file": name, "rule": "telegram-source", "path": "$"})
    return {"files": len(files), "max_excerpt": max(excerpts or [0]), "errors": errors}
