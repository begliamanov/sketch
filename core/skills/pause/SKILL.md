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
   - You must be on the story branch from the state. If not, stop and tell the developer what you found; do not commit anywhere else.
   - Commit everything on the story branch as `t-<n>: [wip] interrupted, not reviewed`, where `<n>` is the task that was in progress. If no task was in progress (for example during the story-end loop), use `story-<story>: [wip] interrupted, not reviewed`.
3. Set `stopped: manual: paused <time>` in `.sketch/state.md` and keep every counter as it is.

## 2. Wait

Say in one line what happened ("Paused in t-3, review round 1. WIP committed: 3 files.") and wait for the developer. Do nothing else.

## 3. When the developer is back

Ask: "Welcome back. Anything I should know? New context, changes, decisions." Take their answer as given.

- Append it, verbatim, to `.sketch/story-context.md` (create it if missing, with a timestamp). Every later agent brief for this story lists this file.
- Send it to the `drift-notetaker` as a `CONTEXT` event.
- If they say nothing is new, note that and continue.

## 4. Carry on

Set `stopped: no`. Continue the loop of `/run-story` from the recorded phase, restarting the interrupted step with a **fresh** agent. Tell the agent that the last commit, if it is a `[wip]` commit, is interrupted work and may be incomplete: it reads the diff, decides whether to build on it or redo it, and states which in its report. Its own commits fix it up. Counters are not reset.
