# V13 fast integration agent playbook (2026-11-10)

**Purpose:** Finish programming the user's full existing V13 Canon as an integrated, patchable, Termux-ready learning system **before** extensive real-weights learning experiments. This document is an execution guide, not a replacement for the Canon, AGENTS.md, security/approval contracts, or SourceHandoff runtime freeze.

**References (reviewed 2026-11-10):**
- OpenAI, Harness engineering: https://openai.com/index/harness-engineering/
- OpenAI, Run long horizon tasks with Codex: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- OpenAI, Codex best practices / AGENTS.md: https://learn.chatgpt.com/guides/best-practices
- Anthropic, steering Claude Code (CLAUDE.md, skills, subagents, hooks): https://claude.com/resources/articles/steering-claude-code-skills-hooks-rules-subagents-and-more
These are engineering patterns, not a guarantee of finishing V13 in hours.

## Non-negotiable execution target

- **One evolving codebase**, not a growing set of disconnected demo branches. Start with the latest verified V13 integration branch/commit; fetch HEAD and cross-check owners before every write. Reconcile existing PR chains and canonical contracts before inventing a new subsystem.
- **Implement the entire agreed blueprint**, not a fake scaffold: actual data paths, model/training adapters, persistence and restart, parameter/config controls, native-capable interfaces, debugging/export, telemetry, patches/rollback, and bounded tests. Do not quietly re-scope or redefine "complete".
- **Separate code completion from learning efficacy:** a tiny synthetic update proves a runnable learning mechanism, not a useful trained B1/B2/C3 or AGI result. Keep every promotion/proof gate unchanged (STEP2/B3 negative gates, SourceHandoff freeze).
- **Minimize early dependence on the user's Redmi:** use disposable toy models, bounded real NumPy/PyTorch weight updates, source-provenance fixtures, emulator/CI, and contract fakes. Reserve real-weight native model learning, memory measurements and battery/storage validation for follow-up with the user. Never fabricate device evidence.
- **Explain to the human as a Vibe Coder:** name the organ (e.g., left/detail B1, right/gist B2, dispatcher JEF, C3 language, World-JEPA), one-sentence function, actual connected status, exact missing proof, and how to view errors. Preserve technical identifiers alongside labels.

## One run = execution, not another planning report

1. **Read, verify and research:** current HEAD of integration branch; AGENTS.md; Canon; current work ledger/CI; code owners; frozen files; existing implementations. Identify ONE highest-leverage missing integration edge or blueprint obligation. Dispatch bounded R1/R2/R3 investigations if useful; keep coding on unblocked tasks while research proceeds. Before adding new code, look for an existing V13 implementation and upstream solution.
2. **Define executable acceptance:** record source module, consumer/owner, real input and output contract, persistence, failure/rollback behavior, and the smallest concrete command proving the update. If model training, show parameters/gradient before and after plus no-op/invalid-input negative control.
3. **Build while research runs:** modify existing modules and their wiring rather than producing another standalone candidate. Keep clean extension seams and operator knobs so later changes do not require rewriting the core. If touching a frozen runtime source is forbidden, work on a reviewed hash-bound candidate and mark the frozen merge BLOCKED; do not silently promote.
4. **Verify cheaply first:** syntax/import, unit/regression and one actual integration smoke. Use toy models when feasible; test restart/checkpoint and that previously negative gates stay negative. Test source/provenance isolation and rollback where relevant. Avoid requiring a full CI suite for every two-line change; run focused tests per milestone and broader suites at integration boundaries. Known unrelated failing tests must be logged precisely, never relabelled PASS.
5. **Integrate before starting the next feature:** make the actual runtime/operator call path reach the new capability in the shared integration checkout; test this path. Small independent owner-scoped PRs are allowed to avoid collisions, but should be reconciled promptly with the integration branch. Never leave success as "in a branch somewhere".
6. **Persist/checkpoint:** save source, tests and continuation ledger with exact commit and verification. Read them back. Append tested command, outcome, open blockers and the exact next code location/command. No unverified percentage/ETA.
7. **Continue to next highest-leverage integration edge within the available execution window.** Do not stop merely because a task unit is done. If a tool or dependency fails, switch to a different executable, nonconflicting code path and preserve a bounded actionable blocker. Do not claim background progress without an actual scheduled run.

## Three parallel research tracks (research must feed V13 code)

Research accompanies implementation; it does not replace it. When available, delegate independent read-only research work to different agents while the coordinator continues coding an unblocked integration edge. If tools do not permit concurrent agents, perform bounded sequential searches; never claim parallel workers were launched. Preserve the full user-approved blueprint rather than simplifying it without approval.

### R1 — Scientific and architectural research: WHAT and WHY?
- Search up-to-date primary papers, official releases, model cards and repositories for underdefined V13 functions: JEPA/EMA, continual online learning, replay, metaplasticity, world and self models, attention, cross-organ learning and scalable memory. Follow new research when it directly addresses an existing issue.
- Compare at least one plausible alternative or a simpler control when a mechanism is uncertain. Explain its assumptions, failures, latency/memory consequences, and the tiny falsifiable test for V13.
- Current research candidate, accessed 2026-11-10: Meta's V-JEPA 2.1 official source (https://github.com/facebookresearch/vjepa2) describes dense predictive loss and deep self-supervision. This large video-world-model code is NOT a Redmi-compatible drop-in or evidence of V13's own learning. Investigate whether a small objective can be adapted and compare it with the current JEPA baseline.

### R2 — Code, open-source solutions and issue research: HOW do others implement it?
- Search the V13 repo first, then upstream open-source source code, releases, issues, PRs, bug reports and regression tests for analogous bugs or architectures, before writing a new one-off component.
- Record URL, date, revision/tag, license, dependencies, trusted source, security risks, Android aarch64/Termux feasibility, memory footprint and license compatibility. Prefer a narrow adapter with source attribution over wholesale copying.
- Sources examined 2026-11-10: Avalanche continual-learning baselines (https://github.com/ContinualAI/avalanche) can inform replay/retention tests but may require PyTorch outside native Termux; Hugging Face PEFT docs (https://huggingface.co/docs/transformers/peft) for LoRA adapter training and restart; llama.cpp separate GGUF LoRA inference (https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md) is NOT evidence of supported native training for pinned V13 models.
- If upstream implementation cannot run on Redmi, extract only a tested small algorithm or interoperable interface that meets the pinned model contract and license. No unreviewed dependency or architecture replacement.

### R3 — Research the development process itself: HOW to deliver faster?
- Periodically review coding-agent guides and actual V13 outcome metrics for parallel agents, context/compaction, reviewing, worktrees, harnesses, deterministic tests, cost, model selection and integration cadence.
- Current sources, accessed 2026-11-10: Codex subagent instructions https://learn.chatgpt.com/docs/agent-configuration/subagents ; Anthropic multiquestion researcher guide https://github.com/anthropics/claude-cookbooks/blob/main/patterns/agents/prompts/research_lead_agent.md .
- Separate independent source review from writing shared runtime files; one coordinator owns merge and integration. Parallel research is helpful only if time saved exceeds extra token/coordination cost. Test proposed workflow changes against elapsed cycle time, merged functionality and regressions, not number of agent messages.

### Research-to-code handoff (required for every research track)
1. Trigger: specify concrete organ, code path or unresolved blueprint requirement; state the user-visible function it unblocks.
2. Evidence: primary source URL, date, exact release/commit, license and compatibility; separate verified upstream behavior from a hypothesis about V13.
3. Proposal: integration seam, existing V13 component to reuse, tradeoffs, mobile budget, expected failure conditions and smallest control experiment.
4. Decision: ADOPT, ADAPT, EXPERIMENT, REJECT or WAIT_FOR_DEVICE, with rationale, owner and next code file/test.
5. Action: implement and test an actionable solution in the shared integration branch rather than opening another indefinite research PR; preserve frozen/runtime promotion gates and tests. If blocked, record exact blocker and continue unrelated integration.
6. Keep time bounded: research only deep enough for the next architectural decision. Deeper background study is permitted when the decision materially depends on it; never halt coding merely to accumulate links.

Research ledger line: Track | V13 organ/problem | source/revision/date/license | comparison | decision | exact integration path/test | owner | next step.
Do not count research notes as finished code. The coordinator must review and connect adopted research results.
## Multiple-agent partition

- Coordinator: owns shared Runtime/operator integration, HEAD, merge resolution, Canary smoke, ledger; only coordinator edits shared orchestration files.
- Worker A (Brain learning): owns B1/B2 training adapters, ability to update a tiny trainable layer, checkpoint+rollback, no change to native GGUF until proof.
- Worker B (World learning): owns T8/World-JEPA source-bound learning, holdouts, replay, private checkpoints; must produce an invocable runtime call.
- Worker C (Language/memory): owns C3-LoRA and Context OS interfaces, saved model metadata, memory/diagnosis exports, with separate specific file ownership.
- Independent reviewer: inspects exact diffs, provenance, safety gates, test claims, conflicts and privacy without mutating the worker's files. One agent should not be asked to merge simultaneous overlapping edits.
These workers describe **delegation assignments when multiple agents are actually available**, not a claim that they have been launched.

## Definition of 'blank programmed' vs 'fully validated'

- **PROGRAMMED/CONNECTED:** callable from the integrated runtime; consumes the intended actual packet/provenance; changes intended trainable state in a controlled tiny test; stores/restarts where required; emits meaningful error code and diagnostic; has configured knobs and a rollback path; focused tests and integration tests passed at an exact commit.
- **NOT YET VALIDATED:** target GGUF training port, real memory/RAM/timing on Redmi, extended old/new holdout retention, learning usefulness, model generality, AGI. Label this separately, never treat absence of measurement as a pass.
- **BLOCKED:** exact missing model master weights/training port/permission/frozen cohort/hardware evidence; keep an owner, link and retry command.

## One compact status line per completed milestone

`Organ | Blueprint requirement | actual integrated path | code status (PROGRAMMED / PARTIAL / BLOCKED) | focused test output | native proof (YES/NO) | commit | next edge`.

No raw "percent complete" without a stable denominator. Measure the number of connected requirements that meet the above definition instead of counting commits, PRs, lines or files.

## Pasteable coordinator prompt for Codex/Claude/Work

> You are V13's code integration coordinator, not an isolated prototype generator. Read AGENTS.md, the canonical V13 handoff and the latest verified integration HEAD. Prioritize fully implementing the user's agreed blueprint, including actual online-learning mechanisms and the interfaces for eventual on-phone diagnostics, without requiring preliminary full model training. Do not simplify the agreed architecture merely to make a demo. Audit existing code and PRs first to avoid duplicating features. Pick the most important missing integration edge, implement it in the common integration worktree, prove it with small genuine weight-update, restart and end-to-end tests where relevant, preserve all frozen-source restrictions and negative safety gates, commit/push and verify, and continue with the next nonconflicting edge within your active execution budget. Parallelize only file-disjoint packages with explicit owners and a single integrator. Add R1 science/new-releases, R2 existing code/bugs, and R3 coding-process research where relevant, requiring an actionable ADOPT/ADAPT/EXPERIMENT/REJECT/WAIT_FOR_DEVICE decision for each research result. Do not spend whole runs documenting CI failures; try a bounded reproduction, log the blocker, and work on another executable feature. Report what changed, exact tests and the remaining unimplemented edges, not an invented completion percentage. Use accessible brain-part names alongside technical names so the user can understand and operate V13.

## Relevant exact paths and baseline

- Integration PR: https://github.com/RedMentos/Aii/pull/1655
- Canon: `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`
- Runtime: `v13/code/v13/runtime.py`, Operator: `v13/code/v13/operator.py`
- World: `v13/code/v13/online_world.py`, `v13/code/v13/world_jepa.py`, `v13/code/v13/world_jepa_online_experiment.py`
- C3: `v13/code/v13/lora_trainer.py`
- Tracking: `v13/code/docs/work_ledgers/CORE_INTEGRATION_20261110.json`
- Existing focused test family:
  `PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_runtime_jepa_integration_20261110.py v13/code/tests/test_online_world_20261108.py v13/code/tests/test_world_jepa_online_experiment_20261108.py v13/code/tests/test_lora_resume_safety.py`
- Public repo privacy scan before review/merge. Never save raw private chat, device identifiers or credentials.

**Reminder:** good prompting can reduce wasted effort, but it cannot authorize a frozen runtime merge, invent a training ABI, or prove an unmeasured model improves.
