# Core handoff — read-only turn-flow audit (2026-11-21)

## Scope
Adds a read-only Store consumer for one persisted turn. It correlates A5 PerceptPacket modalities, B1/B2 QueryPacket and OfferPacket telemetry, C4 FocalCycle/FocalItem consumption, C3 source-bound context references and C3 runner token/latency metrics. It also reports symbolic/tap evidence without upgrading it to native latent injection.

## Safety and evidence boundary
- Opens `brain.sqlite3` with SQLite `mode=ro` and `query_only=ON`; does not instantiate Runtime or acquire the live Store lock.
- Returns no user text, prompt text, body summaries, token IDs, raw audio or source bytes.
- Verifies SourceRef row, blob SHA-256 and character bounds without returning source content.
- Explicitly labels synthetic fixture metrics and leaves `native_injection_proven=false`.
- This is a local diagnostics consumer, not a Redmi test, native model benchmark, weight update, Android control, or release.

## Verification
- Exact tests are in `v13/code/tests/test_flow_audit.py`; GitHub Actions is the execution host.
- Required checks: Python 3.11 / 3.13 / 3.14 compile + read-only SQLite integration tests.
- Full local Aii checkout remains unavailable in this run because GitHub DNS resolution failed; no local Linux or Redmi test is claimed.

## Next integration
After review, expose the read-only report through the existing operator/dashboard diagnostics without modifying frozen Runtime bytes. Then use a fresh authorized private Redmi PIPELINE_STATUS/DIAGNOSTICS receipt to verify whether the installed turn actually delivered both B1/B2 offers through C4 into C3.
