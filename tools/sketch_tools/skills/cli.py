"""Command-line layer of the skills tool: walks the folders it is pointed at."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from sketch_tools.core import exitcodes
from sketch_tools.core.cli import Env, Tool
from sketch_tools.core.errors import UsageError
from sketch_tools.skills.logic import Skill, parse_skill

_SKIPPED = {"node_modules", "__pycache__"}


def _skill_files(folder: str) -> List[str]:
    """Every SKILL.md under `folder`, following links but never twice, skipping hidden and vendored folders."""
    found: List[str] = []
    seen = set()
    for root, dirs, files in os.walk(folder, followlinks=True):
        real = os.path.realpath(root)
        if real in seen:
            dirs[:] = []
            continue
        seen.add(real)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in _SKIPPED)
        if "SKILL.md" in files:
            found.append(os.path.abspath(os.path.join(root, "SKILL.md")))
    return found


def _configure_list(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dir", required=True, action="append", metavar="DIR",
                        help="a folder to search for SKILL.md files. Repeat for more.")
    parser.add_argument("--json", action="store_true", help="print a JSON list instead of tab-separated lines")


def _run_list(args: argparse.Namespace, env: Env) -> int:
    skills: Dict[str, Skill] = {}
    for folder in args.dir:
        if not Path(folder).is_dir():
            raise UsageError("folder does not exist: " + folder)
        for path in _skill_files(folder):
            if path not in skills:
                skills[path] = parse_skill(path, Path(path).read_text(encoding="utf-8", errors="replace"))
    ordered = sorted(skills.values(), key=lambda skill: (skill.name, skill.path))
    if args.json:
        env.stdout.write(json.dumps([{"name": s.name, "description": s.description, "path": s.path} for s in ordered]) + "\n")
    else:
        for skill in ordered:
            env.stdout.write(skill.name + "\t" + skill.path + "\t" + skill.description + "\n")
    return exitcodes.OK


def build_tool() -> Tool:
    tool = Tool("skills", "Find the SKILL.md files on this machine.")
    tool.add_command("list", "list every SKILL.md under the folders, with its name and description", _configure_list, _run_list)
    return tool


def main(argv: Optional[List[str]] = None, env: Optional[Env] = None) -> int:
    return build_tool().main(argv, env)
