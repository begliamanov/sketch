"""Tester report: `counts` is required for PASS and FAIL, optional for CANNOT RUN (t-5).

When the test runner never launched there is nothing to count, so a CANNOT RUN report may leave
`counts` out. A PASS or FAIL report without counts is still rejected, and core/agents/tester.md says so.
"""

import unittest
from pathlib import Path

from tests.report_examples import with_changes
from tests.test_report_roles import RoleCase

ROOT = Path(__file__).resolve().parents[2]
COUNTS = {"passed": 40, "failed": 2, "skipped": 0}
FAILING = [{"name": "BannerTests.hides", "message": "expected hidden"}]


class CountsRequiredUnlessCannotRunTest(RoleCase):
    # criterion 1 (a CANNOT RUN report without counts is accepted) already holds before t-5:
    # no red test is possible.

    def test_a_fail_report_without_counts_is_rejected(self) -> None:
        report = with_changes("tester", result="FAIL", failing_tests=FAILING, counts=...)
        self.assert_problem("tester", report, "counts", "required")

    def test_a_pass_report_without_counts_is_rejected(self) -> None:
        report = with_changes("tester", result="PASS", counts=...)
        self.assert_problem("tester", report, "counts", "required")

    def test_counts_missing_on_a_task_mode_pass_is_rejected(self) -> None:
        report = with_changes("tester", mode="task", result="PASS", counts=...)
        self.assertTrue(any("counts" in p for p in self.problems("tester", report, scope="t-3")))

    # criterion 3. Pins behavior that already exists and is intended, so it passes at once: a later
    # rule that rejected counts on CANNOT RUN must not get through the suite.
    def test_a_cannot_run_report_with_valid_counts_is_still_accepted(self) -> None:
        report = with_changes("tester", result="CANNOT RUN", counts=COUNTS, cannot_run_because="Could not resolve com.example:lib (401)")
        self.assert_valid("tester", report)


class TesterFileTest(unittest.TestCase):
    def test_tester_md_says_counts_are_optional_on_cannot_run(self) -> None:
        text = ROOT.joinpath("core", "agents", "tester.md").read_text()
        line = next(l for l in text.splitlines() if l.startswith("- `counts`"))
        self.assertRegex(line, r"(?i)optional.*CANNOT RUN|CANNOT RUN.*optional")
        self.assertNotRegex(line, r"\(optional\)\s*$")
