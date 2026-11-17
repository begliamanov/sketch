"""tests: the answers about a list of cases (pure logic), and the settings read from the config."""

import unittest

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.tests.logic import (
    CANNOT_RUN, FAIL, PASS, UNKNOWN, classify, expect_red, failing, failures_diff, skipped_diff, summarize,
)
from sketch_tools.tests.model import ASSERTION, ERROR, FAILED, PASSED, SKIPPED, Case
from sketch_tools.tests.settings import command_for, parse_settings, results_pattern_problem

OK = Case("A.ok", PASSED)
BAD = Case("A.bad", FAILED, "expected 1", ASSERTION)
SKIP = Case("A.skip", SKIPPED, "no device")
BOOM = Case("A.boom", FAILED, "ImportError: no module named x", ERROR)


class SummarizeTest(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(summarize([OK, OK, BAD, SKIP, BOOM]), {"passed": 2, "failed": 2, "skipped": 1})
        self.assertEqual(summarize([]), {"passed": 0, "failed": 0, "skipped": 0})

    def test_failing_keeps_the_order(self) -> None:
        self.assertEqual(failing([OK, BAD, SKIP, BOOM]), [BAD, BOOM])
        self.assertEqual(failing([OK]), [])


class ClassifyTest(unittest.TestCase):
    def test_pass_needs_a_clean_exit_and_tests_that_ran_and_passed(self) -> None:
        self.assertEqual(classify(0, 1, [OK, SKIP]), (PASS, ""))

    def test_any_failing_test_is_a_fail_whatever_the_exit_code(self) -> None:
        for code in (0, 1, 65):
            with self.subTest(exit=code):
                result, reason = classify(code, 2, [OK, BAD, BOOM])
                self.assertEqual(result, FAIL)
                self.assertIn("2 failing tests", reason)
        self.assertIn("1 failing test", classify(1, 1, [BAD])[1])
        self.assertNotIn("1 failing tests", classify(1, 1, [BAD])[1])

    def test_a_clean_exit_with_no_result_files_means_nothing_is_known_to_have_run(self) -> None:
        result, reason = classify(0, 0, [])
        self.assertEqual(result, CANNOT_RUN)
        self.assertIn("no test results", reason)

    def test_a_clean_exit_with_result_files_that_list_no_tests_means_nothing_ran(self) -> None:
        result, reason = classify(0, 2, [])
        self.assertEqual(result, CANNOT_RUN)
        self.assertIn("nothing ran", reason)

    def test_a_failed_command_without_results_is_unknown_code_or_environment(self) -> None:
        for files, cases in ((0, []), (1, [])):
            with self.subTest(files=files):
                result, reason = classify(65, files, cases)
                self.assertEqual(result, UNKNOWN)
                self.assertIn("exit 65", reason)

    def test_all_tests_passed_but_the_command_failed_is_unknown(self) -> None:
        result, reason = classify(1, 1, [OK])
        self.assertEqual(result, UNKNOWN)
        self.assertIn("every test passed", reason)
        self.assertIn("exit 1", reason)


class ExpectRedTest(unittest.TestCase):
    def test_tests_that_ran_and_failed_are_fine(self) -> None:
        self.assertEqual(expect_red([OK, BAD], ["A.bad"]), ([], []))

    def test_a_test_that_did_not_run_is_a_problem(self) -> None:
        problems, reviews = expect_red([OK], ["A.missing"])
        self.assertEqual(reviews, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("A.missing", problems[0])
        self.assertIn("did not run", problems[0])

    def test_a_test_that_passed_or_was_skipped_is_a_problem(self) -> None:
        problems, _ = expect_red([OK, SKIP], ["A.ok", "A.skip"])
        self.assertEqual(len(problems), 2)
        self.assertIn("passed", problems[0])
        self.assertIn("must fail", problems[0])
        self.assertIn("skipped", problems[1])

    def test_a_failure_with_an_error_instead_of_an_assertion_is_for_review_not_a_problem(self) -> None:
        problems, reviews = expect_red([BOOM], ["A.boom"])
        self.assertEqual(problems, [])
        self.assertEqual(len(reviews), 1)
        self.assertIn("A.boom", reviews[0])
        self.assertIn("error", reviews[0])
        self.assertIn("ImportError: no module named x", reviews[0])

    def test_a_format_that_cannot_tell_assertions_from_errors_is_never_reviewed(self) -> None:
        self.assertEqual(expect_red([Case("S/t()", FAILED, "XCTAssertEqual failed")], ["S/t()"]), ([], []))

    def test_every_name_is_checked_in_one_pass_and_in_the_order_given(self) -> None:
        problems, reviews = expect_red([OK, BAD, BOOM], ["A.ok", "A.bad", "A.boom", "A.none"])
        self.assertEqual(len(problems), 2)
        self.assertEqual(len(reviews), 1)
        self.assertIn("A.ok", problems[0])
        self.assertIn("A.none", problems[1])

    def test_a_name_that_appears_twice_must_fail_every_time(self) -> None:
        twice = [Case("A.p", FAILED, "x", ASSERTION), Case("A.p", PASSED)]
        problems, _ = expect_red(twice, ["A.p"])
        self.assertEqual(len(problems), 1)
        self.assertIn("passed", problems[0])


class SkippedDiffTest(unittest.TestCase):
    def test_nothing_changed_is_fine(self) -> None:
        self.assertEqual(skipped_diff([OK, BAD, SKIP], [OK, BAD, SKIP]), [])

    def test_a_test_that_ran_before_and_is_skipped_now_is_a_problem(self) -> None:
        problems = skipped_diff([OK, BAD], [Case("A.ok", SKIPPED), BAD])
        self.assertEqual(len(problems), 1)
        self.assertIn("A.ok", problems[0])
        self.assertIn("skipped now", problems[0])

    def test_a_new_test_that_is_skipped_at_once_is_a_problem(self) -> None:
        problems = skipped_diff([OK], [OK, SKIP])
        self.assertEqual(len(problems), 1)
        self.assertIn("A.skip", problems[0])
        self.assertIn("new", problems[0])

    def test_a_test_that_disappeared_is_a_problem(self) -> None:
        problems = skipped_diff([OK, BAD], [OK])
        self.assertEqual(len(problems), 1)
        self.assertIn("A.bad", problems[0])
        self.assertIn("gone", problems[0])

    def test_a_test_skipped_both_times_and_new_tests_that_run_are_fine(self) -> None:
        self.assertEqual(skipped_diff([SKIP], [SKIP, Case("A.new", PASSED)]), [])


class FailuresDiffTest(unittest.TestCase):
    def test_the_same_failures_twice_means_stuck(self) -> None:
        stuck, lines = failures_diff([OK, BAD], [OK, BAD])
        self.assertTrue(stuck)
        self.assertEqual(lines, ["still: A.bad"])

    def test_progress_lists_fixed_new_and_still(self) -> None:
        before = [Case("A.one", FAILED), Case("A.two", FAILED), OK]
        after = [Case("A.one", PASSED), Case("A.two", FAILED), Case("A.three", FAILED)]
        stuck, lines = failures_diff(before, after)
        self.assertFalse(stuck)
        self.assertEqual(lines, ["fixed: A.one", "still: A.two", "new: A.three"])

    def test_no_failures_at_all_is_not_stuck(self) -> None:
        self.assertEqual(failures_diff([OK], [OK]), (False, []))

    def test_fixing_everything_is_not_stuck(self) -> None:
        self.assertEqual(failures_diff([BAD], [OK]), (False, ["fixed: A.bad"]))


CONFIG = """# sketch config
tracker: github
tracker_cli: gh
default_branch: main
test_full: ./gradlew test
test_task: ./gradlew test --tests "{target}"
test_paths: [Tests/**]
test_format: junit-xml
test_results: build/test-results/**/*.xml
formats_dir: .sketch/formats

skills:
  common: []
"""


class SettingsTest(unittest.TestCase):
    def test_the_keys_are_read(self) -> None:
        settings = parse_settings(CONFIG)
        self.assertEqual(settings.test_full, "./gradlew test")
        self.assertEqual(settings.test_task, './gradlew test --tests "{target}"')
        self.assertEqual(settings.test_results, "build/test-results/**/*.xml")
        self.assertEqual(settings.test_format, "junit-xml")
        self.assertEqual(settings.formats_dir, ".sketch/formats")

    def test_a_key_that_is_not_there_is_none(self) -> None:
        settings = parse_settings("# sketch config\ntracker: github\n")
        self.assertEqual((settings.test_full, settings.test_task, settings.test_results,
                          settings.test_format, settings.formats_dir), (None, None, None, None, None))

    def test_an_empty_value_is_none_too(self) -> None:
        self.assertIsNone(parse_settings("# sketch config\nformats_dir: \n").formats_dir)

    def test_command_for_baseline_and_full_is_test_full(self) -> None:
        settings = parse_settings(CONFIG)
        self.assertEqual(command_for(settings, "baseline", None), "./gradlew test")
        self.assertEqual(command_for(settings, "full", None), "./gradlew test")

    def test_command_for_task_fills_in_the_target(self) -> None:
        settings = parse_settings(CONFIG)
        self.assertEqual(command_for(settings, "task", "BannerTests"), './gradlew test --tests "BannerTests"')

    def test_a_task_needs_a_target_and_a_mode_must_exist(self) -> None:
        settings = parse_settings(CONFIG)
        with self.assertRaises(UsageError):
            command_for(settings, "task", None)
        with self.assertRaises(UsageError):
            command_for(settings, "nightly", None)
        with self.assertRaises(UsageError):
            command_for(settings, "task", "two\nlines")

    def test_a_missing_command_or_placeholder_is_a_data_error_naming_the_key(self) -> None:
        with self.assertRaises(DataError) as ctx:
            command_for(parse_settings("# sketch config\n"), "full", None)
        self.assertIn("test_full", str(ctx.exception))
        with self.assertRaises(DataError) as ctx:
            command_for(parse_settings("# sketch config\n"), "task", "X")
        self.assertIn("test_task", str(ctx.exception))
        with self.assertRaises(DataError) as ctx:
            command_for(parse_settings("# sketch config\ntest_task: make test\n"), "task", "X")
        self.assertIn("{target}", str(ctx.exception))


class ResultsPatternTest(unittest.TestCase):
    def test_safe_patterns(self) -> None:
        for pattern in ("build/test-results/**/*.xml", "reports/junit.xml", "out/result.json", "r.xml"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(results_pattern_problem(pattern))

    def test_unsafe_patterns_say_why(self) -> None:
        for pattern, needle in (
            ("", "empty"), ("/etc/*.xml", "relative"), ("../x/*.xml", ".."), ("a/../../b.xml", ".."),
            ("build/*", ".xml or .json"), ("**", "folder"), ("out/", ".xml or .json"),
            ("build/*.txt", ".xml or .json"), ("~/r.xml", "relative"),
            ("*.xml", "folder"), ("**/*.json", "folder"), ("*/x.xml", "folder"), ("**/build/r.xml", "folder"),
            ("?uild/r.xml", "folder"), ("[bc]uild/r.xml", "folder"),
        ):
            with self.subTest(pattern=pattern):
                problem = results_pattern_problem(pattern)
                self.assertIsNotNone(problem)
                self.assertIn(needle, str(problem))


if __name__ == "__main__":
    unittest.main()
