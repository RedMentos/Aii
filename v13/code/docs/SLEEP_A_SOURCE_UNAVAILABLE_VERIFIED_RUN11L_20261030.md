# Sleep A source-unavailable replay continuity — verified RED → GREEN 2026-10-30

Owner GPT-6, review-only child of #1240 exact parent `645c70e8c28fb9e016eaa5d068c2d3977075184d`. Preregistration `96e824908e43ed9f8446a00d2b09f1d6c18eaeb9` committed before test/source; original test-first commit `9068f56de3c8bd367162a82cae9d02906dbed842`, expanded prereg envelope/source-ID tests before patch in `e62bf72f715c69bf203fe3af228d38067418054e`.

## Original negative evidence retained
Actions **41028955114 RED** at `d0ccb8c32a009a043fb75b5ba94536662de42e16`, artifact **12965215780**, ZIP SHA256 **`bc8022d2527ac84960d602b3dd393dac72394e5a9ddde102226e38fd691fc49c`**: 51 tests, 1 genuine FAIL + 2 ERROR (missing live blob raises FileNotFoundError and aborts batch; corrupted live blob falsely retires). After expanding the preregistered envelope controls, Actions **41029066006 RED** at `e62bf72f715c69bf203fe3af228d38067418054e`, artifact **12965236257**, ZIP SHA256 **`7cd565d0c8ce1f5f70a97991e5ae07f0828360a119d965cf24259761dced0b06`**: 53 tests, 2 FAIL + 3 ERROR, including malformed event envelope and event source-ID substitution. Both ZIPs CRC clean, **13/13 inner hashes** and VENV/DEPS/COMPILE/PRIVACY/DIFF exit0, TEST exit1. Original failed attempts are preserved unmodified.

## Minimal fix and independent GREEN
Source commit `a11d1f7214b55a564fdc62f118da26c4de2dee35`, `sleep.py` blob `903da6af1a23f82929a637389e98d6b4a966f3f4`. `SleepCycle._probe` now validates event envelope and event/source-ID binding; explicit tombstones still `RETIRE/SOURCE_DELETED`, while missing/corrupt **live** source bytes produce typed `FAIL/EVENT_SOURCE_UNAVAILABLE`, original SourceRef, check and `source_integrity` path, without retiring or aborting other items. Malformed envelope produces `FAIL/EVENT_ENVELOPE_INVALID` without fabricating a source ref. No source rewriting, fact/weight writes, queue-policy or Age-right changes.

Actions **41029192030 GREEN**, exact tested HEAD `a11d1f7214b55a564fdc62f118da26c4de2dee35`, artifact **12964882895**, ZIP SHA256 **`6507f288080a4940434ed58882ff21f8e65cde9c90cfe401b0e4165002006da0`**, CRC clean, **13/13 inner hashes**, **53/53 tests PASS** in 2.662s, all six VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF exit0, privacy CLEAN. All three original ZIPs privately backed to `/V13-Checkpoints/2026-10-30/Run11L-Sleep-SourceIntegrity/` and independently materialized byte-exact.

## Claim limits and next
This is a software/real-Store synthetic source-loss regression, not evidence of native dreaming, memory consolidation, model learning, or Redmi. The full unfiltered run11k on parent #1240 is independent and was in progress at this checkpoint; do not conflate its result with this focused GREEN. Historical Run34/Run37 frozen source-pin RED remains, no waiver. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE. No main merge.

**Exact rerun:** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_sleep_a_source_unavailable_run11l tests.test_sleep_a_exact_recall_identity_review tests.test_sleep_validation tests.test_sleep_memory_authority_run274 tests.test_sleep_offline tests.test_sleep_scheduler`.

**Next:** inspect run11k terminal raw; continue the independent preregistered 350M Body-JEPA EMA eval-vs-train native follow-up only after the heavy owner is terminal, with exact model SHA/license and all negative gates. Owner GPT-6.
