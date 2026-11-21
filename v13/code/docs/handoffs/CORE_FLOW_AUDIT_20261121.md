# Core handoff — read-only per-turn organ-flow audit (2026-11-21)

## Scope

Adds a read-only Store consumer for one persisted turn and exposes a bounded projection in the existing local WebView. It correlates A5 PerceptPacket modalities, B1/B2 QueryPacket and OfferPacket telemetry, C4 FocalCycle/FocalItem consumption, C3 source-bound context references, C3 runner token/latency metrics, C5 ActionOutcome and B3 tap/symbolic/receiver evidence.

## Selection and privacy

- The dashboard selects the latest completed assistant turn across all chats; it does not claim to represent the currently open chat. The selected event is then audited against its own actual session.
- SQLite access is read-only and query-only, with the shared AndroidControl parent-path policy and final database O_NOFOLLOW/owner/link/inode checks.
- Returns no user text, prompt text, body summaries, token IDs, raw audio, event/session/source IDs, source hashes or source bytes.
- C4 counts an OfferPacket only when the current FocalCycle and matching active FocalItem retain the exact valid source evidence.
- C3 separates source-bound context from semantic-use status; context binding never proves model attention.
- Synthetic fixture metrics are labeled SYNTHETIC_FIXTURE; native injection remains explicitly false.

## Tests

- Exact test files: `v13/code/tests/test_flow_audit.py`, `test_flow_audit_dashboard.py`, and the dashboard click-target test in `test_mobile_dashboard.py`.
- Dedicated CI also compiles the Python and checks inline JavaScript syntax.
- Local full checkout is blocked by GitHub DNS in this environment; no local repository suite is claimed.
- No Redmi receipt or installation is available; REDMI_UNVERIFIED / NOT_RELEASED.

## User-visible access

Open the existing local V13 dashboard and select **Organdurchlauf prüfen**. The result is explicitly labeled as the latest completed turn across all chats. The standalone CLI remains available with an explicit `--session-id`; it is not required for the dashboard flow.
