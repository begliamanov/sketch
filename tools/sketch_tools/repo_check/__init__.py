"""The repo-check tool: rules about commits, tests, the changelog and the working tree, checked
on text that the caller pipes in (from git). It never runs git itself."""

from sketch_tools.repo_check.cli import main

__all__ = ["main"]
