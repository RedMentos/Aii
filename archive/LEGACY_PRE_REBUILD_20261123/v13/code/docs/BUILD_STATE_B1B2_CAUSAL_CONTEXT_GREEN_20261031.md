# B1/B2 causal and strict project-scope context audit — software GREEN 2026-10-31 UTC

Owner GPT-6, independent review-only child of current verified chain `dc2dd656315d3bc4d1ec286afc5858c8b3df8a20`; original Run52 `cognition.py`, seed479, native runner/scorer, model and Canon pins unchanged. Precommitted hypothesis `B1B2_CAUSAL_CONTEXT_AUDIT_PREREG_20261031.md` at `a3aa785cfc425288b2e2ea48359e32fd2b022ae7` before code.

## Two concrete software findings and isolated candidate

1. **Temporal replay leakage:** frozen `Cognition.body_context` and `b1_recent_context` can pass a **newer same-project** retained OfferPacket source into an older USER event if that event is re-entered/probed. They check same event/session/generation/model/topic but not event order. This is a replay/probe hazard; not proof normal forward-only Runtime does it.
2. **Cross-project false matching:** `memory.entities` interprets generic `project rules` as entity `rules`. Harbor prior and Willow current both contain that phrase, so the frozen Cognition path imports Harbor source into Willow despite distinct project names.

New isolated `b1b2_causal_context_candidate.py`, default OFF and not wired into `Cognition.offer`: checks authoritative current/retained USER SourceRefs, generation, same session, exact source excerpts, persisted USER message auto-increment sequence strictly prior to current, and conservative unique capitalized Project name equality. Cross-session B4 intentionally excluded from this candidate pending separate proof; non-project contexts conservatively abstain. No native calls, fact promotion, output or learning authority. New seven-test suite includes explicit legacy counterexamples and valid earlier→later source preservation.

## Original REDs preserved without waivers

- Actions `41161615927` at `464da10db651db45e0029cf14750c2af1aa0117c`: **87 tests, 2 failures** on unrelated Harbor→Willow project import; all other stages zero. Original artifact `13027526445`, ZIP SHA256 `38511226345e88f628dde7ac3adc8a263825bdc481f860a90999e66380db32e3`, CRC PASS and 18/18 hashes. Private backup `Original_RED_41161615927_SHA_38511226.zip` read back byte-identical.
- Actions `41161740316` at `940437ebe86d49c656f966390add153cb858d3bd`: **88 tests, 3 failures** from candidate-only incorrectly doubled raw-regex backslashes (project scope falsely empty). Original artifact `13027122174`, ZIP SHA256 `183e18fe477571a9bee548f883b1703ad4a554d98e0fdccaca8d68e26db65f96`, CRC PASS 18/18 hashes. Private backup `Second_RED_41161740316_SHA_183e18fe.zip` read back byte-identical. Corrected the literal escape in the candidate; frozen sources unchanged.

## Verified GREEN and backup

GitHub Actions `41161775878` at executed head `e9a77c09594bf68aaa0a42802636d6f41a37d3f5`, terminal SUCCESS: **88/88** focused software tests in 3.885s, all 8/8 stage exits zero, privacy CLEAN, source pins exact. Original artifact `13027675496`, ZIP SHA256 `7b65776700510ac72873a79622b9a65d99039bb191d771b7d81bc4f9be00d379`, CRC PASS and 18/18 inner hashes. Private Library backup `/V13-Checkpoints/2026-10-31/B1B2-Causal-Context-Audit/Preflight_GREEN_41161775878_SHA_7b657767.zip` independently materialized and byte-compared identical; both RED backups retained in same folder. Exact focused command: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_b1b2_causal_context_candidate tests.test_f1f5_c5c6_atomic_draft_candidate tests.test_f1f5_event_finalizer_candidate tests.test_run52_lexical_metric_audit tests.test_run52_b1b2_cross_turn tests.test_run51_f1f5_second_attempt tests.test_run50_native_c3_c5_c6_draft tests.test_run49_c5_c6_draft_shadow tests.test_run48_jef_c3_final_agreement_shadow tests.test_run46b_jef_source_eligibility_shadow`.

## Next and limitations

A future consumer proof must show `Cognition.offer` actually receives filtered context and that old-event replay cannot mutate current retained state; this adapter alone is not wired. Do not change frozen Run52 native protocol or rescore seed479. Separate B4 cross-session provenance and general non-project topic matching remain required. No native model/Redmi, full suite, live C5/C6, Age/STEP2/B3/JEPA or whole-system completion claim. Original Run44 RED and all negative gates unchanged. No production merge or auto-merge; platform remaining budget UNKNOWN.
