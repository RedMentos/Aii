# T8 strict-floating-point arithmetic refusal — 2026-11-08

Owner: isolated review branch `codex/t8-strict-fp-errors-20261108`, parent PR #1600, source parent `9c9ab1d9579b03f28ed50554ea65b8f4a4ac34c5`.

## Finding
Latent residual squares and denominator squares were calculated before the nonfinite check. Under `np.seterr(over='raise')`, a finite but extreme matrix can raise `FloatingPointError` instead of the documented `T8_NONFINITE_LATENT_SCORE` refusal. This is a reproducible numerical risk from code inspection, not an executed regression result.

## Candidate
Wrap the residual/denominator calculation in a local strict NumPy error context and normalize `FloatingPointError` to `ValueError('T8_NONFINITE_LATENT_SCORE')`. Add a regression with a finite 1e200 latent coefficient and strict NumPy settings, asserting no FITTED state persisted. Does not alter normal finite metrics or gates.

## Verification limits and next commands
Source and test saved on a separate GitHub review branch. **Exact-checkout tests, privacy scan, independent review, native/Redmi execution NOT performed.** Direct container `git ls-remote` failed with `Could not resolve host: github.com`. Do not promote this candidate without execution.

`PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_world_model*py' -v`

`python v13/code/scripts/public_repo_privacy_scan.py --base 9c9ab1d9579b03f28ed50554ea65b8f4a4ac34c5 --head <candidate-head>`

Review entire #1595–#1600 chain, resolve historical full-suite RED separately, and continue functional C3/JEF/World-JEPA work. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE.
