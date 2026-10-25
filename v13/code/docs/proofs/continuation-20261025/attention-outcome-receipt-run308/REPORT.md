# Run308 — durable exactly-once F1/N5 Attention outcome learning: RED → GREEN

UTC 2026-10-25. Draft PR306, base verified Run307 checkpoint `c199935a94164ac2b07794ed0a5a8dcf92b6bb94`. Independent owner `attention.py`, new tests, CI and scoped proof only. No Runtime/Store schema, native/model, frozen Canon or cohort changes.

## Actual learned-policy defect
The N5 policy's `outcomes` list retains only the most recent 32 response IDs. In actual Runtime/Store SQLite, 34 distinct GRANTED AttentionResponse packets from the same event were each credited once; submitting the first ID again was accepted as outcome #35, changing the learned policy. Reproduced independently on extracted Run305 source. This can affect learned attention ranking after explicit ACTIVE mode, although no ACTIVE grant was made in these tests.

## Evidence
- Preregistration `90746099d8d067b452e364ca7da7793d2a964310`, RED tests `accaf11fa692c9a987799d044017090264a05486`, CI `a77053a93f771cb278570b594ee31cefafc9c893` all committed before source changes.
- **RED** exact source `a77053a93f771cb278570b594ee31cefafc9c893`, Actions `40206301157`: **49 tests, 3 expected FAIL** (old ID recredit after 34, recredit after restart, no durable concurrent receipt); other tests passed, privacy CLEAN. Closed raw artifact `12603224150`, SHA256 `19029fe1369cbda6bd26f91041575e1ddb71e5874bd1ffaf51b332d65c61dc45`.
- **GREEN** code commit `d64369c1d26dce0fa4f6d48a34e3118b14b1cd95`, `attention.py` blob `ff0856172546e6bdb3544dfa5fad8ae92931bf88`, Actions `40206365970`: **49/49 PASS**, privacy CLEAN. Closed raw artifact `12603598673`, SHA256 `6ec03de00a0b5b43d3d7056fb21f0cbd485110c4a81486a37d40e6242d604a46`.
- Fix: one existing `Store.tx()` atomically checks `ATTENTION_OUTCOME_RECEIPT:<response_packet_id>`, updates versioned N5 learned-policy state and inserts the receipt. Immediate duplicates and older IDs outside the bounded 32-item diagnostic cache now fail. Two concurrent calls yield one update and one refusal. Non-GRANTED responses write neither receipt nor policy. Receipts persist across restart. No new table or schema migration; public return shape, N10 modulators and SHADOW/explicit ACTIVE gate unchanged.
- Legacy limitation: response IDs evicted from the last-32 list **before** this change have no reconstructable receipt in the old schema, so historical exactly-once cannot be retroactively proven. New and still-visible legacy outcomes are protected.
- Raw RED/GREEN artifacts downloaded, SHA256SUMS checked, uploaded to private Library `/V13-Inquisition/Proofs/Run308/` and read back byte-for-byte with SHA256 parity. No rejected anyone-writable Drive destination used.

## Scope / next
Actual Linux SQLite learned-attention integrity, not measured native attention or model utility. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE` unchanged. PR306 remains review-scoped; main is older. Full-suite baseline `40202886433` still FAILED (2 failures, 36 errors).

Next: create a **new exact-head source-only Termux ZIP** that includes Run306–308 changes, independently verify member hashes/checkout byte parity, run extracted Age-0 setup and focused regression modules, persist private readback. Then continue substantive Canon utility/learning work outside these already fixed helpers; no false native/Redmi claim.
