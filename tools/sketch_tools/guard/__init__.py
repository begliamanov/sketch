"""The guard tool: blocks the shell commands agents must never run (merge, force-push, push to a
protected branch, close an issue). Runs as a Claude Code PreToolUse hook."""

from sketch_tools.guard.cli import main

__all__ = ["main"]
