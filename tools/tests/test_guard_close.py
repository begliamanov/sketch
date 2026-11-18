"""guard check-command and closing issues: only a task issue of the current story may be closed.

The task table of the state file (--state) says which issue numbers are task issues. The story
issue, any other number, and every close the guard cannot check against a readable state file stay
blocked. An api call that closes an issue stays blocked whatever the number."""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.guard import main

from tests.helpers import run_tool

VALID_STATE = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()
STORY_ISSUE = "120"           # state_valid.md: story_issue
TASK_ISSUES = ("121", "122", "123", "124")  # state_valid.md: the issue column of the task table


def hook(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


class CloseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"
        self.state.write_text(VALID_STATE)

    def check(self, command: str):
        return run_tool(main, ["check-command", "--protect", "main", "--state", str(self.state)],
                        stdin=hook(command))

    def assertAllowed(self, command: str) -> None:
        self.assertEqual(self.check(command), (0, "", ""), command)

    def assertRefusedAsNotATaskIssue(self, command: str) -> None:
        code, out, err = self.check(command)
        self.assertEqual((code, out), (2, ""), command)
        self.assertIn("not a task issue of the current story", err)


class ClosingATaskIssueTest(CloseTestCase):
    """Criterion 1: a task issue in the state file's task table may be closed (gh and glab)."""

    def test_closing_a_task_issue_in_the_table_passes_with_gh(self) -> None:
        self.assertAllowed("gh issue close 121")

    def test_closing_a_task_issue_in_the_table_passes_with_glab(self) -> None:
        self.assertAllowed("glab issue close 122")

    def test_every_task_issue_in_the_table_may_be_closed(self) -> None:  # addition
        for number in TASK_ISSUES:
            with self.subTest(issue=number):
                self.assertAllowed("gh issue close " + number)

    def test_a_close_with_a_comment_and_a_repo_option_passes(self) -> None:  # addition
        self.assertAllowed('gh issue close 123 --comment "done in abc1234, def5678"')
        self.assertAllowed("gh issue close -R owner/repo 123 -c done")

    def test_the_task_table_of_the_current_state_decides(self) -> None:  # addition
        self.state.write_text(VALID_STATE.replace("| 124   |", "| 999   |"))
        self.assertAllowed("gh issue close 999")
        self.assertRefusedAsNotATaskIssue("gh issue close 124")


class ClosingTheStoryIssueTest(CloseTestCase):
    """Criterion 2: the story issue is never closed by an agent."""

    def test_closing_the_story_issue_is_blocked(self) -> None:
        self.assertRefusedAsNotATaskIssue("gh issue close " + STORY_ISSUE)
        self.assertRefusedAsNotATaskIssue("glab issue close " + STORY_ISSUE)

    def test_one_story_issue_close_in_a_chain_blocks_the_chain(self) -> None:  # addition
        self.assertRefusedAsNotATaskIssue("gh issue close 121 && gh issue close " + STORY_ISSUE)


class ClosingAnUnknownIssueTest(CloseTestCase):
    """Criterion 3: a number that is not in the task table is blocked."""

    def test_closing_an_unknown_issue_number_is_blocked(self) -> None:
        self.assertRefusedAsNotATaskIssue("gh issue close 5")
        self.assertRefusedAsNotATaskIssue("glab issue close 5")

    def test_a_number_that_only_contains_a_task_issue_number_is_blocked(self) -> None:  # addition
        self.assertRefusedAsNotATaskIssue("gh issue close 1210")
        self.assertRefusedAsNotATaskIssue("gh issue close 12")


class ClosingWithoutAUsableStateFileTest(CloseTestCase):
    """Criterion 4: a missing or unreadable state file blocks every close."""

    def test_a_missing_state_file_blocks_the_close(self) -> None:
        self.state.unlink()
        code, out, err = self.check("gh issue close 121")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("state", err)

    def test_an_unreadable_state_file_blocks_the_close(self) -> None:
        self.state.unlink()
        self.state.mkdir()  # reading a directory fails with an OS error, even for root
        code, out, err = self.check("glab issue close 121")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("state", err)


class ClosingThroughTheApiTest(CloseTestCase):
    """Criterion 5: an api call that closes an issue stays blocked, even for a task issue."""

    def test_api_call_with_state_closed_on_a_task_issue_number_is_blocked(self) -> None:
        code, out, err = self.check("gh api -X PATCH repos/o/r/issues/121 -f state=closed")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("closes an issue", err)


class TheBlockMessageTest(CloseTestCase):
    """Criterion 6: the message for a refused close says why."""

    def test_the_message_says_the_issue_is_not_a_task_issue_of_the_current_story(self) -> None:
        _, _, err = self.check("gh issue close " + STORY_ISSUE)
        self.assertTrue(err.startswith("error: "))
        self.assertIn("not a task issue of the current story", err)

    def test_the_message_names_the_refused_number(self) -> None:  # addition
        _, _, err = self.check("gh issue close 77")
        self.assertIn("77", err)

    def test_the_message_no_longer_says_the_developer_closes_every_issue(self) -> None:  # addition
        _, _, err = self.check("gh issue close 77")
        self.assertNotIn("the developer closes issues", err)


if __name__ == "__main__":
    unittest.main()
