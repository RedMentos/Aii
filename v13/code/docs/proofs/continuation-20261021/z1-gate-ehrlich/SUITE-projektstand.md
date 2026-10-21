# V13 Messsuite 2026-10-21T06:35:15Z

| § | Benchmark | Status | Braucht | Hinweis |
|---|---|---|---|---|
| 24.1 | Second-Attempt Advantage | MEASURED | models | paraphrase transfer measured; restart/negative-transfer families via integration_second_attempt (models) |
| 24.2 | Immediate Memory | TESTED | none |  |
| 24.3 | Automaticity | TESTED | none | skill fast path and effort; quality-at-fewer-steps not measured |
| 24.4 | Re-open / De-automatization | TESTED | none | skill reopen + age demotion; live salience reopen not measured |
| 24.5 | Retention | TESTED | none |  |
| 24.6 | Output Guarantee | TESTED | none |  |
| 24.7 | Provenance | TESTED | none |  |
| 24.8 | Local Plasticity | TESTED | none |  |
| 24.9 | Body Swap | TESTED | none | slot lifecycle; parity on real bodies not measured |
| 24.10 | Action Safety | TESTED | none | tool gate + C5 suppression; real external actions blocked until WP-K |
| 24.11 | Callosum Utility ohne Homogenisierung | MEASURED_FAILING | models |  |
| 24.12 | Response Governor | TESTED | none |  |
| 24.13 | Controlled Exploration | TESTED | none | curiosity budget only; route discovery under shadow not measured |
| 24.14 | Control-Fabric Overhead | NEEDS_REDMI | redmi |  |
| 24.15 | Channel Utility / Latent-vs-Fallback | MEASURED | models | latent channel not implemented (B3 OFF) |
| 24.16 | World Grounding / Counterfactual Reliability | TESTED | none |  |
| 24.17 | Deliberation Trajectory / Halting | TESTED | none |  |
| 24.18 | Fast Episodic Parametric Trace | MEASURED | models | WP-S3 keyed sparse memory: 8/8 learned, 0 probes forgotten, KL 3e-6 (torch master); near-miss leak open |
| 24.19 | Shared Pre-Router Forgetting | NOT_IMPLEMENTED | models | needs MoE body (WP-N11) |
| 24.20 | Multiscale Gist/Detail Resolution | MEASURED | models |  |
| 24.21 | Developmental Age Control | TESTED | none |  |
| 24.22 | C-native / Selective Body-Wake | TESTED | none |  |
| 24.23 | Adaptive Reasoning Effort | TESTED | models | quality vs fixed low/high baselines needs model run |
| 24.24 | Native Cache/Attention Capability Ablation | MEASURED | models |  |
| 24.25 | Observer-Pass Utility | TESTED | models |  |
| 24.26 | JEF-KV/Broadcast Bridge | TESTED | models | WP-N3 jefbridge: broadcast/KV bridge behaviour tested; real-model KV bridge measurement open |
| 24.27 | Focal Coalition / Unity Test | TESTED | none |  |
| 24.28 | Corollary-Copy / Self-vs-World | TESTED | none |  |
| 24.28B | Teacher Reference / Human Feedback Integrity | TESTED | none |  |
| 24.29 | Modality Scaffold Internalisation | TESTED | models | text A3 student only; no camera/audio (STEP8) |
| 24.30 | Live / Full-duplex Interaction | TESTED | none | WP-N14 text timeline: overlap decision, cut, provisional, handoff with source; audio/video STEP 11 |
| 24.31 | Cross-modal Learning | NOT_IMPLEMENTED | none | WP-N15 lab scaffold only (image source + raw eye + frozen VLM teacher REFERENCE_NOT_FACT + student alignment); core stays text until STEP8 |
| 24.32 | Fluid Experience Lifecycle | TESTED | none |  |
| 24.33 | Redmi Scheduling / Memory Residency | NEEDS_REDMI | redmi |  |
| 24.34 | Needle-class Additive Control Experiment | TESTED | models |  |

## §99 Ablationen

| Hypothese | Kontrollen vorhanden | fehlend |
|---|---|---|
| Fine/Gist split helps | identical policies, shared-body dual state, single body | – |
| Callosum helps | no-message, exact, symbolic | latent |
| Focal coalition helps | – | full context only, retrieval only, fixed slots |
| Episodic fast memory helps | response cache, no memory, param delta only | – |
| JEPA predictor helps | supervised readout, next-token-like probe, no predictor | – |
| Eligibility helps | gradient only, random mask, recency only | – |
| Typed modulators help | scalar reward, human-only, outcome-only | – |
| Dream helps | no dream, replay only, dream no writes | dream policy-only |
| Proceduralization helps | full deliberation, static shortcut | – |
| Age helps stability | fixed conservative, fixed permissive | – |
| Two bodies worth mobile cost | shared body + two states, one body | – |

## §29 V13 funktioniert (24 Eigenschaften, maschinell aus Gates und Benchmarks)

Erreicht 3, teilweise 15, fehlt 6. Ohne alle 24 ist V13 laut §29 ein Harness-Prototyp.

| # | Eigenschaft | Stand | Gates | Benchmarks | Einschätzung 21.10. |
|---|---|---|---|---|---|
| 1 | echte vortrainierte A + B + C | ✅ ERREICHT | RUNNER0 GREEN, STEP1 GREEN | – | ✅ |
| 2 | B1 fein + B2 adaptiv grob mit Cross-scale SourceLinks | ❌ FEHLT | G-B-TIMESCALE-DIVERGENCE-001 EVIDENCE_NOT_PASSING | 24.20 MEASURED | 🟡 |
| 3 | BodyPort-Profile + trainierter Callosum-Bootstrap | 🟡 TEILWEISE | STEP6 PARTIAL | – | 🟡 |
| 4 | adaptive Kanal-Policy mit nachgewiesenem Latent-vs-Fallback-Nutzen + Empfänger-Kalibrierung | ❌ FEHLT | G-CALLOSUM-UTILITY-002 EVIDENCE_NOT_PASSING | 24.15 MEASURED, 24.11 MEASURED_FAILING | ❌ |
| 5 | echter Message-Subspace-Austausch ohne Private-State-Kollaps | ❌ FEHLT | G-CALLOSUM-UTILITY-002 EVIDENCE_NOT_PASSING | 24.11 MEASURED_FAILING | ❌ |
| 6 | kleiner echter JEF-Sprach-/Executive-Body mit privatem Native-KV | 🟡 TEILWEISE | STEP1 GREEN | 24.26 TESTED | 🟡 |
| 7 | versionierter JEF_BROADCAST_CACHE + trainierte JEF↔A/B-Brücken | 🟡 TEILWEISE | – | 24.26 TESTED | 🟡 |
| 8 | A/B-Observer-Pass → OFFER_PACKETs | ❌ FEHLT | STEP2_HARNESS GREEN, STEP2_EXIT EVIDENCE_NOT_PASSING | 24.25 TESTED | 🟡 |
| 9 | FOCAL_COALITION_STATE | ❌ FEHLT | G-FOCAL-CAPACITY-003 EVIDENCE_NOT_PASSING | 24.27 TESTED | 🟡 |
| 10 | selektiver none/A/B/A+B-Wake mit gemessener Eskalations-Qualität | 🟡 TEILWEISE | – | 24.22 TESTED | 🟡 |
| 11 | automatischer Direct/Skill-Pfad | 🟡 TEILWEISE | G-PROCEDURALIZATION-004 PARTIAL | 24.3 TESTED | 🟡 |
| 12 | gezielte Deliberation mit Re-entry + Halting-vs-Trajectory-Test | 🟡 TEILWEISE | – | 24.17 TESTED | 🟡 |
| 13 | handlungsgeerdetes World-JEPA mit Coverage/Counterfactual-Konfidenz | 🟡 TEILWEISE | G-SELF-WORLD-005 PARTIAL | 24.16 TESTED | 🟡 |
| 14 | Context/Provenance ohne History-Korruption | 🟡 TEILWEISE | – | 24.7 TESTED | ✅ |
| 15 | Fast-Episodic-Vorteil beim zweiten Versuch | ✅ ERREICHT | STEP3 GREEN | 24.1 MEASURED | ✅ |
| 16 | lokale Eligibility + echtes JEPA/EMA-Update + Pre-Router-Regressions-Monitor | ❌ FEHLT | – | 24.8 TESTED, 24.19 NOT_IMPLEMENTED | 🟡 |
| 17 | Replay + Restart-Persistenz | 🟡 TEILWEISE | STORE0 GREEN, STEP3 GREEN | 24.5 TESTED | ✅ |
| 18 | Regression-Schutz | 🟡 TEILWEISE | STEP5 CRITERIA_UNMEASURED | – | ✅ |
| 19 | messbarer Übergang Scaffold→Imitation→Exploration→Shadow→gelernte Route je Fähigkeit | 🟡 TEILWEISE | – | 24.32 TESTED, 24.13 TESTED | 🟡 |
| 20 | echte Age-Rechtehülle + bindender user_stage_cap + Reife je Fähigkeit | 🟡 TEILWEISE | G-AGE-REOPEN-001 PARTIAL | 24.21 TESTED | ✅ |
| 21 | adaptive Reasoning-Effort-Policy mit User-Override und Fixed-Effort-Baselines | 🟡 TEILWEISE | – | 24.23 TESTED | 🟡 |
| 22 | native Cache/Sparse-Attention nur nach Ablation | ✅ ERREICHT | – | 24.24 MEASURED | 🟡 |
| 23 | Event/Wake-Scheduler + unabhängiger Response Governor | 🟡 TEILWEISE | – | 24.12 TESTED, 24.33 NEEDS_REDMI | ✅ |
| 24 | endliche Output-Garantie | 🟡 TEILWEISE | – | 24.6 TESTED | ✅ |

## Blueprint-Ausgangskriterien je Gate (§96 STEP2, §100)

| Gate | Status | Kriterium | Messung | Hinweis |
|---|---|---|---|---|
| STEP2_EXIT | EVIDENCE_NOT_PASSING | measurable_complementarity | FAIL (canonical_gate_pass=False) | 09.10.: UTILITY_FAIL, both_exact 0.525 vs b1_only 0.592 |
| STEP2_EXIT | EVIDENCE_NOT_PASSING | each_body_contributes | FAIL (paired.b1_b2_each_win_an_episode=False) |  |
| STEP2_EXIT | EVIDENCE_NOT_PASSING | bounded_rss | UNMEASURED | no preregistered STEP2 RSS budget yet; measured cloud peak 1.50 GB (two_body.analysis), Redmi not measured |
| STEP2_EXIT | EVIDENCE_NOT_PASSING | observer_latency_known | PASS | per-offer native duration on Linux cloud (09.10. cohort); Redmi not measured |
| STEP5 | CRITERIA_UNMEASURED | shadow_generation_atomic_commit | PASS |  |
| STEP5 | CRITERIA_UNMEASURED | train_runner_proof_on_device | UNMEASURED | cloud only; Redmi proof missing (WP-Z7) |
| STEP5 | CRITERIA_UNMEASURED | modulator_packet_real | UNMEASURED | unit tests only; typed-vs-scalar measured only synthetically (ablation99) |
| STEP5 | CRITERIA_UNMEASURED | eligibility_traces_real | UNMEASURED | synthetic ablation99 ties recency-only |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | complementary_error_profiles | FAIL (complementarity_proven=False) |  |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | beats_identical_instances | FAIL (complementarity_proven=False) | same-model same-policy control |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | control_same_model_same_policy | PASS |  |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | control_prompt_only | PASS |  |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | control_shared_body_dual_state | PASS |  |
| G-B-TIMESCALE-DIVERGENCE-001 | EVIDENCE_NOT_PASSING | fixtures_b1_own_information | UNMEASURED | WP-Z2 |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_l1_pass | FAIL (summary.canon_l1_pass=[]) | v3 12.10.: L1 FAIL on all tasks; attempt 4 = WP-Z4 |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_task_utility | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_latency | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_bytes_transferred | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_receiver_OOD | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_source_faithfulness | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_role_retention | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_interference | UNMEASURED | locked until L1 PASS |
| G-CALLOSUM-UTILITY-002 | EVIDENCE_NOT_PASSING | latent_beats_fallbacks_restart_reproducibility | UNMEASURED | locked until L1 PASS |
| G-FOCAL-CAPACITY-003 | EVIDENCE_NOT_PASSING | functional_properties_real_path | UNMEASURED | only synthetic unit tests (tests/test_focal.py) |
| G-FOCAL-CAPACITY-003 | EVIDENCE_NOT_PASSING | beats_full_context | FAIL (verdict.focal_coalition_helps=False) |  |
| G-FOCAL-CAPACITY-003 | EVIDENCE_NOT_PASSING | control_retrieval_only | UNMEASURED | WP-Z5 |
| G-FOCAL-CAPACITY-003 | EVIDENCE_NOT_PASSING | control_fixed_slots | UNMEASURED | WP-Z5 |
| G-PROCEDURALIZATION-004 | PARTIAL | latency_down | UNMEASURED | synthetic only (ablation99, no language model); real latency/energy needs Redmi (WP-Z7) |
| G-PROCEDURALIZATION-004 | PARTIAL | energy_down | UNMEASURED | synthetic only (ablation99, no language model); real latency/energy needs Redmi (WP-Z7) |
| G-PROCEDURALIZATION-004 | PARTIAL | accuracy_noninferior | UNMEASURED | synthetic only (ablation99, no language model); real latency/energy needs Redmi (WP-Z7) |
| G-PROCEDURALIZATION-004 | PARTIAL | reopen_on_error | UNMEASURED | synthetic only (ablation99, no language model); real latency/energy needs Redmi (WP-Z7) |
| G-PROCEDURALIZATION-004 | PARTIAL | constraints_preserved | UNMEASURED | synthetic only (ablation99, no language model); real latency/energy needs Redmi (WP-Z7) |
| G-SELF-WORLD-005 | PARTIAL | external_no_self_action | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-SELF-WORLD-005 | PARTIAL | observation_after_self_action | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-SELF-WORLD-005 | PARTIAL | partial_action_failure | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-SELF-WORLD-005 | PARTIAL | delayed_outcome | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-SELF-WORLD-005 | PARTIAL | unexpected_side_effect | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-SELF-WORLD-005 | PARTIAL | ambiguous_causality | UNMEASURED | synthetic test cases only; no real action sequence (WP-Z12) |
| G-TRAIN-RUNNER-PROOF-001 | PARTIAL | no_commit_without_exact_proof | UNMEASURED | cloud proof only, Redmi proof missing (WP-Z7) |
| G-REPLAY-CONSOLIDATION-001 | EVIDENCE_NOT_PASSING | consolidation_pass | FAIL (status=CONSOLIDATION_PARTIAL) |  |
| G-REPLAY-CONSOLIDATION-001 | EVIDENCE_NOT_PASSING | control_dream_policy_only | UNMEASURED | WP-Z9 |
| G-MODULATOR-SPECIFICITY-001 | PARTIAL | beats_scalar_reward | UNMEASURED | synthetic only (ablation99: 5/5, 5/5, 4/5) |
| G-MODULATOR-SPECIFICITY-001 | PARTIAL | beats_human_only | UNMEASURED | synthetic only (ablation99: 5/5, 5/5, 4/5) |
| G-MODULATOR-SPECIFICITY-001 | PARTIAL | beats_outcome_only | UNMEASURED | synthetic only (ablation99: 5/5, 5/5, 4/5) |
| G-AGE-REOPEN-001 | PARTIAL | age_beats_fixed_conservative | UNMEASURED | synthetic ablation99: NOT supported in the noisy phase; user decision on plasticity open (WP-Z8) |
| G-AGE-REOPEN-001 | PARTIAL | age_beats_fixed_permissive | UNMEASURED | synthetic ablation99: NOT supported in the noisy phase; user decision on plasticity open (WP-Z8) |
| G-MOBILE-LONGRUN-001 | PARTIAL | weeks_on_redmi | UNMEASURED | cloud soak only; Redmi missing (WP-Z7) |
| G-MOBILE-LONGRUN-001 | PARTIAL | retention | UNMEASURED | cloud soak only; Redmi missing (WP-Z7) |
| G-MOBILE-LONGRUN-001 | PARTIAL | thermal | UNMEASURED | cloud soak only; Redmi missing (WP-Z7) |
| G-MOBILE-LONGRUN-001 | PARTIAL | restarts | UNMEASURED | cloud soak only; Redmi missing (WP-Z7) |

Gates: {'GREEN': 7, 'EVIDENCE_NOT_PASSING': 5, 'CRITERIA_UNMEASURED': 1, 'PARTIAL': 7}
Register: 299 Blueprint-Regler, 96 im Code gleich, 0 abweichend, 197 nur deklariert (Abdeckung 34%).
