# Sketch

You talk. Agents build. You merge.

Sketch turns a feature into **slices**: thin pieces that work for real through every layer, like a slice of cake (screen, logic, storage), each big enough to be worth your review. (*The Pragmatic Programmer* calls this a tracer bullet.) For each slice, agents write the tests first, implement, review their own work, and open a PR into your feature branch. Then they stop and wait for you. **No agent ever merges.**

> Status: designed and written, **not yet run end to end**. The Claude Code adapter installs cleanly. Everything else is marked *unverified* below.

---

## TL;DR

```bash
# 1. install (Claude Code)
adapters/claude-code/install.sh
# merge adapters/claude-code/settings.snippet.json into your settings by hand

# 2. in your project, on your own feature branch
/tune-skills            # once per project
/sketch offline notes   # talk until we agree on the next slice
/stories                # approve the story list -> issues are created
/run-slice              # go get coffee
# ... review + merge the PR ...
/sketch                 # next slice
```

Lost? `/how`.

---

## Setup

The system is plain Markdown in `core/`. A harness adapter copies it to where the harness looks and fills in one placeholder: `{{CORE}}` becomes the absolute path of `core/`.

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
- Models: only `slice-reviewer` is pinned (`opus`), in `adapters/claude-code/agents.list`. The rest inherit your session's model.
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

The Claude Code installer is about 80 lines of bash. A new adapter must:

1. Copy each `core/skills/<name>/SKILL.md` to wherever the harness reads slash commands. Replace `{{CORE}}` with the absolute path of `core/`. Keep `$ARGUMENTS`, or map it to the harness's argument syntax.
2. Copy each `core/agents/<name>.md` to wherever the harness defines subagents. Give each one the tools listed for it in `agents.list` (the reviewers are **read-only**).
3. Deny the dangerous commands in the harness's own permission system, not just in the prompts.
4. **Fail hard** if the harness can't do one of these. Don't turn subagents into "the main agent does it all": the loop depends on fresh contexts and an orchestrator that never sees test logs.

Quick and dirty way to read the files without an adapter:

```bash
sed "s|{{CORE}}|$PWD/core|g" core/skills/sketch/SKILL.md
```

---

## How the loop works

### The big picture

```
                 you                                    agents
 ┌───────────────────────────────┐
 │ create feature branch         │
 │ /tune-skills   (once)         │──► scans project, proposes skills + test commands
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ /sketch <idea>                │──► "exists already?" check, then a senior-dev
 │   explain, correct, approve   │    conversation → slice brief
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ /stories                      │──► story-writer: 3–6 stories, criteria, scenarios
 │   approve the list            │    → slice issue + story sub-issues
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ /run-slice                    │──► the loop below, unattended
 └──────────────┬────────────────┘
                ▼
 ┌───────────────────────────────┐
 │ review + merge the slice PR   │
 │ close the story issues        │
 │ /retro  (when suggested)      │
 └──────────────┬────────────────┘
                └──────► /sketch the next slice ... until the feature is done
                         then: feature branch → main, team reviews, /retro final
```

### Inside `/run-slice`

```
baseline:  tester runs full suite on untouched feature branch
           red or can't run? → STOP, that's your problem, not the loop's

branch:    slice-<n>-<slug> from the feature branch
           glossary proposal committed as  slice-<n>: glossary

per story, one at a time, in blocking order
 ┌──────────────────────────────────────────────────────────────┐
 │ test-writer   all tests for the story, verified RED  us-N: tests
 │      ▼                                                       │
 │ implementer   code until green (never touches tests) us-N: ...
 │      ▼                                                       │
 │ reviewer      read-only: criteria covered? tests untouched?  │
 │      │        changelog? scope? proof for every must-fix     │
 │      ├─ SATISFIED ───────────────────────────► done          │
 │      └─ CHANGES NEEDED → fresh implementer → fresh reviewer  │
 │                          (max 2 rounds, then FLAG and move on)
 └──────────────────────────────────────────────────────────────┘

slice end (max 3 rounds)
   tester (full suite) → slice-reviewer (whole diff) → fresh implementer → ...

pr-agent:  push slice branch, open PR into the feature branch
           flags first, then brief, stories, review result, assumptions
STOP. Wait for you.
```

### Rules you can count on

| Rule | Why |
|---|---|
| Agents never merge, force-push, push to main/feature, or close issues | You own what lands. Enforced by the deny list, not just prompts. |
| Tests are written before the code, and are a contract | The implementer can't make its own test pass by editing it. Only a fresh test-writer can change a test, and only on the acceptance criteria. |
| Fresh agent every round | No anchoring on the last attempt. |
| Round caps (3 / 2 / 2 / 3) | No grinding. Hit the cap → flag the story, carry on with the stories that don't depend on it. |
| **Fail hard** | Not logged in, VPN down, missing config, state doesn't match git → it stops and tells you. It never works around a problem. |
| The orchestrator never runs tests | It gets verdicts, not logs. Its context stays small. |
| One commit prefix per story (`us-3: ...`), no squashing | You can read the PR story by story. |
| Every story adds a CHANGELOG line ending `(#issue)` | Missing = must fix. |

Caps and rules: [`core/conventions.md`](core/conventions.md).

### What one slice gives you

```
Issue   #120  Slice 2: Offline notes list
          ├─ #121  us-1: Read notes from cache
          ├─ #122  us-2: Sync on reconnect      (blocked by #121)
          └─ #123  us-3: Offline banner         (blocked by #121)

Branch  slice-2-offline-notes  →  PR into feature/offline-notes

Commits slice-2: glossary
        us-1: tests
        us-1: read notes from local cache
        us-2: tests
        us-2: sync queued edits on reconnect
        us-2: handle conflict on server version   ← review fix
        us-3: tests
        ...
```

---

## Start using it

**Once per project**

1. Install the adapter for your harness (see Setup).
2. In the project: `/tune-skills`. It proposes which skills each role reads and your two test commands (`test_full`, `test_story`). You confirm. Result: `.sketch/config.md`.

**Per feature**

1. `git switch -c feature/<name>` yourself. Agents never create it.
2. `/sketch <idea>`. It checks whether something like it exists, then **stops and lets you explain**. Say as little or as much as you like: the less you say, the more it leads. Exits only when you approve its playback.
3. `/stories`. Approve, split, merge or reword the list. Issues are created only after you say yes.
4. `/run-slice`. Walk away.
5. Review the PR. **Flags are at the top.** Merge it, close the issues.
6. `/sketch` again. It shows a one-line summary of the last slice and suggests a `/retro` when it looks worth it.
7. Feature done: open the big PR to main yourself, let the team review, then `/retro final <PR#>`.

**While it runs**

| You want to | Type |
|---|---|
| step away and come back with new info | `/pause` |
| stop for today | `/stop` (asks: finish the current story first?) |
| continue after a stop, a crash or a closed laptop | `/resume-slice` (shows where it is, waits for your go) |
| remember something for the retro | `/note the PR description is hard to scan` |
| know what's going on | `/how` |

Hard interrupt: Esc, then `/pause` or `/stop`. Unfinished work is committed as `us-N: [wip] interrupted, not reviewed`, never thrown away.

---

## `/how`

Read-only helper. It never changes a file, runs tests, or touches git or the tracker.

**No argument: where am I, what's next.**

```
> /how

/tune-skills (once) -> /sketch -> /stories -> /run-slice -> you review + merge -> /sketch ...
                                                  |
            per story: test-writer -> implementer -> reviewer (loop)
            slice end: tester -> slice-reviewer -> fixes (loop) -> PR

You are here: slice 2 "Offline notes list", stopped (manual: "end of day"),
us-3 review round 1.
Next: /resume-slice

Ask me things like: /how does /pause work · /how why did it stop · /how can the implementer change tests
```

**With a question: answered from the docs and your `.sketch/` files, with the source named.**

```
> /how can the implementer change a test

No. If a test looks wrong, it stops and reports with evidence. A fresh test-writer
re-checks it against the acceptance criteria; only it may change the test, as
"us-N: fix test (rechecked)". If they disagree, you decide.
Source: core/agents/implementer.md, core/conventions.md (Tests)
```

If the answer isn't in the docs, it says so instead of guessing.

---

## Commands

| Command | When | Does |
|---|---|---|
| `/tune-skills` | once per project | role → skills mapping, test commands → `.sketch/config.md` |
| `/sketch <idea> [--skill path]` | start of every slice | agree the next slice, glossary proposals |
| `/stories` | after sketch | stories + issues, after your approval |
| `/run-slice` | after stories | the loop, ends with a PR |
| `/pause` · `/stop` · `/resume-slice` | any time | control a running slice |
| `/note <text>` | any time | one line in the drift journal |
| `/retro` · `/retro final <PR#>` | after a merge, when suggested | at most 3 proposals, as diffs. **Nothing is applied without your yes, item by item.** |
| `/how [question]` | lost | explains, read-only |

## Agents

| Agent | Writes code? | Job |
|---|---|---|
| story-writer | no | slices the brief, creates issues |
| test-writer | tests only | complete red test set per story; re-checks disputed tests |
| implementer | yes | makes tests green, fixes findings, never edits tests |
| reviewer | **read-only** | per story, against the criteria |
| slice-reviewer | **read-only** | whole slice diff, Opus |
| tester | no | runs commands, keeps raw logs, PASS / FAIL / CANNOT RUN |
| pr-agent | no | pushes the slice branch, opens the PR |
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
    slice-brief.md  stories.md  state.md  journal.md  stop-note.md
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
