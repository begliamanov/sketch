# State, journal and stop-note formats

All three files live in `.sketch/` (local only).

## `.sketch/state.md`

Plain `key: value` lines, then one table. Keep it small and rewrite it in full after every completed step.

```
# Slice state
slice: 2
title: Offline notes list
slice_issue: 120
feature_branch: feature/offline-notes
slice_branch: slice-2-offline-notes
phase: story-loop
last_step: us-3 review round 1 done
stopped: no
pr: none
pr_head_sha: none
slice_rounds: 0/3
extra_skills: <paths the developer gave for this slice, or none>

## Stories
| id   | issue | title                  | blocked_by | status      | attempts | review_rounds |
|------|-------|------------------------|------------|-------------|----------|---------------|
| us-1 | 121   | Read notes from cache  | none       | done        | 1/3      | 1/2           |
| us-2 | 122   | Sync on reconnect      | us-1       | in-review   | 1/3      | 0/2           |
| us-3 | 123   | Offline banner         | us-1       | pending     | 0/3      | 0/2           |

## Flags
- us-4: <reason, quoted>
```

- `phase`: `sketch`, `stories`, `baseline`, `story-loop`, `slice-end`, `pr`, `waiting-review`, `done`.
- `status`: `pending`, `tests-red`, `green`, `in-review`, `done`, `flagged`.
- `stopped`: `no`, `failure: <one line>`, or `manual: <one line>` (including `manual: paused <time>`).
- `stop_after_story: yes` is added by `/stop` when the developer wants the current story finished first, and removed when the run stops.
- `pr_head_sha` is the slice branch head when the PR was opened. The retro diffs it against the merged result to see what the developer changed by hand.
- Attempts and rounds are `used/cap`.

## `.sketch/journal.md`

Append-only. One line per event:

```
2026-11-12 10:41  S2 us-2  FLAG    test believed wrong: <detail>; re-check result: <result>
2026-11-12 11:05  S2 us-3  CAP     review cap hit (2/2), unresolved: <must-fix>
2026-11-12 11:30  S2 us-3  ASSUME  implementer used the existing NoteRepository (brief said new)
2026-11-12 13:02  S2 -     REVIEW  slice-end: 1 must-fix, 3 nice-to-have
2026-11-13 09:10  S2 -     NOTE    [me] PR description was hard to scan
2026-11-13 09:25  S2 -     EDIT    [me] after PR: +2 commits, 3 files
2026-11-13 14:00  S2 -     CONTEXT [me] <what the developer said when resuming from /pause>
```

Types: `FLAG`, `CAP`, `ASSUME`, `REVIEW`, `NOTE`, `EDIT`, `CONTEXT`, `STOP`. Lines written by the developer carry `[me]`. Never rewrite or delete earlier lines.

## `.sketch/stop-note.md`

```
stopped: 2026-11-12 11:40
how: manual | failure | crash-found-on-resume
phase: story-loop
where: us-3, review round 1
story choice: finished | aborted (WIP committed)
reason: <the developer's words, or the failure report>
```

`/resume-slice` reads this first.
