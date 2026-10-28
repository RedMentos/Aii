# Prereg: safe TTY operator preflight for source-verified C3 query (2026-10-28)

Owner: isolated operator UX lane `assistant/v13-run11-verified-operator-preflight-20261028` from combined #905 source `4e24234b5c26df7438c5f9af1b23a38e9b2263e3`, combined full software evidence pending. No change to frozen `Runtime._turn`, C3 SourceConsumer, World-JEPA, ContextOS, model weights or original cohorts.

## Problem
The opt-in C3 source-bound budget lane is executable only as a separate `scripts/ask_verified_budget.py` CLI with explicit home/session/query flags. Users in the normal V13 TTY have no discoverable, model-free way to check whether an F1/F5 source is authorized for that question. Do **not** make normal chat silently call native C3 or trust unverified source.

## Bound implementation
- Add **`:verified <question>`** to the local TTY Operator help and command dispatch, as an explicit *preflight only*. Call the existing `scripts.ask_verified_budget.query(runtime, text, session=runtime.session, native=False)` rather than reimplementing admission. Require existing Age0/idle/queue/SourceRef/active-conflict gates. Preserve actual return status READY/CLARIFY/NOT_APPLICABLE; no new session, model load, tool call, training or approval.
- Reject `:verified native ...` and `:verified --native ...` in this new operator path. Native remains an explicit separately pinned isolated CLI pending a source-pinned operator-native lifecycle and deterministic user prohibition/standstill review. Do not imply preflight is an answer or native utility proof.
- Reject empty/oversized input and non-TTY origin; use existing `input_bytes` cap. Tests must show exact existing source yields READY with no native, missing/conflict/revoked yields CLARIFY, out-of-scope yields NOT_APPLICABLE, nonidle and native request fail closed, no session or model invocation, no mutation of Runtime._turn.
- Run focused Operator/C3/SourceConsumer and full software suite, compile, pinned Runtime/model/source hashes, privacy/diff and closed raw artifact. Independent audit and private backup before claiming GREEN.

Age0 RECORD_ONLY/SHADOW, `jepa_weight=0`; no original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi/full-system gate promotion. Next native TTY path only after separate prereg and real deterministic user rules/stop checks.
