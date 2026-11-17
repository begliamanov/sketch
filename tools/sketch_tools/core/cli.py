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

    def command_names(self) -> List[str]:
        """Every registered command, as typed: `set`, `flag add`, ..."""
        return list(self._commands)

    def _groups(self) -> Dict[str, List[str]]:
        """Command groups: names given as "group leaf", mapped to their leaf names in order."""
        groups: Dict[str, List[str]] = {}
        for name in self._commands:
            if " " in name:
                group, leaf = name.split(" ", 1)
                groups.setdefault(group, []).append(leaf)
        return groups

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = _Parser(prog=self.name, description=self.description)
        sub = parser.add_subparsers(dest="command", parser_class=_Parser, metavar="<command>")
        group_actions: Dict[str, Any] = {}
        for name, (help_text, configure, _handler) in self._commands.items():
            if " " not in name:
                configure(sub.add_parser(name, help=help_text, description=help_text))
                continue
            group, leaf = name.split(" ", 1)
            if group not in group_actions:
                group_parser = sub.add_parser(
                    group, help=group + " commands", description=group + " commands"
                )
                group_actions[group] = group_parser.add_subparsers(
                    dest="subcommand", parser_class=_Parser, metavar="<command>"
                )
            configure(group_actions[group].add_parser(leaf, help=help_text, description=help_text))
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
            raise UsageError("missing command. Commands: " + ", ".join(self._top_level_names()))
        name: str = args.command
        groups = self._groups()
        if name in groups:
            leaf = getattr(args, "subcommand", None)
            if leaf is None:
                raise UsageError(
                    "missing command for " + name + ". Commands: " + ", ".join(groups[name])
                )
            name = name + " " + leaf
        handler: Handler = self._commands[name][2]
        result: Any = handler(args, env)
        return int(result)

    def _top_level_names(self) -> List[str]:
        names: List[str] = []
        for name in self._commands:
            top = name.split(" ", 1)[0]
            if top not in names:
                names.append(top)
        return names
