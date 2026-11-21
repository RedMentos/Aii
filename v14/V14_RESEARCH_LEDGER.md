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

- **Primary source:** arXiv:2608.16347v2, version 2 dated 2026-11-09 (v1: 2026-08-17); https://arxiv.org/abs/2608.16347
- **Evidence:** FULLTEXT_REVIEWED on 2026-11-21; methods, results, discussion and limitations read. This remains an arXiv preprint, not an independently reproduced V14 result.
- **Models and method:** Qwen2-0.5B, Phi-3-mini, Mistral-7B and FLAN-T5-base. The projection experiment used 20 held-out questions and a learned MLP; the causal experiment injected at a middle-layer fraction of 0.5 in a manual forward-layer loop, without KV-cache reuse, for up to 25 generated tokens. Each decoder-only pair had 30 paired trials (10 questions × 3 seeds), with an unrelated projected state as negative control and FDR correction.
- **Reported result:** learned projection retrieval was 45–50% top-1 vs 5% chance for the three causal decoder-only pairs, but this did not predict generation-level success. Only Qwen2-0.5B → Phi-3-mini showed a significant causal effect: 23.3% retrieval vs 0.0% negative control, FDR-corrected p=0.0469. Both pairs targeting Mistral-7B had 0.0% real-condition retrieval vs 3.3% negative control and no causal effect. The paper explicitly scopes the positive finding to a causal effect on the representational *vehicle*, not transfer of meaning; its qualitative successful outputs were often not correct answers.
- **Limits:** small/medium models (0.5B–7B), two models quantized to 4-bit, only 30 causal trials per pair, wide 95% CI [10%, 40%] for the sole positive pair, no Android/ARM test, no information-theoretic channel-capacity result, and no proof of shared semantic understanding. This is a modest pair-specific preprint result, not a universal latent-communication recipe.
- **V14 consequence:** keep B3/latent injection OFF. Do not infer receiver compatibility from cosine similarity, retrieval accuracy, or a final-layer tap. Require pair-specific middle-layer extraction/injection, true receiver generation, unrelated-state negative control, exact-message and no-message baselines, held-out task utility, restart/retention and resource measurements. The current V13 tap exposes final output embeddings, so it is not equivalent to the paper's middle-layer intervention.

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


## OSS implementation feasibility — llama.cpp b10964 (2026-11-21)

- **Primary source/revision:** https://github.com/ggml-org/llama.cpp/tree/b10964. The V13 model registry pins this runner family to source revision `b29c606e2` and archive SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`.
- **License:** upstream root `LICENSE` at b10964 is MIT. No upstream code was copied and no dependency was added. Model-weight licenses remain independent.
- **Exact source facts checked:** `include/llama.h` documents the pinned `llama_batch` as token-ID input when `embd == NULL`, or embedding-vector input when `token == NULL`; this legacy batch does not express a mixed token/embedding sequence. The same header exposes `llama_set_adapter_cvec(ctx, data, len, n_embd, il_start, il_end)`, whose buffer is an `n_embd × n_layers` control-vector matrix applied over an inclusive layer range. The pinned `tools/server/server.cpp` exposes dynamic `/lora-adapters` routes but no per-request control-vector route; `tools/server/README.md` documents control vectors as startup CLI options (`--control-vector[-scaled]`).
- **Current V13 connection:** the pinned `LlamaRunner` tap uses `--embedding --pooling none` and the server's embeddings endpoint; its tap contract is final output/RMSNorm embeddings, not arbitrary middle-layer hidden states. The server cannot currently receive a new per-turn cvec through its HTTP API.
- **Engineering conclusion:** a genuine per-request receiver intervention needs a custom C-API runner or a carefully serialized server extension around `llama_set_adapter_cvec`, plus pair-specific trained projection and a negative-control generation test. Restarting the server with a static CLI vector is not a viable interactive substitute. The newer upstream `llama_batch_ext` mixed-input/state-row API must not be assumed available in pinned b10964.
- **Next hard test:** compile against the pinned b10964 source, run a tiny native model with a neutral vector, learned vector and unrelated-vector control, verify output/activation changes and rollback, then test one real B1/B2 model pair. Record native RSS/PSS and TTFT. Until that exists, native hidden-state injection and V14-003 remain NOT_IMPLEMENTED / NOT_RUN.

## Research-to-code checkpoint — RAW EAR prosody and A4 attention (2026-11-21)

- PR #2161, branch `research-perception/v14-prosody-attention-20261121`, adds `prosody_change_score` from within-window F0 excursion or energy dynamics, emitted only for periodic voiced activity. It is a deterministic salience heuristic, not a speech probability or learned detector.
- The existing `consume_pcm16_voice_window` now feeds that score to A4 `Attention.modulate` and includes it in the source-bound C3 admission summary. Telemetry is correctly labelled caller-supplied PCM16 rather than assuming every buffer is synthetic.
- LOCAL_LINUX Python 3.13.5 isolated reproduction: 5/5 PASS (flat-tone negative, pitch-sweep positive, amplitude-burst positive, unvoiced-noise negative, monotonic attention relation). Exact repository test file is pending the new PR workflow; full local checkout is BLOCKED by GitHub DNS. No model inference or Redmi microphone evidence.
- **Next:** read exact-head CI; Core updates its staged overlay source pin to the new adapter blob before the staged B1/B2/C3 Runtime test. REDMI_UNVERIFIED / NOT_RELEASED.



## Research & Perception update — 2026-11-21 / RAW EAR robustness and model alternatives

### R-016 — PACE: audio continual learning requires explicit representation-stability tests

- **Primary source:** Chang Li, Kanglei Zhou & Liyuan Wang, *PACE: Pretrained Audio Continual Learning*, ICLR 2026 (conference paper): https://proceedings.iclr.cc/paper_files/paper/2026/hash/26cce1e512793f2072fd27c391e04652-Abstract-Conference.html ; full paper: https://proceedings.iclr.cc/paper_files/paper/2026/file/26cce1e512793f2072fd27c391e04652-Paper-Conference.pdf
- **Evidence:** FULLTEXT_REVIEWED 2026-11-21; published at ICLR 2026, not merely an abstract/preprint.
- **Setup:** EAT self-supervised audio backbone pretrained on AudioSet-2M (~5,000 hours), evaluated on six sequential audio-CL benchmarks: ESC-50, UrbanSound8K, SpeechCommands V2, TIMIT-2, TIMIT-3 and VocalSet. Three are coarse-grained and three fine-grained.
- **Reported results:** PACE top-1 accuracy: 95.75 / 97.49 / 91.87 on the three coarse benchmarks and 90.95 / 94.05 / 69.08 on the fine-grained benchmarks. It combines regularized analytic first-session adaptation, multi-session adaptive subspace-orthogonal PEFT and boundary-aware spectrogram perturbations. The paper reports direct transfer of vision PEFT strategies to audio can fail through representation saturation or representation shift; naive full-layer adaptation can damage reusable shallow features.
- **Limits:** the evaluated backbone and training setup are not a Redmi drop-in; results are benchmark/session classification, not raw-ear conversational learning or live voice-agent utility. The paper states code will be released after acceptance, but the inspected official author page did not expose a maintained implementation repository. No code/dependency or weight was imported.
- **V14 consequence:** before any audio-adapter training, retain source-disjoint old/new cohorts, measure representation drift and held-out utility per session, compare no-update / analytic-head / selective-adapter paths, and test old-cohort retention plus rollback. Do not infer that ordinary LoRA is safe for the audio encoder; do not turn a temporary frozen baseline into a permanent teacher.

### R-017 — S4VAD: low-latency onset detection is a separate capability from prosody

- **Primary source:** Elad Cohen, Arnon Netzer & Hai Victor Habi, *Low-Latency State Space Voice Activity Detection with Robust Onset Time Evaluation*, arXiv:2609.11110, submitted 2026-09-10: https://arxiv.org/abs/2609.11110
- **Evidence:** FULLTEXT_REVIEWED 2026-11-21; arXiv preprint, not a peer-reviewed conference result in the inspected record.
- **Method/setup:** S4VAD uses four causal S4 blocks with hidden dimension 64, state dimension 64 and a length-201 causal kernel. It consumes 64-dimensional log-Mel features from 16 kHz audio, 32 ms frames and 10 ms hop. Training uses synthetic noisy LibriSpeech mixtures (100-hour subset, SNR -5 to +20 dB); evaluation also includes AVA-Speech. The paper explicitly models noisy onset labels rather than treating timestamps as exact.
- **Reported result:** under its LibriSpeech onset-latency protocol, S4VAD reports P50 10 ms, P90 90 ms and P95 130 ms, versus MarbleNet P90 150 ms / P95 210 ms. These are paper-specific onset metrics, not end-to-end Android response times. Hardware comparison used XNNPACK on an Apple M4 Max 64 GB, not Redmi.
- **Limits:** no maintained official code/weights or license was located during this review; no Android/ARM benchmark, no full-duplex interruption test and no paralinguistic/non-speech understanding. A VAD posterior cannot replace RAW EAR acoustic/prosody channels.
- **V14 consequence:** if onset responsiveness becomes a measured bottleneck, compare a small stateful VAD candidate against the current bounded RAW EAR path using onset delay, false interruption rate and tail latency under noisy speech, silence, backchannels and overlapping speech. Keep VAD probability as a separate optional cue.

### R-018 — Silero VAD: small MIT-licensed optional speech-probability candidate

- **Primary implementation:** https://github.com/snakers4/silero-vad/tree/066409f3d9db45a30d21dfcbf9147826ffdd7052 ; inspected upstream commit `066409f3d9db45a30d21dfcbf9147826ffdd7052`, 2026-10-22.
- **License:** repository `LICENSE` is MIT (blob `0bf5e90cac691b999d4a35044f97167d7bbbf0b9`). The upstream README describes an approximately 2 MB JIT model, ONNX support, 8 kHz / 16 kHz input and stateful streaming use; the repository includes C++ ONNX examples.
- **Limits:** the README's sub-millisecond chunk claim is not an Android measurement. ONNX Runtime availability/ABI on this exact Termux Android target is not established. Model weights and package versions still need an exact pinned hash and dependency review before integration.
- **V14 consequence:** candidate only for a parallel calibrated speech-activity hint, never a replacement for RAW EAR, prosody, non-speech vocalization or acoustic provenance. Do not download or swap it without an explicit experiment gate and a real ARM test.

### R-019 — VoiceNet / VoiceCLAP-Small: richer paralinguistic supervision, but not a Redmi default

- **Primary paper:** Christoph Schuhmann et al., *VoiceNet: Fine-Grained Voice Understanding Beyond Emotion at Scale*, arXiv:2609.32016, submitted 2026-09-25: https://arxiv.org/abs/2609.32016 . **Implementation:** https://github.com/LAION-AI/voicenet . **Model card:** https://huggingface.co/laion/voiceclap-small
- **Evidence:** FULLTEXT_REVIEWED 2026-11-21; arXiv preprint, with a public companion repository and model card. The repo/model card state CC-BY-4.0 for the released VoiceNet model/annotations; underlying encoder provenance/licensing must still be checked independently before redistribution.
- **Method/results:** VoiceNet-Emo has 40 emotion categories; VoiceNet-Ext has 57 talking-style attributes. VoiceCLAP-Small is ~110M parameters, a BUD-E-Whisper-Small / MiniLM dual tower with 768-dimensional normalized embeddings. The paper reports 0.6754 per-prompt balanced accuracy on VoiceNet-Emo, compared with 0.7021 for the 7B VoiceCLAP-Large; the comparison is representation-level ranking, not live assistant behavior.
- **Mobile caveats:** the model card reports F32 weights (~0.1B parameters) and zero-pads clips up to 30 seconds to a full 30-second Whisper-style window. This is not a 40 ms streaming ear, and no Android quantized TTFT/RSS/quality measurement was found. The repository's broad CC-BY-4.0 statement does not replace a separate audit of bundled base weights and all dependencies.
- **V14 consequence:** retain as an offline teacher/benchmark candidate only. If considered, isolate a short-window distilled student and evaluate style/prosody attributes with consented, source-bound examples; do not download or install on Redmi by default.

## Implementation evidence — RAW EAR V3 pause-robust prosody (2026-11-21)

- **Defect reproduced:** V2 derived prosody salience from the full-window energy range. A 0.5 s constant voiced tone with 0.25 s leading and trailing silence produced a 102.31 dB window range and a false maximum `prosody_change_score=1.0`.
- **Fix:** V3 retains `energy_range_db` as the full-window acoustic fact, adds `voiced_energy_range_db` from the 10th–90th percentile of periodic voiced-frame RMS, and computes prosody salience from voiced-only energy dynamics plus F0 excursion. The cue schema is versioned `RAW_EAR_AUTOCORR_V3`.
- **Consumer:** the existing A5 → PerceptPacket → A4 `Attention.modulate` → source-bound C3 admission path receives the new field and score; no transcript or identity is inferred.
- **Exact branch head:** `5e1e9c0ccdce48fd319c24903a6a92ab8a0f6432`; adapter blob `4324813f00eb86db2538ded63dfd1f711188d2cf`; test blob `d457b66cfd792e625f5588f900d876269e551aa9`.
- **CI:** GitHub Actions run `44871559784` PASS: Python 3.11 11/11 and Python 3.13 11/11; compile PASS. Additional staged/integrated run `44871559783` was still running at the first exact readback. Local isolated reproduction across 8, 12, 16, 44.1 and 48 kHz passed; this is not the full repository suite.
- **Integration blocker:** Core PR #2158 still pins the old adapter blob `7ac80a0d0deec8f52361fe89756ebd743b0a3537`; Core was notified to pin V3 blob `4324813f00eb86db2538ded63dfd1f711188d2cf` and rerun the staged B1/B2/C3 consumer. No Core-owned file was changed.
- **Device/release:** no connected authorized Redmi or microphone receipt; REDMI_UNVERIFIED / NOT_RELEASED. No native model inference, learning, Android performance, or phone deployment is claimed.


## R-020 — V14-005 sequential native C3 candidate lab and model-registry audit (2026-11-21)

- **Primary local source:** `v13/code/specs/models.json` at V14 base `c0cedbde718ede6107f4df1f1bf9c784df4e00cf` (blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`); V13 `models.py` blob `bd035cf8029850cce00b179edf533e53bf24358a`; `runners.py` blob `2242d8e75372f84e2384bd59ab69ac95eb3a083a`. The current base and candidate-lab branch contain identical versions of these three V13 files.
- **Registry fact:** current C3 is LiquidAI/LFM2.5-350M-GGUF, revision `657e078c94084481950a2d555a941481f715536b`, QAD_Q4_0, 219,312,832 bytes, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. The previous candidate is LFM2.5-230M-GGUF, revision `cdf97bd8205908758f44aec508d68ac1aef98f5c`, QAD_Q4_0, 149,081,056 bytes, SHA256 `e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292`. The 230M file is 70,231,776 bytes (~47.1%) smaller, but the registry's historical 2026-10-09 cloud selection note reports lower STEP2 B1+B2 exactness (0.37 vs 0.58) and lower AG12 exactness with anti-echo (0.12 vs 0.55), with ~40% faster decode. These are historical cloud measurements, not Redmi measurements.
- **Known negative evidence:** issue #1904 records a historical Redmi C3 230M run returning 2 for 2+2. Do not promote this model as a reasoning replacement from size or latency alone.
- **License:** LFM Open License 1.0, revision-pinned model LICENSE URL; the lab preserves a license text snapshot with SHA256 `61d7e939a05911c765b7e98ffaa1ab5ca6c0174a65350766c25cb10197d19fc8`. Section 5's commercial-use threshold caveat remains visible. The snapshot is provenance evidence, not a claim that its source file is byte-identical to the model repository's license.
- **Executable lab:** PR #2142 implements a read-only sequential C3 comparison through the actual V13 LlamaRunner/llama-server path. It verifies installed/candidate GGUF revision, magic, size and SHA; takes the V13 coordinator lock before installed-state reads; copies verified files into private read-only staging; checks the configured and loaded runner binary identity; records prefill/TTFT/decode/RSS/PSS and four fixed quality checks; stores output digests rather than raw model output. No download, manifest edit, install, swap, SQLite/chat-history read or model promotion occurs.
- **Evidence:** exact lab code/test SHA `40deb8a56686455b361ba41e63cb57b981b5a71b` passed GitHub Linux/Python 3.13.18 workflow `44861145442`: compile + manifest validation + 23/23 synthetic tests. This is not native GGUF inference. Candidate GGUF was not present/verified, so comparison is `NOT_RUN`; no Redmi receipt, PSS/RSS, TTFT, answer-quality measurement or deployment exists.
- **Integration state:** original PR #2142 is based on stale ancestor `c3c32c05a0374e970d274f8a777a7ab85c067d66` and was reported `mergeable=false` against V14 base `c0ced...`. A new branch must be rebuilt from the current base without copying the old research ledger over newer shared entries; preserve the model-lab code, license snapshot and 23-test evidence.
- **Decision:** keep candidate diagnostic-only. No download, experimental try, production swap or model/weight change is authorized by this research record.
