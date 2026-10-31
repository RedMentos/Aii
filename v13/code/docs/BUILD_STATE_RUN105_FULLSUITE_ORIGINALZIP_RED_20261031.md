# BUILD_STATE — Run105 unfiltered current Run104 review chain original-native-ZIP full-suite RED, 2026-10-31

Owner GPT-6 automation11. Review-only child of Run104 PR #1475 exact parent `35113fc42f0b4594ca46ef33194877b8e277054f`. Prereg `97e976d8fdc74afede4a9423a5adc8e202edd87e` before workflow. Exact tested HEAD `4a668e1c3905b4206db99c1ab791e1b059b1a464`. **No source/runtime/test changes in this branch**; only prereg, workflow and trigger. Do not call this GREEN.

## Original terminal evidence — preserve RED

GitHub Actions **41209579681**, job `124561560070`, terminal **FAILURE**: **4,893 tests in 266.285s, 5 FAIL, 64 ERROR, 28 skipped**, `FULL_EXIT=1`. All prerequisite stages VENV/DEPS/TORCH/TRANSFORMERS_PEFT/PIP_CHECK/ORIGINAL_PINS/COMPILE/PRIVACY/DIFF exited **0**; privacy CLEAN. Original pinned STEP2 artifact `12951963045` SHA256 `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46`, 53/53 inner hashes verified; original Run13T artifact `12996917793` SHA256 `86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c`, 39/39 hashes verified. Pinned deps include numpy 2.2.6, CPU torch 2.5.1, transformers 4.44.2, peft 0.13.2; no model download or native model execution.

Original RED artifact `13045368441`: **341,411 bytes**, SHA256 `e72eaa90363e3d605e239b6c8d6478be570b352d79bc257ba33ffee46f29453d`, ZIP CRC PASS, **23/23** inner SHA256SUMS PASS. Original independently downloaded and private Library re-materialized byte-identical at `/V13-Checkpoints/2026-10-31/Run105-Fullsuite-RED/ORIGINAL_RED_ACTIONS_41209579681_SHAe72eaa90.zip`. No retry has overwritten the failed raw.

## Failure taxonomy and strict boundaries

Five top-level FAIL include **3** historical `test_package_source` extracted sub-suites (frozen source-handoff and native-firing candidate expected to execute on changed live Runtime), **1** `test_eligibility_fixed.test_chain_link_is_live`, and **1** `test_run83_native_driver_fake_c3` (fresh runner lacked installed pinned C3 model, report `STRUCTURAL_RED`/`Unavailable`, native calls zero; this is not a positive native test). Top-level ERROR classes include historical source-handoff (11), native-firing (17), rule-transport ablation (6), source-handoff ablation (4), merged firing (2), frozen Run34/37 and several B2/quote/chain-link cases. Embedded subtest tracebacks in the original raw mean naive `ERROR:` grep counts exceed the terminal 64; **terminal 64** is authoritative. Source guards correctly reject changed live source rather than silently treating it as the frozen candidate. Independent extracted-phone local `test_package_source.py` also failed 3/6 with exact source-mismatch guard messages; no promotion.

Run94 original-ZIP 4,907/28-skip GREEN at older exact HEAD is a **different divergent review branch**, not evidence that this HEAD passes. Do not weaken frozen source hashes, silently skip historical tests, or rewrite registered cohorts to turn RED green. Current bounded phone Run104 21/21 and Run107 pinned tar compatibility remain **separate focused GREEN**, not an unfiltered acceptance.

## Next exact actions

Run106 preregistered forensic child `assistant/v13-run106-frozen-candidate-scope-20261031-auto11` at `a837767e1dc93828a939d03c5f8694c197a45373` before this terminal audit. Update its evidence matrix with actual Run105 failure categories; verify original frozen baseline/candidate tests in their exact historical source where available and require explicit fail-closed current-source rejection plus current portable Run104 functional smoke. Never blanket skip or infer native quality. Separately identify genuinely missing prerequisites (e.g. Run83 pinned C3 model) and rerun only with exact authorized artifacts, preserving original failure. Next command for review: `python3 -m zipfile -t ORIGINAL_RED_ACTIONS_41209579681_SHAe72eaa90.zip` then inspect `FULL_RAW.log` and `FULL_EXIT.txt`; do not edit original ZIP.

Age0 RECORD_ONLY; STEP2_EXIT EVIDENCE_NOT_PASSING; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; full V13 INCOMPLETE. No merge/production promotion. Remaining platform budget UNKNOWN.
