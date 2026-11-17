"""Command-line layer of the report tool: reads the report on stdin, saves and reads files in the
reports folder it is pointed at.

A report is `<reports>/<scope>-<role>-<run>.json`. The orchestrator picks the run number for each
agent it starts (1, 2, ... per scope and role) and tells the agent, so a report left over from an
earlier round can never stand in for one that was not submitted."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import DataError, RefusedError, UsageError
from sketch_tools.core.files import atomic_write
from sketch_tools.report import logic


def _add_target(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--role", required=True, metavar="ROLE", help="the agent role, like implementer")
    parser.add_argument("--scope", required=True, metavar="SCOPE", help="t-3 for a task role, story-2 for a story role")
    parser.add_argument("--run", required=True, type=int, metavar="N", help="which start of this agent, 1 or more")
    parser.add_argument("--reports", required=True, metavar="DIR", help="the reports folder")


def _target(args: argparse.Namespace) -> Path:
    """Check role, scope and run, and give the report's path."""
    logic.known_role(args.role, args.scope)
    if args.run < 1:
        raise UsageError("run must be 1 or more")
    folder = Path(args.reports)
    if not folder.is_dir():
        raise UsageError("folder does not exist: " + str(folder))
    return folder / logic.report_name(args.scope, args.role, args.run)


def _read(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _no_report(path: Path) -> str:
    return "no report " + path.name + " was submitted (looked in " + str(path.parent) + ")"


def _configure_submit(parser: argparse.ArgumentParser) -> None:
    _add_target(parser)


def _run_submit(args: argparse.Namespace, env: Env) -> int:
    path = _target(args)
    try:
        report = json.loads(env.stdin.read())
    except ValueError as err:
        raise UsageError("the report is not valid JSON: " + str(err)) from None
    problems = logic.validate(args.role, args.scope, report)
    if problems:
        for problem in problems:
            env.stdout.write("error: " + problem + "\n")
        return exitcodes.CHECK_FAILED
    if path.exists():
        raise RefusedError(
            "report " + path.name + " already exists and is never overwritten: use the next run number"
        )
    submitted = env.now().strftime("%Y-%m-%d %H:%M")
    try:
        atomic_write(path, logic.make_document(args.role, args.scope, args.run, submitted, report))
    except OSError as err:
        raise UsageError("cannot write " + str(path) + ": " + str(err.strerror)) from err
    env.stdout.write("ok: saved " + str(path) + "\n")
    return exitcodes.OK


def _configure_check(parser: argparse.ArgumentParser) -> None:
    _add_target(parser)
    parser.add_argument("--skills", action="append", default=[], metavar="PATH",
                        help="a skill from the agent's brief that must be in skills_applied. Repeat for more.")


def _run_check(args: argparse.Namespace, env: Env) -> int:
    path = _target(args)
    text = _read(path)
    problems = (
        [_no_report(path)] if text is None
        else logic.check_document(text, args.role, args.scope, args.run, args.skills)
    )
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def _configure_get(parser: argparse.ArgumentParser) -> None:
    _add_target(parser)
    parser.add_argument("--json", action="store_true", help="print the value as JSON, whatever it is")
    parser.add_argument("field", metavar="FIELD", help="a field of the report, like verdict or verification.command")


def _run_get(args: argparse.Namespace, env: Env) -> int:
    path = _target(args)
    text = _read(path)
    if text is None:
        raise DataError(_no_report(path))
    try:
        value = logic.get_field(text, args.field)
    except KeyError:
        raise DataError("no field " + args.field + " in " + path.name) from None
    if args.json:
        env.stdout.write(json.dumps(value, ensure_ascii=False) + "\n")
    else:
        printed = logic.format_value(value)
        env.stdout.write(printed + "\n" if printed else "")
    return exitcodes.OK


def build_tool() -> Tool:
    tool = Tool("report", "Agents hand in their report as JSON; it is checked when it is written.")
    tool.add_command(
        "submit", "stdin: the report as JSON. Saved only when valid; every problem is listed.",
        _configure_submit, _run_submit,
    )
    tool.add_command(
        "check", "a valid report for this role, scope and run exists (and names every brief skill)",
        _configure_check, _run_check,
    )
    tool.add_command("get", "print one field of a saved report", _configure_get, _run_get)
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
