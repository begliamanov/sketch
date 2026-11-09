# State, journal and stop-note formats

All three files live in `.sketch/` (local only).

## `.sketch/state.md`

Plain `key: value` lines, then one table. Keep it small and rewrite it in full after every completed step.

```
# Story state
story: 2
title: Offline notes list
story_issue: 120
feature_branch: feature/offline-notes
story_branch: story-2-offline-notes
phase: task-loop
last_step: t-3 review round 1 done
stopped: no
pr: none
pr_head_sha: none
story_rounds: 0/3
extra_skills: <paths the developer gave for this story, or none>

## Tasks
| id   | issue | title                  | blocked_by | status      | attempts | review_rounds |
|------|-------|------------------------|------------|-------------|----------|---------------|
| t-1 | 121   | Read notes from cache  | none       | done        | 1/3      | 1/2           |
| t-2 | 122   | Sync on reconnect      | t-1       | in-review   | 1/3      | 0/2           |
| t-3 | 123   | Offline banner         | t-1       | pending     | 0/3      | 0/2           |

## Flags
- t-4: <reason, quoted>
```

- `phase`: `sketch`, `tasks`, `baseline`, `task-loop`, `story-end`, `pr`, `waiting-review`, `done`.
- `status`: `pending`, `tests-red`, `green`, `in-review`, `done`, `flagged`.
- `stopped`: `no`, `failure: <one line>`, or `manual: <one line>` (including `manual: paused <time>`).
- `stop_after_task: yes` is added by `/stop` when the developer wants the current task finished first, and removed when the run stops.
- `pr_head_sha` is the story branch head when the PR was opened. The retro diffs it against the merged result to see what the developer changed by hand.
- Attempts and rounds are `used/cap`.

## `.sketch/journal.md`

Append-only. One line per event:

```
2026-11-12 10:41  S2 t-2  FLAG    test believed wrong: <detail>; re-check result: <result>
2026-11-12 11:05  S2 t-3  CAP     review cap hit (2/2), unresolved: <must-fix>
2026-11-12 11:30  S2 t-3  ASSUME  implementer used the existing NoteRepository (brief said new)
2026-11-12 13:02  S2 -     REVIEW  story-end: 1 must-fix, 3 nice-to-have
2026-11-13 09:10  S2 -     NOTE    [me] PR description was hard to scan
2026-11-13 09:25  S2 -     EDIT    [me] after PR: +2 commits, 3 files
2026-11-13 14:00  S2 -     CONTEXT [me] <what the developer said when resuming from /pause>
```

Types: `FLAG`, `CAP`, `ASSUME`, `REVIEW`, `NOTE`, `EDIT`, `CONTEXT`, `STOP`. Lines written by the developer carry `[me]`. Never rewrite or delete earlier lines.

## `.sketch/stop-note.md`

```
stopped: 2026-11-12 11:40
how: manual | failure | crash-found-on-resume
phase: task-loop
where: t-3, review round 1
task choice: finished | aborted (WIP committed)
reason: <the developer's words, or the failure report>
```

`/resume-story` reads this first.
