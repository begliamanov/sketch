# Custom orchestration: my flow vs Pocock skills vs pstack

Renamed since these notes were written: the project tracer-loop is now **Sketch**, and a tracer (bullet) is now a **slice** (`/run-slice`, `/resume-slice`, `slice-reviewer`, `slice-N:` prefixes). The notes below keep the old words.

Status: notes only, nothing built yet. Target harnesses: Claude Code (personal), Pi (work).

## My flow

1. **Interview**: me + orchestrator (main session) talk until it understands. Output: `spec.md`.
2. **User stories**: subagent reads `spec.md`, makes one-task stories (splits big ones), creates each as a GitHub/GitLab issue.
3. **Implementation loop**, per story:
   1. write all tests for the story
   2. implement to pass them
   3. review the code
   4. fix review comments
   5. mark ready for dev review, move on. No agent merges. Don't wait for me.
4. I merge tickets one by one and review again.
5. Team reviews.
6. Merge.
7. Retro: suggest better ways of working based on all review comments.
8. I approve or reject the retro.

## Issues spotted in my flow

1. Tests written before code by an agent with only the story: wrong reading of the story means green tests prove nothing. Need explicit acceptance criteria; reviewer checks tests against them.
2. Stacked, unmerged PRs: dependent stories force stacked branches and rebasing after review changes. Story-writer must record dependencies.
3. No path for fixing review comments from phases 4-5. Need a "fix review comments" entry point.
4. Same-model reviewer tends to approve. Needs a different prompt, a checklist, spec + criteria.
5. Interview quality caps everything. Add approval gates: spec, and story breakdown before issues are created.
6. No stop condition: cap fix rounds, then flag the story.
7. Retro can overfit and bloat prompts. Require evidence per suggestion; prefer removing or tightening rules.
8. Portability: the more it relies on Claude Code's Agent tool, the more Pi adapter work. Pi capabilities unverified.

## Phase-by-phase comparison

| Phase | My flow | Pocock | pstack |
|---|---|---|---|
| 1. Interview | Talk until understood, output `spec.md` | `grilling` interviews; `to-spec` writes spec, confirms test seams | Weak: `in-your-own-words`, `sharpen`; avoids asking the human |
| 2. Stories | Subagent splits spec into one-task issues | `to-tickets`: vertical slices, blocking edges, user approves breakdown | None ("best spec is code"); `multi-phase-plan` closest |
| 3.1 Tests | All tests first | `tdd`, tests only at agreed seams | `tdd`, `test-behavior-not-implementation` |
| 3.2 Implement | Make tests pass | `tdd` loop | `poteto-agent` workers with shared principles |
| 3.3 Review | Reviewer agent | `code-review`: standards + spec in parallel | `interrogate` (multi-model, keeps only proven findings), `no-comments`, `blast-radius` |
| 3.4 Fix comments | Fix reviewer comments | none | `babysit` playbook (threads, conflicts, CI; triage fix/dismiss/ask) |
| 3.5 Handoff | Ready for review, never merge | none | `autopilot-stack` (stops before merge, one owner per PR) |
| 4-6 Merge/review | Me, then team | Me | `shipping` lands PRs: leave out |
| 7. Retro | Suggest improvements from review comments | none | `reflect`, `correct`, `encode-lessons-in-structure` |
| 8. Approve retro | Me | none | no human gate: leave out |

## Cross-cutting

| | My flow | Pocock | pstack |
|---|---|---|---|
| Human involvement | High (interview, review, retro approval) | High, confirmation gates | Low, autonomous unless irreversible |
| Planning | Spec then stories | Spec then tickets | Against it |
| Story dependencies | Not designed | Explicit blocking edges | Stacked PRs |
| Evidence of done | Not designed | Tests + spec review | Central: every claim needs evidence or label |
| Subagents | Role per phase | Parallel subagents in `code-review` | One worker type, shared preamble, fresh agent per round |
| Invocation | Skill per phase, chained by orchestrator | User-invoked slash skills | One router, `/poteto-mode` |
| Pi portability | Goal | Unverified | Official repo has only a Claude Code adapter; a third-party Pi package exists (unread) |

## Takeaways

- Pocock fits the front half (phases 1-2, test-first part of 3).
- pstack fits the back half (review, fix comments, handoff, retro). Its style is autonomous, so adapt and add my human gates.
- Neither provides the loop itself: orchestrator, round cap, no-merge guardrail, resume from state.
- pstack ideas to borrow: shared preamble all subagents read first; fresh subagent per fix round; evidence rule for "done"; retro that puts fixes into lint/test/script over more prose; adversarial reviewer (`interrogate`).
- Guardrail: deny `gh pr merge` / `glab mr merge` in permissions, not just in prompts.
- Design principle: portable core in plain Markdown (skills, role prompts, workflow); thin per-harness adapters.

## Caveats on sources

- pstack: read README, `poteto-mode/SKILL.md`, `poteto-agent.md`, `docs/harness/claude-code.md`, `plugin.json`. Playbooks and individual skill files (`interrogate`, `correct`, `babysit`, `autopilot-stack`) were NOT read; their descriptions come from the README.
- Pocock: read `to-spec`, `to-tickets`, `wayfinder`, `code-review`, `tdd` (partially) from the locally installed plugin (v1.3.1).
- Pi: nothing verified about how it loads skills/agents.

## Open questions

1. GitHub, GitLab, or both?
2. Sequential loop or parallel worktrees?
3. Max review/fix rounds before flagging a story?
4. How does Pi handle subagents and skills? Read the pi.dev pstack package: https://pi.dev/packages/@zenspc/pi-pstack
5. Does Pi load Pocock's skills?

## Interview phase: extra requirements (added later)

**Naming: the "interview" phase is now called "Sketch"** (e.g. `/sketch`). Wherever these notes say interview, read Sketch.

- Goal: a shared end result between me and the orchestrator. It must really understand me (verified, not assumed).
- Shared language (DDD ubiquitous language): interview also probes terms; output is `spec.md` + glossary updates (`GLOSSARY.md`, ADRs). Team reviews glossary changes in PRs. Pocock's `domain-modeling` skill covers this (not read in full).
- `grilling` / `grill-me` is too boring and tiring. Need lower-effort interview approaches (see options discussed: draft-and-correct, playback, concrete examples, multiple-choice, brain dump + gap analysis, prototype, role-play, walk-through, questionnaire, mode switch).
- Open: one repo or several (glossary per bounded context)? Who approves glossary changes? Team in the interview or only reviewing afterwards?

## Tracer-bullet model (added later)

- Not one-shot feature implementation. Work in tracer bullets (Pragmatic Programmer): thin end-to-end production-quality slices, built early, fed back into the next steps. Pocock's `to-tickets` uses the same vertical-slice idea.
- Interview is iterative: interviewer asks only until it understands enough for the NEXT tracer, states its understanding (goal, in/out, success check), I confirm. After each tracer, short re-interview from the new state. `spec.md` + glossary are living docs.
- Two-level review/merge:
  - Level 1: each tracer bullet phase = PR into a long-lived **feature branch**. I review and merge these.
  - Level 2: when the feature is done, one big PR feature branch -> main. The team only sees this.
- Loop must pause after each tracer for my review before planning the next one.
- Decisions: tracer must be decently big, worth my review (not a trivial "connect to DB" slice). I create the feature branch; agents create tracer branches/PRs. I own keeping the final PR to the team from being huge. A few up-front architectural questions are fine. "Interview" is being renamed (see below).
- Open: does tracer N+1 start only after I merge N (leaning yes)? One PR per tracer with a commit/issue per story (leaning yes)?

## Sketch phase design (draft)

Flow: Read (recon) -> report findings and STOP -> I explain in detail -> Draft next tracer -> Correct (questions only on forks, with options + recommendation) -> Playback (my words, I approve) -> Save -> hand brief to story-writer.

Decisions (these override the earlier flow line above where they differ):
- `/sketch implement this`: step 1 is a VERY LIGHT existence check only: does something like this already exist in the code? Code is the source of truth. It does NOT walk through the whole feature. It gives a very short brief (found / not found, where) and waits for me to explain in detail.
- After my details, it asks questions only if something is unclear for the specific tracer being sketched, not for the whole feature.
- Persona: the orchestrator is a SENIOR DEV I talk to. I may give thin explanations (I'm human), so it must be proactive: the less I say, the more it leads. It proposes a concrete tracer with defaults and stated assumptions, asks sharp questions, challenges and flags risks, instead of waiting for detail. Still scoped to the current tracer, and still options + recommendation.
- `docs/` is NOT gitignored (glossary, ADRs live there, tracked, team-visible). The sketch spec does NOT go in `docs/`. Location for spec: TBD (proposal: `.sketch/` at repo root, kept out of git via `.git/info/exclude`).
- Examples/prototypes are optional moves when the orchestrator is stuck.
- Quick vs full mode: not decided (recon-first may make it unnecessary).
- Lifecycle of the sketch spec: kept until the retro so the retro can measure drift from the INITIAL sketch. Initial sketch stays frozen; later deviations go in a separate drift log. After the retro it is no longer a source of truth unless explicitly marked. Retro ends by prompting me to delete it.
- Rules: look before asking; draft before questions; options + recommendation; tracer big enough to be worth review (propose merging if trivial, splitting if huge); new/ambiguous terms go to glossary draft; first tracer asks the few architectural questions; stop when understood (playback is the exit gate); I can say "fewer/more questions", "just decide".

Settled:
- Sketch spec lives in `.sketch/` at repo root, kept out of git via `.git/info/exclude` (local only, no shared .gitignore change). Holds: frozen initial sketch, drift log, current tracer brief. CORRECTION: only the spec (frozen initial sketch) is deleted, on prompt, after the retro. `.sketch/` itself stays, with the drift journal, retro logs and config, until I decide to delete them (I may reconsider deleting the folder at all).
- Drift is recorded by a SUBAGENT (not the orchestrator).

Open (come back later):
- Drift log format.
- When the drift subagent runs (end of each tracer? after my merge?) and what it compares (tracer brief vs what was actually built / the merged diff).

## Story-writer and TDD (draft, in progress)

- Story-writer (subagent) turns the approved tracer brief into issues: slice, order with blocking links, mandatory acceptance criteria in glossary terms, show list for approval, then publish. Based on Pocock's `to-tickets` (not yet verified against my tracker). Stories stay within ONE tracer.
- TDD approach (my requirement, starting from the story phase): NOT bit-by-bit red-green-refactor. The COMPLETE test set for one user story is written BEFORE implementation. Tests double as documentation/guide for the implementer and later readers.
- Note: Pocock's `tdd` skill is a one-test-at-a-time loop, so it does not match this; use only its test-quality guidance (behavior through public interfaces, seams).
- Decisions: story issues include a list of test scenarios (names only, no code); test-writer writes the full tests from them. I do NOT review tests or story PRs. I review only when the whole tracer bullet is finished (one tracer PR into the feature branch). So the quality gate between stories is the reviewer agent (checks code AND tests against acceptance criteria). Likely consequence: one branch/PR per tracer, one commit (or issue) per story.
- Test rules: complete test set per story before implementation; verified red for the right reason; implementer must not edit/delete tests (flags instead); tests readable as documentation, in glossary terms.
- Open: tracker (GitHub/GitLab/both), tracer-as-parent-issue vs label, approval of the story list every time or first only, story size.

## Story-writer decisions (latest)

- Trackers: GitHub for personal, GitLab for work (story-writer must support `gh` and `glab`). Native sub-issue / child-item / blocking support per tracker is UNVERIFIED: RESOLVED: `glab` already tested by me on the work laptop and works; `gh` assumed to work (NOT verified, not installed on this machine). No plain-text fallback: if sub-issues or blocking links don't work, the system fails hard (see fail-hard principle).
- Mapping: tracer bullet = one issue (holds the brief); user stories = sub-issues / child items of it; tracer = one PR (into the feature branch); story = one commit.
- Gotcha: `Closes #N` only auto-closes on merge to the default branch, so tracer PRs into the feature branch won't close issues. DECIDED: orchestrator comments "done in PR #X" on each story; I close issues manually.
- Round caps (starting values, tune in retro): implement-to-green 3 attempts; review/fix per story 2 rounds; tracer-end review/fix loop 3 rounds (changed from 2: the final loop also covers regressions); red-test writing 2 attempts; stop early if the same failure repeats; a flagged story does not stop independent stories; flagged items go at the top of the tracer PR description.
- DECIDED: story list shown to me for approval before issues are created, every time (revisit after retro). Story = one observable behavior, ~3-8 test scenarios, fits one agent context (split if title needs "and" or >8 scenarios; merge if trivial). Tracer = ~3-6 stories, big enough to be worth my review.
- Story-writer design is complete except tracker capability testing (sub-issues/child items/blocking on GitHub and GitLab).
- Roles in the loop: reviewer ONLY reviews (read-only, never edits code). Implementer does all fixes. Loop: reviewer reviews -> implementer fixes -> reviewer re-reviews, until the reviewer is satisfied or the round cap is hit (then flag the story).
- Reviewer "satisfied" = (1) all acceptance criteria met and covered by tests, (2) tests untouched since the red-test commit, (3) no unresolved "must fix" findings. "Nice to have" notes go to the tracer PR description and do not trigger another round. Fix rounds use a fresh implementer and a fresh reviewer.
- Test-writer (subagent per story): reads existing code/test style first; writes the COMPLETE test file from the scenario list (extra scenarios marked as additions); readable, glossary terms, grouped by criterion; runs suite and verifies every new test fails for the right reason; commits tests alone; no production code beyond minimal stubs.
- Implementer (fresh subagent per round): runs tests (red), writes code until green with suite still green, stays in scope, NEVER edits/deletes/skips/weakens tests (flags instead), reports assumptions and doubts.
- Commits: kept separate, NOT squashed. Every commit message is prefixed with the story id (`us-1: ...`, `us-2: ...`). No limit on commits per story (review fixes are commits too). Tracer PR = many commits.
- Tests: unit tests only for now (no e2e). No project-wide test command / verification skill needed for now.
- Wrong-test handling: implementer flags -> orchestrator asks a fresh test-writer to re-check against the acceptance criteria; only if it agrees does the test-writer fix the test (never the implementer). I am involved only if they disagree.
- Reviewer design (agreed): read-only tools (read, search, run commands). Checks: (1) suite passes, (2) test files unchanged vs the `us-N: tests` commit, (3) every acceptance criterion maps to a test that would really fail if the feature broke, (4) correctness beyond tests, proven by a command where possible, (5) scope, (6) fit (glossary, conventions, duplication), (7) CHANGELOG entry present and well formed. It lists ALL must-fix findings in one pass (does not stop at the first failing check), to save rounds. Severity: must fix vs nice to have (nice to have goes to the tracer PR description, never triggers a round). Every must-fix needs evidence. Output format: Verdict SATISFIED | CHANGES NEEDED, must fix list (what, file:line, evidence), nice to have, criteria coverage list (SATISFIED is invalid without it). Reads story and tests before code. Gets the implementer's report (assumptions/doubts) but reviews the code first. No rewrites of working code just by preference.
- CHANGELOG is MANDATORY: every story adds an entry ending with the issue number in the form `(#123)`, e.g. `- Add streaming CSV export endpoint (#123)`. Implementer writes it; reviewer checks it (missing or malformed = must fix). Assumed: issue number is the story's issue; file is CHANGELOG.md under Unreleased. Confirm.
- Orchestrator design (draft, agreed points): state kept in `.sketch/state.md` (per-story status, rounds, flags, branch, PR), checked against git and tracker on resume. Loop: create tracer branch from up-to-date feature branch -> next story whose blockers are done -> test-writer -> implementer -> reviewer/implementer loop -> update state, flag on cap, continue with independent stories -> tracer-end review (open) -> tracer PR into feature branch -> stop and wait for me (then `/retro`).
- DECIDED: stories run SEQUENTIALLY. Pushing the tracer branch and opening the tracer PR (with generated description: brief, story checklist with issue links, flags, assumptions, nice-to-haves) is done by a dedicated PR SUBAGENT (no longer "cheap": model not downgraded, same as the rest of the loop), not the orchestrator. Description built from a template filled from `.sketch/state.md` and the tracker; flags quoted verbatim; orchestrator verifies after (PR exists, base is the feature branch, every flagged story appears). Permissions: pre-allow what the loop needs (tests, git commit, `gh`/`glab`) in project settings so it runs unattended; deny `gh pr merge` / `glab mr merge`, pushes to feature branch and main, force-pushes, and closing issues. The PR subagent may push only tracer branches.
- OPEN ITEM 1 DECIDED (regression tests): the FULL test suite runs only at the tracer end (it is expensive), not per story. Per story, the implementer and the per-story reviewer run only that story's own tests (this narrows reviewer check (1) "suite passes" to the story's tests). Tracer end: TESTER agent runs the full suite BEFORE the tracer-end reviewer. The reviewer reviews even if tests are red and adds the failing tests as must-fix findings; a fresh implementer fixes; tester reruns; reviewer reviews again; loop. Reviewer is satisfied only when the tester reports PASS and nothing must-fix remains.
- NEW AGENT `tester`: the orchestrator does NOT run tests (orchestrator will likely be an expensive model). Tester runs the project's test command (and the baseline check before a tracer), writes the full raw log to a file, and reports PASS / FAIL (failing test names verbatim) / CANNOT RUN (environment: credentials, VPN, network, tool missing -> fail hard, stop and tell me). Never edits code. Implementer and test-writer still run tests themselves while working.
- A later story legitimately contradicting an earlier story's test: still flagged for me (old test is a contract; implementer never edits it). Not yet re-confirmed since the full suite now runs only at the tracer end.
- Needed: the test command (e.g. gradle task) must be known; assumed to be recorded in `.sketch/config.md` by `/tune-skills`, fail hard if missing (supersedes "no test command needed for now"). CLARIFIED: it is just the gradle command(s), e.g. `./gradlew test` or `./gradlew testDebugUnitTest` for the full unit suite, plus a form for running one story's tests (e.g. `--tests <class>`). `/tune-skills` proposes it by scanning the project; I confirm it once; no guessing at run time.
- OPEN ITEM 2 (resume). DECIDED by me: it must survive both kinds of stop (stopped by a failure of any kind: crash, closed terminal, full context, machine or network dropping; or stopped by me manually) and gaps of ANY length (minutes to days). Details are decided in the commands bullet below; the rest of this bullet is an older proposal, superseded where it differs (stash replaced by a [wip] commit; always confirm on return): one mechanism for both crash/closed laptop and deliberate stop. `.sketch/state.md` is written after every completed step (tracer, branch, per-story status, round and attempt counters, flags, last completed step, commit SHAs, issue ids, PR). A resume command (name TBD; NOT `/resume`, built-in) reads it, reconciles with git, tracker and PR, and fails hard on any mismatch. Re-entry = restart the interrupted step with a fresh agent (agents are stateless). Counters are kept so resuming never resets round caps. Dirty working tree from a killed agent: stop and ask me (keep or discard), never discard silently. Issue and PR creation are idempotent (check what exists before creating). Never auto-continue silently: report where it stopped, then ask.
- DECIDED commands for manual control: `/stop` asks me whether the current story should finish. If no: write notes (state + stop note) and stop. If yes: continue until the current story finishes, then stop. `/pause` pauses until I come back, then asks me for context and carries on. Resume command name DECIDED: `/resume-tracer` (`/pickup` rejected as not descriptive; `/resume` is a built-in). DECIDED details: (1) `/pause` and `/stop`-with-"no" ABORT the running agent immediately. (2) Half-finished work is committed on the tracer branch with a message marking it interrupted, e.g. `us-3: [wip] interrupted, not reviewed` (instead of the stash proposal); never on the feature branch or main. (3) On return, `/resume-tracer` gives me the context of where it is (stop note, state, what it found when reconciling with git/tracker/PR) and waits for my explicit go before continuing (always confirm). (4) My `/pause` context is logged in the journal as a `[me]` entry and added to the briefs of the remaining agents for the whole tracer. Still to settle: reconciliation table (state vs git/tracker/PR) not yet confirmed; how a restarted agent treats the [wip] commit (proposal: told it is incomplete, may build on or redo it, later commits fix it up).
- DECIDED commit prefixes: a fix that belongs to one story keeps that story's `us-N:` prefix; a fix that spans stories uses `tracer-N:`. Open items 1 (regression), 2 (resume, stop, pause) and 3 (who fixes final-review comments: fresh implementer in the tester/reviewer loop, max 3 rounds) are closed. Diagram page updated to match.
- Retro (per-tracer `/retro` and final retro): deferred, to be revisited at the end of the design.

## Drift log and /retro (OPEN, come back later)

- The drift agent observes DURING the agentic loop: whenever something flag-worthy appears in the review phase (flagged story, test believed wrong, broken assumption, cap hit, spec mismatch found by reviewer), it records it in `.sketch/drift-log.md`.
- After I merge a tracer PR I call `/retro`. The agent walks through the drift log with me and asks whether I want to add anything from my point of view. What I say is documented in the log.
- This replaces the earlier idea of running the drift subagent at the start of the next `/sketch`.
- Entry format proposal (not agreed): per tracer, planned vs built; drift items tagged ADDED / DROPPED / CHANGED / TERMS, each with where it was found (code, agent review, me); signals (rounds used, flagged stories, my review comment count).
- Open: is this per-tracer `/retro` the same as the final retro (after team review), or a lighter one with the final retro still at the end? Format is not final.

## Retro design (agreed so far)

- Two levels: light `/retro` after each tracer merge; deeper final retro after team review (adds team comments, all flags, a few numbers across tracers).
- Options chosen to combine: A "Find Bugs Once" (each problem found by me/team -> earliest automated layer where it should have been caught: reviewer checklist, test/lint, skill rule, glossary/ADR, sketch question; output = table problem -> earliest layer -> proposed change), B drift calibration (planned vs built, what /sketch should have asked, tracer size), C blameless root cause on flags/cap hits, D my point of view (Start/Stop/Continue). Source of ideas: Pragmatic Programmer ("Find Bugs Once", "Fix the problem, not the blame", tracer bullets/iterate estimates, project glossary, automate) and pstack `correct`/`encode-lessons-in-structure`.
- Guardrails: max ~3 proposals per retro; each cites evidence; prefer deleting/tightening rules; rejected proposals recorded; a few numbers only (rounds per story, flagged stories, comments from me and from the team per tracer).
- DECIDED: the retro agent NEVER applies findings on its own. Proposals are written up as diffs; nothing changes without my approval, item by item.
- Baseline for comparison: the frozen initial sketch (whole feature) and each tracer brief (per tracer) vs what was actually built/merged.
- Frequency (per my concern that a retro after every tracer becomes a bottleneck): note-taking stays automatic for every tracer, but the retro CONVERSATION is not mandatory per tracer. Proposal: first ~3 tracers retro each time (calibration); afterwards on demand, with the next `/sketch` start showing a one-line signal summary (flags, cap hits, comments, my post-PR edits) and suggesting a retro only when signals cross thresholds; final retro at the end of the feature is always done. CONFIRMED. Default thresholds for suggesting a retro (tune later, by the retro itself): any flagged story, any cap hit, any non-trivial post-PR edit by me, or more than ~10 review comments. The signal line also says how many tracers ago the last retro was. Skipped retros are not lost: the next one covers every tracer since the last.
- DECIDED: include both `/note` (appends a timestamped line with tracer id to the drift log; no agent reasoning) and post-PR edit tracking (PR subagent records the branch head SHA when it opens the PR in `.sketch/state.md`; the retro diffs that against the merged result, summarizing by size/file, not line by line). Open detail: how I merge tracer PRs (merge commit / squash / rebase) affects how reliably my own commits can be seen; the SHA comparison still works in all cases.
- DECIDED drift log format: two layers. (1) JOURNAL, append-only, one line per event written as work happens by agents and `/note` (timestamp, tracer, story, type FLAG/CAP/ASSUME/REVIEW/NOTE/EDIT, text; `[me]` marks my own notes). (2) STRUCTURED BLOCK per tracer, written at `/retro` from the journal + my PR comments + my post-PR edits: Planned / Built / Drift items tagged ADDED, DROPPED, CHANGED, TERMS, each with who found it and when (sketch, implementation, agent review, me in review, after PR) / Signals (stories, flags, cap hits, my comments, my post-PR edits). The "found by / when found" fields are the core of the retro. A table (TSV) view for counts across tracers can be generated later for the final retro.
- Notes are taken DURING the review phases (automatic from agents, manual from me) into the drift log in `.sketch/`. Details in discussion; open: `/note` command and tracking my own commits made after the PR was opened.

## Project skills and setup (agreed so far)

- Skills are per project. Roles map to skills (story-writer, test-writer, implementer, per-story reviewer, tracer-end reviewer). Implementer and both reviewers share a list so they judge by the same rules.
- Mapping is stored in a small project config file (plain text: role -> skill names), in `.sketch/config.md` (untracked via `.git/info/exclude`). Since `.sketch/` persists, only spec files are ever deleted by the post-retro prompt, never the config.
- One-time per project SETUP flow is its OWN command, run manually by me, very rarely (name: `/tune-skills`; avoids the built-in `/config` and `/init`). `/sketch` does NOT do setup: it only checks that `.sketch/config.md` exists and, if not, prompts me to run `/tune-skills`. Human + agent: agent scans the project (available skills, build files, dependencies, test setup, docs/conventions), proposes the role -> skills mapping and points out gaps; I confirm or edit; it writes the config. Revisit by re-running setup, or when a retro proposes a change (never applied without my approval).
- In `/sketch` I can pass a path to a specific skill (external library skill or a new skill) for that tracer; it is added to the tracer brief. Default: applies to all coding roles; can be restricted. At the retro, offer to make it permanent.
- Agents list which skills they applied in their reports (so a skipped skill is visible).

## System-wide principle: FAIL HARD (Pragmatic Programmer: "Crash Early", dead programs tell no lies)

- If a tool or precondition does not work, the system stops and tells me. It does NOT work around it, substitute something else, or continue "best effort". This applies to the whole system, not just trackers.
- Applies to: missing/unauthenticated `gh`/`glab`, unsupported tracker features (sub-issues, blocking links), missing `.sketch/config.md` or a skill path that doesn't exist, missing test command, wrong branch or missing feature branch, state file inconsistent with git/tracker, a permission denial (do not try another route), failed push/PR creation, failed post-PR checks (wrong base, flagged story missing from description: report, don't auto-fix).
- Error message must say: what failed, where, what was expected, what I can do. Never "completed with warnings".
- Partial progress is recorded in `.sketch/state.md` (e.g. issues already created) so a rerun resumes; that is resuming, not a workaround.
- CLARIFIED SCOPE: fail hard only on things where I must be involved. Failures of the WORK are normal and handled inside the loop (failing tests, compile errors, gradle build failing because of the code): the agents fix them; repeated same failure -> existing no-progress/round-cap rules -> flag the story, independent stories continue. Fail hard (stop, tell me) when: an agreed tool cannot operate at all (not installed, not authenticated, unsupported feature, permission denied), config/skill path missing, environment or state inconsistent, or a decision only I can make (product choice, destructive/irreversible action, scope change, expensive-to-reverse fork). When unsure whether a failure is work or environment, treat it as environment and ask me.
- DECIDED check: before a tracer starts, run the project's test/build command once on the untouched branch; if it is already red or cannot run, fail hard (environment/state, not the loop's job).
- Gradle failures can be environmental (missing credentials, VPN not connected, repository unreachable, auth/token errors, network). These need me: stop and tell me, with the actual error. Same rule for any failure whose fix involves something outside the code (credentials, network/VPN, accounts, access rights, machine setup): agents must not retry blindly, edit build files to bypass it, or work around it.

## Tracer-end review: pstack `interrogate` idea (OPEN, come back later)

- Read `skills/interrogate/SKILL.md` (raw GitHub). Core rule: a finding survives only if a run proves it.
- Process: frame intent (restate it) -> several adversary agents, each in its own worktree, brief "Break this change", must report title + exact command + output + required output -> orchestrator reruns each command and keeps only findings that reproduce and break the intent -> report (intent, verified findings, dropped counts). Never applies fixes. Excludes style/naming/structure/future-risk.
- Unknown: number/models of adversaries (defined in the `arena` skill, not read).
- Candidate use: one pass at the END of a tracer, before the tracer PR to the feature branch; the tracer brief from Sketch is the "intent". Implementer fixes verified findings (with round cap). Cheaper variant: 1-2 adversary subagents + rerun verification.
- Concerns: cost, worktree/multi-agent support in Pi, doesn't catch wrong-but-working design.
- Status: kept open, decision deferred.
- UPDATE: I do NOT want the lite/single-adversary version. I want an ARENA-LIKE review with 2 good agents. Read pstack `arena` SKILL.md: 6 phases (Frame with 3-6 criteria rubric, Fan out N parallel candidates each with own worktree and a rationale, Cross-judge by a readonly judge of a different model family, Pick a base against the rubric, Graft the best parts of losers, Verify). Number of runners and models come from a user config line (`arena runners`), default two (an Opus-class and a Grok-class model); no cost cap in the file.
- LATEST (replaces the adapted design below): tracer-end review is a DIFF review of the whole tracer (not a run-based break-it review). Two strong agents review the full tracer diff independently, then challenge each other's reviews and try to reach ONE decision. Max 3 tries (exchange rounds); if no agreement, stop. Details (what happens to disputed items, who moderates, re-check after fixes) are in the design discussion; open points: handling of unresolved disagreement, whether fixes get a re-check.
- DECIDED LATER: NO OpenAI. Both tracer-end reviewers are Claude agents (normal subagents, ideally two different Claude models for diversity). The PR description states which models reviewed; the "competitor's model" wording and the CLI/API bridge, vendor and work-repo notes below no longer apply. Debate relayed by the orchestrator, continuing the same two subagents between rounds.
- FINAL DECISION (overrides everything above in this section): the two-agent arena/debate review and the interrogate idea are DROPPED. The tracer-end review is a single Opus reviewer, reviewing the whole tracer diff, using the skills defined for the project (Android, Kotlin, Compose, etc.). It follows the same reviewer rules as the per-story reviewer (read-only, evidence for must-fix, must-fix vs nice-to-have). Agreed must-fix items go to a fresh implementer; nice-to-have and unresolved doubts go in the tracer PR description, which states the reviewing model. Open: which skills are loaded, and whether the per-story reviewer also loads the project skills.
- (Dropped) Doubt raised: is the two-agent debate review worth its cost? Treat it as an EXPERIMENT. Track per tracer (in the retro): must-fix items found by the final review that the per-story reviewers missed, how many I accepted vs rejected, rounds used, cost. Consider dropping or shrinking it (e.g. independent reviews + 1 challenge round, or only for big tracers) if the numbers are weak.
- (Superseded) Tracer-end reviewers: two different vendors, one Anthropic model and one OpenAI model. The tracer PR description must state who reviewed, and that the second reviewer is a competitor's model (e.g. "Reviewer A: Anthropic <model>; Reviewer B: OpenAI <model>, a competitor's model"), written by the orchestrator from the actual configuration.
- Feasibility notes: Claude Code subagents run Claude models only, so the OpenAI reviewer must be invoked through a CLI/API bridge (e.g. Codex CLI) via the orchestrator; session continuity between debate rounds is unverified. Work repos: check policy before sending diffs to a second vendor. Debate verdicts should be structured (item id + AGREE/DISAGREE/REFINE) so the orchestrator checks convergence mechanically.
- Open: how the OpenAI agent is invoked; re-check after fixes; does "3 tries" count the independent round.
- (Superseded) Adapted design for tracer-end review (draft): Frame (intent from tracer brief + rubric) -> 2 independent reviewers in parallel, different lenses, each must prove findings with commands -> orchestrator reruns/verifies every finding (no third judge agent) -> merge deduplicated findings -> fresh implementer fixes must-fix (cap 2 rounds) -> re-review fixes -> report goes into tracer PR description.

## Sources

- https://github.com/cursor/plugins/tree/main/pstack
- https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md
- https://github.com/cursor/plugins/blob/main/pstack/agents/poteto-agent.md
- https://github.com/cursor/plugins/blob/main/pstack/docs/harness/claude-code.md
- https://flaviocopes.com/pstack
- https://pi.dev/packages/@zenspc/pi-pstack

## Next step when we resume

Agree the skeleton: list of skills and agents, and which come from where (own / Pocock / pstack idea). Then start with phase 1.

## Build log

The design above was implemented in `core/` and `adapters/claude-code/` without being run. Differences and additions made while building are listed in the top-level `README.md` under "Added while building". Verify the items in `adapters/claude-code/README.md` under "Not verified" on first use.

Agreed after the build: (1) `/resume-tracer` adopts harmless differences between state and reality (and journals them) and stops only on risky ones. (2) A fresh agent that finds a `[wip]` commit reads its diff, decides whether to build on it or redo it, and says which in its report.
