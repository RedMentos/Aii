# BP2b pinned master local preflight verifier prereg · 2026-10-27

Owner: automation11 metadata path, follow-up to seven-file successful HF metadata Actions `40502634640` (raw ZIP SHA256 `b735e8c7718b97a275aec1eb44a74b23c9d71d5edffea65edd7fce2ec0116820`). Pinned lock file `v13/code/specs/bp2b_master_metadata.json` commit `ef0755a3494846b48c74aafe15a38d9e6f691abb` before this verifier implementation.

Goal: local **preflight only** for future native BP2b: compare seven small files byte-for-byte SHA256 and exact sizes to locked public revision, and (unless explicit metadata-only mode) stream/hash the full FP32 `model.safetensors` without loading it as a model. Reject missing, symlinked, tampered, extra/invalid pin schema, duplicate/nonfinite JSON, unexpected paths, incorrect model SHA, and immutable report overwrite. Report `METADATA_ONLY_PASS` or `FULL_FILE_HASH_PASS` only, never claim model execution or training.

Prospective software tests use synthetic tiny files and a synthetic valid-shaped pin to exercise both modes, corruption, symlink, duplicate JSON and refusal of mismatched model weights; no heavy native download. A separate pinned public metadata smoke may reuse already-verified artifact bytes. All gates unchanged. Exact test: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_master_preflight`.
