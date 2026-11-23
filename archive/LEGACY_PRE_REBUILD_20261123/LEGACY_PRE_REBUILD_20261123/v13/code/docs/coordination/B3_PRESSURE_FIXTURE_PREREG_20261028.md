# B3-H10 pressure fixture determinism — preregistration, 2026-10-28

Parent PR #805 at `b5d25359d43828c9e0ca4f93a34bb0fdf2a2b8a6` (review only; source green pending). Earlier parent PR #804 full Linux CI 40608236483 ran 2098 tests and failed exactly one legacy test: `test_b3degrade.Live.test_promotion_needs_human_and_evidence_then_resource_mode_demotes`, observed `L1` instead of `EXACT_SYMBOLIC`.

## Source-verified root cause and limited remedy

`test_b3degrade.py` assigns `r.guard.state='PRESSURE'` and immediately calls `b3_doctor`. Concurrent `Runtime._worker` calls `SleepRuntime.tick()` even when the sleep cycle policy is off; `tick -> resource_state -> guard.update(resources())` can overwrite the manual test-only state before the B3 check. The `ResourceGuard.mode` property correctly maps PRESSURE to ORANGE when not overwritten. The failing assertion is therefore consistent with a test-fixture race; this is a hypothesis until a repeat confirms it, not proof of a production B3 defect.

Only in this existing test, hold `guard.update` at a no-op for the manually injected pressure interval via a scoped `unittest.mock.patch.object`. Check `mode_of(guard)=='ORANGE'` and retain the original B3 demotion/telemetry assertions. Do not alter production `resource_modes`, `sleep`, `b3degrade`, authority, gates, Canon or any model/seed.

Verification: focused `tests.test_b3degrade` plus the HX3 focused suite and full Linux software suite in a pinned Actions workflow; keep original failed raw 40608236483 and all later failures. Repeating the focused test is a fixture stability probe, not native B3 evidence. If full suite fails for another reason, preserve it and investigate, not mark green. No native/Redmi/learning/age promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0.
