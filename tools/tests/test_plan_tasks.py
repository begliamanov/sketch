"""plan tasks-check and tasks-order: the planning file, on text."""

import unittest
from pathlib import Path
from typing import Dict, List

from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.plan.logic import check_tasks, order_tasks

VALID = (Path(__file__).parent / "fixtures" / "tasks_valid.md").read_text()


def build_deps(deps: Dict[int, List[int]]) -> str:
    """A valid tasks.md whose tasks block each other as given: {2: [1]} means t-2 is blocked by t-1."""
    rows = ["| id | title | blocked_by | scenarios |", "|----|-------|------------|-----------|"]
    blocks = []
    for number, blockers in deps.items():
        blocked = ", ".join("t-%d" % b for b in blockers) or "none"
        rows.append("| t-%d | Task %d | %s | 1 |" % (number, number, blocked))
        blocks.append(
            "## t-%d: Task %d\nBlocked by: %s\nDelivers: Does thing %d.\nAcceptance criteria:\n"
            "1. Criterion %d.\nTest scenarios:\n- scenario %d\nTerms: thing\nOut of scope: others\n"
            % (number, number, blocked, number, number, number)
        )
    return "# Tasks for story 1: Demo\n\n" + "\n".join(rows) + "\n\n" + "\n".join(blocks)


def chain(count: int) -> str:
    return build_deps({i: ([i - 1] if i > 1 else []) for i in range(1, count + 1)})


class CheckTasksValidTest(unittest.TestCase):
    def test_the_example_is_valid(self) -> None:
        self.assertEqual(check_tasks(VALID), [])

    def test_a_builder_file_is_valid(self) -> None:
        self.assertEqual(check_tasks(chain(4)), [])

    def test_the_task_count_limits(self) -> None:
        self.assertEqual(check_tasks(chain(3)), [])
        self.assertEqual(check_tasks(chain(8)), [])

    def test_too_few_tasks_say_to_merge_the_story(self) -> None:
        problems = check_tasks(chain(2))
        self.assertTrue(any("2 tasks" in p and "at least 3" in p and "merge" in p for p in problems), problems)

    def test_too_many_tasks_say_to_split_the_story(self) -> None:
        problems = check_tasks(chain(9))
        self.assertTrue(any("9 tasks" in p and "at most 8" in p and "split" in p for p in problems), problems)

    def test_the_limits_can_be_changed(self) -> None:
        self.assertEqual(check_tasks(chain(2), min_tasks=2), [])
        self.assertEqual(check_tasks(chain(9), max_tasks=9), [])
        self.assertNotEqual(check_tasks(chain(4), max_tasks=3), [])

    def test_independent_tasks_are_fine(self) -> None:
        self.assertEqual(check_tasks(build_deps({1: [], 2: [], 3: []})), [])


class CheckTasksProblemsTest(unittest.TestCase):
    def assert_problem(self, text: str, *needles: str) -> None:
        found = check_tasks(text)
        self.assertTrue(
            any(all(n in p for n in needles) for p in found),
            "no problem containing %r in %r" % (needles, found),
        )

    def test_an_empty_file_has_problems(self) -> None:
        self.assertNotEqual(check_tasks(""), [])

    def test_the_first_line(self) -> None:
        self.assert_problem(VALID.replace("# Tasks for story 2: Offline notes list", "# Tasks"), "first line")

    def test_the_table_is_required_and_has_fixed_columns(self) -> None:
        self.assert_problem(VALID.replace("| id | title | blocked_by | scenarios |", "| id | name | blocked_by | scenarios |"), "table header")
        no_table = VALID.split("| id |")[0] + "## t-1: Read notes from cache" + VALID.split("## t-1: Read notes from cache", 1)[1]
        self.assert_problem(no_table, "missing task table")

    def test_table_rows(self) -> None:
        self.assert_problem(VALID.replace("| t-1 | Read", "| 1 | Read"), "task id", '"1"')
        self.assert_problem(VALID.replace("| t-3 | Offline banner | t-1 | 2 |", "| t-2 | Offline banner | t-1 | 2 |"), "t-2", "twice")
        self.assert_problem(VALID.replace("| t-1 | Read notes from cache | none | 3 |", "| t-1 | Read notes from cache | none | many |"), "t-1", "scenarios", '"many"')
        self.assert_problem(VALID.replace("| t-2 | Sync on reconnect | t-1 | 3 |", "| t-2 | Sync on reconnect | t1 | 3 |"), "t-2", "blocked_by", '"t1"')

    def test_a_row_needs_its_block_and_a_block_needs_its_row(self) -> None:
        self.assert_problem(VALID.replace("## t-3: Offline banner", "## t-5: Offline banner"), "t-3", "no block")
        self.assert_problem(VALID.replace("## t-3: Offline banner", "## t-5: Offline banner"), "t-5", "no row")

    def test_the_block_must_agree_with_the_table(self) -> None:
        self.assert_problem(VALID.replace("## t-3: Offline banner", "## t-3: A banner"), "t-3", "title")
        self.assert_problem(VALID.replace("Blocked by: t-2, t-3", "Blocked by: t-2"), "t-4", "blocked")
        self.assert_problem(VALID.replace("Blocked by: t-1\nDelivers: A banner", "Blocked by: none\nDelivers: A banner"), "t-3", "blocked")
        self.assert_problem(VALID.replace("| t-3 | Offline banner | t-1 | 2 |", "| t-3 | Offline banner | t-1 | 5 |"), "t-3", "5 scenarios", "2")

    def test_every_label_is_required(self) -> None:
        for label in ("Blocked by", "Delivers", "Acceptance criteria", "Test scenarios", "Terms", "Out of scope"):
            with self.subTest(label=label):
                lines = VALID.split("\n")
                start = lines.index("## t-3: Offline banner")
                end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## t-4"))
                block = [l for l in lines[start:end] if not l.startswith(label + ":")]
                text = "\n".join(lines[:start] + block + lines[end:])
                self.assert_problem(text, "t-3", label)

    def test_criteria_and_scenarios_must_exist(self) -> None:
        no_criteria = VALID.replace("1. The banner shows while offline and hides when online.\n", "")
        self.assert_problem(no_criteria, "t-3", "no acceptance criteria")
        no_scenarios = VALID.replace("- shows the banner while offline\n- hides the banner when online\n", "")
        self.assert_problem(no_scenarios, "t-3", "no test scenarios")

    def test_criteria_are_numbered_from_one(self) -> None:
        self.assert_problem(VALID.replace("2. An empty cache shows the empty state.", "3. An empty cache shows the empty state."), "t-1", "numbered")

    def test_every_criterion_needs_a_scenario(self) -> None:
        text = VALID.replace("- shows the empty state for an empty cache\n- orders notes by last edit\n", "").replace("| t-1 | Read notes from cache | none | 3 |", "| t-1 | Read notes from cache | none | 1 |")
        self.assert_problem(text, "t-1", "2 criteria", "1 scenario")

    def test_blockers_must_exist_and_not_be_the_task_itself(self) -> None:
        text = VALID.replace("| t-3 | Offline banner | t-1 | 2 |", "| t-3 | Offline banner | t-9 | 2 |").replace("Blocked by: t-1\nDelivers: A banner", "Blocked by: t-9\nDelivers: A banner")
        self.assert_problem(text, "t-3", "t-9", "does not exist")
        text = VALID.replace("| t-3 | Offline banner | t-1 | 2 |", "| t-3 | Offline banner | t-3 | 2 |").replace("Blocked by: t-1\nDelivers: A banner", "Blocked by: t-3\nDelivers: A banner")
        self.assert_problem(text, "t-3", "itself")

    def test_a_dependency_cycle_is_reported_with_its_path(self) -> None:
        problems = check_tasks(build_deps({1: [3], 2: [1], 3: [2], 4: []}))
        cycle = [p for p in problems if "cycle" in p]
        self.assertEqual(len(cycle), 1)
        for task in ("t-1", "t-2", "t-3"):
            self.assertIn(task, cycle[0])

    def test_every_problem_is_reported_in_one_pass(self) -> None:
        broken = (VALID.replace("# Tasks for story 2: Offline notes list", "# Tasks")
                  .replace("## t-3: Offline banner", "## t-3: A banner")
                  .replace("Terms: banner\n", "")
                  .replace("2. An empty cache shows the empty state.", "3. An empty cache shows the empty state."))
        self.assertGreaterEqual(len(check_tasks(broken)), 4)


class OrderTasksTest(unittest.TestCase):
    DEPS = {1: [], 2: [1], 3: [1], 4: [2, 3], 5: []}

    def test_runs_blockers_first_and_lowest_number_first_otherwise(self) -> None:
        self.assertEqual(
            order_tasks(build_deps(self.DEPS)),
            ["run t-1", "run t-2", "run t-3", "run t-4", "run t-5"],
        )

    def test_a_blocker_with_a_higher_number_still_goes_first(self) -> None:
        self.assertEqual(
            order_tasks(build_deps({1: [3], 2: [], 3: []})), ["run t-2", "run t-3", "run t-1"]
        )

    def test_numbers_sort_as_numbers_not_text(self) -> None:
        self.assertEqual(
            order_tasks(build_deps({1: [], 2: [], 10: []})), ["run t-1", "run t-2", "run t-10"]
        )

    def test_the_example_file(self) -> None:
        self.assertEqual(order_tasks(VALID), ["run t-1", "run t-2", "run t-3", "run t-4"])

    def test_a_flagged_task_is_not_run_and_blocks_its_dependents(self) -> None:
        self.assertEqual(
            order_tasks(build_deps(self.DEPS), flagged=["t-2"]),
            ["run t-1", "run t-3", "run t-5", "skip t-4 (blocked by t-2)"],
        )

    def test_skipping_is_transitive(self) -> None:
        deps = dict(self.DEPS)
        deps[6] = [4]
        self.assertEqual(
            order_tasks(build_deps(deps), flagged=["t-2"]),
            ["run t-1", "run t-3", "run t-5", "skip t-4 (blocked by t-2)", "skip t-6 (blocked by t-4)"],
        )

    def test_a_skip_names_every_blocker_that_is_the_cause(self) -> None:
        self.assertEqual(
            order_tasks(build_deps({1: [], 2: [], 3: [1, 2]}), flagged=["t-1", "t-2"]),
            ["skip t-3 (blocked by t-1, t-2)"],
        )

    def test_done_tasks_are_not_run_again_but_satisfy_their_dependents(self) -> None:
        self.assertEqual(
            order_tasks(build_deps(self.DEPS), done=["t-1"]),
            ["run t-2", "run t-3", "run t-4", "run t-5"],
        )

    def test_done_and_flagged_together(self) -> None:
        self.assertEqual(
            order_tasks(build_deps(self.DEPS), done=["t-1"], flagged=["t-2"]),
            ["run t-3", "run t-5", "skip t-4 (blocked by t-2)"],
        )

    def test_nothing_left_gives_no_lines(self) -> None:
        self.assertEqual(order_tasks(build_deps({1: [], 2: [1]}), done=["t-1", "t-2"]), [])

    def test_an_id_that_is_not_in_the_table_is_a_usage_error(self) -> None:
        for kwargs in ({"flagged": ["t-9"]}, {"done": ["t-9"]}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(UsageError) as ctx:
                    order_tasks(build_deps(self.DEPS), **kwargs)
                self.assertIn("t-9", str(ctx.exception))

    def test_a_task_cannot_be_both_done_and_flagged(self) -> None:
        with self.assertRaises(UsageError):
            order_tasks(build_deps(self.DEPS), done=["t-1"], flagged=["t-1"])

    def test_a_cycle_is_a_data_error(self) -> None:
        with self.assertRaises(DataError) as ctx:
            order_tasks(build_deps({1: [2], 2: [1], 3: []}))
        self.assertIn("cycle", str(ctx.exception))

    def test_a_damaged_table_is_a_data_error(self) -> None:
        with self.assertRaises(DataError):
            order_tasks("# Tasks for story 1: x\n\nno table here\n")
        with self.assertRaises(DataError):
            order_tasks(VALID.replace("| t-2 | Sync on reconnect | t-1 | 3 |", "| t-2 | Sync on reconnect | t-9 | 3 |"))


if __name__ == "__main__":
    unittest.main()
