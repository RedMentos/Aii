# Run163 — independent FP32 export cross-audit (2026-10-25)

Owner: Codex Run163; new script/test/workflow/proof only. Base: Run162 head `001e7af6748186b4c1c21ad357a06680079aef44`. No modifications to Run160/161/162 sources, frozen Runtime, model manifests, Canon, or registered cohorts. Heavy native owner: NONE acquired; no heavy native jobs launched.

## Problem / adversarial counterexample
Run162 checks `np.array_equal(z[name], arrays[name])` and calls the roundtrip `BYTE_EXACT_FLOAT32_VALUES`. This is a numerical equality test, not a byte-equality test: IEEE-754 `-0.0` and `+0.0` compare equal but have different binary representations. A local synthetic adversarial fixture reproduces `np.array_equal(changed, original) is True` with different bytes. This is an **integrity claim gap**, not evidence of a corrupted actual B1 export. Additional potential ambiguities: two selected F32 descriptors can point to the same source span; an NPZ may contain extra entries or an unverified manifest.

## Candidate
`body_fp32_export_verify_run163.py` is a separate, **read-only** verifier. Caller must provide an independent 64-hex model SHA. It rehashes the complete GGUF, re-parses bounded GGUF v3 metadata, verifies Run162 report/master digest, bounds and disjointness of selected F32 vector source spans, ZIP entry names and sizes, finite dtype/shape, and exact `array.tobytes()` vs original source bytes. Rehashes source and NPZ after reading. No output weight bytes, writes, gradients, training, EMA, requantization, Runtime authority or gate promotion.

## Local closed evidence
Environment: scratch Linux Python 3.13, NumPy 2.3.5; Run160 parser reconstructed from exact remote source, Git blob `a9195600f34bc5c7384de05e12fda0c51d78dded` (local reconstruction blob matched). Source and tests local:
- `v13/code/scripts/body_fp32_export_verify_run163.py`: Git blob `c9542d9eb1aaa62d685d12588eac94eaba930b49`; SHA256 `22f16aa02d15d5e74613d7d38d55a550b35234b1bd2b0f3d08fd50627031d81a`.
- `v13/code/tests/test_body_fp32_export_verify_run163.py`: Git blob `d3e2d28513097b83e5281f7fefbf833033491d7e`; SHA256 `c5f803ecc2489293584c03c6317e686350b44d4238bb7f8e80091fb4f89db35b`.
- `PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p test_body_fp32_export_verify_run163.py -v`: **11/11 PASS**, raw log SHA256 `b53e2240e5a8e35d8e6b34e037765b7de60bbafecf6d17a4bc78488042503e2f`.
- `python -m compileall -q` on new script/test: PASS.
- First local test attempt ERROR because inherited Run160 source was absent in scratch; retained in local checkpoint; after exact-source reconstruction 11/11 PASS. Full checkout CI remains required.

## Primary sources (accessed 2026-10-25)
- ggml-org GGUF v3 specification: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md (relative tensor_data offsets, alignment, F32 enum).
- NumPy array_equal: https://numpy.org/doc/stable/reference/generated/numpy.array_equal.html (element-wise numerical equality, not raw-bit equality).

## Gates / claim limits
`STEP2=UTILITY_FAIL`; `B3_L1=FAIL`; `Body_JEPA=UNAVAILABLE`; `jepa_weight=0`; `DS2_H2=FAIL`; `V13=INCOMPLETE`. This only validates **selected** F32 inference vectors; it does not prove that unselected tensors are nonoverlapping, that the NPZ is trainable, or that actual B1 weights have been extracted. No native/Redmi evidence.

## Next
1. Confirm full-checkout CI 11 Run163 + 10 Run162 + 8 Run160 tests, compileall, official privacy CLEAN. Preserve failures.
2. Cross-review source/report ambiguity and selected tensor metadata; do not merge without independent review.
3. Schedule private, serialized real B1 extraction only after exact registered full-file SHA preflight, model artifact prerequisites and ownership are rechecked; keep weights private.
4. Investigate Run159 full-suite CI failure independently; no unrelated blockers should stop other canonical work.
