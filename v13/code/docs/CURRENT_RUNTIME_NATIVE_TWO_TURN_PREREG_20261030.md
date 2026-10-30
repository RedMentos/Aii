# V13 current-chain real Runtime native two-turn integration — prereg 2026-10-30

Review-only child of verified #1191 at `2895f9a52aded6d7d84846fd79c5664b53eeeff6`. Owner: automation; new `scripts/current_runtime_native_two_turn_20261030.py`, dedicated software tests/workflow, no edits to canonical Runtime or registered model/seed/cohort/source hashes.

## Purpose and bounded hypothesis
The individual current-source Linux-native smokes for C2, B1, B2 and C3 have each passed, but **none prove the actual Runtime/JEF information flow**. Test a fresh Linux x86_64 Age0 RECORD_ONLY Runtime with all four immutable official models and pinned native runner, in a two-turn synthetic conversation:
1. Auto-route `Budget 120 Euro. Berechne die Hälfte.`: attempt a real C2 Needle3 control proposal, then B1/B2 observer offers and one native output under C5/JEF. Record the *actual* route and roles; do not force a route if C2 is uncalibrated or rejects it.
2. Operator route override `simple`, prompt `Hello.`: test actual C3 native output through the same Runtime/JEF output broker. This is a **two-turn** connected integration, not a claim all organs participated in one turn.

No external tools, network after artifact installation, human data, paid provisioning, self-edit, learning or Age promotion. Native assets are downloaded into fresh scratch with current catalog SHA256 and licenses, model-manager exact revisions and native binary hashes; no weights in artifacts. Limit threads=2, per-turn deadline<=180s, one job at a time, 1MiB raw log caps, explicit memory/disk preflight and process cleanup.

## Acceptance and negative controls
Preserve original native logs, source/model hashes, exact event IDs, SQLite packet kinds and native metrics, raw stdout/stderr, timestamps, output status and SHA256. A **partial** turn, missing body offer, C2 rejection, fallback, ERROR/DEADLINE or missing C3 output is recorded as **RED or PARTIAL**, not silently promoted. Distinguish Linux native from Redmi, software from model utility, and keep STEP2 UTILITY_FAIL, B3, Body-JEPA, `jepa_weight=0`, Age0 RECORD_ONLY and whole-system completion false. The workflow must upload raw even on RED.

Prerequisites: pinned official models C2 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`, C3 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, B1 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, runner tar `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Do not change registered artifacts. Runtime budget UNKNOWN.
