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
- **Exact-head CI:** must be read after this commit; do not inherit the prior #2491 runs as proof for this new head.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No connected phone, microphone capture, private relay, UPDATE_REQUEST, shell, model/weight/permission change or user-data mutation was performed.
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
