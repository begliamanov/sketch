---
name: note
description: Jots a line into the drift journal during or after a story, for observations that are not PR comments. Usage - /note <text>.
disable-model-invocation: true
---

Read `{{CORE}}/state-format.md` for the journal format. Arguments: $ARGUMENTS

1. Fail hard if `.sketch/` or `.sketch/state.md` does not exist ("No story in progress here").
2. If the arguments are empty, ask what to note.
3. Read the story number from `.sketch/state.md`.
4. Add the line with the tool, the developer's words unchanged (the tool adds the time, the `[me]` marker and the format, and creates the journal with its header if it is missing): `{{TOOLS}}/sketch-journal add NOTE S<story> - "<the developer's words>" --me --journal .sketch/journal.md`

Do not discuss the note, rephrase it, or act on it. If the tool exits with an error, say what it said and stop. Reply with one short line confirming it was saved.
