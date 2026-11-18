"""Command-line layer of the tests tool: reads the config and result folders it is pointed at.

`run` is the only command that runs anything. Every other command reads a results folder, which
`run` prints and keeps next to its log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import DataError, UsageError
from sketch_tools.tests import logic
from sketch_tools.tests.model import Case
from sketch_tools.tests.readers import SYSTEM_FAILURES, Reader, get_reader, load_plugins
from sketch_tools.tests.runner import run_tests
from sketch_tools.tests.settings import MODES, Settings, parse_settings


def _settings(args: argparse.Namespace) -> Settings:
    path = Path(args.config)
    try:
        return parse_settings(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise UsageError("cannot read " + str(path) + ": " + str(err.strerror)) from err


def _reader(settings: Settings) -> Reader:
    if not settings.test_format:
        raise DataError("the config has no test_format: line")
    plugins = load_plugins(Path(settings.formats_dir)) if settings.formats_dir else {}
    return get_reader(settings.test_format, plugins)


def _read_folder(folder_text: str, reader: Reader) -> Tuple[int, List[Case]]:
    """How many result files the folder holds, and every case in them, in file-name order."""
    folder = Path(folder_text)
    if not folder.is_dir():
        raise UsageError("folder does not exist: " + str(folder))
    files = sorted(path for path in folder.iterdir() if path.is_file())
    cases: List[Case] = []
    for path in files:
        try:
            cases.extend(reader(path.read_text(encoding="utf-8")))
        except ValueError as err:
            raise DataError(str(path) + ": " + str(err)) from None
    return len(files), cases


def _cases(args: argparse.Namespace, folder_text: str) -> Tuple[int, List[Case]]:
    return _read_folder(folder_text, _reader(_settings(args)))


def _system_failures(args: argparse.Namespace, folder_text: str) -> List[Case]:
    """The system failures in a results folder, for formats whose runner reports them."""
    settings = _settings(args)
    plugins = load_plugins(Path(settings.formats_dir)) if settings.formats_dir else {}
    reader = SYSTEM_FAILURES.get(settings.test_format) if settings.test_format not in plugins else None
    if reader is None:
        return []
    found: List[Case] = []
    for path in sorted(p for p in Path(folder_text).iterdir() if p.is_file()):
        try:
            found.extend(reader(path.read_text(encoding="utf-8")))
        except ValueError as err:
            raise DataError(str(path) + ": " + str(err)) from None
    return found


def _add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, metavar="PATH", help="the config file")


def _add_results(parser: argparse.ArgumentParser) -> None:
    _add_config(parser)
    parser.add_argument("--results", required=True, metavar="DIR", help="a results folder, as `run` printed it")


def _add_before_after(parser: argparse.ArgumentParser) -> None:
    _add_config(parser)
    parser.add_argument("--before", required=True, metavar="DIR", help="the earlier results folder")
    parser.add_argument("--after", required=True, metavar="DIR", help="the later results folder")


# ---- run

def _configure_run(parser: argparse.ArgumentParser) -> None:
    _add_config(parser)
    parser.add_argument("--mode", required=True, choices=MODES, help="baseline or full: test_full; task: test_task")
    parser.add_argument("--target", metavar="TESTS", help="task mode: what replaces {target} in test_task")
    parser.add_argument("--logs", required=True, metavar="DIR", help="where the log and the results folder go")
    parser.add_argument("--root", default=".", metavar="DIR", help="the project folder to run in (default: here)")
    parser.add_argument("--timeout", type=int, metavar="SECONDS", help="stop the command after this long")


def _run_run(args: argparse.Namespace, env: Env) -> int:
    root = Path(args.root)
    if not root.is_dir():
        raise UsageError("folder does not exist: " + str(root))
    outcome = run_tests(_settings(args), args.mode, args.target, root, Path(args.logs), env.now(), args.timeout)
    env.stdout.write("command: " + outcome.command + "\n")
    env.stdout.write("exit: " + str(outcome.exit_code) + "\n")
    if outcome.timed_out:
        env.stdout.write("timed-out: yes\n")
    env.stdout.write("log: " + str(outcome.log) + "\n")
    env.stdout.write("results: " + str(outcome.results_dir) + "\n")
    env.stdout.write("result-files: " + str(outcome.result_files) + "\n")
    return exitcodes.OK


# ---- reading one results folder

def _run_failures(args: argparse.Namespace, env: Env) -> int:
    for case in logic.failing(_cases(args, args.results)[1]):
        env.stdout.write(case.name + (": " + case.message if case.message else "") + "\n")
    return exitcodes.OK


def _configure_summary(parser: argparse.ArgumentParser) -> None:
    _add_results(parser)
    parser.add_argument("--json", action="store_true", help="print one JSON object")


def _run_summary(args: argparse.Namespace, env: Env) -> int:
    counts = logic.summarize(_cases(args, args.results)[1])
    system = _system_failures(args, args.results)
    if args.json:
        data: Dict[str, Any] = dict(counts)
        if system:
            data["system_failures"] = [{"name": case.name, "message": case.message} for case in system]
        env.stdout.write(json.dumps(data) + "\n")
    else:
        for status, count in counts.items():
            env.stdout.write(status + " " + str(count) + "\n")
        for case in system:
            env.stdout.write(logic.describe_system_failures([case]) + "\n")
    return exitcodes.OK


def _configure_classify(parser: argparse.ArgumentParser) -> None:
    _add_results(parser)
    parser.add_argument("--exit", required=True, type=int, metavar="CODE", help="the exit code `run` printed")


def _run_classify(args: argparse.Namespace, env: Env) -> int:
    files, cases = _cases(args, args.results)
    result, reason = logic.classify(args.exit, files, cases, _system_failures(args, args.results))
    env.stdout.write(result + "\n")
    if reason:
        env.stdout.write("reason: " + reason + "\n")
    return exitcodes.OK if result == logic.PASS else exitcodes.CHECK_FAILED


def _configure_expect_red(parser: argparse.ArgumentParser) -> None:
    _add_results(parser)
    parser.add_argument("--test", required=True, action="append", metavar="NAME",
                        help="a test that must have failed, named as the results name it. Repeat for more.")


def _run_expect_red(args: argparse.Namespace, env: Env) -> int:
    problems, reviews = logic.expect_red(_cases(args, args.results)[1], args.test)
    if not problems and not reviews:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    for review in reviews:
        env.stdout.write("review: " + review + "\n")
    return exitcodes.CHECK_FAILED if problems else exitcodes.OK


# ---- comparing two results folders

def _before_after(args: argparse.Namespace) -> Tuple[List[Case], List[Case]]:
    reader = _reader(_settings(args))
    return _read_folder(args.before, reader)[1], _read_folder(args.after, reader)[1]


def _run_skipped_diff(args: argparse.Namespace, env: Env) -> int:
    before, after = _before_after(args)
    problems = logic.skipped_diff(before, after)
    if not problems:
        env.stdout.write("ok\n")
        return exitcodes.OK
    for problem in problems:
        env.stdout.write("error: " + problem + "\n")
    return exitcodes.CHECK_FAILED


def _run_failures_diff(args: argparse.Namespace, env: Env) -> int:
    before, after = _before_after(args)
    stuck, lines = logic.failures_diff(before, after)
    env.stdout.write(("same" if stuck else "progress") + "\n")
    for line in lines:
        env.stdout.write(line + "\n")
    return exitcodes.CHECK_FAILED if stuck else exitcodes.OK


def build_tool() -> Tool:
    tool = Tool("tests", "Run the project's tests once, and read their structured results.")
    tool.add_command(
        "run", "run the configured test command once; keep its log and its result files", _configure_run, _run_run
    )
    tool.add_command("failures", "list the failing tests, name and first line", _add_results, _run_failures)
    tool.add_command("summary", "count passed, failed and skipped tests", _configure_summary, _run_summary)
    tool.add_command(
        "classify", "PASS, FAIL, CANNOT RUN or UNKNOWN, from the exit code and the results",
        _configure_classify, _run_classify,
    )
    tool.add_command(
        "expect-red", "each named test ran and failed (an error instead of an assertion is flagged for review)",
        _configure_expect_red, _run_expect_red,
    )
    tool.add_command(
        "skipped-diff", "a test skipped or lost between two runs", _add_before_after, _run_skipped_diff
    )
    tool.add_command(
        "failures-diff", "do two runs fail the same tests? (exit 1: stuck)", _add_before_after, _run_failures_diff
    )
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
