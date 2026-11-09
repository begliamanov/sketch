---
name: retro
description: Walks through the drift journal and review comments after a slice (or, with "final", after the whole feature and the team's review), asks the developer for their view, and proposes at most three improvements as diffs. Applies nothing without explicit approval, item by item. Usage - /retro or /retro final <big PR number>.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS

## 1. Preconditions (fail hard)

- `.sketch/` exists with a journal and state. The tracker CLI works.
- Mode `slice` (default): the latest slice's PR is merged. Mode `final`: you have the number of the big PR to the default branch, from the arguments or by asking.
- Slices covered: everything since the last retro, recorded in `.sketch/retro/last.md`. If that file is missing, all slices.

## 2. Analyze

Run the `retro-agent` in the right mode. It writes a draft to `.sketch/retro/`.

## 3. Walk through it with the developer

1. Show the drift block of each slice covered: planned, built, drift items with who found each and when, and the signals.
2. Ask: "Anything to add from your side?" (what felt wrong, slow, confusing, or good). Record their answer in the draft under "Developer's view", and as a `[me]` NOTE line in the journal.
3. Show where each review problem should have been caught earlier, and the root cause of each flag.

Keep it short. If a slice had nothing notable, say so and move on.

## 4. Proposals

Present the proposals one at a time (at most three): the change as a diff, and its evidence. For each, ask: approve, reject, or edit.

- **Approved**: apply that one change and nothing else. Prefer editing the file in the sketch repo's `core/`, and tell the developer to rerun `adapters/claude-code/install.sh` for the installed copies. Project-level changes (the config, the glossary, project skills) are made in the project. Never apply a proposal that was not approved in this conversation.
- **Rejected**: append it with the developer's reason to `.sketch/retro/rejected.md`, so it is not proposed again.
- **Edited**: show the edited version and ask again.

## 5. Record

- Write `.sketch/retro/<slices covered>.md` with the drift blocks, the developer's view, and the decisions.
- Update `.sketch/retro/last.md` with the last slice covered.

## 6. Final mode only

At the end, ask whether to delete `.sketch/initial-sketch.md`, the original spec. It stops being a source of truth after the retro. Delete only that file, and only on a yes. Keep the journal, the retro files and the config until the developer says otherwise.
