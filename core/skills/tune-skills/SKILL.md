---
name: tune-skills
description: One-time project setup, run by hand and only rarely. Scans the project, proposes which skills each agent role should read and which test commands to use, and writes .sketch/config.md after the developer confirms. Run it again to change the mapping.
disable-model-invocation: true
---

Read `{{CORE}}/conventions.md` and `{{CORE}}/orchestrator.md` first. Arguments: $ARGUMENTS (normally empty).

You are setting up one project. The developer is involved the whole way: this is a conversation, and nothing is written until they confirm.

## 1. Preconditions (fail hard)

If a check fails because something is missing, follow "Setup gaps" in the orchestrator rules (one list, offer to run the safe steps) before writing a STOPPED report.

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
- skills available: `.claude/skills/*/SKILL.md` in the project, `~/.claude/skills/*/SKILL.md`, and skills inside installed plugins. Read each one's name and description only, and note the absolute path of each `SKILL.md`; the config stores paths, not plugin names.

## 5. Propose, then confirm

Show a table of roles and the skills you suggest for each:

| Role | Suggested skills |
|---|---|
| task-writer | glossary and project conventions |
| test-writer | language, testing libraries, project conventions |
| implementer | language, framework (for example Android, Kotlin, Compose), project conventions |
| reviewer | same as the implementer |
| story-reviewer | same as the implementer |

The implementer and both reviewers share a list on purpose: they judge by the same rules.

Point out **gaps**: a significant dependency or framework with no matching skill ("you use Room, there is no skill for it"). Suggest what to do (point to an existing skill, or write a new one), but do not write skills here.

The developer may give paths to skills (local `SKILL.md` files, or skills for an external library). Accept them, check each path exists, and fail hard on a path that does not.

## 6. Test commands

Propose the test commands, the test file paths and how the results are written, all from the build files. Do not run the full suite now.
- `test_full`: the full unit-test command, for example `./gradlew testDebugUnitTest` (or `./gradlew test`, depending on the modules and variants).
- `test_task`: the form that runs one test class, with `{target}` as the placeholder, for example `./gradlew :app:testDebugUnitTest --tests "{target}"`.
- `test_format` and `test_results`: how the tests report their results, in a file, not on the console. `test_format` is `junit-xml` (Gradle writes it itself under `build/test-results/`; pytest with `--junitxml=<file>`; Vitest and Playwright with their `junit` reporter; Jest with the `jest-junit` package; SwiftPM with `swift test --parallel --xunit-output <file>`) or `xcresult-json` (Xcode: the command removes the old bundle, runs `xcodebuild test ... -resultBundlePath <x>.xcresult`, then writes `xcrun xcresulttool get test-results tests --path <x>.xcresult > <file>.json`, and ends with the exit code of `xcodebuild`, like `rm -rf <x>.xcresult && xcodebuild test ...; rc=$?; xcrun xcresulttool get test-results tests --path <x>.xcresult > <file>.json; exit $rc`. Removing the old bundle first means a stale one can never be read as a fresh result). Change `test_full` and `test_task` so that the command writes the file. `test_results` is a glob of the result files, relative to the project and ending in `.xml` or `.json`, like `app/build/test-results/**/*.xml`. The tool **deletes every file that matches it before each run**, so it must match result files and nothing else.
- If the runner can write neither format, offer to write a small reader instead: a `.py` file in `.sketch/formats/` (set `formats_dir: .sketch/formats`) that sets `FORMAT = "name"` and defines `read(text)` returning a list of `Case` (see `tools/sketch_tools/tests/model.py`), with a test file. Show it to the developer first. It is project code that the tools will run.
- With the developer's yes, run **one** small test once, the narrowest `test_task` form, to capture a real result file: `{{TOOLS}}/sketch-tests run --config .sketch/config.md --mode task --target <one test> --logs .sketch/logs`. Keep that file as the reader's sample. If it has no failing test, ask the developer to name one, or say what to break temporarily. Never invent a result.
- `test_paths`: globs that match every test file of the project, for example `**/src/test/**` or `Tests/**`. `*` stays inside one folder, `**` crosses folders. The loop uses them to check that the implementer never changes a test, so they must cover all test files and nothing else. Look at the test directories you found and show the globs you chose.

Say that these are proposals and that the first baseline check will exercise them. Never guess a command that the build files do not support. If there is no build tool you recognize, ask.

## 7. Write `.sketch/config.md`

After the developer confirms every part:

```
# sketch config
tracker: github | gitlab
tracker_cli: gh | glab
default_branch: <name>
test_full: <command>
test_task: <command with {target}>
test_paths: [<glob>, ...]
test_format: junit-xml | xcresult-json | <the name of your own reader>
test_results: <glob of the result files, ending in .xml or .json>
formats_dir: <folder of your own readers, only if you wrote some>

skills:
  common: [<absolute path to SKILL.md>, ...]
  task-writer: [<in addition to common>]
  test-writer: [<in addition to common>]
  implementer: [<in addition to common>]
  reviewer: [<in addition to common>]
  story-reviewer: [<in addition to common>]
```

Put the shared list under `common` and only the differences under each role.

Then check the file: `{{TOOLS}}/sketch-plan config-check --config .sketch/config.md` must print `ok`. It checks every key, the tracker and its CLI, the `{target}` placeholder, `test_paths`, the test format (and your own readers), `test_results`, each role's list, and that every skill path is absolute and exists. Fix what it reports with the developer before you finish.

## 8. Finish

Print a short summary: what was written, what is still a gap, and that the next step is `/sketch <idea>`.
