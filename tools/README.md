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
```

## Built so far

| Tool | Subcommands |
|---|---|
| `journal` | `add` |
| `state` | `set`, `bump`, `check` |

Launchers (`sketch-journal`, `sketch-state`) and the adapter install step are not built yet.
