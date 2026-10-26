# Run424 — F4 valid-JSON forged PredictionOutcome source binding

Date 2026-10-26; owner GPT; review-only branch `codex/run424-world-receipt-source-binding-20261026`, stacked on Run420/PR418 exact status head `3346b200e149431d478f82e720a69d49ee6b9520`. Independent of Run421 native STEP2 owner and Run423 HX2. No frozen source/model/seed changes.

## Counterexample / RED-first
Run420 correctly tolerates malformed JSON but trusts syntactically valid PredictionOutcome observation IDs when rebuilding WORLD_STATE and when deciding if an authoritative completed action still needs observation. A forged packet with a nonexistent action ID is counted as an observed action. A forged valid JSON packet with an existing action ID and fabricated `observed` data can suppress `recover()` and make materialized state claim a false action outcome.

## Intended fix
Treat stored PredictionOutcome as a derived receipt, never as independent truth: cross-check action ID, event ID, actual persisted action outcome and status, source generation and fixed no-semantic-truth flags. Skip forged receipts in materialization and existing-packet dedup; preserve original raw bytes, recover a new valid sibling for an actual completed action. Avoid changing atomic ModulatorPacket+PredictionOutcome write ordering. Tests exercise forged unknown IDs and existing-ID outcome mismatch across restart, original valid receipts, and corruption retention. Preserve negative gates.

## Acceptance
Independent source-only GitHub Actions inherited world tests, new adversarial tests, privacy CLEAN, remote head and raw evidence verified. Not a native/Redmi/JEPA learning proof.
