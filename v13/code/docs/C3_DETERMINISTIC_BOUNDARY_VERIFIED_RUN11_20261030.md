# C3 deterministic operator: single-question ambiguity regression — verified 2026-10-30

**Scope:** isolated review-only child of #1233, parent `10b3c8d01ff8ed55ba1bfcafd42a90be677a2c5b`. No changes to Canon, original seed83/109, registered model/binary/source hashes, `listarith.question_part`, `german.propose`, native path, ToolStep/C5, learning or runtime. Owner GPT-6; files owned: `v13/code/v13/agi/listarith_de_deterministic_source_candidate.py`, `v13/code/tests/test_c3_deterministic_boundary_run11.py`, new CI workflow and scoped docs only.

## Reproduced bug (original RED retained)

The narrow no-model operator requires one trailing question. The shared `question_part` intentionally concatenates trailing digit-free sentences, and the candidate parser checked only `endswith("?")`. Five preregistered sources with an additional unrelated question were **incorrectly emitted as `SHADOW_RESULT`** (all five failures). This was a real source-boundary ambiguity, not a native-model issue. Positive controls passed.

Prereg committed first `a3a2cb2e21f130465af295f2eaf277fafcce2772`; test-first branch commit `dcc6bc963dc211b7998d30d1b587d3d12c788253`. Original GitHub Actions **41023740411**, artifact **12962487441**, ZIP SHA256 **`c531cd3296a945e77d0c0f02afd659e430fc02e0e3b24d15ef5a5db86f84939e`**. CRC clean; **13/13 inner hashes verified**, exact HEAD `dcc6bc963dc211b7998d30d1b587d3d12c788253`. **40 tests: 5 expected failures**; VENV/DEPS/COMPILE/PRIVACY/DIFF exit 0, TEST exit 1. Raw ZIP privately saved at `/V13-Checkpoints/2026-10-30/Run11-C3-QuestionBoundary/C3_BOUNDARY_RUN11_RED_41023740411.zip`, re-materialized and SHA256 byte-identical. Original RED not overwritten.

## Minimal fix and verified GREEN

Opt-in deterministic parser now refuses a question block with more than one `?` or embedded `.` / `!`. Existing valid single-question syntax and all other operator modes remain unchanged. This is deliberately stricter than general natural-language handling. Source commit `7585b5aae83639d1eb2f23abd52e29d7e433fbf1`, parser blob `6e9680b5cd11136b5298a0e4f91b6599a94a1cf3`.

GitHub Actions **41023818735** at exact HEAD `7585b5aae83639d1eb2f23abd52e29d7e433fbf1`, artifact **12963165218**, ZIP SHA256 **`53f504ee1807df4cfe6904dd1ca6f054dcfab0c58301508a35aefc5a456e8f91`**; CRC clean and **13/13 inner hashes**, **40/40 tests PASS**, all six VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF exit 0, privacy **CLEAN**. Five previously wrong multi-question emissions now abstain; original eight frozen seed109 source examples remain correct; 40 seeded (seed117) novel narrow list variants (2..8 names, repeated/negative/edge integer values, sum and max-min) match deterministic Python values. No native model was invoked. Original ZIP privately backed at `/V13-Checkpoints/2026-10-30/Run11-C3-QuestionBoundary/C3_BOUNDARY_RUN11_GREEN_41023818735.zip`, re-materialized byte-identical.

## Status and next

**SOFTWARE_SYNTHETIC_SHADOW_ONLY**, not Linux-native or Redmi evidence, not general German parsing, not live C5/ToolStep authority. Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; whole V13 `INCOMPLETE`. No full unfiltered suite run here. Review PR remains draft, no automatic merge.

Next: independent review of this small diff against the one-question prereg and any potential false abstentions, then resume higher-priority JEF/Context OS/Body-JEPA end-to-end packages from current remote owner state rather than promoting this narrow utility. Exact rerun command (in repo root with Python deps installed): `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_c3_deterministic_boundary_run11 tests.test_c3_deterministic_operator_auto11 tests.test_c3_operator_bounded_input_auto11 tests.test_c3_operator_receipt_boundary_auto11 tests.test_c3_de_operator_shadow_run11g_20261030 tests.test_listarith_de_closedworld_seed101_20261030`. CI workflow `.github/workflows/v13-c3-boundary-run11.yml` reproduces the same checks and raw receipts.

**Stop reason for this package:** verified intermediate checkpoint only; remaining platform budget UNKNOWN, no full-system completion claimed.
