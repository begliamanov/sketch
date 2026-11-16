"""Tool runner: subcommand dispatch, injected I/O, and the exit-code contract."""

from __future__ import annotations

import argparse
import contextlib
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, NoReturn, Optional, TextIO, Tuple

from sketch_tools.core import exitcodes
from sketch_tools.core.errors import ToolError, UsageError


@dataclass
class Env:
    """Everything a command may touch besides the files it is pointed at."""

    stdin: TextIO
    stdout: TextIO
    stderr: TextIO
    now: Callable[[], datetime]

    @classmethod
    def real(cls) -> "Env":
        return cls(sys.stdin, sys.stdout, sys.stderr, datetime.now)


Configure = Callable[[argparse.ArgumentParser], None]
Handler = Callable[[argparse.Namespace, Env], int]


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that reports bad usage as a UsageError instead of exiting."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


class Tool:
    """One tool: a name and its subcommands."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self._commands: Dict[str, Tuple[str, Configure, Handler]] = {}

    def add_command(
        self, name: str, help_text: str, configure: Configure, handler: Handler
    ) -> None:
        if name in self._commands:
            raise ValueError("command already registered: " + name)
        self._commands[name] = (help_text, configure, handler)

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = _Parser(prog=self.name, description=self.description)
        sub = parser.add_subparsers(dest="command", parser_class=_Parser, metavar="<command>")
        for name, (help_text, configure, _handler) in self._commands.items():
            configure(sub.add_parser(name, help=help_text, description=help_text))
        return parser

    def main(self, argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
        env = env or Env.real()
        args_in = sys.argv[1:] if argv is None else argv
        try:
            return self._run(args_in, env)
        except ToolError as err:
            env.stderr.write("error: " + str(err) + "\n")
            return int(err.exit_code)

    def _run(self, argv: List[str], env: Env) -> int:
        parser = self._build_parser()
        try:
            with contextlib.redirect_stdout(env.stdout):
                args = parser.parse_args(argv)
        except SystemExit as stop:  # --help
            return int(stop.code or exitcodes.OK)
        if args.command is None:
            raise UsageError("missing command. Commands: " + ", ".join(self._commands))
        handler: Handler = self._commands[args.command][2]
        result: Any = handler(args, env)
        return int(result)
