---
name: tune-skills
description: One-time project setup, run by hand and only rarely. Scans the project, proposes which skills each agent role should read and which test commands to use, and writes .sketch/config.md after the developer confirms. Run it again to change the mapping.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md` and `{{CORE}}/orchestrator.md` first. Arguments: $ARGUMENTS (normally empty).

You are setting up one project. The developer is involved the whole way: this is a conversation, and nothing is written until they confirm.

## 1. Preconditions (fail hard)

- The working directory is inside a git repository (`git rev-parse --show-toplevel`). Work from its root.
- The tracker CLI is installed and logged in: `gh` for GitHub, `glab` for GitLab (see step 3 for how to tell). Check `gh auth status` or `glab auth status`.

If any check fails, stop with the STOPPED report from the orchestrator rules.

## 2. Create the local folder

- Create `.sketch/`, `.sketch/logs/` and `.sketch/retro/`.
- Make sure `.sketch/` is in `.git/info/exclude`; append the line if it is not, and say that you did. This keeps it local without touching a shared `.gitignore`.

## 3. Existing config

If `.sketch/config.md` exists, show it and ask what the developer wants to change. Skip the scan unless they ask for it. Otherwise scan.

## 4. Scan

Look at the project, quickly:
- build files and modules (`settings.gradle(.kts)`, `build.gradle(.kts)`, version catalogs) and the main dependencies
- test directories and test libraries
- `CLAUDE.md`, `AGENTS.md`, `README`, `docs/`; whether `docs/GLOSSARY.md` and `CHANGELOG.md` exist
- the tracker: `git remote get-url origin` (github.com means GitHub and `gh`; a GitLab host means GitLab and `glab`; anything else: ask)
- the default branch
- skills available: `.claude/skills/*/SKILL.md` in the project, `~/.claude/skills/*/SKILL.md`, and skills inside installed plugins. Read each one's name and description only.

## 5. Propose, then confirm

Show a table of roles and the skills you suggest for each:

| Role | Suggested skills |
|---|---|
| story-writer | glossary and project conventions |
| test-writer | language, testing libraries, project conventions |
| implementer | language, framework (for example Android, Kotlin, Compose), project conventions |
| reviewer | same as the implementer |
| slice-reviewer | same as the implementer |

The implementer and both reviewers share a list on purpose: they judge by the same rules.

Point out **gaps**: a significant dependency or framework with no matching skill ("you use Room, there is no skill for it"). Suggest what to do (point to an existing skill, or write a new one), but do not write skills here.

The developer may give paths to skills (local `SKILL.md` files, or skills for an external library). Accept them, check each path exists, and fail hard on a path that does not.

## 6. Test commands

Propose two commands from the build files. Do not run the full suite now.
- `test_full`: the full unit-test command, for example `./gradlew testDebugUnitTest` (or `./gradlew test`, depending on the modules and variants).
- `test_story`: the form that runs one test class, with `{class}` as the placeholder, for example `./gradlew :app:testDebugUnitTest --tests "{class}"`.

Say that these are proposals and that the first baseline check will exercise them. Never guess a command that the build files do not support. If there is no build tool you recognize, ask.

## 7. Write `.sketch/config.md`

After the developer confirms every part:

```
# sketch config
tracker: github | gitlab
tracker_cli: gh | glab
default_branch: <name>
test_full: <command>
test_story: <command with {class}>

skills:
  common: [<name or absolute path to SKILL.md>, ...]
  story-writer: [<in addition to common>]
  test-writer: [<in addition to common>]
  implementer: [<in addition to common>]
  reviewer: [<in addition to common>]
  slice-reviewer: [<in addition to common>]
```

Put the shared list under `common` and only the differences under each role.

## 8. Finish

Print a short summary: what was written, what is still a gap, and that the next step is `/sketch <idea>`.
