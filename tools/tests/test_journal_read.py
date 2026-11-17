"""journal me-lines and journal signals: reading the journal back."""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.core.errors import UsageError
from sketch_tools.journal import main
from sketch_tools.journal.logic import ENTRY_TYPES, me_lines, signals

from tests.helpers import run_tool

JOURNAL = """# Drift journal
2026-11-12 10:41  S2 t-2  FLAG    test believed wrong: x
2026-11-12 11:05  S2 t-3  CAP     review cap hit (2/2)
2026-11-12 13:02  S2 -    REVIEW  story-end: 1 must-fix
2026-11-13 09:10  S2 -    NOTE    [me] PR description was hard to scan
2026-11-13 09:25  S2 -     EDIT    [me] after PR: +2 commits, 3 files
2026-11-13 14:00  S2 -    CONTEXT [me] use the new endpoint, not [me] again
2026-11-14 10:00  S3 t-1  FLAG    another flag
2026-11-14 10:05  S3 -    NOTE    [me] second story note
2026-11-14 10:10  S3 t-1  ASSUME  used the existing repo
2026-11-15 09:00  S12 -    STOP    [me] end of day
"""

ALL_ME = [
    "2026-11-13 09:10  S2 -    NOTE    [me] PR description was hard to scan",
    "2026-11-13 09:25  S2 -     EDIT    [me] after PR: +2 commits, 3 files",
    "2026-11-13 14:00  S2 -    CONTEXT [me] use the new endpoint, not [me] again",
    "2026-11-14 10:05  S3 -    NOTE    [me] second story note",
    "2026-11-15 09:00  S12 -    STOP    [me] end of day",
]


class MeLinesTest(unittest.TestCase):
    def test_every_developer_line_verbatim_in_order(self) -> None:
        self.assertEqual(me_lines(JOURNAL), ALL_ME)

    def test_lines_that_only_mention_me_later_are_not_the_developers(self) -> None:
        text = JOURNAL + "2026-11-15 10:00  S3 -    ASSUME  the note said [me] somewhere\n"
        self.assertEqual(me_lines(text), ALL_ME)

    def test_the_header_blank_and_odd_lines_are_ignored(self) -> None:
        self.assertEqual(me_lines("# Drift journal\n\nnot a journal line [me] x\n"), [])
        self.assertEqual(me_lines(""), [])

    def test_stories_narrow_it_down(self) -> None:
        self.assertEqual(me_lines(JOURNAL, stories=["S3"]), [ALL_ME[3]])
        self.assertEqual(me_lines(JOURNAL, stories=["S2", "S3"]), ALL_ME[:4])
        self.assertEqual(me_lines(JOURNAL, stories=["S12"]), [ALL_ME[4]])

    def test_after_keeps_only_later_stories(self) -> None:
        self.assertEqual(me_lines(JOURNAL, after=2), ALL_ME[3:])
        self.assertEqual(me_lines(JOURNAL, after=3), [ALL_ME[4]])
        self.assertEqual(me_lines(JOURNAL, after=12), [])

    def test_stories_and_after_work_together(self) -> None:
        self.assertEqual(me_lines(JOURNAL, stories=["S2", "S3"], after=2), [ALL_ME[3]])

    def test_a_story_that_does_not_look_like_s2_is_a_usage_error(self) -> None:
        for bad in ("2", "s2", "S", "Story2"):
            with self.subTest(story=bad):
                with self.assertRaises(UsageError):
                    me_lines(JOURNAL, stories=[bad])


class SignalsTest(unittest.TestCase):
    def test_counts_every_type_in_order_zeros_included(self) -> None:
        found = signals(JOURNAL)
        self.assertEqual(list(found), list(ENTRY_TYPES))
        self.assertEqual(found, {"FLAG": 2, "CAP": 1, "ASSUME": 1, "REVIEW": 1, "NOTE": 2, "EDIT": 1,
                                 "CONTEXT": 1, "STOP": 1})

    def test_an_empty_journal_is_all_zeros(self) -> None:
        self.assertEqual(signals("# Drift journal\n"), {t: 0 for t in ENTRY_TYPES})

    def test_the_filters(self) -> None:
        self.assertEqual(signals(JOURNAL, stories=["S3"])["FLAG"], 1)
        self.assertEqual(signals(JOURNAL, stories=["S3"])["CAP"], 0)
        self.assertEqual(signals(JOURNAL, after=2), {"FLAG": 1, "CAP": 0, "ASSUME": 1, "REVIEW": 0, "NOTE": 1,
                                                     "EDIT": 0, "CONTEXT": 0, "STOP": 1})
        self.assertEqual(signals(JOURNAL, stories=["S2"], after=2), {t: 0 for t in ENTRY_TYPES})

    def test_lines_with_an_unknown_type_are_not_counted(self) -> None:
        text = JOURNAL + "2026-11-15 10:00  S3 -    WEIRD   something\n"
        self.assertEqual(signals(text), signals(JOURNAL))

    def test_a_bad_story_is_a_usage_error(self) -> None:
        with self.assertRaises(UsageError):
            signals(JOURNAL, stories=["2"])


class JournalReadCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.journal = Path(self._tmp.name) / "journal.md"
        self.journal.write_text(JOURNAL)

    def run_read(self, command: str, *extra: str):
        return run_tool(main, [command, "--journal", str(self.journal), *extra])

    def test_me_lines_prints_each_line_verbatim(self) -> None:
        self.assertEqual(self.run_read("me-lines"), (0, "\n".join(ALL_ME) + "\n", ""))

    def test_me_lines_with_filters(self) -> None:
        self.assertEqual(self.run_read("me-lines", "--story", "S3")[1], ALL_ME[3] + "\n")
        self.assertEqual(self.run_read("me-lines", "--after", "2")[1], "\n".join(ALL_ME[3:]) + "\n")
        self.assertEqual(self.run_read("me-lines", "--story", "S2", "--story", "S3")[1], "\n".join(ALL_ME[:4]) + "\n")

    def test_me_lines_with_nothing_found_prints_nothing(self) -> None:
        self.assertEqual(self.run_read("me-lines", "--after", "99"), (0, "", ""))

    def test_signals_prints_a_line_per_type(self) -> None:
        code, out, _ = self.run_read("signals")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[:3], ["FLAG 2", "CAP 1", "ASSUME 1"])
        self.assertEqual(len(out.splitlines()), 8)

    def test_signals_as_json(self) -> None:
        code, out, _ = self.run_read("signals", "--json", "--after", "2")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["FLAG"], 1)

    def test_bad_story_and_bad_after_exit_3(self) -> None:
        self.assertEqual(self.run_read("signals", "--story", "2")[0], 3)
        self.assertEqual(self.run_read("me-lines", "--after", "x")[0], 3)

    def test_a_missing_journal_exits_3(self) -> None:
        self.journal.unlink()
        code, out, err = self.run_read("signals")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("journal.md", err)

    def test_the_journal_is_never_changed(self) -> None:
        self.run_read("me-lines")
        self.run_read("signals")
        self.assertEqual(self.journal.read_text(), JOURNAL)


if __name__ == "__main__":
    unittest.main()
