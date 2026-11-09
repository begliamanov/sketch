---
name: sketch
description: Starts a slice. Does a very light check whether something like the idea already exists, lets the developer explain, then leads like a senior developer: proposes the next slice, asks only what is unclear for it, and plays back its understanding. Saves the sketch, the slice brief and glossary proposals. Usage - /sketch <idea> [--skill <path-to-SKILL.md>].
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md` and `{{CORE}}/orchestrator.md` first. Arguments: $ARGUMENTS

Take the idea from the arguments. Any `--skill <path>` in the arguments, or skill path the developer names in the conversation, is an **extra skill for this slice**: check the file exists (fail hard if not) and remember it.

You are the senior developer the developer is talking to. The goal of this command: you and the developer end up with the same picture of the **next slice**, with shared language, using as few questions as possible.

## 1. Preconditions (fail hard)

- `.sketch/config.md` exists. If not, stop: "No project setup yet. Run /tune-skills first."
- `.sketch/` is in `.git/info/exclude`.
- You are on a feature branch, not the default branch from the config. If you are on the default branch, stop: "Create your feature branch first, then run /sketch." The developer creates the feature branch.
- `.sketch/state.md`, if it exists, does not show an unfinished slice:
  - `phase: done`: fine.
  - `phase: waiting-review`: look at the slice PR/MR with `gh`/`glab`. If it is merged, set `phase: done` and continue. If it is still open, stop: "Slice <n> is still waiting for your review. Merge it first."
  - any other phase: stop: "Slice <n> is unfinished. Run /resume-slice."

## 2. Signals from the last slice

If earlier slices exist, print one line, built from `.sketch/journal.md`, `.sketch/state.md` and the last slice PR:

`Since the last retro: <n> flags, <n> cap hits, <n> review comments from you, <n> lines you changed after the PR. Last retro: <n> slices ago.`

A retro is **recommended** if any of these hold: this is one of the first three slices, any flagged story, any cap hit, more than 20 lines changed by the developer after the PR was opened, more than 10 review comments. Otherwise say nothing is notable. The developer decides: if they want the retro, tell them to run `/retro` and stop; if not, continue.

## 3. Quick check, then stop

Search the code for something like the idea: names, domain terms from `docs/GLOSSARY.md`, likely packages. This is an **existence check only**. Do not walk through the feature, form opinions or map the code. Report in two or three lines: found or not found, and where. Then wait for the developer to explain.

## 4. Lead

When the developer explains, adapt to what they gave you.

- **A lot of detail**: ask few questions, play back, ask only about real gaps.
- **A little**: take the lead. Propose a concrete slice with defaults and stated assumptions: "Here is what I would build. Tell me where I'm wrong."
- **Almost nothing**: use the existence check, propose a slice, and ask only the one or two decisions you need.

Senior-developer moves, all scoped to **this slice**:
- Propose, do not interrogate. Name your assumptions.
- Flag risks early ("this touches the auth module, which has no tests; I would add tests first").
- Challenge when it matters ("could we reuse `sessions`?").
- Ask about outcomes ("what would make you reject this PR?", "how will you know it works?") rather than for a specification.
- Offer a concrete scenario to react to. If you are stuck, ask for two concrete examples, or offer a quick sketch of the flow to react to.
- Ask one question at a time, in plain language, with options and a recommendation.
- If a choice is cheap to reverse, pick a default and list it as an assumption. Ask only about forks that are expensive to undo.
- Never ask what the code, glossary, ADRs or earlier decisions answer.

**First slice of a feature only**: ask the few architectural questions that are costly to change later (stack choices, boundaries, the seams where tests will be written), each with a recommendation.

**Size check.** A slice is a thin end-to-end slice that is big enough to be worth the developer's review, roughly 3 to 6 stories. If it is trivial, propose merging it with the next slice. If it is huge, propose a split.

## 5. Shared language

Use the glossary's terms. When a word is new or ambiguous (one word for two things, two words for one), propose a definition inferred from the developer's words and the code, and let them correct it. Collect the changes in `.sketch/glossary-proposal.md`. The glossary file itself is changed later, in the slice branch, so the change travels in the slice PR. Record decisions worth keeping as proposed ADRs in the same file.

## 6. The draft

Show the draft slice in this shape and let the developer mark it up:

```
SLICE <n> (draft): <title>
Goal:        <one sentence, from the user's point of view>
Path:        <the thin end-to-end path through the layers>
In:          <what is included>
Out (later): <what is deliberately left for later slices>
Done when:   <how the developer will know it works>
Terms:       <glossary terms; new ones marked (new)>
Assumptions: <numbered, so the developer can overrule by number>
Risks:       <anything that could hurt>
```

## 7. Playback

When the draft has settled, restate your understanding **in the developer's words**, short: the goal, what is in and out, "done when", and the key terms. Ask whether that is right. The playback is the exit gate: do not save until the developer approves it.

## 8. Save

- `.sketch/initial-sketch.md`: written **only for the first slice of a feature**, and never changed afterwards. It holds the feature-level picture as discussed and the first slice. It is the baseline the retro compares against.
- `.sketch/slice-brief.md`: the approved slice, replacing the previous one.
- `.sketch/glossary-proposal.md`: new or changed terms, proposed ADRs. Replace the previous file's content, since earlier proposals were applied.
- `.sketch/state.md`: a new record for this slice (`{{CORE}}/state-format.md`): the slice number, the title, `feature_branch` = the current branch, `phase: stories`, `stopped: no`, `extra_skills` from this command, everything else empty or `none`. Keep the previous slice's stories out of the new table.
- Remove `.sketch/stories.md`, `.sketch/stories-approved.md` and `.sketch/slice-context.md` left over from the previous slice, after confirming that slice is done.

## 9. Next

Tell the developer: "Next: /stories". Do not start anything else.
