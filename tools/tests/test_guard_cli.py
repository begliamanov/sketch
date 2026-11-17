"""guard check-command as the hook runs it: JSON in, exit code out."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sketch_tools.guard import main

from tests.helpers import run_tool

VALID_STATE = (Path(__file__).parent / "fixtures" / "state_valid.md").read_text()


def hook(command: str, tool: str = "Bash") -> str:
    return json.dumps({
        "session_id": "x", "hook_event_name": "PreToolUse", "tool_name": tool,
        "tool_input": {"command": command},
    })


class GuardCliTest(unittest.TestCase):
    def check(self, stdin: str, *args: str):
        return run_tool(main, ["check-command", *args], stdin=stdin)

    def test_an_allowed_command_exits_0_and_says_nothing(self) -> None:
        code, out, err = self.check(hook("git push -u origin story-2"), "--protect", "main")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_a_denied_command_exits_2_and_the_reason_is_on_stderr(self) -> None:
        code, out, err = self.check(hook("git push origin main"), "--protect", "main")
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("error: "))
        self.assertIn("protected", err)

    def test_several_reasons_are_all_reported(self) -> None:
        code, _, err = self.check(hook("git push -f origin story-1 && gh pr merge 5"))
        self.assertEqual(code, 2)
        self.assertIn("force", err)
        self.assertIn("merge", err)

    def test_other_tools_are_not_guarded(self) -> None:
        code, out, err = self.check(hook("git push origin main", tool="Read"), "--protect", "main")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_input_that_is_not_json_is_denied(self) -> None:
        code, _, err = self.check("git push origin main")
        self.assertEqual(code, 2)
        self.assertIn("hook input", err)

    def test_a_bash_call_without_a_command_is_denied(self) -> None:
        for payload in ('{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": {}}',
                        '{"tool_name": "Bash", "tool_input": {"command": 5}}', "[]", "null"):
            with self.subTest(payload=payload):
                code, _, _ = self.check(payload)
                self.assertEqual(code, 2)

    def test_an_unparseable_command_is_denied(self) -> None:
        code, _, err = self.check(hook("echo \"oops"))
        self.assertEqual(code, 2)
        self.assertIn("cannot parse", err)

    def test_raw_mode_reads_the_command_itself(self) -> None:
        code, _, err = self.check("git push origin main\n", "--raw", "--protect", "main")
        self.assertEqual(code, 2)
        self.assertIn("protected", err)
        code, out, _ = self.check("git status\n", "--raw")
        self.assertEqual((code, out), (0, ""))

    def test_protect_can_be_repeated(self) -> None:
        argv = ["--protect", "main", "--protect", "master"]
        self.assertEqual(self.check(hook("git push origin master"), *argv)[0], 2)
        self.assertEqual(self.check(hook("git push origin develop"), *argv)[0], 0)


class GuardFailsClosedTest(unittest.TestCase):
    def test_a_bug_inside_the_guard_blocks_the_command_and_says_so(self) -> None:
        with mock.patch("sketch_tools.guard.cli.logic.check_command", side_effect=RuntimeError("boom")):
            code, out, err = run_tool(main, ["check-command"], stdin=hook("git status"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("guard failed", err)
        self.assertIn("boom", err)


class GuardStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state.md"

    def check(self, command: str):
        return run_tool(main, ["check-command", "--protect", "main", "--state", str(self.state)],
                        stdin=hook(command))

    def test_the_feature_branch_in_the_state_is_protected(self) -> None:
        self.state.write_text(VALID_STATE)
        code, _, err = self.check("git push origin feature/offline-notes")
        self.assertEqual(code, 2)
        self.assertIn("protected", err)
        self.assertEqual(self.check("git push -u origin story-2-offline-notes")[0], 0)

    def test_without_a_state_file_only_the_listed_branches_are_protected(self) -> None:
        self.assertEqual(self.check("git push origin feature/offline-notes")[0], 0)
        self.assertEqual(self.check("git push origin main")[0], 2)

    def test_a_state_without_a_feature_branch_blocks_pushes_but_not_other_commands(self) -> None:
        self.state.write_text(VALID_STATE.replace("feature_branch: feature/offline-notes\n", ""))
        code, _, err = self.check("git push -u origin story-2-offline-notes")
        self.assertEqual(code, 2)
        self.assertIn("feature_branch", err)
        self.assertEqual(self.check("git status")[0], 0)

    def test_a_feature_branch_of_none_blocks_pushes_too(self) -> None:
        self.state.write_text(VALID_STATE.replace("feature_branch: feature/offline-notes", "feature_branch: none"))
        self.assertEqual(self.check("git push -u origin story-2")[0], 2)


if __name__ == "__main__":
    unittest.main()
