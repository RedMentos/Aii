# Run623 — atomic idle-only operator config changes during native turns

2026-10-26 UTC. Review-only child of Run622 PR617 at exact head `4dd297e74ddd218848e05578a9834ea152d6bb90`. Owner `v13/code/v13/operator.py`, new `tests/test_operator_config_atomic_run623.py`, new CI/proof only. No frozen Run618 model/cohort or main changes.

Observed source defect: `:semantic off|shadow|on|auto`, `:sampling anti_echo|legacy`, `:duplex auto|interrupt|off`, and `:effort disabled|low|adaptive|high|max` change active generation/retrieval/control policy **before** the common `r.require_idle()` gate. A user command can therefore mutate config/state during a live turn, while the per-turn source/effective-config snapshot was already captured. This package is a bounded consistency correction, not a new learning/authority feature.

Acceptance contract:
1. Read-only status/query forms of these four commands remain available during a busy turn and do not change config.
2. Every mutating form requires idle **inside the runtime lock** before any persisted or in-memory change. Busy turn, queued job or shadow job must refuse with no partial change.
3. On idle, valid changes persist through restart and still use the original validated config/state paths. Invalid args never mutate; no new Age, tool, training or model rights.
4. No change to native inference, deadline, source references, default language, model weights, registered cohorts or permissions.
5. Real SQLite Runtime tests cover busy refusal, idle success, restart, invalid/no-op and unchanged source/learning/age gates. Source-only CI preserves raw failure and privacy.

No STEP2/B3/Body-JEPA or Redmi promotion. Negative gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.
