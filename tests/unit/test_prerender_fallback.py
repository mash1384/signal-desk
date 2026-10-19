"""첫 화면 미리 그리기가 실패해도 사이트 빌드(=뉴스 배포)는 계속된다. 엄격 모드(main 합치기 전 검사)에서는 실패한다."""
import os
import tempfile
import unittest
from unittest.mock import patch

from pipeline import build


class Stop(Exception):
    """미리 그리기 다음 단계(자산 복사)에서 빌드를 멈춰 그 앞까지만 시험한다."""


def build_until_assets(out):
    with patch.object(build.prerender, "render", side_effect=FileNotFoundError("node")), \
            patch.object(build.shutil, "copytree", side_effect=Stop):
        build._build_site(out, [], {}, {}, {}, {}, 0, extra={})


class PrerenderFallback(unittest.TestCase):
    def test_failure_falls_back_and_logs(self):
        env = {k: v for k, v in os.environ.items() if k != "SIGNAL_PRERENDER_STRICT"}
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, env, clear=True), patch.object(build.util, "log") as log:
            with self.assertRaises(Stop):          # 미리 그리기 실패를 넘어 다음 단계까지 진행했다
                build_until_assets(out)
        self.assertTrue(any("prerender skipped" in str(c) for c in log.call_args_list))

    def test_strict_mode_raises(self):
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {"SIGNAL_PRERENDER_STRICT": "1"}):
            with self.assertRaises(FileNotFoundError):
                build_until_assets(out)
