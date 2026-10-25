# Run308 — F1/N5 learned Attention outcomes need durable exactly-once receipts (2026-10-25)

Owner GPT-6 automation, independent review branch from verified Run307 checkpoint `c199935a94164ac2b07794ed0a5a8dcf92b6bb94`. Own `v13/code/v13/attention.py`, new `tests/test_attention_outcome_receipt_run308.py`, dedicated CPU CI and this proof. No Runtime/Store schema, native, model, Canon or registered cohort changes. Respect Run303 Budget and Run297 native owners.

## Actual defect

`Attention.outcome(response_packet_id, usefulness)` checks idempotence only against the last 32 response IDs in a per-key list. After 34 legitimate outcomes for the same (reason,target), an old response ID falls out of that window and can be submitted again. Actual Runtime/Store SQLite reproduction: 34 GRANTED responses, 34 outcomes, replay the first response → accepted as observation #35, changing the learned mean and potentially ACTIVE attention ranking. This is repeated evidence, not a new result.

## RED-first acceptance

1. 34 real granted AttentionResponse packets with distinct IDs, same learned key, recorded exactly once. Replaying the oldest ID must fail closed; learned count/mean and authority must remain unchanged. Original code is expected RED.
2. After Runtime/Store restart, the same old ID must still be rejected (durable receipt).
3. Two concurrent attempts to report one granted response must yield exactly one successful learning update, one duplicate refusal; no lost or doubled count.
4. Existing immediate-duplicate test, attention request budget, source/teacher gates, neuromod and SHADOW/explicit ACTIVE controls remain unchanged. The last-32 outcomes list may remain as a bounded diagnostic view but must not be the only idempotence ledger.
5. No arbitrary authority, source deletion, model training, age promotion, native/Redmi proof or gate change.

Candidate after RED: in one `Store.tx()` transaction, atomically verify absence of a durable per-response receipt under `states`, update the existing N5 policy state/version and insert the receipt. Check the legacy last-32 list too, to avoid re-crediting still visible pre-upgrade outcomes. Preserve `Attention.outcome` public return shape, log/modulator behavior after a successful commit and original revision. Historical evicted IDs before the new ledger cannot be reconstructed from existing bounded state; document that limitation instead of inventing proof.

Claim limit: actual SQLite learned-attention idempotence only, no native model or measured utility. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE` unchanged. Exact next command: commit RED tests+CI, observe failures, implement atomic receipt, run original Attention/Neuromod tests and privacy, preserve raw RED/GREEN and remote checkpoint.
