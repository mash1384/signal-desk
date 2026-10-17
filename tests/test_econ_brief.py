"""econ_brief(경제지표) 계산 · 문장 검사 단위 테스트. 실행: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
try:
    import econ_brief as E
except ImportError as e:  # zoneinfo 없는 오래된 파이썬
    E = None
    REASON = str(e)


@unittest.skipIf(E is None, "econ_brief 를 불러오지 못함")
class Transform(unittest.TestCase):
    def test_yoy_mom_diff(self):
        s = [("2025-01-01", 100.0), ("2025-02-01", 101.0), ("2026-01-01", 103.0), ("2026-02-01", 104.04)]
        yoy = dict(E.transform(s, "yoy"))
        self.assertAlmostEqual(yoy["2026-01-01"], 3.0)
        self.assertAlmostEqual(yoy["2026-02-01"], 3.0099, places=3)
        self.assertAlmostEqual(dict(E.transform(s, "mom"))["2026-02-01"], (104.04 / 103 - 1) * 100, places=6)
        self.assertAlmostEqual(dict(E.transform(s, "diff"))["2026-02-01"], 1.04, places=6)

    def test_forecast_compare_uses_forecast_decimals(self):
        cpi = E.BY["cpi"]
        self.assertEqual(E.vs_fc(cpi, 3.72, "3.6%", 1), "above")
        self.assertEqual(E.vs_fc(cpi, 3.64, "3.6%", 1), "inline")
        claims = E.BY["claims"]
        self.assertEqual(E.ff_value(claims, "199K"), 199.0)
        self.assertEqual(E.vs_fc(claims, 199.0, "199K", 0), "inline")

    def test_hot_direction(self):
        # 실업률·청구는 낮을수록 고용이 강하다
        x = {"sit": {"dir": "down", "rank10y": 0.1, "trend": "flat"}}
        dk, de, lk, le = E.meaning(E.BY["claims"], x)
        self.assertEqual(dk, "고용이 강해짐")
        self.assertEqual(lk, "고용이 강한 편")


@unittest.skipIf(E is None, "econ_brief 를 불러오지 못함")
class Sentences(unittest.TestCase):
    def test_numbers_must_come_from_source(self):
        src = '{"이번": "3.7%", "기간": "2026-09"}'
        self.assertTrue(E.ok_text("2026년 9월 물가는 3.7%였어요.", src))
        self.assertFalse(E.ok_text("물가는 3.8%였어요.", src))
        self.assertFalse(E.ok_text("물가가 더 오를 것으로 보여요.", src))
        self.assertFalse(E.ok_text("Inflation was 3.7% (물가).", src, "en"))

    def test_lead_line_josa_and_compare(self):
        x = {"latest": {"v": 199.0, "prev": 198.0, "fc": "199K", "sub": None}, "sit": {}}
        s = E.lead_line(E.BY["claims"], x, "ko")
        self.assertIn("199,000건이었어요", s)
        self.assertIn("예상 199,000건과 같아요", s)
        y = {"latest": {"v": 6.35, "prev": 5.58, "fc": None, "sub": 1.34, "fc_sub": "0.6%"}, "sit": {}}
        s = E.lead_line(E.BY["ppi"], y, "ko")
        self.assertNotIn("예상 0.6%보다 높고", s.split(".")[0])
        self.assertIn("전월 대비로는 1.3%로 예상 0.6%보다 높아요", s)


if __name__ == "__main__":
    unittest.main()
