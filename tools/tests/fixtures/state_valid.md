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
extra_skills: none
stop_after_task: no

## Tasks
| id  | issue | title                  | blocked_by | status      | attempts | review_rounds |
|-----|-------|------------------------|------------|-------------|----------|---------------|
| t-1 | 121   | Read notes from cache  | none       | done        | 1/3      | 1/2           |
| t-2 | 122   | Sync on reconnect      | t-1        | in-review   | 1/3      | 0/2           |
| t-3 | 123   | Offline banner         | t-1        | pending     | 0/3      | 0/2           |
| t-4 | 124   | Pull to refresh        | t-1        | flagged     | 3/3      | 0/2           |

## Flags
- t-4: tests keep failing, MissingBanner not found
