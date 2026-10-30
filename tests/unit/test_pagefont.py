"""페이지 글꼴(pipeline/pagefont.py, 10-30 장애): 페이지 · 자료 · 스크립트(불러오는 모듈까지)의 글자가 한 파일에 다 들어간다."""
import json
import os
import tempfile
import unittest

from pipeline import pagefont


def tree(files):
    d = tempfile.mkdtemp(prefix="pagefont-")
    for rel, body in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    return d


class PageFont(unittest.TestCase):
    def test_unicode_range_merges_runs(self):
        self.assertEqual(pagefont.unicode_range([0x20, 0x21, 0x22, 0xAC00, 0xD30E, 0xD30F]), "U+20-22,U+AC00,U+D30E-D30F")

    def test_scripts_follow_versioned_module_imports_once(self):
        out = tree({
            "assets/df/c3.js": "import { a } from './ek.js?v=1';import './lk.js?v=1';",
            "assets/df/ek.js": "import { b } from './lk.js?v=1';const m = import('./acct.js?v=1');",
            "assets/df/lk.js": "import { c } from './ek.js?v=1';",   # 서로 부름(무한 반복 없음)
            "assets/df/acct.js": "",
        })
        page = '<script type="module">import \'/b/assets/df/c3.js?v=1\';</script>'
        got = sorted(os.path.basename(p) for p in pagefont.scripts(out, page))
        self.assertEqual(got, ["acct.js", "c3.js", "ek.js", "lk.js"])

    def test_calendar_font_covers_page_data_and_imported_module_text(self):
        from fontTools.ttLib import TTFont
        out = tree({
            "assets/df/c3.js": "import { h } from './ek.js?v=9';",
            "assets/df/ek.js": "const HELP = '누르고 끌기 · 화살표 키';",      # 모듈 안에서만 나오는 글자
            "daily/econ.json": json.dumps({"요약": ["물가는 3% 안팎"]}, ensure_ascii=False),
        })
        page = '<html><head></head><body><h1>경제 일정</h1><script type="module">import \'/b/assets/df/c3.js?v=9\';</script></body></html>'
        html, info = pagefont.calendar(out, page, "/b/", os.path.join(out, "daily", "econ.json"))
        with TTFont(os.path.join(out, info["file"])) as font:
            cmap = set(font.getBestCmap())
            family = font["name"].getDebugName(1)
        for ch in "경제일정누르고끌기화살표키물가는안팎요약0123456789AZaz%":
            self.assertIn(ord(ch), cmap, ch)
        self.assertNotIn(ord("뷁"), cmap)
        self.assertEqual(family, pagefont.FAMILY)
        self.assertIn('<link rel="preload" as="font" type="font/woff2" crossorigin href="/b/%s">' % info["file"], html)
        self.assertIn(":root,:lang(ko){--sans:\"DF Page Text\"", html)
        self.assertLess(html.index("DF Page Text"), html.index("</head>"))
        # unicode-range 는 실제 파일의 글자와 같다(파일에 없는 글자를 맡지 않는다)
        self.assertIn("unicode-range:%s}" % pagefont.unicode_range(sorted(cmap)), html)

    def test_same_text_same_file_and_bytes(self):
        a, b = tree({}), tree({})
        _, ia = pagefont.build(a, "calendar", "같은 글자", "/")
        _, ib = pagefont.build(b, "calendar", "같은 글자", "/")
        self.assertEqual(ia["file"], ib["file"])
        with open(os.path.join(a, ia["file"]), "rb") as fa, open(os.path.join(b, ib["file"]), "rb") as fb:
            self.assertEqual(fa.read(), fb.read())


if __name__ == "__main__":
    unittest.main()
