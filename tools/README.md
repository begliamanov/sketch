# Sketch tools

Deterministic tools for Sketch. Each tool owns one domain and does it exactly. The design and the
decisions behind it are in [`design/deterministic-tools.md`](../design/deterministic-tools.md).

## Rules

- Python 3.9 or newer, **standard library only** at runtime.
- A tool reads only its arguments, stdin and the files it is pointed at, and writes only to files
  it is pointed at. It never calls git, `gh`, the network or an LLM. (The one planned exception is
  `tests run`.) Paths are always passed in (`--journal`, `--state`), never searched for.
- Exit codes mean the same in every tool: `0` ok, `1` a check found problems or a file is damaged,
  `2` refused (a cap is reached, or the operation is not allowed), `3` bad arguments or unusable input.
- Tests come first. Write them, see them fail for the right reason, then implement. The tests are
  the spec.

## Layout

```
sketch_tools/
  core/        shared: exit codes, errors, the tool runner (cli.py), the only file writers (files.py)
  journal/     logic.py (pure) + cli.py (arguments and files)
  state/       schema.py (allowed values, one place) + logic.py (pure) + cli.py
  repo_check/  globs.py (test-path patterns) + logic.py (pure checks on piped git text) + cli.py
  guard/       shellparse.py (splits a command line into its simple commands) + logic.py (the rules) + cli.py (the hook)
  report/      schema.py (the validator) + roles.py (a schema and rules per agent role) + logic.py + cli.py
  pr/          logic.py (render the description, check the PR JSON and flags) + cli.py
  plan/        tasks_file.py, config_file.py (parsers) + graph.py + logic.py (pure checks, run order) + cli.py
tests/         unittest, with fixtures in tests/fixtures/
```

A tool is `logic.py` (pure functions, easy to test) plus `cli.py` (parse arguments, read and write
the one file). To add a subcommand: write its tests, add a function in `logic.py`, register it in
`build_tool()` in `cli.py`.

## Run

```bash
cd tools
python3 -m unittest discover -s tests -t .          # all tests
python3 -m sketch_tools.journal add NOTE S2 - "text" --me --journal path/to/journal.md
python3 -m sketch_tools.state check --state path/to/state.md
git log --format=%s main..HEAD | python3 -m sketch_tools.repo_check commit-prefix --task t-3
```

## Built so far

| Tool | Subcommands |
|---|---|
| `journal` | `add`, `me-lines`, `signals` |
| `state` | `new-story`, `task add`, `set`, `bump`, `check`, `flag add`, `gate`, `wip-message`, `reconcile` |
| `repo-check` | `commit-prefix`, `tests-unchanged`, `changelog`, `tree-clean` |
| `plan` | `tasks-check`, `tasks-order`, `config-check` |
| `pr` | `render-body`, `check-base`, `check-flags` |
| `report` | `submit`, `check`, `get` (one schema per agent role; reports are `<scope>-<role>-<run>.json`) |
| `guard` | `check-command` (a hook: reads the tool call as JSON, exit 2 blocks) |

The Claude Code installer (`adapters/claude-code/install.sh`) copies the package to `~/.claude/sketch/tools/` and creates a launcher per tool: `sketch-journal`, `sketch-state`, `sketch-repo-check`, `sketch-plan`, `sketch-pr`, `sketch-guard`, `sketch-report`. The docs in `core/` call them as `{{TOOLS}}/sketch-<tool> ...`; a test checks that every such call names a real command.
