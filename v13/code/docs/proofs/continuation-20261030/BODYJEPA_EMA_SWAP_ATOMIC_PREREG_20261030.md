# Body-JEPA EMA swap entry exception-atomicity — preregistration 2026-10-30

Base: PR #1173 verified checkpoint `4b3ebeec764a494597b3349c6e59f0404ae2ba97`. Independent review-only Body-JEPA integrity child, sibling to combined full-suite PR #1174. Ownership: `v13/code/v13/body_jepa.py` EMA swap context only, new focused test, CI, prereg/delta. No frozen cohorts, seeds, model/source artifacts, Canon or existing evidence changed.

## Concrete failure mode
`EmaAdapter.swap().__enter__` copies EMA shadows into trainable student tensors sequentially. If a later shadow has incompatible shape/device/dtype or an unexpected copy error occurs, `__enter__` raises before Python calls `__exit__`. Previously copied student tensors remain overwritten with EMA values. This can corrupt training or make later native evidence untrustworthy.

## Frozen behavior and checks
- Before copying any student parameter, validate complete shadow/parameter count, shapes, devices and dtypes. Reject mismatch without changing a single student tensor.
- After taking complete snapshots, if any copy raises unexpectedly, attempt to restore **all** original student tensors under no-grad and re-raise the original exception if rollback succeeds; if rollback itself fails, raise an explicit rollback-failure error rather than pretending state is intact.
- Successful swaps and exceptions *inside* the context must continue restoring student parameters exactly; EMA shadow and optimizer state unchanged.
- Focused tiny-torch tests: later-shadow shape mismatch, injected second-copy exception with successful rollback, successful entry/body-exception restoration, existing `test_body_jepa`, `test_bj1_input_integrity_20261027`, and shuffled-target controls. Pin torch 2.5.1+cpu, PEFT 0.13.2, Transformers 4.44.2, NumPy 2.2.6; retain closed raw, SHA256SUMS, Canon/privacy/diff.
- No actual body native training, no learned utility claim, no Body-JEPA/STEP2/B3/LP3 gate promotion, jepa_weight=0.

## Open
A real device process kill mid-copy is outside Python exception handling; this software guard is not crash-atomic at OS level. Native/Redmi tests remain required.
