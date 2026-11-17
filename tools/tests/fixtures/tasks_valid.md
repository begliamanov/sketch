# Tasks for story 2: Offline notes list

| id | title | blocked_by | scenarios |
|----|-------|------------|-----------|
| t-1 | Read notes from cache | none | 3 |
| t-2 | Sync on reconnect | t-1 | 3 |
| t-3 | Offline banner | t-1 | 2 |
| t-4 | Retry failed syncs | t-2, t-3 | 2 |

## t-1: Read notes from cache
Blocked by: none
Delivers: The notes list shows cached notes when the server is not reachable.
Acceptance criteria:
1. Cached notes are shown in the list.
2. An empty cache shows the empty state.
Test scenarios:
- shows cached notes
- shows the empty state for an empty cache
- orders notes by last edit
Terms: note, cache
Out of scope: syncing, the banner

## t-2: Sync on reconnect
Blocked by: t-1
Delivers: Edits made offline are sent when the connection returns.
Acceptance criteria:
1. Queued edits are sent on reconnect.
2. A server conflict keeps the server version and tells the user.
Test scenarios:
- sends queued edits on reconnect
- keeps the server version on conflict
- tells the user about a conflict
Terms: edit, sync (new)
Out of scope: retrying failures

## t-3: Offline banner
Blocked by: t-1
Delivers: A banner tells the user the list is offline.
Acceptance criteria:
1. The banner shows while offline and hides when online.
Test scenarios:
- shows the banner while offline
- hides the banner when online
Terms: banner
Out of scope: sync

## t-4: Retry failed syncs
Blocked by: t-2, t-3
Delivers: A failed sync is retried with a growing delay.
Acceptance criteria:
1. A failed sync is retried up to three times.
Test scenarios:
- retries a failed sync
- stops after three tries
Terms: retry
Out of scope: none
