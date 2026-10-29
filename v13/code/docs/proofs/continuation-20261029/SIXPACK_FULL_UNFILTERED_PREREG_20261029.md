# V13 six-package full unfiltered cross-organ software review — 2026-10-29

Exact parent `13a964495e4d30b7bc7255da61e946d100bcff9a`.
This review-only branch changes no runtime/Canon source, cohort or weight.

## Review target
Re-run the **unfiltered** `python -m unittest discover -s tests -p 'test_*.py'`
on the latest integrated review chain after PRs #1157–#1162:
F1/F5 Euro-source equivalence, source lifecycle negatives, World-Model
four-route read-only comparison, current-session event discovery, Sleep
finite user delay, G13 finite scheduler boundary. All focused packages
have green pinned software CI with closed original raw.

## Pinned isolated environment and expected outcomes
- Ubuntu 24.04, Python venv, NumPy 2.2.6, torch 2.5.1+cpu,
  Transformers 4.44.2, PEFT 0.13.2, existing auxiliary deps.
  No model downloads or native GGUF calls.
- Preserve **every** test and error, no skip/exclusion/waiver.
- Existing historical Run34/Run37 native source preflight checks are known
  to fail `native_source_or_catalog_changed` because the registered
  historical `utility.py` blob differs from current production. Their
  original frozen source must **not** be rewritten to make this green.
  A full suite with those two inherited errors remains **RED**, even if
  no new regression appears.
- Record complete stdout/stderr, exit codes, installed package freeze,
  SHA256SUMS, Canon blob, privacy/diff checks and any new failures.
- No STEP2, B3 L1, Body-JEPA, LP3, World-JEPA, jepa_weight or Redmi gate
  promotion from this software review.
