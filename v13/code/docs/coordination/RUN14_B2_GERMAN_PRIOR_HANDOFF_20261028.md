# Run14 German earlier-rule B2 shadow — verified handoff, 2026-10-28

**Review-only PR #926** (child of #925), prereg `4a3df0b8ac6b11364f6b275e42a32fbea8910772`, source tested `16f1141ad2049af2d6814cb3d02fa21439210e9a`. No production merge, no change to frozen Runtime or original TP/s27 native cohort.

**Functional software change:** explicit German `frühere Regeln` can prioritize the older, source-verified project rule excerpt over a newer supplier sheet under the unchanged bounded B2 context; current/revised rules do not trigger it. Only lexical *presence* of rule words is scored, not their values, and the Run13 single-project/source/tombstone/model/slot guard is reapplied. A selected pointer is not a model quote or decision.

**Evidence:** Actions `40699618294` SUCCESS, 33/33 focused, 2459 full OK (1 skipped), compile/privacy/diff PASS; ZIP SHA256 `f937ee53aee529816f45d7ce0224e796f275e76a5f41dea29dc13a1b48f63a6b`, CRC and 18/18 inner SHA256 clean. Private Library `/V13-Checkpoints/2026-10-28/Run14-Handoff/RUN14_GREEN_40699618294_shaF937EE53.zip` byte-identical on readback. Original RED-first Actions `40699470240`, ZIP SHA256 `1cf4ce0728072344830e7f8ddeee0c0ff8b01075f105546b1d0c80d066c72956`, preserved and privately byte-verified.

**Open questions / next:** Does actual B2 quote the old rule when shown this pointer? Does C3/JEF use it correctly without stale-rule authority errors? Run15 is independently preparing disjoint EN/DE long-note fixtures; native arm/seed runner and model-source preregistration are still missing. Do not integrate this cue live until a fresh native utility/ablation comparison and false-positive review. Focused command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_run14_b2_german_prior_cue tests.test_run13_b2_identity_ambiguity_guard`.

**All gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 incomplete. Remaining execution budget UNKNOWN.
