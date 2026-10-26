# Run620 — persistent operator-only answer-language control (acceptance contract)

2026-10-26 UTC. Review-only child of Run619 PR614 exact head `18a749dc6ad210ca39ef2a56eb4c618354dbb1bd`. Separate ownership: `v13/code/v13/operator.py`, new `tests/test_language_operator_run620.py`, new Run620 workflow/proof only. No active Run618 native/model/cohort edits.

User decision 2026-10-09/11: English-first Age-0 and later observable German learning; current `config.DEFAULTS.answer_language=en` and `prompts.TEXT[en/de]` already exist. This package exposes **explicit local operator selection**, not language learning, auto-translation, or a new language model.

Acceptance contract before code:
1. `:language` or `:language status` reports configured language without mutation.
2. `:language de` and `:language en` atomically save the existing validated `answer_language` setting and affect only subsequent turns; require runtime idle, so never switch language mid-answer.
3. Restart reads the same language from settings; existing default remains en for a fresh home. Existing model prompt templates and source/approval policy are unchanged.
4. Reject unknown/multiple arguments, non-local command origin, and busy runtime without persisting any change.
5. Log an explicit operator configuration change with previous/new language; no change to Age, learning, model/runner pins, tool permissions, or receiver authority.
6. Actual SQLite Runtime tests verify default/status/change/restart/reject/busy/telemetry and existing source-only prompt regression. No native/Redmi claims.

Source-only feature. Gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE. No main integration. Tests must distinguish local Run601-source overlays from exact-head CI.
