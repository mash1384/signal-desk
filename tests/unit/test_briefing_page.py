"""브리핑 탭 맨 위(빌드 때 그린다): 영 · 한 짝, 영어가 없는 칸은 영어 화면에서 숨김, 묵은 자료, 근거 단추, 이스케이프."""
import unittest

from pipeline import build

NOW = 1_800_000_000


def doc(**kw):
    ko = {"headline": "물가와 유가가 판을 쥔다", "regime": {"label": "동결 위의 긴장", "s": "물가가 올랐다.", "refs": ["s1"]},
          "big": [{"t": "제목 %d" % i, "s": "본문 %d" % i, "refs": ["s1", "zz"]} for i in range(3)],
          "desks": {"crypto": {"s": "크립토 한 줄", "refs": []}, "world": {"s": "세계 한 줄", "refs": []}},
          "risks": [{"s": "변수 <b>하나</b>", "refs": ["s1"]}], "watch": [{"when": "10/29 03:00", "s": "FOMC", "refs": []}]}
    en = {"headline": "Prices and oil hold the board", "regime": {"label": "Tension on a hold", "s": "Prices rose.", "refs": ["s1"]},
          "big": [{"t": "Title %d" % i, "s": None, "refs": ["s1"]} for i in range(3)],
          "desks": {"crypto": {"s": "Crypto line", "refs": []}, "world": {"s": None, "refs": []}},
          "risks": [{"s": "One risk", "refs": ["s1"]}], "watch": [{"when": "Oct 29 03:00", "s": "FOMC", "refs": []}]}
    d = {"v": 1, "made": NOW - 3600, "next": NOW + 3600, "ko": ko, "en": en,
         "stories": {"s1": {"id": "s1", "t": NOW - 7200, "ko": "소식 </script><script>alert(1)</script>", "v": "호재", "s": 2}}}
    d.update(kw)
    return d


class BriefingPage(unittest.TestCase):
    def test_renders_both_languages_and_hides_missing_english(self):
        html = build.briefing_html(doc(), NOW)
        self.assertIn('id="bf"', html)
        self.assertIn('<h1 id="bf-h"><span data-l="en" lang="en">Prices and oil hold the board</span><span data-l="ko" lang="ko">물가와 유가가 판을 쥔다</span></h1>', html)
        self.assertEqual(html.count('class="bf-c"'), 3)
        # 영어가 없는 칸(인사이트 본문 · 세계 한 줄)은 한국어 칸만 — 영어 화면에서 숨는다(lk.css [data-l])
        self.assertIn('<p data-l="ko" lang="ko">본문 0</p>', html)
        self.assertNotIn('<p data-l="en" lang="en">None', html)
        self.assertIn('<p data-l="ko" lang="ko">세계 한 줄</p>', html)
        self.assertIn('href="%sthemes/crypto/"' % build.B, html)

    def test_source_buttons_only_for_known_stories(self):
        html = build.briefing_html(doc(), NOW)
        self.assertIn('data-bf="s1"', html)
        self.assertNotIn('data-bf="zz"', html)          # 상세 자료가 없는 근거는 단추를 만들지 않는다

    def test_escapes_text_and_embedded_json(self):
        html = build.briefing_html(doc(), NOW)
        self.assertIn("변수 &lt;b&gt;하나&lt;/b&gt;", html)
        self.assertNotIn("</script><script>alert(1)", html)   # 소식 자료가 스크립트 태그를 닫지 못한다
        self.assertIn("<\\/script>", html)

    def test_stale_and_missing(self):
        self.assertEqual(build.briefing_html(None, NOW), "")
        self.assertEqual(build.briefing_html({"v": 1}, NOW), "")
        self.assertEqual(build.briefing_html(doc(made=NOW - 49 * 3600), NOW), "")      # 이틀 넘게 묵으면 싣지 않는다
        self.assertIn("an earlier briefing", build.briefing_html(doc(made=NOW - 20 * 3600), NOW))
        self.assertNotIn("an earlier briefing", build.briefing_html(doc(), NOW))

    def test_empty_sections_are_left_out(self):
        d = doc()
        d["ko"]["desks"], d["ko"]["risks"], d["ko"]["watch"] = {}, [], []
        html = build.briefing_html(d, NOW)
        self.assertNotIn("bf-desks", html)
        self.assertNotIn("bf-box", html)


if __name__ == "__main__":
    unittest.main()


class BriefingStub(unittest.TestCase):
    def test_stub_when_mac_has_none_and_real_file_wins(self):
        import json
        import os
        import tempfile
        from pipeline import public_data
        d = tempfile.mkdtemp()
        public_data.copy_daily(os.path.join(d, "none"), os.path.join(d, "a"))
        self.assertEqual(json.load(open(os.path.join(d, "a/data/daily/briefing.json"))), {"v": 0})
        os.makedirs(os.path.join(d, "f/daily"))
        with open(os.path.join(d, "f/daily/briefing.json"), "w") as f:
            f.write('{"v": 1}')
        self.assertEqual(public_data.copy_daily(os.path.join(d, "f"), os.path.join(d, "b")), ["briefing.json"])
        self.assertEqual(json.load(open(os.path.join(d, "b/data/daily/briefing.json"))), {"v": 1})
