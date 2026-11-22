# JEF report decision-lineage binding — preregistration 2026-10-30

**Owner:** GPT-6. **Review-only child:** current-chain PR #1237, exact starting SHA `0b6fb758828c2834a45c9879191a7854ac96060f`. Scope: JEF report read model only. Frozen Canon, model/source/seed/cohort hashes and all negative gates unchanged.

## Predeclared defect hypothesis
`jefoutcome.report()` currently verifies a retained self-outcome's live byte-exact source and verifies the human feedback receipt against a fetched ExecutiveDecision, but does **not** bind that fetched decision to the retained self-outcome's original event/component/context revision/context digest/baseline. If a retained label's `decision_packet_id` is substituted with another event's valid decision carrying a valid human receipt, the report may count false human overlap/agreement. Training-row admission already binds these fields.

## Frozen software test plan (before patch)
Use a fresh temporary real Store/Runtime with no native model. Event A: a memory decision, FINAL, retained `skip` self-label and valid human `skip` feedback. Event B: another memory decision, FINAL and valid human `skip` feedback. Verify baseline A counts one live label and one human agreement. Then independently mutate only one retained label field at a time, keeping its original live self-source unchanged:
1. Replace A's `decision_packet_id` with B's valid decision ID. Expected human_overlap=0, agreement=None.
2. Change A's `event_id` to a distinct event ID. Expected human_overlap=0.
3. Change A's `context_sha256` to a distinct 64-char digest. Expected human_overlap=0.
4. Change A's `context_revision` to a different revision. Expected human_overlap=0.
5. Change A's `baseline` to a different baseline. Expected human_overlap=0.
All historical `labels` and byte-valid `live_labels` remain 1; no learning, tools, native process or gate promotion. The first and several additional cases should fail on original source. Preserve original RED evidence if CI available.

## Patch contract
Read-only report decision validation must require exact stored packet ID, event ID, component, context revision, context SHA256 and baseline equality before joining to a human receipt. No change to `training_rows`, `after_turn`, source bytes, human receipt admission, existing historical counters or authority. Preserve Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA unavailable, jepa_weight 0, Redmi unmeasured, full-system incomplete.

## Evidence and next
Run targeted existing JEF self-source/human-receipt tests plus new adversarial tests in pinned isolated GitHub Actions, compile, privacy and diff check. Record exact SHA/run/exit codes and original raw artifact if available; no claimed GREEN without test output. After verified remote checkpoint, proceed to another independent organ package rather than stopping.
