import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import tg_publish as P


def m(ko, t=0, ch="a", i=1, coins=(), v="중립", s=1, kind="event", sectors=(), links=()):
    return {"ch": ch, "id": i, "t": t, "ko": ko, "coins": list(coins), "verdict": v, "strength": s, "kind": kind,
            "sectors": list(sectors), "market_wide": False, "links": list(links)}


class TgPublish(unittest.TestCase):
    def test_different_percent_is_different_story(self):
        self.assertFalse(P.same_story(0.95, m("독일 CPI 전년 대비 3.3%"), m("독일 CPI 전월 대비 0.6%")))
        self.assertTrue(P.same_story(0.95, m("독일 CPI 3.3% 부합"), m("독일·EU CPI 3.3%")))

    def test_gray_zone_needs_shared_number_or_coin(self):
        self.assertFalse(P.same_story(0.82, m("젤렌스키, 동맹국 경고 없었다"), m("젤렌스키, 이틀간 공격 안 했다")))
        self.assertTrue(P.same_story(0.82, m("미 정부 17,733 BTC 이동"), m("미 정부 BTC 17,733개 전송")))
        self.assertTrue(P.same_story(0.82, m("바이낸스 RWUSD 상장", coins=["RWUSD"]), m("RWUSD 수수료 0", coins=["RWUSD"])))
        self.assertFalse(P.same_story(0.79, m("A 17,733"), m("B 17,733")))

    def test_cluster_respects_time_gap(self):
        rows = [m("x", t=0, i=1), m("x", t=3600, ch="b", i=2), m("x", t=3600 + P.GAP + 1, ch="c", i=3)]
        sim = [[1.0] * 3] * 3
        self.assertEqual(P.cluster(rows, sim), [[0, 1], [2]])

    def test_merge_first_line_weighted_verdict_and_sources(self):
        g = [m("코인니스 줄", t=10, ch="coinnesskr", i=5, coins=["BTC"], v="호재", s=1, links=["https://t.me/x"]),
             m("월러 줄", t=20, ch="marketfeed", i=9, coins=["BTC", "ETH"], v="악재", s=2, links=["https://coindesk.com/a"]),
             m("또", t=30, ch="coinnesskr", i=6, coins=["BTC"], v="호재", s=0)]
        it = P.merge(g)
        self.assertEqual((it["id"], it["t"], it["ko"], it["n"]), ("coinnesskr-5", 10, "코인니스 줄", 3))
        self.assertEqual(it["v"], "중립")            # 호재 (1+1)+(0+1)=3, 악재 2+1=3 → 동점은 중립
        self.assertEqual(P.merge(g[:2])["v"], "악재")  # 호재 2 대 악재 3
        self.assertEqual(it["coins"], ["BTC", "ETH"])
        self.assertEqual(it["src"], [["coinnesskr", 5, 10], ["marketfeed", 9, 20]])
        self.assertEqual(it["link"], "https://coindesk.com/a")

    def test_visible(self):
        self.assertFalse(P.visible({"kind": "data", "v": "중립", "s": 0, "coins": []}))
        self.assertTrue(P.visible({"kind": "data", "v": "악재", "s": 0, "coins": []}))
        self.assertFalse(P.visible({"kind": "promo", "v": "호재", "s": 2, "coins": ["X"]}))
        self.assertFalse(P.visible({"kind": "data", "v": "중립", "s": 1, "coins": []}))      # JP모건 실적 같은 먼 소식
        self.assertTrue(P.visible({"kind": "event", "v": "중립", "s": 1, "coins": ["BTC"]}))


if __name__ == "__main__":
    unittest.main()
