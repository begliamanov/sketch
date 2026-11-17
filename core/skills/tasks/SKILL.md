---
name: tasks
description: Splits the approved story brief into small tasks with acceptance criteria and test scenarios, then creates the story issue and the task sub-issues on GitHub or GitLab. Normally started by /sketch, with no extra approval; when run by hand, it asks for approval of the list first.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md` and `{{CORE}}/orchestrator.md` first. Arguments: $ARGUMENTS (normally empty).

## 1. Preconditions (fail hard)

- `.sketch/config.md`, `.sketch/story-brief.md` and `.sketch/state.md` exist, and the state has `phase: tasks`.
- The tracker CLI named in the config works (`gh auth status` or `glab auth status`).
- `.sketch/tasks.md` may exist from a stopped earlier run of this command. If the state already holds a story issue number, this is a resume: skip to step 4 and let the publish mode finish what is missing.

## 2. Draft

Run the `task-writer` agent in **draft** mode. Brief it as described in the orchestrator rules: paths to the brief, the glossary, the config, the task-writer's skills (the `common` list plus `task-writer`, plus any extra skills for this story).

Give it run number 1 and check its report (orchestrator rules, "Checking what comes back"). Read its `outcome`: `too-big`, `too-small` or `too-vague` is relayed to the developer with its `detail` (they decide: go back to `/sketch`, or give you what is missing); `outside-code-failure` stops with the STOPPED report; `done` goes on.

Then check the file yourself: `{{TOOLS}}/sketch-plan tasks-check --tasks .sketch/tasks.md` must print `ok`. If it reports problems, give them to the `task-writer` verbatim and have it fix the file once; if it still reports problems, stop and tell the developer. A report that the story has too few or too many tasks is a decision for the developer too (merge it into the next story, or split it).

## 3. Approval

There are two cases. Check which one applies before doing anything else in this step.

**Started by `/sketch` (the normal case).** The developer's approval of the playback is the approval for the tasks and the issues. Do not ask again. Show the table below as information, followed by the task-writer's doubts and assumptions, if any, one line each. Then go straight to step 4. Journal each assumption as an ASSUME line: `{{TOOLS}}/sketch-journal add ASSUME S<n> - "<the assumption>" --journal .sketch/journal.md`. The only exception is step 2: if the story is too big or too vague, stop and ask.

**Run by hand (`/tasks` typed by the developer).** The developer must approve the list explicitly. Do not create any issue before they say yes.

The table:

```
Story <n>: <title> -> <k> tasks
1. t-1  <title>   blocked by: none   <n> scenarios   skills: <short names>
2. t-2  <title>   blocked by: t-1   <n> scenarios   skills: <short names>
```

When run by hand, offer to show any task's criteria and scenarios in full. The developer may approve, merge tasks, split them, reorder, or rewrite criteria. Apply small changes to `.sketch/tasks.md` yourself. For a new split, run the task-writer again with the developer's feedback.

## 4. Publish

Run the `task-writer` agent in **publish** mode (run number 2) and check its report; its `story_issue` (`{{TOOLS}}/sketch-report get --role task-writer --scope story-<n> --run 2 --reports .sketch/reports story_issue`) is the story issue number. Afterwards run `{{TOOLS}}/sketch-state check --state .sketch/state.md`: it must print `ok`, and the story issue number and every task's issue number must be in the file. Then set the phase: `{{TOOLS}}/sketch-state set phase baseline --state .sketch/state.md`.

If publishing fails (sub-issues or blocking links unsupported, a CLI error, an auth problem), stop with the STOPPED report and quote the error. Do not ask for a workaround. Issues created before the failure stay recorded in the state, and running `/tasks` again creates only what is missing.

## 5. Next

If started by `/sketch`, continue straight into `/run-story`. Otherwise tell the developer: "Next: /run-story".
