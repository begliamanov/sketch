---
name: resume-story
description: Resumes a story after it was stopped by the developer, stopped by a failure, or interrupted by a crash or closed terminal. Reads the saved state and stop note, checks them against git, the tracker and the PR, reports where it stopped, and continues only after the developer says go.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS (normally empty).

## 1. Read

- `.sketch/state.md`, `.sketch/stop-note.md` (if present), `.sketch/config.md`, the last lines of `.sketch/journal.md`.
- If there is no state, or `phase` is `done`, say there is nothing to resume.
- If `phase` is `waiting-review`: look at the story PR/MR. Merged means the story is finished: set `phase: done` and suggest `/sketch` for the next story. Still open means there is nothing to resume yet.

## 2. If a failure caused the stop

The state says `stopped: failure: ...`. Re-run the specific check that failed (the tool, the login, the command) before anything else. If it still fails, stop again with the same STOPPED report; do not go further.

## 3. Reconcile with reality

Check everything below and classify each difference.

- **Harmless: adopt it, journal it, report it.** Commits on the story branch that the state does not know about and that only add to it (the developer's own work; record them in the state and journal an `EDIT` line); issue titles or text that were edited; a dirty tree left by a crash (committed as WIP, see below).
- **Risky: stop and ask.** The feature branch moved since the story branch was created; issues closed, deleted or missing; commits the state records that are missing from the story branch; the story branch missing or rewritten; the PR merged or closed unexpectedly; `gh` or `glab` not logged in; the config or a skill path missing.

Collect **all risky mismatches before reporting**, so the developer sees them at once.

- **Git**: the feature branch and the story branch exist; the commits the state records are on the story branch (`git log --grep '^t-<n>:'` for each finished task); commits on the story branch the state does not know about (they may be the developer's); the feature branch moved since the story branch was created; the current branch.
- **Working tree**: if it is dirty (a crash or closed terminal left changes), commit it on the story branch as `t-<n>: [wip] interrupted, not reviewed` (or `story-<story>: [wip] ...`), and report which files it contained. If you are not on the story branch, do not commit; report it.
- **Tracker**: the story issue and the task issues exist; issues closed or edited when the state says otherwise.
- **PR**: if the state has one, whether it is open, merged or closed.
- **Tools**: `gh` or `glab` is logged in.
- **Config and skills**: the config exists and every skill path in it exists.

## 4. Report and wait

Give the developer the context, then wait for an explicit go. Always ask, even when nothing is wrong.

```
Stopped:    <when, how: manual | failure | crash>, <reason in their words or the failure>
Where:      <phase, task, round; counters so far>
Reconciled: OK | adopted: <each harmless difference, one line> | RISKY: <each, one line>
WIP:        <files committed as WIP now, if any>
Next:       <what I will do: restart <step> with a fresh agent>
```

Harmless differences were already adopted; list them so the developer can see them. If there are risky mismatches, do not go on: say what you suggest, and let the developer decide.

## 5. On go

- Set `stopped: no`. Journal a `NOTE` line saying the story was resumed and why it had stopped.
- Continue `/run-story` from the recorded phase, restarting the interrupted step with a **fresh** agent. If the last commit is a `[wip]` commit, tell the agent it is interrupted work and may be incomplete: it reads the diff, decides whether to build on it or redo it, and states which in its report.
- Counters are kept: a resume never resets a round or attempt cap.
- Include `.sketch/story-context.md` in the briefs, if it exists.
