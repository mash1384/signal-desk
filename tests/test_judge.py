import unittest

from pipeline import impact, judge


def art(**kw):
    a = {"id": "x1", "title": "Upbit lists Sui", "title_orig": "Upbit lists Sui", "source": "coindesk", "category": "crypto",
         "assets": ["SUI"], "etype": "listing", "t0": 0, "impact": {"SUI": {"1h": {"r": 1}}}, "impact_status": "done"}
    a.update(kw)
    return a


class Judge(unittest.TestCase):
    def test_normalize_keeps_only_coins_found_in_text(self):
        j = judge.normalize({"kind": "event", "coins": ["SUI", "ETH"], "type": "listing", "direction": "bullish", "strength": 2}, ["SUI"])
        self.assertEqual(j["coins"], ["SUI"])
        self.assertEqual((j["type"], j["dir"], j["str"]), ("listing", "bullish", 2))

    def test_normalize_rejects_bad_output(self):
        self.assertIsNone(judge.normalize({"kind": "maybe"}, []))
        j = judge.normalize({"kind": "opinion", "coins": ["BTC"], "strength": 3, "direction": "bullish"}, ["BTC"])
        self.assertEqual((j["coins"], j["str"], j["dir"], j["type"]), ([], 0, "neutral", ""))

    def test_market_wide_needs_us_context(self):
        j = {"kind": "event", "coins": [], "market_wide": True, "type": "regulation", "direction": "bearish", "strength": 2}
        self.assertFalse(judge.normalize(j, [], "EU weighs wallet checks")["mw"])
        self.assertTrue(judge.normalize(j, [], "CFTC's new crypto market plan faces scrutiny")["mw"])
        self.assertTrue(judge.normalize(j, [], "美 9월 CPI 발표")["mw"])

    def test_non_event_is_not_measured(self):
        a = art(ai={"kind": "price_recap", "coins": [], "mw": False, "type": "", "dir": "neutral", "str": 0})
        self.assertEqual(impact.subjects(a), [])

    def test_market_wide_event_measures_btc(self):
        a = art(assets=[], ai={"kind": "event", "coins": [], "mw": True, "type": "macro", "dir": "bearish", "str": 2})
        self.assertEqual(impact.subjects(a), [("BTC", False)])

    def test_apply_resets_when_target_changes(self):
        a = art()
        hits = []
        n = judge.apply([a], {"x1": {"kind": "promo", "coins": []}}, hits.append)
        self.assertEqual(n, 1)
        self.assertEqual(hits, [a])
        self.assertEqual(a["ai"]["kind"], "promo")
        # 같은 판정이 다시 와도 다시 재지 않는다
        self.assertEqual(judge.apply([a], {"x1": {"kind": "promo", "coins": []}}, hits.append), 0)

    def test_apply_keeps_measurement_when_target_same(self):
        a = art()
        hits = []
        judge.apply([a], {"x1": {"kind": "event", "coins": ["SUI"], "type": "listing", "direction": "bullish", "strength": 2}}, hits.append)
        self.assertEqual(hits, [])
        self.assertEqual(judge.label(a["ai"]), "사건 · 상장 · 호재 · 강도 2")

    def test_upbit_notice_ignores_ai(self):
        a = art(source="upbit-notice")
        judge.apply([a], {"x1": {"kind": "promo"}}, lambda _: None)
        self.assertNotIn("ai", a)

    def test_missing_file_means_rules(self):
        self.assertEqual(judge.load("/nonexistent/j.json"), {})


if __name__ == "__main__":
    unittest.main()
