"""state reconcile: the state file against what git, the tracker and the PR say."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sketch_tools.core.errors import UsageError
from sketch_tools.state import main
from sketch_tools.state.logic import parse_facts, reconcile

from tests.helpers import run_tool

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()

GOOD: Dict[str, Any] = {
    "feature_branch_exists": True,
    "story_branch_exists": True,
    "current_branch": "story-2-offline-notes",
    "feature_moved": False,
    "task_commits": {"t-1": True, "t-2": True, "t-3": False, "t-4": True},
    "unknown_commits": [],
    "tree_dirty": [],
    "issues": {"story": "open", "t-1": "open", "t-2": "open", "t-3": "open", "t-4": "open"},
    "cli_logged_in": True,
    "config_problems": [],
    "state_problems": [],
}


def facts(**changes: Any) -> Dict[str, Any]:
    result = copy.deepcopy(GOOD)
    for key, value in changes.items():
        if value is ...:
            result.pop(key, None)
        else:
            result[key] = value
    return result


def kinds(found: List[Tuple[str, str]]) -> List[str]:
    return [kind for kind, _ in found]


class ReconcileTest(unittest.TestCase):
    def assert_found(self, found: List[Tuple[str, str]], kind: str, *needles: str) -> None:
        self.assertTrue(
            any(k == kind and all(n in m for n in needles) for k, m in found),
            "no %s containing %r in %r" % (kind, needles, found),
        )

    def test_everything_in_order_finds_nothing(self) -> None:
        self.assertEqual(reconcile(VALID, GOOD), [])

    def test_facts_that_were_not_gathered_are_not_checked(self) -> None:
        self.assertEqual(reconcile(VALID, {}), [])

    def test_a_missing_branch_is_risky(self) -> None:
        self.assert_found(reconcile(VALID, facts(feature_branch_exists=False)), "risky", "feature branch", "feature/offline-notes")
        self.assert_found(reconcile(VALID, facts(story_branch_exists=False)), "risky", "story branch", "story-2-offline-notes")

    def test_no_story_branch_yet_is_fine(self) -> None:
        text = VALID.replace("story_branch: story-2-offline-notes", "story_branch: none")
        self.assertEqual(reconcile(text, facts(story_branch_exists=False, current_branch="feature/offline-notes")), [])

    def test_the_feature_branch_moving_is_risky(self) -> None:
        self.assert_found(reconcile(VALID, facts(feature_moved=True)), "risky", "feature branch moved")

    def test_a_task_that_should_have_commits_but_has_none_is_risky(self) -> None:
        for status in ("tests-red", "green", "in-review", "done"):
            with self.subTest(status=status):
                text = VALID.replace("| in-review   |", "| " + status.ljust(11) + " |")
                found = reconcile(text, facts(task_commits={"t-2": False}))
                self.assert_found(found, "risky", "t-2", status, "no commits")

    def test_pending_and_flagged_tasks_may_have_no_commits(self) -> None:
        self.assertEqual(reconcile(VALID, facts(task_commits={"t-3": False, "t-4": False})), [])

    def test_unknown_commits_are_harmless_and_listed(self) -> None:
        found = reconcile(VALID, facts(unknown_commits=["t-2: tweak by hand", "story-2: docs"]))
        self.assertEqual(kinds(found), ["harmless"])
        self.assert_found(found, "harmless", "2 commits", "does not know", "t-2: tweak by hand", "story-2: docs", "EDIT")

    def test_uncommitted_changes_on_the_story_branch_are_harmless(self) -> None:
        found = reconcile(VALID, facts(tree_dirty=[" M a.swift", "?? b.swift"]))
        self.assertEqual(kinds(found), ["harmless"])
        self.assert_found(found, "harmless", "uncommitted", "WIP", "a.swift", "b.swift")

    def test_uncommitted_changes_on_another_branch_are_risky(self) -> None:
        found = reconcile(VALID, facts(tree_dirty=[" M a.swift"], current_branch="feature/offline-notes"))
        self.assertEqual(kinds(found), ["risky"])
        self.assert_found(found, "risky", "feature/offline-notes", "story-2-offline-notes", "do not commit")

    def test_being_on_another_branch_with_a_clean_tree_is_harmless(self) -> None:
        found = reconcile(VALID, facts(current_branch="main"))
        self.assertEqual(kinds(found), ["harmless"])
        self.assert_found(found, "harmless", "main", "story-2-offline-notes")

    def test_closed_or_missing_issues_are_risky(self) -> None:
        found = reconcile(VALID, facts(issues={"story": "closed", "t-2": "missing"}))
        self.assertEqual(kinds(found), ["risky", "risky"])
        self.assert_found(found, "risky", "story issue", "#120", "closed")
        self.assert_found(found, "risky", "t-2", "#122", "missing")

    def test_an_issue_the_state_has_no_number_for_is_not_checked(self) -> None:
        text = VALID.replace("story_issue: 120", "story_issue: none")
        self.assertEqual(reconcile(text, facts(issues={"story": "closed"})), [])

    def test_a_pr_that_was_merged_closed_or_lost_is_risky(self) -> None:
        text = VALID.replace("pr: none", "pr: 45")
        for pr in ("merged", "closed", "missing"):
            with self.subTest(pr=pr):
                self.assert_found(reconcile(text, facts(pr=pr)), "risky", "PR 45", pr)
        self.assertEqual(reconcile(text, facts(pr="open")), [])

    def test_a_merged_pr_while_waiting_for_review_means_the_story_is_finished(self) -> None:
        text = VALID.replace("pr: none", "pr: 45").replace("phase: task-loop", "phase: waiting-review")
        found = reconcile(text, facts(pr="merged"))
        self.assertEqual(kinds(found), ["harmless"])
        self.assert_found(found, "harmless", "PR 45", "merged", "finished")

    def test_no_pr_in_the_state_means_no_pr_check(self) -> None:
        self.assertEqual(reconcile(VALID, facts(pr="closed")), [])

    def test_a_tracker_cli_that_is_not_logged_in_is_risky(self) -> None:
        self.assert_found(reconcile(VALID, facts(cli_logged_in=False)), "risky", "not logged in")

    def test_config_and_state_problems_are_risky_and_quoted(self) -> None:
        found = reconcile(VALID, facts(config_problems=["skills role common: skill file does not exist: /x"],
                                       state_problems=['phase "taskloop" is not valid']))
        self.assertEqual(kinds(found), ["risky", "risky"])
        self.assert_found(found, "risky", "config", "skill file does not exist: /x")
        self.assert_found(found, "risky", "state", 'phase "taskloop" is not valid')

    def test_risky_ones_come_first_so_they_cannot_be_missed(self) -> None:
        found = reconcile(VALID, facts(unknown_commits=["x"], feature_moved=True, tree_dirty=[" M a"]))
        self.assertEqual(kinds(found), ["risky", "harmless", "harmless"])

    def test_every_problem_is_found_in_one_pass(self) -> None:
        found = reconcile(VALID, facts(feature_branch_exists=False, feature_moved=True,
                                       issues={"story": "closed"}, cli_logged_in=False))
        self.assertEqual(kinds(found), ["risky"] * 4)

    def test_a_damaged_state_file_is_a_data_error(self) -> None:
        from sketch_tools.core.errors import DataError

        with self.assertRaises(DataError):
            reconcile(VALID.replace("story_branch: story-2-offline-notes\n", ""), GOOD)


class ParseFactsTest(unittest.TestCase):
    def test_valid_facts_are_returned(self) -> None:
        self.assertEqual(parse_facts(json.dumps(GOOD)), GOOD)
        self.assertEqual(parse_facts("{}"), {})

    def assert_bad(self, text: str, *needles: str) -> None:
        with self.assertRaises(UsageError) as ctx:
            parse_facts(text)
        for needle in needles:
            self.assertIn(needle, str(ctx.exception))

    def test_not_json_and_not_an_object(self) -> None:
        self.assert_bad("{nope", "JSON")
        self.assert_bad("[1]", "object")

    def test_unknown_keys_are_rejected_so_a_typo_cannot_skip_a_check(self) -> None:
        self.assert_bad(json.dumps({"feature_moved": False, "tree_diry": []}), "unknown", "tree_diry")

    def test_types(self) -> None:
        self.assert_bad(json.dumps({"feature_moved": "no"}), "feature_moved", "true or false")
        self.assert_bad(json.dumps({"current_branch": 5}), "current_branch", "text")
        self.assert_bad(json.dumps({"tree_dirty": "a"}), "tree_dirty", "list")
        self.assert_bad(json.dumps({"tree_dirty": [1]}), "tree_dirty", "text")
        self.assert_bad(json.dumps({"task_commits": {"x": True}}), "task_commits", "task id")
        self.assert_bad(json.dumps({"task_commits": {"t-1": "yes"}}), "task_commits", "true or false")
        self.assert_bad(json.dumps({"issues": {"epic": "open"}}), "issues", "story")
        self.assert_bad(json.dumps({"issues": {"story": "fine"}}), "issues", "open, closed or missing")
        self.assert_bad(json.dumps({"pr": "gone"}), "pr", "open, merged, closed or missing")


class ReconcileCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"
        self.state.write_text(VALID)

    def run_reconcile(self, data: Any):
        text = data if isinstance(data, str) else json.dumps(data)
        return run_tool(main, ["reconcile", "--state", str(self.state)], stdin=text)

    def test_nothing_found_prints_ok(self) -> None:
        self.assertEqual(self.run_reconcile(GOOD), (0, "ok\n", ""))

    def test_harmless_lines_exit_0_and_say_so(self) -> None:
        code, out, _ = self.run_reconcile(facts(unknown_commits=["t-2: by hand"]))
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("harmless: "))

    def test_risky_lines_exit_1_and_come_first(self) -> None:
        code, out, _ = self.run_reconcile(facts(unknown_commits=["x"], feature_moved=True))
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("risky: "))
        self.assertTrue(lines[1].startswith("harmless: "))

    def test_bad_facts_exit_3(self) -> None:
        code, out, _ = self.run_reconcile("{nope")
        self.assertEqual((code, out), (3, ""))

    def test_a_damaged_state_exits_1(self) -> None:
        self.state.write_text("garbage\n")
        code, _, _ = self.run_reconcile(GOOD)
        self.assertEqual(code, 1)

    def test_the_state_file_is_not_changed(self) -> None:
        self.run_reconcile(facts(feature_moved=True))
        self.assertEqual(self.state.read_text(), VALID)


if __name__ == "__main__":
    unittest.main()
