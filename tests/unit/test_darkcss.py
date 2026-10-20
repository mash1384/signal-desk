"""다크 모드 CSS 자동 생성(pipeline/darkcss.py): 색 바꾸기 · 구체성 · 손으로 쓴 규칙 존중 · 글자 대비."""
import re
import unittest

from pipeline import darkcss

GEN = darkcss.GEN


def rules(css):
    """생성 결과 → {선택자: {속성: 값}} (@media 감싼 규칙은 키 앞에 '@')."""
    out = {}
    for line in darkcss.generate(css).splitlines():
        media = line.startswith("@")
        if media:
            line = line[line.index("{") + 1:line.rindex("}")].strip()
        head, body = line.split("{", 1)
        decls = dict(d.split(":", 1) for d in body.rstrip("} ;").split(";") if ":" in d)
        for sel in head.split(", "):
            out[("@" if media else "") + sel.strip()] = {k.strip(): v.strip() for k, v in decls.items()}
    return out


class DarkCss(unittest.TestCase):
    def test_surfaces_text_and_borders(self):
        r = rules(".card { background: #fff; color: #0d253d; border: 1px solid #e3e8ee; }")
        d = r[GEN + " .card"]
        self.assertEqual(d["background"], "#111b2b")
        self.assertEqual(d["color"], "#e8eef6")
        self.assertIn("#23324a", d["border"])

    def test_variables_only_rule_is_not_touched(self):
        self.assertEqual(darkcss.generate(".x { color: var(--ink); background: var(--soft); }"), "")

    def test_local_color_variables_follow_shared_tokens(self):
        self.assertEqual(rules(".cal { --up: #087a55; --down: #c43a2c; --gap: 4px; }")[GEN + " .cal"], {"--up": "#3fd29b", "--down": "#ff8e80"})

    def test_generated_rules_keep_light_specificity(self):
        # :where() 로 감싸 원래 규칙과 구체성이 같다 — 더 구체적인 밝은 규칙(색은 변수)을 덮지 않는다
        out = darkcss.generate(".st i { background: #dfe4eb; }")
        self.assertTrue(out.startswith(':where(:root[data-theme="dark"]) .st i'), out)

    def test_handmade_dark_rule_wins_per_property(self):
        css = '.a, .b { background: #fff; color: #0d253d; } :root[data-theme="dark"] .a { background: #123456; }'
        r = rules(css)
        self.assertNotIn("background", r[GEN + " .a"])           # 손으로 정한 속성은 생성하지 않는다
        self.assertEqual(r[GEN + " .a"]["color"], "#e8eef6")      # 나머지 속성은 생성한다
        self.assertEqual(r[GEN + " .b"]["background"], "#111b2b")

    def test_media_and_keyframes(self):
        r = rules("@media (hover: hover) { .x:hover { background: #f6f9fc; } } @keyframes k { from { color: #000; } to { color: #fff; } }")
        self.assertIn("@" + GEN + " .x:hover", r)
        self.assertEqual(len(r), 1)

    def test_inverted_pill_gets_dark_text(self):
        r = rules(".tab[aria-selected='true'] { background: var(--ink); color: #fff; } .tab[aria-selected='true'] .c { color: rgb(255 255 255 / .6); }")
        self.assertEqual(r[GEN + " .tab[aria-selected='true']"]["color"], "#0b1320")
        self.assertTrue(r[GEN + " .tab[aria-selected='true'] .c"]["color"].startswith("rgb(11 19 32 /"))

    def test_shadow_vs_hairline(self):
        r = rules(".a { box-shadow: 0 0 0 1px rgb(18 29 54 / .06), 0 10px 26px -18px rgb(18 29 54 / .35); }")
        lines = r[GEN + " .a"]["box-shadow"]
        self.assertIn("rgb(232 238 246", lines)   # 1px 선 → 밝은 반투명 선
        self.assertIn("rgb(0 0 0", lines)         # 큰 그림자 → 검정

    def test_badge_text_reaches_contrast_on_its_own_background(self):
        for css in (".atag { background: #fff6dc; color: #8a6100; }", ".imp.high { background: #fff1e6; color: #a2410b; }",
                    ".tag.u { background: #e6f6ee; color: #087a55; }"):
            d = next(iter(rules(css).values()))
            fg, bg = darkcss.parse(d["color"]), darkcss.parse(d["background"])
            self.assertGreaterEqual(darkcss.contrast(fg[:3], bg[:3]), 4.5, (css, d))

    def test_accent_text_reaches_contrast_on_dark_surface(self):
        for c in ("#533afd", "#b45309", "#1d4ed8", "#0e9f6e", "#c43a2c", "#5f6c83"):
            got = darkcss.parse(rules(".x { color: %s; }" % c)[GEN + " .x"]["color"])
            for surf in (darkcss.BG, darkcss.SURF, darkcss.SURF2):
                self.assertGreaterEqual(darkcss.contrast(got[:3], surf), 4.5, (c, got))

    def test_inject_appends_once_and_is_valid_braces(self):
        css = ".a { background: #fff; }"
        out = darkcss.inject(css)
        self.assertTrue(out.startswith(css))
        self.assertEqual(out.count("{"), out.count("}"))
        self.assertEqual(darkcss.inject(".a { color: var(--ink); }"), ".a { color: var(--ink); }")

    def test_real_sources_generate_balanced_css(self):
        from pathlib import Path
        web = Path(__file__).resolve().parents[2] / "web"
        for f in [web / "assets/df/lk.css", web / "assets/df/st.css"] + sorted(web.glob("df_*.html")):
            text = f.read_text(encoding="utf-8")
            for css in (re.findall(r"<style[^>]*>(.*?)</style>", text, re.S) if f.suffix == ".html" else [text]):
                gen = darkcss.generate(css)
                self.assertEqual(gen.count("{"), gen.count("}"), f.name)
                self.assertNotIn("var(--", "".join(re.findall(r"--[\w-]+: ([^;]+)", gen)), f.name)


if __name__ == "__main__":
    unittest.main()
