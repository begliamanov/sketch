---
name: stop
description: Stops a running slice. Asks whether the current story should finish first. If yes, finishes it and stops; if no, aborts now, commits interrupted work as WIP, writes a stop note and stops. Usage - /stop.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first.

## 1. Check

Fail hard if there is no slice in progress (`.sketch/state.md` missing, or `phase` is `done` or `waiting-review`).

## 2. Ask

Ask the developer: "Finish the current story first?" Offer yes / no, and ask for a one-line reason (optional, they can skip it).

## 3a. Yes: finish the story, then stop

- Set `stop_after_story: yes` in `.sketch/state.md`.
- Continue the `/run-slice` loop for the current story only: through its tests, implementation and review rounds, until it is `done` or `flagged`.
- Then do not start another story. Go to step 4 with `story choice: finished`.

If the developer interrupts with Esc while you are doing this, handle it as 3b.

## 3b. No: abort now

Treat anything still running as aborted. Check `git status --porcelain`.
- If the tree is dirty, you must be on the slice branch from the state, otherwise stop and tell the developer what you found. Commit everything on the slice branch as `us-<n>: [wip] interrupted, not reviewed` (or `slice-<slice>: [wip] interrupted, not reviewed` when no story was in progress).
- Go to step 4 with `story choice: aborted (WIP committed)`.

## 4. Save and stop

1. Write `.sketch/stop-note.md` in the format of `{{CORE}}/state-format.md`: time, `how: manual`, the phase, where (story and round), the story choice, and the developer's reason in their words.
2. Set `stopped: manual: <one line>` in `.sketch/state.md`; remove `stop_after_story`.
3. Send a `STOP` event to the `drift-notetaker`.
4. Tell the developer in two lines where it stopped and that `/resume-slice` continues from here. Then stop; do not start anything else.
