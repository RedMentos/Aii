# Boss & Integration — Run 14 handoff

Date: 2026-11-22T23:05:31.059Z
Release base: aed1d2b826290c95c70356b5d8b864b5ef382be4
Boss code branch: boss/v14-fair-budget-current-base-20261122-run14
Boss code head: de50fd4708490fb6db19cf24c22fef22baf23eca
Docs branch: boss/v14-run11-current-evidence-sync-20261122
Role: whole-Canon integration, release gate and cross-agent coordination

## Release and authenticated Redmi evidence

- Release exact SHA: aed1d2b826290c95c70356b5d8b864b5ef382be4; 45/45 exact-SHA check-runs SUCCESS.
- Private PIPELINE_STATUS #641 confirms that SHA installed; auto-update enabled; runtime/dashboard UP_TO_DATE; last_error NONE.
- Private DIAGNOSTICS #642: service/runtime/dashboard RUNNING. Last stored FINAL turn unchanged: 57.7388 s total / 41.6269 s TTFT / 38.9453 s prefill / 751 prompt tokens / 2 generated tokens. B1/B2 TIME_BUDGET 53.2/54.2 s; C2 OK; C3 3.1 s. Instant native process map 0 mapped processes / 0 MiB PSS/RSS, child readability unknown. HEALTH #636 still conflicts with DIAGNOSTICS; LEARNING_STATUS #637 unavailable.
- Lab-Age selector ACTIVE/requested 10/effective 5; official Age 0; physical feature execution false; learning commit authority requires separate SHADOW.
- No new chat turn, CHAT_SEND, LOG_PAGE, UPDATE_REQUEST, remote shell, model/weight/permission change or device mutation. console_errors USER_NOT_OPTED_IN.

## Boss code work and tests

- PR #2370 exact head de50fd4708490fb6db19cf24c22fef22baf23eca, DRAFT: 27 queued / 1 skipped / 0 completed success / 0 failures observed. NOT_GREEN / NOT_RELEASED.
- Fixed the two previous exact-head failures and one stale source assertion:
  1. Integrated observer composer now validates and preserves the 26 s short-turn C3 recovery reserve; per-role observer deadline only caps each body's fair slice. It no longer replaces the reserve with 16.5 s.
  2. The synthetic clock patch now targets `v13.cognition.time.monotonic`; `native_turn_budget.plan` receives `now` explicitly and the module does not own a `time` attribute.
  3. The arithmetic restart test sends `calculate 8/4` and now expects that exact source both before and after restart. Production source text is not normalized.
- Refreshed and read back recovery12 → recovery21 → stage → runtime_deploy SHA pins. Commit de50fd4708490fb6db19cf24c22fef22baf23eca is on the Boss branch.
- Local full repository tests: BLOCKED (no Aii checkout; GitHub DNS clone unavailable). No local pytest/native/Redmi pass claimed.
- The scheduler fix is not a speed fix: the device's measured B1/B2 timeouts remain 53.2/54.2 s.

## Cross-agent integration / whole Canon

- #2372 temporal T8/receiver: 2 success / 4 failure / 2 in progress / 3 queued; #2383 QA source-lifecycle chain 4 success / 7 failure. No accepted B1/B2/C3 master-weight diff or held-out utility.
- #2369 Teacher Ear: 14 queued / 2 skipped. R-094/R-095 copied from its exact research ledger; no model download. Teacher Ear is caller-supplied, optional and ephemeral, not ASR inference.
- #2375 RAW EYE: 6 success / 4 failure / 1 skipped; #2384: 3 success / 2 failure. Frame-ingress failures remain.
- #2356 companion QA: 7 success / 1 failure (process restart); #2379 MediaProjection: 5 success / 2 failure and stale companion base; #2376 action journal is stale. No end-to-end Android action or capture receipt.
- #2377 native-probe byte/path verification: 7/7 CI, but a residual path-replacement interval remains between consume-time verification and native loader open. Keep probe/B3 OFF; #2381 stale.
- Exactly five enabled V14 automations verified: Boss, QA & Android, JEPA & Memory, Forschung & Perception, Core & Harness.
- Historical 1,255-heading inventory and the 963,129-byte V14 master/V13 appendix remain unchanged. Master blob 9748ad5ba9a4d4f5c3d004a0577141f6779fcbca is byte-identical across release and docs branches.

## Research

- R-094: sherpa-onnx v2.0.3 code Apache-2.0; 20M English Zipformer model card declares Apache-2.0; Android NDK/JNI does not prove Termux ABI.
- R-095: whisper.cpp code MIT; Whisper tiny model-card Apache-2.0 vs original README MIT weight-license discrepancy unresolved. No download.
- R-092 AudioRecord / JEPA paper ID collision remains unresolved; requested JEPA R-093 rename not verified.

## Next owners

- Boss: wait for exact #2370 matrix, review the complete diff and downstream pins, and do not merge until exact CI and adversarial checks pass.
- Core: preserve C3 reserve; prove real B1/B2→C4→C3 delivery; integrate Teacher Ear only as a consent-bound ephemeral C3 hypothesis.
- JEPA: repair source-lifecycle, optimizer-resume, SleepRuntime and rollback; prove actual numeric deltas/retention before weight claims.
- QA: repair #2356 process restart and #2377 loader path race; fix #2384 frame ingress.
- Perception: connect RAW EYE to A3/A4/C3 and reconcile #2369 audio pins/ephemeral C3 delivery.
- User action: NONE. No phone update request or manual command.
