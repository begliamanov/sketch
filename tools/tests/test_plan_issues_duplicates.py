"""plan issues-todo: duplicates are errors, a clean answer exits 0 (t-4).

Two issues that match one task (or the story) cannot be told apart, so the tool reports
"more than one issue for t-<n>: #a and #b" (the story issue: "... for the story: ...") and exits 1.
An answer made only of have/todo lines is clean and exits 0, even when something is todo.
core/orchestrator.md and core/agents/task-writer.md describe the matching and the exit codes.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from sketch_tools.plan import main

from tests.helpers import run_tool
from tests.test_plan_tasks import VALID as TASKS  # story 2: Offline notes list, t-1 to t-4

ROOT = Path(__file__).resolve().parents[2]
STORY = {"number": 120, "title": "Story 2: Offline notes list"}


class IssuesTodoCliCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tasks = Path(tmp.name) / "tasks.md"
        self.tasks.write_text(TASKS)

    def ask(self, issues: List[Dict[str, Any]]) -> Any:
        facts = {"issues": issues, "links": []}
        return run_tool(main, ["issues-todo", "--tasks", str(self.tasks)], stdin=json.dumps(facts))


class DuplicateTaskIssueTest(IssuesTodoCliCase):
    # Criterion 1
    def test_two_task_issues_for_one_task_print_the_error_naming_both_numbers_and_exit_1(self) -> None:
        code, _, err = self.ask([STORY, {"number": 121, "title": "t-1: Read notes from cache"},
                                 {"number": 130, "title": "t-1: Read notes again"}])
        self.assertEqual(code, 1)
        self.assertIn("more than one issue for t-1: #121 and #130", err)

    def test_the_error_names_the_task_that_has_the_duplicate(self) -> None:
        code, _, err = self.ask([STORY, {"number": 122, "title": "t-2: Sync on reconnect"},
                                 {"number": 123, "title": "t-2: Sync, edited by hand"}])
        self.assertEqual(code, 1)
        self.assertIn("more than one issue for t-2: #122 and #123", err)

    # Addition: the same title below the story issue is outside the window, so it is no duplicate.
    def test_a_second_t_1_below_the_story_issue_is_no_duplicate(self) -> None:
        code, out, err = self.ask([STORY, {"number": 5, "title": "t-1: old story"}, {"number": 121, "title": "t-1: x"}])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("have task t-1: #121", out.splitlines())


class DuplicateStoryIssueTest(IssuesTodoCliCase):
    # Criterion 2
    def test_two_story_issues_print_the_error_naming_both_numbers_and_exit_1(self) -> None:
        code, _, err = self.ask([STORY, {"number": 130, "title": "Story 2: Offline notes list again"}])
        self.assertEqual(code, 1)
        self.assertIn("more than one issue for the story: #120 and #130", err)

    def test_the_story_error_uses_the_same_wording_as_the_task_error(self) -> None:
        _, _, err = self.ask([STORY, {"number": 130, "title": "Story 2: again"}])
        self.assertNotIn("two issues", err)


class CleanAnswerExitCodeTest(IssuesTodoCliCase):
    # Criterion 3
    def test_an_answer_with_todo_lines_exits_0(self) -> None:
        code, out, err = self.ask([])
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.startswith("todo story: "))

    def test_an_answer_with_have_and_todo_lines_exits_0(self) -> None:
        code, out, _ = self.ask([STORY, {"number": 121, "title": "t-1: Read notes from cache"}])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("have task t-1: #121", lines)
        self.assertIn("todo task t-2: t-2: Sync on reconnect", lines)


class CoreDescriptionsTest(unittest.TestCase):
    # Criterion 4: key phrases only, in both files.
    FILES = ("orchestrator.md", "agents/task-writer.md")

    def text(self, name: str) -> str:
        return ROOT.joinpath("core", *name.split("/")).read_text().lower()

    def test_both_files_describe_matching_by_number_window(self) -> None:
        for name in self.FILES:
            with self.subTest(file=name):
                text = self.text(name)
                self.assertIn("number window", text)
                self.assertIn("above the story issue", text)
                self.assertIn("next later story", text)

    def test_both_files_describe_the_t_n_prefix(self) -> None:
        for name in self.FILES:
            with self.subTest(file=name):
                self.assertIn('"t-<n>:"', self.text(name))

    def test_both_files_describe_the_duplicate_error(self) -> None:
        for name in self.FILES:
            with self.subTest(file=name):
                self.assertIn("more than one issue for", self.text(name))

    def test_both_files_describe_the_exit_codes(self) -> None:
        for name in self.FILES:
            with self.subTest(file=name):
                text = self.text(name)
                self.assertRegex(text, r"exits? 0")
                self.assertRegex(text, r"exits? 1")
