"""tests: the xcresult reader and system failures (story 1, t-1).

A system failure is a failure the runner reports that is not a test: Xcode writes it as a Test
Case under a Test Suite named "System Failures". `read` must leave it out of the cases, so it is
never counted as passed or failed, and `read_system_failures` hands it back with its message.

The two xcresult_launch_error_* fixtures are real Xcode 26.2 results of a run where the simulator
was busy and the test runner could not launch. The synthetic files are hand-written to that shape.
"""

import json
import unittest
from pathlib import Path

from sketch_tools.tests.model import FAILED, PASSED, Case
from sketch_tools.tests.readers.xcresult import read as read_xcresult
from sketch_tools.tests.readers.xcresult import read_system_failures

FIXTURES = Path(__file__).parent / "fixtures"
LAUNCH_ERROR = FIXTURES / "xcresult_launch_error_busy_simulator.json"
LAUNCH_ERROR_SECOND_RUN = FIXTURES / "xcresult_launch_error_busy_simulator_second_run.json"
LAUNCH_NAME = "FlashCardsRO encountered an error"
LAUNCH_START = "Failed to install or launch the test runner."


def count(cases, status):
    return len([c for c in cases if c.status == status])


def real_case(name, result, *messages):
    return {"nodeType": "Test Case", "name": name, "nodeIdentifier": "S/" + name, "result": result,
            "children": [{"nodeType": "Failure Message", "name": m} for m in messages]}


def system_failure_suite(name, message):
    return {"nodeType": "Test Suite", "name": "System Failures", "children": [
        {"nodeType": "Test Case", "name": name, "nodeIdentifier": name, "result": "Failed",
         "children": [{"nodeType": "Failure Message", "name": message}]}]}


def run(*suites):
    return json.dumps({"testNodes": [{"nodeType": "Test Plan", "name": "P", "children": [
        {"nodeType": "Unit test bundle", "name": "B", "children": list(suites)}]}]})


def real_suite(*cases):
    return {"nodeType": "Test Suite", "name": "S", "children": list(cases)}


class SystemFailureIsNotCountedTest(unittest.TestCase):
    """1. A system failure under a "System Failures" suite is not counted as passed or failed."""

    def test_real_launch_error_gives_zero_passed_and_zero_failed(self) -> None:
        cases = read_xcresult(LAUNCH_ERROR.read_text())
        self.assertEqual((count(cases, PASSED), count(cases, FAILED)), (0, 0))

    def test_real_launch_error_leaves_no_cases_at_all(self) -> None:
        self.assertEqual(read_xcresult(LAUNCH_ERROR.read_text()), [])

    def test_second_real_launch_error_is_read_with_its_system_failure_left_out_of_the_counts(self) -> None:
        cases = read_xcresult(LAUNCH_ERROR_SECOND_RUN.read_text())
        self.assertEqual((count(cases, PASSED), count(cases, FAILED)), (0, 0))
        self.assertEqual(len(read_system_failures(LAUNCH_ERROR_SECOND_RUN.read_text())), 1)


class SystemFailureKeepsItsMessageTest(unittest.TestCase):
    """2. The system failure's message is kept in the reader's result."""

    def test_real_launch_error_keeps_the_launch_message(self) -> None:
        failures = read_system_failures(LAUNCH_ERROR.read_text())
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].name, LAUNCH_NAME)
        self.assertTrue(failures[0].message.startswith(LAUNCH_START), failures[0].message)
        self.assertIn("Busy", failures[0].message)

    def test_a_system_failure_is_a_failed_case_in_the_reader_result(self) -> None:
        text = run(system_failure_suite("Runner crashed", "boom"))
        self.assertEqual(read_system_failures(text), [Case("Runner crashed", FAILED, "boom")])

    def test_every_system_failure_is_kept_in_file_order(self) -> None:
        text = run(system_failure_suite("first", "one"), system_failure_suite("second", "two"))
        self.assertEqual([(c.name, c.message) for c in read_system_failures(text)],
                         [("first", "one"), ("second", "two")])


class RealTestsBesideASystemFailureTest(unittest.TestCase):
    """3. Real tests beside a system failure are still counted correctly."""

    def test_two_real_failures_beside_a_system_failure_count_two_failed(self) -> None:
        text = run(real_suite(real_case("a()", "Failed", "x"), real_case("b()", "Failed", "y")),
                   system_failure_suite("Runner crashed", "boom"))
        cases = read_xcresult(text)
        self.assertEqual(count(cases, FAILED), 2)
        self.assertEqual([c.name for c in cases], ["S/a()", "S/b()"])

    def test_passed_and_failed_tests_beside_a_system_failure_keep_their_status(self) -> None:
        text = run(system_failure_suite("Runner crashed", "boom"),
                   real_suite(real_case("a()", "Passed"), real_case("b()", "Failed", "y")))
        self.assertEqual(read_xcresult(text), [Case("S/a()", PASSED), Case("S/b()", FAILED, "y")])

    def test_the_system_failure_is_still_kept_beside_real_tests(self) -> None:
        text = run(real_suite(real_case("a()", "Failed", "x"), real_case("b()", "Failed", "y")),
                   system_failure_suite("Runner crashed", "boom"))
        self.assertEqual(read_system_failures(text), [Case("Runner crashed", FAILED, "boom")])
