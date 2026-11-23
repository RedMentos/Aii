# ContextOS typographic literal preservation — verified RED → GREEN, 2026-10-30

Owner GPT-6. Review-only child of JEF #1238 exact parent `c21e180f1902029e1d27aea099728815764dd394`. Preregistration committed **before tests and source** `b9b9293fe1288070ddb7cc430164154676766f80`; test-only commit `2ebe9a08e28600ba05e05864d954b6e062c212cc`. Files: `context_os.py`, nine new synthetic exact-literal tests, pinned focused CI, scoped docs. No Canon, registered cohort, model/seed/source, runtime authority or Age rights change.

## Original RED preserved
GitHub Actions **41027991160**, exact tested HEAD `4bc4ac1c65f40b35b0cdf399d24e671e34b31941`, artifact **12964184114**, original ZIP SHA256 **`8b67ea4e071fb6ad7afb484f217e59fb3144a3afe3fda388a8f27e088505e205`**, CRC clean, **13/13 inner hashes**. **53 tests / 6 genuine failures**: balanced English curly double, French guillemets, curly single, curly contraction quote were not safely pinned/compressed; unclosed French/curly single lost exact RAW fallback. All VENV/DEPS/COMPILE/PRIVACY/DIFF exit0; TEST exit1. Original German quote, intra-word apostrophe and unclosed English controls passed.

## Minimal fix and verified GREEN
Source commit `9aa07923d30b8787cd480dd12d53804c29a7c580`, `context_os.py` Git blob `c515e9a432a1d912dab9cb551f74bb5f47d2e184`. Exact span extraction now recognizes balanced English curly double `“...”`, French `«...»` and curly single `‘...’`, including inner U+2019 contractions. Unmatched typographic quote delimiters force RAW; in-word U+2019 remains an apostrophe. German `„...“` is consumed before English `“...”` check to avoid conflating U+201C roles. Existing ASCII/German semantics and all prior ContextOS tests preserved.

GitHub Actions **41028141235**, exact tested HEAD `9aa07923d30b8787cd480dd12d53804c29a7c580`, artifact **12964437779**, ZIP SHA256 **`944710cb5af4b145dacda854a52b16c8b541203ff44755ece43072a48f622647`**, CRC clean, **13/13 inner hashes**, **53/53 PASS** in 1.280s, all six stage exits0, privacy CLEAN. Both original RED and GREEN ZIPs privately backed at `/V13-Checkpoints/2026-10-30/Run11I-ContextOS-Typographic/` and materialized byte-identical.

## Limits / next
Software/synthetic ContextOS exact-span regression only, no native model, Redmi, general semantic recall or learning improvement. Historical current-chain full unfiltered 3,698 tests / two frozen Run34/Run37 source-pin errors remain RED, not waived or rerun here. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE. No automatic merge.

**Exact rerun:** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_contextos_typographic_quotes_run11i tests.test_context_os_singlequote_exact_20261029 tests.test_context_os_unclosed_code_20261029 tests.test_context_os tests.test_context_warm_postverify_race_run11`.

**Next independent package:** review and integrate separately verified opt-in Body-JEPA EMA target evaluation candidate from branch `assistant/v13-bjepa-target-eval-run11-20261030-gpt6` only if exact source base blob matches, then run cross-organ focused tests on a new child. Owner GPT-6. Keep negative gates.
