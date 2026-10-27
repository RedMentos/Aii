# WP-Z12b independent review: reject invalid heldout action indices

2026-10-27 UTC. Review-only sibling of PR #751, child of PR #749 exact source `bfeee06983a9a3bf7a00fd525c036c234b429fb0`. Ownership: `assistant/v13-world-jepa-action-index-review-20261027`; only `world_jepa_heldout_ablation.py`, its focused test and review proof files. No World-JEPA model, source rows, model seeds, optimizer, runtime, learning gates, or existing measurements modified.

## Confirmed negative case before patch
Existing `score_model` checks `np.array_equal(A, np.eye(4)[action])` without first validating the action indices. NumPy negative indexing maps `action=-1` to the last action: a forged action index -1 paired with a valid action3 one-hot passes the equality check. An index >=4 instead raises `IndexError` rather than the declared controlled `ValueError`. Boolean/float/object index arrays have inconsistent indexing semantics. Verified NumPy negative-index behavior independently (no native model claim). This is a **research scorer integrity** defect; registered rows from the frozen generator contain valid indices, so original PR #749 measurements are not automatically invalidated.

## Fix contract and test
Before constructing `np.eye(4)[action]`, require action to be a 1D NumPy integer array (signed or unsigned, not boolean), exact length `len(X)`, all indices in [0,3]. Fail with `ValueError('Invalid heldout action indices')` for -1, 4, float, bool, wrong shape. Keep original correct-score and wrong-onehot behavior. Test against a small steps=0 WorldJEPA fixture to avoid model downloads and native claims. Do not change the registered source cohort, existing result hashes, training constants, or old evidence. New software-only review result must remain non-promoting; independent CI and full-suite review before integration.

Negative gates remain LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, V13 incomplete. Exact next command: `cd v13/code && python -m unittest -v tests.test_world_jepa_heldout_ablation`.
