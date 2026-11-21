# Core handoff — read-only turn-flow audit (2026-11-21)

## Scope
Adds a read-only Store consumer for one persisted turn. It correlates A5 PerceptPacket modalities, B1/B2 QueryPacket and OfferPacket telemetry, C4 FocalCycle/FocalItem consumption, C3 source-bound context references and C3 runner token/latency metrics. It also reports symbolic/tap evidence without upgrading it to native latent injection.

## Safety and evidence boundary
- Opens `brain.sqlite3` with SQLite `mode=ro` and `query_only=ON`; reuses AndroidControl's exact parent/ancestor policy (including the narrow AOSP /data alias and 0771 exceptions), opens the final DB with O_NOFOLLOW, rejects symlink/hardlink DB files, and checks the DB inode before/after SQLite opens it. Cross-UID path replacement is constrained; malicious same-UID races remain out of scope. It does not instantiate Runtime or acquire the live Store lock.
- Returns no user text, prompt text, body summaries, token IDs, raw audio or source bytes.
- Verifies SourceRef rows, blob SHA-256 and character bounds without returning source content.
- C4 only counts an OfferPacket when the matching FocalItem retains that offer's valid source evidence; an ID-only match is insufficient.
- C3 separates `context_binding_status` from semantic-use status. Source-bound context alone is never called a successful semantic consumption; a runtime-reported use flag remains explicitly not independently verified.
- Explicitly labels synthetic fixture metrics and leaves `native_injection_proven=false`.
- This is a local diagnostics consumer, not a Redmi test, native model benchmark, weight update, Android control, or release.

## Verification
- Exact tests are in `v13/code/tests/test_flow_audit.py`; the existing V13 additive and integrated-regression workflows execute them.
- The additive workflow compiles the new module and test, then runs the exact test file in its configured Python environment.
- LOCAL_LINUX_ISOLATED: helper-path checks PASS for read-only open, symlink/hardlink rejection and writable-ancestor rejection. Exact current-base CI also verifies the live-Store-lock read path; this is synthetic SQLite, not Redmi.
- Full Aii checkout/exact repository test suite remains BLOCKED because GitHub DNS resolution failed in the local container. This is not a full-repository local PASS.
- Redmi/native proof remains REDMI_UNVERIFIED.

## Usage and next integration
From the active Termux runtime, read the current session ID with `:status`, then run from the repository's `v13/code` directory (or with `PYTHONPATH=v13/code`):

```bash
python -m v13.flow_audit --home ~/v13 --session-id <SESSION-ID> --compact
```

An optional `--event-id <EVENT-ID>` is an explicit local selector and is deliberately not session-scoped when used alone; if `--session-id` is also supplied, a mismatch is hidden as not-found. `--session-id` remains mandatory for latest-event selection. The operator/dashboard command is not wired because doing so would require changing hash-pinned existing modules and a separate Boss-reviewed stage/deployer re-pin. Next: review the additive PR, then use a fresh authorized private Redmi PIPELINE_STATUS/DIAGNOSTICS receipt to compare actual persisted B1/B2 → C4 → C3 evidence. No private relay receipt was available in this run.
