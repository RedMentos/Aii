# JEPA / Memory run 13 — temporal target-anchor and receiver-order fix

Date: 2026-11-22
Lane: JEPA & Memory
Branch: `jepa-memory/v14-temporal-world-jepa-omission-20261122-run12`

## Defects reproduced from exact CI on the prior head

- `test_temporal_receiver_matrix_batches_bodyview_contract_with_single_readout_parity` returned `NONCONTIGUOUS_HISTORY` for valid synthetic sessions. The receiver sorted T8 rows by receipt timestamp and random action UUID, while the canonical event stream is ordered by `events.created,id`. Equal/coarse timestamps made those orders diverge.
- Replay/rollback tests hit retention or utility rejection. The old retention measurement called `prediction_loss` before and after an EMA update; because `prediction_loss` embeds the target with the *current* EMA target, the coordinate system moved during the measurement. That made before/after values incomparable and could reject a valid update for target drift rather than forgetting.

## Implementation in this commit

1. Bump the unshipped temporal state schema/revision to v2.
2. Persist a hash-checked fixed target-latent anchor with each accepted retention holdout.
3. Measure current and retained cohort prediction error against those same fixed EMA target coordinates before and after an update; use the same anchor for shuffled-target, shuffled-action and no-history negative controls.
4. Order B1/B2/SELF temporal receiver history by canonical event position, filter outside the bounded recent event window, reject multiple actions for one event, and return all selected history IDs for length-2/3 readout provenance.
5. Extend the A→B replay test to verify the old target anchor survives into the next accepted checkpoint.

## Evidence boundary

- The previous exact-head GitHub CI failed: temporal suite 2/8 and 3/8 tests; optimizer-resume suite failed in staged source composition; staged/integrated suite failed because the nested source-lifecycle builder still pinned an older `memory.py` SHA.
- This commit has not yet been run by GitHub Actions. No local full checkout is available in this environment (the prior CI/handoff records GitHub DNS resolution failure); LOCAL_LINUX full suite is BLOCKED/NOT_RUN.
- No Redmi/Termux test, no native GGUF weight update, no B1/B2 prompt consumption, and no deployment are claimed. REDMI_UNVERIFIED; NOT_RELEASED.
- The new receiver API remains SHADOW-only. Core #2343 owns `bodyview.py`; its current one-step adapter is separate. The temporal adapter call is `TemporalWorldJEPAStoreConsumer(store).receiver_matrix(session_id, actions, history_length=2|3, nonblocking=True)`. Core should consume it additively only after its own exact CI and preserve the fixed Context OS/B5 budget.

## Research note

R-087 (Zhou et al., arXiv:2611.25671) remains a conceptual comparator, not a dependency: source-completed transitions and action-conditioned evidence retrieval are relevant, but its visual-simulator/ViT/GRU/H100 setup is not an Android implementation; the paper text is CC BY-NC-ND 4.0 and no author-linked code/weight license was verified. Keep our EMA/retention path. Next research experiment: compare source-disjoint retrieved evidence against zero/shuffled/wrong-source controls on identical held-out sequences, then measure retention and latency.

## Next

1. Run exact Python 3.13/3.14 temporal and optimizer-resume workflows on this new head.
2. Inspect first failure rather than weakening gates.
3. Rebind the changed temporal/memory source through nested staged consumers if the exact source-pin regression remains.
4. Coordinate with Core to wire the temporal matrix into the actual B1/B2 bodyview SHADOW path.
5. Keep Boss #2355 promotion/rollback serialization and QA #2359 source-pin chain stacked; no merge or device update until all dependent exact-head checks are green.
