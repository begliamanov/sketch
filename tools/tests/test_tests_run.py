"""tests run: the one place the tool runs something. Real shell commands in a temp project."""

import tempfile
import time
import unittest
from pathlib import Path

from sketch_tools.tests import main

from tests.helpers import run_tool

FIXTURES = Path(__file__).parent / "fixtures"


class RunCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = base / "project"
        self.root.mkdir()
        self.logs = base / "logs"
        self.config = base / "config.md"

    def write_config(self, **keys: str) -> None:
        lines = ["# sketch config"] + ["%s: %s" % (key, value) for key, value in keys.items()]
        self.config.write_text("\n".join(lines) + "\n")

    def run_it(self, mode: str = "full", *extra: str):
        argv = ["run", "--config", str(self.config), "--mode", mode, "--logs", str(self.logs),
                "--root", str(self.root), *extra]
        return run_tool(main, argv)


class RunTest(RunCase):
    def test_runs_the_command_keeps_the_log_and_archives_the_results(self) -> None:
        command = "mkdir -p out && cp %s/junit_swiftpm.xml out/TEST-a.xml && echo ran the tests && exit 1" % FIXTURES
        self.write_config(test_full=command, test_results="out/*.xml")
        code, out, err = self.run_it()
        log = self.logs / "20261112-104100-full.log"
        results = self.logs / "20261112-104100-full.results"
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "command: %s\nexit: 1\nlog: %s\nresults: %s\nresult-files: 1\n" % (command, log, results))
        self.assertIn("ran the tests", log.read_text())
        self.assertEqual((results / "001-TEST-a.xml").read_text(), (FIXTURES / "junit_swiftpm.xml").read_text())

    def test_the_exit_code_of_the_tool_is_0_whatever_the_tests_did(self) -> None:
        self.write_config(test_full="exit 7", test_results="out/*.xml")
        code, out, _ = self.run_it()
        self.assertEqual(code, 0)
        self.assertIn("exit: 7\n", out)

    def test_old_result_files_are_removed_before_the_run(self) -> None:
        (self.root / "out").mkdir()
        (self.root / "out" / "TEST-old.xml").write_text("<old/>")
        (self.root / "out" / "keep.txt").write_text("not a result")
        self.write_config(test_full="true", test_results="out/*.xml")
        _, out, _ = self.run_it()
        self.assertFalse((self.root / "out" / "TEST-old.xml").exists())
        self.assertTrue((self.root / "out" / "keep.txt").exists())
        self.assertIn("result-files: 0\n", out)

    def test_results_in_subfolders_get_numbered_names_so_none_collide(self) -> None:
        command = "mkdir -p out/a out/b && echo '<testsuite/>' > out/a/TEST-x.xml && echo '<testsuite/>' > out/b/TEST-x.xml"
        self.write_config(test_full=command, test_results="out/**/*.xml")
        _, out, _ = self.run_it()
        results = self.logs / "20261112-104100-full.results"
        self.assertEqual(sorted(p.name for p in results.iterdir()), ["001-TEST-x.xml", "002-TEST-x.xml"])
        self.assertIn("result-files: 2\n", out)

    def test_a_task_run_fills_in_the_target(self) -> None:
        self.write_config(test_task='echo "{target}" > target.txt', test_results="out/*.xml")
        code, out, _ = self.run_it("task", "--target", "BannerTests")
        self.assertEqual(code, 0)
        self.assertEqual((self.root / "target.txt").read_text(), "BannerTests\n")
        self.assertIn("-task.log", out)

    def test_baseline_uses_the_full_command(self) -> None:
        self.write_config(test_full="echo baseline > b.txt", test_results="out/*.xml")
        self.run_it("baseline")
        self.assertTrue((self.root / "b.txt").exists())
        self.assertTrue((self.logs / "20261112-104100-baseline.log").exists())

    def test_the_command_runs_in_the_root_and_its_stdout_and_stderr_are_in_the_log(self) -> None:
        self.write_config(test_full="pwd && echo oops 1>&2", test_results="out/*.xml")
        self.run_it()
        text = (self.logs / "20261112-104100-full.log").read_text()
        self.assertIn(str(self.root.resolve()), text)
        self.assertIn("oops", text)

    def test_the_command_cannot_wait_for_input(self) -> None:
        self.write_config(test_full="cat; echo done", test_results="out/*.xml")
        started = time.time()
        _, out, _ = self.run_it()
        self.assertLess(time.time() - started, 5)
        self.assertIn("done", (self.logs / "20261112-104100-full.log").read_text())
        self.assertIn("exit: 0\n", out)

    def test_a_command_that_takes_too_long_is_stopped_and_says_so(self) -> None:
        self.write_config(test_full="sleep 30", test_results="out/*.xml")
        started = time.time()
        code, out, _ = self.run_it("full", "--timeout", "1")
        self.assertLess(time.time() - started, 15)
        self.assertEqual(code, 0)
        self.assertIn("exit: 124\n", out)
        self.assertIn("timed-out: yes\n", out)

    def test_the_logs_folder_is_created_and_two_runs_in_one_second_do_not_share_a_log(self) -> None:
        self.logs = self.logs / "deep" / "er"
        self.write_config(test_full="echo one", test_results="out/*.xml")
        self.run_it()
        self.write_config(test_full="echo two", test_results="out/*.xml")
        self.run_it()
        logs = sorted(p.name for p in self.logs.glob("*.log"))
        self.assertEqual(logs, ["20261112-104100-full-2.log", "20261112-104100-full.log"])
        self.assertIn("two", (self.logs / "20261112-104100-full-2.log").read_text())
        self.assertTrue((self.logs / "20261112-104100-full-2.results").is_dir())


class RunRefusesTest(RunCase):
    def test_a_missing_command_is_an_error_naming_the_key_and_creates_nothing(self) -> None:
        self.write_config(test_results="out/*.xml")
        code, out, err = self.run_it("full")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("test_full", err)
        self.assertFalse(self.logs.exists())

    def test_a_task_run_needs_a_target(self) -> None:
        self.write_config(test_task="echo {target}", test_results="out/*.xml")
        code, out, err = self.run_it("task")
        self.assertEqual((code, out), (3, ""))
        self.assertIn("--target", err)

    def test_the_results_pattern_is_required(self) -> None:
        self.write_config(test_full="true")
        code, _, err = self.run_it()
        self.assertEqual(code, 1)
        self.assertIn("test_results", err)

    def test_an_unsafe_results_pattern_deletes_and_runs_nothing(self) -> None:
        decoy = self.root.parent / "decoy.xml"
        decoy.write_text("<x/>")
        (self.root / "mine.txt").write_text("keep")
        for pattern in ("../*.xml", "/tmp/*.xml", "*", "**", "out/", "**/*.json", "*.xml"):
            with self.subTest(pattern=pattern):
                self.write_config(test_full="echo ran > ran.txt", test_results=pattern)
                code, out, err = self.run_it()
                self.assertEqual((code, out), (1, ""))
                self.assertIn("test_results", err)
                self.assertTrue(decoy.exists())
                self.assertTrue((self.root / "mine.txt").exists())
                self.assertFalse((self.root / "ran.txt").exists())

    def test_the_root_must_exist(self) -> None:
        self.write_config(test_full="true", test_results="out/*.xml")
        code, _, err = run_tool(main, ["run", "--config", str(self.config), "--mode", "full",
                                       "--logs", str(self.logs), "--root", str(self.root / "nope")])
        self.assertEqual(code, 3)
        self.assertIn("nope", err)

    def test_the_options_are_required(self) -> None:
        for missing in ("--config", "--mode", "--logs"):
            with self.subTest(missing=missing):
                argv = ["run", "--config", str(self.config), "--mode", "full", "--logs", str(self.logs)]
                index = argv.index(missing)
                del argv[index:index + 2]
                code, _, err = run_tool(main, argv)
                self.assertEqual(code, 3)
                self.assertIn(missing, err)

    def test_an_unknown_mode_exits_3(self) -> None:
        self.write_config(test_full="true", test_results="out/*.xml")
        self.assertEqual(self.run_it("nightly")[0], 3)


if __name__ == "__main__":
    unittest.main()
