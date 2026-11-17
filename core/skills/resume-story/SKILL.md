---
name: resume-story
description: Resumes a story after it was stopped by the developer, stopped by a failure, or interrupted by a crash or closed terminal. Reads the saved state and stop note, checks them against git, the tracker and the PR, reports where it stopped, and continues only after the developer says go.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS (normally empty).

## 1. Read

- `.sketch/state.md`, `.sketch/stop-note.md` (if present), `.sketch/config.md`, the last lines of `.sketch/journal.md`.
- Run `{{TOOLS}}/sketch-state check --state .sketch/state.md`. Problems mean the state file was damaged (a crash, or a hand edit): count it as a risky mismatch and list the problems verbatim.
- If there is no state, or `phase` is `done`, say there is nothing to resume.
- If `phase` is `waiting-review`: look at the story PR/MR. Merged means the story is finished: set `phase: done` and suggest `/sketch` for the next story. Still open means there is nothing to resume yet.

## 2. If a failure caused the stop

The state says `stopped: failure: ...`. Re-run the specific check that failed (the tool, the login, the command) before anything else. If it still fails, stop again with the same STOPPED report; do not go further.

## 3. Reconcile with reality

Gather the facts below, write them as JSON to `.sketch/reconcile-facts.json`, and let the tool classify what differs: `{{TOOLS}}/sketch-state reconcile --state .sketch/state.md < .sketch/reconcile-facts.json`. Leave out a fact you could not gather; it is then not checked. The keys:

- `feature_branch_exists`, `story_branch_exists` (`true` or `false`): `git rev-parse --verify <branch>` succeeds
- `current_branch`: the branch you are on (`git rev-parse --abbrev-ref HEAD`)
- `feature_moved` (`true` or `false`): the feature branch has commits that the story branch does not contain (`git merge-base --is-ancestor <feature-branch> <story-branch>` fails)
- `task_commits`: for each task, whether `git log --grep '^t-<n>:'` finds commits on the story branch, like `{"t-1": true, "t-2": false}`
- `unknown_commits`: the subjects of commits on the story branch that the state does not know about (they may be the developer's own)
- `tree_dirty`: the lines of `git status --porcelain` (empty list when clean; `git status --porcelain | {{TOOLS}}/sketch-repo-check tree-clean` says the same)
- `issues`: `"story"` and each task id, mapped to `open`, `closed` or `missing` on the tracker
- `pr`: `open`, `merged`, `closed` or `missing`, only when the state has a PR
- `cli_logged_in`: `gh auth status` (or `glab auth status`) succeeded
- `config_problems`: the lines `{{TOOLS}}/sketch-plan config-check --config .sketch/config.md` printed, left out when it printed `ok`
- `state_problems`: the lines `{{TOOLS}}/sketch-state check --state .sketch/state.md` printed, left out when it printed `ok`

It prints `risky:` lines first, then `harmless:` lines. Do not reclassify them.
- **Risky: stop and ask.** Collect **all** of them before reporting, so the developer sees them at once.
- **Harmless: adopt it, journal it, report it.** For commits the state did not know about (the developer's own work), journal an `EDIT` line: `{{TOOLS}}/sketch-journal add EDIT S<n> - "<what they added>" --me --journal .sketch/journal.md`. A dirty tree left by a crash is committed as WIP, with the message from the tool: `{{TOOLS}}/sketch-state wip-message --state .sketch/state.md --branch <the branch you are on> --task t-<n>` (leave `--task` out when no task was in progress). It refuses when you are not on the story branch: then do not commit, report it. Say which files the WIP commit contained.

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

- Set `stopped: no` (`{{TOOLS}}/sketch-state set stopped no --state .sketch/state.md`). Journal a `NOTE` line saying the story was resumed and why it had stopped (`{{TOOLS}}/sketch-journal add NOTE S<n> - "<resumed, and why it had stopped>" --journal .sketch/journal.md`).
- Continue `/run-story` from the recorded phase, restarting the interrupted step with a **fresh** agent (it gets the next run number for its report; count the files in `.sketch/reports` for that role and scope). If the last commit is a `[wip]` commit, tell the agent it is interrupted work and may be incomplete: it reads the diff, decides whether to build on it or redo it, and states which in its report.
- Counters are kept: a resume never resets a round or attempt cap.
- Include `.sketch/story-context.md` in the briefs, if it exists.
