# JEPA & Memory handoff — 2026-11-23

## Branch / PR state

- PR: https://github.com/RedMentos/Aii/pull/2405 (DRAFT, stacked; NOT_RELEASED)
- Branch: `jepa-memory/v14-temporal-episodic-recall-20261123-run7`
- Code/test checkpoint: `80ed58ff0b1e8351cbe8f68887ef7db6f6abba20`
- PR base branch: `qa/v14-jepa-source-lifecycle-rebase-20261123-run16`
- The base branch currently points to `c5d847ca36567ea265610b235941bf251f1425fa`, while this PR was opened against older base `de4143790bc9ff7e3dc32c40fbc2a4fe9d09dd64`. GitHub compare reports 22 commits behind and the PR is non-mergeable. QA/Boss must recompose the exact changes onto the current QA head; do not merge this stale stack directly.

## Concrete code change

1. `v13/code/v13/world_jepa_temporal.py`
   - Added one Runtime-scoped temporal consumer shared by idle postcommit and bodyview.
   - Added `warm_active_checkpoint`; idle processing warms the active read-only checkpoint, including when learning permission is off.
   - Added `warm_only` to receiver matrix and episodic recall. A cold checkpoint returns `MODEL_NOT_WARM`; foreground B1/B2 never calls the cold loader.
   - Episodic candidate embeddings are processed in batches of 32 with cooperative deadline checks between batches.
2. `v13/code/v13/sleep.py`
   - Postcommit temporal update uses the Runtime-scoped consumer, so the same checkpoint cache is available to B1/B2 after idle warm-up.
3. `v13/code/v13/bodyview.py`
   - B1/B2 bodyview reads only a warm checkpoint.
   - Prompt-visible contract includes `native_body_consumed=false`, `native_body_weights_changed=false`, and `decision_authority=NONE`.
   - Removed optional unsupported-action detail from the prompt (it remains in the audit) and shortened the note to `prediction_only` to preserve the 700-character budget.
4. Tests
   - Restored strict prompt-visible weight-boundary assertion.
   - Added a cold-loader negative control and a `Cognition.offer` test with a deliberately slow loader; the cold foreground path must not call it.
   - Added a cooperative episodic-recall budget check using a deliberately slow latent call; it must stop after at most the query plus one candidate batch.

## Existing learner evidence retained in this branch

The synthetic SQLite/T8 test suite already asserts:
- `parameter_delta_norm > 0` and `ema_target_delta_norm > 0`;
- source-disjoint train/holdout windows and separate sessions;
- shuffled-target and shuffled-action negative controls;
- persisted optimizer state and exact checkpoint SHA after restart;
- rollback to the prior checkpoint and retry of pending rows;
- replay-on/off matched-step ablation and A→B→C→A retention cohorts;
- source-forget protection while active or rollback checkpoints retain the source.

This is **numeric predictor/EMA learning in the local synthetic Store harness**, not GGUF base-weight training, not native B1/B2 weight updates, and not proof of Android learning.

## Test evidence / environment

- Exact code checkpoint `80ed58ff0b1e8351cbe8f68887ef7db6f6abba20`: GitHub Actions runs `45108720991` (Python 3.13 + 3.14 temporal JEPA) and `45108721030` (offline bridge/security) were queued at the last check. No PASS claim until both complete.
- Earlier CI iterations exposed and fixed a duplicate episodic cold load, the missing prompt-visible weight-change field, and prompt-budget overflow. The final exact-head run is intended to verify the complete fix plus slow-loader and budget negatives.
- Local exact-source checkout/tests are BLOCKED: `git ls-remote` could not resolve GitHub and the archive endpoint was inaccessible. GitHub Actions is the available exact-source environment this run.
- Current parent QA PR #2402 at `c5d847ca36567ea265610b235941bf251f1425fa` has five failing jobs; their logs show the same missing prompt-visible `native_body_weights_changed=false` assertion. This branch contains the fix, but the parent branch does not yet.

## Product boundary / Redmi

- The delivered B1/B2 path is still **source-grounded SHADOW prompt readout**. It is not native latent injection or cross-organ model-weight learning.
- No model, weight, permission, user data, or device state was changed. No release SHA was produced: `NOT_RELEASED`.
- New code is `REDMI_UNVERIFIED / NOT_DEPLOYED`.
- The shared V14 handoff's last recorded private Redmi receipts (#690–693) show installed release `aed1d2`, auto-update reported enabled, but also a 57.74 s turn, 41.63 s TTFT, and zero valid B1/B2 offers. Those are historical recorded observations, not a fresh device check in this run.

## Research note

Sony's Future-Aware Retrieval work suggests a useful next research direction: train cue-specific retrieval utility from future outcomes, but keep inference retrieval future-blind. The public `sony/far` implementation is CC BY-NC 4.0 and GPU-heavy; no code, weights, or dataset were copied. A small V14 cue-utility head should be trained from delayed T8 outcomes and compared against recency, latent-distance, random, and shuffled controls with disjoint retention holdouts.

## Next executable steps

1. Wait for exact-head Actions and fix any remaining failure.
2. QA/Boss to recompose the exact JEPA files/tests onto the current #2402 head while preserving newer source-lifecycle work, then rerun the integrated chain.
3. Coordinate a typed numeric receiver/adapter contract with Core. Keep native latent transfer and B1/B2 weight learning OPEN until an actual consumer and numeric weight evidence exist.
4. After an approved release, use only the verified normal updater and obtain a fresh private device receipt. Do not issue a new Termux command or model swap unless the updater is unavailable/defective and a manual step is truly necessary.

**User action: none.**

## Run 8 — exact-head correction and research handoff (2026-11-23)

- Recorded run start: 2026-11-23 05:06 CET. Completion timestamp: UNKNOWN (no measured platform completion clock).
- Code branch: jepa-memory/v14-temporal-episodic-recall-20261123-run7. Exact current code/test HEAD: 30c5522e4ff676d591a81427091d990e09389f37. Readback confirms the branch ref and bodyview/test blobs.
- Repaired the exact #2405 CI failure at prior code head 80ed58ff: the compact prompt note had been changed to prediction_only while the strict regression still required the explicit phrase "not fact/permission". Restored the explicit epistemic note "prediction; not fact/permission" and removed the redundant episodic_note field to preserve the 700-character body-state envelope. The structured fields native_body_consumed=false, native_body_weights_changed=false and decision_authority=NONE remain required and tested.
- Exact-head checks for 30c5522 are QUEUED at readback: temporal-jepa Python 3.13 and 3.14 (workflow 45110132321) and offline-bridge-security (45110132324). No PASS is claimed yet. Prior head 80ed58ff had 20/21 temporal tests passing and one note-contract assertion failing in both Python versions; offline-bridge-security passed. The latest fix is awaiting exact-head execution.
- LOCAL_LINUX full checkout/pytest/compile remains BLOCKED: no checkout mounted and GitHub DNS/archive access failed. GitHub Actions is the only exact-source test environment available here. REDMI_UNVERIFIED / NOT_DEPLOYED; no phone, model, weight, permission or user data was changed.
- PR #2405 remains DRAFT / NOT_RELEASED and stacked on the QA source-lifecycle branch. Its recorded base SHA de4143790bc9ff7e3dc32c40fbc2a4fe9d09dd64 is older than QA PR #2402 head c5d847ca36567ea265610b235941bf251f1425fa; do not merge the stale stack. QA/Boss must recompose the exact bodyview, temporal learner, sleep and test changes onto the current QA head while preserving the newer source-forget chain, then rerun the complete staged/integrated/optimizer/migration matrix.
- New research PR #2411 adds append-only ledger entry R-107 on the current documentation branch: Future-Aware Recall (arXiv:2609.34677) reviewed in full; sony/far main revision and CC BY-NC 4.0 verified; CUDA/H100-scale dependencies and simulation-only evidence documented. No code, weights or data reused. Proposed future experiment is a future-blind cue-utility head trained only from delayed committed T8 predictive utility, with source/session-disjoint holdouts and recency/latent/random/shuffled controls. This is a hypothesis, not current functionality.
- Canon boundary: temporal numeric JEPA/EMA/checkpoint updates and source-verified episodic retrieval remain synthetic Store/Runtime evidence. B1/B2 receive compact source-grounded SHADOW prompt readouts only. No native learned latent transfer, B1/B2 body-weight changes, GGUF training or Redmi learning is proven.
- User action: NONE. No manual Termux command, update request, model download/swap or permission change.
