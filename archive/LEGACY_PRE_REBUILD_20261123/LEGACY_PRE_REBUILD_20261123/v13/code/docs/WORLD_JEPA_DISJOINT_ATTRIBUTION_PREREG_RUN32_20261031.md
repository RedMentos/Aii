# Run32 prereg — disjoint real-file World-JEPA attribution replication and same-seed original Z12b

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run31 #1358 at exact `83be15bed42b7800260ed82a1cd70fcd7798e131`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Frozen original Z12b source blobs `99a686a131a1bdc89efe0d0cf9610ec54cbd853b` / `2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4`, frozen Run28 slot-shared candidate blob `67e14e0d03c50c4767b74d5b02a819a95c6cc262` and Run28 real-file orchestration blob `dbf3af3f8bc61a846eb542c7db3cc034e94f5bd7`. No edits to these files, seeds 101–103, or their original W1–W6 prereg/FAIL.

## Prior evidence motivating but not pre-qualifying this study

Run29 original registered Actions 41145551357 at seeds 101–103: W1–W5 PASS, **W6 FAIL**. Own-only and world-only attribution were both near ceiling for action-conditioned and no-action models, while the previously *non-gating* `both_world` and `none_self` categories differed more strongly. W6 is binding and must not be reinterpreted or waived. New W7 is a separately preregistered **exploratory replication**, not a replacement for W6 or evidence of full World-JEPA success. The original Z12B_WORLD_JEPA_FAIL remains authoritative.

## Frozen disjoint cohort, before any fit

Seeds **201,202,203** (disjoint from Run28/29 101–103), per seed train=4000, cf=150, attr=300, steps=3000. Same original deterministic action grammar and file-world collectors, no modifications to `collect_train`, `collect_cf`, `collect_attr`, `cf_eval`, `theta_of`, `attr_eval` or `criteria`. Run both (a) original Z12b WorldJEPA 16D and (b) Run28 slot-shared candidate 6×16D=96D with their existing own/zero/shuffled controls, independent work roots and raw. Same seeds are **not exact paired transitions** because real-world scheduler timings vary; do not claim row-level causal pairing. No new hyperparameter, threshold or architecture search.

For each candidate seed, compute original W1–W6 via unchanged `original.criteria`; if any W gate fails, candidate status **SHADOW_CANDIDATE_FAIL** even if W7 passes. Preserve original Z12b W1–W6 separately as descriptive, without overwriting its historical failed cohort. Retain all per-seed raw, hashes, failed partial attempts, and zero-action controls. No native GGUF, Redmi, private user data or live runtime authority.

## New disjoint W7 attribution diagnostic (frozen before seed201)

For each seed and model, calculate four-class macro accuracy over the existing non-ambiguous `own_only_self`, `world_only_world`, `both_world`, `none_self` rates; each class must have >= 15 valid examples per seed, or W7 FAIL with reason. Compare candidate own-action model against its **own** zero-action control, not the original 16D model. Predeclare three subgates:
- **W7a** mean across seeds of `both_world(JEPA)-both_world(zero)` >= **.20**, each seed >= **.10**.
- **W7b** mean across seeds of `none_self(JEPA)-none_self(zero)` >= **.05**, each seed >= **0**.
- **W7c** mean across seeds of the four-class macro difference >= **.08**, each seed >= **.04**.

W7 positive is only exploratory evidence of action-sensitive attribution on a fresh file-world cohort. The candidate still has a 96D vs original 16D capacity confound, no matched-capacity control and original W6 binding. No retrospective threshold adjustment, no dropping failed seeds or changing original gates.

## Acceptance and continuation

Require exact source/blob/seed pin, fresh paths, three original and three candidate seed checkpoints, real-file Linux execution, original W1–W6 for both arms, W7 predeclared thresholds, finite outputs, SHA256SUMS, closed raw, privacy scan and private backup. Fail closed on missing or partial results. Next independent work after this should be a genuine **matched-capacity** control and stronger intervention against the world-only/own-only ceiling; no automatic learning activation.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi, no whole-system completion. No production merge.
