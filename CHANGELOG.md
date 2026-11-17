# Changelog

Sketch follows [semantic versioning](https://semver.org). The current version is in `VERSION`.

## Unreleased

- Deterministic tools in `tools/` (Python 3.9+, standard library only, tests written first): `sketch-journal add`, `me-lines`, `signals`; `sketch-state new-story`, `task add`, `set`, `bump`, `flag add`, `check`, `gate`, `wip-message`, `reconcile`; `sketch-repo-check commit-prefix`, `tests-unchanged`, `changelog`, `tree-clean`; `sketch-plan tasks-check`, `tasks-order`, `config-check`; `sketch-pr render-body`, `check-base`, `check-flags`; `sketch-guard check-command`; `sketch-report submit`, `check`, `get`. The Claude Code installer copies them to `~/.claude/sketch/tools/` and creates a launcher per tool. Needs `python3` 3.9 or newer.
- `/tasks`, `task-writer`, `/run-story`, `/tune-skills` and `/resume-story` check `tasks.md` and `config.md` with `sketch-plan`, and `/run-story` takes the run order from `tasks-order`. A story with fewer than 3 or more than 8 tasks is reported.
- Agents hand in their reports through `sketch-report submit` (JSON, one schema per role), saved in `.sketch/reports/<scope>-<role>-<run>.json` only when complete and consistent: a reviewer cannot say SATISFIED with an open must-fix or a coverage entry that is not OK, and the story-reviewer cannot say SATISFIED unless the tester said PASS. The orchestrator gives each agent a run number, checks the report with `sketch-report check` (including that every skill in the brief is named) and reads results with `sketch-report get`.
- `sketch-guard` runs as a `PreToolUse` hook (add it from `settings.snippet.json`) and blocks merges, force pushes, pushes to main or the feature branch, issue closing, and any `git push` that does not name its branch.
- The PR description is built by `sketch-pr render-body` from the state file and a new `.sketch/pr-extras.json`; `/run-story` checks the PR with `check-base` and `check-flags`.
- The orchestrator, `/run-story`, `/tasks`, `/sketch`, `/pause`, `/stop`, `/resume-story` and `/note` call the tools for state, journal and git checks. Counters are enforced by `sketch-state bump`; the reviewer gets the mechanical check results in its brief.
- Removed the `drift-notetaker` agent: `sketch-journal add` does its job. The installer now removes stale generated agents, skills and core files, so a deleted agent does not linger in `~/.claude`.
- `state.md` always has a `stop_after_task` line (`no` or `yes`), and is written only by `sketch-state`: a new story with `new-story`, each task with `task add`.
- New config key `test_paths`: globs of the project's test files, asked by `/tune-skills`. Re-run `/tune-skills` or add the line to `.sketch/config.md`.
- Removed the Pi placeholder sections from the README. Pi is not supported.

## 0.0.1

First versioned release. Designed and written, not yet run end to end.

- Core agents and skills, with stories split into tasks
- `/sketch` chains into the loop on its own: tasks, issues, story run, PR
- Claude Code adapter (`adapters/claude-code/install.sh`)
