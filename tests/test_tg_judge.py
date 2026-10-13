import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import tg_judge as J


def out(**kw):
    j = {"ko": "바이낸스, BLUR 상장", "kind": "event", "verdict": "호재", "coins": ["BLUR"], "sectors": [], "market_wide": False, "strength": 1}
    j.update(kw)
    return j


class TgJudge(unittest.TestCase):
    def test_rejects_bad_output(self):
        self.assertIsNone(J.normalize({"kind": "maybe", "ko": "x"}))
        self.assertIsNone(J.normalize(out(ko="  ")))

    def test_quiet_kinds_are_neutral_without_sectors(self):
        r = J.normalize(out(kind="promo", verdict="호재", sectors=["meme"], strength=2, market_wide=True))
        self.assertEqual((r["verdict"], r["sectors"], r["strength"], r["market_wide"]), ("중립", [], 0, False))

    def test_sectors_only_on_news_with_a_verdict(self):
        self.assertEqual(J.normalize(out(sectors=["ai", "ai", "nope", "defi", "meme"]))["sectors"], ["ai", "defi"])
        self.assertEqual(J.normalize(out(kind="price_recap", sectors=["meme"]))["sectors"], [])
        self.assertEqual(J.normalize(out(verdict="중립", sectors=["ai"]))["sectors"], [])

    def test_coins_cleaned(self):
        r = J.normalize(out(coins=["$btc", "NVDA", "BTC", "a", "eth"]))
        self.assertEqual(r["coins"], ["BTC", "ETH"])

    def test_market_wide_needs_strength(self):
        self.assertFalse(J.normalize(out(market_wide=True, strength=1))["market_wide"])
        self.assertTrue(J.normalize(out(market_wide=True, strength=2))["market_wide"])

    def test_clean_text_strips_links_and_tags(self):
        self.assertEqual(J.clean_text("BTC ETF 승인 https://x.com/a\n\n#속보 #BTC"), "BTC ETF 승인")


if __name__ == "__main__":
    unittest.main()
