"""python -m tests.run_unit [--focus] [--coverage]. Nonzero for failures OR skips.

--focus runs the passing stage-1 mutation baseline; known-defect regressions are
still collected and fail in the default complete suite (never skip/xfail).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--focus", action="store_true")
    p.add_argument("--legacy", action="store_true", help="measurement only: original target-module tests")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--output", default=".qa/unit.json")
    args = p.parse_args()
    if not os.environ.get("SIGNAL_TEST_CHILD"):
        # A fresh cache is necessary: -B alone still READS old bytecode.
        with tempfile.TemporaryDirectory(prefix="signal-tests-") as cache:
            env = dict(os.environ, PYTHONPYCACHEPREFIX=cache, SIGNAL_TEST_CHILD="1")
            return subprocess.call([sys.executable, "-m", "tests.run_unit"] + sys.argv[1:], env=env)
    from tests.support import ROOT, repository_modules, safety
    safety()
    cov = None
    if args.coverage:
        import coverage
        cov = coverage.Coverage(source=["pipeline", "tools"], data_file=str(ROOT / ".qa" / "coverage"))
        cov.start()
    repository_modules()
    loader = unittest.TestLoader()
    if args.focus:
        suite = unittest.TestSuite() if args.legacy else loader.discover(str(ROOT / "tests" / "unit"), top_level_dir=str(ROOT))
        # 고장 주입 대상이 없는 느린 모듈(글꼴 만들기 7초 · 그림 사전 2초)은 고장 주입 묶음에서만 뺀다 — 전체 단위 시험에서는 그대로 돈다.
        # 대상 목록(tests/mutation/run.py CATALOG)에 그 모듈이 들어오면 다시 넣는다. 11-02: 뺀 것 없이 25초 × 58개가 CI 15분을 넘었다
        try:
            from tests.mutation.run import CATALOG
            targets = {c[0] for c in CATALOG}
        except ImportError:
            targets = set()
        slow = {"tests.unit.test_pagefont": "pipeline/pagefont.py", "tests.unit.test_art": "pipeline/art.py"}
        skip = {m for m, src in slow.items() if src not in targets}

        def keep(s):
            for t in s:
                if isinstance(t, unittest.TestSuite):
                    yield from keep(t)
                elif type(t).__module__ not in skip:
                    yield t
        suite = unittest.TestSuite(list(keep(suite)))
        focus = ["tests.test_judge", "tests.test_classify", "tests.test_econ_brief", "tests.test_daily_brief", "tests.test_story_threads", "tests.test_newdata", "tests.test_tg_publish"]
        # 공개 저장소에는 Mac 작업(tools) 검사가 없다 — 있는 것만
        suite.addTests(loader.loadTestsFromNames([n for n in focus if (ROOT / (n.replace(".", "/") + ".py")).is_file()]))
    else:
        suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    start = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    data = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped), "seconds": round(time.monotonic() - start, 3),
            "details": [{"test": str(t), "trace": e} for t, e in result.failures + result.errors], "python": sys.version.split()[0], "focus": args.focus}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    if cov:
        cov.stop()
        cov.save()
        cov.json_report(outfile=str(ROOT / ".qa" / "coverage.json"))
        cov.report()
    return int(not result.wasSuccessful() or bool(result.skipped) or not result.testsRun)


if __name__ == "__main__":
    sys.exit(main())
