# Deterministic tools for Sketch

Working notes. Discussion only, nothing is implemented. Each item has a status:

- **proposed**: suggested, not yet discussed
- **agreed**: the developer said yes
- **rejected**: the developer said no (kept with the reason, so it is not re-proposed)
- **open**: a question that needs a decision

Last updated: 2026-11-15

## Goal

Use deterministic tools (scripts, hooks, CLI) wherever a step does not need judgment, so that Sketch is cheaper, repeatable, and fails loudly instead of drifting. Today an LLM does many mechanical jobs: editing the state table, formatting journal lines, checking commit prefixes, running `gh` commands. The LLM stays for judgment only: slicing stories into tasks, writing tests, implementing, reviewing against criteria, the retro.

## Principles (from the developer)

- **Tools, plural.** One tool per domain (a file or a concern), each does that one thing perfectly, with subcommands for its features. No single toolbox CLI for everything. (agreed, revised)
- **No dependencies on anything outside.** Definition below is still open (Q5). (agreed in spirit)
- The tool list must be reworked so every entry is a single-purpose tool. The tier tables below are the first draft and several entries (`preflight`, `reconcile`, `pr`, `test`, `issues publish`) are too big and must be split. (agreed)

## Open questions

| # | Question | Status |
|---|---|---|
| Q1 | Implementation language: bash, or one dependency-free Python script? (Install script is already bash; harness-neutral either way.) | open |
| Q2 | One CLI or separate tools? | **decided: one tool per domain**, with subcommands (revised 2026-11-15; first said separate single-job tools) |
| Q3 | Do agent reports get a small structured footer (verdict, findings as a list) so tools can read them? | open |
| Q5 | What counts as "outside"? Strict: a tool only sees args, stdin and named files, so git and `gh` output is piped in by the orchestrator. Pragmatic: git and the filesystem are allowed, the network and the tracker are not. | open (asked first) |
| Q4 | Where does the CLI live and how do adapters install it (`core/bin/`, copied by `install.sh`)? | open |

## Tier 1: replace purely mechanical LLM work

| Tool | Replaces | Status |
|---|---|---|
| `sketch state get/set/task` | Orchestrator rewriting `state.md` after every step. Schema-validated (`phase`, `status`, `stopped`), atomic counter bumps, refuses to exceed a round cap, so caps are enforced, not promised. | proposed |
| `sketch journal add <TYPE> <task> <text>` | The whole `drift-notetaker` agent (a timestamp plus an append). Validates type, `[me]` marker, one line per event, append-only. | proposed |
| `sketch verify-commits <task>` | "Check git log and git status yourself" rule. Checks `t-N:` prefix, order tests → impl → fixes, clean tree, right branch, test files unchanged since the `t-N: tests` commit. | proposed |
| `sketch changelog check` | Reviewer's CHANGELOG check. One new line under Unreleased ending with `(#issue)` matching the task. | proposed |
| `sketch test <mode>` | Run step of the `tester` agent. Reads command from `.sketch/config.md`, runs once, tees log to `.sketch/logs/`, records branch and SHA, parses failing test names, exit code for PASS / FAIL / CANNOT RUN. LLM only for ambiguous classification. | proposed |
| `sketch preflight` | Preconditions in `run-story` / `resume-story` and the "Setup gaps" pass. Prints the full missing list with exact fix commands in one pass. | proposed |
| `sketch reconcile` | `resume-story` step 3. Compares state with git, tracker and PR; classifies each difference harmless or risky. | proposed |
| `sketch wip-commit` | WIP commits in `pause`, `stop`, crash recovery. Refuses when not on the story branch; takes N from state. | proposed |
| `sketch pr open/ready/verify` | Mechanical half of `pr-agent` and the orchestrator's "verify yourself". Fixed `--base <feature-branch>`, explicit push form, records `pr` and `pr_head_sha`, checks flagged tasks appear in the description. | proposed |

## Tier 2: guardrails that enforce the "never" rules

| Tool | What it enforces | Status |
|---|---|---|
| Git hooks / `git push` wrapper | No push to the feature branch or main, no `--force`, no merge. Today these are prose only. | proposed |
| `commit-msg` hook | `t-N:` / `story-N:` prefix. | proposed |
| Claude Code `PreToolUse` hook (via `settings.snippet.json`) | Blocks `gh pr merge`, `gh issue close`, pushes to protected branches, and edits to test files while the implementer runs. Turns "never edits tests" into a wall. | proposed |
| `sketch tests-frozen` | Diff of test paths against the red-test commit; used by the hook and the reviewer. | proposed |

## Tier 3: rendering and tracker plumbing

| Tool | What it does | Status |
|---|---|---|
| `sketch tasks lint` | Validates `tasks.md`: criteria present, each criterion has a scenario, `blocked_by` valid with no cycles, 3 to 8 tasks, `Skills:` within the pool. | proposed |
| `sketch tasks order` | Topological run order; skip tasks whose blocker is flagged. | proposed |
| `sketch issues publish` | Idempotent publish mode of `task-writer`: list existing, create missing, link blockers, write issue numbers to state immediately. | proposed |
| `sketch pr-body render` | Fills the PR template from `state.md` and structured report fields; enforces the 20-line limit and verbatim flags. | proposed |
| `sketch skills resolve <name>` | Plugin-style skill name to absolute `SKILL.md` path; fails if unresolved. | proposed |
| `sketch brief <role> <task>` | Assembles brief paths and skill lists from config and `tasks.md`. | proposed |
| `sketch version check` | `VERSION`, `CHANGELOG.md` and install marker agree. | proposed |

## What stays with the LLM

Splitting a story into tasks, writing tests, implementing, reviewing against criteria, deciding whether a test looks wrong, the retro analysis. `reviewer` and `story-reviewer` stay; their mechanical checks (frozen tests, changelog format, commit prefixes) move to tools.

## Consequences to decide

- `drift-notetaker` becomes a tool, not an agent; most of `tester` and `pr-agent` follow. (proposed)
- `state.md` stays human-readable but only `sketch state` writes it. (proposed)

## Suggested build order (proposed)

1. `state`, `journal`, `verify-commits`
2. `preflight` and the `PreToolUse` guard hook
3. `test`, `tasks lint`, `changelog check`
4. `reconcile`, `pr`, `issues publish`

## Not yet reviewed

`/sketch`, `/tasks`, `/tune-skills`, `/retro` and `/how` were not read in full. Tools for them (for example config validation for `/tune-skills`, retro input collection) are unverified and may be missing from the lists above.

## Decision log

| Date | Decision |
|---|---|
| 2026-11-15 | Notes file created. Nothing agreed yet. |
| 2026-11-15 | Tool 1 `journal-add` agreed: build it, delete the `drift-notetaker` agent. Files to edit later: `orchestrator.md`, `pause`, `stop`, `run-story`, `note`, `agents.list`. |
| 2026-11-15 | Tool 2 `state-set` agreed: build. Counters stay out of it (tool 3 `state-bump`). Writes via temp file + rename. |
| 2026-11-15 | `state check` agreed: build. Shares the schema with `set` and `bump`. |
| 2026-11-15 | Tool 3 `state-bump` agreed: build. Cannot touch anything except counters; `state-set` cannot touch counters. Distinct exit code 2 at cap. |
| 2026-11-15 | Revised: related functions are merged into one tool per domain with subcommands (`state set/bump/check`). Replaces the grouped-folders idea and the first Q2 answer. Rules inside a tool stay strict: `set` refuses counters, `bump` touches only counters. |
| 2026-11-15 | Tools are many and single-purpose, no `sketch` CLI with subcommands (Q2). Tools must not depend on anything outside; exact meaning is Q5. |

## Tool list v3 (one tool per domain, subcommands, decided one by one)

Replaces the tier tables above. Status: proposed / agreed / rejected.

| Tool | Subcommand | One job | Status |
|---|---|---|---|
| `journal` | `add` | Append one validated line to `.sketch/journal.md`; replaces the `drift-notetaker` agent | **agreed**: build tool, delete agent |
| `state` | `set` | Set one field in `state.md`, reject values outside the schema (not counters) | **agreed** |
| `state` | `bump` | Increase one counter, refuse to pass the cap (exit code 2); touches nothing else | **agreed** |
| `state` | `check` | Check `state.md` is valid, report every problem | **agreed**: build |
| `repo-check` | `commit-prefix` | Flag commit subjects without `t-N:` or `story-N:` | proposed |
| `repo-check` | `tests-unchanged` | Fail if a test file changed since the red-test commit | proposed |
| `repo-check` | `changelog` | One new `CHANGELOG.md` line ending in `(#issue)` | proposed |
| `repo-check` | `tree-clean` | OK or list dirty files from `git status` output | proposed |
| `tests` | `run` | Run the test command once, keep the full log, print exit code and log path | proposed |
| `tests` | `failures` | List failing test names from a raw log | proposed |
| `plan` | `tasks-check` | Validate `tasks.md` (criteria, `blocked_by`, cycles, task count) | proposed |
| `plan` | `tasks-order` | Run order, skipping tasks blocked by a flagged one | proposed |
| `plan` | `config-check` | `config.md` has every key, every skill path exists | proposed |
| `pr` | `render-body` | Fill the PR template, enforce 20 lines and verbatim flags | proposed |
| `pr` | `check-base` | PR base equals the feature branch, from `gh pr view` JSON | proposed |
| `guard` | (hook) | Deny push to feature/main, force-push, merge, issue close; runs as a Claude Code hook, so kept apart | proposed |
| `report-check` | (none) | Agent report has its required parts | proposed |
