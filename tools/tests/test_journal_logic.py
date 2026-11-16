"""journal: formatting and validating one entry (pure logic)."""

import unittest
from datetime import datetime

from sketch_tools.core.errors import UsageError
from sketch_tools.journal.logic import ENTRY_TYPES, format_entry

WHEN = datetime(2026, 11, 12, 10, 41)


class FormatEntryTest(unittest.TestCase):
    """The exact lines in core/state-format.md."""

    def test_flag_with_a_task(self) -> None:
        line = format_entry("FLAG", "S2", "t-2", "test believed wrong: x", WHEN)
        self.assertEqual(line, "2026-11-12 10:41  S2 t-2  FLAG    test believed wrong: x")

    def test_cap_pads_the_type_to_the_same_column(self) -> None:
        line = format_entry("CAP", "S2", "t-3", "review cap hit (2/2)", WHEN)
        self.assertEqual(line, "2026-11-12 10:41  S2 t-3  CAP     review cap hit (2/2)")

    def test_story_level_entry_uses_a_dash_for_the_task(self) -> None:
        line = format_entry("REVIEW", "S2", "-", "story-end: 1 must-fix", WHEN)
        self.assertEqual(line, "2026-11-12 10:41  S2 -    REVIEW  story-end: 1 must-fix")

    def test_me_flag_puts_the_marker_before_the_text(self) -> None:
        line = format_entry("NOTE", "S2", "-", "PR description was hard to scan", WHEN, me=True)
        self.assertEqual(
            line, "2026-11-12 10:41  S2 -    NOTE    [me] PR description was hard to scan"
        )

    def test_longest_type_has_one_space_before_the_text(self) -> None:
        line = format_entry("CONTEXT", "S2", "-", "say hi", WHEN, me=True)
        self.assertEqual(line, "2026-11-12 10:41  S2 -    CONTEXT [me] say hi")

    def test_the_text_is_kept_exactly(self) -> None:
        text = "  keep   spacing, quotes \"and\" 'these' and unicode é  "
        line = format_entry("NOTE", "S1", "-", text, WHEN)
        self.assertTrue(line.endswith("NOTE    " + text))

    def test_every_documented_type_is_accepted(self) -> None:
        self.assertEqual(
            ENTRY_TYPES, ("FLAG", "CAP", "ASSUME", "REVIEW", "NOTE", "EDIT", "CONTEXT", "STOP")
        )
        for entry_type in ENTRY_TYPES:
            format_entry(entry_type, "S1", "-", "x", WHEN)

    def test_two_digit_story_and_task_numbers_are_accepted(self) -> None:
        line = format_entry("FLAG", "S12", "t-10", "x", WHEN)
        self.assertEqual(line, "2026-11-12 10:41  S12 t-10  FLAG    x")


class FormatEntryRejectsTest(unittest.TestCase):
    def assert_rejects(self, *args: object, **kwargs: object) -> str:
        with self.assertRaises(UsageError) as ctx:
            format_entry(*args, **kwargs)  # type: ignore[arg-type]
        return str(ctx.exception)

    def test_unknown_type_lists_the_allowed_types(self) -> None:
        message = self.assert_rejects("BOGUS", "S2", "t-2", "x", WHEN)
        self.assertIn("BOGUS", message)
        self.assertIn("FLAG CAP ASSUME REVIEW NOTE EDIT CONTEXT STOP", message)

    def test_lowercase_type_is_rejected(self) -> None:
        self.assert_rejects("flag", "S2", "t-2", "x", WHEN)

    def test_story_must_look_like_s_and_a_number(self) -> None:
        for bad in ("2", "s2", "S", "S2a", "Story2", ""):
            with self.subTest(story=bad):
                self.assertIn("story", self.assert_rejects("FLAG", bad, "t-2", "x", WHEN))

    def test_task_must_be_t_dash_number_or_a_dash(self) -> None:
        for bad in ("t2", "T-2", "t-", "2", "", "--"):
            with self.subTest(task=bad):
                self.assertIn("task", self.assert_rejects("FLAG", "S2", bad, "x", WHEN))

    def test_empty_text_is_rejected(self) -> None:
        for bad in ("", "   "):
            with self.subTest(text=bad):
                self.assertIn("text", self.assert_rejects("FLAG", "S2", "t-2", bad, WHEN))

    def test_a_multi_line_text_is_rejected_not_changed(self) -> None:
        for bad in ("one\ntwo", "one\r\ntwo", "one\rtwo"):
            with self.subTest(text=bad):
                self.assertIn("one line", self.assert_rejects("FLAG", "S2", "t-2", bad, WHEN))


if __name__ == "__main__":
    unittest.main()
