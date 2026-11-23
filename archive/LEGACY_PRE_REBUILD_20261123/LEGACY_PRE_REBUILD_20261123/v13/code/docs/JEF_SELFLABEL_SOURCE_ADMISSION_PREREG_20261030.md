# JEF WP-U1 self-outcome training row source admission — prereg 2026-10-30

Exact parent `81ca76bc6637a5f543f364cf7464f3a241ce0bf3`, built on #1193 JEF report-source repair and #1192 native Age0 review; parent full-suite is running independently. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. No registered model/seed/cohort, source pins, Age, JEF authority or optimizer change.

## Problem and fail-first witness
`jefoutcome.training_rows` currently returns a stored self-outcome label based only on state and the ExecutiveDecision packet ID, without verifying the label source is still live and exact. A tombstoned `OUTCOME_SELF_LABEL` can enter the learner's data array; `learning.shadow_readout` later rejects its `read_source` and aborts the whole candidate even when other good labels exist. A substituted live source ID with a different value can also be admitted to `training_rows` until late validation.

Preregister tests in fresh SQLite Runtime, **no native/model**:
1. A real FINAL self-outcome in explicit `learn` mode and no human label yields exactly one candidate, with matching live `OUTCOME_SELF_LABEL` source.
2. Tombstone that label's source: `training_rows` returns empty, not a dangling candidate; the persisted state label remains for audit. Restart still empty.
3. Substitute the retained label's `source_id` with a different live source (even of `OUTCOME_SELF_LABEL` kind) holding a different value: no candidate.
4. Corrupt the retained `decision_packet_id` to a different event's decision with the same component and context revision: reject mismatched event/context identity.
5. Valid unchanged labels, human precedence and existing SkillLive/JEF lifecycle remain unaffected.

Original RED raw evidence retained before repair. Repair should be confined to read-only training row admission: live kind, source bytes/value, exact decision packet/event/component/revision/context identity. Do not delete stored labels or weaken the learner's later source validation. Any unfiltered full-suite historical Run34/Run37 pin errors remain RED, no waiver. No STEP2/B3/Body-JEPA/JEPA/Age/whole-system promotion.
