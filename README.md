# Sketch

You talk. Agents build. You merge.

Sketch turns a feature into **stories**: thin end-to-end pieces that work for real through every layer, like a slice of cake (screen, logic, storage), each big enough to be worth your review. (*The Pragmatic Programmer* calls this a tracer bullet.) For each story, agents write the tests first, implement, review their own work, and open a PR into your feature branch. Then they stop and wait for you. **No agent ever merges.**

> Status: designed and written, **not yet run end to end**. The Claude Code adapter installs cleanly. Everything else is marked *unverified* below.

---

## TL;DR

```bash
# 1. install (Claude Code)
adapters/claude-code/install.sh
# merge adapters/claude-code/settings.snippet.json into your settings by hand

# 2. in your project
/tune-skills            # once per project
/sketch offline notes   # talk until we agree on the next story, then go get coffee:
                        # it splits it into tasks, creates the issues, runs the loop, opens the PR
# ... review + merge the PR ...
/sketch                 # next story
```

Lost? `/how`.

---

## Setup

The system is plain Markdown in `core/`. A harness adapter copies it to where the harness looks and fills in two placeholders: `{{CORE}}` becomes the path of a filled-in copy of `core/` (so files that point to each other resolve), and `{{CORE_SOURCE}}` the path of the repo's `core/` (used by `/retro`, which edits the source).

| Harness | Adapter | Status |
|---|---|---|
| Claude Code | `adapters/claude-code/` | Installs. Loop not run yet. |
| Pi | none yet | Unverified |
| Cline | none yet | Unverified |
| GitHub Copilot (VS Code) | none yet | Unverified |
| Anything else | none yet | See "Writing an adapter" |

### Requirements (every harness)

- git, plus `gh` (GitHub) or `glab` (GitLab), installed **and logged in**
- a build tool with a test command (built around Gradle; others should work)
- a harness that can run **subagents**: separate agents, each with its own fresh context. The loop depends on this. Without it, there is no adapter.

### Claude Code

```bash
adapters/claude-code/install.sh              # install or update
adapters/claude-code/install.sh uninstall    # remove only what it generated
```

- Writes `~/.claude/agents/*.md` and `~/.claude/skills/*/SKILL.md` (or under `$CLAUDE_HOME`).
- Won't overwrite a file it didn't generate. Edit `core/` and rerun; never edit the generated files.
- **Permissions:** merge `adapters/claude-code/settings.snippet.json` into your settings by hand. It allows what the loop needs and denies merges, closing issues, force-pushes and pushes to main.
- Models: only `story-reviewer` is pinned (`opus`), in `adapters/claude-code/agents.list`. The rest inherit your session's model.
- Start a new session afterwards.

Details and known limits: [`adapters/claude-code/README.md`](adapters/claude-code/README.md).

### Pi *(unverified)*

No adapter yet. What a Pi adapter would map, from what Pi documents (check against your version):

| Sketch | Pi |
|---|---|
| `core/skills/<name>/SKILL.md` (commands) | prompt templates (`~/.pi/agent/prompts/<name>.md`) or skills (`~/.pi/agent/skills/`) |
| `core/agents/*.md` (subagents) | Pi has no built-in subagents. You need an extension or package that adds them |
| `settings.snippet.json` deny list | needs an extension that blocks commands. Prompts alone are not a guardrail |

Open question from the design notes: does the pi-pstack package already provide subagents we can reuse?

### Cline *(unverified)*

| Sketch | Cline |
|---|---|
| commands | workflows: `.clinerules/workflows/<name>.md`, run as `/<name>.md` |
| `conventions.md`, `orchestrator.md` | rules: `.clinerules/` |
| agents | check whether your Cline version has subagents. If not, it cannot run the loop |

### GitHub Copilot in VS Code *(unverified)*

| Sketch | Copilot |
|---|---|
| commands | prompt files: `.github/prompts/<name>.prompt.md`, run as `/<name>` in chat |
| `conventions.md` | `.github/copilot-instructions.md` or `*.instructions.md` |
| agents | custom agents (`.github/agents/*.agent.md`), started through the subagent tool, if your version has it |
| deny list | terminal command auto-approve / deny settings |

### Writing an adapter

The Claude Code installer is about 110 lines of bash. A new adapter must:

1. Write a copy of all of `core/` with `{{CORE}}` replaced by that copy's path and `{{CORE_SOURCE}}` by the repo's `core/`. Then copy each `core/skills/<name>/SKILL.md`, with the same replacements, to wherever the harness reads slash commands. Keep `$ARGUMENTS`, or map it to the harness's argument syntax.
2. Copy each `core/agents/<name>.md` to wherever the harness defines subagents. Give each one the tools listed for it in `agents.list` (the reviewers are **read-only**).
3. Deny the dangerous commands in the harness's own permission system, not just in the prompts.
4. **Fail hard** if the harness can't do one of these. Don't turn subagents into "the main agent does it all": the loop depends on fresh contexts and an orchestrator that never sees test logs.

Quick and dirty way to read the files without an adapter:

```bash
sed -e "s|{{CORE_SOURCE}}|$PWD/core|g" -e "s|{{CORE}}|$PWD/core|g" core/skills/sketch/SKILL.md
```

---

## How the loop works

### The big picture

```
                 you                                    agents
 ┌───────────────────────────────┐
 │ /tune-skills   (once)         │──► scans project, proposes skills + test commands
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ /sketch <idea>                │──► "exists already?" check (offers to create
 │   explain, correct, approve   │    the feature branch), then a senior-dev
 │   (your only approval)        │    conversation → story brief
 └──────────────┬────────────────┘
                ▼  on its own, no more questions
 ┌───────────────────────────────┐
 │ tasks                         │──► task-writer: 3–6 tasks, criteria, scenarios
 │                               │    → story issue + task sub-issues
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ story loop                    │──► the loop below, unattended
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ review + merge the story PR   │
 │ close the task issues         │
 │ /retro  (when suggested)      │
 └──────────────┬────────────────┘
                └──────► /sketch the next story ... until the feature is done
                         then: feature branch → main, team reviews, /retro final
```

### Inside the story loop (`/run-story`)

```
baseline:  tester runs full suite on untouched feature branch
           red or can't run? → STOP, that's your problem, not the loop's

branch:    story-<n>-<slug> from the feature branch
           glossary proposal committed as  story-<n>: glossary

per task, one at a time, in blocking order
 ┌──────────────────────────────────────────────────────────────┐
 │ test-writer   all tests for the task, verified RED  t-N: tests
 │      ▼                                                       │
 │ implementer   code until green (never touches tests) t-N: ...
 │      ▼                                                       │
 │ reviewer      read-only: criteria covered? tests untouched?  │
 │      │        changelog? scope? proof for every must-fix     │
 │      ├─ SATISFIED ───────────────────────────► done          │
 │      └─ CHANGES NEEDED → fresh implementer → fresh reviewer  │
 │                          (max 2 rounds, then FLAG and move on)
 └──────────────────────────────────────────────────────────────┘

story end (max 3 rounds)
   tester (full suite) → story-reviewer (whole diff) → fresh implementer → ...

pr-agent:  push story branch, open PR into the feature branch
           ~20 lines: flags first, tasks, test + review result,
           manual checks, top nice-to-haves, what differs from the plan
STOP. Wait for you.
```

### Rules you can count on

| Rule | Why |
|---|---|
| Agents never merge, force-push, push to main/feature, or close issues | You own what lands. Enforced by the deny list, not just prompts. |
| Tests are written before the code, and are a contract | The implementer can't make its own test pass by editing it. Only a fresh test-writer can change a test, and only on the acceptance criteria. |
| Fresh agent every round | No anchoring on the last attempt. |
| Round caps (3 / 2 / 2 / 3) | No grinding. Hit the cap → flag the task, carry on with the tasks that don't depend on it. |
| **Fail hard** | Not logged in, VPN down, missing config, state doesn't match git → it stops and tells you. It never works around a problem. |
| The orchestrator never runs tests | It gets verdicts, not logs. Its context stays small. |
| One commit prefix per task (`t-3: ...`), no squashing | You can read the PR task by task. |
| Every task adds a CHANGELOG line ending `(#issue)` | Missing = must fix. |

Caps and rules: [`core/conventions.md`](core/conventions.md).

### What one story gives you

```
Issue   #120  Story 2: Offline notes list
          ├─ #121  t-1: Read notes from cache
          ├─ #122  t-2: Sync on reconnect      (blocked by #121)
          └─ #123  t-3: Offline banner         (blocked by #121)

Branch  story-2-offline-notes  →  PR into feature/offline-notes

Commits story-2: glossary
        t-1: tests
        t-1: read notes from local cache
        t-2: tests
        t-2: sync queued edits on reconnect
        t-2: handle conflict on server version   ← review fix
        t-3: tests
        ...
```

---

## Start using it

**Once per project**

1. Install the adapter for your harness (see Setup).
2. In the project: `/tune-skills`. It proposes which skills each role reads and your two test commands (`test_full`, `test_task`). You confirm. Result: `.sketch/config.md`.

**Per feature**

1. `/sketch <idea>`. On the default branch it offers to create and push a feature branch (you agree to the name), or you create it yourself first. It checks whether something like the idea exists, then **stops and lets you explain**. Say as little or as much as you like: the less you say, the more it leads. It exits only when you approve its playback.
2. That approval is the only one per story. The orchestrator then splits the story into tasks, creates the issues, runs the loop and opens the PR on its own. It shows you the task list as it goes but does not wait. Walk away.
3. Review the PR. **Flags are at the top.** Merge it, close the issues.
4. `/sketch` again. It shows a one-line summary of the last story and suggests a `/retro` when it looks worth it.
5. Feature done: open the big PR to main yourself, let the team review, then `/retro final <PR#>`.

**While it runs**

| You want to | Type |
|---|---|
| step away and come back with new info | `/pause` |
| stop for today | `/stop` (asks: finish the current task first?) |
| continue after a stop, a crash or a closed laptop | `/resume-story` (shows where it is, waits for your go) |
| remember something for the retro | `/note the PR description is hard to scan` |
| know what's going on | `/how` |

Hard interrupt: Esc, then `/pause` or `/stop`. Unfinished work is committed as `t-N: [wip] interrupted, not reviewed`, never thrown away.

---

## `/how`

Read-only helper. It never changes a file, runs tests, or touches git or the tracker.

**No argument: where am I, what's next.**

```
> /how

/tune-skills (once) -> /sketch -> (on its own: tasks + issues -> story loop -> PR) -> you review + merge -> /sketch ...
                                                        |
                  per task: test-writer -> implementer -> reviewer (loop)
                  story end: tester -> story-reviewer -> fixes (loop) -> PR

You are here: story 2 "Offline notes list", stopped (manual: "end of day"),
t-3 review round 1.
Next: /resume-story

Ask me things like: /how does /pause work · /how why did it stop · /how can the implementer change tests
```

**With a question: answered from the docs and your `.sketch/` files, with the source named.**

```
> /how can the implementer change a test

No. If a test looks wrong, it stops and reports with evidence. A fresh test-writer
re-checks it against the acceptance criteria; only it may change the test, as
"t-N: fix test (rechecked)". If they disagree, you decide.
Source: core/agents/implementer.md, core/conventions.md (Tests)
```

If the answer isn't in the docs, it says so instead of guessing.

---

## Commands

| Command | When | Does |
|---|---|---|
| `/tune-skills` | once per project | role → skills mapping, test commands → `.sketch/config.md` |
| `/sketch <idea> [--skill path]` | start of every story | agree the next story, glossary proposals; on your yes, runs `/tasks` and `/run-story` itself |
| `/tasks` | run by `/sketch`; by hand only to pick up a cut-off run | tasks + issues (asks for approval when run by hand) |
| `/run-story` | run by `/sketch`; by hand only to pick up a cut-off run | the loop, ends with a PR |
| `/pause` · `/stop` · `/resume-story` | any time | control a running story |
| `/note <text>` | any time | one line in the drift journal |
| `/retro` · `/retro final <PR#>` | after a merge, when suggested | at most 3 proposals, as diffs. **Nothing is applied without your yes, item by item.** |
| `/how [question]` | lost | explains, read-only |

## Agents

| Agent | Writes code? | Job |
|---|---|---|
| task-writer | no | splits the brief into tasks, creates issues |
| test-writer | tests only | complete red test set per task; re-checks disputed tests |
| implementer | yes | makes tests green, fixes findings, never edits tests |
| reviewer | **read-only** | per task, against the criteria |
| story-reviewer | **read-only** | whole story diff, Opus |
| tester | no | runs commands, keeps raw logs, PASS / FAIL / CANNOT RUN |
| pr-agent | no | pushes the story branch, opens the PR |
| drift-notetaker | journal only | appends events, no opinions |
| retro-agent | `.sketch/retro/` only | drift analysis, proposals |

## Where things live

```
your project/
  docs/GLOSSARY.md, docs/adr/   tracked: the team sees them in the PR
  CHANGELOG.md                  tracked
  .sketch/                      local only (.git/info/exclude)
    config.md                   from /tune-skills
    initial-sketch.md           frozen feature picture; deleted after the final retro, if you say so
    story-brief.md  tasks.md  state.md  journal.md  stop-note.md
    logs/  retro/

sketch/                         this repo
  core/                         the system, plain Markdown, harness-neutral
    conventions.md              rules every agent reads first
    orchestrator.md             how the main session behaves
    state-format.md             state, journal, stop-note formats
    agents/  skills/
  adapters/claude-code/         installer, agent tool/model list, permission snippet
  docs/design-notes.md          why it is the way it is
```

## Known gaps

- Never run end to end. First-run checklist: [`adapters/claude-code/README.md`](adapters/claude-code/README.md#not-verified).
- `gh` sub-issues and blocking links: untested. `glab`: tested by hand.
- No adapters for Pi, Cline or Copilot yet.
- Why each decision was made: [`docs/design-notes.md`](docs/design-notes.md).
