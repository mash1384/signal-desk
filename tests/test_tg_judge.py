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
        r = J.normalize(out(coins=["$btc", "NVDA", "BTC", "a", "AI", "eth"]))
        self.assertEqual(r["coins"], ["BTC", "ETH"])

    def test_market_wide_needs_strength(self):
        self.assertFalse(J.normalize(out(market_wide=True, strength=1))["market_wide"])
        self.assertTrue(J.normalize(out(market_wide=True, strength=2))["market_wide"])

    def test_clean_text_strips_links_and_tags(self):
        self.assertEqual(J.clean_text("BTC ETF 승인 https://x.com/a\n\n#속보 #BTC"), "BTC ETF 승인")


if __name__ == "__main__":
    unittest.main()


class FillEn(unittest.TestCase):
    """영어 채우기: 묶음 개수가 어긋나면 한 건씩 다시, 그래도 안 되는 글은 다시 묻지 않는다."""

    def setUp(self):
        import sqlite3, time
        self.con = sqlite3.connect(":memory:")
        self.con.execute("CREATE TABLE msgs (ch TEXT, id INTEGER, t INTEGER, text TEXT)")
        self.con.execute("CREATE TABLE ai (ch TEXT, id INTEGER, ko TEXT, en TEXT)")
        now = int(time.time())
        for i in range(3):
            self.con.execute("INSERT INTO msgs VALUES ('c', ?, ?, 'x')", (i, now - i))
            self.con.execute("INSERT INTO ai VALUES ('c', ?, '한국어', NULL)", (i,))
        J.EN_SKIP.clear()
        self.real = J._fill_en_rows

    def tearDown(self):
        J._fill_en_rows = self.real
        J.EN_SKIP.clear()

    def test_falls_back_to_one_by_one_and_skips_failures(self):
        calls = []

        def fake(con, rows):
            calls.append([r[1] for r in rows])
            if len(rows) > 1 or rows[0][1] == 1:   # 묶음은 늘 실패, 1번 글은 한 건씩 해도 실패
                return False
            con.execute("UPDATE ai SET en='EN' WHERE id=?", (rows[0][1],))
            return True
        J._fill_en_rows = fake
        self.assertTrue(J.fill_en(self.con, k=8))
        self.assertEqual(calls, [[0, 1, 2], [0], [1], [2]])
        self.assertEqual(J.EN_SKIP, {("c", 1)})
        calls.clear()
        self.assertFalse(J.fill_en(self.con, k=8))   # 남은 건 실패한 1번뿐 → 다시 묻지 않는다
        self.assertEqual(calls, [])
