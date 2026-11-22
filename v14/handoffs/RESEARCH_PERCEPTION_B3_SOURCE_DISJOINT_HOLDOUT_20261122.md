# Research/Perception handoff — B3 source-disjoint L1 holdout

**Date:** 2026-11-22  
**PR:** #2317 (DRAFT; stacked on #2313)  
**Code head:** `9c9d816a0c0892610f665ff0d0be9699868c9ff5`  
**Parent B3 branch head at stack time:** `9068cf9d2bcd9af7a432cdba8d8e87e80e730f13`

## Finding

The B3 L1 trainer previously performed a label-stratified split over individual paired examples. The paired capture code rejects duplicate exact source spans, but distinct spans/events can still share one underlying source SHA-256. Such examples could cross the train/test boundary, making the holdout non-independent.

This is an evaluation-validity defect, not evidence that a trained receiver already works.

## Implemented correction

- `_source_disjoint_split` groups all spans/events by the underlying source SHA-256 before stratification.
- Every source group is assigned wholly to train or test.
- A source group with conflicting labels is rejected.
- Each class needs at least four independent source groups; insufficient grouped data fails closed.
- Candidate manifests and reports persist the split policy and exact train/test source-hash groups.
- L0 evidence is now `v13.b3-l0-baselines/2`; it must pin the exact grouped split, source hashes, train/test indices, task labels, provenance and seeds. Old per-example `/1` evidence is intentionally rejected.

## Exact artifacts

- `v13/code/v13/b3train.py`
- `v13/code/tests/test_b3train.py`
- `v13/code/scripts/b3_train_l1_shadow.py`

## Verification

- Isolated Python helper smoke: **PASS** — 32 source groups × 2 spans produced 52 train / 12 test samples; no SHA crossed the split; conflicting-label negative control was rejected.
- Full LOCAL_LINUX repository suite: **BLOCKED** — this execution environment has no Aii checkout.
- Exact PR CI: **PENDING** at handoff creation.
- Redmi/Termux: **REDMI_UNVERIFIED**.
- No real paired tap training, independent L0 channel measurements, L1 utility pass, native receiver injection, permanent weight change, or old-session retention proof is claimed.

## Next action

After exact PR #2317 Python 3.13 B3 workflow passes, rebase the parent #2313 stack onto the current release-development base and rerun paired capture + L1 grouped-split tests there. Then obtain genuine source-disjoint paired taps and independently measured EXACT/CONTROL/SYMBOLIC baselines before any L1 gate. Keep candidate artifacts NOT_PROMOTED and all latent/receiver/body-learning authority at zero.
