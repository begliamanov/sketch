"""Story 1 story-end review findings: two seams that earlier tasks left open.

1. `summary --json` must give the tester a `counts` object that a tester report accepts as it is:
   exactly passed, failed and skipped. A system failure is not a count (see the glossary); it is
   listed as its own top-level key, next to `counts`, and only when there is one.
2. `issues-todo` marks a blocking link `todo` whenever either of its two tasks is `todo`, so the
   blocking links of an earlier story (same t-1..t-4 ids) cannot make this story's links `have`.
   core/agents/task-writer.md tells the task-writer to pass only the current story's links.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from sketch_tools.plan import main as plan_main
from sketch_tools.report.logic import validate
from sketch_tools import tests as sketch_tests_tool

from tests.helpers import run_tool
from tests.report_examples import with_changes
from tests.test_plan_tasks import VALID as TASKS  # story 2: Offline notes list, t-1 to t-4
from tests.test_tests_system_failures_cli import CONFIG, LAUNCH_ERROR, with_system_failure

ROOT = Path(__file__).resolve().parents[2]


class SummaryCountsAcceptedByTesterReportTest(unittest.TestCase):
    """Finding 1: the counts of a run with a system failure go into a FAIL tester report unchanged."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.config = base / "config.md"
        self.config.write_text(CONFIG)
        self.folder = base / "results"
        self.folder.mkdir()

    def summary_json(self, results_file: str) -> Dict[str, Any]:
        (self.folder / "001-results.json").write_text(results_file)
        code, out, _ = run_tool(sketch_tests_tool.main, ["summary", "--config", str(self.config), "--results", str(self.folder), "--json"])
        self.assertEqual(code, 0)
        return json.loads(out)

    def mixed(self) -> Dict[str, Any]:
        # one real failure, one passed test, one system failure
        return self.summary_json(with_system_failure("Runner crashed", "boom", "Passed", "Failed"))

    def test_counts_are_exactly_passed_failed_and_skipped_beside_a_system_failure(self) -> None:
        self.assertEqual(self.mixed()["counts"], {"passed": 1, "failed": 1, "skipped": 0})

    def test_the_counts_are_accepted_as_they_are_in_a_fail_tester_report(self) -> None:
        counts = self.mixed()["counts"]
        report = with_changes("tester", result="FAIL", counts=counts,
                              failing_tests=[{"name": "S.t1", "message": "wrong 1"}])
        self.assertEqual(validate("tester", "story-2", report), [])

    def test_the_system_failure_is_a_separate_top_level_key_next_to_counts(self) -> None:
        data = self.mixed()
        self.assertIn("counts", data)
        names = [item["name"] for item in data["system_failures"]]
        self.assertEqual(names, ["Runner crashed"])
        self.assertEqual(data["system_failures"][0]["message"], "boom")

    # Addition: the real launch-error fixture (a system failure and nothing else) counts nothing.
    def test_a_launch_error_alone_has_zero_counts_and_lists_the_system_failure(self) -> None:
        data = self.summary_json(LAUNCH_ERROR)
        self.assertEqual(data["counts"], {"passed": 0, "failed": 0, "skipped": 0})
        self.assertTrue(data["system_failures"])


class BlockingLinksOfEarlierStoriesTest(unittest.TestCase):
    """Finding 2: a link is `todo` whenever either of its two tasks is `todo`."""

    LINKS = [("t-2", "t-1"), ("t-3", "t-1"), ("t-4", "t-2"), ("t-4", "t-3")]
    STORY_1 = [{"number": 10, "title": "Story 1: Notes"}] + [
        {"number": 10 + n, "title": "t-%d: old task %d" % (n, n)} for n in range(1, 5)]
    STORY_2 = {"number": 20, "title": "Story 2: Offline notes list"}

    def ask(self, issues: List[Dict[str, Any]], links: List[Any]) -> List[str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tasks = Path(tmp.name) / "tasks.md"
        tasks.write_text(TASKS)
        facts = {"issues": issues, "links": [{"blocked": b, "by": y} for b, y in links]}
        code, out, err = run_tool(plan_main, ["issues-todo", "--tasks", str(tasks)], stdin=json.dumps(facts))
        self.assertEqual((code, err), (0, ""))
        return out.splitlines()

    def test_links_of_an_earlier_story_do_not_make_this_storys_links_have(self) -> None:
        lines = self.ask(self.STORY_1 + [self.STORY_2], self.LINKS)
        for blocked, by in self.LINKS:
            with self.subTest(link=blocked + " " + by):
                self.assertIn("todo link %s %s" % (blocked, by), lines)
                self.assertNotIn("have link %s %s" % (blocked, by), lines)

    # Pins existing behavior the developer asked for, so it passes at once (a guard against over-fixing).
    def test_a_link_whose_two_tasks_are_both_have_stays_have(self) -> None:
        tasks = [{"number": 20 + n, "title": "t-%d: task" % n} for n in range(1, 5)]
        lines = self.ask([self.STORY_2] + tasks, self.LINKS)
        for blocked, by in self.LINKS:
            self.assertIn("have link %s %s" % (blocked, by), lines)

    def test_a_link_with_the_blocked_task_have_and_the_blocker_todo_is_todo(self) -> None:
        lines = self.ask([self.STORY_2, {"number": 22, "title": "t-2: Sync"}], [("t-2", "t-1")])
        self.assertIn("todo link t-2 t-1", lines)

    def test_a_link_with_the_blocker_have_and_the_blocked_task_todo_is_todo(self) -> None:
        lines = self.ask([self.STORY_2, {"number": 21, "title": "t-1: Read"}], [("t-2", "t-1")])
        self.assertIn("todo link t-2 t-1", lines)


class TaskWriterPassesOnlyThisStorysLinksTest(unittest.TestCase):
    # Key phrase only, like the criterion 4 tests of test_plan_issues_duplicates.py.
    def test_task_writer_md_says_to_pass_only_links_between_the_current_storys_task_issues(self) -> None:
        text = " ".join(ROOT.joinpath("core", "agents", "task-writer.md").read_text().lower().split())
        self.assertRegex(text, r"only (the )?links between the current story.s task issues")
