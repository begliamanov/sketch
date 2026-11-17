"""Split a shell command line into the simple commands it would run. Best effort: it follows
`;`, `&&`, `||`, `|`, newlines, `( )`, `$( )`, backticks, `bash -c '...'` and `eval`, and it strips
heredoc bodies (data, not commands). It cannot see what a script, a variable or `python -c` does."""

from __future__ import annotations

import os
import re
import shlex
from typing import List, Tuple

_WRAPPERS = {"env", "command", "sudo", "doas", "nice", "nohup", "time", "exec", "builtin",
             "stdbuf", "timeout", "ionice", "setsid"}
# options of those wrappers that take a value (`sudo -u root`, `env -u NAME`, `nice -n 5`)
_VALUE_FLAGS = {"-u", "-g", "-C", "-h", "-p", "-n", "-s", "-t", "-k", "-o", "-r", "-D", "-T", "-U", "-R"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_DURATION = re.compile(r"\d+(\.\d+)?[smhd]?")
_HEREDOC = re.compile(r"(?<!<)<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_PUNCTUATION = ";()<>|&\n"


def simple_commands(command: str) -> List[List[str]]:
    """Every simple command in the line, as a list of words, with wrappers (`sudo`, `env`,
    `command`, `VAR=x`) removed. Raises ValueError when the line cannot be parsed."""
    return _parse(command, strict=True)


def _parse(command: str, strict: bool) -> List[List[str]]:
    text, shell_scripts = _strip_heredocs(command)
    found: List[List[str]] = []
    try:
        words = _split_words(text)
    except ValueError:
        if strict:
            raise
        return found
    for tokens in words:
        tokens = _strip_prefix(tokens)
        if not tokens:
            continue
        found.append(tokens)
        for script in _nested_scripts(tokens):
            found.extend(_parse(script, strict=False))
    for inner in _substitutions(text):
        found.extend(_parse(inner, strict=False))
    for script in shell_scripts:
        found.extend(_parse(script, strict=False))
    return found


def _strip_heredocs(command: str) -> Tuple[str, List[str]]:
    """Remove heredoc bodies. A body that a shell reads (`bash <<EOF`) is returned as a script."""
    lines = command.split("\n")
    kept: List[str] = []
    scripts: List[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        match = _HEREDOC.search(line)
        if not match:
            index += 1
            continue
        end = index + 1
        body: List[str] = []
        while end < len(lines) and lines[end].strip() != match.group(2):
            body.append(lines[end])
            end += 1
        words = line.split()
        if words and os.path.basename(words[0]) in _SHELLS:
            scripts.append("\n".join(body))
        index = end + 1  # skip the terminator line
    return "\n".join(kept), scripts


def _split_words(text: str) -> List[List[str]]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars=_PUNCTUATION)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    commands: List[List[str]] = [[]]
    skip_next = False
    for token in lexer:
        if skip_next:  # the target of a redirection
            skip_next = False
            continue
        if any(char in token for char in "<>") and set(token) <= set(_PUNCTUATION):
            skip_next = True
            if commands[-1] and len(commands[-1][-1]) == 1 and commands[-1][-1].isdigit():
                commands[-1].pop()  # the 2 of 2>&1
            continue
        if set(token) <= set(_PUNCTUATION):
            commands.append([])
            continue
        commands[-1].append(token)
    return [tokens for tokens in commands if tokens]


def _strip_prefix(tokens: List[str]) -> List[str]:
    """Drop `VAR=x` assignments and wrappers like `sudo -u root`, `env`, `command`, `time`."""
    tokens = list(tokens)
    while tokens:
        if _ASSIGNMENT.match(tokens[0]):
            tokens.pop(0)
        elif os.path.basename(tokens[0]) in _WRAPPERS:
            tokens.pop(0)
            while tokens:
                head = tokens[0]
                if head in _VALUE_FLAGS and len(tokens) > 1:
                    del tokens[:2]
                elif head.startswith("-") or _ASSIGNMENT.match(head) or _DURATION.fullmatch(head):
                    tokens.pop(0)
                else:
                    break
        else:
            break
    if tokens:
        tokens[0] = os.path.basename(tokens[0])
    return tokens


def _nested_scripts(tokens: List[str]) -> List[str]:
    """Scripts given to `bash -c '...'` or `eval ...`."""
    if tokens[0] in _SHELLS:
        for index, token in enumerate(tokens[1:], start=1):
            is_c_flag = token.startswith("-") and not token.startswith("--") and token.endswith("c")
            if is_c_flag and index + 1 < len(tokens):
                return [tokens[index + 1]]
        return []
    if tokens[0] == "eval":
        return [" ".join(tokens[1:])]
    return []


def _substitutions(text: str) -> List[str]:
    """The commands inside `$( )` and backticks that the shell would run (not inside single quotes)."""
    found: List[str] = []
    in_single = in_double = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and not in_single:
            index += 2
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif not in_single and text.startswith("$(", index):
            depth, end = 1, index + 2
            while end < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[end], 0)
                end += 1
            found.append(text[index + 2 : end - 1 if depth == 0 else end])
            index = end
            continue
        elif not in_single and char == "`":
            end = text.find("`", index + 1)
            if end != -1:
                found.append(text[index + 1 : end])
                index = end + 1
                continue
        index += 1
    return found
