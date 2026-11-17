"""pr: the command-line behavior, with real files and piped text."""

import json
import tempfile
import unittest
from pathlib import Path

from sketch_tools.pr import main

from tests.helpers import run_tool
from tests.test_pr_logic import FINISHED, FLAG_LINE, FULL, MINIMAL, NO_FLAGS, CheckBaseTest


class PrCliCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.state = self.dir / "state.md"
        self.state.write_text(FINISHED)
        self.extras = self.dir / "extras.json"
        self.extras.write_text(json.dumps(FULL))


class RenderBodyCliTest(PrCliCase):
    def run_render(self, *extra: str):
        return run_tool(main, ["render-body", "--state", str(self.state), "--extras", str(self.extras), *extra])

    def test_prints_the_description(self) -> None:
        code, out, err = self.run_render()
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.startswith("Story 2: Offline notes list (#120)\n"))
        self.assertIn(FLAG_LINE + "\n", out)

    def test_bad_extras_exit_3(self) -> None:
        self.extras.write_text("{nope")
        code, out, err = self.run_render()
        self.assertEqual((code, out), (3, ""))
        self.assertIn("JSON", err)

    def test_over_the_limit_exits_1_and_prints_no_description(self) -> None:
        self.extras.write_text(json.dumps(dict(MINIMAL, manual_checks=["item %d" % i for i in range(20)])))
        code, out, err = self.run_render()
        self.assertEqual((code, out), (1, ""))
        self.assertIn("limit 20", err)
        self.assertEqual(self.run_render("--max-lines", "40")[0], 0)

    def test_a_missing_file_exits_3(self) -> None:
        self.state.unlink()
        code, out, err = self.run_render()
        self.assertEqual((code, out), (3, ""))
        self.assertIn("state.md", err)

    def test_both_paths_are_required(self) -> None:
        code, _, err = run_tool(main, ["render-body", "--state", str(self.state)])
        self.assertEqual(code, 3)
        self.assertIn("--extras", err)


class CheckBaseCliTest(PrCliCase):
    def test_ok(self) -> None:
        stdin = json.dumps(CheckBaseTest.GITHUB)
        code, out, err = run_tool(main, ["check-base", "--base", "feature/offline-notes"], stdin=stdin)
        self.assertEqual((code, out, err), (0, "ok\n", ""))

    def test_a_wrong_base_exits_1(self) -> None:
        stdin = json.dumps(dict(CheckBaseTest.GITHUB, baseRefName="main"))
        code, out, _ = run_tool(main, ["check-base", "--base", "feature/offline-notes"], stdin=stdin)
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("error: "))

    def test_head_is_optional_and_checked_when_given(self) -> None:
        stdin = json.dumps(CheckBaseTest.GITLAB)
        argv = ["check-base", "--base", "feature/offline-notes", "--head", "story-9"]
        self.assertEqual(run_tool(main, argv, stdin=stdin)[0], 1)

    def test_input_that_is_not_json_exits_3(self) -> None:
        code, out, _ = run_tool(main, ["check-base", "--base", "main"], stdin="not json")
        self.assertEqual((code, out), (3, ""))

    def test_the_base_is_required(self) -> None:
        code, _, err = run_tool(main, ["check-base"], stdin="{}")
        self.assertEqual(code, 3)
        self.assertIn("--base", err)


class CheckFlagsCliTest(PrCliCase):
    def test_ok_for_a_rendered_description(self) -> None:
        _, body, _ = run_tool(main, ["render-body", "--state", str(self.state), "--extras", str(self.extras)])
        code, out, _ = run_tool(main, ["check-flags", "--state", str(self.state), "--extras", str(self.extras)], stdin=body)
        self.assertEqual((code, out), (0, "ok\n"))

    def test_a_missing_flag_exits_1(self) -> None:
        code, out, _ = run_tool(main, ["check-flags", "--state", str(self.state)], stdin="nothing here\n")
        self.assertEqual(code, 1)
        self.assertIn("t-4: tests keep failing", out)

    def test_extras_are_optional(self) -> None:
        self.state.write_text(NO_FLAGS)
        code, out, _ = run_tool(main, ["check-flags", "--state", str(self.state)], stdin="anything\n")
        self.assertEqual((code, out), (0, "ok\n"))

    def test_the_state_is_required(self) -> None:
        code, _, err = run_tool(main, ["check-flags"], stdin="x")
        self.assertEqual(code, 3)
        self.assertIn("--state", err)


if __name__ == "__main__":
    unittest.main()
