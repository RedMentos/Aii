# P2 QAD ↔ HF structural tensor audit — isolated source-only candidate (2026-10-29)

Owner: GPT-6 isolated review child. Parent PR #1068, exact parent commit `100268d45a70ab7ad62757e55367bd0dbe147fb6`. This package implements the FIRST **source-only structural check** from the preregistered P2 plan. It is not a model experiment, a native parity result, an adapter training run or a production integration. No Canon, runtime `v13/code/v13/`, registered cohort, model pin, learning authority, approval gate or frozen evidence changed.

## Code and invariant

- `v13/code/scripts/p2_qad_hf_tensor_audit.py`: explicit pinned SHA256 of deployed QAD GGUF `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` and HF instruction master `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`. Hash both *before* parsing or optional GGUF imports. Reads safetensors header without loading model weights, GGUFReader tensor metadata, and existing `gguf.get_tensor_name_map` for the pinned architecture. Checks every HF tensor, mapping collisions, absent tensors, decoded shapes, and unaccounted GGUF tensors. Reports exact metadata hashes for `config.json`, `tokenizer.json`, `tokenizer_config.json` when files are present; null otherwise. Never activates or trains adapters.
- GGUFReader's `shape` contains GGML on-disk dimension order; compare to HF after reversal, following the upstream gguf reader implementation (ggml-org/llama.cpp `gguf-py/gguf/gguf_reader.py`, consulted 2026-10-29).
- `STRUCTURE_RED` on missing/unmapped/extra/mismatched/duplicate tensor metadata, malformed safetensors header, missing files, missing optional gguf dependency or wrong immutable SHA. `STRUCTURE_MATCH_PARITY_UNPROVEN` is **not** a passing parity gate. QAD tensor values, q/k RoPE transformations, tokenizer/chat template, native logits, adapter transfer, LP3 causal utility and Redmi remain unproven. Full HF↔QAD *semantic* parity requires separate preregistered native measurement.
- `v13/code/tests/test_p2_qad_hf_tensor_audit.py`: 10 source-only tests for happy structural mapping without parity promotion, shape orientation, missing/unmapped/collision/extra/nonweight tensors, header parsing and truncated header, pinned SHA refusal.

## Execution and evidence

Local isolated Python stdlib run: `python -m unittest -v /mnt/data/v13_p2/test_p2_qad_hf_tensor_audit.py` → **10/10 PASS** on functionally identical isolated implementation; this is not a test of the exact remote source tree. Exact-remote CI workflow `.github/workflows/v13-p2-qad-hf-structural-audit-20261029.yml` runs `python -m py_compile ...` and `python -m unittest discover -s v13/code/tests -p 'test_p2_qad_hf_tensor_audit.py' -v` on this review branch. Verify its exact head SHA and logs before claiming remote GREEN. No model files available in scratch, no native run, no 150-heldout use, no downloads or training. This package does **not** resolve QAD↔HF parity.

## Exact next commands / prerequisites

1. On review branch, verify remote blob SHA, CI exact head and `10/10 PASS`. Do not merge into production until independent review.
2. In a separately isolated, hash-bound Linux environment with pinned master and GGUF already verified, install compatible `gguf` and run:
   `python v13/code/scripts/p2_qad_hf_tensor_audit.py --master /path/to/pinned/hf-master --gguf /path/to/pinned/QAD-Q4_0.gguf --output /path/to/private/p2-structural-report.json`
3. Independently audit any missing/mismatched tensors and source-pinned tokenizer/config hashes. Even a clean structural report cannot promote parity; separately preregister fixed non-heldout probes, native QAD-vs-HF dequantized comparison and explicit tolerance/AG6 gates before training.
4. Continue disjoint JEF/Context OS/B1-B2/World/Dream canonical packages if model source or native availability blocks P2.

All gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi unmeasured, V13 INCOMPLETE. Public repository only contains generic source and hashes; no private data. No production merge or model/seed/cohort changes. Remaining platform budget UNKNOWN.
