"""tests failures / summary / classify / expect-red / skipped-diff / failures-diff, on result folders."""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.tests import main

from tests.helpers import run_tool

FIXTURES = Path(__file__).parent / "fixtures"
SWIFTPM = (FIXTURES / "junit_swiftpm.xml").read_text()
BAD = "DemoTests.DemoTests.testDoublesZeroWrongly"
GOOD = "DemoTests.DemoTests.testDoublesAPositiveNumber"

ALL_PASS = """<testsuites><testsuite name="T" tests="2" failures="0">
<testcase classname="DemoTests.DemoTests" name="testDoublesAPositiveNumber"/>
<testcase classname="DemoTests.DemoTests" name="testDoublesZeroWrongly"/>
</testsuite></testsuites>"""

ONE_SKIPPED = """<testsuites><testsuite name="T" tests="2">
<testcase classname="DemoTests.DemoTests" name="testDoublesAPositiveNumber"><skipped/></testcase>
<testcase classname="DemoTests.DemoTests" name="testDoublesZeroWrongly"><failure message="failure"/></testcase>
</testsuite></testsuites>"""

WITH_ERROR = """<testsuite><testcase classname="C" name="boom"><error message="ImportError: nope" type="ImportError"/></testcase></testsuite>"""

CONFIG = "# sketch config\ntest_format: junit-xml\n"


class AnalysisCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.config = self.base / "config.md"
        self.config.write_text(CONFIG)

    def results(self, name: str, **files: str) -> Path:
        folder = self.base / name
        folder.mkdir()
        for filename, text in files.items():
            (folder / filename).write_text(text)
        return folder

    def run_it(self, command: str, *extra: str):
        return run_tool(main, [command, "--config", str(self.config), *extra])


class FailuresAndSummaryTest(AnalysisCase):
    def test_failures_prints_name_and_first_line_of_the_message(self) -> None:
        folder = self.results("r", **{"001-a.xml": SWIFTPM})
        self.assertEqual(self.run_it("failures", "--results", str(folder)), (0, BAD + ": failure\n", ""))

    def test_no_failures_prints_nothing(self) -> None:
        folder = self.results("r", **{"001-a.xml": ALL_PASS})
        self.assertEqual(self.run_it("failures", "--results", str(folder)), (0, "", ""))

    def test_a_failure_without_a_message_prints_just_the_name(self) -> None:
        folder = self.results("r", **{"001-a.xml": "<testsuite><testcase classname='C' name='t'><failure/></testcase></testsuite>"})
        self.assertEqual(self.run_it("failures", "--results", str(folder))[1], "C.t\n")

    def test_summary(self) -> None:
        folder = self.results("r", **{"001-a.xml": SWIFTPM})
        self.assertEqual(self.run_it("summary", "--results", str(folder)), (0, "passed 2\nfailed 1\nskipped 0\n", ""))
        code, out, _ = self.run_it("summary", "--results", str(folder), "--json")
        self.assertEqual((code, json.loads(out)), (0, {"counts": {"passed": 2, "failed": 1, "skipped": 0}}))

    def test_several_files_are_read_together_in_name_order(self) -> None:
        folder = self.results("r", **{"001-a.xml": ALL_PASS, "002-b.xml": SWIFTPM})
        self.assertEqual(self.run_it("summary", "--results", str(folder))[1], "passed 4\nfailed 1\nskipped 0\n")


class ClassifyCliTest(AnalysisCase):
    def test_pass(self) -> None:
        folder = self.results("r", **{"001-a.xml": ALL_PASS})
        self.assertEqual(self.run_it("classify", "--results", str(folder), "--exit", "0"), (0, "PASS\n", ""))

    def test_fail_says_how_many(self) -> None:
        folder = self.results("r", **{"001-a.xml": SWIFTPM})
        code, out, _ = self.run_it("classify", "--results", str(folder), "--exit", "1")
        self.assertEqual((code, out), (1, "FAIL\nreason: 1 failing test\n"))

    def test_cannot_run_and_unknown_say_why(self) -> None:
        empty = self.results("empty")
        code, out, _ = self.run_it("classify", "--results", str(empty), "--exit", "0")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("CANNOT RUN\nreason: "))
        code, out, _ = self.run_it("classify", "--results", str(empty), "--exit", "65")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("UNKNOWN\nreason: "))
        self.assertIn("exit 65", out)

    def test_an_empty_junit_file_means_nothing_ran(self) -> None:
        folder = self.results("r", **{"001-a.xml": (FIXTURES / "junit_empty.xml").read_text()})
        code, out, _ = self.run_it("classify", "--results", str(folder), "--exit", "0")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("CANNOT RUN\n"))
        self.assertIn("nothing ran", out)

    def test_the_exit_code_is_required_and_a_number(self) -> None:
        folder = self.results("r")
        self.assertEqual(self.run_it("classify", "--results", str(folder))[0], 3)
        self.assertEqual(self.run_it("classify", "--results", str(folder), "--exit", "x")[0], 3)


class ExpectRedCliTest(AnalysisCase):
    def test_a_test_that_failed_is_ok(self) -> None:
        folder = self.results("r", **{"001-a.xml": SWIFTPM})
        self.assertEqual(self.run_it("expect-red", "--results", str(folder), "--test", BAD), (0, "ok\n", ""))

    def test_problems_are_errors_and_exit_1(self) -> None:
        folder = self.results("r", **{"001-a.xml": SWIFTPM})
        code, out, _ = self.run_it("expect-red", "--results", str(folder), "--test", BAD, "--test", GOOD, "--test", "Nope.nope")
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line.startswith("error: ") for line in lines))
        self.assertIn(GOOD, lines[0])
        self.assertIn("Nope.nope", lines[1])

    def test_a_failure_by_error_is_a_review_line_and_does_not_fail_the_check(self) -> None:
        folder = self.results("r", **{"001-a.xml": WITH_ERROR})
        code, out, _ = self.run_it("expect-red", "--results", str(folder), "--test", "C.boom")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("review: C.boom"))
        self.assertIn("ImportError: nope", out)

    def test_at_least_one_test_is_required(self) -> None:
        folder = self.results("r")
        code, _, err = self.run_it("expect-red", "--results", str(folder))
        self.assertEqual(code, 3)
        self.assertIn("--test", err)


class DiffCliTest(AnalysisCase):
    def run_diff(self, command: str, before: Path, after: Path):
        return self.run_it(command, "--before", str(before), "--after", str(after))

    def test_skipped_diff_ok_and_problem(self) -> None:
        before = self.results("before", **{"001-a.xml": SWIFTPM})
        same = self.results("same", **{"001-a.xml": SWIFTPM})
        skipped = self.results("skipped", **{"001-a.xml": ONE_SKIPPED})
        self.assertEqual(self.run_diff("skipped-diff", before, same), (0, "ok\n", ""))
        code, out, _ = self.run_diff("skipped-diff", before, skipped)
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("error: "))
        self.assertIn(GOOD, out)

    def test_failures_diff_stuck(self) -> None:
        before = self.results("before", **{"001-a.xml": SWIFTPM})
        after = self.results("after", **{"001-a.xml": SWIFTPM})
        self.assertEqual(self.run_diff("failures-diff", before, after), (1, "same\nstill: " + BAD + "\n", ""))

    def test_failures_diff_progress(self) -> None:
        before = self.results("before", **{"001-a.xml": SWIFTPM})
        after = self.results("after", **{"001-a.xml": ALL_PASS})
        self.assertEqual(self.run_diff("failures-diff", before, after), (0, "progress\nfixed: " + BAD + "\n", ""))

    def test_no_failures_either_time_is_progress_not_stuck(self) -> None:
        a = self.results("a", **{"001-a.xml": ALL_PASS})
        b = self.results("b", **{"001-a.xml": ALL_PASS})
        self.assertEqual(self.run_diff("failures-diff", a, b), (0, "progress\n", ""))

    def test_both_folders_are_required(self) -> None:
        folder = self.results("r")
        self.assertEqual(self.run_it("failures-diff", "--before", str(folder))[0], 3)


class FormatAndFolderTest(AnalysisCase):
    def test_a_missing_results_folder_exits_3(self) -> None:
        code, out, err = self.run_it("summary", "--results", str(self.base / "nope"))
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope", err)

    def test_an_empty_results_folder_is_fine(self) -> None:
        folder = self.results("empty")
        self.assertEqual(self.run_it("summary", "--results", str(folder))[1], "passed 0\nfailed 0\nskipped 0\n")

    def test_a_missing_or_unknown_format_is_reported(self) -> None:
        folder = self.results("r")
        self.config.write_text("# sketch config\n")
        code, _, err = self.run_it("summary", "--results", str(folder))
        self.assertEqual(code, 1)
        self.assertIn("test_format", err)
        self.config.write_text("# sketch config\ntest_format: vitest\n")
        code, _, err = self.run_it("summary", "--results", str(folder))
        self.assertEqual(code, 3)
        for name in ("vitest", "junit-xml", "xcresult-json"):
            self.assertIn(name, err)

    def test_the_xcresult_format_reads_xcresulttool_json(self) -> None:
        self.config.write_text("# sketch config\ntest_format: xcresult-json\n")
        folder = self.results("r", **{"001-r.json": (FIXTURES / "xcresult_tests.json").read_text()})
        self.assertEqual(self.run_it("summary", "--results", str(folder))[1], "passed 1\nfailed 1\nskipped 1\n")
        code, out, _ = self.run_it("classify", "--results", str(folder), "--exit", "65")
        self.assertEqual((code, out), (1, "FAIL\nreason: 1 failing test\n"))

    def test_a_file_the_reader_cannot_read_is_an_error_naming_the_file(self) -> None:
        folder = self.results("r", **{"001-a.xml": "not xml at all"})
        code, out, err = self.run_it("summary", "--results", str(folder))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("001-a.xml", err)

    def test_a_project_reader_from_formats_dir_is_used(self) -> None:
        plugins = self.base / "formats"
        plugins.mkdir()
        (plugins / "plain.py").write_text(
            "from sketch_tools.tests.model import Case, FAILED, PASSED\n"
            'FORMAT = "plain"\n'
            "def read(text):\n"
            "    return [Case(l[2:], PASSED if l.startswith('+ ') else FAILED) for l in text.splitlines() if l]\n"
        )
        self.config.write_text("# sketch config\ntest_format: plain\nformats_dir: %s\n" % plugins)
        folder = self.results("r", **{"001-a.txt": "+ fine\n- broken\n"})
        self.assertEqual(self.run_it("failures", "--results", str(folder))[1], "broken\n")
        self.assertEqual(self.run_it("summary", "--results", str(folder))[1], "passed 1\nfailed 1\nskipped 0\n")

    def test_the_config_is_required_and_must_exist(self) -> None:
        folder = self.results("r")
        self.assertEqual(run_tool(main, ["summary", "--results", str(folder)])[0], 3)
        code, _, err = run_tool(main, ["summary", "--config", str(self.base / "no.md"), "--results", str(folder)])
        self.assertEqual(code, 3)
        self.assertIn("no.md", err)


if __name__ == "__main__":
    unittest.main()
