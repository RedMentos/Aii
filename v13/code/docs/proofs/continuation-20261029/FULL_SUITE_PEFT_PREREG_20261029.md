# V13 isolated PEFT full-suite dependency experiment — preregistration (2026-10-29)

## Parent and immutable observations
- Exact review parent `abb1c978409d613f814154580c5ff8b621d335d4` from PR #1151 branch, not production main.
- Independent byte-verified original Actions `40957012351`: 3285 tests / 6 ERROR / 11 skipped; original ZIP sha256 `c3abbd38acc66b12f4bb495849dd3faccbdca74e93286f6d4e3c6102e5dc826d`, CRC clean, 22/22 SHA256SUMS, private byte-exact backup.
- Correct error split: 3 `transformers` import errors (BJ1 checkpoint fit + two LP3 test modules), 1 `peft` import error (`test_body_jepa.MinorSubspaceTests.test_wide_and_tall`), 2 frozen Run34/Run37 source/catalog preflight errors. Original raw and correction report retained. The `transformers==4.44.2` experiment Actions `40958983649` was in progress at preregistration; no outcome is assumed.
- Official PEFT v0.13.2 tag `huggingface/peft` setup.py specifies `torch>=1.13`, `transformers`, `accelerate>=0.21`, `huggingface_hub>=0.17`, `safetensors`. No model download is needed for synthetic GPT2 tests. PEFT v0.13.2 source license Apache-2.0. Source: `https://raw.githubusercontent.com/huggingface/peft/v0.13.2/setup.py` (accessed 2026-10-29).

## Registered experiment
- Fresh Ubuntu 24.04 isolated Python 3.12 venv; install `numpy==2.2.6`, existing basic software dependencies, official CPU `torch==2.5.1+cpu`, `transformers==4.44.2`, `peft==0.13.2`. Record resolved `accelerate` and all other transitive dependencies in pip freeze; `pip check` must pass.
- Run the **entire unfiltered** `python -m unittest discover -s tests -p 'test_*.py'` from `v13/code`, with no excludes/waivers/skips added and no test/source/seed/model/cohort modifications. Record exact HEAD, source/Canon blobs, imports/versions, raw test output, compileall, privacy scan and diff check; hash all stage files and upload original raw on failure as well as success.
- Prediction: missing-peft error should be resolved. New PEFT/HF compatibility failures may appear; they are genuine and must be retained. Run34/Run37 frozen pin failures must remain negative and never be waived. No whole-suite PASS until all tests genuinely pass.

## Limits and gates
This experiment is Linux software/synthetic HF-only. It is not real Body-JEPA or LP3 gain, not Linux-native LFM2, not Redmi, not B3/STEP2 utility, not permission to activate AG6. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, V13 INCOMPLETE.
