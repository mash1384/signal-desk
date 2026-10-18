"""공유 카드 이미지(JPEG). Playwright로 크롬을 띄워 HTML을 찍는다. 없으면 건너뛴다."""

import html
import os

from . import util

_STYLE = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
@import url('https://fonts.googleapis.com/css2?family=Michroma&display=swap');
*{margin:0;box-sizing:border-box}
html,body{width:%dpx;height:%dpx;overflow:hidden;background:#f7f9fc;color:#0d253d;
 font-family:'Pretendard','Noto Sans CJK KR','Noto Sans KR','Apple SD Gothic Neo',sans-serif;word-break:keep-all}
.wrap{position:relative;width:100%%;height:100%%;padding:64px 72px;display:flex;flex-direction:column}
.glow{position:absolute;inset:0;background:radial-gradient(55%% 70%% at 100%% 0%%,rgba(83,58,253,.13),transparent 70%%),radial-gradient(45%% 60%% at 0%% 100%%,rgba(14,159,110,.08),transparent 70%%)}
.brand{position:relative;display:flex;align-items:center;gap:14px;color:#000}
.mark{width:40px;height:40px}
.wm{font-family:'Michroma',sans-serif;font-size:22px;letter-spacing:.24em;text-transform:uppercase}
.meta{position:relative;margin-top:auto;display:flex;gap:14px;align-items:center;font-size:24px;color:#5b6b82}
.chip{padding:6px 16px;border-radius:999px;background:#eef0ff;color:#533afd;font-weight:700;font-size:20px}
h1{position:relative;margin-top:40px;font-size:%dpx;line-height:1.26;font-weight:700;letter-spacing:-.03em;
 display:-webkit-box;-webkit-line-clamp:%d;-webkit-box-orient:vertical;overflow:hidden}
.sub{position:relative;margin-top:22px;font-size:30px;color:#5b6b82;font-weight:500}
.imp{position:relative;margin-top:28px;display:inline-flex;gap:12px;align-items:baseline;font-size:34px;font-weight:700}
.imp small{font-size:22px;color:#5b6b82;font-weight:600}
.up{color:#0e9f6e}.down{color:#df4a3a}
ol{position:relative;margin-top:30px;padding-left:0;list-style:none;display:grid;gap:18px}
li{display:grid;grid-template-columns:44px 1fr auto;gap:14px;align-items:baseline;font-size:30px;font-weight:700;line-height:1.3}
li span{color:#533afd;font-size:26px}
li em{font-style:normal;font-size:24px}
"""

# 카드 모양을 바꾸면 올린다. 예전 모양으로 만든 카드는 한 번에 몇 장씩 다시 그린다
OG_VER = 2


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
    return ('<div class="brand"><svg class="mark" viewBox="0 0 100 100" fill="currentColor"><circle cx="46" cy="54" r="30"/>'
            '<path d="M75.88 70.22 A32.6 32.6 0 1 0 29.78 24.12 A34 34 0 0 1 40.31 20.48 A29.4 29.4 0 0 1 79.52 59.69 A34 34 0 0 1 75.88 70.22 Z"/></svg>'
            '<span class="wm">Delfona</span></div>')


CAT_LABEL = {"crypto": "Crypto", "ai": "AI", "macro": "Macro"}
WIN_LABEL = {"15m": "15m", "1h": "1h", "24h": "24h"}


def article_card(a):
    hd = a.get("headline")
    imp = ""
    if hd:
        d = "up" if hd["r"] >= 0 else "down"
        imp = '<div class="imp %s">%s %s %s%s%.2f%%<small>%s</small></div>' % (
            d, hd["asset"], WIN_LABEL.get(hd["win"], hd["win"]), "vs market " if hd.get("adj") else "", "+" if hd["r"] >= 0 else "−", abs(hd["r"]), " after the story")
    inner = '%s<h1>%s</h1>%s<div class="meta"><span class="chip %s">%s</span>%s · %s KST</div>' % (
        _brand(), html.escape(a["title"]), imp, a["category"], CAT_LABEL.get(a["category"], a["category"]), html.escape(a["source_name"]),
        util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"))
    return _doc(1200, 630, 58 if len(a["title"]) < 40 else 50, 3, inner)


def default_card():
    inner = ('%s<h1>Market-moving news,<br>judged as it lands.</h1><p class="sub">시장을 움직이는 속보, 실시간 판정</p>'
             '<div class="meta">Crypto · Nasdaq · Economy · AI · World</div>') % _brand()
    return _doc(1200, 630, 64, 3, inner)


def brief_card(day_label, rows):
    items = "".join('<li><span>%02d</span>%s<em class="%s">%s %s%.2f%%</em></li>' % (
        i + 1, html.escape(r["title"][:34] + ("…" if len(r["title"]) > 34 else "")), "up" if r["r"] >= 0 else "down",
        r["asset"], "+" if r["r"] >= 0 else "−", abs(r["r"])) for i, r in enumerate(rows[:5]))
    inner = '%s<h1>지난 24시간 가격 반응이 컸던 소식 · %s</h1><ol>%s</ol><div class="meta">지난 24시간 · 같은 시간에 있었던 일일 뿐 원인이라는 뜻은 아님</div>' % (
        _brand(), html.escape(day_label), items)
    return _doc(1080, 1080, 52, 2, inner)


def render(cam, out, articles, limit=30):
    """새 기사 카드와 기본 카드를 만든다. 만든 기사에는 og=True를 표시한다."""
    if not cam.available:
        return False
    os.makedirs(os.path.join(out, "og"), exist_ok=True)
    default_png = os.path.join(out, "og", "default.jpg")
    mark = os.path.join(out, "og", "default-v%d.txt" % OG_VER)
    if (not os.path.isfile(default_png) or not os.path.isfile(mark)) and cam.shoot(default_card(), default_png, 1200, 630):
        util.write_text(mark, "")
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
        refresh = exists and ((a.get("headline") and not a.get("og_has_impact")) or a.get("og_v") != OG_VER)
        if exists and not refresh:
            continue
        if cam.shoot(article_card(a), png, 1200, 630):
            a["og"] = True
            a["og_has_impact"] = bool(a.get("headline"))
            a["og_v"] = OG_VER
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
