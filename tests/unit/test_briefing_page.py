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


class PlainLanguageParts(unittest.TestCase):
    """쉬운 말 단계(tools/easy.py)가 더한 칸: 한눈에 3줄 · 내 생활에서는(고정 문장) · 영향을 받는 곳. 없으면 그리지 않는다."""

    def d(self):
        d = doc()
        d["ko"]["three"] = [{"s": "한 줄 %d" % i} for i in range(3)]
        d["en"]["three"] = [{"s": "Line %d" % i} for i in range(3)]
        d["ko"]["big"][0].update(who=[{"s": "반도체 주식"}], life="chips")
        d["en"]["big"][0]["who"] = [{"s": "Chip stocks"}]
        d["ko"]["big"][1]["life"] = "fx_up"                  # 영어 일반 문장이 없는 열쇠
        d["ko"]["big"][2]["life"] = "no_such_key"
        return d

    def test_three_lines_life_and_chips(self):
        html = build.briefing_html(self.d(), NOW)
        self.assertEqual(html.count('<div class="bf-3">'), 1)
        self.assertIn('<span data-l="ko" lang="ko">한 줄 2</span>', html)
        self.assertEqual(html.count('class="bf-life"'), 2)                       # 모르는 열쇠는 상자 없음
        self.assertIn(build.LIFE["chips"]["en"][0], html)
        self.assertIn('<div class="bf-life" data-l="ko">', html)                 # 영어 문장이 없으면 영어 화면에서 상자째 숨는다
        self.assertIn('<b data-l="en" lang="en">Chip stocks</b><b data-l="ko" lang="ko">반도체 주식</b>', html)

    def test_absent_parts_are_not_drawn(self):
        html = build.briefing_html(doc(), NOW)
        for cls in ("bf-3", "bf-life", "bf-who"):
            self.assertNotIn(cls, html)
        d = self.d(); d["ko"]["three"] = d["ko"]["three"][:2]
        self.assertNotIn('class="bf-3"', build.briefing_html(d, NOW))              # 3줄이 다 있어야

    def test_life_sentence_rotates_by_round_and_is_escaped(self):
        d = self.d()
        a = build.briefing_html(dict(d, made=NOW - 3600), NOW)
        b = build.briefing_html(dict(d, made=NOW - 7200), NOW)
        ks = build.LIFE["chips"]["ko"]
        self.assertTrue(any(x in a for x in ks) and any(x in b for x in ks))
        self.assertNotEqual([x for x in ks if x in a], [x for x in ks if x in b])  # 회차마다 다른 문장

    def test_missing_english_hides_whole_box_in_english(self):
        d = self.d(); d["en"]["three"][1] = {"s": None}; d["en"]["big"][0]["who"] = []
        html = build.briefing_html(d, NOW)
        self.assertIn('<div class="bf-3" data-l="ko">', html)                    # 빈 번호 줄이 영어 화면에 남지 않게
        self.assertIn('<p class="bf-who" data-l="ko">', html)
