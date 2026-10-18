"""Deployment gate. Policy/schema run once; browser setup failures may retry once.
Assertions, missing fixtures and product failures are never retried or ignored.
The CI step including dependency setup has a separate 3-minute hard timeout.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--site", required=True)
    p.add_argument("--flash", required=True)
    p.add_argument("--seconds", type=int, default=180)
    a = p.parse_args()
    start = time.monotonic()
    Path(".qa").mkdir(exist_ok=True)
    commands = [[sys.executable, "-m", "tests.check_site", "--site", a.site, "--flash", a.flash],
                [sys.executable, "-m", "pytest", "tests/e2e/test_matrix.py", "--matrix", "smoke", "--site", a.site, "--flash", a.flash, "-q", "--junitxml=.qa/gate.xml"]]
    for index, command in enumerate(commands):
        for attempt in range(2):
            left = a.seconds - (time.monotonic() - start)
            if left <= 0:
                raise TimeoutError("QA gate exceeded time budget")
            r = subprocess.run(command, capture_output=True, text=True, timeout=left)
            print(r.stdout, end="")
            print(r.stderr, end="", file=sys.stderr)
            if not r.returncode:
                break
            retryable = index == 1 and attempt == 0 and "TargetClosedError" in r.stdout and "AssertionError" not in r.stdout
            if not retryable:
                return r.returncode
            print("one retry: browser closed during setup; first failure retained in log")
        else:
            return r.returncode
    print(json.dumps({"gate": "passed", "seconds": round(time.monotonic() - start, 3)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
