# Research & Perception — run 30: consent-scoped A4 temporal-state eviction (2026-11-25)

## Checkpoint and dependency

- Updated the existing Perception-owned PR [#2491](https://github.com/RedMentos/Aii/pull/2491) on branch `research-perception/v14-speaker-consent-scope-purge-20261125-run29b`; no extra stacked PR was opened.
- Branch parent before this checkpoint: `a182189251ea6c0c03e6f2f16c64d9288790c7ac`; parent chain remains #2491 → #2487 → #2472. The PR is still a draft child of the Perception audio chain, not a release.
- This change is limited to Perception-owned RAW EAR temporal state, its tests and the matching workflow source pin. No Core composer, recovery builder, deployer, Android provider or historical V13 Canon bytes were modified.

## Reproduced defect

`TemporalVoiceEvidenceRegistry` keyed state by (source, generation, consent-scope fingerprint), but on a new receipt it created a fresh state without evicting the old same-source/same-generation key. That left the prior A4 scalar filter state in the Runtime LRU until unrelated eviction and returned `state_reset=false` on a consent rotation. The speaker registry in the same audio path already had explicit epoch eviction in #2491; the temporal registry did not.

## Implementation

- Validate/update the incoming temporal state before eviction, so malformed new input cannot delete the last valid scope.
- After successful update, remove old generations and all prior consent-scope keys for the same source; preserve other sources.
- Report `state_reset=true` and `reset_reason=CONSENT_SCOPE_CHANGED` for a scope change, including scoped→legacy-unscoped transitions.
- Extend the actual `consume_pcm16_voice_window` Runtime consumer regression to assert the reset and that only one temporal registry entry remains.
- Add focused tests for scope rotation, scoped→unscoped transition, malformed-input non-eviction, and preservation of other sources/generation replacement.
- Update the FASTDIAR workflow to run the temporal registry test file and rebind the RAW EAR/libfvad comparator to the exact new source blob.

## Evidence boundary

- **LOCAL_LINUX isolated state-machine reproduction:** 4/4 PASS on CPython in this run. The baseline reproduction first showed two retained keys for one source/generation after receipt rotation and `state_reset=false`; the patched reproduction purges the old key and returns the explicit reset. This is an isolated state-machine reproduction, not the full project module or full checkout.
- **Full LOCAL_LINUX Aii checkout / pytest:** BLOCKED / NOT_RUN; no checkout is mounted and the runner's GitHub DNS/network path is unavailable.
- **Exact-head GitHub Actions on `de18aa02ea783049ab50c3c69d2857c355364a3b`:**
  - FASTDIAR adapter/consumer [run 45574271371](https://github.com/RedMentos/Aii/actions/runs/45574271371): **PASS** on Python 3.13 and 3.14; each job ran **125 tests**, exact `py_compile`, and public-content privacy scan **CLEAN**. This includes the new temporal-registry tests and the real `consume_pcm16_voice_window` consumer regression.
  - RAW EAR/WebRTC/libfvad comparator [run 45574271406](https://github.com/RedMentos/Aii/actions/runs/45574271406): **PASS** on Python 3.13 and 3.14; each job ran 9 Python tests, built the pinned `dpirch/libfvad@532ab666c20d3cfda38bca63abbb0f152706c369` shared library and passed its 13 C unit tests. This is Ubuntu Linux x86_64 native-library evidence, not Android evidence.
  - RAW EAR fastpath [run 45574271401](https://github.com/RedMentos/Aii/actions/runs/45574271401): **PASS** on Python 3.13 and 3.14; each job ran **148 tests**, exact compile, deterministic synthetic benchmark (`device_benchmark=false`) and privacy scan **CLEAN**.
  - Runtime deployment integrity [run 45574271352](https://github.com/RedMentos/Aii/actions/runs/45574271352): **PASS** on Python 3.11 and 3.14.
  - Staged/integrated [run 45574271337](https://github.com/RedMentos/Aii/actions/runs/45574271337): **FAIL**. Staged runtime: 18 failed, 235 passed, 10 skipped, 2 errors, 44 subtests; integrated regression: 1 failed. Both stop at the Core-owned recovery builder's exact `scripts/record_only_controller_guard_20261116.py` SHA mismatch. Two-checkout migration returns `PARTIAL`, not `UPDATED`. No hash pin was weakened.
- **Intermediate CI repair:** comparator run 45574042985 on commit `6affd295` failed because its expected temporal-source blob still pointed to the previous `8b236...` bytes. The workflow was rebound to final blob `4667e4f0d81db4d1c1ce798b8106c5e157dbd4d8` in `de18aa02`; the exact-head comparator rerun above passed.
- **Full LOCAL_LINUX Aii checkout / pytest:** BLOCKED / NOT_RUN; no checkout is mounted and local GitHub DNS/network is unavailable.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. Read-only private relay requests #899–901 (HEALTH / PIPELINE_STATUS / DIAGNOSTICS) have no authenticated device reply at this checkpoint (NO_LIVE_RECEIPT). The latest available V13OBS #115 snapshot is historical (2026-11-24 09:28 UTC); it does not establish this candidate is installed or that the AI is running. No microphone capture, UPDATE_REQUEST, shell, model/weight/permission change or user-data mutation was performed.
- **Release/deployment:** NOT_RELEASED. A GitHub push is not deployment. The last available device snapshot is historical and cannot establish this candidate is installed or that the AI is running.

## Research added

- R-122: full-text review of Mouchon & Lainault, arXiv:2611.20819v1. Its intra-meeting-only prototype memory and end-of-meeting wipe are a useful lifecycle analogy, but its frozen backbone/no-gradient design is not adopted. Results are small-sample/single-seed and its causal-strict track is poor.
- R-123: full NIST PDF review of Seo et al., listed for ICASSP 2026 but marked pre-decisional draft. It shows residual identity leakage across de-identification systems; embeddings are not assumed anonymous. It does not test this temporal scalar registry.
- No OSS, code, model, weight or dataset was reused or downloaded.

## Integration and next step

1. Run exact-head Python 3.13/3.14 FASTDIAR adapter/consumer and RAW EAR/libfvad comparator workflows; read the exact SHA and job results.
2. Boss/Integrator reviews #2491 and composes it into #2487 only after the parent and the Core/QA strict recovery pin chain are independently reviewed. The existing staged/integrated failure remains Core-owned; do not weaken its SHA pin.
3. After merge into the current Perception chain, QA/Core still need the signed Android audio-consent provider/revocation/zeroization lifecycle before AudioRecord is enabled.

**User action:** none required. No manual Termux command, device update, model download or productive swap is requested.


## Additional speaker-registry preflight correction — 2026-11-25

Independent review of the just-added speaker-scope purge found one more fail-closed ordering defect: `SpeakerChangeEvidenceRegistry.update()` evicted the old consent key before checking whether the incoming lookback could fit the registry's `max_frames` bound. A malformed new scope could therefore erase the last valid vectors and then raise.

- Moved current-scope chronology and lookback-capacity validation before any old-generation/old-scope eviction.
- Added `test_invalid_new_consent_scope_does_not_evict_previous_speaker_vectors`, which verifies that an invalid new lookback raises while the prior state object, frames and key remain intact.
- LOCAL_LINUX isolated negative-control reproduction: **PASS**; the pre-fix ordering loses the prior key before raising, while validate-first preserves it.
- Code/test commit: `0dabbc3a49cf161972750dd5f7faaae26e1248d7`; source blob `5e2b4a88e416cfb92d6c94df7544d0be355cbbe8`; test blob `b819a6e4323a0975e3da80fb67718eeaacbcd36f`.
- Exact-head CI for this additional speaker-registry change: pending at this handoff revision. Do not inherit the previous `de18aa02` results as proof for the new speaker source/test bytes.
