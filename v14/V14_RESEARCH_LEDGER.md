# V14 / Inquisition-JEPA — laufendes Forschungsjournal

**Stand:** 2026-11-20. **Arbeitsart:** ergebnisorientiertes laufendes Research, nicht bloß Literaturanhang.  
**Aktive Architektur:** [V14 Master](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md) §§21–23; [Arbeitsplan](V14_LIVE_WORKPLAN.md).  
**Vorsicht:** Ein Paper-Abstract ist kein reproduzierter Experimentalbefund; eine nachgeprüfte URL ist keine vollständig gelesene Arbeit. Jeder Eintrag erhält eine *genaue* Evidenzstufe.

## Benutzung

Bei jedem Forschungsdurchlauf diese Datei zuerst lesen, Kandidaten identifizieren, nach Primärquelle/Duplikaten prüfen, die wesentlichen Tabellen/Limitations/Implementation lesen, Status und nächstes Testexperiment aktualisieren. Danach die relevante V14-Architektur- oder Codeänderung vorschlagen/ausführen und Nachweise zurückverlinken. Stimmige neue Erkenntnisse dürfen den V14-Plan **verbessern/adaptieren**; ein dokumentiertes Ziel des vollständigen V13 wird dabei nie kommentarlos gestrichen. Die Pipeline umfasst auch neue Modelle und Releases, mechanistisch verwandte Arbeiten und negative Studien – nicht nur Paper-Titel.

**Statusbegriffe:** DISCOVERED = Fund; ABSTRACT_VERIFIED = Primär-Abstract geprüft; FULLTEXT_REVIEWED = Methode/Experimente/Grenzen gelesen; REPRO_ATTEMPTED = Versuch protokolliert; NATIVE_TESTED = echte Geräteprüfung; CANDIDATE_PROPOSED = konkreter Integrationsvorschlag; ADOPTED = nach Review in aktiven Design-/Codepfad übernommen; REJECTED = mit Grund dokumentiert. Mehrere Flags nur nach Evidenz. Nur tatsächlich erfolgte Lektüre als „bereits gelesen“ ausgeben.

| ID | Primärquelle / Datierung | Tatsächlicher Kenntnisstand 2026-11-20 | Konkrete V14-Idee / Hypothese | Nächster harter Test |
| --- | --- | --- | --- | --- |
| R-001 | **H-JEPA: End-to-End Learning of Hierarchical World Models for Visual Planning**, arXiv:2610.06805, Erstfassung 2026-10-05, Revision 2026-11-01; https://arxiv.org/abs/2610.06805 | ABSTRACT_VERIFIED / FULLTEXT_PENDING. Hierarchie latenter Weltmodelle mit verschiedenen Zeitskalen; Studie aus visuellem Planning, kein unmittelbarer Beleg für zwei Android-LLMs. | Prüfen, ob B1_DETAIL/B2_GIST und World mehrere selbstlernende latente Zeit-Horizonte nutzen; nicht pauschal einen einzelnen gemeinsamen Tensorraum erzwingen. | Kleine synthetische + echte Sequenzdaten; mehrere Zeitskalen vs flach, gleiches Trainingsbudget, echte Tensor-/Grad-/EMA-Belege, Retention |
| R-002 | **Speculative Self-Distillation enables Efficient Knowledge Internalization**, arXiv:2611.12016, 2026-11-09; https://arxiv.org/abs/2611.12016 | ABSTRACT_VERIFIED / FULLTEXT_PENDING; externe GPU-Referenz nicht mit Termux-Kompatibilität verwechseln. | Kleine adaptiv selektierte Teacher/Peer-Interventionen nur dort, wo eigener Student/Lernpfad zusätzliche Evidenz benötigt. Teacherrolle ist austauschbar/temporär, kein statisches Bewusstseinsorgan. | JEPA allein vs Self-Distillation allein vs kombiniert; Holdout/Forgetting/Costs, Rechte und Modelllizenz |
| R-003 | **RASP: Read-All, Sparse-Plasticity Continual Learning in a Stationary-Size LoRA**, arXiv:2611.03513, 2026-11-02; https://arxiv.org/abs/2611.03513 | ABSTRACT_VERIFIED / FULLTEXT_PENDING; kein ARM- oder Redmi-Proof. | Gewisse Kanäle in Forward-Pass lesen, beim Gewichtsupdate selektiv schützen; möglicher Schutz vor Catastrophic Forgetting für Body-/Head-LoRAs. | Gleiche Retention-/Plastizitätskohorten gegen reguläre LoRA, zufälliges Gating und No-Update; Adapterbudget, ARM-Trainerprofil |
| R-004 | **Stability Does Not Mirror Plasticity: A Module-Level View of Declarative and Procedural Learning in Transformers**, arXiv:2611.23427, eingereicht 2026-11-17; https://arxiv.org/abs/2611.23427 | ABSTRACT_VERIFIED / FULLTEXT_PENDING; Vergleich declarative/procedural und Module, nicht automatisch generelle gesetzmäßige Optimierungsstrategie. | Nicht alle B-/C-/World-/Self-Organe und Layer mit gleicher Lernrate/Reset-Policy behandeln; modul-/aufgabenspezifischen Plastizitäts-/Retention-Head prüfen. | Layer-/Task-spezifische Learning-Rate/Gate-Ablation vs global gleiche Update-Policy; Langzeit-Retention |
| R-005 | **Self-Distillation Enables Continual Learning**, arXiv:2601.19897 / ICML 2026, https://proceedings.mlr.press/v306/shenfeld26a.html | IM V14-VORPLAN REFERENZIERT / erneute Primärdetailprüfung ausstehend; keine eigene neue Reproduktion | Konditionierte on-policy Rückmeldung als eine Lernquelle unter mehreren, ohne dauerhafte feste Teacher-Instanz. | Entsprechende Baselines und positive/negative Fälle mit B1/B2-C3-Head statt bloßer Konzeptparallele |
| R-006 | **Thylation** (vom Nutzer als *beispielhafter* neuer Papername genannt; exakter Titel unbekannt) | UNRESOLVED_NAME / NO CLAIM OF READ; keinesfalls einen passenden Titel erfinden | Beispiel für gewünschte Recall-Funktion: Aliasse/Titel auflösen, bereits datierte Forschung samt V14-Ideen zeigen. | Bei tatsächlichem Link oder eindeutigem Titel recherchieren, hier verknüpfen; keine voreilige Architekturänderung |

## Offene Forschungsketten (für die nächsten Recherche-Läufe)

- **Latente Interoperabilität:** trainierte Cross-Model-Projection, Encoder/Decoder-/Receiver-Injektion, dynamische Kopplung, recurrent routing, shared vs multiple aligned latent spaces. Suche nach echten implementierten Activation-to-Activation-Transfers; Prüfkriterium: Receiver-Utility *über* JSON-SOURCE_EXACT- oder NO_MESSAGE-Baseline.
- **Aktive Fehlergetriebene Lernsteuerung:** Nächste Beobachtung wählen, self-generated experiments, Event-/Hazard-/Omission-Modelle, Error×Eligibility×Modulation und echte numerische Fortschritte; in aktivem `World/Self` statt isoliertem SQLite-Hypothesenspeicher.
- **Kognitiv verteilte Lernorganisation:** Attention/Gain, lokale und globale Plastizität, Memory-Konsolidierung, adaptive Routing-/MoE-Spezialisierung, aktive Reinterpretation beim selben Turn und gegenseitige Hemmung/Verstärkung ohne zentrale Einzelinstanz.
- **Mobile realistisch:** llama.cpp/Cactus/kleine Optimierer auf Android 13 aarch64 6-GB-Klasse; Modellkarten, Gewichte, Modelllizenz, Kernel, PSS/RSS, TTFT, thermische Drosselung, Up-/Downgrades, echte Persistent Training.
- **Selbstoptimierung:** isolierter Patch-/Weight-Sandbox, Regression-/Unlearning-/Safety-Gates, menschlich überprüfbare Tests, später trainierte Update-Folgenprädiktion und Generationenwechsel.
- **Forschungs-Fortschritt des Projekts:** welche WPs im Canon mit *echtem Consumer* statt `CODE_PRESENT` enden; negative Kontrollpfade, STEP2/B3 bestehende FAILs, Agenten-Duplikate und opportunistische OSS-Übernahmen.

## Pro neuem Paper auszufüllen

```yaml
id: R-NNN
paper_title:
aliases: []
doi_arxiv_url:
paper_published_at:
checked_at:
reviewer:
evidence_level: DISCOVERED | ABSTRACT_VERIFIED | FULLTEXT_REVIEWED | REPRO_ATTEMPTED | NATIVE_TESTED
original_claim:
what_is_not_shown:
methods_and_controls:
critical_counterevidence:
v13_canon_links: []
v14_organ_links: []
implementation_hypothesis:
alternatives: []
required_source_code_and_licenses:
model_weights_and_dataset_rights:
ram_speed_android_constraints:
minimal_falsifiable_experiment:
expected_metrics:
real_results: NOT_RUN
decision: OPEN
followup_owner:
git_pr_commit:
```

**Archiv- und Datenschutzregel:** Im öffentlichen GitHub nur öffentliche Paper-/Code-Informationen und synthetische anonymisierte Messungen. Keine privaten Chats, Transkripte, Gerätekennungen, Tokens oder persönlichen Rohdaten in das Journal. Der alte V14-Research-Text bleibt als historischer Kontext erhalten, neue Erkenntnisse erscheinen zusätzlich hier und im aktiv revidierten Master, wenn sie das Design ändern.


## Research and implementation update — 2026-11-20

### R-007 — Architecture-Dependent Causal Transfer of Activation States Across LLMs

- **Source:** arXiv:2608.16347, version 2, 2026-08-17. https://arxiv.org/abs/2608.16347
- **Evidence:** ABSTRACT_VERIFIED; no independent reproduction in V14.
- **Reported result:** learned projections retrieve related activations across several decoder-only model pairs, but causal activation injection improves downstream behavior significantly for only one of the three evaluated pairs.
- **What is not shown:** general semantic interchangeability, universal cross-family transfer, mobile feasibility, or a trained B1/B2 receiver in V14.
- **V14 consequence:** do not infer latent compatibility from cosine similarity or retrieval alone. Require pair-specific receiver injection, causal ablation, task utility over exact-message and no-message baselines, negative controls, and rollback. This supports the existing V14-003 acceptance gate; it does not justify turning B3 on.

### R-008 — SLoRA: Continual Learning with Sparse LoRA Updates

- **Source:** ACL Anthology 2026, https://aclanthology.org/2026.acl-long.247/
- **Evidence:** ABSTRACT_VERIFIED; reported benchmark improvements are paper claims, not V14 results.
- **Reported result:** sparse LoRA update/pruning is reported to reduce forgetting and remove low-utility adapter parameters in the evaluated tasks.
- **What is not shown:** Redmi/ARM performance, compatibility with the current LFM2.5 quantized GGUF files, or safe continuous updates in V14.
- **License:** the referenced GitHub repository has no root LICENSE file or repository license metadata in the checked view; do not copy its implementation until a valid license is established.
- **V14 consequence:** keep as a candidate for adapter-budget/retention experiments only. Compare against ordinary LoRA, random pruning, and no-update controls; require held-out utility and rollback.

### R-009 — MobileFineTuner / on-device Android fine-tuning

- **Source paper:** arXiv:2512.08211, https://arxiv.org/abs/2512.08211
- **Implementation:** https://github.com/Edge-Intelligence-Lab/MobileFineTuner at `be95a289d9cd5ecd93b6fab7fdc3c4551c3f9fb1`
- **License:** Apache-2.0, verified from repository LICENSE.
- **Implementation facts:** Android SDK library; minSdk 29, compileSdk 35, NDK 26.1.10909125, JDK 17, arm64-v8a; C++17 native core; exposes LoRA/full-fine-tuning entry points and a small synthetic Android smoke path.
- **What is not shown:** bundled model weights or dataset rights, a complete continual-learning/replay/retention controller, Redmi Note 10 Pro measurement, or direct support for the current LFM2.5 Q4 GGUF deployment.
- **V14 consequence:** possible separate native Android training backend, not a drop-in Termux or GGUF optimizer. Before adoption, prove model architecture/export compatibility, external weight licenses, memory/RSS, training latency, checkpoint/restart and rollback on the actual device. No dependency or model was added.

### Implementation finding — temporal outcome semantics

The earlier V14 temporal ledger treated every observed event as positive and did not compare the observed outcome label to the expected label; late observations were also scored positively. Draft PR #2130 corrects this: only a matching in-window outcome receives (1-p); mismatch, early, late and verified omission receive (-p); censored/cancelled events produce no update. Local isolated tests are 18/18 PASS, but the bridge still lacks an authenticated Store/World producer and runtime consumer. This is not yet live JEPA or model-weight learning.


## Implementation evidence update — 2026-11-21

PR #2137 is merged as `3db6d1f00fceab9e7755bc8f4c25882ef7f19258`. It converts the earlier temporal-outcome proposal into a source-bound V13 Store path:
- verifies persisted event/generation, source digest/span, CorollaryCopy and exactly one matching ActionOutcome;
- scans the full per-event ActionOutcome history up to 4096 and fails closed above the bound, so older duplicates cannot be hidden;
- distinguishes observed negative outcomes from CANCELLED/ABORTED and OUTCOME_UNKNOWN/INTERRUPTED; cancelled/censored cases produce no prediction error or receiver update;
- persists the scalar temporal readout with rollback and parent-directory fsync.
Exact PR-head V14 real-Store tests and V13 staged/integrated tests pass. The exact merge-commit push integrated regression is still pending at this checkpoint. This is a scalar temporal receiver only: no normal Runtime consumer, no full JEPA, no cross-organ latent coupling and no native B1/B2 body-weight update. The next falsifiable experiment is a real postcommit Runtime consumer with source-bound predictions, held-out utility, no-predictor/replay-only controls, restart, retention and rollback.


## Research and implementation update — 2026-11-21

### R-010 — JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts

- **Primary source:** arXiv:2610.00722, submitted 2026-09-30; https://arxiv.org/abs/2610.00722
- **Evidence:** ABSTRACT_VERIFIED; abstract, introduction, model overview and stated ablations inspected. No independent V14 reproduction.
- **Reported method/result:** action-conditioned latent dynamics predictor is updated persistently from executed action / next-observation pairs; the visual encoder and reward head are held fixed during test-time adaptation. Dense replay creates prediction windows at every temporal offset. The paper reports improvements on eight shifts across four continuous-control environments and an 83% average reduction in autoregressive latent prediction error after 500 episodes.
- **What is not shown:** Android/ARM operation, LLM body coupling, V13 T8 provenance, V14 memory/permission design, or a local Redmi result. No implementation repository was linked in the inspected primary paper.
- **V14 hypothesis:** retain both joint encoder+EMA plasticity and a separately gated predictor-only adaptation mode. Compare them under the same disjoint holdouts, replay budget and rollback tests; do not turn a temporary predictor-only mode into a permanent frozen-teacher architecture.
- **Minimal experiment:** same T8 cohort and seed; joint encoder+EMA vs predictor-only vs no-update; replay on/off; record predictor/encoder/EMA parameter diffs, held-out latent loss, old-cohort retention, CPU/RSS and checkpoint/restart.
- **Reuse/license:** no code or weight license adopted because no implementation link was present in the inspected paper. No external dependency added.

### R-011 — ER-JEPA: Experience Replay Improves Joint-Embedding Predictive Learning in Language Models

- **Primary source:** arXiv:2609.36952, submitted 2026-09-29; https://arxiv.org/abs/2609.36952
- **Evidence:** ABSTRACT_VERIFIED; abstract and replay-method sections inspected. Full experimental appendix and independent reproduction remain pending.
- **Reported method/result:** adds an episodic replay path to LLM-JEPA and compares content-based, uniform and hard replay. The paper reports better predictive/alignment results than its LLM-JEPA baseline on the evaluated tasks.
- **What is not shown:** V13/Android integration, source-bound action outcomes, privacy-safe numeric replay, or native B1/B2 activation injection. The replay path is a training mechanism, not proof of an autonomous persistent agent.
- **V14 hypothesis:** the current bounded full replay of verified numeric T8 rows is a baseline only. Later compare uniform, content-similarity and prediction-error/hard replay under fixed memory/compute budgets, with disjoint holdout and old-cohort retention.
- **Minimal experiment:** replay off vs uniform vs content vs hard; matched update steps and replay bytes; report holdout gain, retention delta, replay utility per byte and negative-control behavior.
- **Reuse/license:** no code link or implementation license was identified in the inspected primary paper; no external code or weights imported.

### R-012 — V-JEPA 2 / V-JEPA 2.1 as an action-conditioned world-model reference

- **Primary source:** Meta AI research publication, 2025-06-11; https://ai.meta.com/research/publications/v-jepa-2-self-supervised-video-models-enable-understanding-prediction-and-planning/ ; paper https://arxiv.org/abs/2506.09985
- **Implementation source:** https://github.com/facebookresearch/vjepa2
- **Evidence:** ABSTRACT_VERIFIED; official abstract, repository README and license files inspected.
- **Reported method/result:** V-JEPA 2 pretrains from large-scale video and post-trains an action-conditioned latent predictor (V-JEPA 2-AC) on robot trajectories for planning. The official abstract reports robot manipulation in two labs using less than 62 hours of robot videos.
- **Resource mismatch:** published repository checkpoints range from 300M to 1B parameters for V-JEPA 2, with V-JEPA 2.1 variants from 80M to 2B. The repository setup is PyTorch/video-oriented; this is not a drop-in Termux/6-GB-class learner.
- **License:** repository README states the majority of source is MIT-licensed with selected Apache-2.0 files; both root LICENSE and APACHE-LICENSE are present. Model/weight and dataset terms must still be checked per checkpoint/source before any download.
- **V14 consequence:** use action-conditioned latent prediction as a design reference, not as evidence that the current small numeric T8 learner is equivalent. No V-JEPA code, weights or dependencies were downloaded or imported.

### Code connection — V14-004 candidate

- Candidate: jepa-memory/v14-world-jepa-store-consumer-20261121-r2; see WORLD_JEPA_STORE_CONSUMER_HANDOFF_20261121.md.
- The new Store consumer reuses V13 WorldJEPA encoder/predictor/EMA and source-verified T8 receipts. It adds a bounded numeric replay cohort, immutable checkpoint plus Store-state CAS pointer, rollback, disjoint holdout/negative controls and B1_DETAIL/B2_GIST numeric SHADOW readouts.
- The role readouts are not native body activations, the consumer is not yet runtime-wired, and no local exact-repository or Redmi test is claimed. Candidate CI must be read back on the exact final SHA before any PASS status.


## Implementation evidence update — 2026-11-21 (JEPA/Memory source-disjoint pagination; PR #2143)

Base `gpt6/v13-private-remote-bridge-20261111` HEAD at branch creation: `c3c32c05a0374e970d274f8a777a7ab85c067d66`; code commit `2311b039eb49375829876e1bea8f2ac2d6975fe8`; PR #2143. The earlier #2133 candidate split by action ID (source leakage), could learn censored/cancelled outcomes, and read only the latest N transitions (older backlog starvation). #2143 adds source-id grouping, observed-outcome-only T8 admission, oldest-first keyset pages and a persistent scan cursor that follows checkpoint restart/rollback. It adds a SELF_MODEL shadow readout and source-linked numeric episodic Memory recall while preserving WorldJEPA online encoder/predictor and EMA updates.

This is still **not a normal Runtime consumer** and not native B1/B2 GGUF learning. #2135's exactly-once OnlineWorld candidate remains blocked by its nested SourceHandoff builder chain. Python 3.13/3.14 CI for #2143 is pending; no local checkout test or Redmi receipt is available. Keep REDMI_UNVERIFIED and all live learning/model/permission gates closed.

## Release-branch readback — PR #2137 merge

Merge commit `3db6d1f00fceab9e7755bc8f4c25882ef7f19258` completed all 13 push workflows PASS, including V14 T8 temporal bridge, staged context/integrated regression and the private owner-read bootstrap test. These are GitHub/CI results, not a live Redmi receipt or a 20-turn phone acceptance claim.


## CI evidence update — 2026-11-21 (PR #2143)

The source-disjoint/paginated JEPA & Memory candidate passed GitHub Actions run `44848998581`: Python 3.13 `57 passed in 4.35s`, Python 3.14 `57 passed in 7.83s`; the compile step passed on both. The additional `v13-private-remote-bridge-tests` push run `44848994421` also passed. The V14 suite includes the real SQLite Store consumer tests and new source-grouping, censored-outcome, oldest-first backlog, restart/cursor, receiver and Memory recall regressions.

These results are CI/Linux only. No local Aii checkout test was run and no Redmi owner receipt exists; keep `REDMI_UNVERIFIED`. The candidate remains not Runtime-wired and does not update native B1/B2 GGUF weights.


## Review-state update — 2026-11-21 / PR #2143

PR #2143 was marked ready for independent review after the exact CI evidence was read back. Tested PR head `a2788aacdae09bb675fff220cbda4ba74d400912`: GitHub Actions run `44848998581` passed 57 tests on Python 3.13 (4.35s) and 57 tests on Python 3.14 (7.83s), with compile successful on both. Additional `v13-private-remote-bridge-tests` run `44848994421` passed. A subsequent docs-only commit records this evidence; no code changed after the tested head. Still no local Aii checkout or Redmi receipt; runtime wiring and native B1/B2 weights remain open.


## R-013 — JEPA-TTT: persistent action-conditioned test-time adaptation

- **Primary source:** Zhang et al., *JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts*, arXiv:2610.00722, submitted 2026-09-30: https://arxiv.org/abs/2610.00722
- **Evidence reviewed:** full arXiv HTML sections covering method, replay, evaluation and ablations. The paper updates an action-conditioned latent dynamics predictor from observed transitions, retains the adapted predictor across episodes, and uses dense replay windows at every temporal offset. In four continuous-control environments and eight dynamics shifts, it reports an 83% average reduction in autoregressive latent prediction error and a 153% planning-performance improvement over its frozen-JEPA comparison after 500 episodes. These are paper-reported results under its robotics setup, not V14/Android evidence.
- **V14 consequence:** keep predictor-only adaptation as an experimental ablation against the current joint encoder+EMA update, never as a permanent frozen-teacher architecture. Compare predictor-only, joint encoder+EMA and no-update under the same source-disjoint T8 holdouts, replay bytes, update budget, restart, rollback and old-cohort retention. A useful next experiment is dense temporal windows only where T8 provenance can prove the adjacent observations and action sequence; current discrete action receipts do not automatically provide those windows.
- **Code/license:** no official implementation link was identified from the paper page/search during this scan; no code or weights imported.

## R-014 — Replay on Demand: retention-aware replay allocation

- **Primary source:** Thede et al., *Replay on Demand: An Emergent Curriculum for Balancing Adaptation and Forgetting in Continued Pretraining*, arXiv:2609.40089, submitted 2026-09-30: https://arxiv.org/abs/2609.40089
- **Implementation:** https://github.com/bethgelab/replay-on-demand — repository README and license inspected; Apache-2.0. It adapts NeMo-RL v0.6.0 and its documented runs use large-model/HPC settings, so this is not an Android drop-in.
- **Method finding:** adaptation examples and replay examples compete in one top-k budget. Adaptation is scored by remaining learning potential relative to a specialist reference; replay is scored by degradation relative to the original model. Replay share and source mix emerge from measured need instead of a fixed ratio. The paper also warns that forgetting can only be detected for capabilities represented in the replay pool.
- **V14 consequence:** do not import the NeMo stack. Prototype a small numeric analogue after the current learner is runtime-wired: score each persisted source cohort by increase in its held-out prediction error against a retained anchor checkpoint, then compare uniform replay, error-prioritized replay and no-replay with equal update/byte budgets. Preserve a disjoint audit holdout; never use the holdout to choose batches. Measure whether replay improves old-source retention without sacrificing new-source utility. No code or dependency imported.

## R-015 — Action-conditioned JEPA is not automatically causal identification

- **Primary source:** Liu, Huang & Shi, *I Act Therefore I Am: When Is JEPA's Action-Conditioning Enough to Learn Causal Mechanisms?*, arXiv:2609.31161, submitted 2026-09-25: https://arxiv.org/abs/2609.31161
- **Evidence reviewed:** abstract and method/identifiability summary. The paper distinguishes accurate next-latent prediction from recovering component-wise causal state; its identifiability result requires sufficiently varied action-induced transition signatures and other explicit assumptions. Its A-JEPA instantiation adds action-modulated transition structure and an entropy-preserving objective.
- **V14 consequence:** retain the strict action-shuffled negative control and test more than aggregate latent prediction loss. Track per-action support, action-conditioned gain, transition diversity and held-out action combinations. Label the current numeric WorldJEPA as predictive, not causal. This is a research hypothesis; no A-JEPA code or weights imported.


## Implementation evidence — uniform replay versus no-replay (2026-11-21)

PR #2148 adds a code-level replay ablation to the persistent Store-backed WorldJEPA consumer. The default remains uniform replay; an explicit no-replay mode excludes prior train-fold rows from the gradient fit but retains the full source-disjoint experience cohort for later replay. The exact SQLite integration test proves the selected fit IDs are new-only in the ablation and old+new in uniform mode, checks the prior holdout retention delta, and restores the checkpoint. Exact GitHub Actions run 44853980297 passed 59 tests on Python 3.13 (12.19s) and Python 3.14 (10.30s), including compile. This is synthetic T8 data through the real SQLite Store and numeric WorldJEPA/EMA code; it is not real-user utility, Runtime wiring, native GGUF learning or Redmi proof. The next experiment is to compare retention and new-cohort utility under matched update/byte budgets, then consider a separately gated prediction-error/anchor-based hard replay policy. Do not claim the RoD method has been implemented.


## R-013 deeper ablation and limitation readback — 2026-11-21

The JEPA-TTT full-paper ablation/limitations sections were checked after the initial entry. Dense replay modestly improves over a dense chronological stream in the paper's aggregate planning metrics (best score 0.678 vs 0.671; mean AUC 0.571 vs 0.548). A matched persistence control that retains the predictor and optimizer across episodes reports a larger gain (best score 0.729 vs 0.289; mean AUC 0.637 vs 0.273). However, the paper explicitly does not measure retention, forward/backward transfer, catastrophic forgetting, or return to the original training dynamics; it studies one persistent dynamics shift. It also freezes the visual encoder and reward head throughout test-time adaptation. Therefore the paper supports persistent predictor/replay as a useful controlled baseline, but cannot justify permanent encoder freezing or establish V14's anti-forgetting requirements. V14 must retain joint encoder+EMA learning as an experimental path and compare it with predictor-only under old-cohort holdout, replay-off, rollback and return-to-prior-dynamics tests.


## R-016 — JEPA-TTT: persistent action-conditioned predictor adaptation (2026-11-21)

- **Primary source:** Zhang et al., *JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts*, arXiv:2610.00722, submitted 2026-09-30: https://arxiv.org/abs/2610.00722
- **Project/method source:** https://jepa-ttt.github.io/
- **Method checked:** the system updates the action-conditioned latent dynamics predictor from observed transitions during deployment. Predictor parameters, optimizer state and replay persist across episodes; the replay buffer forms prediction windows at every temporal offset. The visual encoder and offline-trained reward head remain fixed in the reported experiment; no online environment reward is used for the adaptation objective.
- **Reported evidence:** eight fixed dynamics shifts across four continuous-control environments, 500 test-time episodes per deployment. The paper reports an 83% average reduction in five-step autoregressive latent prediction error and a 153% relative improvement in mean best held-out planning score over frozen JEPA. Its matched persistence control reports mean best score 0.729 vs 0.289 and AUC 0.637 vs 0.273 when predictor/optimizer/buffer persist rather than reset.
- **Limitations relevant to V14:** the study tests one dynamics shift that remains fixed for 500 episodes. It does not test sequences of shifts, return to previous dynamics, catastrophic forgetting, or simultaneous visual/reward shifts. The fixed encoder/reward head are an experimental design choice, not a reason to freeze V14 bodies permanently.
- **V14 consequence:** keep predictor-only persistent adaptation as a comparison arm against joint encoder+EMA and no-update. Use source/digest-disjoint old/new holdouts, matched update and replay-byte budgets, prior-cohort retention, replay-off, rollback, and return-to-prior-dynamics tests. The current #2151 learner is a synthetic Store-backed numeric experiment; it does not reproduce the paper's robotics setup or establish Android utility.
- **Code/license:** no official implementation/weight repository and license were verified in this scan; no dependency or model was imported.

## R-017 — ER-JEPA: episodic replay for representation and token prediction (2026-11-21)

- **Primary source:** Pu, Fan & Lian, *ER-JEPA: Experience Replay Improves Joint-Embedding Predictive Learning in Language Models*, arXiv:2609.36952, submitted 2026-09-29: https://arxiv.org/abs/2609.36952
- **Method checked:** an episodic store retains source-target token pairs. Later updates recompute their current source/target representations and apply both next-token and JEPA alignment losses to historical examples alongside current-batch examples. Content, uniform and hard retrieval policies share the same replay path; the episodic path is removed at inference.
- **Reported evidence:** the main quantitative matched-compute result uses Llama-3.2-1B on NL-RX-SYNTH at 240.31 PFLOPs: content replay 83.65±1.48% vs LLM-JEPA 68.75±4.92% exact match over five seeds. Uniform replay reaches 85.04±0.54%, 3.80 percentage points above the current-batch replay-loss control, and exceeds that control in all five seeds. The paper plots gains across NL-RX-TURK, GSM8K, Spider and NQ-Open, but the detailed five-seed means/standard deviations are not reported for those four transfer datasets in the main results; do not treat the broad cross-task claim as equally quantified.
- **Limitations relevant to V14:** this is a large-model/HPC fine-tuning experiment, not an Android learner. It stores paired training tokens and applies a shared model's token/alignment losses; it does not prove cross-organ latent injection, online learning from arbitrary user conversations, or safe local retention. Its episodic memory must not bypass source consent, deletion, privacy or provenance.
- **V14 consequence:** use replay as a candidate mechanism for selected source-bound trainable heads/adapters after the real Runtime consumer is wired. Preserve digest-disjoint holdout and the new #2151 prior-cohort retention gate; compare uniform, content/error-prioritized and no-replay under equal update/byte budgets. Keep replay storage bounded, source-linked and revocable. Do not import the 1B training stack to Android.
- **Code/license:** no official code/weight repository and license were verified in this scan; no dependency or model was imported.

## Implementation evidence — RAW EAR acoustic cue adapter (2026-11-21)

- **Code source:** merged PR #2155, commit `c0cedbde718ede6107f4df1f1bf9c784df4e00cf`; module `v13/code/v13/audio_voice_cues.py`, test `v13/code/tests/test_audio_ear_voice_cues_v14.py`.
- **Method:** bounded 40 ms frames / 20 ms hops, block-average downsampling, autocorrelation F0 estimate (65–400 Hz), voiced fraction/confidence, pitch/energy ranges and conservative activity hints. The caller supplies at most one second of PCM16. Derived cues are source-bound and can be delivered to A4 attention and a short C3 admission summary; provisional input remains A4-only.
- **Evidence:** exact PR-head safe-additive workflow 44862523075 passed compile + 8/8 synthetic tests; generic staged/integrated workflow 44862523082 passed 240 staged and 415 integrated tests. This does not prove that the Core staged overlay or normal Runtime consumes the module.
- **Limits:** deterministic heuristic, not trained VAD, calibrated probability, ASR, speaker identification or speech understanding. No microphone/Android capture, TTS/vocoder, full-duplex, learning authority or action authority. No license/dependency was added; the code is first-party.
- **Next experiment:** compare against a simple energy/ZCR baseline and a maintained VAD/prosody implementation on the same consented, non-identifying fixtures; measure CPU time and memory on ARM before any runtime promotion. Do not persist raw PCM or infer speaker identity.



## R-018 — RAW EAR comparator candidates: WebRTC VAD and Silero VAD (2026-11-21)

### Why this matters
The merged #2155 adapter extracts heuristic pitch/voicing/energy/activity cues from PCM16. It is useful as a bounded feature source, but its current output is not a calibrated speech/non-speech probability and should not be treated as robust voice-activity detection. The next comparison should measure whether an established VAD improves A4 event boundaries without turning acoustic activity into transcript, speaker identity, emotion, learning authority or action authority.

### Candidate A — WebRTC VAD / libfvad
- **Primary implementation:** [dpirch/libfvad](https://github.com/dpirch/libfvad), a standalone extraction of the WebRTC Native Code VAD engine; the repository states that its implementation has no functional changes from the WebRTC VAD engine and provides a C API and `make check` test path.
- **License:** BSD-3-Clause is declared by the repository. It also carries a `PATENTS` file. Upstream WebRTC's Android VAD makefile labels the code BSD-style and explicitly points to an additional intellectual-property grant in `PATENTS`; this must be reviewed before reuse rather than treating the BSD label as the entire legal analysis.
- **Android relevance:** upstream WebRTC includes an Android.mk target for `libwebrtc_vad` and compiles the VAD C sources as a static library. This is evidence of Android build precedent, not proof that the standalone libfvad tree builds under the user's Termux/NDK toolchain or runs within the Redmi budget.
- **Trade-off:** no learned weight download and a small native C surface make it a strong low-cost baseline; it is a VAD baseline, not prosody or speech understanding.

### Candidate B — Silero VAD
- **Primary project:** [snakers4/silero-vad](https://github.com/snakers4/silero-vad), MIT-licensed. Its repository documents Torch and ONNX CPU paths, 8/16 kHz support, a roughly 2 MB JIT model, and reports sub-millisecond processing for a 30+ ms chunk on its stated single-thread benchmark. That performance claim is not an ARM/Redmi measurement. ONNX use requires the runtime and wrapper/I/O adaptation; the README explicitly leaves architecture support dependent on ONNX Runtime support.
- **Native-port lead:** [nipponjo/silero-vad-c](https://github.com/nipponjo/silero-vad-c) is a small third-party MIT-licensed C port with embedded weights, 16 kHz path and a NEON arm64 backend. Its documented prebuilt targets are Windows/macOS/Linux, not Android; the repository has a very small history/community footprint. Treat it as an experimental build candidate, not a trusted drop-in.
- **Trade-off:** a learned VAD can be a more demanding comparator than the deterministic WebRTC baseline, but it adds a weight/runtime path and needs its own license, ABI, hash and resource validation.

### V14 experiment and decision rule
1. Use identical non-identifying PCM fixtures for current #2155 cues, WebRTC VAD and Silero VAD: speech-like voiced frames, silence, stationary noise, impulsive noise, music-like harmonic input and mixed transitions.
2. Measure frame-level false positives/negatives, onset/offset delay, CPU time, peak RSS and sustained thermal behavior; include a no-audio baseline. Do not compare different frame sizes or thresholds without recording them.
3. Feed only source-bound VAD/activity features into A4 SHADOW. Preserve FINAL/PROVISIONAL and consent checks. Do not persist raw PCM or infer words, speaker identity or emotion.
4. Test Android ARM64/Termux build and runtime only after an isolated Linux build and license/patent review; no production dependency, model download or model swap is authorized by this research note.

### Current status
- Research only; no code imported, no dependency installed, no weights downloaded, no model/permission/device state changed.
- No local ARM benchmark and no Redmi evidence. #2155 remains a heuristic acoustic-cue adapter; #2158 remains a draft staged Runtime candidate with its separate arithmetic fixture failures.
- **Decision:** prefer libfvad as the first no-weight native baseline; keep Silero as a second, more demanding learned comparator. Neither is selected for production until same-fixture utility, ABI, license/patent and Redmi cost gates pass.


## R-019 — INTACT: Isomorphic Intent-to-Action Learning for Search-Free World Models (2026-11-21)

- **Primary paper:** arXiv:2607.26056v1, submitted 2026-07-28: https://arxiv.org/abs/2607.26056
- **Official implementation:** https://github.com/zju3dv/INTACT-JEPA at revision d6e40c039f4c20f1d6e115fa6158e7d098000378 (2026-10-10).
- **License:** repository root LICENSE declares MIT. This is code-source evidence only; external checkpoint/model-weight and dataset terms were not independently established. No code, dependency, model or weight was imported.
- **Method checked:** a shared state-conditioned intent-to-action operator is jointly shaped by physical-successor and goal-intent likelihoods. The paper evaluates direct zero-search action readout and optional plan-centred local CEM. It argues that preserving the local state-conditioned action-family relation is more useful than maximizing pointwise action R² alone; predicted–expert action-family kNN and CKA correlate with closed-loop success in its robotics audit.
- **Reported result (paper claim, not V14 evidence):** one-epoch goal-displacement INTACT reports 85.78%, 100.00%, 97.67% and 97.89% success on four official robotics tasks; optional guarded local CEM reports 96.86% macro success using 384 rather than 9,000 candidate sequences. The paper reports 89.39% shared four-task E5 Direct macro success and action-family kNN correlation r=0.954 across its audited checkpoints.
- **Implementation/resource mismatch:** README describes a ViT-Tiny/14 encoder, 192-dimensional latent, six-layer causal forward transformer and a three-layer width-1024 predictor (18.03M encoder + 3.11M predictor parameters). The implementation is PyTorch/CUDA and robot-vision/action-data oriented; no Android/Termux/ARM build or 6-GB-class runtime was verified. Three seeds are still a coarse scaling estimate, and robotics action families do not directly map to V14 body routing.
- **What is not shown:** no V13 T8 provenance, no B1/B2 native activation receiver, no LLM-body coupling, no Android/Redmi performance, no continual-learning retention across changing task distributions, and no model-weight license verification.
- **V14 consequence:** treat the action-family geometry result as an evaluation hypothesis, not as a drop-in model. After normal Runtime wiring, compare B1/B2 role-conditioned action-family retrieval / conditional action-law quality with the current uncalibrated numeric planner score. Include action-shuffled, SOURCE_EXACT and NO_MESSAGE controls; measure actual receiver utility rather than cosine similarity or pointwise regression alone. Keep the current WorldPlanner score diagnostic-only until calibration, holdout utility and rollback pass.
- **Next experiment:** on the same source/digest-disjoint T8 cohort, compare pointwise readout error with action-family kNN overlap and role-conditioned ranking stability; test whether these predict delayed user outcome better than the current score, under matched replay bytes and update steps. No model download, code reuse, dependency or device change is authorized by this research note.



## R-020 — Audio continual adaptation and low-latency VAD candidates (2026-11-21)

### PACE — Pretrained Audio Continual Learning
- **Primary source:** ICLR 2026 conference paper, Chang Li, Kanglei Zhou, Liyuan Wang, https://proceedings.iclr.cc/paper_files/paper/2026/hash/26cce1e512793f2072fd27c391e04652-Abstract-Conference.html ; arXiv:2602.03355 https://arxiv.org/abs/2602.03355.
- **Evidence:** official ICLR abstract and arXiv abstract checked; no V14 reproduction. The paper reports a six-benchmark audio continual-learning study and finds that directly applying common PEFT strategies can fail because of spectral/semantic misalignment, representation saturation and fine-grained representation drift. PACE combines first-session adaptation, a regularized analytic classifier, adaptive subspace-orthogonal PEFT and boundary-aware spectrogram perturbations.
- **V14 implication:** do not train RAW EAR audio adapters by copying a vision/LLM LoRA recipe. Keep the raw acoustic representation and prosody channels distinct from semantic/audio-task heads; measure subspace drift, source-disjoint old/new-session retention, boundary/onset stability and matched-budget controls before any audio-weight update. PACE results are benchmark claims, not Redmi evidence.
- **Code/weight rights:** no official implementation/weight artifact was verified in this scan; no code or weights imported.

### S4VAD — Low-Latency State Space Voice Activity Detection
- **Primary source:** Elad Cohen, Arnon Netzer, Hai Victor Habi, arXiv:2609.11110, submitted 2026-09-10: https://arxiv.org/abs/2609.11110.
- **Evidence:** abstract checked. The paper proposes a diagonal state-space streaming VAD and a probabilistic correction for noisy speech-onset annotations. It argues that AUROC alone misses temporal responsiveness and reports competitive AUROC with lower onset latency in its evaluated setup.
- **Limitations:** no maintained official implementation, reproducible repository, code license or Android/ARM benchmark was located in this scan. Do not adopt the paper's reported latency as an Android estimate.
- **V14 experiment:** retain as a research design for causal/stateful onset detection. Compare onset/offset latency under noisy timestamp annotations, FPR/FNR, memory and CPU on the same PCM fixtures as libfvad/Silero; do not replace RAW EAR nonverbal/prosodic features with a binary speech gate.

### Silero VAD v5 — pinned MIT comparator
- **Primary source:** https://github.com/snakers4/silero-vad at exact upstream revision `066409f3d9db45a30d21dfcbf9147826ffdd7052` (commit 2026-10-22); root LICENSE at that revision is MIT. The repository documents 8/16 kHz input, a roughly 2 MB JIT model and Torch/ONNX CPU routes; upstream performance claims are not Redmi measurements.
- **Resource caveat:** ONNX requires ONNX Runtime and NumPy; Torch requires a substantially heavier runtime. The small model file alone does not establish the full installed footprint or a working Termux/aarch64 ABI.
- **V14 role:** comparator for speech-activity probability only. Keep raw waveform-derived prosody, pauses, pitch, energy and nonverbal acoustic cues as separate A5 signals. A VAD must not become a transcript, emotion/speaker inference or learning/permission authority.
- **Decision:** research-only. First compare the current deterministic RAW EAR cue extractor with libfvad/WebRTC no-weight baseline and Silero on identical fixtures; then measure Android ABI, RSS/PSS, CPU, onset/offset and battery. No dependency, weight, model or device change is authorized by this note.



## Research update — 2026-11-21 08:4x CET (JEPA/Memory)

### R-010 deeper primary-source review — JEPA-TTT
- Primary paper: https://arxiv.org/abs/2610.00722; official project page: https://jepa-ttt.github.io/ (accessed 2026-11-21).
- The project page reports a matched persistence control with identical update counts: retaining predictor, optimizer and replay state across episodes raises mean best planning score from 0.289 to 0.729 and AUC from 0.273 to 0.637 versus resetting each episode. The main protocol also uses dense temporal windows and persistent replay.
- Limitation remains important: the experiments use one fixed dynamics shift in continuous-control environments. Returning to earlier dynamics, sequential shifts, visual/reward shifts and catastrophic forgetting are not established.
- V14 consequence: our Store consumer persists predictor/encoder/EMA checkpoints and replay rows, but the current `WorldJEPA.fit` creates a fresh Adam optimizer per update and reports `optimizer_moments_persisted=false`. A later package should persist optimizer moments atomically with the checkpoint/cursor, and compare reset-vs-persistent optimizer under identical T8 cohorts, update counts, replay bytes, old/new holdouts and rollback. This paper does not justify freezing the encoder permanently.

### R-011 deeper primary-source review — ER-JEPA
- Primary paper: https://arxiv.org/abs/2609.36952 (accessed 2026-11-21); official abstract confirms an episodic replay path over stored input/target pairs.
- The inspected method summary describes content-based, uniform and hard replay. The reported matched-compute controls indicate that historical replay contributes beyond simply adding token exposure or replaying only the current batch; this remains a paper result, not a V14 reproduction.
- Limitation: no V13/Android implementation, source-bound ActionOutcome provenance, native B1/B2 receiver proof or identified reusable implementation/weight license.
- V14 consequence: keep uniform replay as the measured baseline and no-replay as an ablation. A future content/error-prioritized replay experiment must match update steps and memory/byte budget and use source/content-disjoint new/old holdouts, retention, restart and negative controls. No external code, weights or dependencies imported.


## Research and implementation update — 2026-11-21 11:20 CET (Boss/Integration)

### R-021 — staged training-resume optimizer/replay ablation (NOT production Runtime)

- Exact candidate: RedMentos/Aii PR #2186, head db2d78840ffc6d2fde1fc79262a0541f23c01d91; staged/integrated workflow run 44893742409; V14 T8/Store run 44893742437.
- Environment: GitHub Actions Linux. The 249/10/47 staged-runtime suite calls test_world_jepa_training_resume_stage_20261111.py, which builds a disposable tree from integrated_world_training_resume_candidate_20261111.py. That stage replaces WorldJEPA/checkpoint sources and sets V13_EXPECT_OPTIMIZER_STATE_PERSISTED=1 only in the staged subprocess. The staged overlay, not production source, is what persists optimizer state.
- The 66/66 V14 T8/Store tests exercise the V14 consumer, which still reports optimizer_moments_persisted=false; they do not prove optimizer persistence. Production v13/code/v13/world_jepa_shadow_checkpoint.py remains inference-only and returns optimizer_state_persisted=false. Production WorldJEPAStoreConsumer persists numeric model/EMA state but resets Adam moments on each update.
- Staged optimizer result: persistent Adam m/v and a moment-reset control started at holdout loss 0.363245. Persistent ended at 0.345502 (old-holdout retention delta -0.018170); moment-reset ended at 0.351362 (retention delta -0.013847). This is one synthetic staged cohort, not production runtime or user data.
- Staged replay negative result: hard-error replay ended at holdout loss 0.905487 from 0.366633, old-holdout retention delta +0.532650, retention gate false. Matched uniform-sampled replay ended at 0.373938 with retention delta +0.002480 and was also rejected. Do not promote hard replay; keep it non-default/OFF and do not relax gates.
- V14 consequence: promote the training-resume overlay into the real Store/Runtime checkpoint path with source pins, atomic model+EMA+Adam state, lineage, restart/crash/rollback tests and negative controls. Keep the staged result labeled STAGED_OVERLAY until production consumer and device acceptance are proven.

### R-021 — matched optimizer/replay ablation on the Store-backed WorldJEPA candidate
- Exact candidate: RedMentos/Aii PR #2186, head 4b01ecdfb87e4e5b1b5bc59d934d1536aef8d836; GitHub Actions runs staged/integrated 44893257398 and T8/Store 44893257355.
- Environment/evidence: GitHub Actions Linux, synthetic SQLite Store and numeric NumPy WorldJEPA. V14 T8/Store: 66 passed on Python 3.13 and 66 passed on Python 3.14; staged-runtime 249 passed / 10 skipped / 47 subtests; integrated-regression 415 passed / 3 skipped / 58 subtests. No local full-checkout, native GGUF or Redmi proof.
- Optimizer moment result: persistent Adam m/v and a control that zeroed m/v while retaining the global step both started at holdout loss 0.363245. Persistent ended at 0.345502 (old-holdout retention delta -0.018170); moment-reset ended at 0.351362 (retention delta -0.013847). Both passed the current synthetic retention gate and JEPA beat the action-conditioned mean-delta baseline. This single cohort does not establish a general optimizer winner.
- Replay negative result: hard-error replay ended at holdout loss 0.905487 from 0.366633, old-holdout retention delta +0.532650, and retention_gate_accepted=false. Matched uniform-sampled replay ended at 0.373938 with retention delta +0.002480 and was also rejected by the current gate. The hard arm is therefore not an improvement in this cohort; keep it non-default/OFF and do not relax utility/retention gates.
- V14 consequence: keep uniform/no-replay as baselines; run repeated seeds, equal update/replay-byte budgets, source/content-disjoint new/old holdouts and A->B->A return-to-old dynamics. Persist the negative result in the handoff; do not call one synthetic cohort continuous learning on user data.

### R-022 — Android 13 AOSP private-data path semantics
- Primary source: Android Open Source Project, platform/system/core/rootdir/init.rc, branch android13-release, blob cd71aa8aa947644e6d4c476897757e9a457aba2b; accessed 2026-11-21: https://android.googlesource.com/platform/system/core/+/refs/heads/android13-release/rootdir/init.rc
- Verified source lines: 673-675 set /data to system:system 0771; 843 creates /data/data as system:system 0771; 915-923 create /data/user and bind-mount /data/data onto /data/user/0.
- V14 consequence: a strict private-app DB path validator must reject broad group/world-writable ancestors while making only the exact AOSP root/legacy exceptions, with UID, GID and mode checks and negative controls for wrong owner/group/mode and writable descendants. PR #2190 implements this narrow audit-DB path exception and is merged at code head e18c664...; its broker tests remain synthetic. This source review is not proof of the Redmi's vendor-specific mount/SELinux state.
- Limitations: AOSP init configuration does not attest the user's particular Redmi build, mount namespace, SELinux policy or actual runtime permissions. No device measurement was available; keep REDMI_UNVERIFIED.


## Research & implementation update — 2026-11-21 11:29 CET (Research & Perception)

### R-023 — Atomic first-use binding for runtime-local temporal perception state
- Observed code defect: _runtime_temporal_voice_registry used an unsynchronized get/create/set sequence. Concurrent first audio calls on one Runtime could each construct a registry; each caller could update a different instance while only the last instance remained attached to Runtime. That breaks temporal continuity across simultaneous streams.
- Change: a short module-level initialization lock plus a second read makes first-use registry binding atomic. The registry remains Runtime-local, source/generation-keyed, internally RLock-protected and LRU-bounded to 16 streams. It retains only scalar evidence/timestamps; PCM, transcripts and speaker identity remain absent.
- Regression: an eight-worker barrier test delays construction and asserts exactly one registry instance is created and returned to all callers. Exact-head GitHub Actions run 44895064274 passed 29/29 on Python 3.11 and 29/29 on Python 3.13.
- Evidence boundary: local Aii checkout is blocked by GitHub DNS; no local exact-source compile/test PASS. CI is Linux/synthetic only. Redmi/Termux remains REDMI_UNVERIFIED.
- Integration boundary: the adapter still consumes caller-supplied PCM16. Core #2158 must pin the exact V3 producer and temporal module, preserve text/audio PerceptPacket modality separation, and prove B1/B2 OfferPacket delivery through C4/C3. This change does not supply microphone capture, trained VAD, speech decoding, full-duplex or native JEPA coupling.
- Research note: no new paper is claimed in this checkpoint; this is a concurrency correction derived from the actual Runtime consumer path. The existing R-018 VAD/license/ABI notes remain the source review for WebRTC/libfvad.


## Research update — 2026-11-21 11:40 CET (Research & Perception)

### R-024 — Tiny causal VAD candidates: kiloVAD/PulseVAD, Silero and Android runtime claims

**Primary paper read in full:** Stephen Bauer, Sheila Seidel, Shanza Iftikhar, Scott Veidenheimer and Gorkem Ulkar, “VAD to the Bone: Ultra-Tiny Speech Activity Detection for Edge Deployment”, arXiv:2607.25870v1, submitted 2026-07-28; the arXiv record states accepted for INTERSPEECH 2026. The paper's kiloVAD is a CNN-only, standard-Mel, strictly causal detector. The pruned 2.1k-parameter model reports 0.850 ± 0.007 AUC on AVA-Speech (8 surviving seeds; 2 of 10 collapsed under aggressive pruning), 44k MACs per inference and 200 ms context. The 81k model reports 0.862 ± 0.001 AUC. The paper reports AUC 0.798 at 60 ms context, 0.862 at 200 ms and 0.872 at 360 ms: tiny parameter count does not remove the input-context latency. INT8 post-training quantization is reported essentially lossless; angle-aware self-distilling INT4 QAT improves 1–4% over STE QAT. These are paper-reported AVA-Speech results, not Android measurements.

**Maintained implementation candidate:** AydinAdnan/PulseVAD repository HEAD af25e79d66830a3fee74541812721f6158fc92b5 (2026-09-09). Its repository LICENSE is MIT; README lists 2,118 parameters, 2.1 KB INT8 weights, a 26.8 KB ONNX graph, 12 KB FP32 graph, 38 KB TorchScript and a 10 KB C header, all using a 64-bin log-Mel frontend and 200 ms causal windows. Its author-reported September 2026 matched benchmark uses about 82 minutes, non-overlapping 200 ms windows and threshold sweep: mean F1 90.1% vs Silero 93.6%; music-only false-alarm 33.3% vs 15.7%; noise-only false-alarm 6.3% vs 0.0%. The README says near-mic/clean-to-moderate conditions are its target and explicitly acknowledges weaker music and far-field noise performance. The paper's kiloVAD checkpoints are separately described by the repo as CC BY-NC and excluded; do not confuse those with PulseVAD's MIT repo/model claim. Reproducibility caveat: README benchmark datasets (DEMAND/GTZAN and 82-minute comparison), REPRODUCE.md pipeline datasets, and ATTRIBUTION.md dataset list are not identical; exact artifact/data-manifest reproduction is not yet independently verified. PulseVAD is therefore a research candidate, not an accepted product dependency.

**Streaming baseline:** snakers4/silero-vad upstream README identifies MIT licensing, ONNX CPU support, 8/16 kHz input, and sub-1 ms processing for a 30+ ms chunk on one CPU thread; the JIT model is around 2 MB. The upstream page does not establish Termux/Bionic ABI, Redmi Note 10 Pro RSS or battery cost. This is the more relevant low-latency comparison candidate than a 200 ms-only gate, but remains unmeasured on target hardware.

**Android implementation claim rejected for source reuse:** VoxRT/voxrt-silero-android v0.1.2 says API 26+, arm64-v8a, 1.2 MB Silero weights, a 424 KB native library and ~1 ms / 32 ms frame (3.05% RTF) on a Redmi 9C / Snapdragon 662. The Kotlin wrapper is Apache-2.0 and Silero weights MIT, but the bundled inference runtime is explicitly proprietary. Its measurement is vendor-reported on a different device. Do not import the binary runtime into V14; it can only be a reference point for a later open-runtime benchmark.

**V14 decision / testable next step:** keep RAW EAR V3 prosody, non-speech cues and temporal A4 evidence first-class. A VAD output is a separate speech-presence probability/gate, never a replacement for raw acoustic perception. When a permitted local benchmark is available, compare the current heuristic, WebRTC/libfvad, Silero ONNX and PulseVAD on the same licensed/consented annotated corpus with 20/32/40/200 ms windows; record onset/offset p50/p95, FAR on noise/music, FPR/FNR, CPU time, RSS/PSS and battery. PulseVAD's 200 ms context makes it a possible low-power coarse gate, not a barge-in/fast-turn detector. No model, weight, runtime or dependency was downloaded or swapped in this run.

Primary sources:
- Paper (full text, v1, 2026-07-28): https://arxiv.org/abs/2607.25870
- PulseVAD code/model repository and MIT license: https://github.com/AydinAdnan/PulseVAD/tree/af25e79d66830a3fee74541812721f6158fc92b5
- PulseVAD reproduction protocol: https://github.com/AydinAdnan/PulseVAD/blob/af25e79d66830a3fee74541812721f6158fc92b5/REPRODUCE.md
- Silero VAD upstream: https://github.com/snakers4/silero-vad
- VoxRT Android wrapper/runtime license statement: https://github.com/VoxRT/voxrt-silero-android


## Research & implementation update — 2026-11-21 11:52 CET (Research & Perception)

### R-025 — Real pinned libfvad shared-library smoke on Linux CI

- **Upstream source pin:** dpirch/libfvad commit 532ab666c20d3cfda38bca63abbb0f152706c369 (2024-02-07). README documents the standalone C API and the upstream-derived WebRTC VAD implementation; LICENSE is BSD-3-Clause and the repository also ships a separate WebRTC PATENTS grant. The patent notice is part of the review, not an optional omission.
- **Comparator correctness:** the previous result field named webrtc_baseline was emitted for any backend and the alignment text said WebRTC even for libfvad or the test EnergyBaseline. The harness now always emits vad_baseline and emits the webrtc_baseline compatibility alias only for the actual WEBRTCVAD_PYTHON_WHEELS backend.
- **Native Linux experiment added:** the comparison workflow checks out the pinned libfvad commit, runs autoreconf/configure/make/make check/make install, loads the resulting shared library through the actual ctypes LibFvadBackend, and runs the same synthetic 16 kHz PCM fixture. The test records the exact source revision in backend.version. The fake C-ABI stub remains a separate negative/contract test.
- **Status:** new exact-head CI pending. If successful, classify only as NATIVE_LINUX_PROOF for the pinned libfvad C ABI and synthetic fixture. It is not an Android/Bionic build, Redmi measurement, speech-corpus accuracy result or production dependency.
- **Safety/licensing:** no libfvad binary is committed or copied into the app; the CI build is ephemeral. No production dependency, model, weight or user audio is added. Keep the BSD-3-Clause plus PATENTS review attached to any future product reuse decision.
