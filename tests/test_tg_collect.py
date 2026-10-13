import datetime
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
try:
    from telethon.tl.types import Message, PeerChannel, MessageEntityUrl, MessageEntityTextUrl
    import tg_collect
except ImportError:          # Actions에는 telethon이 없다(Mac 전용 도구)
    tg_collect = None


def msg(i, text, ents=None, edit=None):
    d = datetime.datetime(2026, 10, 13, 9, 0, tzinfo=datetime.timezone.utc)
    return Message(id=i, peer_id=PeerChannel(7), date=d, message=text, entities=ents, edit_date=edit)


@unittest.skipIf(tg_collect is None, "telethon 없음")
class TgCollect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tg_collect.DB = os.path.join(self.tmp.name, "tg", "tg.db")
        self.con = tg_collect.db()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_links_survive_emoji_offsets(self):
        text = "🚨🚨 BTC ETF https://x.com/a 더보기"
        u = text.index("https")
        # 텔레그램 오프셋은 UTF-16 단위: 이모지 하나가 2칸
        ents = [MessageEntityUrl(offset=u + 2, length=len("https://x.com/a")),
                MessageEntityTextUrl(offset=len(text) + 2 - 3, length=3, url="https://coindesk.com/x")]
        r = tg_collect.row("coinnesskr", msg(1, text, ents), "push", now=1)
        self.assertEqual(r["links"], '["https://x.com/a", "https://coindesk.com/x"]')
        self.assertEqual(r["t"], 1791882000)

    def test_save_new_then_edit_keeps_first_got(self):
        self.assertTrue(tg_collect.save(self.con, tg_collect.row("a", msg(1, "v1"), "push", now=100)))
        self.assertFalse(tg_collect.save(self.con, tg_collect.row("a", msg(1, "v1"), "poll", now=130)))
        e = datetime.datetime(2026, 10, 13, 9, 5, tzinfo=datetime.timezone.utc)
        self.assertFalse(tg_collect.save(self.con, tg_collect.row("a", msg(1, "v2", edit=e), "push", now=400)))
        text, got, via = self.con.execute("SELECT text, got, via FROM msgs").fetchone()
        self.assertEqual((text, got, via), ("v2", 100, "push"))
        self.assertEqual(tg_collect.last_ids(self.con), {"a": 1})

    def test_channels_unique(self):
        self.assertEqual(len(set(tg_collect.NAMES)), 12)


if __name__ == "__main__":
    unittest.main()
