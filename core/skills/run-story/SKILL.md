---
name: run-story
description: Runs the implementation loop for the current story. Baseline check, then for each task the test-writer, implementer and reviewer, then the full suite and the story-end review with a fix loop, then opens the story PR into the feature branch. Never merges.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS (normally empty).

You are the orchestrator. You brief agents and check what they hand back. You do not run tests, review code or write code yourself.

## 1. Preconditions (fail hard)

If a check fails because something is missing, follow "Setup gaps" in the orchestrator rules (one list, offer to run the safe steps) before writing a STOPPED report.

- `.sketch/config.md`, `.sketch/tasks.md` and `.sketch/state.md` exist. The state has `phase: baseline`. If it shows a later phase or `stopped` is not `no`, stop: "Run /resume-story."
- The state file is valid: `{{TOOLS}}/sketch-state check --state .sketch/state.md` prints `ok`. Otherwise stop and tell the developer.
- The working tree is clean (`git status --porcelain | {{TOOLS}}/sketch-repo-check tree-clean`) and you are on the feature branch from the state, up to date with its remote (`git fetch`, then check you are not behind). Otherwise stop and tell the developer.
- The tracker CLI works.
- The config and the tasks file are valid: `{{TOOLS}}/sketch-plan config-check --config .sketch/config.md` and `{{TOOLS}}/sketch-plan tasks-check --tasks .sketch/tasks.md` both print `ok`. (`config-check` also checks that every skill path exists and that `test_paths`, the globs of the project's test files, is set.)

## 2. Baseline check

Run the `tester` agent in mode `baseline` (the untouched feature branch). If the result is not PASS, stop with the STOPPED report: a red or unrunnable baseline is the developer's problem (environment or existing breakage), not the loop's. Quote the tester's report and give the log path.

## 3. Story branch

- Create `story-<n>-<slug>` from the feature branch and switch to it. Record it: `{{TOOLS}}/sketch-state set story_branch story-<n>-<slug> --state .sketch/state.md`.
- Apply `.sketch/glossary-proposal.md` to `docs/GLOSSARY.md` and `docs/adr/` (create them if needed) and commit as `story-<n>: glossary`. If the proposal is empty, skip.
- Push the story branch and open a **draft** PR/MR into the feature branch, titled with the story, body "Work in progress" (`gh pr create --draft --base <feature-branch> ...` or `glab mr create --draft --target-branch <feature-branch> ...`). Record it: `{{TOOLS}}/sketch-state set pr <number or url> --state .sketch/state.md`. If the branch has no commit yet, do this right after t-1's tests commit.
- Set the phase: `{{TOOLS}}/sketch-state set phase task-loop --state .sketch/state.md`.

## 4. Task loop, one task at a time

Work the tasks **sequentially**, in the order the tool gives. Ask for the order again before every task, because a flag changes it: `{{TOOLS}}/sketch-plan tasks-order --tasks .sketch/tasks.md --flagged <flagged ids> --done <done ids>` (ids from the state file, like `t-2,t-4`; leave an option out when there are none). Take the first `run` line. A `skip t-<n> (blocked by ...)` line means that task cannot run: flag it with the reason "blocked by <ids>" (see e. Flags below) and move on. When there is no `run` line left, the task loop is over.

For each task, update the state after every step, check for `/pause` and `/stop` between agents, and write events to the journal the moment they happen. Note `git rev-parse HEAD` as the task's start when the task begins. After every task run `{{TOOLS}}/sketch-state check --state .sketch/state.md`; a problem means the state was damaged, so stop with the STOPPED report.

Every agent you start gets a run number for its report, and you check its report when it returns: `{{TOOLS}}/sketch-report check --role <role> --scope t-<n> --run <k> --reports .sketch/reports` must print `ok` (add a `--skills <path>` for each skill in the brief; orchestrator rules, "Checking what comes back"). The report's `outcome` is how you read the result: `{{TOOLS}}/sketch-report get --role <role> --scope t-<n> --run <k> --reports .sketch/reports outcome`. An `outside-code-failure` outcome stops everything with the STOPPED report, quoting its `detail`.

**a. Tests.** Run `test-writer` (mode write). Check its report, its commits and the tree with the tools, and that `git log` has the `t-<n>: tests` commit. `outcome` `no-clean-red` means it could not get a clean red in 2 attempts: flag the task. Otherwise set the status: `{{TOOLS}}/sketch-state set --task t-<n> status tests-red --state .sketch/state.md`. Then read where the red run is kept, because the implementer and the reviewer need both in their briefs: `{{TOOLS}}/sketch-report get --role test-writer --scope t-<n> --run <k> --reports .sketch/reports verification.target` and the same with `verification.results`.

**b. Implement.** Count the attempt first: `{{TOOLS}}/sketch-state bump --task t-<n> attempts --state .sketch/state.md`. Exit code 2 means the cap is reached: flag the task. Otherwise run `implementer` (mode implement; its brief gets the test target and the red run's results folder), check its report, commits and the tree with the tools, and read its `outcome`:
- `done`: set `status: green`.
- `test-looks-wrong`: run `test-writer` in mode `recheck` with the implementer's `detail` (its evidence). Its outcome `test-fixed`: run the implementer again (this counts as an attempt). `test-right`: give its `detail` (the reasoning) to the implementer and run it again. If the implementer still insists, flag the task.
- `conflicts-with-earlier-test`: flag the task: "conflicts with <id>'s test". That is a decision for the developer.
- `same-failure-twice`, or the attempt cap (the `bump` above exits 2): flag the task.

**c. Review.** First run the `tester` in mode `task` (`--scope t-<n>`) with the task's test target and a log path. Then run it again, one target per run, for every other test file the task changed (`git diff --name-only <task start>..HEAD`, filtered by `test_paths`), and give the reviewer all those reports. Run one tester at a time, never two in parallel: they share the results folder. `CANNOT RUN` stops everything (STOPPED report); a `FAIL` is not for you to judge: it goes to the reviewer, which files it as a must-fix. Then run the mechanical checks. Put the tester's report and the checks' output in the `reviewer`'s brief (the reviewer does not run tests). A failing check is not for you to judge: the reviewer files it as a must-fix.
- Tests untouched. `<tests-sha>` is the newest commit whose subject is `t-<n>: fix test (rechecked)`, or else `t-<n>: tests`. Pass each glob of `test_paths` from the config as `--tests`: `git diff --name-only <tests-sha>..HEAD | {{TOOLS}}/sketch-repo-check tests-unchanged --tests <glob>`
- Changelog: `git diff -U99999 <tests-sha>..HEAD -- CHANGELOG.md | {{TOOLS}}/sketch-repo-check changelog --issue <issue number of the task>`
- Commits: `git log --format=%s <task start>..HEAD | {{TOOLS}}/sketch-repo-check commit-prefix --task t-<n>`

Then set `status: in-review` and run `reviewer` (its brief gets the red run's results folder too), and read its `verdict` with `get` (`outside-code-failure` as its `outcome` stops everything).
- A `missing_skill` in its report: resume that reviewer with the skill's path first (orchestrator rules, "Checking what comes back"). This does not count as a review round.
- `SATISFIED`: set `status: done`, then close the task issue with a comment naming the SHAs of the task's commits (`git log --format=%h <task start>..HEAD`): `gh issue close <issue number> --comment "done in <commit SHAs>"` (`glab issue close <issue number>` after `glab issue note <issue number> -m "..."` for GitLab). Journal a REVIEW line if its `nice_to_have` is not empty.
- A task flagged for any reason (here or in another step): its issue stays open, and you add a comment on it saying why it was flagged (the flag reason). Never close the story issue.
- `CHANGES NEEDED`: its `must_fix` (read it with `--json`) is what the fix round gets. Count the round: `{{TOOLS}}/sketch-state bump --task t-<n> review_rounds --state .sketch/state.md`. If it succeeds, run a **fresh** `implementer` in mode `fix` with the `must_fix` findings quoted verbatim, then the `tester` (task mode) and the mechanical checks again, and a **fresh** `reviewer`. If it exits 2 (the cap), or the same finding comes back unchanged, flag the task with the unresolved must-fix findings, and journal a CAP line.

**d. Assumptions.** Read the implementer's `assumptions` (`get`, one per line). Any assumption that differs from the story brief goes to the journal as ASSUME: `{{TOOLS}}/sketch-journal add ASSUME S<n> t-<n> "<the assumption>" --journal .sketch/journal.md`.

**e. Flags.** To flag a task, do both, in this order: add the flag line with `{{TOOLS}}/sketch-state flag add --task t-<n> "<reason>" --state .sketch/state.md`, then set the status with `{{TOOLS}}/sketch-state set --task t-<n> status flagged --state .sketch/state.md`, journal a FLAG line, and comment on the task issue saying why (the flag reason; the issue stays open). `check` reports a flagged task without a flag line. It does not stop tasks that do not depend on it.

**f. Push.** When a task is `done` or `flagged`, push the story branch: `git push -u origin <story-branch>` (the first push sets the upstream). Never push the feature branch or main, never force-push. A push that fails is a failure outside the code: stop with the STOPPED report.

If an agent reports a failure that is outside the code (credentials, VPN, network, access, a missing tool), stop immediately with the STOPPED report. Do not retry, and do not let an agent work around it.

## 5. Story end

When no task can progress, set `phase: story-end` (`{{TOOLS}}/sketch-state set phase story-end --state .sketch/state.md`) and run the loop below, at most 3 rounds. Count each round: `{{TOOLS}}/sketch-state bump story_rounds --state .sketch/state.md`; exit code 2 means the cap is reached.

1. Run `tester` in mode `full`. Its `result` (`get` it) `CANNOT RUN` stops everything (STOPPED report, quoting `cannot_run_because`). Otherwise continue even if the result is `FAIL`.
2. Run `story-reviewer` with the diff scope (the story branch against the feature branch), the tester's report (give it the run number to read) and its `log` path, and the flags and assumptions so far. It reviews even when the suite is red.
3. If its `verdict` is `SATISFIED` and the tester `result` is `PASS`: leave the loop.
4. Otherwise, if rounds remain: when a finding asks for behavior no test covers yet, first run a **fresh** `test-writer` (mode write, `--scope story-<n>`) with those findings as its criteria; it commits `story-<n>: tests`. Then run a **fresh** `implementer` in mode `fix` (`--scope story-<n>`) with the story-reviewer's `must_fix` findings (including failing tests, verbatim) and the test-writer's red run, then go back to step 1 and count the round.
5. At the cap: leave the loop. The unresolved items go on top of the PR.

Journal a REVIEW line with the outcome and the rounds used (`{{TOOLS}}/sketch-journal add REVIEW S<n> - "<outcome, rounds used>" --journal .sketch/journal.md`).

## 6. Open the PR

Set `phase: pr` (`{{TOOLS}}/sketch-state set phase pr --state .sketch/state.md`). Write `.sketch/pr-extras.json` from the reports, quoting items verbatim: `summary` (two or three plain lines on what the user gets, from the brief), `tests_passed` (the tester's `counts.passed` from its last full-suite report), `reviewer_model` (the story-reviewer's `model`), `unresolved` (the story-reviewer's `must_fix` still open, each as one line, only if the story-end loop hit its cap), `nice_to_have` (the story-reviewer's, most important first), `manual_checks` (from the brief and the reviewers), `differs` (implementer assumptions that differ from the brief, each starting with its task id), `wip_commits` (`[wip]` commits never followed by a completed step). Only the first three keys are required; leave out a list that would be empty. Then run the `pr-agent` (give it a run number) with: the story branch, the feature branch, the paths of the state, brief and tasks files, and `.sketch/pr-extras.json`. It builds the description with the pr tool, fills the draft PR/MR from step 3 with it and marks it ready.

Then verify, yourself:
- the PR/MR exists and its **base is the feature branch**: `gh pr view <number> --json baseRefName,headRefName,state | {{TOOLS}}/sketch-pr check-base --base <feature-branch> --head <story-branch>` prints `ok` (for GitLab, `glab mr view <number> --output json` instead)
- every flagged task and every unresolved must-fix appears in its description: `gh pr view <number> --json body -q .body | {{TOOLS}}/sketch-pr check-flags --state .sketch/state.md --extras .sketch/pr-extras.json` prints `ok`
- `{{TOOLS}}/sketch-state check --state .sketch/state.md` prints `ok`, and the state has the PR and `pr_head_sha`

If anything is off, do not repair it silently. Stop with the STOPPED report.

## 7. Finish

- Comment on each `done` task issue: "done in PR #<n>". The story issue stays open; the developer closes it when the PR is merged. Task issues of `done` tasks were already closed in step 4c.
- Set the phase: `{{TOOLS}}/sketch-state set phase waiting-review --state .sketch/state.md`.
- Tell the developer, flags first: what was flagged and why, whether the story review was satisfied, the PR link. Then: "Next: review and merge the PR, then run /sketch for the next story. A retro may be worth running; /sketch will tell you."
