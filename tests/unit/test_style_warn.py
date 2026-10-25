"""배포 전 검사(--style-warn): 말투 규칙은 경고만, 비밀값 · 출처 · 형식은 계속 막는다. 옵션이 없으면 말투도 막는다."""
import contextlib
import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import check_site


def result(*rules):
    errs = [{"file": "daily/themes.json", "rule": r, "path": "/x"} for r in rules]
    return {"policy": {"site": {"files": 1, "errors": []}, "flash": {"files": 1, "errors": errs}}, "schema": [], "files": []}


def run(res, *flags):
    with tempfile.TemporaryDirectory() as tmp, patch.object(check_site, "check", return_value=res), \
            patch("sys.argv", ["check_site", "--site", tmp, "--flash", tmp, "--output", str(Path(tmp) / "r.json"), *flags]):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_site.main()
        return code, out.getvalue()


class StyleWarn(unittest.TestCase):
    def test_style_only_warns_in_deploy_gate(self):
        code, out = run(result("ai-korean-style"), "--style-warn")
        self.assertEqual(code, 0)
        self.assertIn("WARNING style", out)

    def test_style_blocks_without_option(self):
        self.assertEqual(run(result("ai-korean-style"))[0], 1)

    def test_secret_and_source_still_block_in_deploy_gate(self):
        for rule in ("secret-pattern", "telegram-source", "excerpt-length"):
            with self.subTest(rule=rule):
                self.assertEqual(run(result("ai-korean-style", rule), "--style-warn")[0], 1)

    def test_gate_passes_the_option(self):
        self.assertIn("'--style-warn'", (Path(__file__).resolve().parents[1] / "gate.py").read_text())


class ViolationDetails(unittest.TestCase):
    """2026-10-25: 실패 로그에 'violations=3'만 남아 원인을 찾는 데 3시간 걸렸다 — 위치는 찍고 값은 찍지 않는다."""

    def test_schema_violation_names_file_and_path(self):
        res = result()
        res["schema"] = [{"schema": "econ", "path": "/upcoming/2/ko", "validator": "type", "message": "schema type failed", "got": "null", "file": "flash/daily/econ.json"}]
        code, out = run(res, "--style-warn")
        self.assertEqual(code, 1)
        self.assertIn("VIOLATION schema econ file=flash/daily/econ.json path=/upcoming/2/ko schema type failed got=null", out)

    def test_policy_violation_names_rule_and_path_only(self):
        code, out = run(result("telegram-source"), "--style-warn")
        self.assertEqual(code, 1)
        self.assertIn("VIOLATION policy flash rule=telegram-source file=daily/themes.json path=/x", out)

    def test_real_schema_error_reports_type_not_value(self):
        errs = check_site.validate("econ", {"upcoming": [{"ts": 1, "keys": [], "en": "x", "ko": None, "impact": "high"}]})
        bad = [e for e in errs if e["path"] == "/upcoming/0/ko"]
        self.assertEqual(bad[0]["got"], "null")
        errs = check_site.validate("econ", {"upcoming": [{"ts": 1, "keys": [], "en": "x", "ko": ["sk-secret-value-should-not-print"], "impact": "high"}]})
        self.assertNotIn("sk-secret", json.dumps(errs))

    def test_long_lists_are_capped(self):
        res = result(*(["telegram-source"] * 60))
        out = run(res, "--style-warn")[1]
        self.assertEqual(out.count("VIOLATION policy"), 50)
        self.assertIn("and 10 more", out)
