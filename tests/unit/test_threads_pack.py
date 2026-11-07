"""브리핑 첫 자료 줄이기(11-07): pipeline/public_data.py pack_threads 가 만든 threads-pack.json 을
브라우저 brk.js unpack() 이 threads-core.json 과 같은 모양(줄기의 names 만 빠짐)으로 되돌리는지 — 파이썬이 정답 파일을 만들고 node(tests/js/brk_unpack.test.mjs)가 푼다."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.public_data import split_threads

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures/threads_pack_case.json"


def sample():
    stories = {}
    for i in range(60):
        s = {"t": 1_793_900_000 + i * 600, "v": ["호재", "악재", "중립"][i % 3], "s": i % 3, "n": 1 + i % 4,
             "coins": ["BTC"] if i % 2 else [], "kind": ["event", "data", "opinion", "price_recap"][i % 4],
             "ko": "소식 %d" % i, "en": "story %d" % i}
        if i % 5:
            s["th"] = ["crypto"] if i % 2 else ["econ", "ai"]   # 없는 소식도 있다
        stories["id%02d" % i] = s
    threads = [{"id": "t1", "ids": list(stories)[:30], "n": 30, "names": ["hassett"], "th": ["econ"], "ai": {"ko": {"title": "제목"}}},
               {"id": "t2", "ids": list(stories)[30:], "n": 30, "names": [], "th": ["crypto"], "ai": None}]
    return {"v": 1, "made": 1_793_940_000, "threads": threads, "stories": stories}


class ThreadsPack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "threads.json").write_text(json.dumps(sample(), ensure_ascii=False))
        split_threads(self.tmp)
        self.core = json.loads((self.tmp / "threads-core.json").read_text())
        self.pack = json.loads((self.tmp / "threads-pack.json").read_text())

    def test_pack_is_smaller_and_has_no_names_or_titles(self):
        self.assertLess((self.tmp / "threads-pack.json").stat().st_size, (self.tmp / "threads-core.json").stat().st_size * 0.8)
        self.assertTrue(all("names" not in t for t in self.pack["threads"]))
        self.assertNotIn("ko", self.pack["stories"]["cols"])

    def test_fixture_matches_current_pack(self):
        """node 쪽 시험(tests/js/brk_unpack.test.mjs)이 쓰는 정답 파일이 지금 pack_threads 결과와 같다 — 다르면 다시 만든다:
        python -m tests.unit.test_threads_pack --write"""
        self.assertEqual(json.loads(FIX.read_text()), {"core": self.core, "pack": self.pack})


if __name__ == "__main__":
    if "--write" in sys.argv:
        t = ThreadsPack("test_fixture_matches_current_pack"); t.setUp()
        FIX.write_text(json.dumps({"core": t.core, "pack": t.pack}, ensure_ascii=False, indent=1) + "\n"); t.doCleanups()
    else:
        unittest.main()
