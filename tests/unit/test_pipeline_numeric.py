"""사이트 빌드(pipeline) 쪽 경계값: AI 판정 정규화(judge) · 가격 반응 측정(impact). 공개 저장소에서도 돈다."""
import json
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import config, impact as I, judge as J


class JudgeBoundaries(unittest.TestCase):
    def test_normalization(self):
        self.assertIsNone(J.normalize([], []))
        for strength, want in ((-1, 0), (0, 0), (1, 1), (3, 3), (4, 3), ("bad", 0), ({}, 0)):
            r = J.normalize({"kind": "event", "strength": strength, "model": "a" * 41, "coins": ["A", "B", "C", "D", "X"], "market_wide": True}, ["A", "B", "C", "D"], "US CPI")
            self.assertEqual(r["str"], want)
            self.assertEqual(r["coins"], ["A", "B", "C"])
            self.assertFalse(r["mw"])
            self.assertEqual(r["type"], "other")
            self.assertEqual(r["dir"], "neutral")
            self.assertEqual(len(r["m"]), 40)
        for kind in ("price_recap", "opinion", "promo", "unrelated"):
            r = J.normalize({"kind": kind, "market_wide": True, "direction": "bullish", "type": "listing", "strength": 2, "coins": ["BTC"]}, ["BTC"], "US CPI")
            self.assertEqual((r["coins"], r["mw"], r["type"], r["dir"], r["str"]), ([], False, "", "neutral", 0))
        self.assertEqual(J.label(None), "")
        self.assertEqual(J.label({"kind": "event", "dir": "neutral", "str": 0}), "사건 · 기타")
        self.assertEqual(J.label({"kind": "promo"}), "홍보")

    def test_load_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "j.json"
            for doc, expected in (([], {}), ({"v": 1, "j": {}}, {}), ({"v": J.VERSION, "j": []}, {}), ({"v": J.VERSION, "j": {"a": 1}}, {"a": 1})):
                p.write_text(json.dumps(doc))
                self.assertEqual(J.load(str(p)), expected)


class ImpactBoundaries(unittest.TestCase):
    def test_grade_at_each_boundary(self):
        for sign in (-1, 1):
            for z, expected in ((0, "약"), (config.GRADE_MEDIUM - .00001, "약"), (config.GRADE_MEDIUM, "중"), (config.GRADE_STRONG - .00001, "중"), (config.GRADE_STRONG, "강")):
                self.assertEqual(I.grade(sign * z), expected)

    def test_sd_sample_size_and_variance(self):
        self.assertIsNone(I._sd(list(range(19))))
        self.assertAlmostEqual(I._sd(list(range(20))), statistics.stdev(range(20)))
        self.assertIsNone(I._sd([1] * 20))

    def test_pending_two_minute_boundary_and_existing(self):
        a = {"t0": 100, "source": "calendar"}
        win, sec = config.WINDOWS[0]
        self.assertEqual(I._pending(a, 100 + sec + 119), [])
        self.assertIn(("BTC", win, sec), I._pending(a, 100 + sec + 120))
        a["impact"] = {"BTC": {win: {"r": 0}}}
        self.assertNotIn(("BTC", win, sec), I._pending(a, 100 + sec + 120))

    def test_spans_boundary(self):
        self.assertEqual(I._spans([(0, 2), (12, 15), (26, 30)], gap=10), [[0, 15], [26, 30]])

    def test_volatility_cache_expiry(self):
        cache = {"BTC": {"at": 10, "sd": {"1h": 9}}}
        with patch.object(I.market, "candles", return_value=[]) as get:
            self.assertEqual(I.volatility("BTC", cache, 10 + I.STATS_TTL - 1), {"1h": 9})
            get.assert_not_called()
            self.assertEqual(I.volatility("BTC", cache, 10 + I.STATS_TTL), {})
            self.assertEqual(get.call_count, 3)

    def test_concurrency_thresholds(self):
        rows = [{"id": str(t), "t0": t, "importance": 2, "source": "calendar"} for t in (0, config.CONCURRENT_EVENT_SECONDS, 1800, 1801)]
        I.concurrency(rows)
        self.assertEqual(rows[0]["concurrent"], 1)
        self.assertEqual(rows[0]["crowd"], 2)

    def test_type_stats_minimum_and_age(self):
        rows = [{"id": str(i), "title": "x", "t0": 0, "etype": "cpi", "impact": {"BTC": {"1h": {"r": i, "g": "강", "z": i}}}} for i in (1, 2, 3)]
        self.assertEqual(I.type_stats(rows[:2]), [])
        self.assertEqual(I.type_stats(rows)[0]["mean"], 2)
        self.assertEqual(I.type_stats(rows)[0]["strong_share"], 1)
        self.assertEqual(len(I.strongest(rows, 7 * 86400)), 3)
        self.assertEqual(I.strongest(rows, 7 * 86400 + 1), [])
        self.assertEqual(I.strongest(rows, 0, limit=1)[0]["id"], "3")
