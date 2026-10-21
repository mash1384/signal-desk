"""Bounded, reviewable mutation sample; never mutates the working repository.

mutmut 3.8 requires Python >=3.10 (https://pypi.org/project/mutmut/).
This identical runner supports 3.9 and 3.12. The catalog is fixed before running;
survivors remain in the denominator. Syntax/tool errors are NOT killed mutants.
"""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]

# filename, function, original fragment, changed fragment
CATALOG = [   # 공개 저장소: 사이트 빌드(pipeline) 쪽. Mac 작업(tools) 쪽은 비공개 저장소의 catalog_tools.py
    ("pipeline/judge.py", "normalize", 'not isinstance(j, dict)', 'isinstance(j, dict)'),
    ("pipeline/judge.py", "normalize", '== "event"', '!= "event"'),
    ("pipeline/judge.py", "normalize", '[:3]', '[:2]'),
    ("pipeline/judge.py", "normalize", 'min(3,', 'min(2,'),
    ("pipeline/judge.py", "normalize", 'max(0,', 'max(1,'),
    ("pipeline/judge.py", "normalize", 'and not coins', 'and True'),
    ("pipeline/judge.py", "normalize", 'bool(US.search(title or ""))', 'True'),
    ("pipeline/judge.py", "normalize", '[:40]', '[:39]'),
    ("pipeline/judge.py", "apply", 'subjects(a) != before', 'subjects(a) == before'),
    ("pipeline/judge.py", "load", 'doc.get("v") != VERSION', 'doc.get("v") == VERSION'),
    ("pipeline/impact.py", "grade", 'a >= config.GRADE_STRONG', 'a > config.GRADE_STRONG'),
    ("pipeline/impact.py", "grade", 'a >= config.GRADE_MEDIUM', 'a > config.GRADE_MEDIUM'),
    ("pipeline/impact.py", "_sd", 'len(values) < 20', 'len(values) <= 20'),
    ("pipeline/impact.py", "_sd", '(len(values) - 1)', 'len(values)'),
    ("pipeline/impact.py", "_pending", 'now >= article["t0"] + secs + 120', 'now > article["t0"] + secs + 120'),
    ("pipeline/impact.py", "volatility", '< STATS_TTL', '<= STATS_TTL'),
    ("pipeline/impact.py", "_spans", 'lo <= out[-1][1] + gap', 'lo < out[-1][1] + gap'),
    ("pipeline/impact.py", "concurrency", '<= config.CONCURRENT_EVENT_SECONDS', '< config.CONCURRENT_EVENT_SECONDS'),
    ("pipeline/impact.py", "concurrency", '<= 1800', '< 1800'),
    ("pipeline/impact.py", "type_stats", 'len(rows) < 3', 'len(rows) <= 3'),
    ("pipeline/impact.py", "strongest", '> days * 86400', '>= days * 86400'),
    ("pipeline/impact.py", "subjects", 'ai.get("kind") != "event"', 'ai.get("kind") == "event"'),
]

_PRIVATE = Path(__file__).with_name("catalog_tools.py")
if _PRIVATE.is_file():   # 비공개 저장소에서는 Mac 작업 쪽 변이도 함께
    _spec = importlib.util.spec_from_file_location("catalog_tools", _PRIVATE)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    CATALOG = CATALOG + _mod.CATALOG


def changed(source, function, old, new):
    start = source.index("def " + function + "(")
    end = source.find("\ndef ", start + 1)
    end = len(source) if end < 0 else end
    block = source[start:end]
    if old not in block:
        raise ValueError("mutation anchor absent: " + function + " / " + old)
    return source[:start] + block.replace(old, new, 1) + source[end:]


def run_suite(root, report, legacy=False, focus=True):
    env = dict(os.environ)
    env.pop("SIGNAL_TEST_CHILD", None)
    proc = subprocess.run([sys.executable, "-m", "tests.run_unit", "--output", str(report)] + (["--focus"] if focus else []) + (["--legacy"] if legacy else []), cwd=str(root), env=env, capture_output=True, text=True, timeout=45)
    if not report.is_file():
        raise RuntimeError("test runner failed before writing results: " + proc.stderr[-1000:])
    result = json.loads(report.read_text())
    infrastructure = any("_FailedTest" in d["test"] or "TEST SAFETY:" in d["trace"] or "SyntaxError:" in d["trace"] for d in result["details"])
    if not result["tests"] or result["skips"] or infrastructure:
        raise RuntimeError("mutation infrastructure/test error: " + proc.stderr[-1500:])
    return proc.returncode, result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", default=".qa/mutation.json")
    parser.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="signal-mutation-") as tmp:
        root = Path(tmp)
        for dirname in ("pipeline", "tools", "tests"):
            if (ROOT / dirname).is_dir():   # 공개 저장소에는 tools 가 없다
                shutil.copytree(ROOT / dirname, root / dirname, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        report = root / "result.json"
        rc, baseline = run_suite(root, report, args.legacy)
        if rc:
            raise RuntimeError("unmutated baseline is not green; refusing false kills")
        rows = []
        for i, (filename, function, old, new) in enumerate(CATALOG, 1):
            path = root / filename
            original = path.read_text()
            mutant = changed(original, function, old, new)
            compile(mutant, filename, "exec")
            try:
                path.write_text(mutant)
                report.unlink()
                rc, result = run_suite(root, report, args.legacy)
                if result["tests"] != baseline["tests"]:
                    raise RuntimeError("mutation changed test collection")
            finally:
                path.write_text(original)
            row = {"id": i, "file": filename, "function": function, "old": old, "new": new, "status": "killed" if rc else "survived", "failures": [d["test"] for d in result["details"]]}
            rows.append(row)
            print("%02d %s %s.%s" % (i, row["status"], filename, function), flush=True)
    killed = sum(r["status"] == "killed" for r in rows)
    result = {"sample_only": True, "python": sys.version.split()[0], "baseline_tests": baseline["tests"], "total": len(rows), "killed": killed, "rate": killed / len(rows), "seconds": round(time.monotonic() - start, 3), "catalog_sha256": hashlib.sha256(json.dumps(CATALOG).encode()).hexdigest(), "mutants": rows}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("%d/%d = %.1f%% in %.2fs" % (killed, len(rows), 100 * result["rate"], result["seconds"]))
    return int(result["rate"] < .8)


if __name__ == "__main__":
    sys.exit(main())
