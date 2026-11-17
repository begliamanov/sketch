"""Which tracker a git remote URL points at."""

from __future__ import annotations

from typing import Optional, Tuple


def remote_host(url: str) -> str:
    """The host in a git remote URL (https, ssh:// or scp-style). Raises UsageError for a URL
    without one."""
    raise NotImplementedError


def detect_tracker(url: str) -> Tuple[Optional[str], Optional[str], str]:
    """(tracker, cli, host): `github`/`gh` for github.com, `gitlab`/`glab` for a GitLab host, else
    (None, None, host) and the developer is asked."""
    raise NotImplementedError
