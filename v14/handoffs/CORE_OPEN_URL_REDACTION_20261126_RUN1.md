# Core & Harness handoff — Android companion action privacy

**Date:** 2026-11-26  
**Owner:** Core & Harness  
**Parent PR:** [#2528](https://github.com/RedMentos/Aii/pull/2528)  
**Branch:** `core/v14-open-url-terminal-redaction-20261126-run1`  
**Latest code commit:** `2526e24c8521707d7065fed28d495dde856245c6`  
**Release base:** `gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6`

## Runtime changes

1. Terminal `open_url` actions redact the raw URL path/query/fragment from the durable action journal on `EXPIRED` and `CANCELLED`; only the public host and digest remain. Still-pending actions keep the URL for the visible local approval lifecycle. Malformed stored JSON uses a minimal redacted terminal envelope.
2. The companion now rejects any top-level action-request fields outside the exact 11-field envelope. This closes a privacy gap because the request digest binds only `capability + args`; previously an extra unbound field could carry a second private URL into durable `request_json`.
3. Tests cover direct and bulk expiry, cancellation, non-redaction of live requests, malformed JSON with a fragment, helper-level exact-field validation, and a provider `submitLocked` negative-path proving an unbound URL is rejected before durable insertion.

## Verification

- Code-bearing commit `63b05800ca08167b894f2a48e2a7e9ec73d0ee12`: Android Gradle/Robolectric job **SUCCESS** (run 45769108967); offline bridge security **SUCCESS** (run 45769108891). This includes the malformed-JSON/fragment regression.
- Emulator process-restart job from run 45769108967 was still **IN_PROGRESS** at last read.
- Hardening commit `96e8c54f06c04aec4262a0751f2ee8f90184f6c9`: Android Gradle/Robolectric **SUCCESS** on exact PR-head run 45769580810; emulator process-restart remains **IN_PROGRESS**. Latest code commit `2526e24c8521707d7065fed28d495dde856245c6` adds a direct provider negative-path test. Android Gradle/Robolectric **SUCCESS** on run 45770231218 (including the new test); offline bridge security **SUCCESS** on run 45770226583; emulator process-restart remains **IN_PROGRESS** on run 45770231218.
- LOCAL_LINUX: Java 21 present; Gradle absent; Android SDK variables unset. Android Gradle/Robolectric is BLOCKED locally. Full checkout also BLOCKED by GitHub DNS.
- TERMUX/REDMI: REDMI_UNVERIFIED; read-only private relay HEALTH #959 and PIPELINE_STATUS #960 have NO_LIVE_RECEIPT (no `device_status` comment). No device action.

## Safety / release boundary

No user URL, private device data, model weights, permission, app install or user state was changed. No raw URL is written to telemetry or public handoff. The companion's visible per-action consent and independent Android identity remain required. The ActionOutcome path is a signed companion receipt only (`observed=false`, `t8_authoritative=false`, `world_learning_eligible=false`); it is not proof of browser success and is not promoted to T8 learning. PR remains DRAFT / NOT_RELEASED until exact-head Android tests and independent QA review pass.

## Next exact action

Poll the exact-head emulator process-restart job in run 45770231218; if it passes, request QA review. If it fails, repair and rerun. Separately coordinate the #2529 Runtime source-pin cascade with the affected owners; do not merge #2529 while staged-runtime/integrated-regression are red.

## Relevant next research

- R-090 deadline-aware prefill chunking is a design reference only (GPU-serving papers; no Android performance proof). Measure per-role cost from prompt tokens and warm/cold state before changing budgets; preserve B1/B2 opportunity and C3 reserve.
- R-091 makes the key distinction: native input-embedding numerical response is not semantic latent transfer. Require same-model prefill parity and source-disjoint task utility with no-message, exact-source, zero, shuffle, row-shuffle and bidirectional controls; keep production B3 OFF.
- R-107 Future-Aware Recall is conceptual only; the public implementation is CC BY-NC 4.0 and CUDA/H100-oriented. No reuse or model download.
- No model alternative is recommended without comparable native Redmi measurements.
