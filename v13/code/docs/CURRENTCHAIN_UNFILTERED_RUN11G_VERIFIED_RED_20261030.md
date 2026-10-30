# Current review-chain full unfiltered software regression — verified RED, 2026-10-30

Owner GPT-6, review-only child of #1236 exact parent `8744720e30a28dd0c87247bd7a0e37a1f840bb4e`. No source/test code changes, no waived/skipped test selection, no Canon/model/source pin changes. This new full-suite check covers the C3 deterministic, JEF report and Context OS warm patches together; baseline #1227 was on a different earlier chain.

## Exact execution and result

**GitHub Actions 41025103796**, tested HEAD **`af6cfb2333cc2ce22ddb7f8c714d0c3f3f7d5113`**, artifact **12964200381**, original raw ZIP SHA256 **`8ca5ecdd9d836fa1ed3bdce04fa9dd016f6b370015dc02bba0279fef9d5936b3`**, 9,918 bytes, CRC clean, **32/32 inner hashes** independently verified. All 15 stages except FULL returned exit0: Canon0, original native ZIP fetch0, venv0, deps0, CPU torch0, transformers0, peft0, pip check0, three imports0, compile0, privacy CLEAN0, diff0. **FULL exit1**: unfiltered `python -m unittest discover -s tests -p 'test_*.py'` ran **3,698 tests in 385.578s, 2 errors, 14 skips**.

Both errors are the original historical frozen native source-pin failures:
- `test_run34_c3_native_quote_intervention_pilot.Run34NativePilotPreflight.test_pinned_source_model_runner_and_negative_gates`: `ValueError: native_source_or_catalog_changed`.
- `test_run37_c3_rule_use_native_pilot.Run37NativePreflight.test_pinned_source_model_runner_and_negative_gates`: same source-pin failure through Run34 prereg.

**No new full-suite errors observed** compared with earlier #1227, which ran 3,635 tests, 3 errors (two historical plus missing native ZIP), 14 skips on a different branch. This is not a full-suite GREEN and does not waive either original source-pin error. It is software regression evidence, not native model inference or Redmi proof.

## Exact missing prerequisite resolved

The earlier missing `v13/code/tests/NATIVE_40996792157.zip` was injected from **original** public Actions 40996792157 artifact 12951963045 (297,655 bytes, SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`, 54 entries, CRC clean, original HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`). The workflow obtained original bytes with read-only Actions permission, verified SHA256/CRC/HEAD before copying to the expected test path. No test fixture or scorer was modified. The original native ZIP and full-suite raw ZIP are privately backed at `/V13-Checkpoints/2026-10-30/Run11-CurrentChain-FullSuite/` and re-materialized SHA256 byte-identical.

## Workflow credential containment and next

After the tested run, workflow-only commit `bab9814f566de919c1378e86f0f168f457bee860` added `unset GH_TOKEN` immediately after the original artifact fetch, so later dependency installs/tests will not inherit the read-only Actions token; future reruns require an explicit branch-scoped trigger file rather than a workflow edit. **This workflow hardening was not itself exercised in Actions**; the exact tested full-suite head remains `af6cfb2...`, and no new full-suite result is claimed.

Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; whole V13 `INCOMPLETE`. No automatic merge.

Next: preserve historical Run34/Run37 source pins and investigate them only on a separately preregistered branch; continue substantive Body-JEPA opt-in target evaluation candidate on its isolated branch. Exact rerun command (with pinned prerequisites): `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'`. The workflow requires a new `v13/code/docs/CURRENTCHAIN_UNFILTERED_CI_TRIGGER_RUN11G.txt` change to start; never relabel this RED as GREEN.
