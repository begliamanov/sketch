"""Agents close a task issue when its review is satisfied (t-2).

The rule lives in the text of core/: the run-story skill, conventions, the orchestrator rules and the
pr-agent. These tests read those sources and check the meaning of the specific sentence or section.
"""

import re
import unittest
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
RUN_STORY = ROOT / "core" / "skills" / "run-story" / "SKILL.md"
CONVENTIONS = ROOT / "core" / "conventions.md"
ORCHESTRATOR = ROOT / "core" / "orchestrator.md"
PR_AGENT = ROOT / "core" / "agents" / "pr-agent.md"


def between(text: str, start: str, end: str = "") -> str:
    """The part of text from the line starting with `start` up to the line starting with `end`."""
    begin = text.index(start)
    stop = text.index(end, begin + len(start)) if end else len(text)
    return text[begin:stop]


def sentences(text: str) -> List[str]:
    return re.split(r"(?<=[.!?])\s+", " ".join(text.split()))


def review_step() -> str:
    """run-story section 4c."""
    return between(RUN_STORY.read_text(), "**c. Review.**", "**d. Assumptions.**")


def finish_step() -> str:
    """run-story section 7."""
    return between(RUN_STORY.read_text(), "## 7. Finish")


class SatisfiedClosesTheTaskIssueTest(unittest.TestCase):
    """Criterion 1: on satisfied, close the task issue with a comment naming the task's commit SHAs."""

    def satisfied_line(self) -> str:
        lines = [l for l in review_step().splitlines() if l.lstrip().startswith("- `SATISFIED`")]
        self.assertEqual(len(lines), 1, "no single SATISFIED bullet in section 4c")
        return lines[0]

    def test_run_story_closes_the_task_issue_on_satisfied(self) -> None:
        line = self.satisfied_line()
        self.assertRegex(line, r"(?i)\bclose\b[^.]*\btask issue\b")

    def test_run_story_names_the_task_commit_shas_in_the_closing_comment(self) -> None:
        line = self.satisfied_line()
        self.assertRegex(line, r"(?i)comment")
        self.assertRegex(line, r"(?i)commit\s+SHAs?|SHAs? of")


class FlaggedTaskKeepsItsIssueOpenTest(unittest.TestCase):
    """Criterion 2: a flagged task's issue stays open, with a comment saying why."""

    def flagged_sentence(self) -> str:
        found = [
            s
            for s in sentences(review_step())
            if re.search(r"(?i)\bflagged\b", s) and re.search(r"(?i)\bissue\b", s)
        ]
        self.assertTrue(found, "section 4c says nothing about a flagged task's issue")
        return " ".join(found)

    def test_run_story_keeps_a_flagged_tasks_issue_open(self) -> None:
        self.assertRegex(
            self.flagged_sentence(),
            r"(?i)\b(stays|stay|remains|remain|left|leave|keep|kept)\b[^.]*\bopen\b",
        )

    def test_run_story_comments_on_the_flagged_task_issue_saying_why(self) -> None:
        text = self.flagged_sentence()
        self.assertRegex(text, r"(?i)\bcomment")
        self.assertRegex(text, r"(?i)\b(why|reason)\b")


class DeveloperNextStepsTest(unittest.TestCase):
    """Criterion 3: section 7 no longer asks the developer to close task issues."""

    def test_next_steps_drop_closing_the_task_issues(self) -> None:
        self.assertNotIn("close the task issues", finish_step())

    def test_finish_no_longer_says_do_not_close_any_issue(self) -> None:
        self.assertNotIn("do not close any issue", finish_step().lower())

    def test_next_steps_still_tell_the_developer_to_review_and_merge_then_run_sketch(self) -> None:
        text = " ".join(finish_step().split())
        self.assertRegex(text, r"Next: review and merge the PR, then run /sketch for the next story")


class RuleTextsStateTheCloseRuleTest(unittest.TestCase):
    """Criterion 4: conventions, orchestrator and pr-agent say agents close task issues when their
    review is satisfied, and never the story issue."""

    FILES = {"conventions": CONVENTIONS, "orchestrator": ORCHESTRATOR, "pr-agent": PR_AGENT}

    def test_each_text_says_agents_close_a_task_issue_when_its_review_is_satisfied(self) -> None:
        for name, path in self.FILES.items():
            with self.subTest(file=name):
                found = [
                    s
                    for s in sentences(path.read_text())
                    if re.search(r"(?i)\bclose[sd]?\b", s)
                    and re.search(r"(?i)\btask issues?\b", s)
                    and re.search(r"(?i)\bsatisfied\b", s)
                ]
                self.assertTrue(found, "no sentence: close a task issue when its review is satisfied")

    def test_each_text_says_never_close_the_story_issue(self) -> None:
        for name, path in self.FILES.items():
            with self.subTest(file=name):
                found = [
                    s
                    for s in sentences(path.read_text())
                    if re.search(r"(?i)\b(never|not)\s+close\b[^.]*\bstory issue\b", s)
                ]
                self.assertTrue(found, "no sentence: never close the story issue")


class OldCloseWordingIsGoneTest(unittest.TestCase):
    """Scenario: the old blanket 'never close issues' wording is replaced."""

    def test_conventions_no_longer_says_never_close_issues(self) -> None:
        self.assertNotIn("Never close issues", CONVENTIONS.read_text())

    def test_orchestrator_no_longer_lists_closing_issues_among_things_it_never_does(self) -> None:
        text = " ".join(ORCHESTRATOR.read_text().split())
        self.assertNotIn("force-push, or close issues", text)

    def test_orchestrator_guard_description_no_longer_blocks_closing_issues_wholesale(self) -> None:
        # Addition: the guard now allows closing a task issue of the current story (t-1).
        text = " ".join(ORCHESTRATOR.read_text().split())
        self.assertNotIn("the feature branch, and closing issues", text)

    def test_pr_agent_no_longer_says_never_close_or_edit_issues(self) -> None:
        # Addition: the pr-agent line contradicts the new rule for task issues.
        self.assertNotIn("Never close or edit issues", PR_AGENT.read_text())
