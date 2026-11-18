"""repo-check: the command-line behavior, with the text piped in on stdin."""

import unittest

from sketch_tools.repo_check import main

from tests.helpers import run_tool

CHANGELOG_OK = (
    "diff --git a/CHANGELOG.md b/CHANGELOG.md\n--- a/CHANGELOG.md\n+++ b/CHANGELOG.md\n"
    "@@ -1,3 +1,4 @@\n # Changelog\n \n ## Unreleased\n+- Add export (#123)\n"
)


class CommitPrefixCliTest(unittest.TestCase):
    def test_ok(self) -> None:
        code, out, err = run_tool(main, ["commit-prefix"], stdin="t-1: tests\nt-1: code\n")
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_problems_go_to_stdout_one_per_line_and_exit_1(self) -> None:
        code, out, err = run_tool(main, ["commit-prefix"], stdin="fix typo\nt-1: ok\nother\n")
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line.startswith("error: ") for line in lines))

    def test_the_task_option(self) -> None:
        code, out, _ = run_tool(main, ["commit-prefix", "--task", "t-3"], stdin="t-3: a\nt-2: b\n")
        self.assertEqual(code, 1)
        self.assertIn("t-2: b", out)

    def test_the_task_option_accepts_a_story_end_fix_commit(self) -> None:
        code, out, err = run_tool(main, ["commit-prefix", "--task", "t-3"],
                                  stdin="t-3: a\nstory-2: fix\n")
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_a_bad_task_exits_3(self) -> None:
        code, out, err = run_tool(main, ["commit-prefix", "--task", "t3"], stdin="t-1: x\n")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("task", err)


class TestsUnchangedCliTest(unittest.TestCase):
    def test_ok_when_no_test_file_changed(self) -> None:
        code, out, _ = run_tool(main, ["tests-unchanged", "--tests", "Tests/**"], stdin="Sources/A.swift\n")
        self.assertEqual((code, out), (0, "ok\n"))

    def test_a_changed_test_file_exits_1_and_is_named(self) -> None:
        code, out, _ = run_tool(
            main, ["tests-unchanged", "--tests", "Tests/**"], stdin="Tests/NoteListTests.swift\n"
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            out, "error: Tests/NoteListTests.swift changed after the red-test commit\n"
        )

    def test_the_option_can_be_repeated(self) -> None:
        argv = ["tests-unchanged", "--tests", "Tests/**", "--tests", "**/*Test.kt"]
        code, out, _ = run_tool(main, argv, stdin="a/FooTest.kt\n")
        self.assertEqual(code, 1)
        self.assertIn("a/FooTest.kt", out)

    def test_without_a_pattern_exits_3(self) -> None:
        code, out, err = run_tool(main, ["tests-unchanged"], stdin="Tests/a\n")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("--tests", err)


class ChangelogCliTest(unittest.TestCase):
    def test_ok(self) -> None:
        code, out, _ = run_tool(main, ["changelog", "--issue", "123"], stdin=CHANGELOG_OK)
        self.assertEqual((code, out), (0, "ok\n"))

    def test_the_wrong_issue_exits_1(self) -> None:
        code, out, _ = run_tool(main, ["changelog", "--issue", "124"], stdin=CHANGELOG_OK)
        self.assertEqual(code, 1)
        self.assertIn("does not end with (#124)", out)

    def test_the_issue_is_required_and_must_be_digits(self) -> None:
        code, _, err = run_tool(main, ["changelog"], stdin=CHANGELOG_OK)
        self.assertEqual(code, 3)
        self.assertIn("--issue", err)
        code, _, _ = run_tool(main, ["changelog", "--issue", "abc"], stdin=CHANGELOG_OK)
        self.assertEqual(code, 3)


class TreeCleanCliTest(unittest.TestCase):
    def test_clean(self) -> None:
        code, out, _ = run_tool(main, ["tree-clean"], stdin="")
        self.assertEqual((code, out), (0, "ok\n"))

    def test_dirty_files_are_listed_and_exit_1(self) -> None:
        code, out, _ = run_tool(main, ["tree-clean"], stdin=" M a.swift\n?? b.swift\n")
        self.assertEqual(code, 1)
        self.assertEqual(out, "error: dirty: M a.swift\nerror: dirty: ?? b.swift\n")


if __name__ == "__main__":
    unittest.main()
