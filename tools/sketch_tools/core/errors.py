"""Errors a command can raise. The tool runner turns them into a message and an exit code."""

from __future__ import annotations

from sketch_tools.core import exitcodes


class ToolError(Exception):
    """Base class: carries the exit code to use."""

    exit_code = exitcodes.USAGE


class UsageError(ToolError):
    """Bad arguments or unusable input."""

    exit_code = exitcodes.USAGE


class RefusedError(ToolError):
    """The tool refuses to do this (a cap is reached, or the operation is not allowed)."""

    exit_code = exitcodes.REFUSED
