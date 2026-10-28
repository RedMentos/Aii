# Run77 prereg — slot-wise World-JEPA ensemble mean semantics (2026-10-28)

Owner: GPT-6 scheduled continuation, isolated review candidate. Parent is Run76 PR #983 head `2fa443822f99b367d137f0254e69e20268f664e8`, **still CI-pending at preregistration**. This is not an acceptance or quantitative World-JEPA experiment. Run76's frozen source, kernels, cohorts, and registered results must remain byte-identical. Do not modify `world_jepa_slots_isolated.py`, `world_jepa_slots_kernels.py`, `world_jepa.py`, or prior raw evidence.

## Observed discrepancy / hypothesis

`SlotWorldJEPA.predict` says it returns the **mean prediction**, but computes an ensemble and returns `ps[0]`; the spread is computed over **all** ensemble members. That makes the reported prediction depend on the first member rather than the mean, while confidence describes a different aggregation. A separate, default-off subclass should return the actual arithmetic ensemble mean while retaining the original spread and preserving the single-member behavior. This is a source-level semantic correction, **not** evidence of better downstream prediction or utility.

## Frozen verification plan

1. New candidate only: `v13/code/v13/world_jepa_slots_mean_candidate.py`; no modifications to frozen modules. Revision distinct and explicit.
2. New focused test `v13/code/tests/test_run77_slotwise_ensemble_mean.py`: construct exact deterministic two-member predictors with outputs 0 and 2; assert legacy prediction 0, candidate prediction 1, both spread 1. Test order independence by swapping predictors; candidate invariant, legacy changes. Test one-member parity, `slot_errors` consuming the mean, and no monkeypatch of original class.
3. Optional small training smoke only if prerequisites available; any empirical improvement claim requires separate preregistered source-disjoint holdout and baselines.
4. Run `python -m unittest -v tests.test_run77_slotwise_ensemble_mean tests.test_run76_slotwise_isolated tests.test_world_jepa tests.test_world_model`, compileall, full software suite, privacy scan, `git diff --check` in source-bound CI. Preserve raw logs and exit statuses even on RED; pin exact source blobs after files exist.
5. If parent Run76 remains RED or unverified, candidate cannot be integrated; even if all software checks pass, do not promote STEP2/B3/Body-JEPA/LP3/jepa_weight, Age0 authority, native/Redmi or complete V13.

## Open question

Does the ensemble mean improve **heldout calibrated action-outcome prediction** over member-0 and fixed baselines on a new preregistered cohort? This package intentionally does not answer that question. No change to model downloads, external tools, or runtime authority.
