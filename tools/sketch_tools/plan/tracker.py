"""Which tracker a git remote URL points at."""

from __future__ import annotations

from typing import Optional, Tuple

from sketch_tools.core.errors import UsageError


def remote_host(url: str) -> str:
    """The host in a git remote URL (https, ssh:// or scp-style). Raises UsageError for a URL
    without one."""
    text = url.strip()
    if not text or any(char.isspace() for char in text):
        raise UsageError("not a git remote URL: " + repr(url))
    if "://" in text:
        authority = text.split("://", 1)[1].split("/", 1)[0]
        host = authority.rsplit("@", 1)[-1].split(":", 1)[0]
    elif ":" in text and not text.startswith("/"):
        host = text.split(":", 1)[0].rsplit("@", 1)[-1]  # user@host:path
    else:
        raise UsageError("not a git remote URL: " + repr(url))
    if not host:
        raise UsageError("not a git remote URL: " + repr(url))
    return host.lower()


def detect_tracker(url: str) -> Tuple[Optional[str], Optional[str], str]:
    """(tracker, cli, host): `github`/`gh` for github.com, `gitlab`/`glab` for a GitLab host, else
    (None, None, host) and the developer is asked."""
    host = remote_host(url)
    if host in ("github.com", "www.github.com"):
        return "github", "gh", host
    if any(label.startswith("gitlab") for label in host.split(".")):
        return "gitlab", "glab", host
    return None, None, host
