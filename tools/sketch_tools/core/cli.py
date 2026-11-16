"""Tool runner: subcommand dispatch, injected I/O, and the exit-code contract."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, TextIO, Tuple


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


class Tool:
    """One tool: a name and its subcommands."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self._commands: Dict[str, Tuple[str, Configure, Handler]] = {}

    def add_command(
        self, name: str, help_text: str, configure: Configure, handler: Handler
    ) -> None:
        raise NotImplementedError

    def main(self, argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
        raise NotImplementedError
