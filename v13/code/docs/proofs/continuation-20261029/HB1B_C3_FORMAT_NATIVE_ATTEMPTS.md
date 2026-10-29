# HB1b C3 format native review — attempt ledger (2026-10-29)

Owner: GPT-6 isolated review branch `codex/v13-hb1b-c3-format-native-review-20261029`. Parent PR #1055, first prereg `4b4978c4ed55b0397ca03ff930bf06477f8d5137`, addendum `136be8933f99962bcae6d1d41fb46a66f465f541`. No native HB1b model call yet; no original HB1a score change.

## Source-only attempt 1 — RED retained

- GitHub Actions run `40837864810`, exact head `63beed0864d69a7894c0347f5d8466f70702d741`, artifact `12880968679`, ZIP SHA256 `c804f7337b57746f7f92901ca8bf0b63465266f95aa6fdc5fc652f789563b303`.
- Source pins, dependency installation, compilation succeeded. Focused tests: **17 PASS / 1 FAIL**. The mock `FakePool` deliberately emits JSON `{"action":"UNKNOWN"}` for C3, but the new test incorrectly expected two exact `NONE` outcomes for `exact_schema`. The production plan/scorer and model were not involved; no native calls.
- Original ZIP independently downloaded, CRC CLEAN, **5/5 internal SHA256SUMS valid**. Permitted private Library backup `/V13/RawEvidence/HB1B_40837864810_native_source_mock_RED.zip` rematerialized and byte-verified against original ZIP SHA.
- Corrected test expectation in commit `c805bfec6241c02fb476a09e30cfc2019242d576`, then repinned exact source-only workflow in `43321c26b77d26655ec286fb465ab434252613d8`. No source/seed/model/Canon change, no force-push.

## Next

Wait for corrected source-only CI exact head, independently verify original artifact and parent PR #1055 source CI. Only then create/run the separate pinned 24-call native workflow. Native result remains unknown. All gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE; Redmi unmeasured.
