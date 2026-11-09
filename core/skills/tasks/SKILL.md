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

If it reports that the story is too big or too vague, relay that to the developer. They decide: go back to `/sketch`, or give you what is missing.

## 3. Approval

There are two cases. Check which one applies before doing anything else in this step.

**Started by `/sketch` (the normal case).** The developer's approval of the playback is the approval for the tasks and the issues. Do not ask again. Show the table below as information, followed by the task-writer's doubts and assumptions, if any, one line each. Then go straight to step 4. Send the assumptions to the `drift-notetaker`. The only exception is step 2: if the story is too big or too vague, stop and ask.

**Run by hand (`/tasks` typed by the developer).** The developer must approve the list explicitly. Do not create any issue before they say yes.

The table:

```
Story <n>: <title> -> <k> tasks
1. t-1  <title>   blocked by: none   <n> scenarios
2. t-2  <title>   blocked by: t-1   <n> scenarios
```

When run by hand, offer to show any task's criteria and scenarios in full. The developer may approve, merge tasks, split them, reorder, or rewrite criteria. Apply small changes to `.sketch/tasks.md` yourself. For a new split, run the task-writer again with the developer's feedback.

## 4. Publish

Run the `task-writer` agent in **publish** mode. Afterwards check `.sketch/state.md`: the story issue number and every task's issue number are there, and the task table is complete. Set `phase: baseline`.

If publishing fails (sub-issues or blocking links unsupported, a CLI error, an auth problem), stop with the STOPPED report and quote the error. Do not ask for a workaround. Issues created before the failure stay recorded in the state, and running `/tasks` again creates only what is missing.

## 5. Next

If started by `/sketch`, continue straight into `/run-story`. Otherwise tell the developer: "Next: /run-story".
