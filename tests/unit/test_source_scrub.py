"""남의 기사 글에 '텔레그램 출처 · 링크' 모양이 있으면 배포 전에 거른다(pipeline/collect.scrub_sources).
11-09: RSS 기사 한 건의 발췌문이 공개 검사(tests/policy/scan.py)에 걸려 배포 8회 연속 실패, 사이트 2시간 멈춤."""
import copy
import unittest

from pipeline import collect
from tests.policy import scan


def art(i, **kw):
    a = {"id": "20261109-%04d" % i, "url": "https://example.com/%d" % i, "title": "업비트 서버 점검 완료", "title_orig": "업비트 서버 점검 완료",
         "excerpt": "업비트가 9일 서버 점검을 마쳤다.", "summary": ["업비트가 점검을 마쳤다."], "source_name": "tokenpost"}
    a.update(kw)
    return a


class Scrub(unittest.TestCase):
    def test_same_pattern_as_public_policy(self):
        # 들어오는 쪽 거름과 공개 검사가 따로 놀면 다시 배포가 막힌다
        self.assertEqual(collect.TG_SOURCE.pattern, scan.SOURCE.pattern)
        self.assertEqual(collect.TG_SOURCE.flags, scan.SOURCE.flags)

    def test_excerpt_and_summary_lines_are_removed_article_kept(self):
        xs = [art(1, excerpt="공지는 공식 텔레그램 채널에 올라왔다. 점검은 끝났다.", summary=["점검이 끝났다.", "자세한 내용은 t.me/upbit 에서"]), art(2)]
        out, fixed, dropped = collect.scrub_sources(copy.deepcopy(xs))
        self.assertEqual((len(out), fixed, dropped), (2, 2, 0))
        self.assertEqual(out[0]["excerpt"], "")
        self.assertEqual(out[0]["summary"], ["점검이 끝났다."])
        self.assertEqual(out[1], xs[1])   # 깨끗한 기사는 그대로
        for a in out:                     # 공개 검사의 글자 검사를 통과
            self.assertFalse([v for _, v in scan.strings(a) if scan.SOURCE.search(scan.normalize(v))])

    def test_title_or_url_match_drops_article(self):
        xs = [art(3, title="출처: 텔레그램 — 거래소 공지"), art(4, url="https://t.me/s/somechannel/1"), art(5, excerpt="Source%3A%20Telegram 공지")]
        out, fixed, dropped = collect.scrub_sources(xs)
        self.assertEqual([a["id"] for a in out], ["20261109-0005"])
        self.assertEqual(out[0]["excerpt"], "")   # 주소 인코딩된 것도 공개 검사와 같게 풀어 봄
        self.assertEqual(dropped, 2)

    def test_mentions_of_telegram_the_company_stay(self):
        # 텔레그램 회사 소식은 출처 표기가 아니라 그대로 둔다(공개 검사도 통과)
        a = art(6, title="Telegram sees 700,000 new crypto wallets in 48 hours", excerpt="Telegram has recorded more than 700,000 new wallets.")
        out, fixed, dropped = collect.scrub_sources([copy.deepcopy(a)])
        self.assertEqual((out, fixed, dropped), ([a], 0, 0))


if __name__ == "__main__":
    unittest.main()
