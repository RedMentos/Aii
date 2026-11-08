# V13 whole-system learning continuity — user clarification 2026-11-08

**Status:** implementation steering / interpretation of existing Canon; NOT a replacement Canon, new gate, or evidence of working learning. Parent: `codex/resume-20261106`. Owner: independent review branch. Canon: `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`). Preserve later user decisions.

## Binding interpretation

The user explicitly rejects reducing V13 to one feedback loop, one JEPA cycle, one model learning at a time, or an endless sequence of isolated numeric guards. V13 is a **multi-organ, multi-timescale, mutually influencing learning ecology**. Different learning signals and representations can coexist, feed one another, and have distinct authorities and retention schedules:

- A0–A5 perception, salience, feature selection, teacher/student projector and modality-specific representation learning.
- B1_DETAIL and B2_GIST: distinct time/resolution specialization, local predictors, representations, adapters and eventual bounded direct parameter updates; neither is merely a static response generator.
- B3_CALLOSUM, B4_DISTRIBUTED_STATE and B5_SUPPORT_INTERFACES: communication/translation, shared context, and alignment learned from provenance-bound signals; Age0 injection remains OFF until gates.
- C_JEF_SYSTEM / C0–C7: control, attention allocation, routing, language/report, outcome attribution and policy learning; JEF is a subsystem, not one LLM or sole global controller.
- F1–F7 and cross-cutting fabrics: attention/gain, fast episodic and associative memory, world/self graph, action→outcome prediction, JEPA/EMA, eligibility + local error + typed neuromodulation, teacher/imitation, feedback/reward, replay/sleep/consolidation, homeostasis and metaplasticity.
- Meta-learning: learn which organ, method, tool and amount of compute to deploy; learn how to learn, not just what to answer.
- Tool and modality development: discover deficits, propose/build isolated tool candidates (including vision/audio workflows), benchmark and retain/reject them with operator approval and sandbox permissions. Tool creation is a learning path, not a shortcut to unsupervised actions.
- Long-timescale architecture evolution: component swaps, consolidation from short-lived state into stable weights, and cautiously evaluated self-modification. No self-granting permissions, no bypass of frozen model cohorts, no Age0 base-weight changes.

These are **interacting mechanisms, not a linear list of fourteen modules to finish in order**. A single experience may inform attention, associations, routing, predictors, organ-specific adapters, replay and eventually stable weights, with different confidence, time, and permission requirements. A teacher or another organ is a reference, not automatic ground truth. Multiple training mechanisms require independent evidence and rollback.

## Execution policy for subsequent runs

1. Read Canon and newer decisions before prioritizing. Maintain a per-feature coverage/acceptance ledger across the **entire** blueprint, not just C5/T8. Preserve all W9 fields and all open gates.
2. Prefer a **real integrated vertical slice with multiple concurrent learning paths** (e.g. source-bound experience → association/retrieval + local predictor/JEPA shadow + attention/router update candidate + replay + second-attempt/retention/restart/rollback), rather than treating a single feedback ledger as the whole learning system.
3. Prove real data flow, persistent state, runtime consumer, telemetry, baseline/ablation, second-attempt utility, retention, restart and rollback. Distinguish structural/synthetic/Linux-native/Redmi proof. A passing helper unit test is not learning utility.
4. Build isolated candidates around frozen SourceHandoff cohorts. Explicitly maintain Age0 RECORD_ONLY / SHADOW_UPDATE / APPROVED_COMMIT boundaries; no direct base-weight plasticity or autonomous tool activation without the requisite approvals.
5. For each package state **which organs and learning mechanisms interact**, what remains disconnected, and which next integration closes the most meaningful gap. Avoid serial micro-PRs that never enter a runnable consumer.
6. Cross-review, privacy scan, remote readback, evidence hashes, checkpoint and continue. Do not mark whole-system acceptance from partial proof.

## Current known negative claims (do not promote)

STEP2 UTILITY_FAIL; B3 L1 FAIL/NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; full-suite historical RED; no new Redmi proof. C5 ledger PRs #1605–#1608 are review-only, not runtime integrated. Older native learning and model work is recorded in BUILD_STATE but does not by itself establish end-to-end continual learning.

## Next implementation decision

Inspect the newest owner branches, actual Runtime consumers, learning-state stores and registered cohorts. Choose an integration slice that connects **at least two distinct existing learning mechanisms** under the canonical permissions, then execute exact-source tests and compare against baseline/ablation. Keep this note as a steering document; do not edit the frozen Canon.

## Checkpoint

Source: this document on an isolated branch. Tests: none (documentation-only). No weights, gates, seeds, or cohorts changed. Exact next command: fetch `v13/code/BUILD_STATE.json`, `v13/ROADMAP.md`, `v13/code/v13/agi/runtime.py` and current owner PRs; identify runtime path and baseline; implement and test a connected slice on a new owner-safe branch. Open questions: actual current owner/branch for multi-path learning, freeze constraints, available Linux-native artifacts and Redmi runner.


## Engineering throughput contract — user clarification 2026-11-08

The user explicitly wants **substantial connected implementation**, not endless defensive micro-patches and test-only PRs. Work in feature-sized batches: inspect source/ownership and define the integration boundary, implement multiple connected pieces with real consumers and persistence, run cheap compiler/type/lint/unit feedback during development, then execute targeted integration and acceptance tests, fix discovered failures, review and checkpoint. Keep existing safety gates, source freeze, privacy scans and registered native evidence intact. A passing unit suite is a milestone, never the end of the project.

**Language choice is engineering-driven, not a blanket rewrite.** Python remains suitable for orchestration, experimentation and model ecosystem glue. Prefer Rust for newly built native hot paths, concurrent queue/state machinery, binary protocol parsing, memory-sensitive streaming or tools where ownership/type safety and speed materially help. Use Rust's compiler, clippy, rustfmt, unit/integration tests and sanitizer/Miri where available; profile before replacing functioning Python or native C/C++ inference kernels. For Android/Termux, verify target support, ABI, dependency size, cross-compilation and runtime RAM/latency. Rust does not guarantee logical correctness or learned utility.

**Package-level evidence:** for each substantial slice, identify interacting organs and learning mechanisms; actual runtime entrypoint; persistence and restart; operator permissions; cheap dev checks; end-to-end baseline, ablation, retention, rollback; native/Redmi gaps; remote commit and readback. Test strategically at module boundaries and before integration, not by running full expensive suites after every line. Do not suppress known RED gates or change preregistered cohorts.

**Execution rhythm:** code substantial connected functionality → compiler/static checks and focused tests → fix → integration/evidence/review/privacy → durable remote checkpoint → continue next high-value package. Agents may own disjoint modules, not shared frozen runtime files. Avoid creating new isolated helper-only PRs unless a concrete blocker requires it. This is a priority/working-method clarification, not permission to bypass safety or accept untested code.
