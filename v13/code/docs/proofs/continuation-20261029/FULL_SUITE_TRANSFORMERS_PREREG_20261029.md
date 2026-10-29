# V13 full unfiltered software replay — isolated Transformers dependency (2026-10-29)

## Frozen observation / parent
- Parent branch: `codex/v13-c3-stream-finalizer-20261029-auto10al`, exact parent commit `cdf5f48c5bacbca494674a2554e96bf1e4e8dc2b`; review-only, not main.
- Earlier full suite: Actions run `40957012351` on parent-of-parent commit `12c3c152a5a183f7dd3899761a62d964854f0a97`: 3285 tests, 6 ERROR, 11 skipped; exit 1. Four import errors: `ModuleNotFoundError: No module named 'transformers'` in synthetic LP3/BJ1 test modules. Two historical frozen source-preflight errors in Run34/Run37: `native_source_or_catalog_changed`. All six remain genuine original failures.
- Official CPU `torch==2.5.1+cpu` resolved the earlier missing-torch import errors; `transformers` was never installed. Original artifact: `40957012351`, ID `12933534420`, sha256 `c3abbd38acc66b12f4bb495849dd3faccbdca74e93286f6d4e3c6102e5dc826d` as reported by Actions.
- Current immutable Canon blob: `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

## Hypothesis and executable experiment
Install `transformers==4.44.2` in the same isolated Python 3.12 virtualenv with `torch==2.5.1+cpu`, `numpy==2.2.6`, existing software dependencies, then execute the **entire** unfiltered `python -m unittest discover -s tests -p 'test_*.py'` from `v13/code`. No skips, allowlist, exclusions, test source edits or modified historical pins. Record exact HEAD, pip freeze, install logs, `pip check`, torch and transformers import versions, raw unittest output, source/Canon Git blobs, compileall, privacy scan and diff check. Hash every raw file before uploading the artifact.

## Acceptance / expected limits
- Preregistered expectation: four missing-transformers import errors should disappear; new runtime failures are possible and must remain recorded. Historical Run34/Run37 `native_source_or_catalog_changed` are expected to remain RED and **must not be waived**.
- FULL stage returns nonzero for any failing test or import; workflow conclusion stays RED. Never claim a full-suite PASS if either frozen pin error remains.
- No production source, model weights, cohorts, seeds, Canon, Age0 rights, JEF/C3/B1/B2, STEP2/B3/Body-JEPA/LP3 or Redmi gate changes. This is Linux software evidence only.
- Original failures, artifact IDs and original raw remain retained. Record result and exact follow-on package in a new additive checkpoint.
