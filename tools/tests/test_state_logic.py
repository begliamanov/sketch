"""state: set, bump and check on the text of state.md (pure logic)."""

import unittest
from pathlib import Path
from typing import List

from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.state.logic import add_flag, bump, check, set_header, set_task

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()


def changed_lines(before: str, after: str) -> List[str]:
    """The lines of `after` that differ from `before` (same line count assumed)."""
    old, new = before.split("\n"), after.split("\n")
    assert len(old) == len(new), "line count changed"
    return [n for o, n in zip(old, new) if o != n]


class SetHeaderTest(unittest.TestCase):
    def test_changes_only_that_line(self) -> None:
        after = set_header(VALID, "phase", "story-end")
        self.assertEqual(after, VALID.replace("phase: task-loop", "phase: story-end"))

    def test_keeps_a_missing_final_newline_missing(self) -> None:
        text = VALID.rstrip("\n")
        self.assertFalse(set_header(text, "phase", "pr").endswith("\n"))

    def test_every_phase_is_accepted(self) -> None:
        for phase in ("sketch", "tasks", "baseline", "task-loop", "story-end", "pr",
                      "waiting-review", "done"):
            with self.subTest(phase=phase):
                self.assertIn("phase: " + phase + "\n", set_header(VALID, "phase", phase))

    def test_a_bad_phase_lists_the_allowed_ones(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            set_header(VALID, "phase", "taskloop")
        self.assertIn("phase must be one of", str(ctx.exception))
        self.assertIn("sketch tasks baseline task-loop story-end pr waiting-review done",
                      str(ctx.exception))

    def test_stopped_accepts_no_failure_and_manual_with_a_reason(self) -> None:
        for value in ("no", "failure: tester could not run", "manual: paused 14:00"):
            with self.subTest(value=value):
                self.assertIn("stopped: " + value + "\n", set_header(VALID, "stopped", value))

    def test_stopped_rejects_anything_else(self) -> None:
        for value in ("yes", "failure:", "failure", "manual:  ", "No"):
            with self.subTest(value=value):
                with self.assertRaises(UsageError):
                    set_header(VALID, "stopped", value)

    def test_numbers_none_urls_and_shas(self) -> None:
        good = [("story", "3"), ("story_issue", "130"), ("story_issue", "none"), ("pr", "none"),
                ("pr", "45"), ("pr", "https://github.com/o/r/pull/45"),
                ("pr_head_sha", "none"), ("pr_head_sha", "a35c24b"),
                ("pr_head_sha", "a35c24b0123456789abcdef0123456789abcdef0")]
        for key, value in good:
            with self.subTest(key=key, value=value):
                self.assertIn(key + ": " + value + "\n", set_header(VALID, key, value))
        bad = [("story", "x"), ("story", "-1"), ("story_issue", "abc"), ("pr", "pull 45"),
               ("pr_head_sha", "xyz"), ("pr_head_sha", "abc")]
        for key, value in bad:
            with self.subTest(key=key, value=value):
                with self.assertRaises(UsageError):
                    set_header(VALID, key, value)

    def test_free_text_keys_take_any_one_line_but_not_empty_or_multi_line(self) -> None:
        for key in ("title", "last_step", "feature_branch", "story_branch", "extra_skills"):
            with self.subTest(key=key):
                self.assertIn(key + ": some words, here\n", set_header(VALID, key, "some words, here"))
                for bad in ("", "  ", "two\nlines"):
                    with self.assertRaises(UsageError):
                        set_header(VALID, key, bad)

    def test_stop_after_task_is_set_to_yes_or_no(self) -> None:
        for value in ("yes", "no"):
            with self.subTest(value=value):
                self.assertIn("stop_after_task: " + value + "\n", set_header(VALID, "stop_after_task", value))
        for bad in ("maybe", "", "Yes"):
            with self.subTest(value=bad):
                with self.assertRaises(UsageError):
                    set_header(VALID, "stop_after_task", bad)

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            set_header(VALID, "colour", "blue")
        self.assertIn("unknown key", str(ctx.exception))

    def test_a_counter_is_refused_and_points_to_bump(self) -> None:
        with self.assertRaises(RefusedError) as ctx:
            set_header(VALID, "story_rounds", "0/3")
        self.assertIn("bump", str(ctx.exception))

    def test_a_file_without_that_line_is_a_data_error(self) -> None:
        text = VALID.replace("phase: task-loop\n", "")
        with self.assertRaises(DataError) as ctx:
            set_header(text, "phase", "done")
        self.assertIn("phase", str(ctx.exception))

    def test_only_the_header_block_is_edited_not_a_matching_line_in_the_flags(self) -> None:
        text = VALID + "phase: not a real line\n"
        after = set_header(text, "phase", "done")
        self.assertEqual(changed_lines(text, after), ["phase: done"])


class SetTaskTest(unittest.TestCase):
    def test_changes_only_that_cell_and_keeps_the_row_aligned(self) -> None:
        after = set_task(VALID, "t-3", "status", "tests-red")
        (row,) = changed_lines(VALID, after)
        self.assertEqual(
            row, "| t-3 | 123   | Offline banner         | t-1        | tests-red   | 0/3      | 0/2           |"
        )

    def test_a_longer_value_grows_the_cell(self) -> None:
        after = set_task(VALID, "t-3", "title", "A much longer title than the old column held")
        (row,) = changed_lines(VALID, after)
        self.assertIn("| A much longer title than the old column held |", row)
        self.assertTrue(row.endswith("| 0/3      | 0/2           |"))

    def test_every_status_is_accepted(self) -> None:
        for status in ("pending", "tests-red", "green", "in-review", "done", "flagged"):
            with self.subTest(status=status):
                after = set_task(VALID, "t-1", "status", status)
                self.assertIn("| " + status, after)

    def test_a_bad_status_lists_the_allowed_ones(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            set_task(VALID, "t-1", "status", "finished")
        self.assertIn("pending tests-red green in-review done flagged", str(ctx.exception))

    def test_issue_blocked_by_and_title(self) -> None:
        self.assertIn("| 130   |", set_task(VALID, "t-1", "issue", "130"))
        self.assertIn("| none  |", set_task(VALID, "t-1", "issue", "none"))
        self.assertIn("| t-1,t-2 ", set_task(VALID, "t-3", "blocked_by", "t-1,t-2"))
        for field, bad in (("issue", "abc"), ("blocked_by", "t1"), ("blocked_by", "t-1,"),
                           ("title", ""), ("title", "a|b")):
            with self.subTest(field=field, value=bad):
                with self.assertRaises(UsageError):
                    set_task(VALID, "t-1", field, bad)

    def test_counters_are_refused_and_point_to_bump(self) -> None:
        for field in ("attempts", "review_rounds"):
            with self.subTest(field=field):
                with self.assertRaises(RefusedError) as ctx:
                    set_task(VALID, "t-1", field, "1/3")
                self.assertIn("bump", str(ctx.exception))

    def test_the_id_and_unknown_fields_cannot_be_set(self) -> None:
        for field in ("id", "colour"):
            with self.subTest(field=field):
                with self.assertRaises(UsageError):
                    set_task(VALID, "t-1", field, "x")

    def test_unknown_task_is_rejected(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            set_task(VALID, "t-9", "status", "done")
        self.assertIn("t-9", str(ctx.exception))


class BumpTest(unittest.TestCase):
    def test_a_header_counter(self) -> None:
        after, old, new = bump(VALID, "story_rounds")
        self.assertEqual((old, new), ("0/3", "1/3"))
        self.assertEqual(after, VALID.replace("story_rounds: 0/3", "story_rounds: 1/3"))

    def test_a_task_counter(self) -> None:
        after, old, new = bump(VALID, "attempts", task_id="t-1")
        self.assertEqual((old, new), ("1/3", "2/3"))
        (row,) = changed_lines(VALID, after)
        self.assertIn("| 2/3      |", row)

    def test_the_other_task_counter(self) -> None:
        _, old, new = bump(VALID, "review_rounds", task_id="t-2")
        self.assertEqual((old, new), ("0/2", "1/2"))

    def test_bumping_up_to_the_cap_is_allowed_and_one_more_is_refused(self) -> None:
        text = VALID
        for expected in ("1/3", "2/3", "3/3"):
            text, _, new = bump(text, "story_rounds")
            self.assertEqual(new, expected)
        with self.assertRaises(RefusedError) as ctx:
            bump(text, "story_rounds")
        self.assertIn("at cap (3/3)", str(ctx.exception))

    def test_a_counter_already_over_its_cap_is_refused(self) -> None:
        with self.assertRaises(RefusedError):
            bump(VALID.replace("story_rounds: 0/3", "story_rounds: 4/3"), "story_rounds")

    def test_a_key_that_is_not_a_counter_is_rejected(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            bump(VALID, "phase")
        self.assertIn("not a counter", str(ctx.exception))

    def test_a_task_counter_needs_its_task_and_a_header_counter_must_not_have_one(self) -> None:
        with self.assertRaises(UsageError):
            bump(VALID, "attempts")
        with self.assertRaises(UsageError):
            bump(VALID, "story_rounds", task_id="t-1")

    def test_a_malformed_counter_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            bump(VALID.replace("story_rounds: 0/3", "story_rounds: lots"), "story_rounds")

    def test_unknown_task_is_rejected(self) -> None:
        with self.assertRaises(UsageError):
            bump(VALID, "attempts", task_id="t-9")


class AddFlagTest(unittest.TestCase):
    def test_appends_one_line_after_the_last_flag(self) -> None:
        after = add_flag(VALID, "t-2", "review cap hit (2/2)")
        self.assertEqual(
            after,
            VALID.replace(
                "- t-4: tests keep failing, MissingBanner not found\n",
                "- t-4: tests keep failing, MissingBanner not found\n- t-2: review cap hit (2/2)\n",
            ),
        )

    def test_into_an_empty_flags_section(self) -> None:
        text = VALID.replace("- t-4: tests keep failing, MissingBanner not found\n", "")
        self.assertTrue(add_flag(text, "t-4", "why").endswith("## Flags\n- t-4: why\n"))

    def test_keeps_blank_lines_that_follow_the_last_flag(self) -> None:
        text = VALID + "\n\n"
        after = add_flag(text, "t-2", "why")
        self.assertTrue(after.endswith("- t-2: why\n\n\n"))

    def test_the_reason_is_kept_exactly(self) -> None:
        reason = "  odd   spacing, \"quotes\" and é  "
        self.assertIn("- t-2: " + reason + "\n", add_flag(VALID, "t-2", reason))

    def test_does_not_touch_the_task_table(self) -> None:
        before = VALID.split("\n")
        after = add_flag(VALID, "t-2", "why").split("\n")
        self.assertEqual(len(after), len(before) + 1)
        table_end = before.index("## Flags")
        self.assertEqual(after[:table_end], before[:table_end])

    def test_an_unknown_task_is_rejected(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            add_flag(VALID, "t-9", "why")
        self.assertIn("t-9", str(ctx.exception))

    def test_an_empty_or_multi_line_reason_is_rejected(self) -> None:
        for bad in ("", "   ", "one\ntwo"):
            with self.subTest(reason=bad):
                with self.assertRaises(UsageError):
                    add_flag(VALID, "t-2", bad)

    def test_a_task_that_already_has_a_flag_is_refused(self) -> None:
        with self.assertRaises(RefusedError) as ctx:
            add_flag(VALID, "t-4", "again")
        self.assertIn("already flagged", str(ctx.exception))

    def test_a_file_without_a_flags_section_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            add_flag(VALID.replace("## Flags", "## Other"), "t-2", "why")


class CheckTest(unittest.TestCase):
    def problems(self, text: str) -> List[str]:
        return check(text)

    def assert_problem(self, text: str, *needles: str) -> None:
        found = self.problems(text)
        self.assertTrue(
            any(all(n in p for n in needles) for p in found),
            "no problem containing %r in %r" % (needles, found),
        )

    def test_the_example_from_the_format_is_valid(self) -> None:
        self.assertEqual(self.problems(VALID), [])

    def test_an_empty_task_table_and_no_flags_section_are_valid(self) -> None:
        head = VALID.split("## Tasks")[0]
        text = head + "## Tasks\n| id  | issue | title | blocked_by | status | attempts | review_rounds |\n|-----|-------|-------|------------|--------|----------|---------------|\n"
        self.assertEqual(self.problems(text), [])

    def test_stop_after_task_is_a_required_yes_or_no(self) -> None:
        for value in ("yes", "no"):
            with self.subTest(value=value):
                self.assertEqual(self.problems(VALID.replace("stop_after_task: no", "stop_after_task: " + value)), [])
        self.assert_problem(VALID.replace("stop_after_task: no\n", ""), "missing key", "stop_after_task")
        self.assert_problem(VALID.replace("stop_after_task: no", "stop_after_task: maybe"),
                            "stop_after_task", '"maybe"')

    def test_every_flagged_task_needs_a_flag_line(self) -> None:
        self.assert_problem(VALID.replace("- t-4: tests keep failing, MissingBanner not found\n", ""),
                            "t-4", "flagged", "no flag")

    def test_a_flag_line_needs_a_flagged_task(self) -> None:
        self.assert_problem(VALID + "- t-2: surprise\n", "t-2", "not flagged")
        self.assert_problem(VALID + "- t-9: ghost\n", "t-9", "does not exist")

    def test_a_task_may_have_only_one_flag_line(self) -> None:
        self.assert_problem(VALID + "- t-4: again\n", "t-4", "twice")

    def test_a_flag_line_must_look_like_dash_task_colon_reason(self) -> None:
        self.assert_problem(VALID + "- <reason, quoted>\n", "flag line", "<reason, quoted>")

    def test_missing_key(self) -> None:
        self.assert_problem(VALID.replace("phase: task-loop\n", ""), "missing key", "phase")

    def test_bad_values_name_the_key_and_the_value(self) -> None:
        self.assert_problem(VALID.replace("phase: task-loop", "phase: taskloop"),
                            "phase", '"taskloop"')
        self.assert_problem(VALID.replace("stopped: no", "stopped: maybe"), "stopped", '"maybe"')
        self.assert_problem(VALID.replace("story: 2", "story: two"), "story", '"two"')

    def test_bad_task_status(self) -> None:
        self.assert_problem(VALID.replace("| done        |", "| finished    |"),
                            "t-1", "status", '"finished"')

    def test_counter_over_its_cap_and_malformed_counter(self) -> None:
        self.assert_problem(VALID.replace("| 1/3      | 0/2", "| 4/3      | 0/2"),
                            "t-2", "attempts", '"4/3"', "over its cap")
        self.assert_problem(VALID.replace("story_rounds: 0/3", "story_rounds: x"),
                            "story_rounds", '"x"')

    def test_a_counter_exactly_at_its_cap_is_fine(self) -> None:
        self.assertEqual(self.problems(VALID.replace("story_rounds: 0/3", "story_rounds: 3/3")), [])

    def test_blocked_by_must_point_at_a_real_other_task(self) -> None:
        self.assert_problem(VALID.replace("| t-1        | pending", "| t-9        | pending"),
                            "t-3", "blocked_by", '"t-9"', "does not exist")
        self.assert_problem(VALID.replace("| t-1        | pending", "| t-3        | pending"),
                            "t-3", "blocked_by", "itself")

    def test_a_task_id_may_not_repeat(self) -> None:
        self.assert_problem(VALID.replace("| t-3 | 123", "| t-2 | 123"), "t-2", "twice")

    def test_missing_sections_and_a_wrong_first_line(self) -> None:
        self.assert_problem(VALID.replace("## Tasks", "## Jobs"), "## Tasks")
        self.assert_problem(VALID.replace("# Story state", "# State"), "first line")

    def test_a_changed_table_header_is_reported(self) -> None:
        self.assert_problem(VALID.replace("| status      |", "| state       |"), "table header")

    def test_every_problem_is_reported_in_one_pass(self) -> None:
        broken = (VALID.replace("phase: task-loop", "phase: taskloop")
                  .replace("| done        |", "| finished    |")
                  .replace("| 1/3      | 0/2", "| 4/3      | 0/2")
                  .replace("| t-1        | pending", "| t-9        | pending"))
        self.assertGreaterEqual(len(self.problems(broken)), 4)


if __name__ == "__main__":
    unittest.main()
