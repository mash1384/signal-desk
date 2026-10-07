"""공유 카드 이미지(JPEG). Playwright로 크롬을 띄워 HTML을 찍는다. 없으면 건너뛴다."""

import html
import os

from . import config, util

_STYLE = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
*{margin:0;box-sizing:border-box}
html,body{width:%dpx;height:%dpx;overflow:hidden;background:#0d0d10;color:#f4f4f6;
 font-family:'Pretendard','Noto Sans CJK KR','Noto Sans KR','Apple SD Gothic Neo',sans-serif;word-break:keep-all}
.wrap{position:relative;width:100%%;height:100%%;padding:64px 72px;display:flex;flex-direction:column}
.glow{position:absolute;inset:0;background:radial-gradient(60%% 70%% at 85%% 0%%,rgba(214,255,63,.18),transparent 70%%),radial-gradient(50%% 60%% at 0%% 100%%,rgba(138,108,255,.22),transparent 70%%)}
.brand{position:relative;display:flex;align-items:center;gap:14px;font-size:30px;font-weight:800;letter-spacing:-.02em}
.mark{width:40px;height:40px}
.slash{color:#d6ff3f}
.meta{position:relative;margin-top:auto;display:flex;gap:14px;align-items:center;font-size:24px;color:#a8a8b3}
.chip{padding:6px 14px;border-radius:999px;border:2px solid currentColor;font-weight:700;font-size:20px;letter-spacing:.06em}
.crypto{color:#ffb547}.ai{color:#a996ff}.macro{color:#6be3c9}
h1{position:relative;margin-top:36px;font-size:%dpx;line-height:1.28;font-weight:800;letter-spacing:-.03em;
 display:-webkit-box;-webkit-line-clamp:%d;-webkit-box-orient:vertical;overflow:hidden}
.imp{position:relative;margin-top:28px;display:inline-flex;gap:12px;align-items:baseline;font-size:34px;font-weight:800}
.imp small{font-size:22px;color:#a8a8b3;font-weight:600}
.up{color:#4ade80}.down{color:#ff6b6b}
ol{position:relative;margin-top:30px;padding-left:0;list-style:none;display:grid;gap:18px}
li{display:grid;grid-template-columns:44px 1fr auto;gap:14px;align-items:baseline;font-size:30px;font-weight:700;line-height:1.3}
li span{color:#d6ff3f;font-size:26px}
li em{font-style:normal;font-size:24px}
"""


class Camera:
    """Playwright로 크롬을 한 번 띄워 여러 장을 찍는다. 설치돼 있지 않으면 available=False."""

    def __init__(self):
        self.available = False
        self._pw = self._browser = None
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            util.log("playwright missing; skip images")
            return
        try:
            self._pw = sync_playwright().start()
            try:
                self._browser = self._pw.chromium.launch(channel="chrome")
            except Exception:
                self._browser = self._pw.chromium.launch()
            self.available = True
        except Exception as e:
            util.log("browser launch failed", e)
            self.close()

    def shoot(self, page_html, png_path, w, h):
        if not self.available:
            return False
        page = None
        try:
            page = self._browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            page.set_content(page_html, wait_until="networkidle", timeout=20000)
            page.evaluate("document.fonts.ready.then(() => true)")
            page.screenshot(path=png_path, type="jpeg", quality=85)
            return os.path.getsize(png_path) > 2000
        except Exception as e:
            util.log("screenshot failed", e)
            return False
        finally:
            if page:
                page.close()

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self.available = False


def _doc(w, h, title_px, clamp, inner):
    return "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><style>%s</style></head><body><div class=\"wrap\"><div class=\"glow\"></div>%s</div></body></html>" % (
        _STYLE % (w, h, title_px, clamp), inner)


def _brand():
    return ('<div class="brand"><svg class="mark" viewBox="0 0 28 28"><rect x=".5" y=".5" width="27" height="27" rx="8" fill="#d6ff3f"/>'
            '<path d="M5 15h4l2.5-6 4 11 2.5-5H23" fill="none" stroke="#141418" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            'SIGNAL<span class="slash">/</span></div>')


def article_card(a):
    hd = a.get("headline")
    imp = ""
    if hd:
        d = "up" if hd["r"] >= 0 else "down"
        imp = '<div class="imp %s">%s %s %s%.2f%%<small>%s</small></div>' % (
            d, hd["asset"], hd["win"], "+" if hd["r"] >= 0 else "−", abs(hd["r"]), (" 반응 강도 " + hd["g"]) if hd.get("g") else "")
    inner = '%s<h1>%s</h1>%s<div class="meta"><span class="chip %s">%s</span>%s · %s KST</div>' % (
        _brand(), html.escape(a["title"]), imp, a["category"], config.CATEGORY_LABEL[a["category"]], html.escape(a["source_name"]),
        util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"))
    return _doc(1200, 630, 58 if len(a["title"]) < 40 else 50, 3, inner)


def default_card():
    inner = '%s<h1>해외 속보를 한국어로,<br>그 뉴스가 움직인 가격까지.</h1><div class="meta">크립토 · AI · 매크로 시그널 데스크</div>' % _brand()
    return _doc(1200, 630, 64, 3, inner)


def brief_card(day_label, rows):
    items = "".join('<li><span>%02d</span>%s<em class="%s">%s %s%.2f%%</em></li>' % (
        i + 1, html.escape(r["title"][:34] + ("…" if len(r["title"]) > 34 else "")), "up" if r["r"] >= 0 else "down",
        r["asset"], "+" if r["r"] >= 0 else "−", abs(r["r"])) for i, r in enumerate(rows[:5]))
    inner = '%s<h1>오늘의 시그널 · %s</h1><ol>%s</ol><div class="meta">지난 24시간 가격 반응이 컸던 뉴스 · 상관이지 인과가 아님</div>' % (
        _brand(), html.escape(day_label), items)
    return _doc(1080, 1080, 52, 2, inner)


def render(cam, out, articles, limit=30):
    """새 기사 카드와 기본 카드를 만든다. 만든 기사에는 og=True를 표시한다."""
    if not cam.available:
        return False
    os.makedirs(os.path.join(out, "og"), exist_ok=True)
    default_png = os.path.join(out, "og", "default.jpg")
    if not os.path.isfile(default_png):
        cam.shoot(default_card(), default_png, 1200, 630)
    made = 0
    for a in articles:
        if made >= limit:
            break
        png = os.path.join(out, "og", a["id"] + ".jpg")
        # 공유 가치가 있는 기사(중요도 2 이상 또는 반응 강·중)만 만든다
        if a.get("importance", 1) < 2 and not ((a.get("headline") or {}).get("g") in ("강", "중")):
            continue
        exists = a.get("og") and os.path.isfile(png)
        # 반응이 측정되면 카드를 한 번 다시 그린다
        refresh = exists and a.get("headline") and not a.get("og_has_impact")
        if exists and not refresh:
            continue
        if cam.shoot(article_card(a), png, 1200, 630):
            a["og"] = True
            a["og_has_impact"] = bool(a.get("headline"))
            made += 1
        else:
            a["og"] = False
    util.log("og images", made)
    return os.path.isfile(default_png)


def render_brief(cam, out, day_label, rows):
    if not cam.available or not rows:
        return None
    path = os.path.join(out, "og", "brief.jpg")
    return path if cam.shoot(brief_card(day_label, rows), path, 1080, 1080) else None
