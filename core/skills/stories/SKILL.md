---
name: stories
description: Splits the approved slice brief into small user stories with acceptance criteria and test scenarios, shows the list for approval, then creates the slice issue and the story sub-issues on GitHub or GitLab.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md` and `{{CORE}}/orchestrator.md` first. Arguments: $ARGUMENTS (normally empty).

## 1. Preconditions (fail hard)

- `.sketch/config.md`, `.sketch/slice-brief.md` and `.sketch/state.md` exist, and the state has `phase: stories`.
- The tracker CLI named in the config works (`gh auth status` or `glab auth status`).
- `.sketch/stories.md` may exist from a stopped earlier run of this command. If the state already holds a slice issue number, this is a resume: skip to step 4 and let the publish mode finish what is missing.

## 2. Draft

Run the `story-writer` agent in **draft** mode. Brief it as described in the orchestrator rules: paths to the brief, the glossary, the config, the story-writer's skills (the `common` list plus `story-writer`, plus any extra skills for this slice).

If it reports that the slice is too big or too vague, relay that to the developer. They decide: go back to `/sketch`, or give you what is missing.

## 3. Approval, every time

Show the developer the list as a short table:

```
Slice <n>: <title> -> <k> stories
1. us-1  <title>   blocked by: none   <n> scenarios
2. us-2  <title>   blocked by: us-1   <n> scenarios
```

Offer to show any story's criteria and scenarios in full. The developer may approve, merge stories, split them, reorder, or rewrite criteria. Apply small changes to `.sketch/stories.md` yourself. For re-slicing, run the story-writer again with the developer's feedback. Do not create any issue before an explicit approval.

## 4. Publish

Run the `story-writer` agent in **publish** mode. Afterwards check `.sketch/state.md`: the slice issue number and every story's issue number are there, and the story table is complete. Set `phase: baseline`.

If publishing fails (sub-issues or blocking links unsupported, a CLI error, an auth problem), stop with the STOPPED report and quote the error. Do not ask for a workaround. Issues created before the failure stay recorded in the state, and running `/stories` again creates only what is missing.

## 5. Next

Tell the developer: "Next: /run-slice".
