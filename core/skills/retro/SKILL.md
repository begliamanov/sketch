---
name: retro
description: Walks through the drift journal and review comments after a story (or, with "final", after the whole feature and the team's review), asks the developer for their view, and proposes at most three improvements as diffs. Applies nothing without explicit approval, item by item. Usage - /retro or /retro final <big PR number>.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md`, `{{CORE}}/orchestrator.md` and `{{CORE}}/state-format.md` first. Arguments: $ARGUMENTS

## 1. Preconditions (fail hard)

- `.sketch/` exists with a journal and state. The tracker CLI works.
- Mode `story` (default): the latest story's PR is merged. Mode `final`: you have the number of the big PR to the default branch, from the arguments or by asking.
- Stories covered: everything since the last retro, recorded in `.sketch/retro/last.md`. If that file is missing, all stories.

## 2. Analyze

Run the `retro-agent` in the right mode (give it the next run number for this story). It writes a draft to `.sketch/retro/` and hands back a report: check it, and read the draft's path with `{{TOOLS}}/sketch-report get --role retro-agent --scope story-<n> --run <k> --reports .sketch/reports draft_path`.

## 3. Walk through it with the developer

Follow "How to talk" in the orchestrator rules.

1. One line per finding: every flag or cap hit, every defect the developer or the team found in review, and every `[me]` line from `.sketch/journal.md` for the stories covered (NOTE, EDIT and CONTEXT; cut at a sentence end, never reworded) with what became of it. Get them from the tool, not by reading: `{{TOOLS}}/sketch-journal me-lines --journal .sketch/journal.md --after <the last story the previous retro covered>` (or `--story S<n>`), and print its lines exactly as they are. These are the developer's own words, so they come before anything else. Later, say for each note whether it became a proposal, and if not, why not.
2. Your take on the cause and the fix.
3. Ask: "Anything to add from your side?" (what felt wrong, slow, confusing, or good). Record the answer in the draft under "Developer's view", and as a `[me]` NOTE line in the journal.
4. Drift blocks, where each review problem should have been caught, and flag causes: only when the developer asks.

In `final` mode, include the one-line numbers (rounds, flags, comments from the developer and from the team per story).
If a story had nothing notable, say so and move on.

## 4. Proposals

Present the proposals one at a time (at most three): the change as a diff, and its evidence. For each, ask: approve, reject, or edit.

- **Approved**: apply that one change and nothing else. Edit the source file under `{{CORE_SOURCE}}`, never the installed copy under `{{CORE}}`, and tell the developer to rerun the adapter's install script (for Claude Code: `adapters/claude-code/install.sh`) so the installed copies pick up the change. Project-level changes (the config, the glossary, project skills) are made in the project. Never apply a proposal that was not approved in this conversation.
- **Rejected**: append it with the developer's reason to `.sketch/retro/rejected.md`, so it is not proposed again.
- **Edited**: show the edited version and ask again.

## 5. Record

- Write `.sketch/retro/<stories covered>.md` with the drift blocks, the developer's view, and the decisions.
- Update `.sketch/retro/last.md` with the last story covered.

## 6. Final mode only

At the end, ask whether to delete `.sketch/initial-sketch.md`, the original spec. It stops being a source of truth after the retro. Delete only that file, and only on a yes. Keep the journal, the retro files and the config until the developer says otherwise.
