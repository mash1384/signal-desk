"""상장 레이더·이벤트 리스크·맵·패턴 데이터 단위 테스트. 실행: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import events, listings, mapdata, moves, patterns, signals, util  # noqa: E402


class Listings(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(listings.notice_kind("카이아(KAIA) 신규 거래지원 안내 (KRW, BTC, USDT 마켓)"), "listing")
        self.assertEqual(listings.notice_kind("원화마켓 신규 상장 (샌드박스 SAND)"), "listing")
        self.assertEqual(listings.notice_kind("BTC, ETH 마켓 코인 추가 (블룸 BLT)"), "listing")
        self.assertEqual(listings.notice_kind("블라스트(BLAST) 거래 유의 종목 지정 안내"), "caution")
        self.assertEqual(listings.notice_kind("웨이브 유의 촉구 안내"), "other")
        self.assertEqual(listings.notice_kind("테더 USDT, KRW 마켓 추가 안내"), "other")

    def test_symbols(self):
        self.assertEqual(listings.symbols("KRW, BTC 마켓 디지털 자산 추가 (ALGO, AUDIO)"), ["ALGO", "AUDIO"])
        self.assertEqual(listings.symbols("BTC 마켓 디지털 자산 추가 (바이프로스트 BFC, 리니어 파이낸스 LINA)"), ["BFC", "LINA"])
        self.assertEqual(listings.symbols("오원익스체인지(O) 신규 거래지원 안내 (KRW, BTC, USDT 마켓)"), ["O"])
        self.assertEqual(listings.symbols("네오, 오미세고, 리스크 원화 마켓 오픈"), [])
        self.assertTrue(listings.is_krw("원화마켓 신규 상장 (디카르고 DKA)"))
        self.assertFalse(listings.is_krw("BTC 마켓 디지털 자산 추가 (썬 SUN)"))

    def test_trade_time(self):
        notice = util.kst_to_ts(2026, 10, 9, 17, 6)
        t = listings.trade_time_from_body("<p>거래지원 개시 시점</p> 공지 게시 시점으로부터 1시간 이내 10월 9일 18시 30분 예정", notice)
        self.assertEqual(util.iso(t), "2026-10-09T09:30:00Z")
        dec = util.kst_to_ts(2025, 12, 31, 20, 0)
        self.assertEqual(util.iso(listings.trade_time_from_body("거래지원 개시 시점 1월 1일 10시 예정", dec)), "2026-01-01T01:00:00Z")
        self.assertIsNone(listings.trade_time_from_body("입금 지원은 30분 내 개시합니다", notice))

    def test_curve_and_metrics(self):
        mins = {1000 * 60 + i * 60: (100.0, 100.0 + i) for i in range(0, 1500)}
        pts = listings._curve(mins, 1000 * 60, 100.0, [0, 1, 60, 1440])
        self.assertEqual(pts, [[0, 0.0], [1, 1.0], [60, 60.0], [1440, 1440.0]])
        m = listings.metrics({"trade": {"pts": [[0, 0.0], [60, 50.0], [120, 80.0], [1440, 20.0]]}})
        self.assertEqual((m["peak24"], m["peak_min"], m["r60"], m["r1440"]), (80.0, 120, 50.0, 20.0))
        self.assertAlmostEqual(m["dd_from_peak"], -33.333, places=2)


class Events(unittest.TestCase):
    def test_kind_of(self):
        self.assertEqual(events.kind_of("Core CPI m/m"), "cpi")
        self.assertEqual(events.kind_of("FOMC Meeting Minutes"), "minutes")
        self.assertIsNone(events.kind_of("President Trump Speaks"))

    def test_stats(self):
        rows = [(i, {"15m": 0.1 * i, "1h": (-1) ** i * 0.2 * i}) for i in range(1, 11)]
        st = events.stats_for(rows)
        self.assertEqual(st["n"], 10)
        self.assertAlmostEqual(st["abs1h"]["med"], 1.1, places=3)
        self.assertEqual(st["abs1h"]["max"], 2.0)
        self.assertEqual(st["up"], 0.5)
        self.assertEqual(len(st["recent"]), 10)

    def test_merge_dedups_same_release(self):
        hist = {"kinds": {"cpi": [1000]}, "moves": {"1000": {"15m": 0.1, "1h": 0.5}}}
        acc = {"cpi": {"1300": {"15m": 0.2, "1h": 0.9}, "90000": {"15m": 0.3, "1h": -0.4}}}
        rows = events._merged("cpi", hist, acc)
        self.assertEqual([t for t, _ in rows], [1000, 90000])


class MapLayout(unittest.TestCase):
    def test_layout_deterministic_and_centered(self):
        syms = ["BTC", "ETH", "SOL", "XRP"]
        c = {("BTC", "ETH"): 0.9, ("BTC", "SOL"): 0.7, ("BTC", "XRP"): 0.6, ("ETH", "SOL"): 0.8, ("ETH", "XRP"): 0.5, ("SOL", "XRP"): 0.55}
        cm = {}
        for (a, b), v in c.items():
            cm[(a, b)] = cm[(b, a)] = v
        p1 = mapdata.layout(syms, cm, {})
        p2 = mapdata.layout(syms, cm, {})
        self.assertEqual(p1, p2)
        self.assertEqual(p1["BTC"], [0.0, 0.0])
        r = {s: (p1[s][0] ** 2 + p1[s][1] ** 2) ** 0.5 for s in syms[1:]}
        self.assertLess(r["ETH"], r["XRP"])  # BTC와 더 같이 움직이면 더 가깝다

    def test_corr(self):
        a = {i: 0.01 * (i % 5) for i in range(100)}
        self.assertAlmostEqual(mapdata.corr(a, a), 1.0, places=6)
        self.assertIsNone(mapdata.corr(a, {}))


class Patterns(unittest.TestCase):
    def _art(self, i, etype, r1):
        return {"id": "a%d" % i, "t0": 1000 + i, "title": "t%d" % i, "category": "crypto", "etype": etype,
                "headline": {"asset": "BTC"}, "impact": {"BTC": {"1h": {"r": r1, "z": r1 * 2, "g": "약"}}}}

    def test_similar_needs_samples(self):
        arts = [self._art(i, "hack", 0.5 if i % 2 else -0.5) for i in range(7)]
        patterns.attach_similar(arts, 2000)
        self.assertEqual(arts[0]["pattern"]["n"], 6)
        self.assertEqual(arts[0]["pattern"]["up"], 0.5)
        few = [self._art(i, "etf", 0.1) for i in range(3)]
        patterns.attach_similar(few, 2000)
        self.assertEqual(few[0]["pattern"], {"label": "ETF", "sym": "BTC", "adj": False, "n": 2})


class Moves(unittest.TestCase):
    def test_ols_recovers_beta(self):
        x = [((i * 7919) % 101 - 50) / 1000 for i in range(400)]
        y = [1.5 * v + (((i * 104729) % 31) - 15) / 100000 for i, v in enumerate(x)]
        beta, sd, r2 = moves._ols(y, x)
        self.assertAlmostEqual(beta, 1.5, places=2)
        self.assertGreater(r2, 0.99)

    def test_detect_finds_one_jump(self):
        cum = [0.0] * 400
        for i in range(200, 400):
            cum[i] = min(3.0, (i - 200) * 0.1)        # 200분부터 30분 동안 +3%
        ev = moves._detect(cum, 0.5, 2.5)
        self.assertEqual(len(ev), 1)
        a, e = ev[0]
        self.assertTrue(200 <= a <= 207 and e >= 229)

    def test_mentions_word_boundary(self):
        self.assertTrue(moves._mentions("SOL ETF approved", ["SOL"]))
        self.assertFalse(moves._mentions("SOLUTION for banks", ["SOL"]))
        self.assertTrue(moves._mentions("솔라나 급등", ["SOL", "솔라나"]))

    def test_recap_titles_are_not_causes(self):
        self.assertTrue(moves._recap("All about NEAR's latest rebound and the odds of a new price reversal"))
        self.assertFalse(moves._recap("Polkadot Launches USDT-Backed dotUSD Under OpenGov"))
        self.assertFalse(moves._recap("XRP jumps after SEC approval of spot ETF"))


class Signals(unittest.TestCase):
    def test_vol_ratio_against_week(self):
        now = 1_791_000_000 - (1_791_000_000 % 3600)
        hours = [(now - (200 - i) * 3600, 100.0, 1e8) for i in range(200)]      # 평소 시간당 1억
        hours[-1] = (hours[-1][0], 100.0, 5e8)                                   # 마지막 끝난 시간 5억
        r, krw = signals.vol_ratio(hours, now, 1)
        self.assertEqual((r, krw), (5.0, 500000000))
        hours.append((now, 100.0, 9e9))                                          # 진행 중인 시간봉은 세지 않는다
        self.assertEqual(signals.vol_ratio(hours, now + 600, 1)[0], 5.0)


if __name__ == "__main__":
    unittest.main()
