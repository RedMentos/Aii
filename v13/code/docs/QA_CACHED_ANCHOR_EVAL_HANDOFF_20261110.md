# QA cached anchor KL dropout and mixed-mode restoration — 2026-11-10

## Finding / severity
MEDIUM: `anchor_retention_kl()` compared a master reference generated in eval mode with an adapted model left in training mode. Dropout alone could create nonzero/noisy KL for unchanged weights. A read-only diagnostic also must not alter a model with mixed child training flags.

## Fix
`v13/code/v13/body_jepa.py`: run the adapted anchor forward under eval, use no_grad, validate nonempty integer token sequences, and restore all per-module train/eval flags in a finally block even if a later anchor or forward fails. This is a diagnostics-only patch, not a change to B1/B2 weight-learning authority or any Canon gate.

## Tests / evidence
`v13/code/tests/test_cached_anchor_eval.py`: four focused PyTorch tests: unchanged reference zero KL under high dropout; exception state restoration; invalid later anchor state restoration; nonzero KL on a changed projection. These four equivalent tests were run in an isolated local torch 2.10.0+cpu smoke harness: **4/4 PASS**. The exact repository test module has been committed but has NOT been run from a complete repo checkout. No GitHub Actions result or Redmi/Termux hardware proof claimed. GitHub DNS in the local container was unavailable; the GitHub connector was used to read/write the current branch.

## Branch dependencies and integration
Branch `qa/v13-anchor-retention-eval-20261110` is stacked on `qa/v13-heldout-mixed-modes-20261110` (PR #1680), which itself depends on QA PRs #1676/#1672 and must be reconciled with Body-JEPA work by Core. Do not merge this branch directly into stale main. All production code modifications are within QA's existing Body-JEPA retention ownership. Existing STEP2/JEPA/B3 negative gates remain negative.

## Next
Run the exact repository test and existing Body-JEPA suite in a checkout/CI; inspect any failures; coordinate a combined candidate with Core. Test model checkpoint, rollback and Termux memory after source integration. Audit other cached retention consumers for train/eval symmetry and long-lived anchor-cache RAM usage.
