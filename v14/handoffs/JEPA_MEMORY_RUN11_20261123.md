# JEPA & Memory — Run 11 handoff (2026-11-23)

## Ownership and exact branch state

- PR: #2426 — JEPA temporal source-forget checkpoint invalidation.
- Branch: `jepa-memory/v14-temporal-safe-forget-20261123-run10`.
- Latest code/test head: `66aa86a00559896ad4e1d1a0018269171f760767`.
- Latest docs-only head after research-ledger append: `69abc77f19086e7a58a00cb7963fb4937b6b2c95`.
- Readback: `v13/code/v13/world_jepa_temporal.py` blob `96433c6e73d83eb3f45683d4767ba3e8253da6f9`; temporal runtime test blob `dfc37235396ccb96402a217cae74b58b6aa5a1c7`; research ledger blob `1e2377310056765b2f959678db3fe05c4c0d0a72`.
- This is a QA-parent stack, not a release-branch merge or release candidate.

## Implemented code

The temporal source-forget check previously examined only bounded `experience_rows`, retained holdouts and LearningIntent provenance. Because `MAX_ROWS=2048`, an older T8 training source could age out of replay metadata while still influencing active/rollback parameters.

The guard now checks the full eligible ActionOutcome history up to each checkpoint's own persisted `scan_cursor` by joining `actions` to `events.source_id`. It excludes source rows that are still only pending/untrained. The query is bounded at `MAX_ROWS + 1`; this exceeds the maximum possible pending set by one and avoids an unbounded SQL parameter list on Android SQLite. Both active and previous checkpoints use the same shared JEPA lock as the WorldJEPA source-forget path.

The new regression covers:
- a source present in scanned T8 history but absent from bounded replay/holdout/intent metadata;
- a pending-only row that must not invalidate a clean checkpoint;
- an unrelated source;
- a row beyond the checkpoint cursor.

The clean-previous/restart fixture was expanded to the full 256-action page budget to stabilize source/session-disjoint synthetic holdouts. No utility threshold, learning permission, optimizer gate or product default was weakened.

## Exact test evidence

- GitHub Actions temporal workflow `45136932525`: **PASS** on Python 3.13 and 3.14; each version ran 25 temporal runtime tests and 17 postcommit runtime tests; compile step passed.
- GitHub Actions runtime-deployment integrity `45136932490`: **PASS**.
- Optimizer-resume/source-forget workflow `45136932628`: **FAIL** at the QA-owned staged lifecycle source pin. Composer expected `memory.py` SHA-256 `bdd6cc576cef69601c570bf80ace72f4d07c0e5091a28a4f8d8ba933b0040255`, but the PR candidate contains `33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701`; error: `unsupported lifecycle source: memory.py`.
- Staged/integrated workflow `45136932504`: **FAIL** at the same stale memory.py pin; migration reports PARTIAL downstream. QA was notified on #2402, comment `7095208639`. JEPA did not edit QA-owned composer, recovery, stage or deployer files.
- Local Aii repository suite: **BLOCKED / NOT_RUN**. No checkout is mounted in the execution container and GitHub DNS resolution fails there. An isolated SQLite query harness passed 5/5 logic checks; that is not a repository test and is not counted as LOCAL_LINUX project evidence.
- No native GGUF/body-weight update, learned B1/B2 latent injection, or Redmi behavior is proven by these tests.

## Research

Appended R-080 to `v14/V14_RESEARCH_LEDGER.md`: continual deletion in post-training agent networks, transition-based unlearning, and plasticity collapse. Evidence is ABSTRACT_VERIFIED only. The practical V14 implication is to test downstream derived-trajectory lineage and repeated-forget stability after the direct full-prefix scan. No external code, dependency, model or weights were imported; exact external code licenses remain unverified.

## Device and release boundary

- No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, remote shell, model/weight change, permission change or device mutation was performed.
- No private V13OBS payload was copied into this public handoff.
- Candidate remains **DRAFT / NOT_RELEASED**. Redmi verification for this candidate remains **REDMI_UNVERIFIED**.
- The separate public P0 issue #1904 remains open: normal chat latency/correctness and B1/B2 offer delivery are not accepted.

## Next executable actions

1. QA: rebind the exact memory.py source pin and dependent builder/stage/deployer hashes bottom-up on the QA-owned composition branch; rerun optimizer-resume, staged/integrated, migration and privacy checks on one exact head.
2. Boss: review #2426 on the current QA base; merge only into that QA parent after the full exact-head matrix is green. Do not release or request a phone update from this PR alone.
3. JEPA: next add explicit source-lineage closure for downstream ActionOutcome trajectories that consume earlier source-derived context, then test repeated A→B deletion, later replay, retained utility, future learning capacity, restart and rollback. Keep all source-derived probes inside the forget lineage.
4. Keep B1/B2 receiver and learning promotion SHADOW/OFF until independent holdout utility, retention, rollback and device consent gates pass.
5. No user action is required for this code-only checkpoint.

## Run accounting

- Started: 2026-11-23 09:02 Europe/Berlin (automation context).
- Completed: UNKNOWN.


## Next cross-organ provenance gap verified (not changed in this PR)

The direct source-forget fix above is not yet full derived-source unlearning. Current code inspection shows a producer/consumer gap:

- Runtime computes the broader `meta['context_source_refs']` only after output preparation in `v13/code/v13/runtime.py` around lines 577–586.
- C5 selection is emitted earlier at `runtime.py:503` through `ActionGate.select(...)`, but the call receives no context-source set.
- `v13/code/v13/focal.py:577` creates the committed `ActionSelection` packet with only `[e['source_ref']]`, even though the turn may have used Memory, history, executive state, observer offers and other source-backed context.
- `v13/code/v13/world_jepa_store_authority.py` verifies the EventEnvelope's single `source_ref` and requires `event.provenance` to contain exactly that one ref; the verified T8 proof therefore cannot express the full context dependency set.
- `ActionOutcome` currently contains action_id/status/actual only. It does not independently restore the missing context lineage.

**Required cross-agent contract:** Core/Runtime must construct and attach the complete, bounded source-ref set actually admitted to the selected action before the ActionSelection commit; JEPA must validate every ref against Store source/hash/span and persist the complete set into each temporal training row/checkpoint; base WorldJEPA and Memory source-forget must query every member; missing, revoked or over-bound provenance must fail closed for learning. Do not infer context dependencies from text after the fact.

**Next test:** source A enters B's recalled/observer context; B's ActionSelection and T8 ActionOutcome must carry A and B refs; train a checkpoint; forget A; verify B-derived windows/checkpoints are invalidated or rebuilt, while an unrelated C cohort remains. Then repeat a later update and verify no A-derived trajectory re-enters. This requires Core producer ownership and JEPA/Memory consumer coordination; no Core-owned runtime/focal/Store file was modified in this PR.
