# Run13Y prereg — AG9 metacognition invalid confidence/label containment (2026-10-30)

Owner GPT-6; review-only child of Run13X checkpoint `7965a39e960d13faf923dd469df8226bd0204a81`. Independent organ: AG9 metacognition, not C3 receipt. Read Canon v10.16.1, roadmap WP-AG9/WP-DS3 and newer decisions. No change to native cohorts, source pins, C3/JEF/JEPA scorers or active model weights.

## Concrete test-first bug

Current `v13/agi/metacog.py` calls `clamp01(confidence)` before recording, where `max(0., min(1., float(nan)))` silently becomes **1.0**, `inf` becomes 1.0, and `-inf` becomes 0.0. It also records `correct=int(bool(correct))`, so the string `"false"` becomes a **positive label**. These can contaminate the calibrated histogram and Age calibration metric without any source evidence. `decide` on invalid numeric input must not imply calibrated confidence.

## Exact isolated fix

Modify only `v13/code/v13/agi/metacog.py` on this review branch: validate confidence is finite and not boolean before clamp; require `correct` to be exact bool or integer 0/1, reject strings/floats and malformed component names before StateBox mutation. Preserve finite numeric values' existing [0,1] clamp for compatibility. `calibrated` on invalid input returns None; `decide` on invalid input returns explicit `INVALID_CONFIDENCE`, `abstain=True`, `second_attempt=False` and no authority. Keep existing support threshold, bins, calibration math, Age gates and valid-data behavior unchanged. No active delivery/learning policy change, no new model or native run.

## Evidence and limits

Test-first RED on real StateBox with a small in-memory Store: NaN/Inf, boolean confidence, string/float labels, blank component, no writes on rejection, valid 20-label calibration, monotonic table, valid `decide`, invalid `decide` fail closed, and no gate promotion. Then GREEN, compile, privacy scan, original raw ZIP with hashes, private byte-verified backup. This is software input integrity only, not AG9 semantic calibration or WP-DS3 usefulness, no STEP2/B3/Body-JEPA/JEPA/Redmi/whole-system promotion. No main merge before independent review. Exact next step: add failing tests first, run focused CI, patch AG9 and revalidate.
