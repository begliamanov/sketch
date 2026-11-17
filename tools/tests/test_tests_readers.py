"""tests: the readers (junit-xml, xcresult-json) and the project-local plugin loader.

The two fixtures `junit_swiftpm.xml` / `junit_empty.xml` and `xcresult_tests.json` are real output
of `swift test --parallel --xunit-output` and of `xcodebuild test` + `xcresulttool` (Xcode 26.2) on
a package with one passing, one failing and one skipped test. The inline XML and JSON below are
hand-written to the formats' shapes, for cases a real run did not produce."""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.tests.model import ASSERTION, ERROR, FAILED, PASSED, SKIPPED, Case
from sketch_tools.tests.readers import BUILTIN, BUILTIN_NAMES, get_reader, load_plugins
from sketch_tools.tests.readers.junit import read as read_junit
from sketch_tools.tests.readers.xcresult import read as read_xcresult

FIXTURES = Path(__file__).parent / "fixtures"


class JunitRealFilesTest(unittest.TestCase):
    def test_swiftpm_output(self) -> None:
        cases = read_junit((FIXTURES / "junit_swiftpm.xml").read_text())
        self.assertEqual(cases, [
            Case("DemoTests.DemoTests.testSkippedOnPurpose", PASSED),
            Case("DemoTests.DemoTests.testDoublesAPositiveNumber", PASSED),
            Case("DemoTests.DemoTests.testDoublesZeroWrongly", FAILED, "failure", ASSERTION),
        ])

    def test_a_run_with_no_tests_is_an_empty_list_not_an_error(self) -> None:
        self.assertEqual(read_junit((FIXTURES / "junit_empty.xml").read_text()), [])


GRADLE_LIKE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.BannerTests" tests="4" skipped="1" failures="1" errors="1" timestamp="2026-11-17T10:00:00" time="0.4">
  <testcase name="shows the banner offline()" classname="com.example.BannerTests" time="0.1"/>
  <testcase name="hides the banner online()" classname="com.example.BannerTests" time="0.1">
    <failure message="expected:&lt;true&gt; but was:&lt;false&gt;" type="org.opentest4j.AssertionFailedError">org.opentest4j.AssertionFailedError: expected
    at com.example.BannerTests.hides(BannerTests.kt:12)</failure>
  </testcase>
  <testcase name="loads from cache()" classname="com.example.BannerTests" time="0.1">
    <error message="boom" type="java.lang.IllegalStateException">java.lang.IllegalStateException: boom</error>
  </testcase>
  <testcase name="needs a device()" classname="com.example.BannerTests" time="0.0">
    <skipped/>
  </testcase>
</testsuite>
"""


class JunitHandWrittenTest(unittest.TestCase):
    def test_gradle_shaped_file(self) -> None:
        self.assertEqual(read_junit(GRADLE_LIKE), [
            Case("com.example.BannerTests.shows the banner offline()", PASSED),
            Case("com.example.BannerTests.hides the banner online()", FAILED,
                 "expected:<true> but was:<false>", ASSERTION),
            Case("com.example.BannerTests.loads from cache()", FAILED, "boom", ERROR),
            Case("com.example.BannerTests.needs a device()", SKIPPED),
        ])

    def test_a_skip_reason_becomes_the_message(self) -> None:
        text = '<testsuite><testcase name="t" classname="C"><skipped message="no device"/></testcase></testsuite>'
        self.assertEqual(read_junit(text), [Case("C.t", SKIPPED, "no device")])

    def test_without_a_message_attribute_the_first_line_of_the_text_is_used(self) -> None:
        text = '<testsuite><testcase name="t" classname="C"><failure>\n\n  first line\nsecond</failure></testcase></testsuite>'
        self.assertEqual(read_junit(text), [Case("C.t", FAILED, "first line", ASSERTION)])

    def test_a_failure_with_nothing_to_say_has_an_empty_message(self) -> None:
        text = '<testsuite><testcase name="t" classname="C"><failure/></testcase></testsuite>'
        self.assertEqual(read_junit(text), [Case("C.t", FAILED, "", ASSERTION)])

    def test_a_case_without_a_class_is_named_by_its_name(self) -> None:
        self.assertEqual(read_junit('<testsuite><testcase name="plain"/></testsuite>'), [Case("plain", PASSED)])
        self.assertEqual(read_junit('<testsuite><testcase name="plain" classname=""/></testsuite>'), [Case("plain", PASSED)])

    def test_testsuites_and_nested_suites_are_all_read_in_order(self) -> None:
        text = ('<testsuites><testsuite name="a"><testcase name="one" classname="A"/>'
                '<testsuite name="inner"><testcase name="two" classname="A"/></testsuite></testsuite>'
                '<testsuite name="b"><testcase name="three" classname="B"/></testsuite></testsuites>')
        self.assertEqual([c.name for c in read_junit(text)], ["A.one", "A.two", "B.three"])

    def test_a_file_that_is_not_junit_is_a_value_error(self) -> None:
        for bad in ("", "not xml", "<html><body/></html>", "<testsuite>", "{}"):
            with self.subTest(text=bad):
                with self.assertRaises(ValueError):
                    read_junit(bad)

    def test_a_case_without_a_name_is_a_value_error(self) -> None:
        with self.assertRaises(ValueError):
            read_junit("<testsuite><testcase classname='C'/></testsuite>")


class XcresultRealFileTest(unittest.TestCase):
    def test_xcresulttool_output(self) -> None:
        cases = read_xcresult((FIXTURES / "xcresult_tests.json").read_text())
        self.assertEqual(cases, [
            Case("DemoTests/testDoublesAPositiveNumber()", PASSED),
            Case("DemoTests/testDoublesZeroWrongly()", FAILED,
                 'DemoTests.swift:10: XCTAssertEqual failed: ("0") is not equal to ("1") - zero doubled should be 1 (wrong on purpose)'),
            Case("DemoTests/testSkippedOnPurpose()", SKIPPED, "Test skipped - skipped on purpose"),
        ])


def tree(*cases: dict) -> str:
    return json.dumps({"testNodes": [{"nodeType": "Test Plan", "name": "P", "children": [
        {"nodeType": "Unit test bundle", "name": "B", "children": [
            {"nodeType": "Test Suite", "name": "S", "children": list(cases)}]}]}]})


def case(name: str, result: str, identifier: str = "", *messages: str) -> dict:
    node = {"nodeType": "Test Case", "name": name, "result": result,
            "children": [{"nodeType": "Failure Message", "name": m} for m in messages]}
    if identifier:
        node["nodeIdentifier"] = identifier
    return node


class XcresultHandWrittenTest(unittest.TestCase):
    def test_the_results(self) -> None:
        text = tree(case("a()", "Passed", "S/a()"), case("b()", "Failed", "S/b()", "first", "second"),
                    case("c()", "Skipped", "S/c()", "why"), case("d()", "Expected Failure", "S/d()"))
        self.assertEqual(read_xcresult(text), [
            Case("S/a()", PASSED), Case("S/b()", FAILED, "first"), Case("S/c()", SKIPPED, "why"),
            Case("S/d()", PASSED),
        ])

    def test_a_case_without_an_identifier_is_named_by_its_name(self) -> None:
        self.assertEqual(read_xcresult(tree(case("a()", "Passed"))), [Case("a()", PASSED)])

    def test_cases_are_found_at_any_depth(self) -> None:
        deep = {"nodeType": "Test Suite", "name": "Inner", "children": [case("x()", "Passed", "In/x()")]}
        self.assertEqual([c.name for c in read_xcresult(tree(deep, case("y()", "Passed", "S/y()")))], ["In/x()", "S/y()"])

    def test_a_result_it_does_not_know_is_a_value_error_naming_the_test(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            read_xcresult(tree(case("a()", "Mystery", "S/a()")))
        self.assertIn("S/a()", str(ctx.exception))
        self.assertIn("Mystery", str(ctx.exception))

    def test_a_file_that_is_not_xcresulttool_json_is_a_value_error(self) -> None:
        for bad in ("", "not json", "[]", "{}", '{"testNodes": "x"}'):
            with self.subTest(text=bad):
                with self.assertRaises(ValueError):
                    read_xcresult(bad)

    def test_a_run_with_no_cases_is_an_empty_list(self) -> None:
        self.assertEqual(read_xcresult(tree()), [])


PLUGIN = '''from typing import List

from sketch_tools.tests.model import Case, FAILED, PASSED

FORMAT = "plain"


def read(text: str) -> List[Case]:
    return [Case(line[2:], PASSED if line.startswith("+ ") else FAILED) for line in text.splitlines() if line]
'''


class PluginsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, name: str, text: str) -> None:
        (self.dir / name).write_text(text)

    def test_the_built_in_formats(self) -> None:
        self.assertEqual(list(BUILTIN_NAMES), ["junit-xml", "xcresult-json"])
        self.assertEqual(set(BUILTIN), {"junit-xml", "xcresult-json"})

    def test_a_project_reader_is_loaded_and_works(self) -> None:
        self.write("plain.py", PLUGIN)
        plugins = load_plugins(self.dir)
        self.assertEqual(list(plugins), ["plain"])
        self.assertEqual(plugins["plain"]("+ ok one\n- bad two\n"), [Case("ok one", PASSED), Case("bad two", FAILED)])

    def test_files_that_are_not_readers_are_left_alone(self) -> None:
        self.write("_helper.py", "raise RuntimeError('must not be run')")
        self.write("notes.txt", "x")
        (self.dir / "sub").mkdir()
        self.assertEqual(load_plugins(self.dir), {})

    def test_a_folder_that_does_not_exist_is_a_usage_error(self) -> None:
        with self.assertRaises(UsageError):
            load_plugins(self.dir / "nope")

    def test_a_broken_reader_is_a_data_error_naming_the_file(self) -> None:
        for name, text, needle in (
            ("syntax.py", "def (:\n", "syntax.py"),
            ("noformat.py", "def read(text):\n    return []\n", "FORMAT"),
            ("noread.py", 'FORMAT = "x"\n', "read"),
            ("badname.py", 'FORMAT = ""\ndef read(text):\n    return []\n', "FORMAT"),
        ):
            with self.subTest(file=name):
                self.write(name, text)
                with self.assertRaises(DataError) as ctx:
                    load_plugins(self.dir)
                self.assertIn(needle, str(ctx.exception))
                (self.dir / name).unlink()

    def test_a_reader_may_not_take_a_built_in_name_or_repeat_a_name(self) -> None:
        self.write("a.py", PLUGIN.replace('"plain"', '"junit-xml"'))
        with self.assertRaises(DataError) as ctx:
            load_plugins(self.dir)
        self.assertIn("junit-xml", str(ctx.exception))
        (self.dir / "a.py").unlink()
        self.write("one.py", PLUGIN)
        self.write("two.py", PLUGIN)
        with self.assertRaises(DataError) as ctx:
            load_plugins(self.dir)
        self.assertIn("plain", str(ctx.exception))

    def test_get_reader_finds_built_in_and_project_formats_or_lists_the_known_ones(self) -> None:
        self.write("plain.py", PLUGIN)
        plugins = load_plugins(self.dir)
        self.assertIs(get_reader("junit-xml", plugins), BUILTIN["junit-xml"])
        self.assertIs(get_reader("plain", plugins), plugins["plain"])
        with self.assertRaises(UsageError) as ctx:
            get_reader("vitest", plugins)
        message = str(ctx.exception)
        for name in ("vitest", "junit-xml", "xcresult-json", "plain"):
            self.assertIn(name, message)


if __name__ == "__main__":
    unittest.main()
