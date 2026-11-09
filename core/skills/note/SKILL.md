---
name: note
description: Jots a line into the drift journal during or after a story, for observations that are not PR comments. Usage - /note <text>.
disable-model-invocation: true
---

Read `{{CORE}}/state-format.md` for the journal format. Arguments: $ARGUMENTS

1. Fail hard if `.sketch/` or `.sketch/state.md` does not exist ("No story in progress here").
2. If the arguments are empty, ask what to note.
3. Read the story number from `.sketch/state.md`.
4. Append exactly one line to `.sketch/journal.md` (create it with the header `# Drift journal` if missing):

```
<YYYY-MM-DD HH:MM>  S<story> -  NOTE  [me] <the developer's words, unchanged>
```

Use `date '+%Y-%m-%d %H:%M'` for the time. Do not discuss the note, rephrase it, or act on it. Reply with one short line confirming it was saved.
