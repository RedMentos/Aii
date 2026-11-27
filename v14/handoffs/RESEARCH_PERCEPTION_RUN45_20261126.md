## Research & Perception Run 45 — session-stratified A4/A5 information probe (2026-11-26T15:15:28+01:00)

**Owner:** Research & Perception. **Branch:** `research-perception/v14-audio-temporal-window-order-20261126-run41b`. **PR:** [#2527](https://github.com/RedMentos/Aii/pull/2527), DRAFT, currently stacked on Perception #2524. **Current PR branch HEAD:** `c9fb9212ac8f8f3bd7a5fedfd506cc22d70ded2d` (docs-only checkpoint after tests). **Tested code/test HEAD:** `4d1dc7a3315c8fec0016d1162f361f431ee0a4c1`.

**Concrete defect / Canon path:** the A4/A5 shadow feature-set probe conditioned acoustic feature/action information only on goal, required one globally monotonic timestamp sequence, shuffled outcomes across sessions, and computed self-predictive MI across session boundaries. That can reject valid independently clocked sessions and allow between-session feature/outcome confounding to look like within-session predictive value. Canon paths: A4 salience/attention, A5 source-bound PerceptPacket, active perception evaluation; no learning authority is implied.

**Implementation:**
- Validate strictly increasing windows *within each session*; a new session may restart its local clock at zero.
- Condition single-feature and joint feature/action CMI on `(session_id, goal_id)`.
- Permute outcomes only within the same session × goal strata.
- Compute feature self-predictive MI within each session, weighted by its adjacent-pair count; expose per-session values and explicit conditioning metadata.
- Balance the synthetic fixture independently in each session × goal stratum; add a negative control where feature/action correlation exists only between sessions.

**Exact code:** `v14/experiments/audio_feature_set_probe.py` blob `c59f3b4387434b4c0c5f0c14dea052ee047c9f10`; test blob `3f568b0323cf2a3cdd9eb29c69358bbee7d0d6cf`. The prior failed CI attempt exposed an unhashable-dict bug in the new self-MI calculation; fixed by computing over the hashable feature tuples, then retested on the exact head above.

**LOCAL_LINUX:** CPython 3.13.5 scratch-equivalent session-stratification tests **4/4 PASS** (reset clocks, within-session monotonic rejection, synthetic XOR synergy, between-session confound rejection). The full Aii checkout is not mounted, so the exact repository test file/full suite was **NOT_RUN locally**.

**Exact GitHub Actions on head `4d1dc7a`:**
- [Feature-set probe workflow 45836865270](https://github.com/RedMentos/Aii/actions/runs/45836865270): **15/15 PASS on Python 3.13 and 3.14**, including the actual repository RAW EAR extractor → A5 PerceptPacket producer integration test.
- [Model-lab workflow 45836865202](https://github.com/RedMentos/Aii/actions/runs/45836865202): **58 tests PASS**, 4 optional native/WebRTC tests skipped because the pinned libfvad shared library / test-only WebRTC wrapper was not built/installed.
- Same model-lab run: **latent-cache-tiny 3/3 PASS**; [offline bridge security 45836865242](https://github.com/RedMentos/Aii/actions/runs/45836865242) PASS.
- These are GitHub-hosted Linux CI results, not local full-checkout tests, Android, native GGUF inference, learned weights or Redmi evidence.

**Scientific scope:** the diagnostic remains synthetic-only. It is an acoustic-feature → later-action proxy, not Heintz et al.'s exact AAD rIMI/CSD estimator; no real A4 prediction-score vector or trusted attended-speaker state exists in the normal Runtime consumer yet. It does not change attention policy, JEPA, weights, Runtime routing or permissions.

**Cross-lane blocker:** parent #2524 exact staged/integrated still fails at the Core-owned `NATIVE_FILES["v13/native_latent_receiver.py"]` pin. Current #2524 branch head is `772d38114d5718034ca303a0de377e9afe9eff83`, receiver blob `3ce4f71bc6fb2a2e8d1260c5fa14582cb7740964`; #2525 still carries `640349157839e0f18559f34a775827abb13df44a`. Perception posted the exact comparison to Core PR #2525 (comment 7194494606); Core owns the refresh. No Core recovery/stage/deployer files were edited. PR #2527 still has stale base SHA `b298719af8faf75811d03d486de7725395a590b0`, is DRAFT / mergeable=false, and is NOT_RELEASED.

**Upstream inference note R-167:** llama.cpp issue #29002's original LFM2.5 multi-sequence truncation report was later challenged by a harness indexing bug; after the harness correction, F32 LFM2.5-350M was 12/12 byte-identical and Q4_K_M had numerical differences but no short outputs. A separate single-sequence checkpoint report and PR #30666 concern SWA checkpoint invalidation, not proof of a recurrent-state defect in V14. See the dated R-167 ledger entry. Keep LFM2 execution serialized until the exact pinned model/quantization path is independently measured; do not claim the original report proves recurrent corruption.

**Device / deployment:** private V13OBS #115 remains historical (2026-11-24 09:28 UTC). New read-only owner-relay requests #974 HEALTH, #975 PIPELINE_STATUS and #976 DIAGNOSTICS were created with ten-minute expiry; all had no device comments at 14:16:18 UTC. Record **NO_LIVE_RECEIPT**; current Redmi runtime/updater state is **REDMI_UNVERIFIED**. No UPDATE_REQUEST, CHAT_SEND, restart, model/weight/permission/data mutation or deployment occurred. B3 OFF; NOT_RELEASED.

**Next executable step:** Core refreshes #2525 against #2524's current parent and recomputes the pin chain; then Perception rebases #2527 onto the refreshed parent. After that, the real missing prerequisite is a normal-turn A4 predictor score vector plus a trusted, separately sourced attended-state label, with ≥5-minute temporal separation, session holdout and switch-focused controls. Until then the proxy remains diagnostic-only.

**Nutzeraktion: keine Aktion nötig.**

