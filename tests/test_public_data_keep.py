"""공개 자료 보존: 임시 파일과 가짜 입력만 사용한다. 운영 작업/외부 호출 없음."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.support import repository_modules, safety

safety()
repository_modules()
import briefing as B  # noqa: E402
import daily_brief as D  # noqa: E402
import econ_brief as E  # noqa: E402
import judge_live as J  # noqa: E402
import release_watch as R  # noqa: E402
import story_threads as S  # noqa: E402
import tg_publish as P  # noqa: E402
import theme_brief as T  # noqa: E402


class KeepPublicData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = 1_800_000_000

    def put(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path, path.read_bytes()

    def test_flash_empty_keeps_recent_file_and_never_pushes(self):
        path, before = self.put("flash.json", {"items": [{"t": self.now - 60}]})
        with patch.object(P, "BRANCH_DIR", str(self.root)), patch.object(P, "git") as git, \
                patch.object(P.subprocess, "run") as process:
            process.return_value.returncode = 0
            with self.assertRaisesRegex(ValueError, "실패"):
                P.publish({"at": self.now, "items": []})
        self.assertEqual(path.read_bytes(), before)
        git.assert_not_called()

    def test_flash_expiry_and_nonempty_update_are_allowed(self):
        (self.root / ".git").mkdir()
        for items, old_t in (([], self.now - P.WINDOW - 1), ([{"t": self.now}], self.now - 60)):
            with self.subTest(items=items):
                path, _ = self.put("flash.json", {"items": [{"t": old_t}]})
                doc = {"at": self.now, "items": items}
                with patch.object(P, "BRANCH_DIR", str(self.root)), patch.object(P, "git") as git, \
                        patch.object(P.subprocess, "run") as process:
                    process.return_value.returncode = 0
                    P.publish(doc)
                self.assertEqual(json.loads(path.read_text()), doc)
                self.assertTrue(git.called)

    def test_flash_serialization_failure_keeps_previous_bytes(self):
        (self.root / ".git").mkdir()
        path, before = self.put("flash.json", {"items": [{"t": self.now - 60}]})
        with patch.object(P, "BRANCH_DIR", str(self.root)), patch.object(P, "git") as git:
            with self.assertRaises(TypeError):
                P.publish({"at": self.now, "items": [{"bad": object()}]})
        self.assertEqual(path.read_bytes(), before)
        git.assert_not_called()

    def test_daily_empty_preserves_same_day_and_healthy_update_writes(self):
        path, before = self.put("2026-10-21.json", {"key": [{"ko": "이전 소식"}]})
        with patch.object(D, "OUT", str(self.root)), patch.object(D, "log") as log:
            self.assertIsNone(D.save({"date": "2026-10-21", "key": []}))
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("실패", str(log.call_args_list))
            doc = {"date": "2026-10-21", "key": [{"ko": "새 소식"}]}
            self.assertEqual(D.save(doc), str(path))
            self.assertEqual(json.loads(path.read_text()), doc)

    def test_threads_missing_store_and_empty_collection_preserve_both_files(self):
        import numpy as np
        path, before = self.put("threads.json", {"threads": [{"id": "old", "ids": ["s1"]}]})
        idx, old_idx = self.put("thread_index.json", {"s": {"s1": "old"}})
        with patch.object(S, "OUT", str(path)), patch.object(S, "STATE", str(self.root)), \
                patch.object(S, "collect", return_value=([], np.zeros((0, 1)))), \
                patch.object(S, "log") as log, patch.object(sys, "argv", ["story_threads.py"]):
            with self.assertRaisesRegex(ValueError, "실패"):
                S.main()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(idx.read_bytes(), old_idx)
        self.assertIn("실패", str(log.call_args_list))
        self.assertFalse((self.root / "ai.json").exists())

    def test_threads_valid_collection_can_have_no_qualifying_threads(self):
        import numpy as np
        path, _ = self.put("threads.json", {"threads": [{"id": "old", "ids": ["s1"]}]})
        meta = [{"id": "s1", "t": self.now, "ko": "새 소식", "en": "", "coins": []}]
        with patch.object(S, "OUT", str(path)), patch.object(S, "STATE", str(self.root)), \
                patch.object(S, "collect", return_value=(meta, np.zeros((1, 1)))), \
                patch.object(S, "build_threads", return_value=[]), \
                patch.object(sys, "argv", ["story_threads.py", "--no-ai"]):
            S.main()
        self.assertEqual(json.loads(path.read_text())["threads"], [])
        self.assertEqual(json.loads((self.root / "thread_index.json").read_text())["s"], {})

    def test_briefing_empty_or_prior_only_does_not_call_writer(self):
        path, before = self.put("briefing.json", {"ko": {"headline": "이전 브리핑"}})
        for ev in ([], [{"id": "P1", "text": "직전 브리핑"}]):
            with self.subTest(ev=ev), patch.object(B, "gather", return_value=(ev, {})), \
                    patch.object(B, "ask", return_value={}) as ask, patch.object(B, "log") as log:
                self.assertIsNone(B.run(str(path), self.now))
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(ask.call_count, 0)
                self.assertIn("실패", str(log.call_args_list))

    def test_briefing_empty_generated_answer_keeps_previous(self):
        path, before = self.put("briefing.json", {"ko": {"headline": "이전 브리핑"}})
        with patch.object(B, "gather", return_value=([{"id": "K1", "text": "금리 4%"}], {})), \
                patch.object(B, "ask", return_value={}), patch.object(B, "log") as log:
            self.assertIsNone(B.run(str(path), self.now))
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("실패", str(log.call_args_list))

    def test_themes_empty_collection_logs_failure_and_keeps_previous(self):
        path, before = self.put("themes.json", {"total": 50, "themes": [{"k": "crypto"}]})
        with patch.object(T, "OUT", str(path)), patch.object(T, "load_items", return_value=([], "db")), \
                patch.object(T, "get", return_value=[]), patch.object(T, "write_theme") as writer, \
                patch.object(T, "history", return_value=None), patch.object(T, "WRITE_AI", False), \
                patch.object(T, "log") as log:
            self.assertIsNone(T.run())
        self.assertEqual(path.read_bytes(), before)
        writer.assert_not_called()
        self.assertIn("실패", str(log.call_args_list))

    def test_release_maintenance_or_empty_response_does_not_publish(self):
        path, before = self.put("release_live.json", {"items": [{"id": "old"}]})
        state, _ = self.put("release_state.json", {"done": {}, "items": [{"id": "old", "ts": self.now - 7201}]})
        doc = {"by": {}, "upcoming": [{"ts": self.now - 30, "keys": ["cpi"]}]}
        for response in ("<html>maintenance</html>", '{"Results":{"series":[]}}'):
            tick = [self.now]

            def advance(seconds, tick=tick):
                tick[0] += seconds

            with self.subTest(response=response), patch.object(R, "HOME", str(self.root)), \
                    patch.object(R, "OUT", str(path)), patch.object(R, "STATE", str(state)), \
                    patch.object(R, "econ_doc", return_value=doc), patch.object(R, "get", return_value=response), \
                    patch.object(R.time, "time", side_effect=lambda tick=tick: tick[0]), \
                    patch.object(R.time, "sleep", side_effect=advance), patch.object(R, "publish") as publish:
                R.run(self.now)
                publish.assert_not_called()
                self.assertEqual(path.read_bytes(), before)

    def test_econ_maintenance_parse_cannot_replace_valid_indicators(self):
        path, before = self.put("econ.json", {"indicators": [{"k": "cpi"}] * 11})
        with patch.object(E, "cached", return_value="<html>maintenance</html>"):
            rows = E.releases(E.BY["cpi"])
        self.assertEqual(rows, [])
        with patch.object(E, "build", return_value={"indicators": rows, "upcoming": []}), \
                patch.object(sys, "argv", ["econ_brief.py", "--out", str(path)]), patch.object(E, "log") as log:
            E.main()
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("실패", str(log.call_args_list))

    def test_judge_empty_article_response_keeps_cache_and_public_file(self):
        cache, old_cache = self.put("cache.json", {"j": {"a1": {"kind": "event"}}})
        public, before = self.put("judgments.json", {"j": {"a1": {"kind": "event"}}})
        with patch.object(J, "HOME", str(self.root)), patch.object(J, "CACHE", str(cache)), \
                patch.object(J, "LOCK", str(self.root / "lock")), patch.object(J, "BRANCH_DIR", str(self.root)), \
                patch.object(J, "get_json", return_value=[]), patch.object(J, "publish") as publish, \
                patch.object(J, "ask") as ask, patch.object(J, "log") as log:
            J.run()
        self.assertEqual(cache.read_bytes(), old_cache)
        self.assertEqual(public.read_bytes(), before)
        publish.assert_not_called()
        ask.assert_not_called()
        self.assertIn("실패", str(log.call_args_list))

    def test_judge_healthy_articles_update_with_fake_answer(self):
        cache, _ = self.put("cache.json", {"j": {"old": {"kind": "event"}}})
        articles = [{"id": "new", "t0": self.now, "title": "새 소식"}]
        with patch.object(J, "HOME", str(self.root)), patch.object(J, "CACHE", str(cache)), \
                patch.object(J, "LOCK", str(self.root / "lock")), patch.object(J, "BRANCH_DIR", str(self.root)), \
                patch.object(J, "get_json", return_value=articles), patch.object(J, "publish") as publish, \
                patch.object(J, "ask", return_value={"kind": "event"}), patch.object(J.time, "time", return_value=self.now):
            J.run()
        self.assertEqual(json.loads(cache.read_text())["j"], {"new": {"kind": "event"}})
        publish.assert_called_once()
