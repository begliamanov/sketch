"""plan: the command-line behavior, with real files."""

import tempfile
import unittest
from pathlib import Path

from sketch_tools.plan import main

from tests.helpers import run_tool
from tests.test_plan_config import VALID as CONFIG
from tests.test_plan_tasks import VALID as TASKS, chain


class PlanCliCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.tasks = self.dir / "tasks.md"
        self.tasks.write_text(TASKS)


class TasksCheckCliTest(PlanCliCase):
    def test_ok(self) -> None:
        code, out, err = run_tool(main, ["tasks-check", "--tasks", str(self.tasks)])
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_problems_one_per_line_and_exit_1(self) -> None:
        self.tasks.write_text(TASKS.replace("# Tasks for story 2: Offline notes list", "# Tasks"))
        code, out, err = run_tool(main, ["tasks-check", "--tasks", str(self.tasks)])
        self.assertEqual((code, err), (1, ""))
        self.assertTrue(out.startswith("error: "))
        self.assertIn("first line", out)

    def test_the_task_count_options(self) -> None:
        self.tasks.write_text(chain(2))
        self.assertEqual(run_tool(main, ["tasks-check", "--tasks", str(self.tasks)])[0], 1)
        argv = ["tasks-check", "--tasks", str(self.tasks), "--min-tasks", "2"]
        self.assertEqual(run_tool(main, argv)[:2], (0, "ok\n"))
        self.tasks.write_text(chain(9))
        argv = ["tasks-check", "--tasks", str(self.tasks), "--max-tasks", "9"]
        self.assertEqual(run_tool(main, argv)[:2], (0, "ok\n"))

    def test_a_missing_file_exits_3(self) -> None:
        code, out, err = run_tool(main, ["tasks-check", "--tasks", str(self.dir / "nope.md")])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope.md", err)

    def test_the_path_is_required(self) -> None:
        code, _, err = run_tool(main, ["tasks-check"])
        self.assertEqual(code, 3)
        self.assertIn("--tasks", err)


class TasksOrderCliTest(PlanCliCase):
    def test_prints_the_order(self) -> None:
        code, out, _ = run_tool(main, ["tasks-order", "--tasks", str(self.tasks)])
        self.assertEqual((code, out), (0, "run t-1\nrun t-2\nrun t-3\nrun t-4\n"))

    def test_flagged_and_done_take_comma_separated_ids(self) -> None:
        argv = ["tasks-order", "--tasks", str(self.tasks), "--done", "t-1", "--flagged", "t-2,t-9x"]
        code, _, _ = run_tool(main, argv)
        self.assertEqual(code, 3)
        argv = ["tasks-order", "--tasks", str(self.tasks), "--done", "t-1", "--flagged", "t-2"]
        code, out, _ = run_tool(main, argv)
        self.assertEqual((code, out), (0, "run t-3\nskip t-4 (blocked by t-2)\n"))

    def test_an_unknown_id_exits_3(self) -> None:
        code, out, err = run_tool(main, ["tasks-order", "--tasks", str(self.tasks), "--flagged", "t-9"])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("t-9", err)

    def test_a_cycle_exits_1(self) -> None:
        from tests.test_plan_tasks import build_deps

        self.tasks.write_text(build_deps({1: [2], 2: [1], 3: []}))
        code, out, err = run_tool(main, ["tasks-order", "--tasks", str(self.tasks)])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("cycle", err)

    def test_nothing_to_run_prints_nothing(self) -> None:
        argv = ["tasks-order", "--tasks", str(self.tasks), "--done", "t-1,t-2,t-3,t-4"]
        self.assertEqual(run_tool(main, argv)[:2], (0, ""))


class ConfigCheckCliTest(PlanCliCase):
    def setUp(self) -> None:
        super().setUp()
        self.skills = self.dir / "skills"
        text = CONFIG
        for name in ("common", "glossary", "testing", "kotlin", "compose"):
            folder = self.skills / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("---\nname: " + name + "\n---\n")
            text = text.replace("/skills/" + name + "/", str(folder) + "/")
        self.config = self.dir / "config.md"
        self.config.write_text(text)

    def test_ok_when_every_skill_file_exists(self) -> None:
        code, out, err = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_a_missing_skill_file_is_reported_and_exits_1(self) -> None:
        (self.skills / "kotlin" / "SKILL.md").unlink()
        code, out, _ = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertIn("does not exist", out)
        self.assertIn(str(self.skills / "kotlin" / "SKILL.md"), out)

    def plugin_folder(self, source: str) -> Path:
        folder = self.dir / "formats"
        folder.mkdir()
        (folder / "plain.py").write_text(source)
        return folder

    def use_plugin_format(self, folder: Path) -> None:
        text = self.config.read_text().replace(
            "test_format: junit-xml", "test_format: plain\nformats_dir: " + str(folder))
        self.config.write_text(text)

    def test_a_format_from_the_projects_formats_dir_is_accepted(self) -> None:
        folder = self.plugin_folder('FORMAT = "plain"\ndef read(text):\n    return []\n')
        self.use_plugin_format(folder)
        code, out, _ = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual((code, out), (0, "ok\n"))

    def test_a_format_that_is_in_no_folder_is_reported_with_the_known_ones(self) -> None:
        self.config.write_text(self.config.read_text().replace("test_format: junit-xml", "test_format: plain"))
        code, out, _ = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertIn('test_format "plain"', out)
        self.assertIn("junit-xml", out)

    def test_a_broken_reader_in_formats_dir_is_a_problem_naming_the_file(self) -> None:
        folder = self.plugin_folder("def (:\n")
        self.use_plugin_format(folder)
        code, out, _ = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertIn("formats_dir", out)
        self.assertIn("plain.py", out)

    def test_a_formats_dir_that_does_not_exist_is_a_problem(self) -> None:
        self.use_plugin_format(self.dir / "no-such-folder")
        code, out, _ = run_tool(main, ["config-check", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertIn("formats_dir", out)

    def test_a_missing_config_exits_3(self) -> None:
        code, out, err = run_tool(main, ["config-check", "--config", str(self.dir / "nope.md")])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope.md", err)

    def test_the_path_is_required(self) -> None:
        code, _, err = run_tool(main, ["config-check"])
        self.assertEqual(code, 3)
        self.assertIn("--config", err)


if __name__ == "__main__":
    unittest.main()
