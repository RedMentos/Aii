# Seed61 original native artifact independent audit prereg — 2026-10-30

Owner: `assistant/v13-seed61-independent-raw-audit-20261030-0635`, review-only child of PR #1216 at `d1bc56ba6c77c19c9e9ddc71595424df4dc3a548`.

## Frozen inputs, no rerun
- Original native run 41007813416, exact head `5ac90444fe2e0317a954cb4ed94730900b33d92c`, artifact 12955848461, original ZIP SHA256 `5296bf6bdf9fda8ac2c2b95ec9b73e10a1a1eb53574038c803a9d3ac12c55ad1`. CI RED (malformed here-doc), ZIP has 24 raw rows but no SHA256SUMS.
- Corrected-workflow native run 41008162051, exact head `45624d16f53cad1ae95e3a5cfc5a7467f32d527c`, artifact 12956867267, original ZIP SHA256 `dd7d00dc04a82180171bc3d1739bb21cd53ead7d3a05e26e4e6ac3b2b8e8556a`. CI RED (independent REPORT_CHECK assertion at inline Python line 61), ZIP has 24 raw rows and SHA256SUMS. Do not rewrite the original.
- Corrected source-only preflight 41008170038 GREEN; separate from native evidence.
- Frozen seed61 fixtures/scorer/source/model pins and original seed53/59 failures are not to be edited.

## Hypothesis and verification
The inline verifier compares the original Python `score_pair()` object with a JSON-deserialized persisted score using `==`. Its `equation_diagnostic()` produces lists of **tuples**, which JSON serializes as lists; a correct equation makes structural equality false without a semantic scoring change. This hypothesis must be checked with a negative test (changed numeric result must still fail) and against the exact original ZIP. Do not silently waive other raw checks.

Implement a standalone standard-library, **read-only** ZIP auditor with fixed original ZIP hashes, duplicate/path/CRC/manifest integrity, stage exits, all 24 source/event/score/flag bindings, PID-bound post-close receipt checks and negative gate checks. Preserve each RED stage and distinguish native rows generated from validated full experiment. Include a JSON-roundtrip score comparator and unit tests for tuple/list equivalence versus changed values. Optionally perform exact-source frozen scorer replay in CI; any replay mismatch is RED, not corrected by rescoring.

## Acceptance and claim limit
Pass focused software tests, verify original artifact bytes and independently inspect all 24 rows. The native workflow stays RED until its complete original verifier passes; a posthoc auditor is evidence review, **not** a replacement success. No STEP2, B3, Body-JEPA, jepa_weight, age, Redmi, or whole-system promotion. No live tools or new model runs. Checkpoint source, tests, raw audit, hashes and exact next command on review branch, no auto-merge.
