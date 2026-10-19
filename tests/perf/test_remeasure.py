"""성능 측정 도구: 빈 측정만 기록을 남기고 다시 재며, 끝까지 비면 실패한다."""
import asyncio
import unittest

from tests.perf.vitals import EmptyMeasurement, with_remeasure


def sampler(results):
    it = iter(results)

    async def sample():
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    return sample


class Remeasure(unittest.TestCase):
    def test_empty_once_then_ok_is_recorded(self):
        log = []
        row = asyncio.run(with_remeasure(sampler([EmptyMeasurement("empty"), {"lcp_ms": 80}]), log, {"page": "live/"}))
        self.assertEqual(row, {"lcp_ms": 80})
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["page"], "live/")

    def test_always_empty_fails(self):
        log = []
        with self.assertRaises(EmptyMeasurement):
            asyncio.run(with_remeasure(sampler([EmptyMeasurement("e")] * 3), log, {}))
        self.assertEqual(len(log), 3)

    def test_other_failures_are_not_retried(self):
        log = []
        with self.assertRaises(ValueError):
            asyncio.run(with_remeasure(sampler([ValueError("empty page content"), {"lcp_ms": 1}]), log, {}))
        self.assertEqual(log, [])
