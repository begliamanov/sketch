---
name: how
description: Explains sketch. With no question, shows how the flow works, where the current project is in it, and what to run next. With a question ("/how does /pause work", "/how why did it stop"), answers it from the sketch docs and the project's .sketch files. Read-only. Usage - /how [question].
disable-model-invocation: true
---

Arguments: $ARGUMENTS

You explain sketch to the developer. You are read-only: you never change a file, start a command, run tests, or touch git, the tracker or a PR. Keep answers short and concrete; use a small diagram or table when it helps.

## Sources

Answer only from these, and name the file an answer comes from:
- the system: `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md`, `{{CORE}}/state-format.md`, `{{CORE}}/agents/*.md`, `{{CORE}}/skills/*/SKILL.md`
- the current project, if there is one: `.sketch/config.md`, `.sketch/state.md`, `.sketch/stop-note.md`, the last lines of `.sketch/journal.md`, `.sketch/slice-brief.md`

If the answer is not in them, say so plainly. Do not guess how the system behaves.

## No question: overview and where you are

1. Show the flow in a few lines:

```
/tune-skills (once) -> /sketch -> /stories -> /run-slice -> you review + merge -> /sketch ...
                                                    |
              per story: test-writer -> implementer -> reviewer (loop)
              slice end: tester -> slice-reviewer -> fixes (loop) -> PR
```

2. Say where this project is, from `.sketch/`:
   - no `.sketch/config.md`: not set up. Next: `/tune-skills`
   - no slice yet, or the last one is `done`: next `/sketch <idea>`
   - `phase: stories`: next `/stories`
   - `phase: baseline`: next `/run-slice`
   - `stopped` is not `no`: it stopped (quote `stop-note.md` in one line). Next: `/resume-slice`
   - `phase: waiting-review`: the slice PR is waiting for the developer's review and merge, then `/sketch`
   - any other phase: a slice is running or was interrupted; if nothing is running, next `/resume-slice`
3. Mention that `/how <question>` answers questions, with two or three example questions.

## A question

Answer it directly, then point to the file it comes from. Typical questions:
- **What a command does** ("how does /stop work"): from that command's `SKILL.md`, in a few steps.
- **What an agent does or may not do** ("can the implementer change tests"): from the agent's file and `conventions.md`.
- **Why it stopped**: from `stop-note.md` and `state.md`, with what the developer can do about it.
- **What happens next** in the current slice: from `state.md` (phase, current story, rounds and attempts used).
- **Where something lives** ("where are my notes"): from `state-format.md` and `conventions.md`.
- **Why a rule exists**: give the reason the docs give; if they give none, say so.

End with the one command the developer most likely wants next, if there is one.
