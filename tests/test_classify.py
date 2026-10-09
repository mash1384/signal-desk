"""분류·파싱·임팩트 계산 단위 테스트. 실행: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import classify, collect, impact, util  # noqa: E402

MK = {"id": "mk-economy", "hint": "macro", "require": True}
CRYPTO = {"id": "coindesk", "hint": "crypto", "require": False}
AI = {"id": "aitimes", "hint": "ai", "require": False}


class Classify(unittest.TestCase):
    def test_word_boundary(self):
        self.assertFalse(classify.has_any("he said it", ["ai"]))
        self.assertTrue(classify.has_any("new ai model", ["ai"]))

    def test_general_feed_needs_title_keyword(self):
        self.assertIsNone(classify.classify("한성숙 대통령 제청 거부", "경제 금리 환율 이야기", MK))
        self.assertEqual(classify.classify("美 국채 10년물 금리 최고…환율 급등", "", MK), "macro")

    def test_general_feed_title_strong(self):
        # 제목 핵심어 하나만으로 남긴다
        self.assertEqual(classify.classify("트럼프 관세로 美 가격 올라…뉴욕 연은", "", MK), "macro")
        self.assertEqual(classify.classify("XRP 다시 중앙화 논란", "", MK), "crypto")
        self.assertEqual(classify.classify("삼성·TSMC, 올 3분기도 파운드리 '희비교차'", "", MK), "ai")
        # 금액·일반어만 있는 기사는 여전히 버린다
        self.assertIsNone(classify.classify("현대로템 20억달러 수주 승부수", "", MK))
        self.assertIsNone(classify.classify("하나은행, 장기연체채권 1343억 소각", "", MK))

    def test_source_only_filter(self):
        fed = {"id": "fed", "hint": "macro", "require": True, "only": ["fomc", "monetary policy", "minutes"]}
        self.assertIsNone(classify.classify("Federal Reserve Board announces approval of application by Isabella Bank", "", fed))
        self.assertEqual(classify.classify("Federal Reserve issues FOMC statement", "", fed), "macro")

    def test_block_prefix(self):
        self.assertIsNone(classify.classify("[인사] 한국은행", "금리 환율", MK))

    def test_stock_listing_not_high(self):
        self.assertEqual(classify.event_type("코스닥 상장예심 통과", "", "macro"), "other")
        self.assertEqual(classify.event_type("업비트, NMR 디지털 자산 추가", "", "crypto"), "listing")

    def test_assets(self):
        self.assertEqual(classify.extract_assets("Bitcoin and Ether rally as SOL lags", ""), ["BTC", "ETH", "SOL"])
        self.assertEqual(classify.extract_assets("The solution is said to work", ""), [])

    def test_crypto_hint(self):
        self.assertEqual(classify.classify("Bitcoin ETF inflows rise", "", CRYPTO), "crypto")
        self.assertEqual(classify.classify("오픈AI 새 모델 공개", "", AI), "ai")


class Parse(unittest.TestCase):
    def test_rss(self):
        body = b"""<?xml version="1.0"?><rss><channel><item><title>A &amp; B</title><link>https://x.com/a?utm_source=z</link>
        <description><![CDATA[<p>Hello <b>world</b></p>]]></description><pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
        items = collect.parse_feed(body)
        self.assertEqual(items[0]["title"], "A & B")
        self.assertEqual(collect.clean_text(items[0]["summary"]), "Hello world")
        self.assertEqual(collect.normalize_url(items[0]["url"]), "https://x.com/a")
        self.assertEqual(util.parse_time(items[0]["published"]), 1791374400)

    def test_atom(self):
        body = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title><link rel="alternate" href="https://y.com/1"/>
        <updated>2026-10-07T12:00:00Z</updated><summary>S</summary></entry></feed>"""
        it = collect.parse_feed(body)[0]
        self.assertEqual((it["title"], it["url"]), ("T", "https://y.com/1"))

    def test_naive_korean_time_is_kst(self):
        self.assertEqual(util.parse_time("2026-10-07 21:00:00"), 1791374400)

    def test_duplicate_title(self):
        ex = [{"url_key": "https://a/1", "t0": 1000, "title": "비트코인 현물 ETF 순유입 7거래일 연속 기록"}]
        self.assertTrue(collect.is_duplicate("비트코인 현물 ETF 순유입 7거래일 연속 기록", "https://b/2", 2000, ex))
        self.assertFalse(collect.is_duplicate("이더리움 스테이킹 수익률 하락", "https://b/3", 2000, ex))


class Impact(unittest.TestCase):
    def test_grade(self):
        self.assertEqual(impact.grade(-3.2), "강")
        self.assertEqual(impact.grade(2.0), "중")
        self.assertEqual(impact.grade(0.4), "약")

    def test_measure_with_fake_candles(self):
        t0 = 1_791_000_000 - (1_791_000_000 % 60) + 30
        rows = [(t0 - 30 + i * 60 - 60, 100.0 + i, 100.0 + i + 0.5) for i in range(0, 1600)]
        orig = impact.market.candles
        impact.market.candles = lambda sym, interval, s, e: rows if interval == 60 else [(0, 1.0, 1.0 + 0.001 * ((k % 7) - 3)) for k in range(200)]
        try:
            a = {"id": "x", "t0": t0, "category": "macro", "source": "s", "assets": [], "impact": {}}
            impact.measure([a], {}, t0 + 90000)
        finally:
            impact.market.candles = orig
        v = a["impact"]["BTC"]["15m"]
        # 시가: t0가 속한 분의 open, 종가: t0+15분 직전 분의 close
        start = (t0 // 60) * 60
        i0 = (start - (t0 - 30 - 60)) // 60
        i1 = (((t0 + 900) // 60) * 60 - 60 - (t0 - 30 - 60)) // 60
        expect = ((100.0 + i1 + 0.5) / (100.0 + i0) - 1) * 100
        self.assertAlmostEqual(v["r"], round(expect, 3))
        self.assertEqual(a["impact_status"], "done")


if __name__ == "__main__":
    unittest.main()
