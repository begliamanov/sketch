"""state new-story and state task add: the last two steps that used to be written by hand."""

import tempfile
import unittest
from pathlib import Path
from typing import List

from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.state import main
from sketch_tools.state.logic import add_flag, add_task, check, header_value, new_story

from tests.helpers import run_tool

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()

NEW_STORY = """# Story state
story: 2
title: Offline notes list
story_issue: none
feature_branch: feature/offline-notes
story_branch: none
phase: tasks
last_step: story brief approved
stopped: no
pr: none
pr_head_sha: none
story_rounds: 0/3
extra_skills: none
stop_after_task: no

## Tasks
| id  | issue | title                  | blocked_by | status      | attempts | review_rounds |
|-----|-------|------------------------|------------|-------------|----------|---------------|

## Flags
"""


class HeaderValueTest(unittest.TestCase):
    def test_reads_a_header_value(self) -> None:
        self.assertEqual(header_value(VALID, "phase"), "task-loop")
        self.assertEqual(header_value(VALID, "title"), "Offline notes list")
        self.assertEqual(header_value(VALID, "story_rounds"), "0/3")

    def test_a_missing_key_is_none(self) -> None:
        self.assertIsNone(header_value(VALID.replace("phase: task-loop\n", ""), "phase"))
        self.assertIsNone(header_value(VALID, "colour"))

    def test_only_the_header_block_counts(self) -> None:
        self.assertIsNone(header_value("# Story state\n\n## Flags\nphase: done\n", "phase"))


class NewStoryTest(unittest.TestCase):
    def test_the_exact_text_of_a_new_record(self) -> None:
        self.assertEqual(new_story("2", "Offline notes list", "feature/offline-notes"), NEW_STORY)

    def test_the_new_record_is_valid(self) -> None:
        self.assertEqual(check(new_story("2", "Offline notes list", "feature/offline-notes")), [])

    def test_extra_skills_and_the_cap_are_used(self) -> None:
        text = new_story("3", "T", "feature/x", extra_skills="/a/SKILL.md, /b/SKILL.md",
                         story_rounds_cap=5)
        self.assertIn("extra_skills: /a/SKILL.md, /b/SKILL.md\n", text)
        self.assertIn("story_rounds: 0/5\n", text)
        self.assertEqual(check(text), [])

    def test_a_flag_and_a_task_can_be_added_straight_away(self) -> None:
        text = new_story("2", "T", "feature/x")
        text = add_task(text, "t-1", "First", issue="121")
        text = add_flag(text, "t-1", "why")
        self.assertIn("## Flags\n- t-1: why\n", text)

    def test_bad_values_are_rejected(self) -> None:
        bad: List[tuple] = [
            ("x", "T", "b"), ("-1", "T", "b"), ("", "T", "b"),
            ("2", "", "b"), ("2", "two\nlines", "b"),
            ("2", "T", ""), ("2", "T", "a\nb"),
        ]
        for story, title, branch in bad:
            with self.subTest(story=story, title=title, branch=branch):
                with self.assertRaises(UsageError):
                    new_story(story, title, branch)

    def test_a_bad_extra_skills_or_cap_is_rejected(self) -> None:
        with self.assertRaises(UsageError):
            new_story("2", "T", "b", extra_skills="")
        for cap in (0, -1):
            with self.subTest(cap=cap):
                with self.assertRaises(UsageError):
                    new_story("2", "T", "b", story_rounds_cap=cap)


class AddTaskTest(unittest.TestCase):
    ROW = ("| t-5 | none  | Add thing" + " " * 14 + "| t-1        | pending     | 0/3      | 0/2           |")

    def test_appends_one_aligned_row_after_the_last_task(self) -> None:
        after = add_task(VALID, "t-5", "Add thing", blocked_by="t-1")
        before_lines, after_lines = VALID.split("\n"), after.split("\n")
        self.assertEqual(len(after_lines), len(before_lines) + 1)
        index = before_lines.index("| t-4 | 124   | Pull to refresh        | t-1        | flagged     | 3/3      | 0/2           |")
        self.assertEqual(after_lines[index + 1], self.ROW)
        self.assertEqual(after_lines[: index + 1], before_lines[: index + 1])
        self.assertEqual(after_lines[index + 2 :], before_lines[index + 1 :])

    def test_the_result_is_valid(self) -> None:
        self.assertEqual(check(add_task(VALID, "t-5", "Add thing", blocked_by="t-1")), [])
        self.assertEqual(check(add_task(VALID, "t-5", "Add thing", blocked_by="t-1,t-2")), [])

    def test_the_issue_and_the_caps(self) -> None:
        after = add_task(VALID, "t-5", "Add thing", issue="130", attempts_cap=4, review_rounds_cap=3)
        row = [line for line in after.split("\n") if line.startswith("| t-5")][0]
        self.assertIn("| 130   |", row)
        self.assertIn("| 0/4      |", row)
        self.assertIn("| 0/3           |", row)

    def test_into_an_empty_table(self) -> None:
        after = add_task(NEW_STORY, "t-1", "First", issue="121")
        lines = after.split("\n")
        separator = [i for i, line in enumerate(lines) if line.startswith("|---")][0]
        self.assertTrue(lines[separator + 1].startswith("| t-1 | 121   | First"))
        self.assertEqual(lines[separator + 2], "")
        self.assertEqual(check(after), [])

    def test_a_long_title_grows_its_cell(self) -> None:
        after = add_task(NEW_STORY, "t-1", "A very long title that is wider than the column")
        self.assertIn("| A very long title that is wider than the column |", after)

    def test_an_existing_task_is_refused(self) -> None:
        with self.assertRaises(RefusedError) as ctx:
            add_task(VALID, "t-2", "Again")
        self.assertIn("t-2 already exists", str(ctx.exception))

    def test_bad_values_are_rejected(self) -> None:
        cases = [("t5", "T", "none", "none"), ("T-5", "T", "none", "none"), ("", "T", "none", "none"),
                 ("t-5", "", "none", "none"), ("t-5", "a|b", "none", "none"),
                 ("t-5", "two\nlines", "none", "none"), ("t-5", "T", "t1", "none"),
                 ("t-5", "T", "t-1,", "none"), ("t-5", "T", "none", "abc")]
        for task_id, title, blocked, issue in cases:
            with self.subTest(case=(task_id, title, blocked, issue)):
                with self.assertRaises(UsageError):
                    add_task(VALID, task_id, title, blocked_by=blocked, issue=issue)

    def test_a_task_cannot_block_itself(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            add_task(VALID, "t-5", "T", blocked_by="t-1,t-5")
        self.assertIn("itself", str(ctx.exception))

    def test_a_bad_cap_is_rejected(self) -> None:
        for kwargs in ({"attempts_cap": 0}, {"review_rounds_cap": 0}, {"attempts_cap": -2}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(UsageError):
                    add_task(VALID, "t-5", "T", **kwargs)

    def test_a_file_without_a_task_table_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            add_task(VALID.replace("## Tasks", "## Other"), "t-5", "T")

    def test_a_blocker_that_does_not_exist_is_left_for_check_to_report(self) -> None:
        after = add_task(VALID, "t-5", "T", blocked_by="t-9")
        self.assertTrue(any("t-9" in p and "does not exist" in p for p in check(after)))


class StateNewCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"

    def run_state(self, *args: str):
        return run_tool(main, [*args, "--state", str(self.state)])

    def new_story(self, *extra: str):
        return self.run_state("new-story", "--story", "2", "--title", "Offline notes list",
                              "--feature-branch", "feature/offline-notes", *extra)

    def test_new_story_writes_the_record(self) -> None:
        code, out, err = self.new_story()
        self.assertEqual((code, out, err), (0, "ok: story 2 started\n", ""))
        self.assertEqual(self.state.read_text(), NEW_STORY)

    def test_the_record_passes_check(self) -> None:
        self.new_story()
        self.assertEqual(self.run_state("check")[:2], (0, "ok\n"))

    def test_extra_skills_and_the_cap_options(self) -> None:
        code, _, _ = self.new_story("--extra-skills", "/a/SKILL.md", "--story-rounds-cap", "4")
        self.assertEqual(code, 0)
        text = self.state.read_text()
        self.assertIn("extra_skills: /a/SKILL.md\n", text)
        self.assertIn("story_rounds: 0/4\n", text)

    def test_it_replaces_a_finished_story(self) -> None:
        self.state.write_text(VALID.replace("phase: task-loop", "phase: done"))
        code, _, _ = self.new_story()
        self.assertEqual(code, 0)
        self.assertEqual(self.state.read_text(), NEW_STORY)

    def test_it_refuses_to_replace_an_unfinished_story(self) -> None:
        for phase in ("task-loop", "waiting-review", "sketch"):
            with self.subTest(phase=phase):
                before = VALID.replace("phase: task-loop", "phase: " + phase)
                self.state.write_text(before)
                code, out, err = self.new_story()
                self.assertEqual((code, out), (2, ""))
                self.assertIn(phase, err)
                self.assertEqual(self.state.read_text(), before)

    def test_it_refuses_to_replace_a_file_it_cannot_read_a_phase_from(self) -> None:
        self.state.write_text("garbage\n")
        code, _, err = self.new_story()
        self.assertEqual(code, 1)
        self.assertIn("phase", err)
        self.assertEqual(self.state.read_text(), "garbage\n")

    def test_missing_options_exit_3(self) -> None:
        code, _, err = self.run_state("new-story", "--story", "2")
        self.assertEqual(code, 3)
        self.assertIn("--title", err)

    def test_bad_values_exit_3_and_write_nothing(self) -> None:
        code, _, _ = self.run_state("new-story", "--story", "x", "--title", "T",
                                    "--feature-branch", "b")
        self.assertEqual(code, 3)
        self.assertFalse(self.state.exists())


class StateTaskAddCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"
        self.state.write_text(VALID)

    def run_state(self, *args: str):
        return run_tool(main, [*args, "--state", str(self.state)])

    def test_adds_a_row(self) -> None:
        code, out, err = self.run_state("task", "add", "--id", "t-5", "--title", "Add thing",
                                        "--blocked-by", "t-1")
        self.assertEqual((code, out, err), (0, "ok: added t-5\n", ""))
        self.assertIn(AddTaskTest.ROW + "\n", self.state.read_text())
        self.assertEqual(self.run_state("check")[:2], (0, "ok\n"))

    def test_blocked_by_defaults_to_none_and_issue_is_optional(self) -> None:
        self.run_state("task", "add", "--id", "t-5", "--title", "Add thing", "--issue", "130")
        row = [l for l in self.state.read_text().split("\n") if l.startswith("| t-5")][0]
        self.assertIn("| 130   |", row)
        self.assertIn("| none       |", row)

    def test_the_cap_options(self) -> None:
        self.run_state("task", "add", "--id", "t-5", "--title", "T", "--attempts-cap", "4",
                       "--review-rounds-cap", "3")
        row = [l for l in self.state.read_text().split("\n") if l.startswith("| t-5")][0]
        self.assertIn("| 0/4      |", row)
        self.assertIn("| 0/3           |", row)

    def test_an_existing_task_exits_2_and_changes_nothing(self) -> None:
        code, out, err = self.run_state("task", "add", "--id", "t-2", "--title", "Again")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("t-2 already exists", err)
        self.assertEqual(self.state.read_text(), VALID)

    def test_bad_values_exit_3(self) -> None:
        code, _, _ = self.run_state("task", "add", "--id", "t5", "--title", "T")
        self.assertEqual(code, 3)
        self.assertEqual(self.state.read_text(), VALID)

    def test_id_and_title_are_required(self) -> None:
        code, _, err = self.run_state("task", "add", "--id", "t-5")
        self.assertEqual(code, 3)
        self.assertIn("--title", err)


if __name__ == "__main__":
    unittest.main()
