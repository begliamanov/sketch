"""plan issues-todo: only task issues of the current story count (t-3).

A task issue belongs to the current story when its number is above the story issue's number, below the
next later "Story <m>:" issue's number (if there is one), and its title starts with "t-<n>:" (a title
edited by hand after the prefix still counts). Every story restarts at t-1, so the title alone cannot
tell stories apart. Without a story issue, every task is todo.
"""

import unittest
from typing import Any, Dict, List

from sketch_tools.core.errors import DataError
from sketch_tools.plan.issues import issues_todo

from tests.test_plan_tasks import VALID as TASKS  # story 2: Offline notes list, t-1 to t-4

STORY_TITLE = "Story 2: Offline notes list"
TASK_TITLES = ["t-1: Read notes from cache", "t-2: Sync on reconnect", "t-3: Offline banner", "t-4: Retry failed syncs"]


def story_issues(story_number: int, first_number: int) -> List[Dict[str, Any]]:
    """The story issue and t-1..t-4 task issues of one story, numbered upward from first_number."""
    titles = ["Story %d: Offline notes list" % story_number] + TASK_TITLES
    return [{"number": first_number + i, "title": title} for i, title in enumerate(titles)]


def task_lines(issues: List[Dict[str, Any]]) -> List[str]:
    """The `have`/`todo` lines for the story and its tasks (links left out)."""
    try:
        lines = issues_todo(TASKS, {"issues": issues, "links": []})
    except DataError as err:  # the old rule reports a clash instead of picking the current story
        raise AssertionError("expected an answer, got a data error: " + str(err)) from None
    return [line for line in lines if " link " not in line]


class CurrentStoryOnlyTest(unittest.TestCase):
    # Criterion 1
    def test_story_2_tasks_resolve_to_story_2_issues_when_story_1_has_the_same_task_titles(self) -> None:
        issues = story_issues(1, 10) + story_issues(2, 20)  # story 1: #10 (story), #11-#14; story 2: #20, #21-#24
        self.assertEqual(task_lines(issues), [
            "have story: #20", "have task t-1: #21", "have task t-2: #22", "have task t-3: #23", "have task t-4: #24"])

    def test_the_answer_does_not_depend_on_the_order_of_the_issue_list(self) -> None:
        issues = story_issues(2, 20) + story_issues(1, 10)
        issues.reverse()
        self.assertEqual(task_lines(issues), [
            "have story: #20", "have task t-1: #21", "have task t-2: #22", "have task t-3: #23", "have task t-4: #24"])

    def test_tasks_the_current_story_lacks_are_todo_even_if_an_earlier_story_has_them(self) -> None:
        issues = story_issues(1, 10) + story_issues(2, 20)[:3]  # story 2 has only t-1 and t-2 so far
        self.assertEqual(task_lines(issues), [
            "have story: #20", "have task t-1: #21", "have task t-2: #22",
            "todo task t-3: t-3: Offline banner", "todo task t-4: t-4: Retry failed syncs"])

    # Criterion 2
    def test_task_issue_below_the_story_issue_number_is_todo(self) -> None:
        issues = [{"number": 50, "title": "t-1: Read notes from cache"}, {"number": 120, "title": STORY_TITLE},
                  {"number": 121, "title": "t-2: Sync on reconnect"}]
        self.assertEqual(task_lines(issues), [
            "have story: #120", "todo task t-1: t-1: Read notes from cache", "have task t-2: #121",
            "todo task t-3: t-3: Offline banner", "todo task t-4: t-4: Retry failed syncs"])

    # Criterion 3
    def test_task_issue_above_a_later_story_issue_is_todo(self) -> None:
        issues = [{"number": 120, "title": STORY_TITLE}, {"number": 121, "title": "t-1: Read notes from cache"},
                  {"number": 122, "title": "t-2: Sync on reconnect"},
                  {"number": 130, "title": "Story 3: Something else"},
                  {"number": 131, "title": "t-3: Offline banner"}, {"number": 132, "title": "t-4: Retry failed syncs"}]
        self.assertEqual(task_lines(issues), [
            "have story: #120", "have task t-1: #121", "have task t-2: #122",
            "todo task t-3: t-3: Offline banner", "todo task t-4: t-4: Retry failed syncs"])

    def test_hand_edited_title_inside_the_window_is_have_and_the_same_prefix_above_a_later_story_is_not(self) -> None:
        issues = [{"number": 120, "title": STORY_TITLE},
                  {"number": 121, "title": "t-1: Something else entirely"},  # edited by hand, inside the window
                  {"number": 122, "title": "t-2: Sync on reconnect"},
                  {"number": 130, "title": "Story 3: Something else"},
                  {"number": 131, "title": "t-1: Read notes from cache"}]  # above the later story: ignored
        self.assertEqual(task_lines(issues), [
            "have story: #120", "have task t-1: #121", "have task t-2: #122",
            "todo task t-3: t-3: Offline banner", "todo task t-4: t-4: Retry failed syncs"])

    # Criterion 4
    def test_without_a_story_issue_every_task_is_todo_even_if_task_issues_exist(self) -> None:
        issues = [{"number": 10 + i, "title": title} for i, title in enumerate(TASK_TITLES)]
        self.assertEqual(task_lines(issues), [
            "todo story: " + STORY_TITLE, "todo task t-1: t-1: Read notes from cache",
            "todo task t-2: t-2: Sync on reconnect", "todo task t-3: t-3: Offline banner",
            "todo task t-4: t-4: Retry failed syncs"])

    def test_without_a_story_issue_of_its_own_other_stories_issues_do_not_count(self) -> None:
        # Addition: only story 1 exists in the tracker, the tasks file is story 2's.
        self.assertEqual(task_lines(story_issues(1, 10))[0], "todo story: " + STORY_TITLE)
        self.assertEqual([l.split(":")[0] for l in task_lines(story_issues(1, 10))[1:]],
                         ["todo task t-1", "todo task t-2", "todo task t-3", "todo task t-4"])

    # Criterion 5
    def test_story_issue_is_matched_by_its_title_and_gates_the_task_issues(self) -> None:
        issues = story_issues(1, 10) + [{"number": 120, "title": STORY_TITLE}] + [
            {"number": 121 + i, "title": title} for i, title in enumerate(TASK_TITLES)]
        self.assertEqual(task_lines(issues)[0], "have story: #120")
        self.assertEqual(task_lines(issues)[1:], ["have task t-%d: #%d" % (i + 1, 121 + i) for i in range(4)])


if __name__ == "__main__":
    unittest.main()
