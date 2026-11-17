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
- `sketch/tools/`: a copy of `tools/sketch_tools`, `run.py`, and `bin/sketch-<tool>` launchers. `{{TOOLS}}` in the docs becomes the path of `bin/`. The installer fails if `python3` is older than 3.9, and it removes generated agents, skills and core files whose source no longer exists (for example an agent that was deleted from `core/agents/`).

Every generated file gets a marker line. `{{CORE}}` is replaced by the path of that copy (`~/.claude/sketch/core`), and `{{CORE_SOURCE}}` by the absolute path of the repo's `core/` (used by `/retro`, which edits the source). The script refuses to overwrite any file that does not carry its marker, and it fails if an agent in `core/agents/` is missing from `agents.list`. Edit `core/` and rerun; do not edit the generated files.

Start a new Claude Code session afterwards so the agents and skills are picked up.

## The guard hook

`settings.snippet.json` also adds a `PreToolUse` hook that runs `sketch-guard check-command` before every Bash command. It blocks `git merge`, `gh pr merge` and `glab mr merge`, merge and issue-close calls through `gh api` and `glab api`, force pushes (including `+branch`, `--force-with-lease`, `-f`), deleting or mirroring remote branches, pushes to `main`, `master` and the feature branch of the running story (read from `.sketch/state.md`), closing issues, and any `git push` that does not name its branch (`git push -u origin <story-branch>`), or that uses a variable instead. It sees through wrappers (`sudo`, `env`, `command`), `&&` and `;` chains, `$( )`, backticks, `bash -c` and `eval`, and heredocs fed to a shell. It fails closed: input it cannot read, a command it cannot parse and a bug in the guard itself all block. Its launcher turns every failure into a block (exit 2), including a wrong option in the hook line and a missing `python3`, because Claude Code lets a command run on any other failure.

It cannot see what a script, a variable or `python -c` does, so it lowers the risk, it is not a seal. The deny rules below stay as the first line.

## Permissions

The script does not touch `settings.json`. Merge `settings.snippet.json` into your user or project settings by hand:
- **allow**: the commands the loop needs, so it can run unattended, including the tool launchers
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
- the hook format in `settings.snippet.json` (`hooks.PreToolUse`, `matcher`, `type: command`) and that exit code 2 blocks the command and shows stderr to the agent: both are written from memory. Test it: ask Claude to run `git push origin main` and check that it is blocked
- the `glab mr view --output json` flag used by the PR check
- that the permission rule for the tool launchers matches, including when they sit behind a pipe (`git status --porcelain | .../sketch-repo-check tree-clean`)
