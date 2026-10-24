# Run46 — learned key-conditioned attention, synthetic positive

Preregistered at `53e9ced313aa40cced95510fc3121d787abf3616`, based on Run45 `f58877055b4abbb1e2475b85e625befd199c2bd8`. The previous Run44 generic transformer result remains **FAIL_SYNTHETIC** and is not overwritten.

**Hypothesis:** Run44's generic transformer detected value presence but did not bind the query key to its value. A trainable query/key/value embedding model with softmax attention (3,081 parameters, 300 Adam steps, fixed seeds 20261024/20261025) can learn the association on fresh synthetic pairings. Data are derived from Run44's staged synthetic JSONL; history provider remains a **mock**, not real V13 `native_history`.

**Predeclared result:** Heldout exact value accuracy **1.0000**; no-context **0.1055**, shuffled-value **0.4258**, uniform-attention **0.4258**, untrained **0.0547**. All preregistered synthetic thresholds passed. Three **post-hoc** independent heldout seeds 20261026–28 each yielded 1.0000 context accuracy, with shuffled .3516–.4141 and uniform .4453–.4844. Post-hoc results are corroborative only, not a new preregistered gate.

**Software checks:** 7/7 synthetic tests PASS, 7/7 Python -O PASS, compileall PASS. Offline hash-verified dependency bootstrap PASS. Raw metrics and both test logs are committed in `evidence/`. The local complete source/evidence archive has SHA256 `27ba33c9049b2df103204b20f64771e14de72ec32eb5cd5f470d1b56f6a31f45`. No actual V13 native model, real Runtime/Store, retention/rollback, or Redmi proof.

**Reproduce in full checkout:** From this directory, run `python scripts/bootstrap_vendor.py` (decodes the existing Run44 source archive and copies the already-persisted Run42 source with exact Git-blob checks), then `python -m unittest discover -s tests -v`, `python scripts/key_binding.py`, and optionally `python scripts/review_holdout.py`. Requires installed torch and numpy. No downloads, paid provisioning or changes to production weights.

**Claim limit:** This demonstrates a **toy associative attention learner**, not an LLM, JEPA, RSI, AGI or a completed V13 organ. It does not establish that C3 or either body can learn or retain such associations. All original gates stay STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.

**Next:** Independent full-checkout review and a real source-validated, rollback-safe C3/B1/B2 learning path with retention ablations. No production integration or Age-right promotion without its original proof gates. Ownership only this folder.
