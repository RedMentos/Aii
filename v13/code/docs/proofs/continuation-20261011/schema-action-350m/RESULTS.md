# Generic native schema action diagnostic — LFM2.5-350M

All 32 preregistered native calls completed with raw observations. The isolated server was reaped and actual model, launcher and adjacent runtime-library hashes remained unchanged. This is a cloud semantic diagnostic with one server CPU thread and concurrent Dream/tap workers; timing values are observations, not comparable latency or Redmi evidence. The original 70-case STEP2 report is preserved and remains UTILITY_FAIL.

| Arm | Explicit copy: correct action | Explicit copy: complete requested output | Arithmetic: correct action | Arithmetic: complete requested output |
|---|---:|---:|---:|---:|
| Schema-free JSON | 4/4 | 0/4 | 1/4 | 0/4 |
| Action-only enum | 4/4 | 4/4 | 2/4 | 2/4 (action only) |
| Full schema, action first | 4/4 | 4/4 | 1/4 | 0/4 |
| Full schema, facts first | 3/4 | 3/4 | 1/4 | 0/4 |

All four enum values can be emitted correctly in the action-first and action-only copy tasks. The observed original NONE-only collapse is therefore not a fixed prohibition of A/B/UNKNOWN by this model, template or enum grammar. Facts-first is worse on one copy case: an explicitly requested NONE becomes UNKNOWN. Schema-free copy responses append an extra `task` key, so they fail the unchanged strict whole-object score despite their correct action values.

The two full-schema arms have identical parsed constraints, input messages, sampling settings and token budget. Their wire property order actually differs, and the native answers follow that order: action/eligible/remaining versus remaining/eligible/action. This validates that the control reached the decoder. It does not establish benefit: both fail every complete arithmetic result, and neither produces the correct A or B choices. Schema-free and action-only controls also fail those two positive-choice arithmetic tasks. These failures occur on new simple generic inputs, without STEP2 analyst offers or hidden prior-rule dependencies.

Consequently, no production schema-order fix is recommended from this evidence. The source-audit hypothesis remains plausible as a general handicap but is not supported as the main cause here. The demonstrated problem is broader instruction/decision quality in the current tiny C3 under this fixed diagnostic prompt. An identical diagnostic against a stronger already installed Instruct model would help separate prompt/task difficulty from model capacity; it would be a separate model control, not a retrospective repair of the original acceptance cohort.

Evidence: `report.json` contains actual messages, template responses, request wires, output key order, raw native responses/tokens and exact per-row scores. `summary.json` independently aggregates the saved rows. Report SHA256: `28a6ad5158ca1b49979221a0c6ad4a07276ea62d592527c00734f7eb9d2de440`. Six offline contract tests pass. No runtime, model, shared library, installed config, adapter, authority, acceptance fixture or oracle was changed for this diagnostic. Diagnostic completion is not semantic utility PASS, training or activation.
