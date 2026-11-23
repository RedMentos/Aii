# JEF live-current F1/F5 two-source atomic-read SHADOW preregistration — 2026-10-31 UTC

**Owner:** GPT-6; isolated review branch `assistant/v13-jef-current-source-atomic-gpt6-20261031` from verified Run61 `0d0189d52c48af80c76e690e0bcf4904c7f3a459`. Preregister before implementation/tests/CI. No change to existing `:jefsource` historical operator, `jef_f1f5_source_admission.decide`, `jef_typed_source_shadow`, P2X cohort or any source/model/seed/scorer.

## Need and hypothesis

Existing JEF F1/F5 typed two-source admission verifies policy/sheet HumanDecision lineage and supports historical event-ID replay. For a **live-current** decision boundary, a source-correct older USER event must not remain eligible after a newer authoritative USER event in the same session. Historical replay is still valid for diagnostics; do not redefine it as live delivery. New default-OFF `v13/jef_f1f5_live_current_candidate.py` uses one Store transaction for latest-authoritative-USER check, exact current SourceRef, original `admission.decide` and read-only postcheck. Never calls a model, changes weights, writes a message, commits output or authorizes an action.

## Frozen cohort and negatives

- Reuse unchanged 36 P2X calibration fixtures (two archived human F1/F5 source memories per case, exact policy/sheet), expected 36/36 typed `A|B|NONE` proposals in SHADOW. This is software revalidation of existing known cohort, **not** a disjoint utility claim or native proof.
- At least 36/36 stale-current negative controls: after each successful query, insert a new authoritative USER event in the same session and invoke the live-current candidate on the older query. Must return `UNKNOWN`, not the old action; the historical `admission.decide` may still return its old proposal (negative control).
- Other negatives: no opt-in, integer `1`, forged approval receipt, wrong current SourceRef, wrong session, revoked sheet, conflicting hidden active source, and source mutation during decision. All fail closed with zero writes and zero model/native/tool/learning authority.
- Preserve existing 36 positive / 144 negative JEF F1/F5 source admission suite as regression.

## Boundaries and acceptance

Real SQLite, actual Store SourceRefs and HumanDecision records; no model call, no native/Redmi, no TTY, no live Runtime install. A `live_current_verified` marker is **not** a permission token. Require software tests, exact pinned source and fixture, privacy scan, diff check, closed raw SHA256 manifest, private byte-verified backup. If any stale event returns a proposal, retain RED and do not wire to live output. Historical `:jefsource` remains unchanged. No STEP2, B3, Body-JEPA, JEPA weights, age or whole-system promotion.

**Exact planned command:** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_jef_f1f5_live_current_candidate tests.test_jef_f1f5_source_admission tests.test_jef_typed_source_shadow`. Next step after evidence: consider a separately approved C2/JEF→C3 typed envelope, not automatic delivery.
