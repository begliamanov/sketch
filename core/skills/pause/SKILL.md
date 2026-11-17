---
name: pause
description: Pauses a running story until the developer is back. Aborts whatever is running, commits interrupted work as a WIP commit, waits, then asks for context and carries on. Usage - /pause.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first.

The developer may have pressed Esc to interrupt a running agent and then typed this, or typed it at a step boundary. Either way, treat anything still running as aborted.

## 1. Secure the work

1. Fail hard if there is no story in progress (`.sketch/state.md` missing or `phase` is `done`).
2. Check `git status --porcelain`. If the tree is dirty:
   - Get the commit message from the tool: `{{TOOLS}}/sketch-state wip-message --state .sketch/state.md --branch <the branch you are on, from git rev-parse --abbrev-ref HEAD> --task t-<n>`, where `<n>` is the task that was in progress (leave `--task` out when no task was, for example during the story-end loop). It refuses (exit 2) when you are not on the story branch: then stop and tell the developer what you found; do not commit anywhere else.
   - Commit everything on the story branch with that message.
3. Set it in the state and keep every counter as it is: `{{TOOLS}}/sketch-state set stopped "manual: paused <time>" --state .sketch/state.md`.

## 2. Wait

Say in one line what happened ("Paused in t-3, review round 1. WIP committed: 3 files.") and wait for the developer. Do nothing else.

## 3. When the developer is back

Ask: "Welcome back. Anything I should know? New context, changes, decisions." Take their answer as given.

- Append it, verbatim, to `.sketch/story-context.md` (create it if missing, with a timestamp). Every later agent brief for this story lists this file.
- Journal it as a `CONTEXT` event, in their words: `{{TOOLS}}/sketch-journal add CONTEXT S<n> - "<their words>" --me --journal .sketch/journal.md`.
- If they say nothing is new, note that and continue.

## 4. Carry on

Set `stopped: no` (`{{TOOLS}}/sketch-state set stopped no --state .sketch/state.md`). Continue the loop of `/run-story` from the recorded phase, restarting the interrupted step with a **fresh** agent (it gets the next run number for its report). Tell the agent that the last commit, if it is a `[wip]` commit, is interrupted work and may be incomplete: it reads the diff, decides whether to build on it or redo it, and states which in its report. Its own commits fix it up. Counters are not reset.
