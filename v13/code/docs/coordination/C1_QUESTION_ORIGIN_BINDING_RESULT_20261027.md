# C1/JEF unresolved-question origin — RED/GREEN checkpoint 2026-10-27

Review-only child of C1 goal-sequence branch at exact parent `b29c0436e5c39c2bda9ab6711b1437725a6c110f`, ultimately PR #776, not main. Prereg commit `c039da2893dd8d9aa15680c713cf8d55223966d0` precedes RED test commit `b2de32645c96dffd1045ab31975876c1b42feb7f` and source fix `1252182cb9fff339d1992ffc18235e9c3b84d657`. No frozen model/source cohort or production merge modified.

## Proven failure and fix

Previously `Executive._question_valid` accepted a persisted `open_questions[].source_ref` merely because it was a valid source, while the referenced stored `OfferPacket` belonged to the same session. It did not require that the question source equal the offer's actual authoritative originating event. A foreign-session source, a mismatched same-session source or a newer event's source attached to an older offer could therefore enter `report_context.unresolved_observer_hypotheses[].source_request`. The new guard requires exact authoritative same-session event/source/generation binding and the source in the offer provenance. Genuine unresolved questions survive later turns.

## Closed focused evidence

- **RED Actions 40588749361**, expected FAILURE: 30 tests, 3 new failures, 27 pass. Original ZIP artifact `12771109745`, SHA256 `2141d8e6e3b51f48f199d2e894dbc08bbae9e49fcc384f57d9565ef29138cfab`; HEAD `9d2bb2916bc1a117a84e21e3f89e5056de58d093`; SOURCE_BLOB `e42e586b7e685cf3b0abc80a17c203bfc7dfc845`, TEST_BLOB `f1d081392cddc7b4bf69bf1d4bcf527b9699f974`. PREREG/INSTALL/COMPILE/PRIVACY/DIFF exits0, UNIT exit1; CRC PASS.
- **GREEN Actions 40588859650 SUCCESS:** 30/30 PASS, all PREREG/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. Original ZIP artifact `12772992407`, SHA256 `ad8d25f3bec6aa85e07206dff9d8b6408548b3c4e5c635822fda99682adf73b2`; HEAD `1252182cb9fff339d1992ffc18235e9c3b84d657`, SOURCE_BLOB `057dda1e705053047489516fc9ab10581018f5a4`, same test blob. CRC PASS.
- Both original raw ZIPs privately saved and independently re-materialized SHA256 byte-identical at `/V13-Checkpoints/2026-10-27/Automation11-C1-QuestionOrigin/`; not the rejected anyone-writable Drive destination.
- **Full source-wide Actions:** workflow `.github/workflows/c1-question-origin-fullsuite.yml` queued/running, raw result pending at this checkpoint. No full PASS claimed yet.

## Gates and next command

Evidence is Linux software/synthetic DB only, not Redmi/Termux, native model, semantic utility or production integration. LP1/LP2/BJ1/STEP2/B3 negatives, `jepa_weight=0`, `age_authority=0`, full V13 scope unchanged/incomplete. Independent review required, no auto-merge. Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_executive_question_origin_binding_review tests.test_executive_goal_sequence_binding_review tests.test_executive_task_origin_binding_review tests.test_executive_source_action_integrity_review tests.test_executive`. Next: inspect raw full-suite exit codes, close evidence, then return to distinct canonical roadmap packages.
