# HB0b source-view / blind-arm export — preregistration (2026-10-29)

Parent: `21f7337dd681edba06637c0b9b93fd81b218750d` (HB0 PR #1047, software-only pending CI). Owner: V13 automation. Committed before implementation. Independent child; never edits frozen runtime or original cohorts.

## Problem

HB0's deterministic fixtures contain `oracle_action` and internal `sheet_index/rule_index`. Passing a raw fixture to C3 would leak answers and invalidate P0. Build an executable **source-view firewall and replay export** so the model-facing payload contains only explicitly authorized text, and the answer key is a separate scored artifact. The public synthetic cohort remains NOT blind and cannot prove model generalization.

## Contract

New `scripts/hb0_arm_export.py` consumes the original `hb0_split_information_cohort.fixtures()` and refuses source/cohort drift via its canonical SHA256. It renders exact matched arms:
- `c3_only`: current request, no historical values.
- `b1_only`: current + authentic recent B1 sheet.
- `b2_only`: current + authentic B2 rules note.
- `both_exact`: current + both authentic source texts, with source provenance.
- `single_body_dual`: identical source information as both_exact, but packed as a single-body context control.
- `shuffled_b1`: current + B2 rules + a B1 sheet from a different project; must not silently relabel it as the current project.

All arm payloads have a fixed system instruction and user text; no oracle, sheet/rule index, action, budget/option values in `c3_only`, no source-value leak from an unselected organ, no hidden answers in metadata. Preserve project headers for source identity. An exporter writes *fresh* separate `prompts.jsonl`, `answers.jsonl`, `manifest.json` with SHA256 of exact bytes and complete row/arm coverage; answer file is explicitly forbidden as model input. Reject pre-existing output directory. No model call, model download, tool activation or native measurement.

## Predeclared tests / falsifiers

1. 150 x 6 = 900 prompts, six matched arms per fixture, exact IDs and family-disjoint calibration/structural-holdout split; stable deterministic bytes and hashes.
2. No oracle or hidden task axes in any model-facing JSON; current-only contains no rule/option values; b1_only and b2_only each lack the other source.
3. `both_exact` and `single_body_dual` contain identical source values; shuffled B1 is explicitly foreign, and the exact source guard must abstain when authentic B1 is absent.
4. A negative test must catch oracle contamination, wrong-project source substitution, duplicate arm, corrupted manifest and existing-output overwrite.
5. Tests/compileall/full suite/privacy on pinned source head; retain failed raw. No registered cohort changes.

## Claim limits

This is a data-path/contamination preflight, **not** real model performance, a learned C3 consumer, native STEP2, independent heldout, or a new proof gate. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE. Real P0 requires a fresh private model cohort and a C3-alone vs oracle comparison, then same-source B1+B2 vs one-body-two-timescales and shuffled controls with real weights.
