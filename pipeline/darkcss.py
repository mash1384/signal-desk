"""다크 모드 CSS 자동 생성: 밝은 CSS 의 색 선언을 읽어 :root[data-theme="dark"] 규칙을 만든다.
밝은 화면을 고치면 다크도 따라온다. 손으로 다듬은 다크 규칙(소스에 이미 있는 것)이 뒤에 오므로 그쪽이 이긴다.

색 바꾸기(속성별):
- 배경: 아주 밝은 무채색 → 어두운 남색 면, 밝은 색조(초록 · 빨강 · 보라 · 노랑 바탕) → 같은 색조의 어두운 바탕,
        짙은 바탕(툴팁 등) → 한 단계 밝은 남색
- 글자: 짙은 색 → 밝은 글자, 중간 회색 → 밝은 회색, 강조색 → 어두운 면 위 대비 4.5:1 이 될 때까지 밝게, 흰 글자는 그대로
- 테두리 · 얇은 선(그림자 흐림 0~2px): 밝은 남색 반투명, 큰 그림자: 검정 반투명
"""
import colorsys
import re

DARK = ':root[data-theme="dark"]'
# 생성 규칙은 :where() 로 감싸 원래 밝은 규칙과 구체성이 같다 — '같은 규칙, 다른 색'. 더 구체적인 밝은 규칙(색은 변수)을 덮지 않는다
GEN = ':where(:root[data-theme="dark"])'
BG, SURF, SURF2, LINE = (11, 19, 32), (17, 27, 43), (24, 36, 58), (35, 50, 74)
INK, MUTE = (232, 238, 246), (163, 178, 199)
TOKENS = {"--ink": "#e8eef6", "--ink2": "#c9d4e3", "--mute": "#a3b2c7", "--faint": "#8d9bb2", "--line": "#23324a", "--soft": "#111b2b",
          "--primary": "#a99dff", "--navy": "#e8eef6", "--up": "#3fd29b", "--down": "#ff8e80", "--upS": "#10302a", "--downS": "#3a1d21"}
COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)")


def parse(c):
    """'#abc' · '#aabbcc' · '#aabbccdd' · 'rgb(1 2 3 / .5)' · 'rgba(1,2,3,.5)' → (r, g, b, a). 모르면 None."""
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(x * 2 for x in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a
    m = re.match(r"rgba?\(([^)]*)\)", c)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(1).strip()) if p]
    if len(parts) < 3:
        return None
    try:
        r, g, b = (float(p) for p in parts[:3])
        a = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1) if len(parts) > 3 else 1.0
    except ValueError:
        return None
    return int(r), int(g), int(b), a


def fmt(rgb, a=1.0):
    r, g, b = (max(0, min(255, int(round(x)))) for x in rgb)
    return "#%02x%02x%02x" % (r, g, b) if a >= 0.999 else "rgb(%d %d %d / %s)" % (r, g, b, ("%.2f" % a).rstrip("0").rstrip("."))


def lum(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hls(rgb):
    return colorsys.rgb_to_hls(*(x / 255 for x in rgb))


def from_hls(h, l, s):
    return tuple(x * 255 for x in colorsys.hls_to_rgb(h, l, s))


def background(rgb, a):
    h, l, s = hls(rgb)
    if l >= 0.93 and s < 0.35:                      # 흰색 · 아주 밝은 회색 면
        base = BG if (rgb[2] - rgb[0] > 3 and l < 0.985) else SURF   # 살짝 푸른 페이지 바탕(#f7f9fc 류)은 더 어둡게
        return fmt(base, a)
    if l >= 0.86 and s < 0.35:                      # 밝은 회색(칩 · 눌린 칸)
        return fmt(SURF2 if l >= 0.9 else LINE, a)
    if l >= 0.8:                                    # 밝은 색조 바탕(호재 초록 · 악재 빨강 · 보라 · 노랑)
        return fmt(from_hls(h, 0.15, min(0.55, s * 0.6)), a)
    if l <= 0.25 and a < 0.6:                       # 짙은 반투명 바탕(옅은 칸 · 막대) → 밝은 반투명
        return fmt(INK, min(0.5, a * 1.2))
    if l <= 0.25:                                   # 짙은 바탕(툴팁 · 반전 단추) → 한 단계 밝은 면
        return fmt((30, 44, 68), a)
    return None                                     # 진한 강조색 바탕(단추)은 그대로


def text(rgb, a):
    h, l, s = hls(rgb)
    if l >= 0.95 and s < 0.2:                       # 흰 글자(진한 바탕 위) 그대로. 반투명 흰 글자(눌린 단추 속 숫자)는 바탕이 밝아지므로 어둡게
        return fmt(BG, min(1.0, a + 0.15)) if a < 0.999 else None
    if l < 0.25 or (s < 0.25 and l < 0.35):         # 짙은 글자(남색 포함) → 밝은 글자
        return fmt(INK, a)
    if s < 0.25:                                    # 중간 회색 → 밝은 회색
        return fmt(MUTE, a)
    out, ll = rgb, l                                # 강조색: 어두운 면에서 4.5:1 이 될 때까지 밝게
    while contrast(out, SURF2) < 4.6 and ll < 0.95:
        ll += 0.02
        out = from_hls(h, ll, s)
    return fmt(out, a) if out != rgb else None


def fit(color, bg):
    """색 바탕(배지) 위 글자: 같은 규칙의 바탕과 대비 4.6:1 이 될 때까지 밝게."""
    c, b = parse(color), parse(bg)
    if not c or not b or c[3] < 0.999 or b[3] < 0.999:
        return color
    h, l, s = hls(c[:3])
    out = c[:3]
    while contrast(out, b[:3]) < 4.6 and l < 0.97:
        l += 0.02
        out = from_hls(h, l, s)
    return fmt(out)


def line(rgb, a, blur):
    if blur > 2.5:                                  # 그림자
        return fmt((0, 0, 0), min(0.7, a * 1.7 if a < 1 else 0.5))
    h, l, s = hls(rgb)
    if l <= 0.45 and s < 0.6:                       # 짙은 반투명 선(남색 고리) → 밝은 반투명 선
        return fmt(INK, min(0.3, a * 1.3) if a < 1 else 0.14)
    if l >= 0.8:                                    # 밝은 테두리 → 선 색
        return fmt(LINE if s < 0.35 else from_hls(h, 0.3, min(0.5, s)), a)
    return text(rgb, a)


def convert(prop, value):
    prop = prop.strip()
    prop = prop if prop.startswith("--") else prop.lower()
    if prop.startswith("--"):                       # 색 변수: 공용 다크 값(lk.css 와 같게). 부분에서 다시 정한 것(.cal { --up })도 따라온다
        return TOKENS.get(prop) if COLOR.search(value) else None
    if prop in ("color", "fill", "stroke", "caret-color", "-webkit-text-fill-color", "text-decoration-color"):
        kind = "text"
    elif prop.startswith("background"):
        kind = "bg"
    elif prop in ("box-shadow", "outline", "outline-color", "text-shadow") or prop.startswith("border"):
        kind = "line"
    else:
        return None
    changed = False

    def sub(m, blur=0.0):
        nonlocal changed
        c = parse(m.group(0))
        if c is None:
            return m.group(0)
        rgb, a = c[:3], c[3]
        new = background(rgb, a) if kind == "bg" else text(rgb, a) if kind == "text" else line(rgb, a, blur)
        if new is None:
            return m.group(0)
        changed = True
        return new

    if kind == "line" and prop in ("box-shadow", "text-shadow"):
        out = []
        for part in split_top(value):
            nums = [float(x) for x in re.findall(r"(?<![\w.#(])(-?\d*\.?\d+)(?:px)?(?=[\s,]|$)", COLOR.sub(" ", part))]
            blur = nums[2] if len(nums) >= 3 else 0.0
            out.append(COLOR.sub(lambda m, blur=blur: sub(m, blur), part))
        value2 = ", ".join(out)
    else:
        value2 = COLOR.sub(sub, value)
    return value2 if changed else None


def split_top(value):
    """쉼표로 나누되 괄호 안 쉼표는 무시."""
    parts, depth, cur = [], 0, ""
    for ch in value:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def norm(sel):
    return " ".join(sel.replace(DARK, "").replace(":where()", "").split())


def handmade(css):
    """손으로 쓴 다크 규칙: {밝은 선택자: {속성, …}}. 생성 규칙은 이 (선택자, 속성)을 건드리지 않는다."""
    out = {}
    for head, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in split_top(head):
            sel = sel.strip()
            for prefix in (":where(%s)" % DARK, DARK):
                if sel.startswith(prefix + " "):
                    props = {d.split(":", 1)[0].strip() for d in body.split(";") if ":" in d}
                    out.setdefault(sel[len(prefix):].strip(), set()).update(props)
                    break
    return out


def generate(css):
    """밝은 CSS → 다크 규칙 문자열. @media 안 규칙도 같은 @media 로 감싼다. 이미 다크인 규칙 · @keyframes 는 건너뛴다."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    hand = handmade(css)

    def rules(block, wrap=None):
        i = 0
        while i < len(block):
            j = block.find("{", i)
            if j < 0:
                break
            head = block[i:j].strip()
            depth, k = 1, j + 1
            while k < len(block) and depth:
                depth += block[k] == "{"
                depth -= block[k] == "}"
                k += 1
            body = block[j + 1:k - 1]
            i = k
            if head.startswith("@media") or head.startswith("@supports"):
                rules(body, head)
                continue
            if head.startswith("@") or DARK in head or "data-theme" in head:
                continue
            decls = []
            for d in body.split(";"):
                if ":" not in d:
                    continue
                prop, val = d.split(":", 1)
                new = convert(prop, val)
                if new is not None:
                    decls.append((prop.strip(), new.strip()))
            # 진한 글자색 바탕 + 흰 글자(눌린 단추 · 알림 알약): 다크에선 바탕이 밝은 글자색이 되므로 글자를 어둡게
            if re.search(r"background(-color)?\s*:\s*var\(--(ink|navy)\)", body) and re.search(r"(^|;)\s*color\s*:\s*#fff(fff)?\b", body):
                decls.append(("color", "#0b1320"))
            bg = next((v for p, v in decls if p in ("background", "background-color") and COLOR.fullmatch(v)), None)
            if bg:
                decls = [(p, fit(v, bg) if p == "color" and COLOR.fullmatch(v) else v) for p, v in decls]
            if not decls:
                continue
            groups = {}   # 손으로 쓴 다크 규칙이 이미 정한 (선택자, 속성)은 빼고, 남은 선언이 같은 선택자끼리 묶는다
            for s in split_top(head):
                s = s.strip()
                keep = tuple(d for d in decls if d[0] not in hand.get(norm(s), ()))
                if keep:
                    groups.setdefault(keep, []).append(s)
            for keep, heads in groups.items():
                emit(heads, keep, wrap)

    def emit(heads, decls, wrap):
            sels = []
            for s in heads:
                s = s.strip()
                if not s or s.startswith(("from", "to")) or re.fullmatch(r"\d+%", s):
                    continue
                if s in (":root", "html"):
                    sels.append(DARK)
                elif s.startswith(("html ", "html.", "html[")):
                    sels.append(DARK + s[4:])
                else:
                    sels.append(GEN + " " + s)
            if sels:
                rule = "%s { %s; }" % (", ".join(sels), "; ".join("%s: %s" % d for d in decls))
                out.append("%s { %s }" % (wrap, rule) if wrap else rule)

    rules(css)
    return "\n".join(out)


def inject(css):
    """소스 CSS 끝에 생성 규칙을 붙인다. 손으로 쓴 다크 규칙(:root[data-theme="dark"] …)은 구체성이 더 높아 그대로 이긴다."""
    gen = generate(css)
    return css + "\n/* ---------- 다크 모드 자동 생성(pipeline/darkcss.py) ---------- */\n" + gen + "\n" if gen else css
