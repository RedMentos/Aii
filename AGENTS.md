# V13 continuation rules

## Working style for all agents (user rules, 2026-10-27)

These rules come first and apply to every AI in this project (Claude, GPT/Codex, subagents).

- Work diligently and autonomously. Keep going until the packages are done or the limits are used up; do not stop after one small task and do not wait for permission on routine steps.
- Model roles: Opus only for drafts, principles and review; Sonnet for code and tests; Haiku for simple searches. (GPT: use the same split with the models you have.)
- Always record the state in memory, `v13/ROADMAP.md` and git, and verify the remote after each push. Local work alone is not a backup.
- Reuse legally usable code and legally usable theory, and record the source, license and access date (IH-H31). Never copy anything whose license is unclear.
- Before every test, check against the Blueprint whether the component has its data and prerequisites (including a consumer for its output) and how much gain could be visible at all, also for the component alone. If something is missing, build first. No repetition without a new idea.
- In chat: short, honest, explanatory, plain German (no internal jargon; explain names). Ask the user only when a real decision is needed.
- A phone package exists only when everything is in; then one big per-component test run.
- Full overview and build order: `v13/blueprint-stand/BAU_REIHENFOLGE.md` (packages WP-BP1..BP12) and the overview page linked there in ROADMAP.md.

These project instructions preserve the user's decisions, including the 2026-10-12 request to recover research, open questions, end goals and agent work rules and continue without requiring a full chat export. Read the current remote HEAD before work; this file does not replace the Canon or the existing plan.

## Sources and priorities

- Start with `v13/code/docs/HANDOFF_CURRENT.md`, `v13/code/BUILD_STATE.json`, `v13/ROADMAP.md`, `v13/NUTZER_ENTSCHEIDUNGEN.md` and `v13/code/docs/USER_CONTINUATION_DECISIONS_20261011.md`.
- Canon: `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`. The user's newer decisions prevail over older design choices. Runtime code and closed evidence determine implemented state.
- Finish the existing Drive plan. Continue implementing, testing and fixing until robust extended human testing is possible. Research and future improvements supplement the plan; they do not replace unfinished packages. Missing exact historical transcripts are a retrieval limitation, not a reason to stop authorized work.
- End goal: many distinct model organs, English first and later observable German learning, world model, continuous learning, a reduced brain simulation on Android/Termux. Local tools, knowledge and developing autonomy toward RSI/AGI remain long-term aims, never an already demonstrated result.

## Research and unanswered questions

- Recover prior relevant decisions instead of asking the user to explain them again. Distinguish original user messages, archived extraction notes and assistant interpretations; never invent exact last-three-message wording.
- Archived `v13/sichtung/chat1.md` records researching current models and versions individually, including newest Hugging Face entries rather than only leaderboards. Verify current recommendations against primary model cards, official repositories, papers and licenses before selecting them.
- Follow Canon IH-H31: record source, access date, claim scope and current/historical/hypothesis status. Record license, revision, compatibility, provenance and missing prerequisites for usable third-party code/models.
- Each research question needs evidence for and against, a small Redmi-testable baseline, V13 mapping, failure modes, an ablation and what result would change the implementation. Research can challenge a mechanism while preserving the locked functional goal.
- Keep open questions, blockers, missing models and prerequisites in the persistent handoff. Resolve what can be researched or tested independently; ask only for a genuinely missing decision or device action. Model swaps require separately bound comparisons and must not alter an active preregistered cohort.

## Agents, evidence and persistence

- The user requests agent-assisted work. Delegate independent code/research/review packages with explicit file ownership; the coordinator checks results, integrates and tests. Do not let agents concurrently mutate shared status or frozen sources. Do not claim access to Claude's live conversation; exchange via the agreed GitHub/Drive handoff.
- Heavy native inference and full-master training run serially under the measured Linux cgroup budget. Read current lifecycle/registration before starting. Never run competing heavy jobs or signal unowned processes.
- Preserve original protocols, numerical settings, model/source hashes, failed attempts and negative gates. Current runtime Python is frozen for SourceHandoff: prepare fixes as isolated hash-bound candidates until that cohort permits integration.
- Implemented means code, actual data path, persistence/restart, tests and telemetry. Software/synthetic tests, structural checks, Linux-native runs and real Redmi measurements are distinct evidence levels. Never present SHADOW/scaffold as learned utility.
- Existing STEP2 UTILITY_FAIL and B3 L1 FAIL remain until their original gates pass. `canonical_architecture_complete` and `user_full_scope_complete` remain false while any required scope is open.
- Publish reviewable checkpoints regularly to the authorized `RedMentos/Aii` work branch without re-requesting routine push permission. Verify remote commit/tree after each push; local commits alone are not a backup. Preserve a current handoff for Codex/Claude/other agents and update the agreed second location when technically available.
- Close and hash-bind raw evidence before saving; use the existing lossless small-object storage for large artifacts. Give brief progress updates and continue across checkpoints rather than stopping after one small task. Never claim a save, model run or result before confirmation.

## Cross-review between Claude and GPT/Codex (user request 2026-10-21)

The user wants Claude and GPT/Codex to check each other's work. This is a standing rule for both sides:

- Before building on the other side's latest work, review it first: run the full suite, read the runtime-code diff (`v13/code/v13/`), try at least one counterexample per new guard or gate, check that every FAIL stays FAIL and that SHADOW/synthetic/Linux/Redmi evidence levels stay separate, check that preregistrations were committed before their runs, and run `python v13/code/scripts/public_repo_privacy_scan.py --base <last reviewed commit> --head <their branch>` (must print CLEAN).
- Also check the goal: no harm to people; new tools or modules default off and only run with the user's conscious, unmanipulated permission; unmeasured SHADOW parts get no decision authority.
- Record each round at the top of `v13/PRUEFUNG_CLAUDE_FUER_GPT.md` (or `v13/PRUEFUNG_GPT_FUER_CLAUDE.md`): reviewed commits, commands with output, findings (bug / note / OK) and what you changed. Fix confirmed small bugs with a test; leave larger findings as open points for the other side or the user.
- Never overwrite the other side: `git fetch` before every push, merge foreign commits instead of replacing them, no force-push, and name in the handoff what came from whom. The repo is public: nothing private (tokens, personal data, private chats, device identifiers) in git; private material goes to Drive only. Back up each round to git and Drive.
