"""소식 그림(점묘화): 그림 고르기 규칙(pipeline/art.py) · 브라우저 쪽(web/assets/df/artm.js)과 같은 답 · 그림 파일 · 브리핑 카드 그림."""
import json
import os
import re
import struct
import unittest

from pipeline import art, build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(ROOT, "web", "assets", "art")
IX = art.load()

# (한국어 제목, 영어 제목, 코인, 기대하는 사전 항목 — None 은 지구)
CASES = [
    ("FBI, 북한이 63억 달러 규모의 바이낸스 크립토 해킹을 저질렀다고 확인했다", "", [], "해킹(주제)"),   # 주제 먼저: 북한 · 바이낸스보다
    ("이더리움 현물 ETF 23일 연속 유출", "", [], "이더리움"),                                         # '유출'은 해킹이 아니다(펀드 자금)
    ("자금 유출 지속", "", [], None),                                                                 # 자금 ≠ 금
    ("금리 인상 확률 70%", "", [], None),                                                             # 금리 ≠ 금
    ("금값 사상 최고치", "", [], "금"),
    ("금 현물 가격이 온스당 4,144달러로 1% 상승했다", "", [], "금"),
    ("인도네시아 수출 급증", "", [], None),                                                           # 인도네시아 ≠ 인도
    ("엔지니어 채용 늘어", "", [], None),                                                             # 엔지니어 ≠ 니어
    ("CME 페드워치 기준 12월 인상 확률 70.7%", "", [], "연준"),                                       # CME 페드워치 = 연준 금리 예상
    ("CME 비트코인 선물 미결제약정 사상 최대", "", [], "CME"),
    ("중국 AI 기업 딥시크 신모델 공개", "", [], "딥시크"),                                            # 이름(회사)이 나라보다 먼저
    ("트럼프, 중국에 추가 관세", "", [], "트럼프"),
    ("영국 9월 물가 3.8%", "", [], "영국"),                                                           # 나라가 넓은 주제(물가)보다 먼저
    ("美 국채 30년물 금리 5.3%", "", [], "재무부 · 국채"),
    ("", "Bitcoin whale moves $1B to Coinbase", [], "비트코인"),                                      # 영어 제목, 이름이 넓은 주제(고래)보다 먼저
    ("", "Trump says he won the deal", [], "트럼프"),                                                 # 'won'(이겼다)은 원화가 아니다
    ("어떤 작은 프로젝트가 토큰을 발행했다", "", ["SOL"], "솔라나"),                                   # 제목에 없으면 코인
    ("어떤 작은 프로젝트가 토큰을 발행했다", "", [], None),
    ("OpenAI, 새 모델 공개", "", [], "OpenAI"),
    ("AI가 일자리를 바꾼다", "", [], "AI"),
    ("Liquid AI가 1.7B 모델 출시", "", [], "AI"),
    ("MAIL 서버 점검 공지", "", [], None),                                                            # 영문은 앞뒤가 영문 · 숫자가 아니어야(MAIL 안의 AI)
]


FIXTURE = os.path.join(ROOT, "tests", "fixtures", "art_cases.json")


def rows():
    """예시 + 사전의 모든 항목 이름(첫 한국어 이름)."""
    r = [[ko, en, coins, "id%d" % i] for i, (ko, en, coins, _) in enumerate(CASES)]
    return r + [[e[1][0] + " 관련 소식", "", [], "x%d" % i] for i, e in enumerate(IX["e"]) if e[1]]


def answers():
    return [[ko, en, coins, sid, art.matched(IX, ko, en, coins), art.pick(IX, ko, en, coins, sid)] for ko, en, coins, sid in rows()]


class Rules(unittest.TestCase):
    def test_index_loaded(self):
        self.assertTrue(IX and IX["e"] and IX["fb"], "web/assets/df/art.json 이 없거나 비었다")

    def test_cases(self):
        for ko, en, coins, want in CASES:
            with self.subTest(ko=ko or en):
                self.assertEqual(art.matched(IX, ko, en, coins), want)

    def test_fixture_matches(self):
        """브라우저 쪽(artm.js)은 tests/js/art.test.mjs 가 같은 정답 파일로 확인한다 — 두 쪽이 같은 답.
        사전을 바꾸면 python -m tests.unit.test_art --write 로 정답 파일을 다시 만든다."""
        with open(FIXTURE, encoding="utf-8") as f:
            self.assertEqual(json.load(f), answers(), "정답 파일이 지금 사전과 다르다(--write 로 다시 만들기)")

    def test_rotation_is_stable_and_spreads(self):
        ids = IX["fb"]
        self.assertEqual(art.pick(IX, "아무 말", sid="a1"), art.pick(IX, "아무 말", sid="a1"))
        self.assertEqual({art.pick(IX, "아무 말", sid="s%d" % i) for i in range(60)}, set(ids))

    def test_avoid_takes_another_picture(self):
        e = next(e for e in IX["e"] if len(e[4]) >= 2)
        first = art.pick(IX, e[1][0] + " 소식", sid="q")
        self.assertNotEqual(art.pick(IX, e[1][0] + " 소식", sid="q", avoid=[first]), first)


class Files(unittest.TestCase):
    def test_every_picture_exists_and_parses(self):
        ids = {i for e in IX["e"] for i in e[4]} | set(IX["fb"])
        on_disk = {f[:-4] for f in os.listdir(ART) if f.endswith(".bin")}
        self.assertEqual(ids - on_disk, set(), "사전에 있는데 파일이 없다")
        self.assertEqual(on_disk - ids, set(), "쓰지 않는 그림 파일")
        for i in sorted(ids):
            b = open(os.path.join(ART, i + ".bin"), "rb").read()
            self.assertEqual(b[:2], b"DA", i)
            w, h, flags, focus, n = struct.unpack("<BBBBH", b[2:8])
            self.assertTrue(8 <= w <= 128 and 8 <= h <= 128 and focus <= 100, i)
            cr = json.loads(b[8:8 + n].decode("utf-8"))
            self.assertEqual(len(b), 8 + n + (w * h + 1) // 2, i)
            if flags & 2:
                self.assertEqual(cr, [], "로고는 출처 줄이 없다: %s" % i)
            else:
                self.assertTrue(cr and all(t and u.startswith("https://") for t, u in cr), "사진은 출처가 있어야 한다: %s" % i)
                for _t, u in cr:
                    if "unsplash.com" in u:
                        self.assertIn("utm_source=delfona", u, "Unsplash 출처 링크에는 utm 이 붙어야 한다")


class Briefing(unittest.TestCase):
    def doc(self):
        NOW = 1_800_000_000
        st = {"a": {"ko": "CME 페드워치 기준 연준 12월 인상 확률 70%", "en": "", "coins": []},
              "b": {"ko": "이더리움 현물 ETF 23일 연속 유출", "en": "", "coins": ["ETH"]},
              "c": {"ko": "호르무즈 해협 상선 공격 늘어", "en": "", "coins": []}}
        big = [{"t": "금리는 멈췄는데 걱정은 남아요", "s": "본문", "refs": ["a"]}, {"t": "크립토에서 돈이 빠져나가요", "s": "본문", "refs": ["b"]},
               {"t": "해협이 조여와요", "s": "본문", "refs": ["c"]}]
        return {"v": 1, "made": NOW - 3600, "next": NOW + 3600, "stories": st,
                "ko": {"headline": "금리는 멈췄고 크립토는 빠져요", "regime": {"label": "l", "s": "s"}, "big": big}, "en": {}}, NOW

    def test_cards_get_distinct_pictures_and_head_avoids_card_subjects(self):
        d, now = self.doc()
        html = build.briefing_html(d, now)
        cards = re.findall(r'<article class="bf-c" data-art="([0-9a-f]+)"', html)
        head = re.findall(r'id="bf" data-art-h="([0-9a-f]+)"', html)
        self.assertEqual(len(cards), 3)
        self.assertEqual(len(set(cards)), 3, "세 카드는 서로 다른 그림")
        rev = {i: e[0] for e in IX["e"] for i in e[4]}
        self.assertEqual([rev.get(i) for i in cards], ["연준", "이더리움", "호르무즈"])
        self.assertEqual(len(head), 1)
        self.assertNotIn(rev.get(head[0]), {"연준", "케빈 워시", "이더리움", "호르무즈"}, "머리 그림은 카드와 같은 대상이 아니다")

    def test_no_index_means_no_attributes(self):
        d, now = self.doc()
        saved = art.INDEX
        try:
            art.INDEX = os.path.join(ROOT, "no-such-art.json")
            html = build.briefing_html(d, now)
        finally:
            art.INDEX = saved
        self.assertNotIn("data-art", html)


if __name__ == "__main__":
    import sys
    if "--write" in sys.argv:
        with open(FIXTURE, "w", encoding="utf-8") as f:
            json.dump(answers(), f, ensure_ascii=False, indent=0)
        print("wrote", FIXTURE)
    else:
        unittest.main()
