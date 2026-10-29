# Context OS warm reactivation must follow FINAL delivery — preregistration

UTC 2026-10-29. Review-only child of PR #1133 at `f1af2f174c1b6d3ef416dc346ebd998f9a4061bb`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No active learning, native/Redmi proof, gate promotion, model/source/cohort pin change or live activation.

## Observed source-level failure path

`ContextOS.observe(event_id, role, metrics, status, memory_ids)` currently unconditionally refreshes `warm` for every supplied memory ID, even when the observed answer status is `CANCELLED`, `ERROR` or `PROVISIONAL`. The runtime normally calls `observe` after FINAL, but the API explicitly accepts non-FINAL statuses (and already rejects non-FINAL cache-cost credit). An interrupted/non-delivered answer must not update the activity-silent warm-memory policy (§9.1, W6 no provisional learning).

## Frozen test cases and success criterion

1. Fresh authorized F1 memory + CANCELLED observation without a context plan: memory must not enter the warm set; an actual FINAL observation must still warm it.
2. ERROR and PROVISIONAL statuses must not warm any memory, even if the caller supplies IDs.
3. A previously warmed memory that decayed below the admission threshold must not be reactivated by a CANCELLED observation.
4. Preserve the existing no-plan FINAL warm behavior and all existing Context OS tests. No memory source, HumanDecision, feedback or provenance change.
5. Focused CI must run the new tests and original `test_context_os.py` (plus current Context OS singlequote tests), compilation, public privacy scan and `git diff --check`. Preserve original RED raw and corrected GREEN raw. Full-suite inheritance is not a gate promotion.

## Minimal authorized candidate

Only guard the `warm` state mutation on `status == 'FINAL'`. Keep cache metric admission/receipts, `warm()` source/permission verification, runtime defaults, SHADOW/ACTIVE authority and data schema unchanged. No persistent schema migration required. Source stays on a new review branch; original negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED and V13 INCOMPLETE.

Owned paths: `v13/code/v13/context_os.py` (warm status guard only), `v13/code/tests/test_context_warm_final_20261029.py`, `.github/workflows/v13-context-warm-final-20261029.yml`, this prereg and dedicated BUILD_STATE. The earlier Context OS exact-span change remains byte-identical.
