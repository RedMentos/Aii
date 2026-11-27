# Research & Perception — Run 62 (2026-11-27)

## Product checkpoint

Two Perception changes are now stacked as a single A4/A5 line:

- [#2553 — preserve shared A4 weights on temporal reset](https://github.com/RedMentos/Aii/pull/2553), child of #2551.
- [#2554 — lease-bound A5 visual frames on session-scoped A4](https://github.com/RedMentos/Aii/pull/2554), child of #2553.

Current branch: `research-perception/v14-a5-visual-frame-on-session-scoped-a4-20261127-run62`; code-bearing head at PR creation `f78dbdc369ba2e3cac5e9acff05dca033c05be2a`. Board/docs checkpoint after code: `62414aea9aa4cc2b320943c46763736e0b2ed3b9` (docs-only).

## A4 shared-checkpoint correction (#2553)

A4 temporal history is session-local, but numeric weights are intentionally shared for the same source/generation/consent scope. The old chronology/gap reset wrote a fresh zero predictor into that shared checkpoint, erasing weights learned by another session. The fix reloads a valid checkpoint into the resetting session and leaves the persistent version untouched; missing/invalid/consent-rotated state still initializes through the existing reset path.

Regression coverage:
- `RESET_CHRONOLOGY`: session A trains non-zero weights; session B resets chronology; exact weights/update count and checkpoint version remain unchanged while B gets a fresh temporal baseline.
- `RESET_GAP`: same preservation under a long gap.
- Existing consent-rotation negative control still resets the old consent scope.

Predictor blob: `2519e5cbbbfacc7bb252a4cd2c84148e4f641176`; regression-test blob: `abd5d2b53e6423ddebe73f52816e3431bea29b5d`; integrated audio composer blob: `f1fd06c70f9d27148c22df869abe0ad66a4cf467`.

## A5 visual-frame adapter (#2554)

The adapter consumes a FINAL `SCREEN_FRAME_AVAILABLE` observation only while a matching `UIObservationLease` is live. It decodes a frame in memory, computes the existing RAW-EYE descriptor, attaches a non-semantic structure cue to the exact A4 visual segment, and returns a source-bound `PerceptPacket` plus bounded `PerceptAdmission`. An already-installed hashed-BOW projector can return up to three `STUDENT_ESTIMATE / REFERENCE_NOT_FACT` hypotheses; it does not load a teacher. Adapter-held features are cleared on lease revocation/exit. No screenshot, pixels, features or transcript are persisted; action and learning authority remain false.

A5 bridge blob: `c39077ba43db1c1623825b82732b56808330c688`; A4 visual-salience blob: `8b6c4286b22e6bf7280ff7f37090e0a07e398207`; tests blob: `8ed18c2ac527fb314a8636274dbd20df07e3e339`; exact UI lease dependency blob: `a6c26206d535199b244d0de83fbeb38bb8ad3951`.

## Exact tests

**LOCAL_LINUX**
- CPython 3.13.5 / SQLite 3.46.1 isolated A4 reset-semantics reproduction: **3/3 PASS** (old wipe reproduced; corrected shared-weight preservation; consent-rotation negative control).
- Full local Aii checkout/pytest: **BLOCKED / NOT_RUN**. No checkout is mounted and `git ls-remote https://github.com/RedMentos/Aii.git` cannot resolve github.com.

**GitHub Actions — exact code-bearing heads**
- A4 predictor/update-gate regression: **47/47 PASS** on Python 3.13 and 47/47 on Python 3.14.
- A4 temporal source-isolation: **9/9 PASS** on Python 3.13 and 9/9 on Python 3.14.
- Source-bound A4/A5 feature-set: **15/15 PASS** on Python 3.13 and 15/15 on Python 3.14.
- RAW EAR optional NumPy/backend and A4/A5/C3 consumer suite: **175/175 PASS** on Python 3.13 and 175/175 on Python 3.14.
- RAW EAR vs WebRTC/libfvad: **186/186 PASS** on Python 3.13 and 186/186 on Python 3.14; pinned native libfvad C tests **13/13 PASS**.
- A5 visual-frame bridge: **11 tests + 3 subtests PASS** on Python 3.13 and the same on Python 3.14.
- RuntimeDeploy offline integrity: **92 tests PASS** on Python 3.11 and 92 tests PASS on Python 3.14; no deployment performed.
- Public-content privacy scan: **CLEAN**.

**Shared staged/integrated gate — FAIL**
- `20 failed, 233 passed, 10 skipped, 2 errors, 41 subtests passed`.
- Integrated regression: one setup failure.
- Causes are upstream of this Perception adapter: Core Recovery still pins the old `integrated_audio_context_candidate_20261121.py` blob; Core arithmetic `v13/contracts.py` and observer `v13/cognition.py` pins are stale; QA two-checkout migration assertions expect `UPDATED` but current safe result is `PARTIAL`.
- The same failure reproduces on #2553 and #2554; Perception did not weaken pins or migration assertions.

## Integration / device boundary

- Core #2549 and child #2552 are stacked on the parallel #2550 line. Perception has now carried the A5-owned files onto the combined A4/A5 #2554 line. Core should rebase its owned Recovery → Stage → RuntimeDeploy chain onto #2554 after review and refresh composer, arithmetic and observer pins bottom-up; QA retains migration assertion ownership.
- **A5 is WIRED_SYNTHETIC, not Android-verified.** Tests use generated PNGs and a synthetic provider. There is no Android MediaProjection provider, no platform onStop cleanup proof, and no normal-turn Runtime callsite yet.
- No Android/Termux microphone/frame capture, native model, Redmi receipt or device deployment. **REDMI_UNVERIFIED / NOT_RELEASED**.
- P0 basic chat, B1/B2 valid-offer delivery and native B3 latent coupling remain unresolved. The A4/A5 work does not satisfy whole-system acceptance.
- No model/weight/permission/updater/data change; no user action required.

## Next executable steps

1. Core rebase #2549/#2552 onto #2554 and refresh the exact Recovery → Stage → RuntimeDeploy source pins; QA resolves the two migration expectations without changing safety semantics.
2. Perception adds independent-registry/store conflict stress coverage, then works with Core on the missing normal-turn A5/signed-audio consumers under live consent leases.
3. Only after a real authorized MediaProjection/AudioRecord provider and exact runtime callsite exist should QA pursue Redmi proof. Never infer phone operation from CI.
