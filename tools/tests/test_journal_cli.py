"""journal add: the command-line behavior, with real files in a temp folder."""

import tempfile
import unittest
from pathlib import Path

from sketch_tools.journal import main

from tests.helpers import run_tool

HEADER = "# Drift journal\n"
LINE = "2026-11-12 10:41  S2 t-2  FLAG    test believed wrong: expects 5, spec says 4"


class JournalAddTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.journal = Path(self._tmp.name) / "journal.md"

    def add(self, *args: str):
        return run_tool(main, ["add", *args, "--journal", str(self.journal)])

    def test_creates_the_journal_with_its_header_and_the_line(self) -> None:
        code, out, err = self.add("FLAG", "S2", "t-2", "test believed wrong: expects 5, spec says 4")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self.journal.read_text(), HEADER + LINE + "\n")

    def test_reports_the_line_it_appended(self) -> None:
        _, out, _ = self.add("FLAG", "S2", "t-2", "test believed wrong: expects 5, spec says 4")
        self.assertEqual(out, "appended: " + LINE + "\n")

    def test_earlier_lines_stay_byte_for_byte(self) -> None:
        before = HEADER + "old line one\nold line two\n"
        self.journal.write_text(before)
        self.add("NOTE", "S2", "-", "later")
        after = self.journal.read_text()
        self.assertTrue(after.startswith(before))
        self.assertEqual(after[len(before):], "2026-11-12 10:41  S2 -    NOTE    later\n")

    def test_does_not_add_a_second_header_to_an_existing_journal(self) -> None:
        self.journal.write_text(HEADER)
        self.add("NOTE", "S2", "-", "x")
        self.assertEqual(self.journal.read_text().count("# Drift journal"), 1)

    def test_a_file_without_a_final_newline_still_gets_one_line_per_entry(self) -> None:
        self.journal.write_text(HEADER + "unterminated")
        self.add("NOTE", "S2", "-", "x")
        self.assertEqual(
            self.journal.read_text(),
            HEADER + "unterminated\n2026-11-12 10:41  S2 -    NOTE    x\n",
        )

    def test_me_flag_marks_the_developers_own_words(self) -> None:
        self.add("NOTE", "S2", "-", "hard to scan", "--me")
        self.assertIn("NOTE    [me] hard to scan\n", self.journal.read_text())

    def test_the_time_comes_from_the_clock_it_is_given(self) -> None:
        from datetime import datetime

        code, _, _ = run_tool(
            main,
            ["add", "NOTE", "S2", "-", "x", "--journal", str(self.journal)],
            now=datetime(2027, 1, 5, 9, 3),
        )
        self.assertEqual(code, 0)
        self.assertIn("2027-01-05 09:03  S2 -    NOTE    x\n", self.journal.read_text())

    def test_two_entries_end_up_in_call_order(self) -> None:
        self.add("NOTE", "S2", "-", "first")
        self.add("NOTE", "S2", "-", "second")
        lines = self.journal.read_text().splitlines()
        self.assertTrue(lines[1].endswith("first"))
        self.assertTrue(lines[2].endswith("second"))


class JournalAddRejectsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.journal = Path(self._tmp.name) / "journal.md"

    def add(self, *args: str):
        return run_tool(main, ["add", *args, "--journal", str(self.journal)])

    def test_bad_type_exits_3_and_leaves_no_file(self) -> None:
        code, out, err = self.add("BOGUS", "S2", "t-2", "x")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("type must be one of FLAG CAP ASSUME REVIEW NOTE EDIT CONTEXT STOP", err)
        self.assertFalse(self.journal.exists())

    def test_bad_input_leaves_an_existing_journal_untouched(self) -> None:
        self.journal.write_text(HEADER + "keep me\n")
        code, _, _ = self.add("FLAG", "S2", "t-2", "line one\nline two")
        self.assertEqual(code, 3)
        self.assertEqual(self.journal.read_text(), HEADER + "keep me\n")

    def test_bad_story_and_task_and_text_exit_3(self) -> None:
        for args in (("FLAG", "2", "t-2", "x"), ("FLAG", "S2", "t2", "x"), ("FLAG", "S2", "t-2", " ")):
            with self.subTest(args=args):
                code, _, err = self.add(*args)
                self.assertEqual(code, 3)
                self.assertTrue(err.startswith("error:"))

    def test_missing_journal_path_exits_3(self) -> None:
        code, out, err = run_tool(main, ["add", "NOTE", "S2", "-", "x"])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("--journal", err)

    def test_missing_folder_exits_3_with_a_clear_message(self) -> None:
        missing = Path(self._tmp.name) / "no-such-dir" / "journal.md"
        code, out, err = run_tool(main, ["add", "NOTE", "S2", "-", "x", "--journal", str(missing)])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("no-such-dir", err)


if __name__ == "__main__":
    unittest.main()
