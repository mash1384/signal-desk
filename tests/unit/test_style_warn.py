"""배포 전 검사(--style-warn): 말투 규칙은 경고만, 비밀값 · 출처 · 형식은 계속 막는다. 옵션이 없으면 말투도 막는다."""
import contextlib
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
