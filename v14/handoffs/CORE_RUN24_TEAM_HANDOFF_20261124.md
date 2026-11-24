# Core & Harness — Run 24 shared handoff

**Checkpoint:** 2026-11-24T20:54:27Z (latest verified commit timestamp; actual run start/end and remaining platform budget are UNKNOWN).  
**Development base:** release `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`.  
**Release state:** NOT_RELEASED. **Device state:** REDMI_UNVERIFIED; last shared record says AI STOPPED_BY_USER. No device action was performed.

## Active Core work

1. **PR #2478 — fair B1/B2 pre-answer budget and staged runtime.** Current branch head `93173a839c3142a42a94e3666d5127957a75f148`. Two exact defects found in CI were patched on the same Core-owned branch:
   - the feedback-bootstrap ActionLearn candidate is a CLI-only variant; the RecordOnly guard now accepts its exact source hash plus the base source hash, retains the `updates_allowed` guard, and rebinds the semantic consumer to the guarded output;
   - body-attempt telemetry now records the attempt boundary rather than a stale `runner.last_metrics.status`; post-commit retries skip roles whose turn-local attempt ended DEADLINE/CANCELLED/INTERRUPTED.
   Raw-byte SHA256 → builder blob SHA1 → wrapper SHA256 → stage pin chain was recomputed and read back. Exact-head CI has 27 checks registered: 1 SKIPPED, 26 QUEUED at last poll; no PASS/FAIL result yet.

2. **PR #2480 — per-organ attempt/consumption diagnostics.** Current head `0b5e2fe5fee5d05589ebab57fae6fe9e12b352c7`. `brain_panel.status` now joins B1/B2 attempt metrics and delivered OfferPacket IDs to C4 selected IDs and the C3 native prompt receipt. It exposes numeric token/TTFT/duration/PSS fields and exact delivery/selection/template-inclusion states, bounded to 16 rows and without raw text. `semantic_use_proven` remains false. The first exact run found one test-fixture ID-length error (5 passed, 1 failed); the fixture was corrected. New exact-head CI has 8 checks QUEUED at last poll.

3. **PR #2481 — Android ActionOutcome process-death harness.** Current head `95dd586a84dff5700b79ba6871d7e8615d23764f`. Ported QA PR #2427's exact Espresso/ActivityScenario process-death harness to the Core ActionIntent/ActionOutcome stack. QA and Core MainActivity blobs match. The old UIAutomator job failed because hierarchy dump timed out while the process remained alive; that failure is not relabeled as PASS. On the new exact head, Android build and Core Python 3.13/3.14 jobs plus offline security are SUCCESS; the Android emulator process-death job is IN_PROGRESS.

## Evidence boundaries

- **LOCAL_LINUX_ISOLATED:** CPython 3.13.5 / pytest 9.0.2; per-organ evidence helper compile + 5 focused tests PASS.
- **LOCAL_LINUX full repository:** BLOCKED / NOT_RUN. No checkout is mounted; `git ls-remote` failed GitHub DNS. Do not describe full local pytest or full-repo compilation as run.
- **CI:** PR #2464 parent native-prefill path had 31/32 SUCCESS and 1 SKIPPED. QA PR #2427 source harness had 5/5 SUCCESS on its own branch. New combined heads remain as listed above.
- **ANDROID_EMULATOR:** PR #2481 build/Core matrices SUCCESS; process-death emulator job still running at last poll.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No authorized live receipt, CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, restart, model change or permission change.
- **Updater/deployment:** not invoked; GitHub push/PR is not deployment.

## Next executable work

1. Poll exact-head CI for #2478 and #2480; fix failures rather than treating queued checks as PASS.
2. Poll #2481 Android emulator process-death job; retain visible Stop, persisted OFF, process-death and no-redispatch assertions.
3. Once green, request independent review and integrate against the newest compatible branch; do not merge stale bases.
4. Use measured B1/B2 prompt tokens, TTFT, generated tokens, sampled PSS and C4/C3 receipt joins to calibrate fair slices while retaining both bodies and the C3 reserve.
5. Only after a separate authorized installation and owner-verified device receipt can Redmi status be promoted.

**Research/model decision:** No model alternative or model swap is justified yet; the required native per-role comparison is not available. The next useful experiment is measurement-driven B1/B2 budget calibration from the new counters.  
**User action required:** NONE.
