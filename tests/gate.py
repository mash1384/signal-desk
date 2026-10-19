"""Deployment gate: contracts once, readiness up to twice, smoke exactly once.
The 150-second default leaves reporting/termination time within CI's 180-second
step. Dependency installation is outside this budget and must be measured too.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--site', required=True)
    p.add_argument('--flash', required=True)
    p.add_argument('--seconds', type=int, default=150)
    p.add_argument('--browser-channel', default='chromium' if os.environ.get('CI') else 'chrome')
    args = p.parse_args()
    start = time.monotonic()
    Path('.qa').mkdir(exist_ok=True)

    def run(stage, command):
        left = args.seconds - (time.monotonic() - start)
        if left <= 0:
            raise TimeoutError('QA gate exceeded %ds budget before %s' % (args.seconds, stage))
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=left)
        except subprocess.TimeoutExpired as error:
            raise TimeoutError('QA gate timeout during %s (total budget %ds)' % (stage, args.seconds)) from error
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
        return result.returncode

    contracts = [sys.executable, '-m', 'tests.check_site', '--site', args.site, '--flash', args.flash]
    ready = [sys.executable, '-m', 'tests.browser_ready', '--channel', args.browser_channel]
    smoke = [sys.executable, '-m', 'pytest', 'tests/e2e/test_matrix.py', 'tests/e2e/test_release.py', '--matrix', 'smoke',
             '--site', args.site, '--flash', args.flash, '--browser-channel', args.browser_channel, '-q', '--junitxml=.qa/gate.xml',
             '--a11y', 'report', '-s']   # 배포 데이터는 매번 새 뉴스 — 접근성 기준선 비교는 경고로 로그에만(고정 스냅샷 검사는 로컬 strict)
    try:
        rc = run('contracts', contracts)
        if rc:
            return rc
        rc = run('browser readiness', ready)
        if rc:
            print('one retry of isolated browser readiness; first failure retained above')
            rc = run('browser readiness retry', ready)
            if rc:
                return rc
        # Test output never controls retries, including setup/CALL TargetClosedError.
        rc = run('smoke tests', smoke)
        if rc:
            return rc
    except TimeoutError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({'gate': 'passed', 'seconds': round(time.monotonic() - start, 3)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
