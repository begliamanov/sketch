# Sketch conventions

Every agent and command in this system reads this file first. It is plain Markdown on purpose: the same text should work in any harness.

## What this system does

Work is delivered as **slices**: thin pieces of a feature that work for real through every layer (like a slice of cake), each big enough to be worth a human review. The idea is the tracer bullet from *The Pragmatic Programmer*. One slice is one issue, one branch and one PR. Inside a slice, work is split into **stories** (`us-1`, `us-2`, ...), each one a sub-issue and a run of commits.

The human (the developer) creates the feature branch and merges every slice PR. Agents never merge.

## Fail hard

Stop and tell the developer when they must be involved. Do not work around it, substitute another tool, or continue best-effort.

**Stop and tell the developer when:**
- an agreed tool cannot operate at all: not installed, not authenticated, feature unsupported, permission denied
- config or a skill path is missing
- state does not match git, the tracker or the PR
- a failure needs something outside the code: credentials, VPN, network, access rights, machine setup
- a decision only the developer can make: product choice, scope change, anything destructive or expensive to reverse
- you cannot tell whether a failure is the code or the environment (treat it as the environment)

**Handle yourself, inside the loop:**
- a test fails, code does not compile, a build fails because of the code
- review findings
- the same failure repeating is not yours to grind on: follow the round caps, then flag the story and continue with stories that do not depend on it

An error report says: what failed, where, what was expected, what the developer can do. Never "completed with warnings". Never edit build files, remove dependencies or try another route to get past a block.

## Round caps (starting values)

| Loop | Cap |
|---|---|
| Making a story's tests pass | 3 attempts |
| Per-story review and fix | 2 rounds |
| Writing the red tests | 2 attempts |
| Slice-end tester, review and fix | 3 rounds |

Stop early if the same failure appears twice in a row. A flagged story does not stop stories that do not depend on it. Flags go at the top of the slice PR.

## Git and commits

- The developer creates the feature branch. Agents create slice branches from it and push only those.
- Never merge. Never push to the feature branch or main. Never force-push. Never close issues (comment "done in PR #N" instead).
- Every commit message starts with its story: `us-3: ...`. A fix spanning several stories uses `slice-2: ...`.
- Do not squash. Review fixes are their own commits.
- Interrupted work is committed on the slice branch as `us-3: [wip] interrupted, not reviewed`.
- Story commit order: `us-N: tests`, then implementation, then any fixes.

## Changelog

Every story adds one line to `CHANGELOG.md` under Unreleased, ending with the story's issue number:

```
- Add streaming CSV export endpoint (#123)
```

A missing or malformed entry is a must-fix finding.

## Tests

- Unit tests only, for now.
- The complete test set for a story is written before any implementation, from the story's acceptance criteria and test scenario list.
- Tests are readable as documentation: names in glossary terms, grouped by acceptance criterion.
- New tests must fail for the right reason (behavior missing, not a typo or broken import) before implementation starts.
- Tests are a contract. The implementer never edits, deletes, skips or weakens a test. If a test looks wrong, stop and report with evidence. A fresh test-writer re-checks it against the criteria, and only it may change the test.
- Per story, run only that story's tests. The full suite runs at the slice end, by the tester.
- Commands come from `.sketch/config.md`. Never guess a command.

## Reviewing

- Reviewers are read-only. They never edit code.
- Severity: **must fix** needs evidence (a command and its output, or the exact criterion it breaks). **Nice to have** never triggers another round; it goes into the slice PR description.
- A reviewer is satisfied when: every acceptance criterion maps to a test that would really fail if the feature broke, test files are unchanged since the red-test commit, no must-fix remains, and the CHANGELOG entry is correct.
- Fix rounds use a fresh implementer and a fresh reviewer.

## Language

`docs/GLOSSARY.md` is the shared language. Use its terms in code, tests, issues and commit messages. A new or ambiguous term goes into a proposed glossary change, which travels in the slice PR.

## Files

```
docs/                tracked, the team sees it
  GLOSSARY.md
  adr/
.sketch/             local only, excluded via .git/info/exclude
  config.md          role -> skills, test commands (from /tune-skills)
  initial-sketch.md  frozen until the retro; the developer is asked to delete it after
  slice-brief.md    the current slice
  state.md           where the loop is
  journal.md         append-only events
  stop-note.md       why and where it stopped
  logs/              raw test logs from the tester
  retro/             drift blocks and proposal decisions
CHANGELOG.md
```

`state.md` is written after every completed step, with the round and attempt counters, so a resume never resets a cap.

## Reports

Every agent ends its work with a short report: what it did, assumptions it made, doubts it has, and the skills it applied (so a skipped skill is visible). Quote findings verbatim; do not paraphrase them.

## Retro rule

Nothing changes in these agents, skills or conventions without the developer's explicit approval, item by item. A retro only proposes, as diffs, with the evidence it came from.
