"""story_threads(이야기 줄기) 문장 검사 단위 테스트. 실행: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import story_threads as T  # noqa: E402

TX = {1: "Nasdaq fell 2.14% as chip stocks slid", 2: "A container ship sank after being hit by projectiles near the Strait of Hormuz",
      3: "EU officials say sanctions against Russia will be maintained", 4: "트럼프 미국 대통령이 TSMC 회장과 통화했다"}


class Sentences(unittest.TestCase):
    def test_refs_inside_text_are_split(self):
        self.assertEqual(T.split_refs("공격했어요 [1, 5].", []), ("공격했어요.", [1, 5]))
        self.assertEqual(T.split_refs("보였어요. refs: [1, 2]", []), ("보였어요.", [1, 2]))

    def test_cause_only_with_market_words(self):
        self.assertIsNone(T.why_bad("A container ship sank after being hit by projectiles.", [2], TX, "en"))
        self.assertIsNotNone(T.why_bad("The Nasdaq fell 2.14% as chip stocks slid.", [1], TX, "en"))
        self.assertIsNotNone(T.why_bad("반도체주 하락으로 나스닥이 하락했어요.", [1], TX, "ko"))

    def test_reported_future_is_allowed_but_own_forecast_is_not(self):
        self.assertIsNone(T.why_bad("EU officials said sanctions against Russia will be maintained.", [3], TX, "en"))
        self.assertIsNotNone(T.why_bad("Sanctions will be maintained.", [3], TX, "en"))

    def test_figures_and_titles_must_come_from_sources(self):
        self.assertIsNotNone(T.why_bad("The Nasdaq fell 2%.", [1], TX, "en"))
        self.assertIsNotNone(T.why_bad("트럼프 전 대통령이 TSMC 회장과 통화했어요.", [4], TX, "ko"))
        self.assertIsNone(T.why_bad("트럼프 대통령이 TSMC 회장과 통화했어요.", [4], TX, "ko"))


if __name__ == "__main__":
    unittest.main()
