# P2X candidate360 native launcher --lora-scaled CLI repair (2026-10-29)

Independent review-only child of P2X owner PR #1090 exact source `1aa13abec66eccd2df24942479e1194e826caa5e`. Do not edit or force-push owner branch. Scope only `v13/code/scripts/p2x_candidate360_standalone.py`, focused regression(s), corresponding owner test expectation, dedicated source-only CI and additive report. Canon, original frozen cohort, model/source/seed/adapter hashes, base/failed raw and negative gates remain unchanged. No production activation.

Observed original native failure: GitHub Actions 40872516890 exact head `1aa13abec66eccd2df24942479e1194e826caa5e`, artifact 12897095608, downloaded ZIP SHA256 `17204c9c08303e6c8fdeb5f36e4a469233d5dbb700cb550992113543d9e7fe3f`, CRC clean, 54 ZIP members, 53 inner SHA256SUMS entries verified with zero mismatches. The pinned binary started but immediately rejected argument: `error while handling argument "--lora-scaled": lora-scaled format: FNAME:SCALE`. Existing launcher sends three tokens `--lora-scaled <adapter> 1`, while exact runner expects a single `<adapter>:1` value. NATIVE_EXIT=1, SERVER_EXIT_RED, 0/360 calls; no quality evidence. Earlier native failures retained, no fabricated result.

RED-first: mock-owned server argv regression must fail on the original source (expects exactly one `FNAME:SCALE` argument, no trailing standalone `1`). GREEN: minimally repair argv construction, update legacy test to assert new contract, verify all existing source-only tests, full software suite, privacy and raw hashes. The pinned server binary SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39` remains unchanged. No native rerun while model/resource owner is active; a new source-bound Linux native 360-call run requires a serialized owner and independently audited exact adapter bytes, not this software proof.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi UNMEASURED, V13 INCOMPLETE.

## Exact source-only RED before repair

Actions 40875212641 on test-only head `ef6b98f94717acefdd115e7e4107321cc2fe3a51`: 31 focused tests, exactly one expected failure (`'synthetic-adapter' != 'synthetic-adapter:1'`), 30 PASS; original source pinned, compile/privacy/diff/FROZEN exits 0; full skipped as preregistered. Artifact 12896714713 ZIP SHA256 `50288cce4df400300baf67d4ac863f1400d30e7c367ba793be5045ef5b16ecd3`, CRC clean, 21/21 inner hashes. Original 360-call native failure remains 0/360; no rerun or utility claim.
