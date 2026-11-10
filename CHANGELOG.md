# Changelog

Sketch follows [semantic versioning](https://semver.org). The current version is in `VERSION`.

## Unreleased

## 0.1.0

Run end to end in Claude Code. Adds a Pi adapter.

- Pi adapter: a Pi package (`package.json` at the repo root) with the `/sketch-sync` extension (`adapters/pi/extensions/sketch-sync.ts`). `/sketch-sync` copies the skills and agents into `~/.pi/agent/` and a filled-in copy of `core/` into `~/.pi/agent/sketch/core/`, then you run `/reload`. `/sketch-sync remove` deletes exactly the files it wrote. It never overwrites a file it did not create. Tools and models per agent are set in `adapters/pi/agents.list`.
- On Pi, commands are typed as `/skill:<name>`. The sync rewrites the command names in the copied text to match.
- The `sketch` skill description is quoted, so its frontmatter parses as YAML.
- Renamed agent `reviewer` to `task-reviewer`, so it can't clash with other harnesses' built-in `reviewer` agents. Claude Code users: delete the stale `~/.claude/agents/reviewer.md`, then rerun `install.sh`.

## 0.0.1

First versioned release. Designed and written, not yet run end to end.

- Core agents and skills, with stories split into tasks
- `/sketch` chains into the loop on its own: tasks, issues, story run, PR
- Claude Code adapter (`adapters/claude-code/install.sh`)
