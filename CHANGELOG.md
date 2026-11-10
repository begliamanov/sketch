# Changelog

Sketch follows [semantic versioning](https://semver.org). The current version is in `VERSION`.

## Unreleased

- Renamed agent `reviewer` to `task-reviewer`, so it can't clash with other harnesses' built-in `reviewer` agents. Claude Code users: delete the stale `~/.claude/agents/reviewer.md`, then rerun `install.sh`.

## 0.0.1

First versioned release. Designed and written, not yet run end to end.

- Core agents and skills, with stories split into tasks
- `/sketch` chains into the loop on its own: tasks, issues, story run, PR
- Claude Code adapter (`adapters/claude-code/install.sh`)
