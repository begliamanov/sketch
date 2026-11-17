"""state gate and state wip-message: the two answers /sketch, /pause and /stop used to work out."""

import tempfile
import unittest
from pathlib import Path

from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.state import main
from sketch_tools.state.logic import gate, wip_message

from tests.helpers import run_tool

VALID = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()


def with_phase(phase: str) -> str:
    return VALID.replace("phase: task-loop", "phase: " + phase)


class GateTest(unittest.TestCase):
    def test_no_state_file_means_go(self) -> None:
        self.assertEqual(gate(None), ("go", ""))

    def test_a_finished_story_means_go(self) -> None:
        self.assertEqual(gate(with_phase("done")), ("go", ""))

    def test_every_phase_in_progress_stops_and_points_to_resume_story(self) -> None:
        for phase in ("sketch", "tasks", "baseline", "task-loop", "story-end", "pr"):
            with self.subTest(phase=phase):
                self.assertEqual(gate(with_phase(phase)), ("stop", "Story 2 is unfinished. Run /resume-story."))

    def test_waiting_for_review_with_a_merged_pr_means_mark_done(self) -> None:
        for state in ("merged", "MERGED", "Merged"):
            with self.subTest(state=state):
                self.assertEqual(gate(with_phase("waiting-review"), state), ("mark-done", ""))

    def test_waiting_for_review_with_an_open_pr_stops(self) -> None:
        for state in ("open", "OPEN", "opened"):
            with self.subTest(state=state):
                self.assertEqual(
                    gate(with_phase("waiting-review"), state),
                    ("stop", "Story 2 is still waiting for your review. Merge it first."),
                )

    def test_a_pr_closed_without_merging_stops(self) -> None:
        decision, message = gate(with_phase("waiting-review"), "closed")
        self.assertEqual(decision, "stop")
        self.assertIn("closed without being merged", message)

    def test_waiting_for_review_needs_to_know_the_pr_state(self) -> None:
        with self.assertRaises(UsageError) as ctx:
            gate(with_phase("waiting-review"))
        self.assertIn("--pr-state", str(ctx.exception))
        with self.assertRaises(UsageError):
            gate(with_phase("waiting-review"), "weird")

    def test_the_pr_state_is_ignored_when_it_is_not_needed(self) -> None:
        self.assertEqual(gate(with_phase("done"), "open"), ("go", ""))
        self.assertEqual(gate(with_phase("task-loop"), "merged")[0], "stop")

    def test_a_file_without_a_phase_or_a_story_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            gate(VALID.replace("phase: task-loop\n", ""))
        with self.assertRaises(DataError):
            gate(VALID.replace("story: 2\n", ""))


class GateCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"

    def gate(self, *extra: str):
        return run_tool(main, ["gate", "--state", str(self.state), *extra])

    def test_no_file_prints_go(self) -> None:
        self.assertEqual(self.gate(), (0, "go\n", ""))

    def test_done_prints_go_and_mark_done_prints_that(self) -> None:
        self.state.write_text(with_phase("done"))
        self.assertEqual(self.gate(), (0, "go\n", ""))
        self.state.write_text(with_phase("waiting-review"))
        self.assertEqual(self.gate("--pr-state", "merged"), (0, "mark-done\n", ""))

    def test_a_stop_prints_the_reason_and_exits_1(self) -> None:
        self.state.write_text(with_phase("task-loop"))
        self.assertEqual(self.gate(), (1, "stop: Story 2 is unfinished. Run /resume-story.\n", ""))

    def test_a_missing_pr_state_exits_3(self) -> None:
        self.state.write_text(with_phase("waiting-review"))
        code, out, err = self.gate()
        self.assertEqual((code, out), (3, ""))
        self.assertIn("--pr-state", err)

    def test_a_damaged_file_exits_1(self) -> None:
        self.state.write_text("garbage\n")
        code, _, err = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("phase", err)


class WipMessageTest(unittest.TestCase):
    BRANCH = "story-2-offline-notes"

    def test_a_task_in_progress(self) -> None:
        self.assertEqual(wip_message(VALID, self.BRANCH, "t-3"), "t-3: [wip] interrupted, not reviewed")

    def test_no_task_in_progress_uses_the_story(self) -> None:
        self.assertEqual(wip_message(VALID, self.BRANCH), "story-2: [wip] interrupted, not reviewed")

    def test_on_any_other_branch_it_refuses_and_names_both(self) -> None:
        with self.assertRaises(RefusedError) as ctx:
            wip_message(VALID, "feature/offline-notes", "t-3")
        message = str(ctx.exception)
        self.assertIn("feature/offline-notes", message)
        self.assertIn(self.BRANCH, message)

    def test_no_story_in_progress_refuses(self) -> None:
        with self.assertRaises(RefusedError) as ctx:
            wip_message(with_phase("done"), self.BRANCH, "t-3")
        self.assertIn("no story in progress", str(ctx.exception))

    def test_a_story_branch_that_does_not_exist_yet_refuses(self) -> None:
        text = VALID.replace("story_branch: story-2-offline-notes", "story_branch: none")
        with self.assertRaises(RefusedError) as ctx:
            wip_message(text, self.BRANCH)
        self.assertIn("story branch", str(ctx.exception))

    def test_a_task_that_is_not_in_the_table_or_badly_named(self) -> None:
        for task in ("t-9", "t3", "story-2", ""):
            with self.subTest(task=task):
                with self.assertRaises(UsageError):
                    wip_message(VALID, self.BRANCH, task)

    def test_a_damaged_state_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            wip_message(VALID.replace("story_branch: story-2-offline-notes\n", ""), self.BRANCH)


class WipMessageCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"
        self.state.write_text(VALID)

    def run_wip(self, *extra: str, branch: str = "story-2-offline-notes"):
        return run_tool(main, ["wip-message", "--state", str(self.state), "--branch", branch, *extra])

    def test_prints_only_the_message(self) -> None:
        self.assertEqual(self.run_wip("--task", "t-3"), (0, "t-3: [wip] interrupted, not reviewed\n", ""))
        self.assertEqual(self.run_wip(), (0, "story-2: [wip] interrupted, not reviewed\n", ""))

    def test_the_wrong_branch_exits_2_and_prints_nothing(self) -> None:
        code, out, err = self.run_wip(branch="main")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("main", err)

    def test_the_branch_is_required(self) -> None:
        code, _, err = run_tool(main, ["wip-message", "--state", str(self.state)])
        self.assertEqual(code, 3)
        self.assertIn("--branch", err)

    def test_the_file_is_not_changed(self) -> None:
        self.run_wip("--task", "t-3")
        self.assertEqual(self.state.read_text(), VALID)


if __name__ == "__main__":
    unittest.main()
