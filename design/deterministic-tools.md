# Deterministic tools for Sketch

Working notes. Implementation started 2026-11-16 in `tools/` (see its README for what is built). Each item has a status:

- **proposed**: suggested, not yet discussed
- **agreed**: the developer said yes
- **rejected**: the developer said no (kept with the reason, so it is not re-proposed)
- **open**: a question that needs a decision

Last updated: 2026-11-16

## Goal

Use deterministic tools (scripts, hooks, CLI) wherever a step does not need judgment, so that Sketch is cheaper, repeatable, and fails loudly instead of drifting. Today an LLM does many mechanical jobs: editing the state table, formatting journal lines, checking commit prefixes, running `gh` commands. The LLM stays for judgment only: slicing stories into tasks, writing tests, implementing, reviewing against criteria, the retro.

## Principles (from the developer)

- **Tools, plural.** One tool per domain (a file or a concern), each does that one thing perfectly, with subcommands for its features. No single toolbox CLI for everything. (agreed, revised)
- **No dependencies on anything outside.** Definition below is still open (Q5). (agreed in spirit)
- The tool list must be reworked so every entry is a single-purpose tool. The tier tables below are the first draft and several entries (`preflight`, `reconcile`, `pr`, `test`, `issues publish`) are too big and must be split. (agreed)

## Engineering requirements

From the developer (agreed): written in Python; well structured; easy to extend and change later; configurable; follows best practices; **tests are written first, before the implementation** (red tests, then code that makes them pass, the same contract Sketch uses for its own tasks).

My concrete proposals for these (proposed, not yet discussed):

- **Layers.** Pure logic (parse, validate, decide) separate from a thin CLI layer that does the I/O. Pure functions are testable with plain fixtures.
- **One module per tool**, one function per subcommand, registered in one table, so adding a subcommand does not touch the others.
- **One shared schema module** for allowed values (phases, statuses, journal types, counters), read by `state set/bump/check` and `journal add`, so they cannot disagree.
- **Extension points.** Test-output parsers (`test_format`) and `guard` rules are plugins in a registry, so a new runner or rule is one new file.
- **Configuration.** Everything configurable lives in `.sketch/config.md` and is passed in by path (`--config`), never found by walking up directories.
- **Standard library only at runtime.** Dev tooling (tests, type checks, lint) may use packages; runtime may not.
- **Typed and checked.** Full type hints, a type checker in strict mode, a linter and formatter.
- **Tests first.** For each subcommand, the fixture tests are written and seen failing for the right reason before any implementation. Input text in, expected output and exit code out. The tests are the spec, and the implementation never edits them. Assumption: pytest as a dev-only dependency (cheap to change).
- **Exit-code contract.** 0 ok, 1 check failed, 2 cap reached or refused, 3 bad usage, same meaning in every tool; a `--json` flag for machine output.

## Open questions

| # | Question | Status |
|---|---|---|
| Q1 | Implementation language | **decided: Python** (2026-11-15) |
| Q2 | One CLI or separate tools? | **decided: one tool per domain**, with subcommands (revised 2026-11-15; first said separate single-job tools) |
| Q3 | How do tools read agent reports? | **decided: D**, agents submit reports through a tool (`report submit`), validated at write time, saved as JSON |
| Q5 | What counts as "outside"? | **decided**: a tool reads only its arguments, stdin and files it is pointed at; writes only to files it is pointed at; never calls git, `gh`, the network or an LLM. Only exception: `tests run` runs the command from `config.md`. The orchestrator runs git/`gh` and pipes output in. |
| Q4 | Where the tools live and how adapters install them | **decided: Option 1**, source in `tools/`, each adapter's install copies it to a fixed path (e.g. `~/.claude/sketch/tools/`) and creates launchers (`sketch-state`, `sketch-journal`, ...). No pip. Python package layout inside, so pip packaging stays possible later. |

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

Splitting a story into tasks, writing tests, implementing, reviewing against criteria, deciding whether a test looks wrong, the retro analysis. `task-reviewer` and `story-reviewer` stay; their mechanical checks (frozen tests, changelog format, commit prefixes) move to tools.

## Consequences to decide

- `drift-notetaker` becomes a tool, not an agent; most of `tester` and `pr-agent` follow. (proposed)
- `state.md` stays human-readable but only `sketch state` writes it. (proposed)

## Suggested build order (proposed)

1. `state`, `journal`, `verify-commits`
2. `preflight` and the `PreToolUse` guard hook
3. `test`, `tasks lint`, `changelog check`
4. `reconcile`, `pr`, `issues publish`

## Tests tool notes (revised 2026-11-16)

- **Structured results, not console scraping.** `tests` reads a normalized result (test name, status, message, duration) from a result file the test command writes. The config says where: `test_format` and `test_results`, per test kind. If the file is missing the answer is CANNOT RUN or UNKNOWN, and it stops and asks. No fallback to scraping logs, and no LLM reading logs. (agreed in direction; developer confirmed the extension model below)
- **Formats:** `junit-xml` (Gradle, pytest, Vitest, Playwright, Jest with `jest-junit`, most UI-test tools; flags for each runner are from memory and must be verified before we promise them) and `xcresult` (Xcode; the `xcresulttool` command is unverified). This replaces the earlier list of gradle, xcodebuild and pytest as separate formats.
- **Extension (decided):** readers are plugins behind one interface (`read(path) -> list[TestResult]`) registered in one table. Built-in readers live in `tools/`. **A user adds a reader in their own project**, in a folder the config points at (for example `formats_dir: .sketch/formats`), without touching the Sketch repo. The new reader's fixture tests (real captured results: pass, failure, skipped, nothing ran) come first.
- **LLM helps with setup, proactively.** During `/tune-skills`, the LLM detects the project's test runner and checks it against the supported formats before anything fails. If the runner can write JUnit XML, it proposes the exact flags and config. If not, it drafts a project-local reader plus its fixture tests, and the developer confirms. The LLM only helps set things up; at run time the tools are deterministic.
- **Fail early:** an unsupported or misconfigured runner stops at `/tune-skills` or the baseline check, with a message saying what to do, never halfway through a story.
- **Related gaps:** `test_task`'s `{class}` placeholder is Gradle-flavored and needs a neutral name such as `{target}`; UI tests (flaky, need a simulator or browser) get their own discussion when they are added; `/tune-skills` currently says "do not run the full suite now"; decided 2026-11-16 (option A): `/tune-skills` may run one small test (or the narrowest `test_task` form) once, after showing the command and getting a yes, to capture a real result file as the reader's fixture. If the sample has no failing case, the LLM asks the developer to name a failing test or says what to break temporarily; it never invents one. The `/tune-skills` text must be updated accordingly.
- Loading Python from the project folder must be reconciled with the Q5 rule ("reads only what it is pointed at"): the config points at the folder.

## Candidates from reading /sketch, /tasks, /tune-skills, /retro (2026-11-16)

All agreed 2026-11-16 ("build them all"). Each follows the Q5 rule: facts come in as text or JSON, the orchestrator gathers them with git and `gh`.

| Tool | Subcommand | One job | Where it comes from | Status |
|---|---|---|---|---|
| `setup` | `check` | Given facts (git repo, commit, remote, auth, `.sketch/`, exclude line, config, docs, feature branch, pushed), print every missing step in order with its exact command, marked safe or developer-only | "Setup gaps" in the orchestrator, `/sketch`, `/run-story`, `/tune-skills` | **agreed**; **built** 2026-11-17 |
| `journal` | `me-lines` | List every `[me]` line for given stories, verbatim | `/retro` step 3.1 | **agreed**; **built** 2026-11-17 |
| `journal` | `signals` | Count flags and cap hits per story from the journal | `/sketch` step 2 and `/retro` | **agreed**; **built** 2026-11-17 |
| `retro` | `recommend` | Apply the rule (first 3 stories, any flag, any cap hit, over 20 lines changed, over 10 comments) to counts and say recommended or not | `/sketch` step 2 | **agreed**; **built** 2026-11-17 |
| `state` | `gate` | From `phase` and PR state say: ok, ask about the PR, or stop with the right message | `/sketch` step 1 | **agreed**; **built** 2026-11-17 |
| `state` | `new-story` | Write a fresh story record in the exact state format | `/sketch` step 8 | **agreed**; **built** 2026-11-17 |
| `state` | `reconcile` | Compare state with piped facts (commits per task, branches, issues, PR) and classify each difference harmless or risky | `/resume-story` step 3 | **agreed**; **built** 2026-11-17 |
| `state` | `wip-message` | Build the `[wip]` commit message from state; refuse if the branch is not the story branch | `/pause`, `/stop`, resume | **agreed**; **built** 2026-11-17 |
| `plan` | `brief-skills` | Compute the skill paths for one agent brief (common + task picks inside the role list, full list for story-reviewer, pool names for reviewers) | orchestrator "Briefing an agent" item 5 | **agreed**; **built** 2026-11-17 |
| `plan` | `issues-todo` | Given `tasks.md` and the existing issues as JSON, list which issues and blocking links are still to create | `/tasks` publish mode | **agreed**; **built** 2026-11-17 |
| `skills` | `list` | List `SKILL.md` files with name, description and absolute path | `/tune-skills` scan | **agreed**; **built** 2026-11-17 |
| `plan` | `detect-tracker` | Map a remote URL to github or gitlab and `gh` or `glab`, or "ask" | `/tune-skills` scan | **agreed**; **built** 2026-11-17 |

## Gaps found while building (decided 2026-11-16)

- **`stop_after_task`**: decided: it is a normal header line that is always present (`no` or `yes`), set with `state set stop_after_task yes|no`. No add or remove of lines. `core/state-format.md`, `/stop` and `/sketch` were updated; `state new-story` must write `stop_after_task: no`.
- **Flags section**: decided: `state flag add --task ID REASON` appends `- ID: REASON`. Setting the task status to `flagged` stays a separate `state set`; `state check` reports a flagged task without a flag line and a flag line without a flagged task. There is no remove: flags stay until the next story. Open for later: where story-level flags (an unresolved story-end must-fix) live, to settle with `pr render-body`.
- **Wiring** (done 2026-11-17): `journal`, `state` and `repo-check` are installed by `adapters/claude-code/install.sh` (launchers `sketch-journal`, `sketch-state`, `sketch-repo-check`, run with `python3 -I`) and called from the orchestrator rules, `/run-story`, `/tasks`, `/sketch`, `/pause`, `/stop`, `/resume-story`, `/note`, `pr-agent` and `task-writer`. The `drift-notetaker` agent is deleted, and the installer removes stale generated files. `{{TOOLS}}` is the new placeholder. A test checks that every `{{TOOLS}}/sketch-...` call written in `core/` names a real command and carries `--state` or `--journal`.
- **Task rows and new story files** (done 2026-11-17): `state task add` and `state new-story` are built and wired into `/sketch` and `task-writer`. `new-story` refuses to replace a state file whose phase is not `done`. The three round caps are options (defaults 3, 3 and 2) so they can be configured later. Still open: `/note` and `/pause` read the story number from `state.md` by eye (no `state get`).
- **Guard limits and unverified parts** (open): it cannot see what a script, a variable in anything but a refspec, `xargs` or `python -c` does, and `git pull` (which merges) is not blocked. The hook format (`hooks.PreToolUse`, `matcher`, exit 2 blocks, stderr shown to the agent) is written from memory, as is `glab mr view --output json`; check both on the first real run.
- **Mechanical review checks**: the orchestrator now runs `tests-unchanged`, `changelog` and `commit-prefix` before each review and gives the output to the reviewer, which files any failure as a must-fix. This needs a new config key `test_paths` (asked by `/tune-skills`).

## Not yet reviewed

`/how` was not read. `/sketch`, `/tasks`, `/tune-skills` and `/retro` were read on 2026-11-16; their candidates are in the section above.

## Decision log

| Date | Decision |
|---|---|
| 2026-11-15 | Notes file created. Nothing agreed yet. |
| 2026-11-15 | Tool 1 `journal-add` agreed: build it, delete the `drift-notetaker` agent. Files to edit later: `orchestrator.md`, `pause`, `stop`, `run-story`, `note`, `agents.list`. |
| 2026-11-15 | Tool 2 `state-set` agreed: build. Counters stay out of it (tool 3 `state-bump`). Writes via temp file + rename. |
| 2026-11-17 | The last six agreed tools built: `plan brief-skills`, `plan issues-todo`, `plan detect-tracker`, `skills list`, `setup check`, `retro recommend`. All 11 tools of the agreed list now exist. Decisions while building: `brief-skills` on this base is `common` + the role's list + the story's `extra_skills` (this base has no per-task skill picks; add them when the picks feature lands). `issues-todo` takes the existing issues and links as JSON (the orchestrator lists them with `gh`) and prints `have`/`todo` lines, exit 1 while anything is todo. `setup check` takes a facts JSON and prints numbered steps as `safe`, `ask` (safe once the developer gave a name) or `yours`. `skills list` walks folders, follows links but never twice, skips hidden and vendored folders, and reads the `---` front matter (quoted, folded and wrapped values). `retro recommend` takes the counts (flags and caps from `journal signals`, lines and comments from git and the tracker) and its three limits are options. Wired into the orchestrator rules (setup gaps, skill briefing), `/sketch`, `/tune-skills` and the task-writer. |
| 2026-11-17 | `tests` built (687 tests; a real `swift test` and a real `xcodebuild` + `xcresulttool` run through the installed launcher both gave the right classify, failures, summary and expect-red). Formats: `junit-xml` and `xcresult-json`; the Xcode format was verified on this machine (Xcode 26.2): a real `.xcresult` was captured from a SwiftPM package with a passing, a failing and a skipped test, and `xcrun xcresulttool get test-results tests --path <x>.xcresult` gives the JSON the reader reads (fixture `xcresult_tests.json`). The JUnit reader is checked against real SwiftPM `--xunit-output` files (which report a skipped test as passed: a runner quirk). `run` clears stale result files, runs the command with stdin closed (killing its process group on `--timeout`), keeps the log, and archives the result files in `<stamp>-<mode>.results/`; every other command reads such a folder, so a later run cannot overwrite what an earlier step judges. `classify` is PASS, FAIL, CANNOT RUN or UNKNOWN (UNKNOWN: code or environment, for the agent to judge from the log). `expect-red` flags tests that did not run, passed or were skipped as errors, and tests that failed with an error instead of an assertion as `review:` lines (JUnit can tell, xcresult cannot). Project readers load from `formats_dir`. `{class}` became `{target}`. The config parser moved to `core/` so `plan` and `tests` do not import each other. Wired into the tester, test-writer, implementer, reviewer, `/tune-skills` (which now asks for the format and offers to write a reader, and may run one small test with a yes) and `/run-story` (passes the red run's target and results folder on). `plan config-check` validates `test_format`, `test_results` and `formats_dir`. |
| 2026-11-17 | `state gate`, `wip-message`, `reconcile` and `journal me-lines`, `signals` built (574 tests) and wired into `/sketch`, `/retro`, `/resume-story`, `/pause` and `/stop`. `gate` takes the PR state as an option; `wip-message` takes the task in progress as an option (only the orchestrator knows it); `reconcile` takes a facts JSON the orchestrator gathers with git and `gh` (every key optional, unknown keys rejected) and prints `risky:` lines first. `journal` filters are `--story S2` (repeatable) and `--after N`. Not built: `retro recommend` (`/sketch` still applies the retro rule by eye, on counts from `signals`). |
| 2026-11-17 | `report` built (497 tests). A schema per role (implementer, test-writer, reviewer, story-reviewer, tester, task-writer, pr-agent, retro-agent) from the agents' own hand-back sections, plus cross-field rules (SATISFIED needs no must-fix and all coverage OK; story-reviewer SATISFIED needs tester PASS; non-success outcomes need a detail). Refinement of Q3: files are named `<scope>-<role>-<run>.json` and the orchestrator gives each agent a run number, so a stale report from an earlier round cannot pass `check`. An invalid submission is never saved; a saved one is never overwritten. All eight agent files, the orchestrator rules, `/run-story`, `/tasks` and `/retro` now use it; the PR extras file is filled from `report get`. |
| 2026-11-17 | `guard` and `pr` built (384 tests). `guard check-command` is a Claude Code `PreToolUse` hook: hook JSON on stdin, exit 2 blocks, fails closed. `git push` must name its branch, spelled out (no variables). Protected branches: `--protect main --protect master` plus the feature branch read from `state.md`. `pr render-body` takes the state file plus `.sketch/pr-extras.json` (a stand-in for the structured reports of Q3) and enforces ~20 lines (flags and the fold not counted); `check-base` reads `gh pr view --json` or glab JSON; `check-flags` checks flags and unresolved items are in the body. |
| 2026-11-17 | `plan` built (291 tests): `tasks-check`, `tasks-order`, `config-check`, wired into `/tasks`, `task-writer`, `/run-story`, `/tune-skills`, `/resume-story`. Limits: `tasks-check` cannot link a criterion to a scenario (scenarios are names only), so it checks that there are at least as many scenarios as criteria; task count defaults 3 to 8 (options); `config-check` still requires the `{class}` placeholder (the planned rename to `{target}` was not made). |
| 2026-11-17 | `state new-story` and `state task add` built (228 tests): no state file is written by hand any more. Round caps are command options with the old defaults. |
| 2026-11-17 | Wired the built tools into the system and moved the work to branch `deterministic-tools`, based on `add-versioning` (developer decision: A). Installer copies `tools/`, creates launchers, removes stale generated files; docs call the tools; `drift-notetaker` deleted; `test_paths` config key added. 194 tests. |
| 2026-11-16 | `repo-check` built (174 tests green): `commit-prefix`, `tests-unchanged`, `changelog`, `tree-clean`. Details fixed while building: `changelog` needs a full-context diff (`git diff -U99999`) and errors if the `## Unreleased` heading is not visible; test paths are globs (`*` one folder, `**` across folders, rest literal); `tree-clean` reports each path as `dirty: <porcelain line>`. |
| 2026-11-16 | Gaps decided: `stop_after_task` is a required `yes`/`no` header line (no add/remove); `state flag add` added, `check` enforces flag consistency. The runner now supports command groups (`flag add`). 127 tests green. |
| 2026-11-16 | Implementation started. Built tests first and green: core (runner, exit codes, atomic file writes), `journal add`, `state set/bump/check` (103 tests). Choices made while building: Python 3.9 minimum (system Python is 3.9.6, no pytest installed), tests use stdlib `unittest` instead of pytest (no install needed; replaces the earlier pytest assumption); the journal column rule (the spec examples in `state-format.md` contradict each other on spacing for task-less lines; chose one aligned rule: task padded to 3 characters then 2 spaces, type padded to 7 then 1 space). |
| 2026-11-16 | Pi support dropped (developer decision). This branch is based on `add-versioning`, which has no Pi adapter, so there is nothing to delete here; when this work lands it overrides what `origin/main` has. Claude Code is the only adapter, so `guard check-command` is a Claude Code `PreToolUse` hook only. |
| 2026-11-16 | `guard check-edit` dropped. `guard` is now just `check-command`; test protection is `repo-check tests-unchanged` (detect, not prevent). |
| 2026-11-16 | `/tune-skills` may run one small test once at setup (after a yes) to capture a real fixture (option A). Assumptions taken as cheap defaults: `{class}` becomes `{target}`; untracked files count as dirty. |
| 2026-11-16 | Test results: structured result files (`junit-xml`, `xcresult`), no console scraping. Readers are project-local plugins; the LLM helps proactively with setup in `/tune-skills`. Replaces the gradle/xcodebuild/pytest list. |
| 2026-11-16 | (superseded) Test runners for the first version: Gradle, Xcode (`xcodebuild`), pytest. Parsers are plugins behind one interface so more can be added later. |
| 2026-11-16 | All 12 candidates from the skills review agreed: `setup check`, `journal me-lines`, `journal signals`, `retro recommend`, `state gate/new-story/reconcile/wip-message`, `plan brief-skills/issues-todo/detect-tracker`, `skills list`. |
| 2026-11-16 | Q5 decided: strict rule, one exception (`tests run`). All of Q1 to Q5 are now answered. |
| 2026-11-16 | Q4 decided: Option 1 (`tools/` copied by each adapter's install, launchers on a stable path). |
| 2026-11-15 | Tests are written first, before implementation (developer requirement). |
| 2026-11-15 | Q1 decided: Python. Engineering requirements recorded (structure, extensibility, configurability, best practices); concrete proposals listed, not yet agreed. |
| 2026-11-15 | Q3 decided: option D. Agents submit reports through `report submit` (validated when written, saved as JSON); replaces the standalone `report-check`. Cannot force an agent to submit or prove a rule was truly applied; `report check` catches a missing or invalid report every time. Every adapter must put the tool on each agent's path. |
| 2026-11-15 | `guard` agreed: `check-command`, `check-edit`. Core holds the logic, each adapter wires the hook (Claude Code first). `check-edit` needs an "implementer active" marker, to settle at build time. Cannot see commands hidden inside scripts. |
| 2026-11-15 | `pr` agreed: `render-body`, `check-base`, `check-flags`. `render-body` starts with what `state.md` holds; richer sections wait on Q3 (structured report footer). |
| 2026-11-15 | `plan` agreed: `tasks-check`, `tasks-order`, `config-check`. `tasks-check` verifies structure only (quality stays with task-writer and reviewer). `config-check` becomes the single list of required `config.md` keys. |
| 2026-11-15 | `tests` agreed: `run`, `failures`, `classify`, `summary`, `expect-red`, `skipped-diff`, `failures-diff`. `logs-old` dropped for now. Needs `test_format` config key. |
| 2026-11-15 | `repo-check tree-clean` agreed: build. Untracked files count as dirty. |
| 2026-11-15 | `repo-check changelog` agreed: build. Input is the piped diff of `CHANGELOG.md`. |
| 2026-11-15 | `repo-check tests-unchanged` agreed: build. New config key for the test-file pattern; `/tune-skills` must ask for it. |
| 2026-11-15 | `repo-check commit-prefix` agreed: build. Input is piped in (`git log --format=%s`), the tool never runs git. |
| 2026-11-15 | `state check` agreed: build. Shares the schema with `set` and `bump`. |
| 2026-11-15 | Tool 3 `state-bump` agreed: build. Cannot touch anything except counters; `state-set` cannot touch counters. Distinct exit code 2 at cap. |
| 2026-11-15 | Revised: related functions are merged into one tool per domain with subcommands (`state set/bump/check`). Replaces the grouped-folders idea and the first Q2 answer. Rules inside a tool stay strict: `set` refuses counters, `bump` touches only counters. |
| 2026-11-15 | Tools are many and single-purpose, no `sketch` CLI with subcommands (Q2). Tools must not depend on anything outside; exact meaning is Q5. |

## Tool list v3 (one tool per domain, subcommands, decided one by one)

Replaces the tier tables above. Status: proposed / agreed / rejected.

| Tool | Subcommand | One job | Status |
|---|---|---|---|
| `journal` | `add` | Append one validated line to `.sketch/journal.md`; replaces the `drift-notetaker` agent | **agreed**; **built** (tool only: the agent is not deleted yet and nothing calls the tool yet) |
| `state` | `set` | Set one field in `state.md`, reject values outside the schema (not counters) | **agreed**; **built** |
| `state` | `bump` | Increase one counter, refuse to pass the cap (exit code 2); touches nothing else | **agreed**; **built** |
| `state` | `check` | Check `state.md` is valid, report every problem | **agreed**: build |
| `repo-check` | `commit-prefix` | Flag commit subjects without `t-N:` or `story-N:` (`--task t-N` requires that prefix; `[wip]` passes); reads subjects from stdin, never runs git | **agreed**; **built** |
| `repo-check` | `tests-unchanged` | Fail if a test file changed since the red-test commit; reads changed file names from stdin, test pattern via `--tests` | **agreed**; **built**; needs a new `config.md` key for the test-file pattern (`/tune-skills` must ask for it) |
| `repo-check` | `changelog` | One new `CHANGELOG.md` line under Unreleased ending in `(#issue)`; reads the diff from stdin, issue via `--issue` | **agreed**; **built**; must handle this repo's CHANGELOG heading format |
| `repo-check` | `tree-clean` | OK or list dirty files (untracked included) from `git status --porcelain` on stdin | **agreed**; **built**; one definition of "clean" for `run-story`, `resume-story`, `pause`, `stop` and the post-agent check |
| `tests` | `run` | Run the configured test command once, keep the full log, print exit code, log path, branch, SHA | **agreed**; **built** 2026-11-17 |
| `tests` | `failures` | List failing test names and first lines of each message from a raw log | **agreed**; **built** 2026-11-17 |
| `tests` | `classify` | PASS / FAIL / CANNOT RUN / UNKNOWN from exit code and log; UNKNOWN goes to an LLM | **agreed**; **built** 2026-11-17 |
| `tests` | `summary` | Counts of passed, failed, skipped tests | **agreed**; **built** 2026-11-17 |
| `tests` | `expect-red` | Given a task's test names: each ran and failed, none passed; assertion failure vs compile/import error | **agreed**; **built** 2026-11-17 |
| `tests` | `skipped-diff` | Compare skipped/disabled counts between two logs | **agreed**; **built** 2026-11-17 |
| `tests` | `failures-diff` | Same failing tests in two runs? ("same failure twice" rule) | **agreed**; **built** 2026-11-17 |
| `tests` | `logs-old` | List logs older than N stories, deletes nothing | **rejected** for now (cleanup can wait until logs hurt) |
| `plan` | `tasks-check` | Validate `tasks.md` (criteria, `blocked_by`, cycles, task count) | **agreed**; **built** 2026-11-17 |
| `plan` | `tasks-order` | Run order, skipping tasks blocked by a flagged one | **agreed**; **built** 2026-11-17 |
| `plan` | `config-check` | `config.md` has every key, every skill path exists | **agreed**; **built** 2026-11-17 |
| `pr` | `render-body` | Fill the PR template, enforce 20 lines and verbatim flags | **agreed**; **built** 2026-11-17 |
| `pr` | `check-base` | PR base equals the feature branch, from `gh pr view` JSON | **agreed**; **built** 2026-11-17 |
| `pr` | `check-flags` | Every flagged task and unresolved must-fix in `state.md` appears in the PR description | **agreed**; **built** 2026-11-17 |
| `guard` | `check-command` | Deny push to feature/main, force-push, merge, issue close, merge into protected branches; runs as a Claude Code hook | **agreed**; **built** 2026-11-17 |
| `guard` | `check-edit` | Deny edits to test files while the implementer runs | **rejected** (2026-11-16): needs an "active role" marker that can go stale, and `repo-check tests-unchanged` already detects the change right after, with the original safe in the `t-N: tests` commit |
| `report` | `submit` | Agent hands in its report (JSON on stdin); rejected with exact errors if malformed; saved to `.sketch/reports/<scope>-<role>-<run>.json` | **agreed**; **built** 2026-11-17 |
| `report` | `check` | Orchestrator checks a valid report exists for a scope, role and run (and names every brief skill); fails if missing | **agreed**; **built** 2026-11-17 |
| `report` | `get` | Read one field (verdict, must_fix, assumptions...) from a saved report | **agreed**; **built** 2026-11-17 |
