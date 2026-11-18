"""tests classify / summary on system failures (story 1, t-2).

A system failure is a failure the runner reports that is not a test (see the glossary). Alone it
means CANNOT RUN: the environment broke, the code was never judged. Beside real failures the
result is FAIL, and the reason names the system failure too. It is never counted as passed or
failed.

The launch-error fixtures are real Xcode 26.2 results: the simulator was busy, the test runner
could not launch, and the run ended with exit code 65.

"Results with no system failure classify as before" is covered by the existing classify and summary
tests in test_tests_cli.py / test_tests_logic.py, which stay green; a new test for it could not be red.

JUnit (criterion 5), decided from the reader's code and what real harnesses write: JUnit XML has
no system failure concept. Gradle, pytest, Vitest, Jest and SwiftPM write a failed launch or
collection as an ordinary <failure>/<error> testcase, or as no testcase at all, and the reader
already handles both: the first is a failing test, the second is classified from the exit code
and the empty result. Nothing to fix there, so no JUnit test is added (it could not be red).
"""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.tests import main

from tests.helpers import run_tool

FIXTURES = Path(__file__).parent / "fixtures"
LAUNCH_ERROR = (FIXTURES / "xcresult_launch_error_busy_simulator.json").read_text()
SECOND_RUN = (FIXTURES / "xcresult_launch_error_busy_simulator_second_run.json").read_text()
XCRESULT_TESTS = (FIXTURES / "xcresult_tests.json").read_text()
LAUNCH_NAME = "FlashCardsRO encountered an error"
LAUNCH_START = "Failed to install or launch the test runner."
CONFIG = "# sketch config\ntest_format: xcresult-json\n"


def with_system_failure(name: str, message: str, *real_results: str) -> str:
    """A hand-written xcresult file: real tests (one per result) beside one system failure."""
    cases = [{"nodeType": "Test Case", "name": "t" + str(i), "nodeIdentifier": "S/t" + str(i) + "()",
              "result": result, "children": [{"nodeType": "Failure Message", "name": "wrong " + str(i)}]}
             for i, result in enumerate(real_results)]
    system = {"nodeType": "Test Suite", "name": "System Failures", "children": [
        {"nodeType": "Test Case", "name": name, "nodeIdentifier": name, "result": "Failed",
         "children": [{"nodeType": "Failure Message", "name": message}]}]}
    return json.dumps({"testNodes": [{"nodeType": "Test Plan", "name": "P", "children": [
        {"nodeType": "Unit test bundle", "name": "B", "children": [
            {"nodeType": "Test Suite", "name": "S", "children": cases}, system]}]}]})


class SystemFailureCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.config = base / "config.md"
        self.config.write_text(CONFIG)
        self.folder = base / "results"
        self.folder.mkdir()

    def write(self, text: str) -> None:
        (self.folder / "001-results.json").write_text(text)

    def run_it(self, command: str, *extra: str):
        return run_tool(main, [command, "--config", str(self.config), "--results", str(self.folder), *extra])

    def classify(self, exit_code: int = 65):
        return self.run_it("classify", "--exit", str(exit_code))


class OnlySystemFailuresTest(SystemFailureCase):
    """1. Only system failures: classify returns CANNOT RUN, not UNKNOWN or FAIL."""

    def test_the_real_launch_error_classifies_as_cannot_run(self) -> None:
        self.write(LAUNCH_ERROR)
        code, out, _ = self.classify()
        self.assertEqual(out.splitlines()[0], "CANNOT RUN")
        self.assertEqual(code, 1)

    def test_the_second_real_launch_error_classifies_as_cannot_run(self) -> None:
        self.write(SECOND_RUN)
        self.assertEqual(self.classify()[1].splitlines()[0], "CANNOT RUN")

    def test_a_system_failure_with_exit_zero_is_still_cannot_run(self) -> None:
        # added scenario: the verdict does not depend on the exit code
        self.write(LAUNCH_ERROR)
        out = self.classify(0)[1]
        self.assertEqual(out.splitlines()[0], "CANNOT RUN")
        self.assertIn(LAUNCH_NAME, out)

    def test_a_synthetic_system_failure_alone_classifies_as_cannot_run(self) -> None:
        # added scenario: a system failure beside only passed and skipped tests is still not a pass
        self.write(with_system_failure("Runner crashed", "boom", "Passed", "Skipped"))
        self.assertEqual(self.classify()[1].splitlines()[0], "CANNOT RUN")


class CannotRunMessageTest(SystemFailureCase):
    """2. The CANNOT RUN message names the system failure and carries the launch message."""

    def test_the_reason_contains_the_launch_message(self) -> None:
        self.write(LAUNCH_ERROR)
        reason = self.classify()[1].splitlines()[1]
        self.assertTrue(reason.startswith("reason: "), reason)
        self.assertIn(LAUNCH_START, reason)

    def test_the_reason_names_the_system_failure(self) -> None:
        self.write(LAUNCH_ERROR)
        self.assertIn(LAUNCH_NAME, self.classify()[1].splitlines()[1])

    def test_the_reason_says_it_is_a_system_failure(self) -> None:
        self.write(LAUNCH_ERROR)
        self.assertIn("system failure", self.classify()[1].splitlines()[1])


class MixedWithRealFailuresTest(SystemFailureCase):
    """3. System failures mixed with real failures: classify returns FAIL and names the system failure."""

    def test_the_fail_reason_names_the_system_failure_and_its_message(self) -> None:
        self.write(with_system_failure("Runner crashed", "boom", "Failed"))
        code, out, _ = self.classify()
        self.assertEqual((code, out.splitlines()[0]), (1, "FAIL"))
        self.assertIn("Runner crashed", out)
        self.assertIn("boom", out)

    def test_the_fail_reason_still_counts_the_real_failing_tests(self) -> None:
        self.write(with_system_failure("Runner crashed", "boom", "Failed", "Failed"))
        out = self.classify()[1]
        self.assertIn("2 failing tests", out)
        self.assertIn("Runner crashed", out)


class CliOutputTest(SystemFailureCase):
    """4. The CLI output for the flash-cards results file says CANNOT RUN with the launch message."""

    def test_classify_prints_cannot_run_and_the_launch_message(self) -> None:
        self.write(LAUNCH_ERROR)
        _, out, err = self.classify()
        self.assertTrue(out.startswith("CANNOT RUN\nreason: "), out)
        self.assertIn(LAUNCH_START, out)
        self.assertEqual(err, "")

    def test_summary_shows_the_system_failure_apart_from_the_counts(self) -> None:
        self.write(LAUNCH_ERROR)
        code, out, _ = self.run_it("summary")
        self.assertEqual(code, 0)
        self.assertIn("passed 0\n", out)
        self.assertIn("failed 0\n", out)
        self.assertIn(LAUNCH_NAME, out)

    def test_summary_json_keeps_the_counts_and_shows_the_system_failure(self) -> None:
        self.write(with_system_failure("Runner crashed", "boom", "Passed", "Failed"))
        data = json.loads(self.run_it("summary", "--json")[1])
        self.assertEqual((data["passed"], data["failed"], data["skipped"]), (1, 1, 0))
        self.assertIn("Runner crashed", json.dumps(data))
