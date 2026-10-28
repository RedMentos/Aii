# Run80 prereg — Claude independent review full-suite optional restore path (2026-10-28)

Owner GPT-6 scheduled continuation; review-only child of Claude independent review PR #982 exact head `f0a78f3c8434cbe14f874643cb486743bdb56b7a`. Original Run75 CI 40779726227 RED: focused slotwise 12 PASS but full suite 1774 tests had one PermissionError in historical `tests.test_toolforecast.CheckpointTests.test_competence_check_scores_states_not_calls` when checking optional `/root/native/restore/round8-note-tool-raw`. Original RED raw ZIP, hashes and prior claims must remain unchanged.

## Fixed correction plan before code

- **Test portability only**: no runtime/model/Claude slotwise code changes, no tampering with original proof, no user private data.
- The optional restored historical evidence probe is not a required prerequisite for the synthetic `cc.analyze(rows)` assertions. Replace its direct `Path('/root/native/restore/round8-note-tool-raw').exists()` with a tiny helper that returns False when the OS refuses metadata access (catch `OSError`), preserving the original plan checks when the path is actually accessible.
- Add independent regression that monkeypatches `Path.exists` to raise `PermissionError` and asserts the optional probe refuses cleanly; when `Path.exists` returns True, helper returns True. Do not weaken any `cc.plan` or `cc.analyze` validation.
- Source-bound CI: pinned changed test/helper SHA, focused test_toolforecast and new regression, original Claude Z12c slotwise tests, full suite, privacy and raw SHA256SUMS. Original historical RED preserved; GREEN only after exact source CI and independent raw audit.
- Claim limit: a portable historical unit test is not Claude Z12c quantitative reproduction, JEPA utility, native/Redmi proof, or full V13. All Age0/STEP2/B3/Body-JEPA/LP3/jepa_weight negative gates remain.

Next after GREEN: independent review of Claude Z12c source claims C1-C7 (C5 per-query pairs still missing), and compare with isolated Run76-79 candidates; no merge into Claude-owned branch without review.
