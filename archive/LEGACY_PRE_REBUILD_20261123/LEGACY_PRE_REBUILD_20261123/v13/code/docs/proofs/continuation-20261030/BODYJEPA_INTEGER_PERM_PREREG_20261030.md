# Body-JEPA shuffled-target permutation integer-integrity — preregistration 2026-10-30

Base: PR #1171 verified checkpoint `0a153ec51a1ca13e84eb54b27e7974b9899868ae`. Independent Body-JEPA candidate branch; ownership: `v13/code/v13/body_jepa.py` derangement function only, new test, CI and proof/delta. No JEF files, Canon, native models, seeds, source artifacts or preregistered cohorts touched.

## Concrete failure mode
The bounded shuffled-target control currently does `int(v)` on every value returned by an RNG permutation. A malformed RNG returning fractional floats, numeric strings or booleans can be silently coerced into a valid derangement (e.g. [1.9,2.9,0.9] -> [1,2,0]), fabricating a supposedly valid negative control. This violates the identity of the shuffled-target ablation.

## Frozen checks
- Reject malformed fractional float, numeric-string and boolean permutation entries before any truncation/coercion; each must consume only one RNG draw and raise `ValueError('invalid RNG permutation')`.
- Accept Python ints and NumPy integer scalar permutations (as the existing real RNG produces); successful original draw sequence and 64-attempt cap unchanged.
- Reject duplicate/missing/fixed-point permutations exactly as before.
- Run existing `tests.test_bodyjepa_derangement_bound_20261029` and `tests.test_body_jepa` (latter needs pinned torch/PEFT), plus new tests, isolated CI, Canon SHA, privacy/diff, closed raw.
- This is a software ablation-integrity fix only, not a Body-JEPA learning utility or STEP6 gate promotion; jepa_weight remains 0 and all original negative gates remain.
