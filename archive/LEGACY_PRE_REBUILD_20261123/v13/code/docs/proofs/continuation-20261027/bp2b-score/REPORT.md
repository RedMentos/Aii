# WP-BP2b blinded scoring checkpoint · 2026-10-27

Owner: automation11 BP2b blinded scorer, PR #707 review-only child of PR #706 exact `dcb0697470395ca7b1a171b4cf1bf112b2a31958`. Prereg before code `b7c7e22bf46666de310c4f7456053b8038a37020`. Source `v13/code/scripts/bp2b_transfer_score.py` Git blob `f3af04eab7514e946960da784c6700f086c9088b`, frozen cohort blob `853660938b55ac1d8ac3a022c942cd99f4fad7e2`.

GitHub Actions `40502360380`, exact head `4bc057fbc52c73c1f955f8bc64d3f297a5bac200`: 21/21 PASS (7 scorer, 6 cohort, 8 locality), compile0, privacy CLEAN. Original artifact `12732464557`, ZIP SHA256 `85b739e8fb16b2202017f62805ea2b360530282bd7b3984c5e6c130a7fa4a3cf`, 1969 bytes, CRC PASS, private Library `/V13-Checkpoints/2026-10-27/BP2b-Blinded-Score/bp2b-score-40502360380.zip` byte-exact after re-materialization.

Behavior: strict JSON, duplicate-key/nonfinite rejection, bounded inputs, exact case_id order, frozen cohort SHA and content verification, separate model-facing vs scoring-only data, boundary-aware answer-key hits, response hashes without raw responses. All outputs explicitly `UNATTESTED_SUPPLIED_PREDICTIONS`, `native_proof=false`, `learning_authority=0`. No model loaded, no adapter trained, no Q4/Redmi evidence.

Next package: pin exact public LiquidAI LFM2.5-1.2B-Instruct FP32 metadata and tokenizer against model SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a`; then implement a native 4-arm source-bound trainer/evaluator, with heavy-owner serialization and independent verification. Exact software replay: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_transfer_score tests.test_bp2b_transfer_cohort tests.test_bp2b_locality_anchors`.

Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL, jepa_weight=0, Redmi unmeasured, V13 whole-system incomplete. PR is review-only; main and production gates untouched.
