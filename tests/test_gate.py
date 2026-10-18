import contextlib
import io
import subprocess
import sys
import unittest
from unittest.mock import patch

from tests import gate


def outcome(code=0, text='passed\n'):
    return subprocess.CompletedProcess([], code, text, '')


class GateStages(unittest.TestCase):
    def execute(self, outcomes, extra=()):
        with patch.object(sys, 'argv', ['gate', '--site', 'fixture', '--flash', 'fixture'] + list(extra)), \
                patch.object(gate.subprocess, 'run', side_effect=outcomes) as run, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = gate.main()
        return rc, run.call_args_list

    def test_review_three_smoke_failures_never_retry(self):
        for message in ('ERROR at setup\nTargetClosedError', 'FAILED test_page CALL phase\nTargetClosedError', 'TargetClosedError\nAssertionError'):
            with self.subTest(message=message):
                rc, calls = self.execute([outcome(), outcome(), outcome(1, message), outcome()])
                self.assertEqual(rc, 1)
                self.assertEqual(len(calls), 3)
                self.assertEqual(sum('pytest' in c.args[0] for c in calls), 1)
                self.assertTrue(all(0 < c.kwargs['timeout'] <= 150 for c in calls))

    def test_only_readiness_can_fail_once_then_pass(self):
        rc, calls = self.execute([outcome(), outcome(1, 'TargetClosedError'), outcome(), outcome()])
        self.assertEqual(rc, 0)
        self.assertEqual([c.args[0][2] for c in calls], ['tests.check_site', 'tests.browser_ready', 'tests.browser_ready', 'pytest'])

    def test_second_readiness_failure_stops_before_smoke(self):
        rc, calls = self.execute([outcome(), outcome(1), outcome(1), outcome()])
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 3)
        self.assertFalse(any('pytest' in c.args[0] for c in calls))

    def test_contract_failure_stops_before_browser(self):
        rc, calls = self.execute([outcome(1), outcome()])
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 1)

    def test_readiness_timeout_is_fatal(self):
        rc, calls = self.execute([outcome(), subprocess.TimeoutExpired(['ready'], 1), outcome()])
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 2)

    def test_exhausted_budget_has_clear_failure(self):
        with patch.object(gate.time, 'monotonic', side_effect=[0, 151]), patch.object(sys, 'argv', ['gate', '--site', 'fixture', '--flash', 'fixture']), \
                patch.object(gate.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(gate.main(), 1)
        run.assert_not_called()
        self.assertIn('exceeded 150s budget', errors.getvalue())
