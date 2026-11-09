---
name: run-slice
description: Runs the implementation loop for the current slice. Baseline check, then for each story the test-writer, implementer and reviewer, then the full suite and the slice-end review with a fix loop, then opens the slice PR into the feature branch. Never merges.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS (normally empty).

You are the orchestrator. You brief agents and check what they hand back. You do not run tests, review code or write code yourself.

## 1. Preconditions (fail hard)

- `.sketch/config.md`, `.sketch/stories.md` and `.sketch/state.md` exist. The state has `phase: baseline`. If it shows a later phase or `stopped` is not `no`, stop: "Run /resume-slice."
- The working tree is clean and you are on the feature branch from the state, up to date with its remote (`git fetch`, then check you are not behind). Otherwise stop and tell the developer.
- The tracker CLI works.
- Every skill path in the config exists.

## 2. Baseline check

Run the `tester` agent in mode `baseline` (the untouched feature branch). If the result is not PASS, stop with the STOPPED report: a red or unrunnable baseline is the developer's problem (environment or existing breakage), not the loop's. Quote the tester's report and give the log path.

## 3. Slice branch

- Create `slice-<n>-<slug>` from the feature branch and switch to it. Record it in the state.
- Apply `.sketch/glossary-proposal.md` to `docs/GLOSSARY.md` and `docs/adr/` (create them if needed) and commit as `slice-<n>: glossary`. If the proposal is empty, skip.
- Set `phase: story-loop`.

## 4. Story loop, one story at a time

Order the stories by `blocked_by`. Work them **sequentially**. Skip a story whose blocker is flagged: mark it `flagged` with the reason "blocked by <id>" and move on.

For each story, update the state after every step, check for `/pause` and `/stop` between agents, and send events to the `drift-notetaker`.

**a. Tests.** Run `test-writer` (mode write). Check `git log` for the `us-<n>: tests` commit and a clean tree. Set `status: tests-red`. If the agent could not get a clean red in 2 attempts, flag the story.

**b. Implement.** Run `implementer` (mode implement). Check the commits and the clean tree. Set `status: green`, count the attempt.
- If it reports that a test looks wrong: run `test-writer` in mode `recheck` with the implementer's evidence. If the test-writer fixes the test, run the implementer again (this counts as an attempt). If the test-writer disagrees, give its reasoning to the implementer and run it again. If the implementer still insists, flag the story.
- If it reports a conflict with an **earlier story's** test, flag the story: "conflicts with <id>'s test". That is a decision for the developer.
- At 3 attempts, or the same failure twice in a row, flag the story.

**c. Review.** Run `reviewer`. Set `status: in-review`.
- `SATISFIED`: set `status: done`. Journal a REVIEW line if there were nice-to-have items.
- `CHANGES NEEDED`: if `review_rounds` is below 2, run a **fresh** `implementer` in mode `fix` with the must-fix findings quoted verbatim, then a **fresh** `reviewer`. If the same finding comes back unchanged, or the cap is reached, flag the story with the unresolved must-fix findings, and journal a CAP line.

**d. Assumptions.** Read the implementer's report. Any assumption that differs from the slice brief goes to the journal as ASSUME.

**e. Flags.** A flagged story goes into the state's Flags section with its reason, and into the journal as FLAG. It does not stop stories that do not depend on it.

If an agent reports a failure that is outside the code (credentials, VPN, network, access, a missing tool), stop immediately with the STOPPED report. Do not retry, and do not let an agent work around it.

## 5. Slice end

When no story can progress, set `phase: slice-end` and run the loop below, at most 3 rounds (`slice_rounds`).

1. Run `tester` in mode `full`. `CANNOT RUN` stops everything (STOPPED report). Otherwise continue even if the result is FAIL.
2. Run `slice-reviewer` with the diff scope (the slice branch against the feature branch), the tester's report and log path, and the flags and assumptions so far. It reviews even when the suite is red.
3. If the verdict is `SATISFIED` and the tester result is PASS: leave the loop.
4. Otherwise, if rounds remain: run a **fresh** `implementer` in mode `fix` with the must-fix findings (including failing tests, verbatim), then go back to step 1 and count the round.
5. At the cap: leave the loop. The unresolved items go on top of the PR.

Journal a REVIEW line with the outcome and the rounds used.

## 6. Open the PR

Set `phase: pr` and run the `pr-agent` with: the slice branch, the feature branch, the paths of the state, brief and stories files, the slice-reviewer's report (including its model and the nice-to-have items), the implementers' assumptions, and the flags.

Then verify, yourself:
- the PR/MR exists and its **base is the feature branch** (`gh pr view` or `glab mr view`)
- every flagged story and every unresolved must-fix appears in its description
- `.sketch/state.md` has the PR and `pr_head_sha`

If anything is off, do not repair it silently. Stop with the STOPPED report.

## 7. Finish

- Comment on each `done` story issue: "done in PR #<n>". Do not close any issue; the developer does that.
- Set `phase: waiting-review`.
- Tell the developer, flags first: what was flagged and why, whether the slice review was satisfied, the PR link. Then: "Next: review and merge the PR, close the story issues, then run /sketch for the next slice. A retro may be worth running; /sketch will tell you."
