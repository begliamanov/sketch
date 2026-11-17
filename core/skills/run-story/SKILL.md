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
- Set the phase: `{{TOOLS}}/sketch-state set phase task-loop --state .sketch/state.md`.

## 4. Task loop, one task at a time

Work the tasks **sequentially**, in the order the tool gives. Ask for the order again before every task, because a flag changes it: `{{TOOLS}}/sketch-plan tasks-order --tasks .sketch/tasks.md --flagged <flagged ids> --done <done ids>` (ids from the state file, like `t-2,t-4`; leave an option out when there are none). Take the first `run` line. A `skip t-<n> (blocked by ...)` line means that task cannot run: flag it with the reason "blocked by <ids>" (see e. Flags below) and move on. When there is no `run` line left, the task loop is over.

For each task, update the state after every step, check for `/pause` and `/stop` between agents, and write events to the journal the moment they happen. Note `git rev-parse HEAD` as the task's start when the task begins. After every task run `{{TOOLS}}/sketch-state check --state .sketch/state.md`; a problem means the state was damaged, so stop with the STOPPED report.

**a. Tests.** Run `test-writer` (mode write). Check its commits and the tree with the tools (orchestrator rules, "Checking what comes back"), and that `git log` has the `t-<n>: tests` commit. Set the status: `{{TOOLS}}/sketch-state set --task t-<n> status tests-red --state .sketch/state.md`. If the agent could not get a clean red in 2 attempts, flag the task.

**b. Implement.** Count the attempt first: `{{TOOLS}}/sketch-state bump --task t-<n> attempts --state .sketch/state.md`. Exit code 2 means the cap is reached: flag the task. Otherwise run `implementer` (mode implement), check its commits and the tree with the tools, and set `status: green`.
- If it reports that a test looks wrong: run `test-writer` in mode `recheck` with the implementer's evidence. If the test-writer fixes the test, run the implementer again (this counts as an attempt). If the test-writer disagrees, give its reasoning to the implementer and run it again. If the implementer still insists, flag the task.
- If it reports a conflict with an **earlier task's** test, flag the task: "conflicts with <id>'s test". That is a decision for the developer.
- At the attempt cap (the `bump` above exits 2), or the same failure twice in a row, flag the task.

**c. Review.** First run the mechanical checks and put their output in the `reviewer`'s brief. A failing check is not for you to judge: the reviewer files it as a must-fix.
- Tests untouched. `<tests-sha>` is the newest commit whose subject is `t-<n>: fix test (rechecked)`, or else `t-<n>: tests`. Pass each glob of `test_paths` from the config as `--tests`: `git diff --name-only <tests-sha>..HEAD | {{TOOLS}}/sketch-repo-check tests-unchanged --tests <glob>`
- Changelog: `git diff -U99999 <tests-sha>..HEAD -- CHANGELOG.md | {{TOOLS}}/sketch-repo-check changelog --issue <issue number of the task>`
- Commits: `git log --format=%s <task start>..HEAD | {{TOOLS}}/sketch-repo-check commit-prefix --task t-<n>`

Then set `status: in-review` and run `reviewer`.
- `SATISFIED`: set `status: done`. Journal a REVIEW line if there were nice-to-have items.
- `CHANGES NEEDED`: count the round: `{{TOOLS}}/sketch-state bump --task t-<n> review_rounds --state .sketch/state.md`. If it succeeds, run a **fresh** `implementer` in mode `fix` with the must-fix findings quoted verbatim, then the mechanical checks again and a **fresh** `reviewer`. If it exits 2 (the cap), or the same finding comes back unchanged, flag the task with the unresolved must-fix findings, and journal a CAP line.

**d. Assumptions.** Read the implementer's report. Any assumption that differs from the story brief goes to the journal as ASSUME: `{{TOOLS}}/sketch-journal add ASSUME S<n> t-<n> "<the assumption>" --journal .sketch/journal.md`.

**e. Flags.** To flag a task, do both, in this order: add the flag line with `{{TOOLS}}/sketch-state flag add --task t-<n> "<reason>" --state .sketch/state.md`, then set the status with `{{TOOLS}}/sketch-state set --task t-<n> status flagged --state .sketch/state.md`, and journal a FLAG line. `check` reports a flagged task without a flag line. It does not stop tasks that do not depend on it.

**f. Push.** When a task is `done` or `flagged`, push the story branch: `git push -u origin <story-branch>` (the first push sets the upstream). Never push the feature branch or main, never force-push. A push that fails is a failure outside the code: stop with the STOPPED report.

If an agent reports a failure that is outside the code (credentials, VPN, network, access, a missing tool), stop immediately with the STOPPED report. Do not retry, and do not let an agent work around it.

## 5. Story end

When no task can progress, set `phase: story-end` (`{{TOOLS}}/sketch-state set phase story-end --state .sketch/state.md`) and run the loop below, at most 3 rounds. Count each round: `{{TOOLS}}/sketch-state bump story_rounds --state .sketch/state.md`; exit code 2 means the cap is reached.

1. Run `tester` in mode `full`. `CANNOT RUN` stops everything (STOPPED report). Otherwise continue even if the result is FAIL.
2. Run `story-reviewer` with the diff scope (the story branch against the feature branch), the tester's report and log path, and the flags and assumptions so far. It reviews even when the suite is red.
3. If the verdict is `SATISFIED` and the tester result is PASS: leave the loop.
4. Otherwise, if rounds remain: run a **fresh** `implementer` in mode `fix` with the must-fix findings (including failing tests, verbatim), then go back to step 1 and count the round.
5. At the cap: leave the loop. The unresolved items go on top of the PR.

Journal a REVIEW line with the outcome and the rounds used (`{{TOOLS}}/sketch-journal add REVIEW S<n> - "<outcome, rounds used>" --journal .sketch/journal.md`).

## 6. Open the PR

Set `phase: pr` (`{{TOOLS}}/sketch-state set phase pr --state .sketch/state.md`) and run the `pr-agent` with: the story branch, the feature branch, the paths of the state, brief and tasks files, the story-reviewer's report (including its model and the nice-to-have items), the implementers' assumptions, and the flags.

Then verify, yourself:
- the PR/MR exists and its **base is the feature branch** (`gh pr view` or `glab mr view`)
- every flagged task and every unresolved must-fix appears in its description
- `{{TOOLS}}/sketch-state check --state .sketch/state.md` prints `ok`, and the state has the PR and `pr_head_sha`

If anything is off, do not repair it silently. Stop with the STOPPED report.

## 7. Finish

- Comment on each `done` task issue: "done in PR #<n>". Do not close any issue; the developer does that.
- Set the phase: `{{TOOLS}}/sketch-state set phase waiting-review --state .sketch/state.md`.
- Tell the developer, flags first: what was flagged and why, whether the story review was satisfied, the PR link. Then: "Next: review and merge the PR, close the task issues, then run /sketch for the next story. A retro may be worth running; /sketch will tell you."
