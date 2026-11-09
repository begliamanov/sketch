# Claude Code adapter

`core/` is plain Markdown. This adapter turns it into Claude Code agents and skills.

## Install

```
adapters/claude-code/install.sh              # install or update
adapters/claude-code/install.sh uninstall    # remove what it generated
```

It writes into `~/.claude` (or `$CLAUDE_HOME`):
- `agents/<name>.md` for each line of `agents.list`, with `tools` and `model` added to the frontmatter
- `skills/<name>/SKILL.md` for each folder in `core/skills/`
- `sketch/core/`: a filled-in copy of all of `core/`. Skills and agents point to each other through `{{CORE}}/...`, so the files they open must have real paths too.

Every generated file gets a marker line. `{{CORE}}` is replaced by the path of that copy (`~/.claude/sketch/core`), and `{{CORE_SOURCE}}` by the absolute path of the repo's `core/` (used by `/retro`, which edits the source). The script refuses to overwrite any file that does not carry its marker, and it fails if an agent in `core/agents/` is missing from `agents.list`. Edit `core/` and rerun; do not edit the generated files.

Start a new Claude Code session afterwards so the agents and skills are picked up.

## Permissions

The script does not touch `settings.json`. Merge `settings.snippet.json` into your user or project settings by hand:
- **allow**: the commands the loop needs, so it can run unattended
- **deny**: merging, closing issues, force-pushes, pushes to main or master

Known limits of that file:
- Pushing to the **feature branch** cannot be denied generically, because its name differs per feature. The PR agent is told to push only `git push -u origin <story-branch>`, and the orchestrator checks the PR afterwards.
- `gh api` and `glab api` can do anything, including merging, so they are **not** in the allow list. The task-writer may need one for sub-issues or blocking links; you will be asked, and you can approve it case by case.
- The permission pattern syntax (`:*` prefix match, and `*` in `story-*`) is written from memory. Check it against your Claude Code version.

## Models

`agents.list` pins only `story-reviewer` (to `opus`). Everything else uses the session's model (`inherit`). Change a line and rerun the script.

## Not verified

None of this has been run. Things to check on the first real use:
- a skill name colliding with a built-in command (`/stop`, `/pause`, `/note`, `/retro`, `/how`); if one does, rename the folder in `core/skills/`
- how a command typed while the orchestrator is working is delivered: it is assumed to be seen at the next step boundary, with Esc as the hard interrupt
- that subagents see `{{CORE}}`-expanded absolute paths and can read them
- the `gh` and `glab` flags for sub-issues, child items and blocking links
