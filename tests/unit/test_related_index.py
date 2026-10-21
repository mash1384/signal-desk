"""관련 기사의 선택·순서 보존과 전체 입력 재순회 방지."""
import copy
import random
import unittest

from pipeline import build


def article(key, time, kind="other", assets=(), category="crypto"):
    return {"id": key, "t0": time, "etype": kind, "assets": list(assets), "category": category}


class CountedArticles(list):
    reads = 0

    def __iter__(self):
        for item in super().__iter__():
            self.reads += 1
            yield item

    def __getitem__(self, index):
        self.reads += 1
        return super().__getitem__(index)


class RelatedIndex(unittest.TestCase):
    def test_primary_precedes_category_and_overlapping_matches_appear_once(self):
        target = article("target", 20, "event", ["BTC", "ETH"])
        rows = [article("category", 19), article("asset", 18, assets=["ETH"]),
                article("both", 17, "event", ["BTC", "ETH"]), article("type", 16, "event")]
        index = build.RelatedIndex(rows)
        self.assertEqual([a["id"] for a in build.related(target, rows, index=index)],
                         ["asset", "both", "type", "category"])

    def test_equal_time_and_unsorted_input_keep_original_order(self):
        target = article("target", 20, "event")
        rows = [article("old", 10, "event"), article("future", 21, "event"),
                target, article("tie", 20, "event"), article("recent", 19, "event")]
        index = build.RelatedIndex(rows)
        self.assertEqual([a["id"] for a in build.related(target, rows, index=index)], ["old", "tie", "recent"])
        descending = sorted(rows, key=lambda a: -a["t0"])
        index = build.RelatedIndex(descending)
        self.assertEqual([a["id"] for a in build.related(target, descending, index=index)], ["tie", "recent", "old"])

    def test_duplicate_ids_preserve_legacy_primary_and_fallback_rules(self):
        target = article("target", 20, "event")
        rows = [article("target", 19, "event"), article("dup", 18, "event"),
                article("dup", 17, "event"), article("dup", 16), article("fallback", 15), article("fallback", 14)]
        index = build.RelatedIndex(rows)
        self.assertEqual([a["id"] for a in build.related(target, rows, index=index)],
                         ["dup", "dup", "fallback", "fallback"])

    def test_missing_type_matches_missing_type_but_other_does_not(self):
        missing = article("missing", 20)
        del missing["etype"]
        rows = [article("other", 19), {**article("none", 18, category="world"), "etype": None},
                article("asset", 17, assets=["BTC"], category="world")]
        index = build.RelatedIndex(rows)
        self.assertEqual([a["id"] for a in build.related(missing, rows, index=index)], ["none", "other"])
        self.assertEqual([a["id"] for a in build.related(article("target", 20), rows, index=index)], ["other"])

    def test_matches_reference_for_mixed_inputs_and_limits_without_mutation(self):
        rng = random.Random(7021)
        rows = [article(str(i // 2), rng.randrange(12), rng.choice([None, "other", "event", "report"]),
                        rng.sample(["BTC", "ETH", "NVDA"], rng.randrange(4)), rng.choice(["crypto", "world", "ai"]))
                for i in range(120)]
        for ordered in (rows, sorted(rows, key=lambda a: -a["t0"])):
            before = copy.deepcopy(ordered)
            index = build.RelatedIndex(ordered)
            for target in ordered + [article("external", 0), article("external", 20)]:
                for limit in (-1, 0, 1, 5, 9):
                    with self.subTest(target=target["id"], limit=limit):
                        self.assertEqual(build.related(target, ordered, limit, index=index), build.related(target, ordered, limit))
            self.assertEqual(ordered, before)

    def test_sparse_old_queries_do_not_rescan_the_corpus(self):
        rows = CountedArticles(article(str(i), 6000 - i, category="crypto" if i % 3 else "world") for i in range(6000))
        index = build.RelatedIndex(rows)
        target = rows[5000]
        rows.reads = 0
        result = build.related(target, rows, index=index)
        self.assertEqual([a["id"] for a in result], ["5002", "5003", "5005", "5006", "5008"])
        self.assertLessEqual(rows.reads, 6)

    def test_separate_builds_do_not_reuse_old_candidates(self):
        target = article("target", 20)
        first, second = [article("first", 19)], [article("second", 18)]
        self.assertEqual(build.related(target, first, index=build.RelatedIndex(first)), first)
        self.assertEqual(build.related(target, second, index=build.RelatedIndex(second)), second)


if __name__ == "__main__":
    unittest.main()
