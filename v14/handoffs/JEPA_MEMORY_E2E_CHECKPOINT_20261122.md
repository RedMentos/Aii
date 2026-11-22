# JEPA & Memory E2E checkpoint — 2026-11-22

## Code and review state

- PR: https://github.com/RedMentos/Aii/pull/2247 — DRAFT / NOT_RELEASED.
- Branch: jepa-memory/v14-per-session-retention-current-20261121-run12.
- Code-bearing tested SHA: 58942cfb9141f7915ee5d85c925c551553f2416d.
- Current branch HEAD at handoff: 050e6f6fa01448aece9aa25d4624278d6f136fcf (research-handoff-only commit after the tested code SHA).
- Base: gpt6/v13-private-remote-bridge-20261111 at bdcad466ffea75a2b41f7d23be168f53c7197d20.
- Boss/Core composition PR #2258 remains DRAFT. #2247 overlaps its staged-builder/deploy pin chain; no rebase or Core-owned pin edits were made.

## Exact test evidence

GitHub Actions push run https://github.com/RedMentos/Aii/actions/runs/44968103405 and PR run https://github.com/RedMentos/Aii/actions/runs/44968107084 both completed SUCCESS on code SHA 58942cf.

The dedicated JEPA optimizer-resume matrix passed in Python 3.13 and 3.14. It ran:
- production JEPA/optimizer/staged-consumer/Store compile;
- real SQLite/T8 resume-vs-reset control;
- 54-report Store A→B→A replay/retention/receiver loop across seeds 13, 19, 43, full-encoder and predictor-only modes, replay arms and projection controls;
- staged optimizer-resume regression;
- selective predictor plasticity and per-parameter Adam resume;
- idle postcommit JEPA/EMA/replay/rollback integration;
- public repository privacy scan.

Per-seed diagnostics were uploaded even on failure:
- Python 3.13 artifact ID 14731629843.
- Python 3.14 artifact ID 14732656726.

### A→B→A results

Each interpreter produced 54 reports. Both had 54/54 source-disjoint holdout manifests, 54/54 exact rollback readbacks, and 54/54 negative-control separation checks.

| Result | Python 3.13 | Python 3.14 |
|---|---:|---:|
| Full-encoder A2 accepted | 22/27 | 20/27 |
| Full-encoder A2 utility-rejected | 5/27 | 7/27 |
| Predictor-only A2 accepted | 25/27 | 27/27 |
| Predictor-only A2 utility-rejected | 2/27 | 0/27 |
| On-demand-loss full-encoder accepted | 5/6 | 5/6 |
| On-demand-loss predictor-only accepted | 6/6 | 6/6 |
| Exact rollback readback | 54/54 | 54/54 |
| Source-disjoint train/holdout manifests | 54/54 | 54/54 |

The full-encoder on-demand-loss projected candidate for seed 43 is rejected; its matched unprojected candidate passes. The predictor-only projected on-demand-loss arm passes all three seeds in both interpreters. These are numeric predictor/encoder/EMA updates in the synthetic SQLite Store path, not GGUF/base-body weight edits.

## Critical remaining receiver gap

The numeric receiver matrix is still a SHADOW adapter. It ridge-fits role heads from WorldJEPA latent predictions to synthetic transition targets and does not change actual B1/B2 model weights. The two interpreter results are:

| Receiver/planner | Python 3.13 | Python 3.14 |
|---|---:|---:|
| Planner ready | 3/54 | 0/54 |
| Planner unavailable | 51/54 | 54/54 |
| B1_DETAIL readout-only | 3/54 | 0/54 |
| B1_DETAIL utility rejected | 51/54 | 54/54 |
| B2_GIST readout-only | 29/54 | 24/54 |
| B2_GIST utility rejected | 25/54 | 30/54 |
| SELF_MODEL readout-only | 3/54 | 0/54 |
| SELF_MODEL utility rejected | 51/54 | 54/54 |

The small cross-interpreter difference is evidence that receiver utility is not robust. It is **not** acceptable to loosen the gate or promote the readout. The A→B→A predictor loop is green; actual B1/B2 semantic use and useful receiver admission are not.

Core PR #2266 is complementary: it provides a native input-embedding ingress probe with exact pinned llama.cpp and ARM64 compile evidence, but it explicitly does not prove trained cross-model alignment, semantic use, or production B3 routing. A coordination comment is attached to #2266.

### Next functional step

Define and implement a model-revision/source-bound, trainable B1/B2 receiver adapter using **actual B1/B2 outputs, supervised targets, or explicit user corrections**. Do not train it on the current synthetic transition y labels and call that organ learning. Persist adapter parameters and optimizer state; bind every update to trusted T8 source/outcome provenance; test disjoint sessions, zero/shuffled/OOD/wrong-action controls, retention, restart and rollback; require stable receiver utility on Python 3.13/3.14 before native B3 promotion. Then connect the adapter to the real B1/B2 consumer rather than only the SHADOW planner.

## Research and deployment

- JEPA-TTT persistence/dense-replay review: v14/handoffs/JEPA_TTT_PERSISTENT_PREDICTOR_RESEARCH_20261122.md.
- CGEM outcome-gated progress/failure event memory review: v14/handoffs/CGEM_EVENT_MEMORY_RESEARCH_20261122.md.
- Both are RESEARCH_ONLY. No code, weights, datasets or dependencies imported; no phone/model/permission changes.
- Full local repository checkout tests remain BLOCKED in this worker. GitHub CI is synthetic Linux evidence only.
- Redmi: REDMI_UNVERIFIED. No authenticated owner receipt, device write, update request or installed-app evidence. NOT_RELEASED.
- The shared V14 board and V14_USER_NEXT_ACTION remain Boss-owned; this handoff and PR comments provide the JEPA evidence for Boss to incorporate after the integration base is stable.

## Run 11 update — 2026-11-22, source-forget guard and latest CI evidence

### Code checkpoint

- JEPA code commit: `35c5e8222a9c06dcc74aede9bb0f2182fb2cb171` on `jepa-memory/v14-per-session-retention-current-20261121-run12`, PR #2247.
- Added `source_forget_guard` in `v13/code/v13/world_jepa_consumer.py` and wired it into `Memory._forget_source`.
- The guard serializes source deletion against the JEPA consumer lock; checks both active and rollback checkpoints; checks the complete scanned T8 action history up to each checkpoint cursor so a source cannot escape detection merely because its bounded replay row was evicted; removes pending-only rows; and prunes orphan checkpoint files.
- It deliberately refuses deletion if a source may have trained an active/rollback checkpoint. This is **not unlearning**. A real source-specific checkpoint rebuild/unlearning path remains missing; the guard prevents a false deletion claim until that exists.
- Added regression cases for active-checkpoint refusal, evicted-row history detection, and pending-only row removal.

### Exact test results on current code commit 35c5e8

The dedicated CI job ran:

`PYTHONPATH=v13/code PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -s v13/code/tests/test_v14_world_jepa_store_aba_replay.py`

- Python 3.13: **16 passed in 74.00s**.
- Python 3.14: **16 passed in 148.69s**.
- The same jobs compiled the production JEPA/Store/runtime/test source set successfully.
- The new source-forget tests are included in those 16 tests and passed on both interpreters.
- `V13 incremental World JEPA`: PASS.
- `V13 combined online JEPA integration`: PASS (49 tests; separate suite).
- `V13 runtime deployment integrity`: PASS.
- `V14 Perception public privacy scan`: PASS.

The overall `V14 JEPA Store A-B-A and Runtime Python 3.13 and 3.14` workflow is **FAIL**, not green: both interpreter jobs pass the numeric A-B-A suite, then fail at the staged-runtime test with `ValueError: unsupported lifecycle source: memory.py`. The staged integrated regression also fails for this same pin. The source lifecycle builder still pins the old memory.py digest `391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484`; the dependent `integrated_memory_world_candidate_20261111.py` pins the lifecycle-builder digest, and downstream candidate pins must be rebound by Core/Integrator. I did not edit those Core-owned files. A coordination comment is on PR #2288 (comment 7072389199).

Other CI failures observed on this commit:
- `V13 private owner-read Termux bootstrap`, `V13 Lab Age control state and WebView truth`, and staged-context regression: the same unsupported `memory.py` source pin.
- `V13 safe additive candidate tests`: not applicable to this change set; it rejects this non-additive PR shape.
- `V13 two-checkout migration`: two assertions fail after the simulated updater reports runtime/dashboard UPDATED and the expected commit; this is a separate updater-contract issue, not diagnosed in this JEPA lane.
- The reviewed-PR integration job was cancelled.
- Local repository checkout is unavailable in this worker, so no LOCAL_LINUX test is claimed. These are CI_LINUX results only.

### Latest A→B→A numeric evidence

Artifacts from run 44972553618:
- Python 3.13: artifact 14734606568.
- Python 3.14: artifact 14734162031.

Both interpreters produced 54 reports, 54/54 source-disjoint train/holdout manifests, 54/54 negative-control separations, and 54/54 exact rollback readbacks. All accepted updates changed checkpoint hashes, persisted optimizer moments, and had nonzero parameter deltas.

| Arm | Python 3.13 | Python 3.14 |
|---|---:|---:|
| Full-encoder B accepted | 27/27 | 26/27 |
| Full-encoder A2 accepted | 18/27 | 23/27 |
| Predictor-only B accepted | 23/27 | 24/27 |
| Predictor-only A2 accepted | 27/27 | 25/27 |
| On-demand-loss full-encoder A2 | 4/6 | 5/6 |
| On-demand-loss predictor-only A2 | 6/6 | 6/6 |

Mean accepted A2 parameter-delta norms: full encoder 0.19002 (Py3.13) / 0.22427 (Py3.14); predictor-only 0.39711 / 0.36354. Full-encoder A2 mean encoder deltas were 0.07251 / 0.07249 and EMA-target deltas 0.07415 / 0.07828. Predictor-only correctly had zero encoder and EMA deltas. The retention/utility gate rejected the remaining updates rather than promoting regressions.

The actual receiver remains the critical gap:
- Planner ready: 0/54 (Py3.13), 1/54 (Py3.14).
- B1_DETAIL: utility rejected in 54/54 (Py3.13), 53/54 (Py3.14).
- B2_GIST: readout-only in 17/54 (Py3.13), 22/54 (Py3.14); all remaining cases utility-rejected.
- Memory recall returned no ranked action in 54/54 (Py3.13), 53/54 (Py3.14).
These are synthetic SQLite T8/numeric-world-model results. They are not B1/B2 GGUF weight changes, semantic latent transfer, or Android evidence.

### Research consequence

- JEPA-TTT (arXiv:2610.00722, 30 Sep 2026) supports persistent predictor adaptation with dense replay under dynamics shift. Treat it as a predictor/replay baseline, not as a reason to freeze the rest of V14's organs: https://arxiv.org/abs/2610.00722
- `Unlearning Isn't Deletion` (ICML 2026, PMLR 306) shows that task-level metrics can hide reversible suppression; future V14 deletion tests need representation/recovery probes, not only a one-time loss or output check: https://proceedings.mlr.press/v306/xu26cd.html
- `Lethe` (arXiv:2601.22601v4, revised 4 Oct 2026) reports knowledge resurfacing after continued training on retained data. A future JEPA unlearning path must be tested after subsequent replay/updates, not only immediately after deletion: https://arxiv.org/abs/2601.22601
- No paper code, weights, dependencies, or data were imported in this run.

### Next executable step

1. Core/Integrator rebinds the lifecycle candidate pin for the changed `memory.py` and its downstream candidate SHA chain, then reruns staged runtime/Termux bootstrap tests. Until that happens this hook is present in PR source but **not deployable through the staged runtime**.
2. Implement an explicit source-bound `OfferPacket`↔human-correction association. The current `Memory.feedback` record is event-scoped and does not itself prove which B1/B2 offer was corrected. Use the existing `BodyJepaTrainer` only after this binding exists, with actual B1/B2 offer outputs and explicit correction targets, model-revision binding, session-disjoint holdouts, zero/shuffled/OOD controls, persisted optimizer/EMA state, restart and rollback. Do not reuse synthetic transition y-labels as body supervision.
3. Keep numeric WorldJEPA and receiver heads SHADOW until the real B1/B2 consumer demonstrates useful, stable readout. Redmi remains REDMI_UNVERIFIED; no update request or deployment occurred; NOT_RELEASED.

The shared `V14_USER_NEXT_ACTION.md` and work board remain Boss-owned; PR #2288 comment 7072389199 carries the exact integration handoff for the next run.

