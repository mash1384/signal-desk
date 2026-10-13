import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
try:
    import daily_brief as D
except ImportError:          # tools/tg_publish가 numpy 등 Mac 쪽 환경을 기대할 때
    D = None


@unittest.skipIf(D is None, "tools 환경 없음")
class DailyBrief(unittest.TestCase):
    def test_window_is_kst_9_to_9(self):
        s, e = D.window(dt.date(2026, 10, 13))
        self.assertEqual(dt.datetime.fromtimestamp(s, D.KST).strftime("%m-%d %H"), "10-13 09")
        self.assertEqual(e - s, 86400)

    def test_due_picks_last_finished_day(self):
        at = dt.datetime(2026, 10, 14, 9, 7, tzinfo=D.KST).timestamp()
        self.assertEqual(D.due(at)[-1], dt.date(2026, 10, 13))
        at = dt.datetime(2026, 10, 14, 8, 0, tzinfo=D.KST).timestamp()
        self.assertEqual(D.due(at)[-1], dt.date(2026, 10, 12))

    def test_check_rejects_made_up_numbers_causal_and_advice(self):
        src = "BTC +2.00% · 호재 45건"
        ok = {"headline": "호재 45건의 하루", "review": "BTC는 2.00% 올랐다."}
        self.assertEqual(D.check(ok, src), [])
        self.assertEqual(D.check({"headline": "BTC 3% 급등", "review": "x"}, src), ["headline"])
        self.assertIn("review", D.check({"headline": "h", "review": "ETF 소식 때문에 비트코인이 올랐다."}, src))
        self.assertIn("review", D.check({"headline": "h", "review": "지금 매수하세요."}, src))
        self.assertIn("review", D.check({"headline": "h", "review": ""}, src))

    def test_category(self):
        self.assertEqual(D.category({"ko": "엔비디아 실적 예상 상회", "coins": [], "sectors": [], "kind": "data"}), "ai")
        self.assertEqual(D.category({"ko": "독일 CPI 3.3%", "coins": [], "sectors": [], "kind": "data"}), "econ")
        self.assertEqual(D.category({"ko": "흑해 드론 공격", "coins": [], "sectors": [], "kind": "event"}), "world")
        self.assertEqual(D.category({"ko": "고래가 매수", "coins": ["UNI"], "sectors": [], "kind": "event"}), "crypto")


if __name__ == "__main__":
    unittest.main()
