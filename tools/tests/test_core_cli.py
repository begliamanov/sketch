"""The tool runner: dispatch, errors and the exit-code contract."""

import argparse
import unittest

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import RefusedError, UsageError

from tests.helpers import run_tool


def build_demo() -> Tool:
    tool = Tool("demo", "a demo tool")

    def configure_echo(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("word")

    def run_echo(args: argparse.Namespace, env: Env) -> int:
        env.stdout.write(args.word + "\n")
        return exitcodes.OK

    def run_bad(args: argparse.Namespace, env: Env) -> int:
        raise UsageError("that input is bad")

    def run_refuse(args: argparse.Namespace, env: Env) -> int:
        raise RefusedError("not allowed")

    def run_check_failed(args: argparse.Namespace, env: Env) -> int:
        env.stdout.write("problem found\n")
        return exitcodes.CHECK_FAILED

    tool.add_command("echo", "print a word", configure_echo, run_echo)
    tool.add_command("bad", "always bad input", lambda p: None, run_bad)
    tool.add_command("refuse", "always refuses", lambda p: None, run_refuse)
    tool.add_command("fail", "a failing check", lambda p: None, run_check_failed)
    return tool


class ExitCodeContractTest(unittest.TestCase):
    def test_codes_have_the_documented_values(self) -> None:
        self.assertEqual(
            (exitcodes.OK, exitcodes.CHECK_FAILED, exitcodes.REFUSED, exitcodes.USAGE),
            (0, 1, 2, 3),
        )

    def test_error_classes_carry_their_exit_code(self) -> None:
        self.assertEqual(UsageError("x").exit_code, 3)
        self.assertEqual(RefusedError("x").exit_code, 2)


class ToolDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = build_demo()

    def test_runs_the_named_subcommand(self) -> None:
        code, out, err = run_tool(self.tool.main, ["echo", "hello"])
        self.assertEqual((code, out, err), (0, "hello\n", ""))

    def test_uses_the_exit_code_the_handler_returns(self) -> None:
        code, out, _ = run_tool(self.tool.main, ["fail"])
        self.assertEqual((code, out), (1, "problem found\n"))

    def test_usage_error_prints_message_and_exits_3(self) -> None:
        code, out, err = run_tool(self.tool.main, ["bad"])
        self.assertEqual((code, out), (3, ""))
        self.assertEqual(err, "error: that input is bad\n")

    def test_refused_error_prints_message_and_exits_2(self) -> None:
        code, out, err = run_tool(self.tool.main, ["refuse"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: not allowed\n")

    def test_unknown_subcommand_exits_3_and_names_it(self) -> None:
        code, out, err = run_tool(self.tool.main, ["nope"])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("nope", err)

    def test_missing_subcommand_exits_3_and_lists_the_commands(self) -> None:
        code, out, err = run_tool(self.tool.main, [])
        self.assertEqual((code, out), (3, ""))
        for name in ("echo", "bad", "refuse", "fail"):
            self.assertIn(name, err)

    def test_missing_argument_exits_3(self) -> None:
        code, out, err = run_tool(self.tool.main, ["echo"])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("error:", err)

    def test_help_exits_0_and_describes_the_tool(self) -> None:
        code, out, _ = run_tool(self.tool.main, ["--help"])
        self.assertEqual(code, 0)
        self.assertIn("a demo tool", out)
        self.assertIn("print a word", out)


if __name__ == "__main__":
    unittest.main()
