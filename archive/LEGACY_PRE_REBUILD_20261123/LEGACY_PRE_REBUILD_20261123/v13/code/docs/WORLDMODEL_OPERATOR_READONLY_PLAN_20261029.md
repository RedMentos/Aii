# WP-T8 operator read-only integration plan (2026-10-29)

Parent review branch PR #1140 head `35330b85f21aa837ed754eed6b879909e5b8364b`; this child is an isolated review candidate, not production integration or a change to a frozen SourceHandoff cohort. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` remains binding.

**Functional gap:** World-Model already fits persisted own action outcomes and exposes `report`/`for_event` as Python APIs, but the local operator's existing `:world` shows self/world state rather than the learned World-Model's actual prediction/evidence. Add a separate, TTY-only `:worldmodel` read-only command, without modifying `:world`.

Contract: `:worldmodel [status]` returns `world_model.report(store)`. `:worldmodel event <Event-ID> <simple|detail|gist|both>` first proves the event belongs to the operator's currently selected session and then calls `world_model.for_event`. Foreign and nonexistent event IDs have indistinguishable errors. No fit, state writes, learning rights, model calls, tools, external network, or new prediction authority. All predictions remain `HYPOTHESIS`, `SELF_CAUSED`, never a causal/real-world guarantee.

Verification: software tests must cover unfitted status with no state change, actual Store `ActionSelection` + `CorollaryCopy` + `ActionOutcome` → `WorldModel.fit` → TTY report/event prediction with state/packet/action counts unchanged, unknown/foreign session veto, malformed arguments, Age0 RECORD_ONLY, and no runner processes. Run existing World-Model tests and privacy scan. A separate real-Store integration test verifies persisted World-Model survives a Runtime restart. These are synthetic own digital actions through real Store APIs, not real model/Redmi measurements. No STEP2/B3/Body-JEPA/LP3 or whole-system gate promotion.

Original `v13/code/v13/operator.py` and `v13/code/v13/world_model.py` are preserved on the parent; any child source change is an isolated review candidate until explicit integration checks. User-authorized TTY only.
