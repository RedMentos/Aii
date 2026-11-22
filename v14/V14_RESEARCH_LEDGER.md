# V14 / Inquisition-JEPA — laufendes Forschungsjournal

**Stand:** 2026-11-22. **Arbeitsart:** ergebnisorientiertes laufendes Research, nicht bloß Literaturanhang.  
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


## R-024 — Persistent JEPA test-time learning vs optimizer drift — 2026-11-21

**Primary sources read:**
- Zhang et al., *JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts*, arXiv:2610.00722 (v1, 2026-09-30), https://arxiv.org/abs/2610.00722. The method adapts an action-conditioned latent dynamics predictor from observed transitions, uses dense temporal replay, and carries adaptation across episodes. Its matched persistence control holds update count fixed while carrying predictor + optimizer state; the paper reports a substantial advantage over resetting in its tested continuous-control environments. This is not evidence that the same effect transfers directly to V14's small tabular/state predictor or Android workload.
- Li et al., *STABLE: A Continual Learning Optimizer with Adaptive Drift Control*, arXiv:2611.10655 (v1, 2026-11-07), https://arxiv.org/abs/2611.10655. It argues that carried Adam/AdamW moments can themselves create a task-boundary stability gap: old-task geometry may scale new-task updates poorly. Its proposed primal-dual drift budget is an optimizer-level stability/plasticity control. This is a candidate research direction, not an adopted implementation.

**V14 implication:** production WorldJEPA currently persists predictor/EMA checkpoint state but its checkpoint module explicitly reports `optimizer_state_persisted=false`. The #2186 staged overlay is not production evidence. The next implementation should compare, on identical source-disjoint cohorts and equal update counts: (A) reset moments, (B) persistent Adam moments, and (C) persistent moments plus a bounded drift controller. Keep replay modes separately ablated (none/uniform; do not reuse the previously rejected hard-replay setting). Record parameter/EMA deltas, new and old holdout loss, negative controls, restart equivalence, and rollback. Only promote the method with repeated seeds and no retention regression; optimizer permission remains OFF by default.

**Status:** RESEARCHED / NOT_IMPLEMENTED / NO_ANDROID_PROOF. The two papers study different environments and model families; neither justifies automatic optimizer-state carryover or a live weight update in V14.

## R-025 — STABLE: optimizer-level drift control for continual adaptation (2026-11-21)

**Primary paper and implementation**
- Li et al., *STABLE: A Continual Learning Optimizer with Adaptive Drift Control*, arXiv:2611.10655v2 (first submitted 2026-11-07; v2 2026-11-10), accepted at NeurIPS 2026: https://arxiv.org/abs/2611.10655
- Official implementation: https://github.com/atlas-luiss/STABLE, exact repository HEAD `41e3e49e86b5fae6714ee564f21d7f637736f4a0`; optimizer source blob `609210850c62276b82a6863def957dad49ad27df`; README blob `a14b48cb0fa482ce55724f46daf1d6babd1a73f1`.
- **License:** repository MIT (`LICENSE` blob `971b49084efab6b1c458d9184d2f2e35c7e1dd4e`). Third-party notices identify Apache-2.0-derived DualPrompt/timm code in the separate prefix-ViT pipeline. No source, dependency, dataset or weight was imported.
- **Runtime mismatch:** upstream tested Python 3.12, PyTorch 2.8, CUDA 12.8 and one A100 64-GB GPU; requirements include torch/torchvision/timm. It is not an Android/Termux dependency candidate. The optimizer equations can be independently prototyped in the existing NumPy WorldJEPA learner without importing PyTorch or the vision stack.

**Method checked**
- At each task boundary, snapshot trainable parameters as an anchor. For later tasks, add the Lagrangian pullback term `2 * lambda * (theta - anchor)` to the gradient before Adam.
- Measure squared parameter drift from the anchor. Increase the dual multiplier when drift exceeds the budget plus a dead zone; decay it when drift is safely below the budget; otherwise hold it. Optional violation memory increases response to repeated overshoot. The first task can calibrate a drift budget from recent update magnitudes.
- The paper's guarantee is conditional on local score stability for distance-based classifiers. Its reported experiments are continual vision PEFT (LoRA/prompt adapters), not a JEPA world predictor, language model, native GGUF body or Android workload. Treat the paper's results as a research hypothesis, not V14 evidence.

**V14 consequence / experiment proposal — NOT IMPLEMENTED**
- Candidate use is a *soft, per-organ drift governor* on a small numeric WorldJEPA predictor or explicitly selected adapter, not a permanent freeze and not an Age/resource-budget control. The anchor should be refreshed only at a measured dynamics/task boundary; the dual multiplier should be able to relax so plasticity returns.
- After the current production-Store A→B→A experiment is fixture-correct and green, compare (A) reset optimizer, (B) persistent Adam, and (C) persistent Adam plus a STABLE-style NumPy dual drift controller. Match source-disjoint cohorts, update steps, replay mode/bytes, seeds and checkpoint budget. Record per-phase parameter/EMA drift, new/old holdout losses, action-shuffled/zero controls, A→B→A reacquisition, restart equivalence and exact rollback.
- Do not accept a single-seed gain or a lower drift value as utility. The controller must preserve useful adaptation and improve or at least not regress prior-task retention across repeated seeds. Continuous streams may not have clean task boundaries; boundary detection itself must be measured, and a false boundary can over-constrain learning.
- Keep runtime learning/optimizer gates OFF. No native model-weight update, device action, dependency install or model swap is authorized by this research note. A future implementation needs its own test/ablation PR and explicit approval before any Redmi/native experiment.

**Status:** RESEARCHED / EXPERIMENT_PROPOSED / NOT_IMPLEMENTED / NO_ANDROID_PROOF.


## R-026 — Source-bound diversity for multi-scale B1/B2→C4 selection (2026-11-21)

**Primary sources checked**
- Carbonell & Goldstein, *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*, SIGIR 1998. Author-hosted full paper: https://www.cs.cmu.edu/~jgc/publication/MMR_DiversityBased_Reranking_SIGIR_1998.pdf. MMR combines query relevance with novelty relative to already selected passages; the paper reports its clearest advantage in non-redundant multi-document summarization. The method's relevance/novelty trade-off is user-tunable.
- Santos, Peng, Macdonald & Ounis, *Explicit Search Result Diversification through Sub-Queries*, 2010, DOI https://doi.org/10.1007/978-3-642-12275-0_11; bibliographic/abstract record: https://eprints.gla.ac.uk/44352/. xQuAD uses explicit query aspects and rewards coverage of aspects not yet represented, rather than only comparing each candidate with already selected candidates.

**V14 implication — research, not an algorithm claim**
- The merged C4 source-span rule is a conservative provenance gate, not MMR, xQuAD, a learned semantic-diversity model, or true B3 latent coupling. It discounts a B1/B2 redundancy penalty only when both offers carry valid refs for the same source ID, digest and modality, their spans are disjoint, and lexical overlap is low. This protects potentially complementary fine-detail and gist contributions from being discarded solely because both summarize the same user turn.
- Next ablation: compare (A) existing C4 redundancy, (B) source-span gate, and (C) a bounded MMR-style novelty score on a fixed source corpus. If stable explicit sub-aspects can be produced without adding model latency, test an xQuAD-like coverage term separately. Hold model prompts and source evidence constant; report answer correctness, evidence-span coverage, duplicate evidence, false diversity (disjoint but semantically redundant spans), C3 context tokens/latency, B1/B2 contribution acceptance and per-role utility across repeated seeds.
- Required negative controls: same span/different modality; missing or malformed refs; same-role duplicates; overlapping spans; disjoint paraphrases that are still semantically redundant; one useful body plus one low-quality body. Keep source authority and model hypotheses separate.
- No paper code, third-party dependency, dataset or weights were imported. ACM/ACL paper text is cited as research only; no license to copy its code is inferred. The proposed experiment is not a native model or Redmi result.

**Status:** RESEARCHED / EXPERIMENT_PROPOSED / C4_SOURCE_SPAN_RULE_MERGED_INTEGRATION_CI_GREEN / NO_ANDROID_PROOF.


---

## Implementation evidence update — 2026-11-21 18:04 CET

This is a negative experimental result from the current V14 implementation branches, not a new paper and not a claim of native model learning.

### WorldJEPA A→B→A retention result
- **PR #2231 exact head:** `11b85db03c906d8616916bc6325a4c11ff2a9870`, base `7a07d01d3f6c9c3a4fb96511ae7decd73c27ccf9`.
- **PR #2237 exact head:** `390c12c2822645ec46a849901c467e0748f00390`, stacked on #2231.
- The uniform, uniform-budget and session-contiguous replay variants, in both full and predictor-only modes, report `UTILITY_GATE_REJECTED`. The emitted old-holdout-retention checks fail, with old-task loss deltas roughly **+0.009 to +0.270**. Some new-task holdouts improve, but those gains do not compensate for old-task regression.
- The shared documentation head `7a07d01` also has a Python 3.14 T8 failure in `test_pending_cohort_rollback_rewinds_cursor_and_replays_verified_rows`: the utility gate rejects the candidate, while the test expects `UPDATED_EXPERIMENTAL_WORLD_JEPA`. This is consistent with a fixture/utility mismatch, not evidence that an update should be forced through.
- **Environment:** GitHub Actions / synthetic Python–NumPy–SQLite–T8 state. No native GGUF body, Android device, Redmi training run or accepted production parameter update is involved.
- **Conclusion:** zero accepted updates are established by this experiment. The utility gate is doing its job by rejecting old-task regression. Do not lower thresholds, relabel rejected candidates as successful learning, or enable the optimizer/learning gates.

### Required next experiment
1. Fix the staged recovery-builder pin for #2231 from the exact candidate bytes; rebind the recovery → integrated stage → runtime deployer SHA chain after every composed change.
2. Construct matched source-disjoint A→B→A cohorts that can pass both new-task utility and old-task retention. Match update steps, replay mode/bytes, optimizer state and checkpoint budget; repeat across multiple seeds.
3. Report exact parameter/gradient/EMA/optimizer-moment diffs, old and new holdout losses, action-shuffled and zero-update negative controls, restart equivalence, cursor replay and exact rollback.
4. Keep the utility gate and all production/native learning permissions OFF until an accepted, reproducible update is demonstrated. A successful NumPy/SQLite experiment remains synthetic evidence only.

**Research interpretation:** R-025 (STABLE-style per-organ drift governor) remains an experiment proposal, not an adopted algorithm. R-026 (source-bound C4 diversity, with MMR/xQuAD as future ablations) remains a separate heuristic/research track. No paper, source code, dependency, dataset or model weight was imported or promoted in this checkpoint.

---

## R-031 — FD-VAD semantic endpointing for future full-duplex voice (2026-11-21)

- **Primary paper:** Puneet Mathur and Dinesh Manocha, *FD-VAD: Semantic Endpoint Detection for Streaming Full-Duplex Speech*, arXiv:2609.35791v1, 2026-09-16; full text reviewed at https://arxiv.org/abs/2609.35791. The repository paper citation still says “Submitted”; treat this as a preprint, not a peer-reviewed result.
- **Method:** causal 2.56 s audio window, refreshed every 320 ms; frozen WavLM-base-plus (50 Hz features) → two-layer downsampling/projection adapter (12.5 Hz audio tokens) → Qwen2.5-0.5B-Instruct. Only the adapter and LoRA are trained (10.3M parameters, ~1.7% of total). A confidence threshold and consecutive-decision gate trade false interruption against delay. It predicts semantic Continue/Stop directly from audio without an ASR transcript.
- **Reported evidence:** held-out Smart Turn v3.1 test: chunk F1 0.832 with 0.6% false-stop; complete/incomplete utterance accuracy 0.972/0.969. TurnBench dev: zero-shot EOT recall 0.853 at FP 0.097, with 1,019 ms median commit latency. The TurnBench setup first uses a Silero acoustic gate and requires at least 1 s of post-speech silence. The separate tau=0.9, K=1 operating point reports 190 ms median delay and 2.0% false-interruption; do not combine that number with the TurnBench result. The 45.8 ms per 2.56 s window (46.8 ms p90) was measured on one NVIDIA A100, not a phone.
- **OSS and rights checked:** official repository https://github.com/fd-vad/fd-vad at HEAD `99112fc9cf6efbf80f556378d8e553d78a932300`; root LICENSE is MIT. README confirms code-only repository and a ~120 MB adapter/LoRA checkpoint; WavLM and Qwen base weights are downloaded separately. Model card https://huggingface.co/puneetUMD/fd-vad marks the checkpoint MIT and lists a ~119 MB adapter and ~1.5 GB self-contained offline bundle. WavLM-base-plus is MIT, Qwen2.5-0.5B is Apache-2.0, and Smart Turn v3.1 data is BSD-2-Clause. The README quickstart requires PyTorch/torchaudio; the pinned lock includes torch 2.6 CUDA 12.4, Transformers, PEFT and a large training stack. The small pyproject dependency list is not the complete model runtime.
- **Limits:** English-only model/data; no Android arm64/Bionic build, CPU-only inference, RAM/PSS, battery or Redmi benchmark was found. A 1.5 GB offline bundle plus framework/runtime overhead is a substantial unmeasured cost, and a second 0.5B semantic model could duplicate C3 work.
- **V14 consequence:** keep acoustic A0–A5/RAW EAR separate from semantic turn completion. A future optional `TURN_STATE` head may consume causal audio evidence and emit Continue/Stop/Uncertain with calibrated confidence; it must not replace pitch/prosody/non-speech signals or become a permission gate. First compare a small temporal head against the current acoustic path at the same 320 ms cadence, measuring false interruption, EOT recall, commit latency and RAM. No code, model, dataset or dependency imported.
- **Status:** FULLTEXT_REVIEWED / OFFICIAL_CODE_AND_MODEL_CARD_LICENSE_READ / NOT_IMPORTED / NOT_MOBILE_VALIDATED / NO_ANDROID_PROOF.

## R-032 — S4VAD: latency-aware streaming acoustic VAD (2026-11-21)

- **Primary paper:** Elad Cohen, Arnon Netzer and Hai Victor Habi, *Low-Latency State Space Voice Activity Detection with Robust Onset Time Evaluation*, arXiv:2609.11110v1, 2026-09-10; full text reviewed at https://arxiv.org/abs/2609.11110. Preprint; no S4VAD-specific official implementation or license was found.
- **Method:** four causal S4 blocks, hidden dimension 64, 64-dimensional log-Mel input at 16 kHz, 32 ms frames and 10 ms hop. The convolutional S4 kernel is replaced by a recurrent state update for streaming inference. The paper also models onset annotation uncertainty instead of treating human timestamps as exact.
- **Reported evidence:** S4VAD reports 0.3 ms model hardware latency at the paper's target FPR; onset latency is 39.3 ms on LibriSpeech and 114.3 ms on AVA-Speech. Its LibriSpeech onset-latency distribution lists P50 10 ms, P90 90 ms and P95 130 ms. Evaluation uses synthetic LibriSpeech+DNS mixtures and AVA-Speech; hardware inference uses XNNPACK on an Apple M4 Max 64 GB. These are not Android or 6 GB phone measurements.
- **V14 consequence:** extend the existing RAW EAR/libfvad/Silero comparison with event-level onset/offset delay and annotation-uncertainty intervals, not only AUROC/F1. If reproducing, match frame/hop, CPU thread count and false-positive operating point; test a small stateful temporal filter/head before importing a full S4 stack. The general `state-spaces/s4` repository is Apache-2.0, but it is not an S4VAD-specific implementation and is not imported.
- **Status:** FULLTEXT_REVIEWED / NO_S4VAD_CODE_OR_WEIGHT_LICENSE_VERIFIED / NOT_IMPLEMENTED / NO_ANDROID_PROOF.

### R-031 implementation audit and TurnBench caveat — 2026-11-21

- Exact official FD-VAD repository HEAD and MIT LICENSE were checked via GitHub. README states that the repository ships code only; the ~120 MB adapter/LoRA checkpoint and the frozen WavLM/Qwen bases are separate artifacts. The model card lists ~1.5 GB for the fully offline bundle.
- The official README quickstart uses PyTorch and torchaudio. The pinned lock includes CUDA 12.4 PyTorch packages, Transformers and PEFT; the minimal pyproject dependency list does not describe the full inference stack. No Android/Termux CPU/ARM runtime was demonstrated.
- Full-text caveat: the TurnBench result uses a Silero acoustic gate that requires at least 1 s of post-speech silence. Therefore 0.853 EOT recall at FP 0.097 is conditional on that gate and has 1,019 ms median commit latency. The 190 ms / 2.0% false-interruption point is a separate operating point.
- Decision unchanged: do not download/import FD-VAD or replace RAW EAR. Keep semantic `TURN_STATE` separate and optional; compare a lightweight temporal head before considering a second 0.5B LLM.


## R-033 — Foreground VAD and Android voice-stack reuse candidates (2026-11-21)

### Mamba-FVAD — abstract reviewed only
- Primary record: Mamba-FVAD: A Lightweight Foreground Voice Activity Detection Model for Overlapped Speech, arXiv:2609.19856v1, submitted 2026-09-17: https://arxiv.org/abs/2609.19856
- The abstract describes enrollment-free foreground-speech detection under competing speakers and reports 1–2 ms per frame on CPU. The arXiv full text was not accessible in this review, so architecture details, parameter count, hardware, exact frame definition, dataset protocol and confidence intervals are not claimed as reviewed. Secondary summaries disagree on CPU latency; the abstract number is not an Android estimate.
- No official source repository, downloadable checkpoint or weight license was verified. No code, data or weights imported.
- V14 implication: if foreground selection becomes necessary, treat it as a separate optional cue beside RAW EAR prosody/non-speech evidence. Evaluate foreground recall/FAR, missed quiet target speech, interruption precision and speaker-switch behavior on a licensed multi-speaker corpus. Do not infer identity, diarize, or replace the existing acoustic stream with a foreground label.
- Status: ABSTRACT_REVIEWED_ONLY / NO_OFFICIAL_CODE_OR_WEIGHT_LICENSE / NOT_IMPLEMENTED / NO_ANDROID_PROOF.

### Maintained Android voice projects — reuse review
- soniqo/speech-android main HEAD 66059f2a… and its speech-core submodule pin 852d9d1…; soniqo/speech-core main HEAD 59b9d790…. Repository/core root licenses are Apache-2.0. The Android wrapper is Kotlin/JNI with C++17 core, so it is not a drop-in dependency for the current Termux Python runtime.
- Its README describes a Silero VAD v5-only path at about 2 MB download and under 10 MB peak RAM, a 40 MB VAP model, and a much larger full voice stack (about 1.2 GB). These are upstream project claims, not independent V14 or Redmi measurements. VAP is relevant to future full-duplex turn-taking (user/agent two-channel context); its architecture is MIT while the cited weights are CC BY 4.0. Model and dependency licenses remain separate from the wrapper license.
- VoxRT/voxrt-silero-android main HEAD 77b56e6… advertises roughly 1 ms per 32 ms frame on a Redmi 9C / Snapdragon 662. Its Kotlin wrapper is Apache-2.0 and Silero weights are MIT, but its native runtime binary is proprietary and restricts repackaging/modification. This is a vendor benchmark on a different phone, not evidence for Redmi Note 10 Pro; reject for core reuse under the current open/reproducible requirement.
- No candidate was downloaded, installed, benchmarked on a device, or substituted for the existing optional caller-owned Silero ONNX adapter.

### Concrete V14 decision
- Keep RAW EAR V3 as the source-bound acoustic feature producer. Preserve prosody, pitch confidence, impulsive/non-speech and uncertainty fields; speaker identity/timbre and calibrated speech probability remain explicitly unmeasured.
- Revisit Soniqo VAP only when the voice effector and permissioned microphone path exist, with a separately licensed model artifact and measured Android memory/latency. It cannot replace raw ear or prove full duplex by itself.
- No model swap, new dependency, microphone permission, or learning gate change is authorized by this research.

Status: RESEARCHED_WITH_ABSTRACT_LIMIT / OSS_LICENSES_REVIEWED / NO_IMPORT / NO_DOWNLOAD / REDMI_UNVERIFIED.
## R-034 — Counterfactual World Models: residual reuse for same-event action outcomes (2026-11-21)

- **Primary paper:** Randall Balestriero, Yann LeCun and Kerda Varaku, *Counterfactual World Models: JEPAs That Reason About “What If”*, arXiv:2611.24778v1, submitted 2026-11-18. Full HTML paper reviewed: https://arxiv.org/html/2611.24778. This is a new preprint, not a peer-reviewed result at this checkpoint.
- **Core result:** a factual action-conditioned predictor mu(H,a) estimates an individual alternative outcome after observing the factual transition using z_cf(a') = z_next + mu(H,a') - mu(H,a_t). The observed endpoint preserves the event-specific residual; the model supplies only the predicted action contrast. A physical-readout variant applies the same correction after a state readout, which can be materially more additive than raw embedding coordinates.
- **Theory and boundaries:** factual marginals—even exact generative likelihoods—do not identify same-event counterfactual coupling without additional structure. Residual reuse is exact for additive disturbances and has a short-transition O(h^2) relative-error result when action and disturbance enter through separate smooth channels, the context is sufficient, actions have support/overlap, and the behavior policy uses only recorded context plus independent randomization. It can fail at contacts, clipping/saturation, command-multiplying/gain faults, folded coordinates, insufficient state context, and raw pixels. The interaction ratio rho = Var(Y(a') - Y(a)) / Var(Y(a')) is a paired/simulator evaluation diagnostic; factual logs alone cannot certify small rho. Do not apply one residual across later transitions unless the disturbance persists.
- **Reported evidence:** seven rendered simulators and frozen DINOv2/MAE encoders, with four further encoders in follow-up comparisons. At 8k factual episodes per environment and three seeds, readout-space correction reports 85.6–95.7% physical counterfactual R^2 on four primary tasks versus 38.1–45.6% for the same factual predictors; feature-space correction reaches 73.4–94.1% there. BlueROV2 requires substantially more factual data and a physical readout. Hindsight planning reports 35–69% success versus 14–23% for a simulator oracle that lacks the observed event outcome. All environments are simulated; these are not real-robot, Android, or mobile-latency results.
- **Official OSS and exact revision:** https://github.com/galilai-group/counterfactual-WM at 5c84bba92b2ff19d41175070a61238fa1396d10d (2026-11-19). Repository code is MIT; cwm/sims/vendor/pusht_env.py has its own MIT notice and BlueROV2 meshes are LGPL-3.0. The repository ships no pretrained weights, behavior policies or datasets. Separate artifact licenses include MAE ViT-B/16 CC-BY-NC-4.0, DINOv2 Apache-2.0, DINOv3 custom, SigLIP 2/CLIP Apache-2.0, EVA-02 MIT, V-JEPA 2 model-card terms, Push-T policy Apache-2.0, and a Ball-in-Cup policy with no stated license. Dataset cards and simulator licenses remain separate. Do not use the unlicensed Ball-in-Cup policy or MAE weights in a commercial V14 path without an independent rights decision.
- **Runtime/deployment caveat:** the official reproduction specifies Linux x86_64, Python 3.11, NVIDIA CUDA 13/R580+ and EGL; its paper reproduction used about 150 GPU-hours and rendered datasets ranging from several GB to tens of GB. This is a research reproduction stack, not a candidate Termux dependency or Redmi model. No code, data, dependency or weights were imported.
- **V14 consequence:** propose a separate, opt-in same-event counterfactual outcome field for World/Self/JEPA replay and action-error attribution, not a replacement for factual prediction, not evidence of learned cross-organ latent coupling, and not a direct authority to execute alternative actions. The candidate must carry the factual event/source, executed action, queried alternative action, context/version and observed endpoint; retain a factual-only baseline, action-shuffle/zero-residual negative controls, and report error by interaction/failure mode. First validate on a tiny synthetic additive-vs-gain-fault/contact fixture; only promote after paired/simulator evaluation confirms where the correction improves over the factual predictor. Core/JEPA ownership is required for the real Runtime consumer.
- **Status:** FULLTEXT_REVIEWED / OFFICIAL_REPO_AND_LICENSES_CHECKED / PAPER_CODE_NOT_IMPORTED / EXPERIMENT_PROPOSED / NO_ANDROID_PROOF.
## R-035 — Age of Learning: temporal persistence of verified prediction errors (2026-11-21)

- **Primary paper:** Chenyang Wang, Stefan Forsström, Roger Olsson, Di Yuan and Qing He, *Age of Learning: Temporal Persistence of Prediction Errors as a Learning Signal*, arXiv:2609.32593v1, submitted 2026-09-26. Full paper text reviewed at https://arxiv.org/abs/2609.32593. Preprint; no peer-reviewed status claimed.
- **Method:** sample-level instantaneous AoL is one when a prediction is correct and increments while misclassified; an EMA aggregates prior error episodes. Normalized sample- or class-level AoL weights are applied to loss or weighted resampling. The online version tracks only O(C) class state, evaluates a current batch or replay buffer, increments when observed class accuracy is below a threshold, resets when recovered, and leaves unobserved classes unchanged. The official README clarifies that the reported online AoL update runs once after each training epoch, not each SGD mini-batch.
- **Evidence:** offline CIFAR-10/100 long-tail tests use ResNet-32, 200 epochs, batch 128 and NVIDIA TITAN X; selected AoL variants generally match or improve baselines, with e.g. CIFAR-10 IF-400 Softmax 60.32% → 63.94% and Sigmoid 60.17% → 66.62%. Online Period-10 CIFAR results use three seeds (42, 1024, 2026): mean gains are +3.10±0.51 points for CIFAR-10 IF-200, +1.42±1.15 for IF-50, and +0.92±0.24 for IF-10; CIFAR-100 gains are +2.31±0.89, +1.42±0.91 and +0.02±0.03. Period-1 fast-changing/sparse streams can lose the benefit, especially at IF-200. Large-scale Places365/ImageNet tests use four NVIDIA GH200s and a 500k buffer; these are not mobile measurements.
- **Limitations:** the paper deliberately uses binary correctness, not error severity, confidence or semantic type. Noisy labels, ambiguous cases and OOD inputs can accumulate high AoL without becoming useful training targets. The streaming signal depends on sufficient temporal consistency and observed evaluation opportunities; it is not elapsed wall-clock time and is unstable when the distribution changes too rapidly. Results are classification/long-tail experiments, not generative JEPA, multimodal, voice or action-outcome evidence.
- **Official OSS/license:** https://github.com/sanyeungwang/Age-of-Learning at 686fd16da98c31c5ad601d1b018deeb318f03e97. Root code is MIT. The repository has no requirements.txt; main.py imports NumPy, LMDB, Pillow, PyTorch and Torchvision. No weights or datasets are bundled. No code, dataset, dependency or weight was imported.
- **V14 consequence:** test a separately named error_persistence_steps / error_persistence_ema signal as a *modulator* for source-bound, actually verified World/JEPA prediction errors. Do not call it official Age or conflate it with Age 0–5 capability rights. For open outcomes, retain a distinct PENDING state until the event's justified observation window closes; only then record a verified omission or mismatch. Do not increment on silence, missing logs, unavailable sensors, ambiguous/OOD evidence or unobserved replay. Bind state to organ, source, event, prediction target and evaluation version; reset or decay only after verified resolution. Compare against instantaneous loss, shuffled event order, zero-persistence and zero-update controls; preserve old-task utility/retention gates. This is an experiment proposal, not permission to activate production learning.
- **Status:** FULLTEXT_REVIEWED / OFFICIAL_CODE_AND_MIT_LICENSE_CHECKED / PAPER_CODE_NOT_IMPORTED / EXPERIMENT_PROPOSED / NO_ANDROID_PROOF.
## R-036 — Omission is a time-bound, precision-weighted event; attention acts at a later update stage (2026-11-21)

- **Primary empirical study 1:** Yuki Suda et al., *Propagation of Prediction Signals Revealed by Synchronous Oscillations in the Frontotemporal Network During Tone Omission in Macaque Monkeys*, European Journal of Neuroscience 62(12), first published 2025-12-28, DOI 10.1111/ejn.70360. Full article reviewed: https://onlinelibrary.wiley.com/doi/10.1111/ejn.70360. Two macaques, 256-channel ECoG, 1000-Hz/50-ms tones every 500 ms, 900 presentations and 100 omissions per session, with 10% random omissions versus every-10th predictable omissions; 67 sessions in one monkey and 87 in the other. Predicted omission showed pre-omission theta/alpha frontotemporal synchrony; phase-slope analysis suggested theta STG→PFC (bottom-up) and alpha/beta PFC→STG (top-down) directionality. Effects were not uniform across all bands/regions/animals. The authors could not fully separate predictions of omission from predictions of tone presence, and they note that shorter inter-stimulus intervals (about 150 ms or less in earlier work) change omission responses. This is biological circuit evidence, not an AI architecture, Android audio result or direct instruction to emulate EEG bands.
- **Primary empirical study 2:** Tjerk T. Dercksen, Andreas Widmann and Nicole Wetzel, *Voluntary Attention Selectively Modulates Omission Responses*, Human Brain Mapping 47(5):e70518, published 2026-04-09, DOI 10.1002/hbm.70518, PMCID PMC13065894. Full text reviewed: https://pmc.ncbi.nlm.nih.gov/articles/PMC13065894/. Thirty-six adults enrolled; 33 analyzed, 63-channel EEG, visual hand-clap paired with sound every 0.9–1.15 s, 87.5% sound-present and 12.5% unexpected omission trials, with matched no-sound control blocks. Early oN1 (peaks 104/136 ms) and oN2 (~168 ms) were not convincingly modulated by attention modality; later fronto-central oP3 components (~338/370/432 ms) were larger when attention was directed to audition and reduced/absent when directed to vision. Thus early sensory omission/error and later attention-weighted contextual updating should not be collapsed into one scalar. The paper is CC BY 4.0; this is a human EEG result from one controlled paradigm, not proof of a universal attention law.
- **Synthesis/review:** *“Nothing” Really Matters: What Omission Responses Reveal About the Predictive Brain*, European Journal of Neuroscience, first published 2026-05-28, DOI 10.1111/ejn.70566, is a review rather than primary evidence. It distinguishes local regularity/adaptation responses from slower model-based, content-specific predictions and emphasizes that omission mismatch depends on expected timing, learned probability and precision. Treat it as a synthesis, not a single experiment.
- **V14 design consequence:** represent `PRESENT`, `EXPECTED_OMISSION`, `UNEXPECTED_OMISSION`, and `UNKNOWN/UNOBSERVED` separately. An omission may become evidence only at a source-bound expected-time window and only if the predicted event probability/precision is high enough; an absent log, muted microphone, permission denial, occlusion, delayed event or unavailable sensor must remain UNKNOWN, not a negative target. Keep raw A-plane acoustic/sensory evidence intact; let A4/JEF later apply attention/precision to contextual updating without erasing the low-level mismatch. A5/World should retain expected event class, source, predicted time/window, probability/uncertainty, observed state, attention context and eventual resolution provenance. For learning, distinguish an immediate signed sensory mismatch from a later context-update signal and from long-run error persistence (R-035). Do not infer human-like consciousness or copy neural frequency bands into the phone runtime.
- **Test proposal:** synthetic temporal fixture with four conditions (high-confidence present, high-confidence omission at expected time, low-confidence/misaligned omission, sensor unavailable). Assert only the high-confidence time-aligned omission emits an omission error; unknown/misaligned cases never train as negative labels. Then compare attention-on/off at the higher-level update stage while keeping raw acoustic packets identical. Preserve source/clock/consent, and use zero-attention and shuffled-timing negative controls.
- **License/reuse:** Dercksen et al. article states CC BY 4.0. Suda et al. article is marked Open Access on Wiley, but a specific reuse license was not verified here; no code, EEG data or figures were imported. No mobile implementation or Android measurement is available from either study.
- **Status:** TWO_PRIMARY_FULLTEXTS_REVIEWED / ONE_REVIEW_FULLTEXT_REVIEWED / DESIGN_HYPOTHESIS_ONLY / NO_CODE_IMPORTED / NO_ANDROID_PROOF.

## R-037 — Directed KV-cache transfer: reconstruction + receiver effect, with query-conditioned compression (2026-11-21)

### Primary research

- **Siyi Chen et al., “See What I See, Know What I Think: Dense Latent Communication Across Heterogeneous Agents,” arXiv:2606.13594v2, submitted 2026-06-11.** Full HTML reviewed: https://arxiv.org/html/2606.13594v2. Preprint; no peer-review claim. The method maps sender KV groups into receiver-compatible groups with positional disentanglement, per-group transformations/gates and two training phases: receiver-cache reconstruction followed by task-generation supervision. The six directed Qwen3-4B/8B/14B pairs plus Mistral-7B→Qwen3-4B show useful transfer in the evaluated regimes; the authors report that context-aware receivers can retain 10/288 KV groups while keeping 88.3/87.3/69.9% on GSM8K/ARC-Challenge/MATH-algebra versus 91.7/88.0/69.8% with the full cache, whereas context-unaware receivers need much denser retention. Their Qwen3 study used 30,000 reconstruction steps and 2,000 generation steps. The estimated payload is 27.2–30.2 MB/example for dense caches versus 3.17–3.95 kB for generated text; these are estimated message sizes, not measured mobile transfer or end-to-end latency. The paper is CC BY 4.0. It does not test LFM2.5↔Qwen3.5 or Android.

- **Maximillian Rossi et al., “Receiver-Conditioned Latent Communication gives 94% CacheBack,” arXiv:2609.32046, 2026-09-25.** Full HTML reviewed: https://arxiv.org/html/2609.32046. Preprint; no peer-review claim. CacheBack uses the receiver's question to score and select useful sender positions, without training a new adapter. On 50 FanOutQA tasks with Qwen3-8B and an 8×H100 setup, one reported 4× operating point is 55.3% strict accuracy vs 40.7% for same-size text (+14.7 pp) and 192 s vs 612 s median task completion (3.2×); the paper also reports 16× settings removing about 94% of sender positions across its tested families/topologies. This is GPU/server evidence, not Android evidence. The paper distinguishes full-cache context re-expansion from receiver-conditioned selection.

- **Fernando Cardenas Piepereit, “Architecture-Dependent Causal Transfer of Activation States Across Large Language Models,” arXiv:2608.16347v2, 2026-08-17.** Abstract reviewed only: https://arxiv.org/abs/2608.16347. The reported projection retrieval is 45–50% top-1 vs 5% chance for three decoder-only pairs, but the pre-registered generation-injection effect is significant for only Qwen2-0.5B→Phi-3-mini (23.3% vs 0% negative control, p=0.047 FDR-corrected); the two pairs targeting Mistral-7B show no effect despite representation alignment. This is an important counterexample: representational similarity/retrieval is not proof of useful receiver-side causal transfer. Full text and license were not verified in this run.

### Maintained OSS / license / fit

- **agentcacheback/cacheback** main, observed latest commit 5638d787524d863b29b7b9bf032ffa913faf5df4; code implementation commit 8cb09d7dd1621a5f653ddac89cacf68dc9a18f6f. Repository license: Apache-2.0. pyproject.toml declares Python ≥3.10, safetensors>=0.4.3, torch>=2.4, transformers>=4.57.1,<6; optional GPU stack pins vLLM 0.11.1 / Torch 2.9.0 CUDA 12.8. Its CPU quickstart uses Qwen3-0.6B. The public main API explicitly supports the same model or matching copies and says cross-model alignment is unsupported. The default stack is Hugging Face Qwen3 or vLLM, not the current V13 llama.cpp runner. No ARM/Termux/Redmi benchmark or model weights were imported. No code, data, dependency or weight was imported into Aii.

### Local runnable mechanism experiment

- Added v14/experiments/latent_cache_tiny/ with a PyTorch sender (2 layers, width 24, 4 heads), receiver (3 layers, width 32, 4 heads), learned directed K/V maps, per-head gates, Phase-I receiver-cache reconstruction, Phase-II receiver task-loss training, actual receiver cache injection, shuffled/no-message/random-adapter controls, and state save/reload equivalence.
- **LOCAL_LINUX:** CPython 3.13, PyTorch 2.10.0+cpu, NumPy 2.3.5; no Transformers package or model weights. py_compile PASS; python -m unittest -v **3/3 PASS** in 9.93 s. Seed-13 full run: 12.41 s wall, 344,584 KiB peak RSS. Held-out cache reconstruction MSE 6.5134→0.2054; Phase-I latent accuracy 85.94%; final latent accuracy 100%; exact receiver-context 100%; no-message 0%; shuffled cache 12.50%; random adapter 13.28%; adapter parameter ΔL2 20.2719; max Phase-I gradient norm 2.1451; serialized/reloaded receiver logits max delta 0.0. Three further seeds (17/29/41) each reached 100% latent accuracy; shuffled controls were 13.28/7.03/13.28%, random-adapter controls 9.38/11.72/17.97%. Exact results are in results_20261121.json.
- **Proof boundary:** this is a real gradient-trained adapter and receiver injection for newly initialized tiny PyTorch models on a synthetic associative-recall task. It is not OOD generalization, not a symbolic-message comparison, not a V13 production consumer, not LFM2.5/Qwen3.5 native inference, not GGUF/llama.cpp, and not Android.

### Verified V13 compatibility gap and design consequence

- Current V13 B1 is LiquidAI LFM2.5-1.2B-Instruct-GGUF; B2 is ggml-org Qwen3.5-0.8B-GGUF, so the actual pair is heterogeneous. v13/code/v13/runners.py uses llama-server HTTP generation/tokenization and a separate pooled /v1/embeddings purpose; its metrics explicitly set CAN_LATENT_TAP=False, CAN_LATENT_INJECT=False, CAN_TRAIN_BODY=False. The pooled embedding path is not per-layer K/V access. v13/code/v13/enlightened_space.py explicitly remains symbolic rather than a trained native JEPA receiver. Current production B3 therefore remains PARTIAL_SYMBOLIC_ONLY.
- **V14 design:** make context-aware vs context-unaware receiver availability an explicit channel property. A receiver that already has the source prompt may be able to use query-conditioned sparse transfer; a receiver without it needs dense or otherwise proven source-information preservation. A CacheBack-style selector is a candidate for same-model/matching-copy paths or after a compatible directed adapter, not a drop-in cross-model B1↔B2 solution. Use a separately trained adapter for each directed model/tap/revision pair. Require actual native cache tap and receiver injection, source-bound privacy/secret-leak controls, exact-context, no-message, symbolic, shuffled and OOD controls, task-level receiver effect, gradients/parameter diff, held-out retention, restart/rollback and real RSS/TTFT before any B3 authority or CAN_LATENT_INJECT=true.
- **Next executable step:** Core must expose a model-specific native K/V tap/injection seam for the existing llama.cpp/Android path (or explicitly evaluate a reversible native runner alternative without swapping models). Research/Perception can then run the same controls on the actual LFM2.5↔Qwen3.5 pair. No model download or production swap is proposed here.

- **Status:** TWO_LATENT_COMMUNICATION_FULLTEXTS_REVIEWED / ONE_CAUSAL_TRANSFER_ABSTRACT_REVIEWED / CACHEBACK_OSS_APACHE2_CHECKED / LOCAL_LINUX_TINY_MODEL_PROOF / NO_NATIVE_B1_B2_LATENT_PROOF / NO_ANDROID_PROOF.

## R-038 — Android UI observation permissions and source-bound A5 lease (2026-11-21)

### Primary platform documentation reviewed

- **Android AccessibilityService API:** https://developer.android.com/reference/android/accessibilityservice/AccessibilityService. The official reference describes AccessibilityService as an assistive service for users with disabilities, requires the user to enable it in system settings, and gates retrieval of interactive-window content behind declared service capabilities. This is not a general-purpose permission to scrape arbitrary app UI. V14 must not repurpose AccessibilityService for generic screen harvesting; use it only if the shipped feature genuinely provides disability assistance and the user explicitly enables it.
- **Android MediaProjection guide:** https://developer.android.com/media/grow/media-projection. Projection is a user-consented capture session with a system-mediated prompt and stop/lifecycle handling. Android 14/API 34 adds app-window sharing; on Android 13/API 33 the available projection scope is the full display, which may include unrelated apps, notifications and system UI. A consent receipt is session-bound; it is not a reusable permanent permission.
- **NotificationListenerService API:** https://developer.android.com/reference/android/service/notification/NotificationListenerService. Notification access is separately granted by the user through system settings; the service must wait for its listener connection before consuming notification events. This is notification-scoped input, not general screen access.

These are current official API references reviewed on 2026-11-21, not research papers. No third-party OSS implementation, model, code, weight, dataset or dependency was imported; no additional license obligation was introduced by this work.

### V14 implementation consequence

- Prefer APP_INTENT and CONTENT_PROVIDER events where the app exposes a supported API. Use NOTIFICATION_LISTENER only for notification-scoped events with current user-granted access. Accept ACCESSIBILITY_ASSISTIVE only with an explicit disability-assistance purpose and a separately verified OS provider. Accept MEDIA_PROJECTION only with a current per-session receipt; reject APP_WINDOW scope below API 34. Redmi Android 13 therefore cannot be described as app-only MediaProjection.
- Added a strict A5 metadata-only observation schema. It accepts event kind, source/session IDs, receipt reference, method/scope, Android API level, bounded Android ELAPSED_REALTIME interval and PROVISIONAL/FINAL provenance. It rejects screenshot bytes, UI text, node trees, package names, notification content, raw-capture persistence, action authority and learning authority.
- Added UIObservationLease bound to Runtime identity, active generation, source ID, receipt, capture session, capture method/scope, API level and thread. A5UIRuntimeAdapter consumes the existing Runtime/Store/A4 instance without changing the pinned Runtime source. The provider must expose a current-grant check, a linearizable guard shared with revocation, and a revocation subscription. The subscription remains active after the short lease exits; the provider callback must run after releasing its guard. Adapter revocation tombstones the A5 source, removes all packets referencing it, clears the bounded process cache, unsubscribes, and removes an unshared blob. Downstream cache reads expose FINAL packets only.
- Added adapter entrypoints for lease acquisition, A5 ingress, bounded per-event FINAL-only UI context reads, revocation and explicit close. Ingress writes only a content-free metadata summary as an A5_UI_EVENT source, persists a PerceptPacket, calls the existing A4 attention scorer, and uses the existing source-bound admission budget. PROVISIONAL observations remain persisted as provisional evidence but are not admitted or allowed to file A4 high-resolution requests. Core must instantiate the adapter in the active-turn path and call adapter.close() before Store shutdown; no automatic Runtime._turn or Runtime.close hook exists yet.
- This is a Perception adapter over the existing Runtime object, not an Android capture implementation. No authenticated OS receipt provider, AccessibilityService, NotificationListenerService, MediaProjection session, screenshot decoding, visual model, automatic _turn queue hookup, B1/B2/C3 context delivery or Android device test exists yet. A5 UI remains SHADOW / REDMI_UNVERIFIED.

### Local test evidence and limits

- LOCAL_LINUX / CPython 3.13.5: python -m py_compile PASS for the isolated bridge; 14/14 isolated tests PASS using a synthetic SQLite Store and fake A4/provider. Covered Runtime-like ingress, A4/admission, provisional exclusion, source/generation/receipt/thread binding, non-reentrant revocation serialization, tombstone/cache/blob cleanup, raw-field rejection, API 33 vs 34 projection scope, accessibility-purpose gating and NotificationListener API floor.
- The repository-level unittest is added separately and must be checked by exact-head GitHub CI. The isolated harness does not import the full Aii Runtime/Store, does not use Android APIs and is not a native-device proof.
- No model/weight, installed permission, microphone/screen-capture setting, updater, user data or device state was changed.

**Status:** OFFICIAL_ANDROID_API_DOCS_REVIEWED / A5_UI_LEASE_AND_RUNTIME_INGRESS_IMPLEMENTED / LOCAL_LINUX_ISOLATED_13_OF_13 / FULL_REPOSITORY_CI_PENDING / OS_CAPTURE_PROVIDER_NOT_IMPLEMENTED / REDMI_UNVERIFIED.


## R-039 — MobileVLM V2 as an on-demand A5 visual teacher candidate (2026-11-21)

### Primary paper reviewed

- Xiangxiang Chu et al., **MobileVLM V2: Faster and Stronger Baseline for Vision Language Model**, arXiv:2402.03766v1, submitted 2024-02-06 (preprint; no peer-reviewed venue established by the source reviewed): https://arxiv.org/abs/2402.03766 and full HTML https://arxiv.org/html/2402.03766v1.
- Main method/experiment sections reviewed: CLIP ViT-L/14 at 336×336, MobileLLaMA-1.4B-Chat, LDPv2 projector, 576→144 visual-token reduction, 1.7B configuration, multi-task data and the mobile latency table. The model freezes the vision encoder but trains the projector and LLM; the paper's training used 8×A100 GPUs, not on-device learning.
- Reported result: 64.2 average over six VLM benchmarks for MobileVLM V2 1.7B. The paper reports 51.63 generated tokens/s and 4.96 s total for 256 output tokens on NVIDIA Jetson Orin with a 4-bit LLM and llama.cpp. This is an Orin result, not Android/Redmi evidence.

### Maintained OSS and Android implementation evidence

- Official model/code repository: https://github.com/Meituan-AutoML/MobileVLM, README blob 8531f3b890850f904c90fe3a6857763933fc945f, LICENSE blob 261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64. Repository code is Apache-2.0. Its current main HEAD 688fdec914810485c8766da96c63d9d2ce15f750 dates to 2024-04-15, so the model repository itself is not actively maintained in the current cadence; the llama.cpp integration is the actively updated runtime path. The README explicitly says datasets and checkpoints remain subject to their original licenses.
- Current llama.cpp MobileVLM documentation: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal/MobileVLM.md, blob 6c17dbf902eafc6d262d6faa846ff5999fd6d8ab. It explicitly supports MobileVLM_V2-1.7B, uses the mtmd CLI, requires projector type ldpv2 for V2, and includes an Android aarch64 build path under tools/mtmd/android/build_64.sh.
- The llama.cpp document includes a Snapdragon 778G Android run for MobileVLM_V2-1.7B using the release-2005b build, 4 CPU threads and the F16 mmproj: CLIP image encoding 20.61 s, prompt evaluation 21.12 tok/s, output generation 12.83 tok/s, total 44.41 s for a 377-token response. This is the strongest directly relevant Android evidence found, but it is Snapdragon 778G, not the user's Snapdragon 732G / Redmi Note 10 Pro. It is not transferable as a Redmi benchmark.
- A separate current-version V1 example in the same document reports a severe regression (0.30 tok/s and 865 s total) compared with an older release. That is a different V1 run, not a V2 result, but it demonstrates that the exact llama.cpp revision and model/projector pairing must be pinned and remeasured.
- A community GGUF conversion, https://huggingface.co/cyzero-kim/MobileVLM_V2-1.7B-GGUF, is labeled Apache-2.0 and at verified revision bb2cbd1. Its listed files are 792 MB for the Q4_K LLM, 595 MB for F16 mmproj, and 169 MB for Q4_K mmproj. The Q4 pair is about 961 MB on disk; this is a storage figure, not RAM usage. The conversion is third-party, not the official Meituan release; verify hashes and model/projector compatibility before use.
- Model cards label MobileVLM_V2-1.7B and MobileLLaMA-1.4B-Chat Apache-2.0. The CLIP ViT-L/14-336 Hugging Face model card does not state a license or training-data provenance; do not infer a weight license from the upstream code license. The MobileLLaMA card lists Aeala/ShareGPT_Vicuna_unfiltered as its SFT dataset but does not resolve that dataset's terms. More importantly, the MobileVLM V2 paper uses ShareGPT4V-PT, whose dataset card is CC-BY-NC-4.0 (https://huggingface.co/datasets/Lin-Chen/ShareGPT4V); this conflicts with treating the complete trained artifact as unconditionally Apache-2.0 for commercial redistribution. The model card/license label does not resolve the upstream training-data terms. Keep this candidate out of redistributed/commercial builds until dataset/checkpoint provenance is legally reviewed.

### V14 fit and limits

- Best role: optional on-demand A5 visual teacher after an A5 event/A4 salience request, not an always-on perception loop and not a B1/B2 body. It can describe image content, but the reviewed model card/paper does not establish coordinate-grounded Android tap targets, UI-tree semantics, reliable action grounding, or safe control.
- The 778G reference suggests image encoding alone can take about 20.6 s with the documented F16 projector; the 732G Redmi may be slower. It therefore belongs behind A4's slow/high-resolution request path if later approved, with small output budgets and explicit timeout/cancel.
- No RAM/PSS, thermal, battery, TTFT-on-Redmi or Android 13 measurement was found. The 961 MB Q4 file-pair size does not predict runtime memory. The F16 and Q4 projector variants need a quality/latency comparison on the actual target.
- No model download, conversion, build, swap, or device permission was attempted. No weights were loaded.

**Status:** PAPER_MAIN_SECTIONS_REVIEWED / OFFICIAL_CODE_APACHE_2 / LLAMA_CPP_ANDROID_PATH_DOCUMENTED / SNAPDRAGON_778G_REFERENCE_ONLY / DATASET_LICENSE_REVIEW_REQUIRED / REDMI_UNVERIFIED / NO_MODEL_CHANGE.

## R-040 — Replay can provably increase forgetting (2026-11-21)

### Primary research and scope

- **Mahdaviyeh et al., “Replay can provably increase forgetting,” PMLR 330:15–42 (CoLLAs 2026).** Official proceedings: https://proceedings.mlr.press/v330/mahdaviyeh26a.html . Full arXiv HTML reviewed: https://arxiv.org/html/2506.04377v1 . The arXiv version identifies its license as **CC BY-NC-ND 4.0**; cite and summarize only, do not copy/adapt its figures or text.
- The result is conditional, not “replay is bad.” In over-parameterized continual linear regression, the worst-case construction shows replay can move error from one old sample onto another, changing forgetting from O(1/T) to Θ(1). The average-case result shows random replay can increase expected forgetting for some task-subspace relationships. MLP / Rotated-MNIST / Split-MNIST experiments are non-monotonic and sample-, class- and task-dependent; some settings benefit only after a larger replay count. The paper also gives sufficient benign conditions in its studied setting. It is not an LLM/JEPA result and does not establish a universal anti-replay theorem.
- **V14 consequence:** replay volume is not a safety or retention guarantee. Preserve source/session-disjoint holdouts and compare zero replay, uniform replay, session-contiguous replay and loss-selected replay across multiple seeds. Report each old session separately and keep exact checkpoint rollback. Do not relax the per-session gate to make an update pass.

### Testable adaptation

- Keep the existing source-disjoint per-session acceptance gate.
- Add matched zero/uniform/session-contiguous/loss-selected controls and multi-seed results; separate new-task utility from old-session retention.
- A replay policy that improves the aggregate while regressing any protected old session remains rejected.

- **Status:** FULL_ARXIV_HTML_REVIEWED / PMLR_RECORD_VERIFIED / CONDITIONAL_RESULT / NO_CODE_IMPORTED / NO_ANDROID_PROOF.

## R-041 — Replay on Demand: an emergent curriculum for continued pretraining (2026-11-21)

### Primary research and method

- **Thede et al., “Replay on Demand: An Emergent Curriculum for Balancing Adaptation and Forgetting in Continued Pretraining,” arXiv:2609.40089 (2026).** Official preprint: https://arxiv.org/abs/2609.40089 ; full 31-page text reviewed: https://pdfs.assets.alphaxiv.org/2609.40089v1.pdf .
- RoD scores adaptation examples by current language-model loss minus an adaptation-specialist reference loss, and replay examples by current loss minus the pretrained model's reference loss. It jointly top-k selects from both streams under one budget. Reference losses are precomputed and content-hash keyed. Each step scores m×k candidates with a forward-only pass (m=2 in the paper), then trains on k. The specialist reference requires an offline no-replay continued-pretraining run unless already available; a smaller source/reference model can transfer a curriculum to a larger target.
- **Limitations:** only forgetting represented in the replay pool is visible; LM loss is not downstream capability; proxy replay can fit the proxy distribution rather than restore the pretrained function; each experimental condition is a single-seed run (seed 42), despite replication across model families/scales/domains. Main experiments use distributed NVIDIA B200 GPUs with GPU count varying by model and setting; this is not a mobile recipe.
- **OSS:** https://github.com/bethgelab/replay-on-demand at exact main SHA `9ecc05173a4a5a8b872e18608c319df0eab5db81`; repository LICENSE is Apache-2.0. The public implementation uses NVIDIA NeMo-RL v0.6.0 / Megatron / Ray / SLURM and an NGC container; it is not a Redmi dependency candidate. No code or dependency was imported.
- **V14 consequence:** only the small principle of demand-sensitive replay is a possible future local experiment, after strict per-session retention is stable. Do not port the second reference-model scoring loop or GPU stack to Android. Use bounded candidate pools, stored per-cohort loss baselines, zero/uniform/session-contiguous controls, multiple seeds, exact parameter diff, restart and rollback.

- **Status:** FULL_TEXT_REVIEWED / OSS_APACHE2_REVISION_CHECKED / SINGLE_SEED_AND_EXTRA_FORWARD_PASS_LIMITATIONS_RECORDED / NO_CODE_IMPORTED / NO_ANDROID_PROOF.

## R-042 — SmolVLM-256M as a low-storage, on-demand A5 visual teacher candidate (2026-11-21)

### Primary paper reviewed

- Andrés Marafioti et al., **SmolVLM: Redefining small and efficient multimodal models**, arXiv:2504.05299v1, submitted 2025-04-07; preprint, not peer-reviewed evidence. Full HTML sections 1–4.5 reviewed: https://arxiv.org/html/2504.05299v1.
- SmolVLM-256M combines a 93M SigLIP-B/16 vision encoder with a SmolLM2-135M language backbone. The paper reports 0.8 GB GPU VRAM at batch 1, 44.0 average across its listed image/video benchmark suite, OCRBench 52.6%, TextVQA 50.2%, DocVQA 58.3%. The 500M variant raises those scores to 61.0%, 60.2%, and 70.5%, at 1.2 GB GPU VRAM. These are the paper's evaluation settings, not Redmi measurements.
- The paper's on-device/edge section benchmarks throughput on NVIDIA A100 and L4 GPUs (e.g. 256M reaches 2.7 examples/s at batch 8 on L4); the smartphone demo is not a Snapdragon 732G benchmark. It explicitly notes that visual compression can hurt fine-grained OCR/localization and that smaller models struggle beyond 8k context.

### Model, GGUF and runtime provenance

- Original checkpoint: https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct, current model revision `d039ab0d4b9311b617e8ffec1d06c8464364aeb3` (last modified 2026-11-13); model card labels Apache-2.0 and identifies base models HuggingFaceTB/SmolLM2-135M-Instruct and google/siglip-base-patch16-512. Both base model cards also label Apache-2.0. No original checkpoint was downloaded.
- llama.cpp conversion: https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF, revision `b9e4379657e1450d04d02eec8e345667265b0a00`, model card labels Apache-2.0. Q8 files: language model 175 MB + mmproj 104 MB = 279 MB on disk. F16 files: 328 MB + 190 MB = 518 MB on disk. These are storage sizes, not peak RSS/PSS or total runtime memory.
- Official llama.cpp multimodal docs use `libmtmd`, list SmolVLM-256M/500M GGUF models, and describe image/audio/video input: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md. The Android guide documents building/running llama.cpp CLI from Termux: https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md. The combination suggests a testable Android path but does not prove this exact model/projector builds or runs on Redmi; that combined path remains UNVERIFIED.
- The SmolVLM model card lists The Cauldron and Docmatix training datasets. Their full dataset-license/provenance terms were not audited in this pass; do not infer every training-source term from the checkpoint's Apache-2.0 card label.

### V14 fit and caveats

- Candidate role: A4-triggered, on-demand visual teacher for A5 screen/image input, not an always-on loop, B1/B2 replacement, action executor, or native B3 latent body.
- At 279 MB Q8 on disk and a paper-reported 0.8 GB GPU memory at batch 1, the 256M model is a plausible low-storage experiment for the 6-GB-class device, but current B1/B2 residency, CPU-only execution, image tiling, allocator peaks, thermal throttling and Redmi memory pressure are unknown.
- OCRBench 52.6 and TextVQA 50.2 indicate useful but limited recognition; the 500M model is materially stronger but uses more memory. Neither model card nor paper establishes reliable Android UI element coordinates, tap-target grounding, or safe action selection. Use structured app/API events where available; visual output may inform perception but must not itself authorize actions.
- The paper evaluates images at longest edge 1920 for the 256M/500M models. High-resolution tiling can increase work; downscaling may erase small UI text. A4 should request bounded crops only when needed and preserve source/time/consent provenance.

### Test plan and permission boundary

- Before any download, obtain explicit user consent for a separate experimental model download. Do not change installed models or the production selector.
- On the actual Redmi/Termux environment, compare 256M Q8 and 500M Q8 only if approved; first verify the exact llama.cpp revision and that its Android build includes libmtmd and the matching mmproj loader.
- Measure model+mmproj disk size/checksums, load RSS/PSS, peak memory during a 512/1024/1920-longest-edge image, TTFT, output tokens/s, thermal/battery, and OCR/UI-task quality. Use only synthetic or explicitly consented local screen fixtures; no private app screenshots in public logs.
- Negative controls: no-image, blurred text, shuffled screen/crop, stale capture receipt, and text-only API event. Acceptance requires source-bound visual evidence and human/permission-gated actions; no direct tap authority from VLM output.
- Compare against MobileVLM V2 only after the same-device measurement; its 1.7B Q4 model+projector is about 961 MB on disk and its published Android reference is Snapdragon 778G, not the Redmi 732G.

**Status:** PAPER_FULLTEXT_REVIEWED / MODEL_CARD_AND_BASE_LICENSES_REVIEWED / GGUF_REVISION_AND_FILE_SIZES_VERIFIED / LLAMA_CPP_ANDROID_PATH_DOCUMENTED_NOT_RUN / CANDIDATE_ONLY / NO_DOWNLOAD / NO_MODEL_CHANGE / REDMI_UNVERIFIED.


## R-043 — A5 UI Runtime context readout source binding and lease regression (2026-11-21)

### Exact-head failure reviewed

- PR #2246 code head `ad0d6a3b1f4935b22677c6f9c521ec97e099deec`, GitHub Actions run `44940487917`, failed the same three tests on CPython 3.13.18 and 3.14.10: 12 passed, 3 failed, 5 subtests passed in each job. `py_compile` passed on both versions; staged Runtime passed; integrated regression was still in progress at review time.
- Root cause 1 (real adapter defect): `PerceptPacket` in `v13/code/v13/contracts.py` stores its source identity in nested `source_ref.source_id`; it has no top-level `source_id`. `A5UIRuntimeAdapter.context()` filtered on `packet.get("source_id")`, so every valid cached packet was silently excluded.
- Root cause 2 (test defect): the different-generation test used `grant` without binding it in the context manager.
- Root cause 3 (test/API mismatch): two tests called `context()` without the required lease argument, contradicting the method's fail-closed contract. The API must not become permissive merely to satisfy those tests.

### Corrective change

- Context readout now resolves `source_ref.source_id`, checks the current `event_id` and `brain_generation_id`, and still requires the live thread-bound lease(s), FINAL state and UI modality.
- Regressions now bind the lease variable correctly, test source-ref and generation spoofing as negative controls, assert provisional packets remain unavailable even with a valid lease, and assert lease-free reads raise `PermissionError`.
- No Android provider, capture, screenshot, AccessibilityService, MediaProjection, notification reader, action executor or B1/B2/C3 turn hookup was added. This remains a synthetic-provider adapter path.

### Verification boundary

- Exact failing CI evidence is reproducible from run `44940487917` on Python 3.13/3.14. Corrective code-bearing SHA `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723` passed the A5 lease workflow on both Python versions (15 tests + 5 subtests each); staged/integrated regression also passed in run `44941328011`.
- This worker has no mounted full Aii checkout and GitHub DNS resolution fails, so the full repository test cannot be run locally here. Any standalone logic check is synthetic and is not a substitute.
- `REDMI_UNVERIFIED` / `NOT_RELEASED`; no model, weight, permission, updater, app or user data changed.

### Next integration

Core must provide an authenticated Android observe_ui receipt provider and retain the lease through the actual active turn and all downstream reads/generation. QA must verify provider revoke-request cancellation and post-lock cleanup through the complete consumer chain. Research/Perception owns this adapter contract and will only add real screen features after that provider exists.


### Second exact-head run and remaining test corrections

- The next exact run (`44941137655`) reached the corrected context reader: 13 tests passed and 2 failed on both Python 3.13.18 and 3.14.10; `py_compile` passed. The source-bound readout no longer returned an empty tuple.
- Remaining failures were test assertions/setup, not a new adapter exception: one assertion still expected a nonexistent top-level packet `source_id` instead of `source_ref.source_id`; the different-generation revocation test never called `ingest`, so there was no persisted source row to tombstone.
- The test now checks the nested SourceRef and persists the observation before changing the active generation. These preserve the original contract: revocation must not cancel a different generation, but it must tombstone the already-persisted source.
- Final exact-head A5 lease CI is PASS on Python 3.13 and 3.14 (15 tests + 5 subtests each); privacy scan is PASS. Staged/integrated regression remained IN_PROGRESS at final readback. The strict additive-candidate validator is FAIL_BY_POLICY because this PR modifies an existing bridge plus shared V14 research/handoff files; no bypass is requested. Do not merge or release until Boss review and the remaining integration checks complete.


### Final code-bearing SHA and CI readback

- Code-bearing SHA: `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723`. PR #2246 is retargeted directly to the current release-development branch and includes the merged #2243 base.
- A5 lease workflow run `44941324466` (push) and `44941328040` (pull_request): **PASS** on CPython 3.13.18 and 3.14.10; `py_compile` PASS; `15 passed, 5 subtests passed` on each interpreter; public privacy scan PASS.
- `v13-private-remote-bridge-tests` run `44941324373`: PASS. Perception public privacy scan run `44941327893`: PASS. Agent-PR integration policy run `44941327955`: PASS.
- `V13 safe additive candidate tests` run `44941327931`: **FAIL_BY_POLICY**, not a functional test failure. The validator accepts only strictly added inert modules/tests/handoff files; this PR intentionally modifies an existing A5 bridge and the shared V14 research ledger/handoff. No bypass was attempted; independent Boss review is required.
- `V13 staged context and integrated regression` run `44941328011`: **PASS** — staged-runtime `251 passed, 10 skipped, 47 subtests`; integrated-regression `424 passed, 3 skipped, 58 subtests` (6 warnings). These are CI synthetic/staged checks, not local Redmi evidence.
- Local standalone nested-source/event/generation/finality/modality filter check: **4/4 PASS**. Full repository LOCAL_LINUX test remains BLOCKED because the complete checkout is not mounted and GitHub DNS resolution fails in this worker.
- Device and release: `REDMI_UNVERIFIED` / `NOT_RELEASED`. The adapter uses a synthetic OS provider; no phone, capture, microphone, model or permission was exercised.


## R-044 — Lightweight visual UI grounding candidates and Android capture boundary (2026-11-21)

### GoClick — primary record and maintained OSS

- **Paper:** Hongxin Li, Yuntao Chen, Zhaoxiang Zhang, “GoClick: Lightweight Element Grounding Model for Autonomous GUI Interaction,” arXiv:2604.23941, submitted 2026-04-27. Only the arXiv abstract/metadata was accessible in this review; **full paper not read**, and peer review status not verified. The abstract claims a 230M-parameter encoder-decoder grounding model and a 3.8M curated core set refined from 10.8M examples. Do not treat its reported accuracy as a Redmi result.
- **Code:** https://github.com/ZJULiHongxin/GoClick, repository declares MIT. README describes a two-stage plan→function-description→grounding architecture, Florence-2 based; requires Transformers 4.45.0, timm and PyTorch 2+, with CUDA recommended. Its benchmark scripts use external planners (for example GPT-4o) and GPU-oriented evaluation; not a standalone on-device Android agent.
- **Weights:** https://huggingface.co/HongxinLi/GoClick-Base declares MIT, 0.3B parameters, F32 Safetensors, based on microsoft/Florence-2-large, and uses `trust_remote_code=True`. No GGUF/llama.cpp/ARM64 path, quantized file or Android measurement was verified. Training recipe uses multi-GPU `torchrun`; no mobile training claim. Dataset provenance/license was not audited. **Not a current Redmi candidate**; only a possible future grounding teacher after a real ARM/quantization path and explicit opt-in.

### MobileExplorer — architecture idea, not a verified dependency

- **Paper:** Runxi Huang et al., “MobileExplorer: Accelerating On-Device Inference for Mobile GUI Agents via Online Exploration,” arXiv:2605.26546, submitted 2026-05-26. Abstract only reviewed; full text, implementation, license and exact device matrix were not verified.
- Abstract reports lightweight parallel UI-element exploration during VLM reasoning, structured traces, and two-level rollback; claims 23% fewer reasoning steps / end-to-end latency and up to 5% success improvement on its AndroidWorld + custom tasks. Conditions are not independently checked here. Treat as a **research hypothesis**, not a measured V13 optimization.
- Testable V14 adaptation: while the planner reasons, perform only bounded, read-only, consented element exploration; store source/generation/session-bound candidate traces; require verified state restoration and a stop switch; compare no-exploration, shuffled traces and failed-rollback controls. Do not execute taps or mutate UI during speculative exploration.

### Android platform boundary

- Official Android foreground-service documentation: https://developer.android.com/develop/background-work/services/fgs/service-types. MediaProjection requires calling `createScreenCaptureIntent()` and obtaining the user's grant before `getMediaProjection()`; Android 14+ additionally requires the `mediaProjection` foreground-service type and permission, and Android 15 disallows starting that FGS from `BOOT_COMPLETED`. This reinforces an explicit, user-visible capture session; no covert boot-time screen capture.
- For the Redmi's Android 13, do not import API-34+ manifest rules as if they were already required on that device. The user-granted capture intent remains the key authorization boundary. Verify exact target SDK and device behavior on hardware before claiming support.

### Decision / next experiment

- Keep the metadata-only A5 UI lease as a provider-independent contract; do not couple it to a specific VLM.
- Prefer Android API/accessibility event metadata when available and explicitly granted; use MediaProjection only with the platform grant and an active visible session. A visual grounding model may rank/locate elements but must never itself authorize a tap.
- No GoClick/MobileExplorer model or dataset was downloaded, imported, or swapped. No Android permission was requested. ARM64 build, memory/PSS, TTFT and Redmi grounding quality remain NOT_TESTED.
- Status: PAPER_ABSTRACT_ONLY / OSS_README_AND_LICENSE_REVIEWED / MODEL_CARD_REVIEWED / NO_IMPORT / NO_DOWNLOAD / NO_ANDROID_PROOF.


### Final broader CI completion — 2026-11-21

- Run `44941328011` completed successfully on the same code-bearing SHA `01ce1c5fc9c8d2c1dc3f41718e3b6508d7b9d723`.
- Staged Runtime: `251 passed, 10 skipped, 47 subtests`.
- Integrated regression: `424 passed, 3 skipped, 58 subtests` (6 warnings).
- These are CI staged/synthetic tests. They do not establish Android OS capture, a real UI provider, active-turn consumer wiring or Redmi behavior.


## R-047 — Optional NumPy acceleration for RAW_EAR autocorrelation (2026-11-21)

### Hypothesis and implementation

- The existing RAW_EAR extractor in `v13/code/v13/audio_voice_cues.py` spends most of its pure-Python time in the per-lag normalized-autocorrelation loop. Replacing only that calculation with `numpy.correlate` should preserve the current frame segmentation, activity classes, F0/prosody outputs and schema while reducing CPU cost.
- PR #2256 adds an explicit `backend="numpy"` option to `extract_voice_cues` and `voice_backend="numpy"` to the actual `consume_pcm16_voice_window` A5→A4→C3 consumer. Default remains `python`; NumPy is imported lazily only when explicitly selected. No new mandatory runtime dependency and no automatic backend swap.
- The hybrid implementation vectorizes only pitch autocorrelation; it deliberately leaves the rest of the Python extractor unchanged to minimize semantic drift. A more aggressive fully vectorized prototype was faster but is not the chosen implementation.

### Local evidence

- LOCAL_LINUX Python 3.13.5 x86_64, NumPy already loaded: one-second 16-kHz window median 131.30 ms / p95 135.89 ms for pure Python versus 6.23 ms / p95 8.37 ms for the hybrid NumPy backend (~21× median speedup).
- Exact output parity across 100 deterministic random synthetic PCM windows at 8/12/16/32/44.1/48 kHz and durations 40 ms–1 s; seven additional silence/tone/noise/impulse/voice-like controls also matched exactly.
- tracemalloc peak: 922,767 bytes for Python and 934,805 bytes for the hybrid NumPy path (+12,038 bytes while NumPy was already imported). Process RSS and cold NumPy import cost were not measured.
- A full vectorized prototype measured ~2.19 ms per one-second window, but duplicates more of the extraction pipeline; it remains an experiment, not the implementation.
- CI matrix for PR #2256 is pending. No full local Aii checkout test or Redmi/ARM measurement is claimed.

### Constraints and next acceptance

- The backend is opt-in and the Runtime default remains Python. Core may pass `voice_backend="numpy"` only in an explicitly experimental path after the actual device confirms cold import cost, RSS, 40–100-ms incremental latency, full-duplex interruption behavior and output retention.
- Synthetic PCM is not a speech corpus. The benchmark establishes algorithm parity and CPU cost only; it does not establish real speech accuracy, VAD calibration or human-prosody validity.
- Keep WebRTC/Silero VAD evidence separate from RAW_EAR pitch/prosody and non-speech classes. No model weights, speech dataset, microphone access or Android permission was downloaded or enabled.
- Official Termux packaging was checked directly at `termux/termux-packages/packages/python-numpy/build.sh` (blob `36b2c798600562acea3250ae2c3f8e9014610d2a`): current recipe pins NumPy 2.5.5, declares BSD-3-Clause, and builds Android wheels including the `aarch64 → arm64_v8a` path; declared runtime dependencies are `libc++`, `libopenblas`, and `python`. This establishes a maintained Android/Termux packaging route, not that NumPy is installed on this Redmi or that cold import/RSS is affordable. No package was installed.
- Exact PR #2256 code head `176a6cff` initially passed `py_compile` and all 42 tests on CPython 3.13/3.14, but its benchmark step failed on both because direct script execution did not include `v13/code` on `sys.path`. Fixed in `63b5410769b872ddb64e002ab1c764e9e90966af` by adding the script-relative code root. Exact workflow `44946779051` passes both Python 3.13 and 3.14, including benchmark and privacy scan. Exact staged/integrated workflow `44946779195` also passes: staged-runtime 251 passed / 10 skipped / 47 subtests; integrated regression 424 passed / 3 skipped / 58 subtests. Safe-additive validation still fails by policy because this PR modifies an existing production module; no bypass or allowlist weakening was attempted.

**Historical status on head 63b5410:** OPT_IN_CODE_IMPLEMENTED / SYNTHETIC_PARITY_100_OF_100 / LOCAL_X86_CPU_MEASURED / EXACT_FOCUSED_CI_PASS_3_13_3_14 / STAGED_RUNTIME_AND_INTEGRATED_CI_PASS_44946779195 / REDMI_UNVERIFIED.



## R-048 — Tandem: hybrid recurrent-state reuse on mobile NPUs (2026-11-21)

### Source and review depth

- Primary paper: Zhuomin Chen et al., *Tandem: Serving Hybrid Linear-Attention GUI Agents on Mobile NPUs*, arXiv:2610.26660v1, submitted 2026-10-19. Full HTML paper read, including Sections 3–6, evaluation tables and discussion; it is a preprint, not a peer-reviewed result in the source reviewed here.
- Maintained implementation inspected: `flyingdoog/tandem`, a fork of `ggml-org/llama.cpp` b11200. Repository LICENSE is MIT (blob `e7dca554bcb802f98408383a864404e3aa4eacca`). The fork adds roughly 3,000 C/C++ lines across 24 files and builds with Android NDK r28b + Hexagon SDK 6.6. A separate dependency/SDK license and provenance audit would be required before reuse; no code was imported.

### Method and measured results

- Tandem checkpoints hybrid recurrent state at observed prompt-divergence points rather than generic chat message boundaries; for speculation it retains only a short rollback tail so the bulk of prefill remains on the NPU matrix path; it shares weight-block reads across candidate verification; it releases NPU active-power votes after 3 s idle while keeping model weights/state resident.
- Primary device: OnePlus 13T, Snapdragon 8 Elite / Hexagon v79, Android 16, 16 GB RAM; model Qwen3.5-4B Q4_K_M. Second device: OnePlus 15, Snapdragon 8 Elite Gen 5 / Hexagon v81, Android 16, 16 GB. Measurements include a 61-request replay trace, 21-screen app set, 510 held-out steps, 300 AndroidControl steps and 100 real phone tasks.
- On the primary device, text-step latency fell 1.96 s → 1.38 s (30%) and screenshot-step latency 5.66 s → 4.76 s (16%) against the fastest llama.cpp NPU configuration. Energy per text step fell 15.1 J → 10.1 J (33%); screen-off standby with the model loaded fell 0.76 W → 0.22 W. On the next NPU generation text-step latency fell 27%.
- On 510 held-out steps, action fidelity was 265/510 correct text steps and 287 vs 288 correct screenshot steps (Tandem vs llama.cpp); the paper reports identical action outputs for the 100 real-task runs, while some free-text summaries can differ due to floating-point rounding. These are step-level results, not a general task-success guarantee.
- Other recurrent architectures: the checkpoint policy alone reduces new prompt tokens by 11–12% and latency by 9–12% on LFM2-2.6B and Granite-4.0-H-Micro on the same Snapdragon NPU; with all Tandem kernels LFM2 is 16% faster than llama.cpp. This does not establish results for V13's installed LFM2.5-1.2B model or CPU/GPU backend.

### V14 interpretation / fit

- Strong transferable hypothesis: an agent's stable Context OS header/task prefix and changing recent event/screen tail create a different cache boundary from ordinary chat. If the current model/backend exposes safe recurrent-state save/restore, measure a divergence-point checkpoint against the existing prompt-cache path; verify exact output, state restore, memory overhead and restart/eviction behavior.
- NPU-specific parts (Hexagon HMX/HVX kernels, power votes, NDK/SDK integration and Qwen3.5 MTP head) are not directly portable to the Redmi Note 10 Pro target and must not be presented as a ready alternative. The paper's devices have Snapdragon 8 Elite/Gen 5 and 16 GB RAM; no Redmi-class evidence.
- Do not import the fork wholesale: it is a large llama.cpp fork tied to a specific NPU path and older base b11200. A small server-side checkpoint policy experiment may be more tractable only after inspecting the exact current llama.cpp recurrent-state API and V13's actual model architecture.

**Status:** FULL_TEXT_PREPRINT_REVIEWED / OSS_README_AND_MIT_LICENSE_CHECKED / NPU_HARDWARE_SPECIFIC / NO_CODE_IMPORTED / NO_MODEL_OR_WEIGHT_CHANGE / NO_REDMI_PROOF / RESEARCH_HYPOTHESIS_ONLY.



## R-049 — LFM2.5 recurrent prompt-cache applicability and license (2026-11-21)

### Exact model family and license

- Official Liquid AI model cards identify LFM2.5-1.2B-Instruct as 16 layers (10 double-gated convolution blocks + 6 GQA blocks), 1.17B parameters; LFM2.5-230M as 14 layers (8 double-gated convolution blocks + 6 GQA blocks). The installed V13 quantized variants are not independently remeasured here; the model-card architecture is a family-level reference, not proof of exact local GGUF metadata.
- Both official Hugging Face cards declare `lfm1.0`, the LFM Open License v1.0. Liquid AI's license page says it is Apache-2.0-based but **not Apache-2.0**: commercial-use rights are limited to legal entities below the USD 10M annual-revenue threshold; qualified non-profits and research/non-commercial use are exempt; attribution is required and there is no copyleft. Treat this as a custom open-weight license and retain its exact text with any model provenance. No model was downloaded or swapped.

### V13 current runtime readback

- Current `gpt6/v13-private-remote-bridge-20261111` source readback: `v13/code/v13/runners.py` blob `96d91b8aa0d110a7dbcfd438fc8b3b7c504eed9a`; `config.py` blob `a4fa0e0eeb6c544035ebf8ec0b46f5ebe11151481`.
- `LlamaRunner` starts each model server with `-np 1`, configured `-t/-tb`, `-b/-ub`, `--cache-ram` and `--ctx-checkpoints`; current defaults are 128 MiB host prompt cache and 6 checkpoints per slot. Each generation sends `cache_prompt=true` and `id_slot=0`. `RunnerPool` retains one resident runner per role when its resource/fabric policy allows it. `bodies.py` pins C3_LANGUAGE and enables the body fabric when `body_residency_mb>0`; current config default is 1,800 MiB for resident bodies (B1/B2/C3), with RED/ORANGE pressure modes allowed to evict non-pinned bodies. These are BOOT values, not Redmi measurements. Thus the normal path uses an in-memory prompt cache/checkpoint path and single-sequence server slots; it does not add `--slot-save-path` or issue slot save/restore on every turn.
- Existing historical V13 note `v13/code/docs/NATIVE_CACHE.md` (2026-10-12; Linux cloud, 4-vCPU Xeon, llama.cpp b10964, not Redmi) measured warm prefix reuse for LFM2.5-1.2B and LFM2.5-350M and A→B→A host-cache reuse. It also found no cache path bit-identical to cold prefill; exact-output paths therefore kept full prefill. This historical bench is not a current model/runner or Android acceptance test.

### Upstream llama.cpp status and risk separation

- llama.cpp PR #26004, merge commit `033df86b69ec1a333eb241f0c16325a4d43dcff5`, merged 2026-10-08 and is present in current upstream `master`: server slot save/restore now persists the context-checkpoint appendix. This fixes the disk slot-restore gap reported in #25913. It matters for explicit save→restart→restore; it is separate from the in-memory per-turn cache used by V13's current runner.
- LFM2.5 co-batching report #29002 is not a confirmed state-corruption bug: a maintainer traced the early-EOG result to the reproducer's logits-row indexing after a sequence finished; after correcting the harness, F32 was byte-identical and remaining Q4_K_M differences were numerical. V13's `-np 1` also avoids multi-sequence co-batching in each model server. Do not disable a future multi-sequence path based only on the original report; require a corrected reproducer and output/logit comparison.

### Concrete next measurement (no device action issued)

- For the next owner-authorized Redmi diagnostic, capture per-role `cache_n`, `prompt_n`, prompt-eval time, TTFT, runner PID/restart, body-residency mode/live-process count, model revision and cache/checkpoint flags on (a) a repeated same-prefix turn, (b) a changed recent tail, (c) A→B→A role/session switching, and (d) after resource-driven runner eviction/reload. A large `cache_n` separates model decode/prefill speed from cache-miss problems; zero reuse despite an identical prefix points to prompt/template/session continuity or an older binary. Do not infer either from the existing 28.72-s C3 prefill report alone.
- Private owner-read issues Aiiii #431 and #432 and V13OBS #115 were checked: all still have zero comments/no new authenticated receipt. No new request was issued. No Termux command, model download, weight change, updater request or phone mutation.

**Status:** MODEL_ARCHITECTURE_AND_LICENSE_VERIFIED / RUNTIME_CACHE_FLAGS_READBACK / UPSTREAM_SLOT_CHECKPOINT_FIX_MERGED / CACHE_HIT_ON_REDMI_UNVERIFIED / NO_MODEL_CHANGE / NO_DEVICE_ACTION.


## R-050 — Cross-family latent cache transfer and native receiver ingress feasibility (2026-11-21)

### XKV — receiver-aware dual-cache communication

- **Paper:** Jiyao Liu, Qi Zhang, Yaoyi Jia, Ziwen Kan, Song Wang, “Dual-Cache Latent Space Communication between Heterogeneous Language Models,” arXiv:2608.20617, submitted 2026-08-20. Full arXiv text reviewed; this is an arXiv preprint, not a verified peer-reviewed publication. Primary source: https://arxiv.org/abs/2608.20617
- **Method:** both frozen models prefill complementary contexts. A learned-query pooler compresses both sender and receiver K/V caches; a learned layer-axis map and cross-layer attention form a compact receiver-aligned memory; each raw receiver cache position queries that memory and receives a per-head-gated K/V residual in native receiver geometry. Only the translator is trained; zero-initialized output heads make the initial update an identity.
- **Reported evidence:** 45 dataset/model-pair settings across five split-evidence QA datasets and the 3×3 ordered grid of Qwen-0.6B, Gemma-1B and Llama-3B. The six heterogeneous pairs vary family, depth, KV-head count, head dimension and tokenizer. The paper reports 4.55M translator parameters, 5.8 ms average translator latency and 167.6 ms average end-to-end latency; the comparison is 59.9/227.9 ms for LCF-X and 1,139.5 ms for text-to-text. XKV's macro score is 52.37 vs 49.76 for LCF-X and 48.86 for text communication. Hardware was one NVIDIA A100 80GB, Ubuntu 22.04, CUDA 12.2; each experiment was run once.
- **Limits:** translator-only latency is not total inference time; both models still prefill their own contexts. The paper itself lists larger-model scaling, multi-turn/many-agent communication and latent-message interpretation as future work. No Redmi/ARM64, Android, LFM2.5 or Qwen3.5 measurements. No official code repository or code license was located in this review; do not import an implementation or weights.
- **V14 implication:** this is the strongest reviewed design match for the eventual B1/B2 Callosum path because it makes communication receiver-aware and position-specific instead of broadcasting one sender summary. It is a research target, not proof that our current runtime can read or write native K/V tensors.

### HeteroFold — cross-tokenizer and cross-depth K/V transfer

- **Paper:** Vincent-Daniel Yun et al., “Prefill-Free Cross-Family KV Cache Transfer for Heterogeneous Multi-Agent LLMs,” arXiv:2609.32259, submitted 2026-09-26. Full paper reviewed. Primary source: https://arxiv.org/abs/2609.32259
- **Method:** shared character-boundary token alignment; proportional layer alignment with sender layers at offsets −4/0/+4; moment-matched Recolor affine K/V maps; receiver-attention/output-aware rank-16 correction; fold the correction into fixed per-layer K/V maps. Both base models remain frozen.
- **Reported evidence and limits:** six directed pairs among Llama-3.1-8B, Qwen3-4B and Ministral-3-14B in BF16. At 32K context, the paper reports 10.7× speedup over native prefill for Llama→Ministral, but results are not uniformly equal to text communication: some long-context scores remain substantially lower. The official repo README states about 50 GB for its three model weights and 0.5 GB of data, CUDA GPU requirements, and testing on A40/A100/H100/RTX 6000 Ada. This is not a mobile implementation.
- **OSS/license check:** official repo https://github.com/daniel-eai/Prefill-Free-Multi-Agent-LLMs at main SHA d8018c9a103094511fd58bb6572d1e4b038e071e. pyproject.toml declares MIT metadata, but the repository has no root LICENSE file at this readback; treat reuse as license-unverified until the actual license text is confirmed. Requirements pin PyTorch 2.9.1 and CUDA 12.8 wheels, Transformers 5.10.2 and other large Python dependencies. Llama-3.1 and Ministral weights are gated; each model's weight license is separate. No import, model download or weight swap was performed.
- **V14 implication:** reuse the algorithmic ideas only after legal review and a small compatible-model benchmark. HeteroFold's character alignment is useful where tokenizers differ; its BF16/CUDA stack and model scale are not a Redmi candidate.

### Native llama.cpp ingress: a concrete intermediate path, not K/V injection

- **Pinned upstream:** ggml-org/llama.cpp tag b10964 resolves to commit b29c606e28a01b1bc8c1351026a0fa6e616bf6c4; MIT license. Header: https://github.com/ggml-org/llama.cpp/blob/b10964/include/llama.h
- **Verified API facts from that exact header:** llama_batch has an embd pointer for raw input token embeddings when token IDs are NULL; the header exposes llama_model_n_embd_inp and llama_model_n_embd_out. It also exposes llama_state_seq_get_data / llama_state_seq_set_data for serializing/restoring one sequence in a context. That state API does not promise compatibility across different model architectures or revisions.
- **Verified server boundary:** the b10964 server registers /embedding, /embeddings and /v1/embeddings output routes. No raw input-embedding injection HTTP route was found in server.cpp. Therefore an HTTP-only LlamaRunner cannot inject projected activations into a receiver.
- **Current V13 nuance:** the normal LlamaRunner tap path can request per-token final embeddings through the embedding server mode; that is an output-state tap, not a K/V tensor tap and not a receiver injection path. It must not be described as native K/V coupling.
- **Actionable staged path:** Core can build a local-only libllama receiver wrapper that feeds a projected sender activation sequence through llama_batch.embd. The sender final-state width and receiver input width must be read from the actual loaded model metadata, not assumed equal. This is a soft-prefix/activation-ingress bridge, not XKV and not direct K/V-cache transfer. It requires a custom native receiver runner because the current HTTP server exposes output embeddings only. First prove same-model token-embedding parity, then zero/shuffle/dimension/revision negative controls, then a trained B1→B2 adapter with frozen bodies and held-out receiver utility. Keep the existing symbolic/text fallback and all production gates unchanged.
- **No claim:** no native input-embedding receiver was built or run in this pass; no K/V cache was extracted or injected; no trained cross-organ adapter exists; no model was downloaded; B3 remains symbolic/SHADOW in production and Redmi remains unverified.

### Concrete next experiment

1. Core: implement the pinned b10964 native receiver seam behind an OFF-by-default experimental gate; expose model revision, input/output dimensions, positions, dtype and sequence identity; reject non-finite vectors, dimension mismatch and revision mismatch.
2. Perception + JEPA: use actual B1/B2 activation pairs only after a permitted native runner exists; train only a small adapter, keep both base models frozen, and record gradient norm, adapter parameter diff, holdout utility, per-session retention, restart and rollback.
3. Compare exact text, symbolic, latent, zero, shuffled, reversed-position and OOD controls on the same questions. Report TTFT, prefill, RSS/PSS and adapter overhead separately.
4. Only after the activation ingress works should Core pursue native K/V tap/injection and an XKV-style receiver-position translator. Do not assume llama.cpp sequence-state serialization is a cross-model K/V API.


## R-051 — Plasticity of Growing and Elastic Neural Networks in Online Continual Learning (2026-11-21)

- **Paper:** Jeong Min Kong and Richard S. Sutton, arXiv:2608.01475, submitted 2026-08-02. Full paper reviewed; preprint status only, no peer-review record or maintained official code repository verified. Primary source: https://arxiv.org/abs/2608.01475
- **Experimental setup:** online permuted MNIST and FashionMNIST, 10,000 or 40,000 samples per task, SGD learning rate 0.001, one-sample-at-a-time updates. Dormancy is estimated from a random 5% task sample. The headline plots report within-task online training accuracy, not held-out old-task retention. The study compares fixed networks, staged growth with frozen old connections, adaptive growth (AGN) that keeps all connections trainable, and adaptive elastic networks (AEN) that prune estimated-dead units at task boundaries.
- **Result:** AGN maintains high online accuracy despite an increasing estimated dormant-unit fraction; AEN maintains high accuracy with near-zero estimated dormancy and a network size that plateaus. The staged/frozen variant loses accuracy. Two-layer variants show similar trends but can converge to larger connection counts.
- **Limits:** small supervised image-classification task streams; no language-model, multimodal, world-model, causal-memory or Android evaluation. AEN's 5% sample can misclassify active units as dead, and the reported online accuracy does not prove retained knowledge on prior held-out sessions. No measured V13 RSS/latency or parameter-retention evidence. No code/license reuse was verified.
- **V14 implication:** this supports testing structural plasticity in small trainable A4/attention/perception adapters, not freezing the existing organs and not growing the large B1/B2 bodies. First repair the current per-session JEPA retention gate. Then compare fixed, AGN and AEN heads with source-disjoint old-session holdouts, random-prune and no-growth controls, gradient/parameter diffs, restart/rollback, and bounded parameter/RSS/latency budgets. Keep learning gates OFF until those tests pass.


---

## Boss exact-state correction — 2026-11-21 23:26 CET

This correction supersedes older branch-level status claims without deleting the research evidence above.

### R-047 / current RAW EAR implementation

- Earlier head `63b5410769b872ddb64e002ab1c764e9e90966af` had the focused NumPy, prosody, consent, WebRTC and staged/integrated CI reported in R-047. The local 21× median CPU comparison was x86_64 with NumPy already loaded; it is not an ARM64 or cold-import measurement.
- Current PR #2256 head is `08fce3420ff2fc548276c421e99e79390d78e910`. Exact Python 3.13 and 3.14 jobs both fail two speaker-evidence tests: unvoiced-noise low similarity ends with `confidence_gate_passed=true`, and threshold-absent mode ends with `change_score=0.0` rather than 0.5. Source review identifies same-batch look-back contamination: frames appended earlier in the current batch become candidate references for later frames in that same batch, overwriting the cross-window score. Perception has been asked to freeze the pre-batch look-back snapshot for all comparisons and append only after scoring. No NumPy promotion is accepted until this exact head and the staged/integrated suite pass.
- Python remains the default; the optional backend remains OFF unless explicitly requested.

### R-050 / native receiver implementation state

- Exact pinned source readback: ggml-org/llama.cpp b10964 resolves to `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; `include/llama.h` blob `3ab935939c6d183e5862aba93f346691e658403b` exposes `llama_batch.embd`, `llama_model_n_embd_inp`, and `llama_model_n_embd_out`. The LICENSE blob at that revision is `e7dca554bcb802f98408383a864404e3aa4eacca` (MIT).
- Core PR #2266 head `3166858133844fc80201334f53ade450557d1191` now contains an explicit operator-only native input-embedding receiver probe. The owner reports six isolated wrapper tests, C++ core `-Wall -Wextra -Werror` compile/selftest and a stub-header adapter syntax compile PASS. Exact Python 3.13/3.14, real pinned llama.cpp Linux link/build and Android ARM64 cross-compile workflows are still queued. No real model execution, same-model parity, Android binary install or Redmi receipt exists. The path is diagnostic-only: `production_route=false`, `semantic_use_proven=false`, `training_authority=0`, `native_receiver_authority=0`.
- This is an input-embedding ingress experiment, not K/V extraction/injection, not XKV, not a trained cross-family adapter and not production B3.

### R-050 legal / hardware caveats rechecked

- XKV primary preprint: https://arxiv.org/abs/2608.20617. It reports 45 settings and a 5.8 ms average translator time; that number is translator-only on one A100 80GB setup, while both models still prefill. No official implementation/license was found in this review.
- HeteroFold primary preprint: https://arxiv.org/abs/2609.32259. The official repository's `pyproject.toml` declares MIT metadata, but fetching root `LICENSE` returns 404. Treat reuse as license-unverified until a license text is provided. Its README describes BF16 models totaling about 50 GB plus roughly 0.5 GB of data and a CUDA 12.8/PyTorch 2.9.1 stack; this is not a Redmi dependency candidate.
- These papers are design references, not proof of V13's native latent coupling. No model, dataset, code dependency or weight was downloaded or imported.

### R-051 / plasticity caveat

- Primary preprint: https://arxiv.org/abs/2608.01475. Its experiments are online supervised permuted-MNIST/FashionMNIST streams. The paper's headline accuracy is online training accuracy, not source-disjoint old-session holdout retention. No official code/license was verified.
- Use AGN/AEN only as a future small-head structural-plasticity comparison after JEPA per-session retention is stable. Keep base organs frozen only as a temporary experiment, not as the permanent architecture; measure actual gradient/parameter changes, old-session holdout, checkpoint/restart, rollback, RSS and latency. No such V14 experiment is accepted yet.

### Research branch integration state

- Research/Perception PR #2260 is CLOSED and was a DRAFT, not merged. Its research ledger and handoff content are being integrated into this Boss branch; its stale board/user-next-action snapshots were not copied.
- The current Boss branch is still DRAFT / NOT_RELEASED. All CI and device boundaries remain as recorded in the live workplan and Canon coverage index.


## Research update — 22/11/2026 04:55 CET (Boss & Integration)

### R-052 — MobileMoE: moderate-sparsity, fine-grained/shared experts for on-device bodies

- **Primary source:** [MobileMoE: Scaling On-Device Mixture of Experts, arXiv:2605.27358](https://arxiv.org/abs/2605.27358), submitted 26 May 2026.
- **Reported method/result:** the paper studies sub-billion active MoE bodies (0.3–0.9B active, 1.3–5.3B total), and argues for moderate sparsity with fine-grained and shared experts under mobile memory/compute constraints. It reports 1.8–3.8× faster prefill and 2.2–3.4× faster decode than its dense MobileLLM-Pro baseline at comparable INT4 weight memory, across its stated evaluation setup. These are paper results, not Redmi measurements.
- **V14 mapping:** useful architecture evidence for the long-term B1_DETAIL/B2_GIST sparse-MoE target. The transferable hypothesis is not “install this model”; it is that moderate sparsity plus fine-grained experts and a small shared-expert path may provide a useful mobile Pareto point. Preserve two different bodies: separate role-specific routers, temporal scales, expert allocation and objective functions; any shared experts must not collapse B1/B2 into identical chatbots. Measure active parameters, resident expert memory, expert cache churn, routing load balance, TTFT, PSS, output quality and detail/gist complementarity.
- **Limits / counterevidence:** the paper's arXiv page exposes no author-linked code or model-weight license in the checked view. Total parameters span 1.3–5.3B; total weight storage and runtime memory may exceed the target device budget even when active parameters are smaller. The abstract does not establish fit, ABI support or quality on the Redmi target.
- **Decision:** RESEARCH_ONLY / NO_DOWNLOAD / NO_MODEL_SWAP. Do not adopt a model until exact weight license, quantization, Android ABI, storage, peak memory, latency, quality and rollback are verified.

### R-053 — LARS activation-memory reduction and first-order phone-NPU LoRA

- **Primary sources:** [LARS / Activation-Efficient Fine-Tuning via Sequence-Compressed Low-Rank Subspaces, arXiv:2604.22783v2](https://arxiv.org/abs/2604.22783) (v2 dated 16 Oct 2026; accepted to AACL 2026); [First-Order LoRA Training with Phone NPUs, arXiv:2610.24816v2](https://arxiv.org/abs/2610.24816) (v2 dated 26 Oct 2026).
- **LARS finding:** it reduces retained adapter activation scaling from sequence-dependent O(BSRL) toward O(BRL) by pooling into a sequence-level low-rank subspace. The paper reports 23% GPU and 47.8% CPU overall memory reduction at sequence length 1024 versus LoRA, with larger relative savings at longer sequence lengths. It also reports lower CPU power/energy per optimizer step. This is a useful hypothesis where activation memory, rather than trainable parameter count, dominates.
- **LARS risk:** sequence pooling trades token-level granularity for memory. That can damage B1_DETAIL, temporal audio, exact source-span alignment or fine-grained JEPA prediction. It should be tested only on a small adapter/head or a deliberately pooled objective, not assumed suitable for the main bodies or raw temporal learner. No author-linked implementation/license was found in the checked arXiv page.
- **Phone-NPU LoRA finding:** the paper keeps the training graph, adapters and optimizer on CPU while an NPU computes the frozen-weight forward, checkpoint recomputation and input-gradient products from resident weight tiles. It adds gradient-sensitive precision, row range guards, checkpoint/resume, yield and thermal pacing. Its reported devices are Snapdragon 8 Elite / 8 Elite Gen 5 with Hexagon V79/V81; the paper does not demonstrate the V14 target device.
- **Reuse/license readback:** [QVAC Fabric tag v10549.5.1](https://github.com/tetherto/qvac-fabric-llm.cpp/tree/v10549.5.1) has an MIT LICENSE (LICENSE blob e7dca554bcb802f98408383a864404e3aa4eacca). Its training guide documents LoRA CPU/Vulkan paths, checkpoints and optimizer-state resume; the tag README says Vulkan LoRA training on Adreno 800+ for selected architectures, while other Adreno devices are listed for OpenCL inference. This does not establish Vulkan training on the target phone. [HexaTrain](https://github.com/yuubinnkyoku/HexaTrain) has an Apache-2.0 LICENSE (blob 58d9cf1e698014cd1d825eff230e16c1ef6eccb8); its current README baseline is a 758,528-parameter transformer on Snapdragon 8 Elite Gen 5 / Android 16 / QNN 2.48. It is a hardware-specific research reference, not a drop-in V14 dependency. The phone-NPU paper's own code was not linked in the checked primary arXiv page.
- **Testable V14 adaptation:** after the existing JEPA per-session retention gate is stable, compare a tiny CPU LoRA baseline against a sequence-pooled low-rank head on a small fixed dataset and context lengths. Record peak RSS/PSS, activation bytes by sequence length, optimizer/checkpoint bytes, wall time, CPU power if available, parameter delta, old-session holdout, restart and rollback. Keep the experiment isolated from production masters and do not download weights or activate an NPU path.
- **Decision:** RESEARCH_ONLY. QVAC/HexaTrain license metadata is recorded, but dependency graph, ABI, model architecture and device compatibility still require separate review. No code, dependency, model or weight was imported in this run.

### R-074 — Android AudioRecord default-rate mismatch in the signed RAW EAR consumer (2026-11-22)

**Primary sources reviewed:** Android Developers, AudioRecord API reference (accessed 2026-11-22), AudioFormat API reference (accessed 2026-11-22), and the Android guide on sharing audio input (accessed 2026-11-22). The API identifies 44,100 Hz as the only AudioRecord rate guaranteed to work on all devices; 22,050, 16,000 and 11,025 Hz may work on some devices. It requires checking getState() after construction. AudioFormat documents the client sample rate and platform conversion; the sharing guide requires registering AudioRecordingCallback before capture and describes silence, device-route, preprocessing and stream-format changes under concurrent capture.

**Repository evidence:** audio_capture_consumer.py previously hard-coded 16,000 Hz and capped Base64 at 44,000 characters, although audio_input.submit_audio_only, audio_ear.observe_pcm16 and audio_voice_cues.extract_voice_cues accept 8–48 kHz. A full one-second 44.1-kHz mono PCM16 window is 88,200 bytes and 117,600 Base64 characters. The old cap could not carry it.

**Change candidate:** default the signed one-shot request to 44,100 Hz; derive the encoded-length bound from the one-second byte limit; preserve exact request/receipt/sample geometry and never relabel or silently resample. Keep alternate rates out of the default until a device-specific capability test explicitly selects them. The provider must sign the client PCM format actually returned, and abort if the recording callback reports silencing or a route/preprocessing/format change.

**Tests required:** full 44.1-kHz signed request/receipt/PCM digest round-trip; over-limit payload rejection; replay, source, generation, consent, permission, finality and no-PCM-persistence negatives; staged Runtime consumer. Android AudioRecord/permission/route tests remain NOT_RUN until the companion provider exists. No new dependency, model or weight selected or downloaded.
### R-075 — FASTDIAR causal frame-level speaker embeddings (2026-11-22)

**Paper read in full:** Nikita Torgashov and Okan Köpüklü, *FASTDIAR: Frame-Level Speaker Encoder for Streaming Diarization*, arXiv:2610.02941v1, submitted 2026-10-02; five-page preprint submitted to ICASSP 2027, not yet treated as peer-reviewed. Full paper PDF: https://arxiv.org/pdf/2610.02941. Official implementation/checkpoints: https://github.com/microsoft/fastdiar (revision read from main at this review; repository LICENSE is MIT, Copyright Microsoft 2026).

**Method:** causal frame-level speaker encoder with a bounded 2-second past, one 192-D normalized embedding every 80 ms, and confidence-gated online clustering with a fixed 960-ms output delay. Training distils an utterance-level ReDimNet2-B6 teacher on simulated VoxCeleb2 mixtures and LibriHeavyMix, with MUSAN and simulated room responses. It does not train on a real diarization corpus.

**Reported evidence and conditions:** on an AMD Threadripper PRO 5995WX CPU, the 2.7M-parameter Small / 4.6M Medium / 10.4M Large variants report RTF 0.05 / 0.09 / 0.19 in the paper's model-scaling ablation; Large has a 960-ms fixed latency. Results are not uniform across benchmarks: with overlap included, FASTDIAR leads only VoxConverse and RAMC while Streaming Sortformer leads NOTSOFAR, DIHARD3, AMI and MSDWild; FASTDIAR is last on DIHARD3 under both overlap protocols. VoxConverse and NOTSOFAR development sets were used for checkpoint selection and threshold tuning. The paper does not separately ablate its confidence gate. The one-label-per-frame decoder counts overlapped regions as errors.

**OSS/runtime caveats:** official repo is MIT and publishes small/medium/large checkpoints, but its pinned stack includes PyTorch 2.13, torchaudio 2.11, torchcodec 0.15, NumPy, SciPy, Silero VAD and other packages; it is not a lightweight Termux dependency. README loads 16-kHz mono audio. The reported CPU is a high-end x86 Threadripper, not ARM/Redmi. Code license does not automatically clear all VoxCeleb2/LibriHeavyMix/MUSAN dataset or checkpoint redistribution terms; verify each before any product use.

**V14 adaptation hypothesis:** useful future A4 speaker-change/overlap evidence, not a speaker-identity authority. It is not a drop-in for the current one-second signed capture: the method needs a continuous 2-second state and 80-ms frame stream. A candidate must compare the existing deterministic RAW EAR heuristic, FASTDIAR Small, and NO_MODEL on the same source-bound streams, with confidence-gate ablation, overlap/noise/silence negatives, fixed-latency and retention checks. Keep identity/learning/action authority false. Because FASTDIAR expects 16-kHz input while the Android-guaranteed capture contract is 44.1 kHz, retain the original PCM for RAW EAR and evaluate a separate anti-aliased 44.1→16-kHz feature view; do not relabel samples or use the current block-average reduction as a speaker-model resampler.

**Decision:** RESEARCH_ONLY / NOT_SELECTED / NOT_DOWNLOADED. No model, dependency or weight was installed. ARM latency/RSS, quantization, accuracy on local conversational audio and data-license suitability remain unmeasured.


## R-077 — symmetric RAW EAR FIR decimation on constrained CPU (2026-11-22)

**Primary method reference:** SciPy's official `signal.decimate` documentation specifies anti-alias filtering before downsampling and documents a Hamming-window FIR option: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.decimate.html . The V14 implementation does not import SciPy or copy its implementation; it uses a small standard-library Hamming-windowed sinc filter to avoid a SciPy/NumPy Android dependency.

**Implementation:** the RAW EAR pitch/voicing feature view now applies a cached centered odd-tap low-pass FIR before integer decimation. Symmetric-pair convolution preserves the same linear-phase output while reducing coefficient multiplications. The cutoff, tap count, endpoint reflection, sample geometry and timestamps are unchanged. This is only a pitch/voicing feature decimator, not a calibrated VAD, speaker-embedding resampler or playback resampler.

**LOCAL_LINUX evidence:** CPython 3.13.5 x86_64, isolated algorithm reproduction. Direct-reference parity passed 36 seeded/random rate-length cases across 16, 22.05, 44.1 and 48 kHz with maximum absolute difference below 2e-11. Warm-cache 11-run medians on one second of 140-Hz full-scale PCM improved 12.1–19.5% in the isolated decimator. These are host-only timings, not whole-pipeline or Redmi measurements.

**Exact-head CI boundary:** the Perception producer and comparator pins are internally aligned, and the producer's A5→A4→C3 regressions pass on the Perception candidate. Staged/integrated CI on that candidate fails at the Core-owned composer source pin; the recovery/stage/deployer chain must be rebound and rerun on the combined candidate before merge. No Android AudioRecord, ARM runtime, Termux or Redmi test is claimed.

**Decision:** CANDIDATE_FOR_INTEGRATION / NO_DEPENDENCY / NO_DEVICE_CLAIM. Keep deterministic acoustic labels heuristic and retain the calibrated-probability limitation. Do not infer device speedup or production deployment from x86 timings.


## R-078 — llama.cpp native input-embedding API and license check (2026-11-22)

**Primary source/revision:** [ggml-org/llama.cpp revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4](https://github.com/ggml-org/llama.cpp/tree/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4). The exact-revision [LICENSE](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/LICENSE) is MIT (ggml authors, 2023–2026). The pinned [include/llama.h](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/include/llama.h) defines `llama_batch.embd` as the float embedding input when `token == NULL`, documents `llama_decode` over that batch, and exposes `llama_get_embeddings_ith` for output embeddings.

**V14 mapping:** the Core diagnostic receiver uses this native input path and is built in CI for Linux plus Android ARM64. This verifies the pinned API/ABI build path, not that an installed Redmi model can emit a semantically useful cross-family activation. The MIT code license does not grant model-weight rights; no model or weights were downloaded, swapped or modified.

**Next experiment:** use existing installed models only, with same-model parity, zero-input, shuffled-row, dimension, model-revision and source-tap controls. Measure receiver effect and task utility against SOURCE_EXACT and NO_MESSAGE, then train/evaluate an adapter with independent labels, holdout, OOD, retention and rollback. Production B3 stays OFF until all gates pass.

**Status:** SOURCE_AND_LICENSE_VERIFIED / API_REVIEWED / DIAGNOSTIC_ONLY; no new model alternative selected.


## R-079 — WebRTC/libfvad VAD comparison path and CLI verification (2026-11-22)

**Primary upstream:** `dpirch/libfvad`, exact source revision `532ab666c20d3cfda38bca63abbb0f152706c369` (the revision pinned by the V14 comparison workflow). Repository license is BSD-3-Clause; the upstream README describes it as a standalone extraction of the WebRTC VAD engine and documents `make check`. No libfvad source was copied into V13/V14 and no runtime dependency was installed.

**Secondary wrapper note:** upstream `wiseman/py-webrtcvad` declares an MIT wrapper license and includes the WebRTC BSD license for its bundled C code. The current workflow's test-only `webrtcvad-wheels==2.0.14.post1` distribution is a separate fork/package; its exact source revision/license was not established in this check, so it remains CI-only and is not selected for production.

**Method:** `v14/experiments/raw_ear_vad_compare.py` loads the exact RAW EAR V3 extractor by AST and source hash, compares its activity hints with a 20-ms WebRTC/libfvad baseline, OR-aligns two VAD decisions into the same 40-ms/20-ms windows, then applies the same `TemporalVoiceEvidence` smoother to both. It reports precision/recall/FPR/FNR/F1, false positives per nonspeech minute, onset/offset delay, wall/CPU time, RTF and whole-process peak RSS. The OR-alignment is an evaluation adapter, not native WebRTC post-processing.

**Concrete defect found:** the libfvad CLI path called `os.getenv("V14_LIBFVAD_VERSION", ...)` without importing `os`; direct `main(... --backend libfvad ...)` therefore raised `NameError`, although lower-level class tests passed. The Perception follow-up adds the missing import and a CLI regression that builds a temporary annotated WAV, invokes `main()` against the workflow-pinned shared library, and verifies the emitted backend revision. This makes the existing comparator entry point testable; it does not change RAW EAR or production inference.

**Evidence limits:** the workflow builds the exact pinned libfvad revision, runs upstream `make check`, and tests a synthetic harmonic voice-like fixture plus a C-ABI stub. That is native Linux/CI comparator smoke, not real speech-corpus accuracy. Real annotated WAV evaluation is caller-supplied and must remain local; no private audio is uploaded or logged. No Android/ARM64/Termux/Redmi timing, microphone, battery, PSS or quality result is available.

**Decision:** retain libfvad as a research comparator only. Do not replace the current RAW EAR path or add a production dependency until a permissively licensed real speech/noise corpus, independent annotations, negative music/noise controls, target ARM64 build and actual Redmi resource/quality measurements show a useful advantage. No model, weight, dependency, permission or device state was changed.


**Implementation status:** PR #2329 is open against the Boss audio-integration branch. Exact head `adcf619ea36b00daa7f68c81d4da6aa327f348cc` passed the `V14 RAW EAR vs WebRTC/libfvad comparison harness` workflow, run `45007987039` (Python 3.13/3.14 matrix). This verifies the CLI regression against the workflow-built pinned native library in Linux CI. The full local Aii checkout remains BLOCKED by GitHub DNS resolution in the execution container; no local full-suite or Android result is claimed.


## R-080 — LATER: action-conditioned retrieval of delayed transition evidence (2026-11-22)

**Primary source:** Zhou, Xu, Wang and Tang, *LATER: Learning Action-Conditioned Temporal Evidence Retrieval for Predictive World Models*, arXiv:2611.25671v1, submitted 2026-11-19: https://arxiv.org/abs/2611.25671 . Full text reviewed.

**Method:** partitioned memories store completed real transitions and remain fixed during candidate rollouts. A response bridge reads them using the current state and candidate action; auxiliary multi-cut supervision trains the memory writers while zero-initialized gates preserve a recent-only baseline. The paper separates retaining evidence from selectively reading it and evaluates paired-history interventions with the query observation/action held fixed.

**V14 hypothesis:** keep trusted observed T8/ActionOutcome evidence immutable during speculative prediction; only finalized source-verified outcomes update persistent writer/replay state. Readout should be conditioned on the receiver's current state/latent and proposed action, with a recent-only fallback. Compare correct earlier evidence, shuffled evidence, omitted evidence and hypothetical-only evidence under session/source-disjoint holdouts, delayed queries, restart, forget/revocation and rollback. This is additive to World/Self/Memory/JEPA and does not replace B1/B2 bodies.

**Limits and rights:** LATER uses a CF-JEPA/ViT-Tiny/14 backbone, 192-D latent split, GRU writers, gated rank-8 bridge and simulated physical-control tasks; its reported CEM measurements include H100-class execution. No public implementation repository or code license was identified in the paper/full-text page, and the paper's own reuse license was not verified from retrieved metadata. No code, weights or datasets are copied or selected.

**Decision:** RESEARCH_ONLY / TESTABLE_HYPOTHESIS. Do not import wholesale. First complete the source-bound T8→WorldJEPA/EMA→replay/retention→B1/B2 consumer loop and establish an Android-sized baseline. Future prototype: tiny action-conditioned readout vs recent-history, exact/no-memory and shuffled controls.


### R-080 implementation follow-up — temporal readout reaches the B1/B2 prompt (2026-11-22)

**Code candidate:** JEPA PR #2372, head 64ae877d7189c3109aff60583ef73aeed1fe4c32. The temporal T8 receiver now has an additive bodyview adapter: B1_DETAIL reads two committed transitions and B2_GIST reads three, then each receives a bounded action-conditioned prediction matrix through the existing Cognition.offer prompt path. The adapter validates checkpoint/source/history provenance, requires at least eight train-split support samples per emitted action, keeps the body-state budget at 700 characters, and returns no temporal readout when the learner lock is busy. The new regression calls Cognition.offer itself, captures the actual B1/B2 user prompt payload, verifies QueryPacket source provenance and the two distinct horizons, then checks the busy-lock fallback. The stored source audit deliberately says body_prompt_consumed=false; the QueryPacket plus captured prompt is the consumer proof.

**What this does not implement:** this is not a reproduction of LATER. The current reader uses recent same-session T8 history and action-conditioned candidate readouts. It does not yet retrieve partitioned cross-session transition memories during candidate rollouts, train memory writers with multi-cut auxiliary supervision, or prove delayed physical evidence use. It is a synthetic Store/NumPy SHADOW consumer, not a native B1/B2 model-weight update or Redmi result.

**Next measurable experiment:** hold the current query and candidate action fixed; compare correct earlier history, omitted history, shuffled history and hypothetical-only history. Use session/source-disjoint holdouts, delayed readout, zero-support negatives, restart, source revocation, rollback and matched replay steps. Keep the recent-history/no-memory path as the baseline. Report prediction error and downstream receiver utility separately; do not promote on predictor loss alone.

**Related primary source:** Zhang et al., *JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts*, arXiv:2610.00722 (submitted 2026-09-30): https://arxiv.org/abs/2610.00722 . Its abstract describes persistent predictor updates across episodes with dense replay while leaving the visual encoder and reward head fixed; it reports an average 83% reduction in autoregressive latent prediction error and 153% planning improvement over a frozen JEPA baseline after 500 episodes across eight dynamics shifts/four continuous-control environments. These are the paper's benchmark claims, not comparable evidence for V14's synthetic text/T8 store or Android device. The abstract was checked; no code or weight license was selected in this run.

**Decision:** RESEARCH_ONLY / TESTABLE_ABLATION. LATER and JEPA-TTT support testing a separation between durable observed evidence and selective action-conditioned readout. They do not justify importing a heavyweight robotics stack, changing installed models, or claiming learned native latent coupling. No dependency, model, weight or device setting was changed.

### R-081 — JEPA-TTT/LATER reuse and license screen (2026-11-22)

**Primary papers**
- LATER, arXiv:2611.25671 (submitted 2026-11-19): action-conditioned retrieval over partitioned memories of completed real transitions, fixed during candidate rollouts, with multi-cut auxiliary writer supervision. Its abstract reports 15.5% → 25.0% terminal success over reconstructed CF-JEPA on distracted Two-Stage PushT and 20.2% lower along-push MAE under distractors. The arXiv license link resolves to CC BY-NC-ND 4.0. No official code repository was found in the paper page or a GitHub repository search. Treat the paper as research input only; do not copy/redistribute its text or derivative material.
- JEPA-TTT, arXiv:2610.00722 (submitted 2026-09-30; World Models in Physical AI Workshop @ NeurIPS 2026): persistent action-conditioned predictor updates with dense replay across episodes, keeping the visual encoder and offline reward head fixed. The paper reports 83% lower five-block latent prediction MSE and 153% higher mean best held-out planning score than Frozen JEPA after 500 episodes across eight dynamics shifts/four control environments. Its official project page links paper/results/citation but no training-code repository; the arXiv page did not expose a code or weight license.

**Independent reproduction screen (not official code):**
- GitHub repository ZhengQingJing/jepa-ttt-reproduction, main HEAD 30002a766ecfc133245d3260d059fea2d768f486, identifies itself as an independent reproduction and is MIT-licensed.
- Its pinned upstreams are also MIT at the exact revisions declared in scripts/setup_upstream.py: lucas-maes/le-wm 8edfeb336732b5f3ce7b8b210d0ba370a09e2cac and galilai-group/stable-worldmodel 21446f1ede6d5284e981bd7b47f432b994e6d812.
- Reproduction dependencies are Python 3.11/Linux, PyTorch 2.8.0+cu126, torchvision 0.23.0+cu126, NumPy 1.26.4, Gymnasium 1.1.1, Einops 0.8.0 and a pinned Transformers commit; README reports a CUDA/bfloat16 GPU and RTX A6000 for the published runs. This is not an Android/Termux dependency candidate.
- The reproduction's downloaded checkpoint/dataset asset license was not established from the inspected README/manifest. Do not download, vendor or redistribute those assets without a separate license and provenance check.

**V14 decision:** REUSE_BENCHMARK_IDEAS_ONLY. The current JEPA lane already has a smaller source-verified T8/EMA/replay path. Reuse the papers' experimental controls—matched update budget, persistent-vs-reset optimizer, dense-vs-sparse temporal coverage, fixed held-out trajectories and action-conditioned history interventions—rather than importing a CUDA robotics stack. For LATER, test correct/omitted/shuffled/hypothetical history under fixed current query/action; for JEPA-TTT, compare dense replay and persistent optimizer against matched frozen/reset baselines. No third-party code, checkpoint, dataset, dependency, model or device setting was imported.
