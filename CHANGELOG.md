# Changelog

Sketch follows [semantic versioning](https://semver.org). The current version is in `VERSION`.

## Unreleased

- Skills are picked per task: the task-writer adds a `Skills:` line to each task (`sketch-plan tasks-check` accepts it), `sketch-plan brief-skills --tasks ... --task t-<n>` narrows a role's skills to it, reviewers can report a `missing_skill` and are resumed with it, and every report must name one concrete rule per skill. Agents have fixed models in `agents.list` (sonnet for writers, opus for reviewers and the retro, haiku for the tester and the PR agent).
- The tester also runs one task's tests before its review (`mode task`, scope `t-<n>`, `sketch-report` accepts it), so the reviewer reads the tester's report and never runs tests itself.
- A draft PR/MR is opened when a story starts; the pr-agent fills its description and marks it ready at the end.
- The orchestrator rules and the retro skill have a "How to talk" section: answer first, short, details behind a pointer, real risks without being asked.
- Deterministic tools in `tools/` (Python 3.9+, standard library only, tests written first): `sketch-journal add`, `me-lines`, `signals`; `sketch-state new-story`, `task add`, `set`, `bump`, `flag add`, `check`, `gate`, `wip-message`, `reconcile`; `sketch-repo-check commit-prefix`, `tests-unchanged`, `changelog`, `tree-clean`; `sketch-plan tasks-check`, `tasks-order`, `config-check`; `sketch-pr render-body`, `check-base`, `check-flags`; `sketch-guard check-command`; `sketch-report submit`, `check`, `get`; `sketch-tests run`, `classify`, `failures`, `summary`, `expect-red`, `skipped-diff`, `failures-diff`; `sketch-plan brief-skills`, `issues-todo`, `detect-tracker`; `sketch-setup check`; `sketch-retro recommend`; `sketch-skills list`. The Claude Code installer copies them to `~/.claude/sketch/tools/` and creates a launcher per tool. Needs `python3` 3.9 or newer.
- `/tasks`, `task-writer`, `/run-story`, `/tune-skills` and `/resume-story` check `tasks.md` and `config.md` with `sketch-plan`, and `/run-story` takes the run order from `tasks-order`. A story with fewer than 3 or more than 8 tasks is reported.
- Agents hand in their reports through `sketch-report submit` (JSON, one schema per role), saved in `.sketch/reports/<scope>-<role>-<run>.json` only when complete and consistent: a reviewer cannot say SATISFIED with an open must-fix or a coverage entry that is not OK, and the story-reviewer cannot say SATISFIED unless the tester said PASS. The orchestrator gives each agent a run number, checks the report with `sketch-report check` (including that every skill in the brief is named) and reads results with `sketch-report get`.
- The "setup gaps" list, an agent's skills, what the tracker still needs, the tracker of a remote, skill discovery and the retro recommendation now come from tools (`sketch-setup`, `sketch-plan`, `sketch-skills`, `sketch-retro`) instead of being worked out by eye.
- Tests are run and read through `sketch-tests`, from structured result files (JUnit XML, or `xcresulttool` JSON for Xcode), never from console text. New config keys: `test_format`, `test_results` (a glob of the result files; **files matching it are deleted before each test run**), and optionally `formats_dir` for your own readers. The placeholder in `test_task` is now `{target}` (was `{class}`). Re-run `/tune-skills` or edit `.sketch/config.md`. The tester, test-writer, implementer and reviewer use the tool; the test-writer's report now carries the red run's `target` and `results`.
- `sketch-guard` runs as a `PreToolUse` hook (add it from `settings.snippet.json`), fails closed (its launcher turns any failure into a block), and blocks merges, force pushes, pushes to main or the feature branch, issue closing, and any `git push` that does not name its branch.
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
