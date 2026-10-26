# Run420 — F4 WorldState durable PredictionOutcome corruption recovery

2026-10-26 · owner GPT · current-chain branch `codex/run420-world-packet-recovery-current-20261026`, stacked on Run419/PR415 at `3cd2b0359d04577cd24998cf41b59e86da46e69c`. No production merge or new native owner. Historical RED-first PR417 on older Claude world.py was closed/superseded to preserve the current 18,066-byte WorldState atomic PredictionOutcome+ModulatorPacket transaction; no regression to older 13,323-byte code.

## Reproduced defect

With the exact current `v13/world.py` blob `504c9f7fab013be04051adcdb3d67120b4fb4ddc`, a synthetic authoritative event and one malformed persisted `PredictionOutcome` row `{invalid` caused a real `Runtime(home)` restart to throw `JSONDecodeError`. The persisted raw packet was not maliciously removed; the unguarded `_refresh` `json.loads` and SQLite `json_extract` on malformed packets were the problem. This prevents usable persistent chat/world recovery even when other actions are valid.

## Scoped fix

Guard the two existing-outcome lookups and crash recovery SQL using SQLite `CASE WHEN json_valid(payload)`, requiring a typed `observation` and matching action id. In `_refresh`, parse each row strictly, skip invalid packets, retain their raw SQLite bytes, count only valid typed observation IDs and use the newest valid event for state. Invalid packet counts are logged without granting semantic truth or training reward. Keep the current atomic write transaction for ModulatorPacket+PredictionOutcome unchanged. RED-first regressions cover malformed JSON, valid JSON with wrong observation type, valid sibling recovery and repeated restart. Inherited world observation/recovery/atomicity tests must remain green.

## Claims and next

Source-only software test, not a native JEPA/Body proof. No registered model/seed/source cohort hashes changed, no Age/approval/learning activation, no unauthorized tools. STEP2 `UTILITY_FAIL`, B3 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi unmeasured, whole V13 incomplete. Verify exact-head CI and privacy; independently review SQL guard semantics and replay the original local corruption counterexample. Native S_s20 remains owned by Run418 Actions 40260347495, not this branch.
