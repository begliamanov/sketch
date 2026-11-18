"""repo-check: the pure checks, on the text git prints."""

import unittest
from typing import List

from sketch_tools.core.errors import UsageError
from sketch_tools.repo_check.globs import glob_to_regex
from sketch_tools.repo_check.logic import (
    check_changelog,
    check_commit_prefix,
    check_tests_unchanged,
    check_tree_clean,
)


def lines(*items: str) -> str:
    return "\n".join(items) + "\n"


class GlobTest(unittest.TestCase):
    def matches(self, pattern: str, path: str) -> bool:
        return glob_to_regex(pattern).fullmatch(path) is not None

    def test_double_star_crosses_folders(self) -> None:
        self.assertTrue(self.matches("Tests/**", "Tests/A.swift"))
        self.assertTrue(self.matches("Tests/**", "Tests/sub/dir/B.swift"))
        self.assertFalse(self.matches("Tests/**", "Sources/A.swift"))
        self.assertFalse(self.matches("Tests/**", "Tests"))

    def test_single_star_stays_in_one_folder(self) -> None:
        self.assertTrue(self.matches("*.py", "a.py"))
        self.assertFalse(self.matches("*.py", "pkg/a.py"))
        self.assertTrue(self.matches("tests/test_*.py", "tests/test_a.py"))
        self.assertFalse(self.matches("tests/test_*.py", "tests/sub/test_a.py"))

    def test_leading_double_star_slash_also_matches_no_folder(self) -> None:
        self.assertTrue(self.matches("**/*Test.kt", "FooTest.kt"))
        self.assertTrue(self.matches("**/*Test.kt", "src/test/FooTest.kt"))
        self.assertFalse(self.matches("**/*Test.kt", "src/Foo.kt"))

    def test_question_mark_is_one_non_slash_character(self) -> None:
        self.assertTrue(self.matches("a?.txt", "ab.txt"))
        self.assertFalse(self.matches("a?.txt", "a/.txt"))
        self.assertFalse(self.matches("a?.txt", "a.txt"))

    def test_everything_else_is_literal(self) -> None:
        self.assertTrue(self.matches("a.b", "a.b"))
        self.assertFalse(self.matches("a.b", "axb"))
        self.assertTrue(self.matches("Tests/(Foo)+[1].swift", "Tests/(Foo)+[1].swift"))
        self.assertFalse(self.matches("Tests/(Foo)+[1].swift", "Tests/Foo1.swift"))

    def test_the_whole_path_must_match(self) -> None:
        self.assertFalse(self.matches("Tests/*.swift", "xTests/A.swift"))
        self.assertFalse(self.matches("Tests/*.swift", "Tests/A.swift.bak"))


class CommitPrefixTest(unittest.TestCase):
    def test_task_story_and_wip_subjects_are_fine(self) -> None:
        text = lines("t-1: tests", "t-1: add banner", "t-3: [wip] interrupted, not reviewed",
                     "story-2: glossary", "t-12: ten and more")
        self.assertEqual(check_commit_prefix(text), [])

    def test_blank_lines_and_empty_input_are_fine(self) -> None:
        self.assertEqual(check_commit_prefix(""), [])
        self.assertEqual(check_commit_prefix("\n\n  \n"), [])

    def test_a_subject_without_a_prefix_is_reported_with_the_subject(self) -> None:
        problems = check_commit_prefix(lines("t-1: ok", "fix typo"))
        self.assertEqual(len(problems), 1)
        self.assertIn('"fix typo"', problems[0])
        self.assertIn("no task prefix", problems[0])

    def test_near_misses_are_reported(self) -> None:
        for bad in ("T-1: x", "t-1 x", "t-1:", "t-1:x", "t-: x", "story: x", " t-1: x",
                    "task-1: x", "t-1 : x"):
            with self.subTest(subject=bad):
                self.assertEqual(len(check_commit_prefix(lines(bad))), 1)

    def test_every_bad_subject_is_reported_once(self) -> None:
        self.assertEqual(len(check_commit_prefix(lines("a", "t-1: ok", "b", "c"))), 3)

    def test_with_a_task_only_that_prefix_passes(self) -> None:
        self.assertEqual(check_commit_prefix(lines("t-3: tests", "t-3: [wip] x"), task="t-3"), [])
        problems = check_commit_prefix(lines("t-3: ok", "t-2: add banner"), task="t-3")
        self.assertEqual(len(problems), 1)
        self.assertIn('"t-2: add banner"', problems[0])
        self.assertIn("t-3", problems[0])

    def test_t_1_is_not_t_10(self) -> None:
        self.assertEqual(len(check_commit_prefix(lines("t-10: x"), task="t-1")), 1)
        self.assertEqual(len(check_commit_prefix(lines("t-1: x"), task="t-10")), 1)

    # Criterion 1 (t-4): a task range may contain story-end fix commits.
    def test_a_story_end_fix_commit_passes_in_a_task_range(self) -> None:
        text = lines("t-3: tests", "story-2: fix the changelog line", "t-3: [wip] x")
        self.assertEqual(check_commit_prefix(text, task="t-3"), [])

    def test_a_task_range_of_only_story_end_fix_commits_passes(self) -> None:
        self.assertEqual(check_commit_prefix(lines("story-12: fix", "story-2: fix"), task="t-3"), [])

    # Criterion 2 (plain task commits pass) is already covered, and green today, by
    # test_with_a_task_only_that_prefix_passes above.

    # Criterion 3: other or missing prefixes still fail, with today's messages.
    def test_a_commit_without_a_prefix_still_fails_next_to_a_story_end_fix(self) -> None:
        problems = check_commit_prefix(lines("story-2: fix", "fix typo", "t-3: ok"), task="t-3")
        self.assertEqual(problems, ['"fix typo" has no t-3: prefix'])

    def test_another_task_prefix_still_fails_next_to_a_story_end_fix(self) -> None:
        problems = check_commit_prefix(lines("story-2: fix", "t-2: add banner"), task="t-3")
        self.assertEqual(problems, ['"t-2: add banner" is not t-3'])

    def test_a_malformed_story_prefix_fails(self) -> None:
        # Addition: the valid story-2 line makes this red until story prefixes are accepted.
        for bad in ("story2: fix", "story-: fix", "story-2:fix", "Story-2: fix", "story-x: fix"):
            with self.subTest(subject=bad):
                problems = check_commit_prefix(lines("story-2: fix", bad), task="t-3")
                self.assertEqual(problems, ['"' + bad + '" has no t-3: prefix'])

    def test_a_bad_task_argument_is_a_usage_error(self) -> None:
        for bad in ("t3", "story-2", "", "T-1"):
            with self.subTest(task=bad):
                with self.assertRaises(UsageError):
                    check_commit_prefix(lines("t-1: x"), task=bad)


class TestsUnchangedTest(unittest.TestCase):
    def test_reports_each_changed_test_file(self) -> None:
        problems = check_tests_unchanged(
            lines("Sources/A.swift", "Tests/NoteListTests.swift", "Tests/sub/B.swift"), ["Tests/**"]
        )
        self.assertEqual(len(problems), 2)
        self.assertIn("Tests/NoteListTests.swift", problems[0])
        self.assertIn("changed after the red-test commit", problems[0])
        self.assertIn("Tests/sub/B.swift", problems[1])

    def test_no_changed_test_file_is_ok(self) -> None:
        self.assertEqual(check_tests_unchanged(lines("Sources/A.swift", "README.md"), ["Tests/**"]), [])
        self.assertEqual(check_tests_unchanged("", ["Tests/**"]), [])
        self.assertEqual(check_tests_unchanged("\n  \n", ["Tests/**"]), [])

    def test_any_of_several_patterns_counts(self) -> None:
        patterns = ["Tests/**", "**/*Test.kt", "tests/test_*.py"]
        problems = check_tests_unchanged(
            lines("Tests/a", "src/FooTest.kt", "tests/test_x.py", "src/Foo.kt"), patterns
        )
        self.assertEqual(len(problems), 3)

    def test_a_file_matching_two_patterns_is_reported_once(self) -> None:
        problems = check_tests_unchanged(lines("Tests/A.swift"), ["Tests/**", "**/*.swift"])
        self.assertEqual(len(problems), 1)

    def test_no_pattern_is_a_usage_error(self) -> None:
        with self.assertRaises(UsageError):
            check_tests_unchanged(lines("Tests/a"), [])


def diff(*body: str) -> str:
    head = ["diff --git a/CHANGELOG.md b/CHANGELOG.md", "index 111..222 100644",
            "--- a/CHANGELOG.md", "+++ b/CHANGELOG.md", "@@ -1,9 +1,10 @@"]
    return "\n".join(head + list(body)) + "\n"


BASE = [" # Changelog", " ", " Sketch follows semver.", " ", " ## Unreleased"]
TAIL = [" ", " ## 0.1.0", " ", " - Old thing (#99)"]


class ChangelogTest(unittest.TestCase):
    def problems(self, text: str, issue: str = "123") -> List[str]:
        return check_changelog(text, issue)

    def assert_problem(self, text: str, *needles: str) -> None:
        found = self.problems(text)
        self.assertTrue(any(all(n in p for n in needles) for p in found), found)

    def test_one_new_list_item_under_unreleased_ending_in_the_issue_is_ok(self) -> None:
        text = diff(*BASE, "+- Add streaming CSV export endpoint (#123)", *TAIL)
        self.assertEqual(self.problems(text), [])

    def test_a_new_line_after_existing_unreleased_lines_is_ok(self) -> None:
        text = diff(*BASE, " - Earlier entry (#100)", "+- Add export (#123)", *TAIL)
        self.assertEqual(self.problems(text), [])

    def test_trailing_spaces_are_ignored(self) -> None:
        self.assertEqual(self.problems(diff(*BASE, "+- Add export (#123)  ", *TAIL)), [])

    def test_no_added_line_is_reported(self) -> None:
        self.assert_problem(diff(*BASE, *TAIL), "no new line under Unreleased")
        self.assert_problem("", "no new line under Unreleased")

    def test_a_line_under_another_heading_is_not_under_unreleased(self) -> None:
        text = diff(*BASE, *TAIL, "+- Sneaky (#123)")
        self.assert_problem(text, "not under Unreleased", "Sneaky")

    def test_two_new_lines_are_reported(self) -> None:
        text = diff(*BASE, "+- One (#123)", "+- Two (#123)", *TAIL)
        self.assert_problem(text, "expected one new line", "2")

    def test_a_line_without_the_issue_number_is_reported(self) -> None:
        self.assert_problem(diff(*BASE, "+- Add export", *TAIL), "does not end with (#123)")
        self.assert_problem(diff(*BASE, "+- Add export (#124)", *TAIL), "does not end with (#123)")
        self.assert_problem(diff(*BASE, "+- Add export #123", *TAIL), "does not end with (#123)")
        self.assert_problem(diff(*BASE, "+- Add export (#1234)", *TAIL), "does not end with (#123)")

    def test_a_line_that_is_not_a_list_item_is_reported(self) -> None:
        self.assert_problem(diff(*BASE, "+Add export (#123)", *TAIL), "not a list item")

    def test_the_file_header_lines_are_not_counted_as_added_lines(self) -> None:
        # "+++ b/CHANGELOG.md" is in the header of every diff and must not count.
        self.assertEqual(self.problems(diff(*BASE, "+- Add export (#123)", *TAIL)), [])

    def test_a_diff_that_does_not_show_the_heading_is_an_error_not_a_guess(self) -> None:
        text = diff(" - Earlier entry (#100)", "+- Add export (#123)", " ")
        self.assert_problem(text, "Unreleased heading", "-U99999")

    def test_a_heading_added_in_the_same_diff_is_recognized(self) -> None:
        text = diff("+## Unreleased", "+- Add export (#123)", " ", " ## 0.1.0")
        self.assertEqual(self.problems(text), [])

    def test_the_issue_must_be_digits(self) -> None:
        for bad in ("abc", "#123", "", "12 3"):
            with self.subTest(issue=bad):
                with self.assertRaises(UsageError):
                    check_changelog(diff(*BASE, "+- x (#1)", *TAIL), bad)


class TreeCleanTest(unittest.TestCase):
    def test_an_empty_status_is_clean(self) -> None:
        self.assertEqual(check_tree_clean(""), [])
        self.assertEqual(check_tree_clean("\n \n"), [])

    def test_every_dirty_and_untracked_path_is_reported(self) -> None:
        problems = check_tree_clean(" M Sources/NoteList.swift\n?? Tests/NewTests.swift\nA  new.txt\n")
        self.assertEqual(len(problems), 3)
        self.assertIn("M Sources/NoteList.swift", problems[0])
        self.assertIn("?? Tests/NewTests.swift", problems[1])
        self.assertIn("A  new.txt", problems[2])
        for problem in problems:
            self.assertTrue(problem.startswith("dirty: "))


if __name__ == "__main__":
    unittest.main()
