"""Pure guard rules: given a shell command, say why it must not run. No file access.

Rules (core/conventions.md): agents never merge, never force-push, never push to the feature branch
or main, never close issues. `git push` must name its branch (the PR agent already does:
`git push -u origin <story-branch>`), because without calling git there is no way to know which
branch a bare `git push` would update."""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Set

from sketch_tools.guard.shellparse import simple_commands

_GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                      "--super-prefix", "--config-env"}
_PUSH_VALUE_OPTIONS = {"--push-option", "--receive-pack", "--exec", "--repo"}
_FORGE_VALUE_OPTIONS = {"-R", "--repo", "--hostname"}
_CLOSE_VALUE_OPTIONS = {"-c", "--comment", "-r", "--reason", "--duplicate-of"} | _FORGE_VALUE_OPTIONS
_MERGE_ENDPOINT = re.compile(r"(^|/)merge($|[/?])")
_CLOSE_FIELD = re.compile(r"(state|state_event)=(closed?)")


def check_command(
    command: str, protected: Sequence[str] = (), push_block: Optional[str] = None,
    task_issues: Optional[Sequence[str]] = None, close_block: Optional[str] = None,
) -> List[str]:
    """Every reason the command must not run, one message each. Empty list means allowed.

    `protected` are branch names that may not be pushed to. `push_block`, when given, is a reason
    to refuse every `git push` (for example: the state file names no feature branch).
    `task_issues` are the issue numbers of the current story's tasks: the only issues that may be
    closed. `close_block`, when given, is the reason no close can be checked (no usable state)."""
    try:
        commands = simple_commands(command)
    except ValueError as err:
        return ["cannot parse the command (" + str(err) + "): rewrite it as plain commands"]
    reasons: List[str] = []
    for tokens in commands:
        for reason in _check_one(tokens, set(protected), push_block, set(task_issues or ()), close_block):
            if reason not in reasons:
                reasons.append(reason)
    return reasons


def _check_one(
    tokens: List[str], protected: Set[str], push_block: Optional[str],
    task_issues: Set[str], close_block: Optional[str],
) -> List[str]:
    if tokens[0] == "git":
        return _check_git(tokens[1:], protected, push_block)
    if tokens[0] in ("gh", "glab"):
        return _check_forge(tokens[0], tokens[1:], task_issues, close_block)
    return []


def _check_git(args: List[str], protected: Set[str], push_block: Optional[str]) -> List[str]:
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in _GIT_VALUE_OPTIONS else 1
    if index >= len(args):
        return []
    subcommand, rest = args[index], args[index + 1 :]
    if subcommand == "merge":
        return ["git merge is not allowed: agents never merge, the developer merges the story PR"]
    if subcommand == "push":
        return [push_block] if push_block else _check_push(rest, protected)
    return []


def _check_push(args: List[str], protected: Set[str]) -> List[str]:
    reasons: List[str] = []
    positionals: List[str] = []
    force = everything = delete = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positionals.extend(args[index + 1 :])
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in ("--force", "--force-with-lease", "--force-if-includes"):
                force = True
            elif name in ("--all", "--mirror", "--prune"):
                everything = True
            elif name == "--delete":
                delete = True
            elif name in _PUSH_VALUE_OPTIONS and "=" not in arg:
                index += 1
        elif arg.startswith("-") and len(arg) > 1:
            cluster = arg[1:]
            force = force or "f" in cluster
            delete = delete or "d" in cluster
            if cluster == "o":
                index += 1
        else:
            positionals.append(arg)
        index += 1

    refspecs = positionals[1:]  # the first positional is the remote
    if not refspecs:
        reasons.append("git push needs an explicit branch, like: git push -u origin <story-branch>")
    for refspec in refspecs:
        if "$" in refspec or "`" in refspec:  # a variable or a substitution: not spelled out
            reasons.append("git push needs an explicit branch, like: git push -u origin <story-branch>")
            continue
        if refspec.startswith("+"):
            force = True
            refspec = refspec[1:]
        source, _, target = refspec.partition(":") if ":" in refspec else (refspec, "", refspec)
        if ":" in refspec and source == "":
            delete = True
        target = target[len("refs/heads/"):] if target.startswith("refs/heads/") else target
        if target.startswith("refs/tags/"):
            continue
        if target in ("HEAD", "@"):
            reasons.append("git push needs an explicit branch, like: git push -u origin <story-branch>")
        elif target in protected:
            reasons.append(
                "git push to " + target + " is not allowed: it is a protected branch, "
                "push your story branch instead"
            )
    if force:
        reasons.append("git push --force is not allowed: Sketch never force-pushes")
    if everything:
        reasons.append("git push --all, --mirror and --prune are not allowed: they push or remove every branch")
    if delete:
        reasons.append("git push cannot delete a remote branch")
    return reasons


def _check_close(tool: str, args: List[str], task_issues: Set[str], close_block: Optional[str]) -> List[str]:
    """`args` follow `issue close`. Only a number in `task_issues` may be closed."""
    if close_block:
        return [close_block]
    numbers: List[str] = []
    unknown = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in _CLOSE_VALUE_OPTIONS:
            index += 1  # the next word is this option's value, not an issue number
        elif arg.startswith("-"):
            # only a known option with its value attached (--comment=x) is understood; any other
            # option might take a value that hides an issue number, so it blocks
            unknown = unknown or arg.split("=", 1)[0] not in _CLOSE_VALUE_OPTIONS or "=" not in arg
        else:
            numbers.append(arg.lstrip("#"))
        index += 1
    if not unknown and len(numbers) == 1 and numbers[0] in task_issues:
        return []
    shown = numbers[0] if len(numbers) == 1 and not unknown else "<unclear number>"
    return [
        tool + " issue close " + shown
        + " is not allowed: it is not a task issue of the current story"
    ]


def _check_forge(
    tool: str, args: List[str], task_issues: Set[str] = frozenset(), close_block: Optional[str] = None
) -> List[str]:
    positionals: List[str] = []
    index = 0
    while index < len(args) and len(positionals) < 2:
        arg = args[index]
        if arg in _FORGE_VALUE_OPTIONS:
            index += 1
        elif not arg.startswith("-"):
            positionals.append(arg)
        index += 1
    if positionals[:1] == ["api"]:
        reasons: List[str] = []
        if any(_MERGE_ENDPOINT.search(arg) for arg in args):
            reasons.append(tool + " api call to a merge endpoint is not allowed: agents never merge")
        if any(_CLOSE_FIELD.fullmatch(arg) for arg in args):
            reasons.append(tool + " api call that closes an issue is not allowed: agents never close issues through the api")
        return reasons
    if positionals[1:2] == ["merge"] and positionals[0] in ("pr", "mr"):
        return [tool + " " + positionals[0] + " merge is not allowed: agents never merge"]
    if positionals == ["issue", "close"]:
        close_args = args[args.index("close") + 1 :]
        return _check_close(tool, close_args, task_issues, close_block)
    return []
