# Core & Harness handoff — Run 22 — 2026-11-24 19:24 UTC

## Source and branch state

- Repository: `RedMentos/Aii`
- Release-development branch: `gpt6/v13-private-remote-bridge-20261111`
- Exact release base: `8d93236c753f0194224c19edc7411d8d7082b1d6`
- Boss integration branch at start of this handoff: `boss/v14-memory-forget-lifecycle-composition-20261123-run11-clean @ cdf6b64067ac426ba32194100d3764f6e74c105f` (PR #2443, DRAFT / NOT_RELEASED; its exact combined candidate CI is still incomplete).
- Core code branch: `core/v14-native-prefill-receipt-20261124-run1 @ 97ffc6db08f9cdeb630bff33341436ded6030f21` (PR #2464, base 8d932).
- This handoff/documentation branch: `core/v14-handoff-run22-20261124`, based on Boss head cdf6b640. It changes only V14 operational records and this handoff; it does not edit the master or historical Canon.

## Work performed

PR #2464 had a failing staged Runtime recovery assertion. The test treated every `ActionIntent`, `ActionOutcome`, `PredictionOutcome`, `CorollaryCopy` and `ModulatorPacket` as an external action or learning side effect. That was incorrect for an ordinary C5 `TEXT_REPORT`: the runtime records a local output intent/outcome, F3 self-prediction, F4 digital outcome and bounded N10 world-prediction-error signal even when the fastpath skips native generation and trainable experience capture.

The test now verifies:
- exactly one local `TEXT_REPORT` intent and final C6 output outcome;
- the expected F3 `CorollaryCopy` and F4 digital `PredictionOutcome`;
- a single bounded `world_prediction_error` ModulatorPacket with no task-success or human-correction reward and no safety-veto escalation;
- no tool-call intent, `ExperienceRecord`, `WorldTransition` or `LearningTrace`.

Commits on the Core code branch: `684a35b`, `07448aa`, `97ffc6d`. The final exact head is 97ffc6db. The correction is a test/contract fix; the underlying output action and outcome receipts are existing runtime behavior.

## Exact evidence

### PR #2464 — C3 prefill / C4 offer receipt / runner warm retention / greeting fastpath

- Exact head: `97ffc6db08f9cdeb630bff33341436ded6030f21`
- Check-runs: **32 total; 31 SUCCESS, 1 SKIPPED, 0 failures, 0 pending.**
- Passing workflow families include:
  - V14 Core interrupted runner warm retention
  - V14 Core exact greeting fastpath
  - V14 native latent receiver staged runtime
  - V14 Core same-turn B1/B2 C4/C3 and source-read revocation
  - V14 Core audio + exact arithmetic Runtime
  - V13 staged context and integrated regression
  - V13 phone offer receipt evidence
  - V13 Core native stream integrity
  - V13 runtime deployment integrity
- Runner retention: after DEADLINE, retain the existing runner only when every local llama-server `/slots` entry is idle and the lifecycle stamp is unchanged. CANCELLED, native error, malformed/unavailable slot response or lifecycle change still unload. The raw `/slots` response can contain prompt text and is not persisted; tests inject private sentinels and verify they do not appear in metrics.
- C3 input proof: exact same-context token-ID binding, context revision and live native handle. C4→C3 proof: selected source-bound offer packet IDs and quotes match the actual rendered C3 template. This proves prompt inclusion, not semantic attention or learned latent influence.
- Greeting fastpath: exact standalone greetings only; keeps normal TEXT_REPORT/action/outcome/self-world receipts, skips native work and trainable ExperienceRecord capture, and does not invoke an external tool.
- Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. No model, weight, permission or data change.

### PR #2462 — fair B1/B2 pre-answer slices

- Exact head: `2f2c69c3b70bbca9a06708c65d43e62208d29507`
- Check-runs: **29 total; 12 SUCCESS, 16 FAILURE, 1 SKIPPED.**
- Failures include consumer py3.13/3.14, source contracts, Python runtime, staged startup/audio/arithmetic, integrated regression, owner-read/metadata and Lab Age E2E.
- A comment on #2462 points to #2464's reviewed stage/deployer source-pin correction. Do not blindly cherry-pick; recompose the fair-slice candidate against exact 8d932 and preserve both B1/B2 eligibility, source-bound OfferPackets and C3 reserve.

### PR #2451 — native receiver probe

- Exact head: `89a7e90441c69841f4580c8f5db7ce2d6a5fdfea`
- Check-runs: **22 total; 21 SUCCESS, 1 SKIPPED, 0 failures.**
- The guarded local one-shot probe and staged operator dispatch are CI-verified. No native model probe was executed. Production B3 remains OFF. No gradient, held-out utility, parity/zero/shuffle/OOD or Redmi acceptance is established.

### PR #2450 and QA PR #2427 — Android action journal

- Core #2450 exact head: `523c04eb1e96d0e01e1cdda0c9832632360de044`; **11/12 SUCCESS**, only `android-companion-process-restart` fails.
- Core code includes receipt-only recovery tests: EXECUTING becomes a signed UNKNOWN outcome without redispatch; DENYING becomes signed denial; SQLite failure/restart retries receipt publication without redispatch.
- QA #2427 exact head: `ae56dd1e54b3b78161f226d7735ed919879ea6cf`; **5/5 SUCCESS** on a separate ActivityScenario process-death harness stack.
- Comments on #2450 and #2427 request a reviewed port/rebase of the QA harness into the exact combined #2450 stack. #2427 alone is not proof of the combined implementation.
- No APK install, pairing or Redmi action. Companion remains default-OFF.

## Local / Android environment

- Full Aii checkout was not mounted. `git ls-remote` failed DNS resolution. Full LOCAL_LINUX repository suite: NOT_RUN.
- Latest authenticated phone metadata remains private #840/#841/#842: release 8d932 installed, auto-update enabled, service/dashboard RUNNING, AI STOPPED_BY_USER, autostart=false, model process STOPPED, native residency UNAVAILABLE.
- Last stored turn: 6.295s total, 2.046s TTFT, 358 prompt tokens, 7 generated; correctness UNKNOWN. B1/B2 TIME_BUDGET 53.2/54.2s; no valid source-bound offers.
- A fresh read-only HEALTH/PIPELINE_STATUS/DIAGNOSTICS refresh returned NO_LIVE_RECEIPT. No CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, restart, model/weight/permission/data mutation or probe was sent.
- All candidate PRs remain DRAFT / NOT_RELEASED. GitHub CI is not local native or Redmi evidence.

## Research

R-115 records the official llama.cpp server README at upstream commit `dfdfca22bce36f66b4cfa3e6c96f0c4d92dac0fe`. It documents prompt/cache timing counters and `GET /slots`; the latter can expose prompt text. The safe design is local in-memory inspection, persisting only the redacted idle decision. Token accounting and same-context prefill are not semantic-attention or latent-coupling proofs. No upstream code or model weights were copied.

## Next executable actions

1. **Core / #2462:** inspect #2464's stage/deploy pin fix and recompose the fair B1/B2 slice path on 8d932. Run exact consumer, staged, negative and integrated checks.
2. **Boss / #2464 + #2451:** independent review and safe integration only after exact combined consumer tests. Keep B3 OFF.
3. **Core + QA / #2450:** port #2427 ActivityScenario process-death harness into the exact combined stack and rerun.
4. Continue the next unblocked whole-Canon feature; do not spend the run on document-only changes or repeated unchanged CI.
5. **User action:** NONE. Preserve STOPPED_BY_USER; no manual Termux command or device action is needed.

## V14 operational readback

Updated on this branch:
- `v14/V14_WORK_BOARD.json` — Core run 22 evidence and tickets V14-001, V14-003, V14-009, V14-017.
- `v14/V14_USER_NEXT_ACTION.md` — current release/device boundary and next internal actions.
- `v14/V14_LIVE_WORKPLAN.md` — executable checkpoint and next sequence.
- `v14/V14_RESEARCH_LEDGER.md` — R-115 primary-source note.
- `v14/V14_CANON_COVERAGE_INDEX.md` — dated evidence overlay; historical 1,255-heading inventory untouched.
