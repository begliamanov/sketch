"""state set / bump / check: the command-line behavior, with real files."""

import os
import tempfile
import unittest
from pathlib import Path

from sketch_tools.state import main

from tests.helpers import run_tool

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()


class StateCliCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.state = self.dir / "state.md"
        self.state.write_text(VALID)

    def run_state(self, *args: str):
        return run_tool(main, [*args, "--state", str(self.state)])


class StateSetTest(StateCliCase):
    def test_sets_a_header_field(self) -> None:
        code, out, err = self.run_state("set", "phase", "story-end")
        self.assertEqual((code, out, err), (0, "ok: phase = story-end\n", ""))
        self.assertEqual(self.state.read_text(), VALID.replace("phase: task-loop", "phase: story-end"))

    def test_sets_a_task_field(self) -> None:
        code, out, _ = self.run_state("set", "--task", "t-3", "status", "tests-red")
        self.assertEqual((code, out), (0, "ok: t-3 status = tests-red\n"))
        self.assertIn("| tests-red   |", self.state.read_text())

    def test_a_bad_value_exits_3_and_leaves_the_file_alone(self) -> None:
        code, out, err = self.run_state("set", "phase", "taskloop")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("phase must be one of", err)
        self.assertEqual(self.state.read_text(), VALID)

    def test_a_counter_exits_2(self) -> None:
        code, _, err = self.run_state("set", "story_rounds", "0/3")
        self.assertEqual(code, 2)
        self.assertIn("bump", err)
        self.assertEqual(self.state.read_text(), VALID)

    def test_a_damaged_file_exits_1(self) -> None:
        self.state.write_text(VALID.replace("phase: task-loop\n", ""))
        code, _, err = self.run_state("set", "phase", "done")
        self.assertEqual(code, 1)
        self.assertIn("phase", err)

    def test_leaves_no_temp_files_behind(self) -> None:
        self.run_state("set", "phase", "done")
        self.assertEqual(os.listdir(self.dir), ["state.md"])

    def test_a_missing_state_file_exits_3(self) -> None:
        self.state.unlink()
        code, out, err = self.run_state("set", "phase", "done")
        self.assertEqual((code, out), (3, ""))
        self.assertIn(str(self.state), err)

    def test_the_state_path_is_required(self) -> None:
        code, _, err = run_tool(main, ["set", "phase", "done"])
        self.assertEqual(code, 3)
        self.assertIn("--state", err)


class StateBumpTest(StateCliCase):
    def test_bumps_a_header_counter(self) -> None:
        code, out, err = self.run_state("bump", "story_rounds")
        self.assertEqual((code, out, err), (0, "ok: story_rounds 0/3 -> 1/3\n", ""))
        self.assertIn("story_rounds: 1/3\n", self.state.read_text())

    def test_bumps_a_task_counter(self) -> None:
        code, out, _ = self.run_state("bump", "--task", "t-1", "attempts")
        self.assertEqual((code, out), (0, "ok: t-1 attempts 1/3 -> 2/3\n"))

    def test_at_the_cap_exits_2_and_leaves_the_file_alone(self) -> None:
        for _ in range(3):
            self.run_state("bump", "story_rounds")
        before = self.state.read_text()
        code, out, err = self.run_state("bump", "story_rounds")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("at cap (3/3)", err)
        self.assertEqual(self.state.read_text(), before)

    def test_a_non_counter_exits_3(self) -> None:
        code, _, err = self.run_state("bump", "phase")
        self.assertEqual(code, 3)
        self.assertIn("not a counter", err)

    def test_changes_nothing_but_the_counter(self) -> None:
        self.run_state("bump", "--task", "t-2", "review_rounds")
        after = self.state.read_text()
        self.assertEqual(len(after.split("\n")), len(VALID.split("\n")))
        changed = [n for o, n in zip(VALID.split("\n"), after.split("\n")) if o != n]
        self.assertEqual(len(changed), 1)


class StateCheckTest(StateCliCase):
    def test_a_valid_file_prints_ok_and_exits_0(self) -> None:
        code, out, err = self.run_state("check")
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_problems_are_listed_one_per_line_and_exit_1(self) -> None:
        self.state.write_text(
            VALID.replace("phase: task-loop", "phase: taskloop").replace("| done        |", "| finished    |")
        )
        code, out, err = self.run_state("check")
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line.startswith("error: ") for line in lines))

    def test_check_never_writes(self) -> None:
        self.state.write_text(VALID.replace("phase: task-loop", "phase: taskloop"))
        before = self.state.read_text()
        self.run_state("check")
        self.assertEqual(self.state.read_text(), before)

    def test_a_missing_state_file_exits_3(self) -> None:
        self.state.unlink()
        code, out, _ = self.run_state("check")
        self.assertEqual((code, out), (3, ""))


if __name__ == "__main__":
    unittest.main()
