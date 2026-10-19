"""Meaningful unit checks for the measurement's aggregation rules (no browser)."""
import unittest
from types import SimpleNamespace

from tests.e2e.network import Offline
from tests.perf.vitals import aggregate, cls_value, network_metrics, Reply


class Metrics(unittest.TestCase):
    def test_detail_fixture_uses_real_utc_opens_and_no_future_candles(self):
        offline = Offline.__new__(Offline)
        offline.host, offline.now, offline.manifest, offline.unmapped = 'fixture', 1259, {}, []

        def candles(limit, start=1001000):
            reply = Reply(SimpleNamespace(method='GET', url='https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=%d&startTime=%d' % (limit, start)))
            offline.handle(reply)
            return reply.payload['json']

        old = candles(1000)
        self.assertEqual([row[0] for row in old], [1020000, 1080000, 1140000, 1200000])
        self.assertEqual(old, candles(4))
        self.assertEqual(candles(1000, 1020001)[0][0], 1080000)

    def test_cls_uses_largest_session_not_lifetime_total(self):
        shifts = [{'at': t, 'value': v} for t, v in [(0, .04), (500, .06), (1400, .1), (2400, .9), (2500, .01)]]
        self.assertAlmostEqual(cls_value(shifts), .91)

    def test_cls_session_cannot_exceed_five_seconds(self):
        self.assertAlmostEqual(cls_value([{'at': t, 'value': .1} for t in range(0, 6301, 700)]), .8)
        self.assertEqual(cls_value([]), 0)

    def test_network_counts_exclude_embedded_data_and_keep_failed_http(self):
        rows = [{'url': 'https://fixture/' + str(i), 'type': kind, 'bytes': size}
                for i, (kind, size) in enumerate([('Document', 100), ('Script', 30), ('Font', 40), ('Fetch', 0)])]
        rows.append({'url': 'data:image/svg+xml,inline', 'type': 'Image', 'bytes': 999})
        self.assertEqual(network_metrics(rows), {'requests': 4, 'bytes': 170, 'font_files': 1, 'font_bytes': 40, 'js_bytes': 30})

    def test_medians_are_per_page_and_device(self):
        rows = []
        for device, values in [('pc', [900, 100, 120]), ('mobile', [1500, 1600, 1700])]:
            for value in values:
                rows.append(dict(page='live/', device=device, lcp_ms=value, cls=0, requests=2,
                                 bytes=100, font_files=1, font_bytes=20, js_bytes=10))
        medians = aggregate(rows)
        self.assertEqual([(r['device'], r['lcp_ms'], r['runs']) for r in medians], [('pc', 120, 3), ('mobile', 1600, 3)])
