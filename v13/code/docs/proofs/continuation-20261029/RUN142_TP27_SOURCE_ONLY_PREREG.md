# Run142 prereg — cross-cohort TP/s27 source-only B1/B2 fusion control

Date 2026-10-29. Owner `codex/v13-run142-tp27-source-only-crosscohort-20261029`. Exact parent Run140 PR #1041 GREEN at `cc8796f02f7fd10929fc3b0d1af45a93911cef3d`; Run140 42-row source-only candidate remains unchanged. This package is **software replay on an already observed native cohort**, not a new native run or prospective held-out utility proof.

## Frozen source and provenance

TP/s27 single-arm native donor PR #916, exact Actions `40685405624`, source HEAD `fa76c7599fc066b7cb2d58b133a649bd9604ded9`, artifact `12817780450`, original ZIP SHA256 `965bf4ef904cf96c759e1324b74c23662b03f1aa1c5c4698be71e9f5bb9db635`, CRC CLEAN, 29/29 SHA256SUMS and all 12 exits zero independently verified. Source JSON `step2_TP_s27.json` SHA256 `3c4e9aada921da8a35b43b69f720757369777d4ab8242e30f7067314f758e1d9`, tool JSON `tool_TP_s27.json` SHA256 `7e1a7c1fd11116a8fce4a9431e25a9bd9721d9e0306d20f51dd49db0c370bcb6`. Fixture SHA256 `b721650791284e4369d440d494de4aaf76da35fe4be11e34cb87bba1285e4040`, registered seed 27, exact 10 fixtures Aquila/Bellatrix/Cetus/Deneb/Erebos/Fomalhaut/Ganymede/Hyperion/Icarus/Janus, seven variants each = 70 source + 70 tool rows. B1/B2/C3 model/runner hashes, fixture/seed/variant protocol and original failed attempts immutable. Linux native only; Redmi unmeasured.

## Predeclared algorithm and controls

Re-use unchanged Run140 `decide_source_only` on TP/s27 **only after** strict original raw SHA, fixture, variant, source-row hash, source-ref and exact B1/B2 verified-quote checks. Do not pass C3 output, oracle, model hypotheses or unverified source into decision. Require a complete exact B1 option pair and unambiguous source-verified B2/current rules; otherwise UNKNOWN/ABSTAIN. If any source schema/provenance mismatch, fail closed and preserve RED; do not loosen original guard to make results look better. Count all 70 rows including both_exact, both_control, both_none, B1-only, B2-only, same-policy and prompt-only. Score against oracle only after decision; report committed/wrong/abstained/action-exact by variant. Original TP/s27 tool replay is a separate comparator, never substituted for source-only predictions. Any wrong committed remains explicit RED; no promotion.

## Post-observation disclosure / non-promoting hypothesis

The native TP/s27 results were inspected before this prereg: tool utility B1-only .633333, both_exact .341667, both_control .383333; both_exact 0/10 exact, 10/10 UNKNOWN, zero wrong committed. Verified source access in both_exact had B1 options in 9/10, B2 rules in 3/10 and joint access in 2/10; both_control joint access 4/10. Therefore the source-only control may improve *some* C3 extraction failures but cannot demonstrate unique B2 timescale learning, and source access itself is a likely bottleneck. These are descriptive prior observations, not fresh held-out success.

## Acceptance

Add isolated `scripts/step2_tp27_source_only_control.py`, focused tests for frozen 70-row replay, source tamper, wrong fixture/seed/variant, missing/duplicated rows and no oracle input to decision. Exact-head branch-only CI downloads original Actions artifact, verifies all 29 raw hashes and source/tool SHA256, runs focused/full/privacy/diff, archives closed SHA256SUMS including RED. Preserve original Run140 source/tests and negative gates. No new native/model/Redmi calls, runtime edits, weight updates, Age authority or gate promotion. STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, Age0 RECORD_ONLY, jepa_weight=0, V13 INCOMPLETE.

Next after verified checkpoint: compare B2 rule coverage and C3 rule extraction on fresh registered 12-arm/3-seed cohort with independent controls; separately pursue STEP3 second-attempt and JEPA causal utility rather than endless helper work.
