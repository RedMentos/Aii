# Run378 — B3 Callosum must distinguish signed numeric evidence (preregistered)

Parent: verified Run375/PR370 checkpoint `0be1eac772c5db165099e4be795a8ae563d278bc`; independent of Run377 Context OS owner and Run373 native C3. Review branch, not main.

Owned: `v13/code/v13/callosum.py`, new `v13/code/tests/test_callosum_signed_numeric_run378.py`, isolated `.github/workflows/run378-callosum-signed-numeric.yml`, this proof directory. No changes to B3 learned utility, calibration, channel ladder, latent gates, Age or model/source hashes.

Observed bug: `NUM=re.compile(r'\\d+(?:[.,]\\d+)?')` strips signs. `signed_gain` then considers an exact-evidence sender claiming `-4` to **agree** with receiver claiming `+4` or `4`, amplifying a contradiction across hemispheres. This directly violates B3-H3 signed suppression intent and source fidelity.

RED-first software tests: `-4` vs `4` and `+4` with source evidence must yield signed_gain -0.5 and reason EXACT_EVIDENCE_CONTRADICTS_RECEIVER; `-4` vs `-4` and `+4` vs `4` must agree; without source evidence a contradiction must remain neutral (no unverified suppression). Existing multi-digit decimal, nonnumeric and inherited Callosum tests remain green.

GREEN: include optional leading +/- only when it is a genuine numeric sign (not a hyphen in a word/range) and normalize explicit leading `+` to the same magnitude as unsigned. Preserve negative sign and all existing signed_gain rules. No semantic numerical reasoning or native B3 claim.

Evidence: source-bound RED/GREEN Actions, inherited Callosum tests, compileall/privacy, raw SHA receipts and private Library byte comparison. STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole V13 remain NOT_PROMOTED.
