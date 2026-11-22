# JEPA & Memory — Run 20 handoff

**Date:** 2026-11-22 22:24 CET  
**Code PR:** [#2372](https://github.com/RedMentos/Aii/pull/2372)  
**Code branch:** `jepa-memory/v14-temporal-exact-forget-retention-20261122-run14`  
**Exact code head:** `50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b`  
**Status:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Implemented code change

The actual B1/B2 prompt regression exposed a real budget defect: the temporal readout was constructed, but the compact body-state view exceeded the fixed 700-character limit and the fallback removed `world_jepa_temporal`. The old length check also omitted the final `authority` and `role` fields.

- `71b68906`: compact prompt labels and per-action rows; retain full canonical target semantics and full 64-hex history source hashes in the stored audit; use 8-hex display fingerprints only in the prompt; preserve `native_body_consumed=false` and `decision_authority=NONE`; count the final authority/role envelope.
- `50e3c8d`: update tests for the compact note semantics and assert that the audit still contains canonical target semantics and full source hashes.
- The predictor/checkpoint and training weights were not changed by this fix.

## Verification

- Previous exact head `71b68906`: temporal Python 3.13 and 3.14 each reached the actual Cognition.offer prompt inclusion, <=700-character, role-target, source-prefix and checkpoint assertions; both failed only at the old note-text assertion: 14 passed / 1 failed.
- Current exact head `50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b`:
  - temporal T8 run `45072681648`: Python 3.13/3.14 IN_PROGRESS at last readback;
  - staged/integrated `45072681696`: staged-runtime FAIL 19/231/10 skipped/2 errors from QA memory.py pin; integrated-regression IN_PROGRESS;
  - optimizer-resume `45072681698`: Python 3.13/3.14 FAIL at same QA pin;
  - owner-read `45072681647`: owner-read job PASS, staged startup FAIL at same QA pin.
- Exact QA pin mismatch: expected `61e881ad8b3f8cb60a96339599a1627cd5af7b5a5bfd29fe5f371c17f5a29ebc`; actual `memory.py` SHA-256 `33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701`. JEPA did not edit QA-owned files.
- LOCAL_LINUX isolated prompt-budget fixture: 8/8 PASS across B1/B2 and 1–4 supported actions including final authority/role fields. Full repo compile/pytest BLOCKED: no checkout and GitHub DNS failure.

## Consumer and product boundary

Test path: trusted synthetic T8 ActionOutcomes → persistent Store-backed temporal WorldJEPA/EMA predictor → source-bound B1/B2 bodyview → actual `Cognition.offer` prompt capture. The accepted gate in the prompt fixture is explicitly test-only; learned receiver utility remains separately measured. This is not native B1/B2 weight learning or trained native latent transfer. Sleep/replay remains experimental Store-backed learning; no native Dream consolidation proof.

## Device / updater

Latest authenticated read-only device evidence still places release-development SHA `aed1d2b826290c95c70356b5d8b864b5ef382be4` on the phone with auto-update enabled and UP_TO_DATE. That is not deployment of #2372. B1/B2 remain TIME_BUDGET; the last stored turn remains slow and correctness is UNKNOWN. No new turn, UPDATE_REQUEST, shell, model/weight/permission change or device mutation. **REDMI_UNVERIFIED**.

## Research

R-092 records *To Retain or to Adapt? Generalizing Continual Learning* (arXiv:2607.05609). It motivates a predictive replay-window ablation, complementing R-089 dense replay and R-090 stratified retention. The proposed experiment compares uniform, recency-window, predictive-window and stratified replay under matched budgets, stable/gradual/abrupt shifts and return-to-first-cohort, measuring ALE, invariant regression, revision latency, B1/B2 holdout utility, EMA deltas, restart/rollback and replay cost. Research-only; no code or weights reused.

## Next

Poll exact temporal CI on `50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b`. QA must rebind the lifecycle chain bottom-up to the actual `memory.py` bytes, then rerun staged/optimizer/integrated tests. Do not rebase #2372 until QA and Boss matrices are green. Then run the multi-shift replay/retention ablations. No user action is required.
