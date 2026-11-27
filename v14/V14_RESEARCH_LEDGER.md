# V14 / Inquisition-JEPA — laufendes Forschungsjournal

**Stand:** 2026-11-27. **Arbeitsart:** ergebnisorientiertes laufendes Research, nicht bloß Literaturanhang.  
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

- **Primary source:** Fernando Cárdenas Piepereit, arXiv:2608.16347v2, revised 2026-11-09 (v1 submitted 2026-08-17). Full v2 HTML read on 2026-11-25: https://arxiv.org/html/2608.16347v2
- **Licensing and reproducibility:** The paper is CC BY 4.0. Its v2 Data and Code Availability statement says the concept-pair sets, extraction/projection scripts, injection mechanism, raw results for all 180 generation trials, run logs, pre-registration, and a table-recomputation script are on Zenodo DOI 10.5281/zenodo.24088479; it states code is MIT and data/documentation CC BY 4.0. The Zenodo record/files could not be retrieved in this run, so their inventory and actual contents were not inspected and nothing was reused. The paper reports v2 corrected three Section 4.1 statements; tables and conclusions are unchanged. It is an arXiv preprint, not a peer-reviewed venue in the reviewed metadata.
- **Question and method:** Tests whether activation states can be mapped and causally injected across four open-weight models: Qwen2-0.5B, Phi-3-mini-128k-Instruct (4-bit), Mistral-7B-v0.1 (4-bit), and FLAN-T5-base. The study compares 12 RELATED and 12 lexically dissimilar SYNONYM concept pairs across layers; mean-pools token states after removing special tokens and, for causal decoders, position 0; trains a middle-layer (0.5) MLP projection on sentence/question representations disjoint from the concept-pair set; evaluates top-1 retrieval among 20 held-out questions (5% chance); then performs generation-time injection against a wrong-question negative control. Injection is at the last token of a multi-token “Answer:” placeholder after a fixed middle layer, using a manual layer loop without KV-cache reuse.
- **Reported results:** Projection retrieval reaches 45–50% top-1 for the three decoder-only pairs versus 5% chance; Qwen2→FLAN-T5 is at chance (5%). Rank-based mutual-kNN alignment is more robust to activation-magnitude outliers than CKA/Procrustes in the reported comparison. End-to-end causal generation transfer passes its pre-registered criterion for only one of three decoder-only pairs: Qwen2-0.5B→Phi-3-mini, 23.3% versus 0.0% wrong-state control, FDR-corrected p=0.0469, n=30, 95% CI [10%, 40%]. Both pairs targeting Mistral show 0.0% real versus 3.3% control. Even the positive pair often produces text related to the source question rather than the correct answer.
- **Critical interpretation:** The authors explicitly claim transfer of a causal representational *vehicle*, not transfer of meaning or shared understanding. Hidden-state alignment and retrieval are insufficient predictors of generation-level causal transfer. The sole positive result is modest, has a wide interval, and sits just below the conventional 0.05 threshold after FDR correction. The paper is limited to 0.5B–7B models, CPU-constrained experiments, two 4-bit models, 30 trials per causal pair, and no information-theoretic channel analysis.
- **Position-0 finding:** In this study, naive causal-decoder mean pooling produced near-1.000 cosine similarity even for unrelated/random word pairs because one early-position activation dominated. Excluding position 0 was necessary in the authors' tested Qwen2/Phi-3 setup; this is an empirical result for those models, not a universal law. The paper also reports that raw CKA/Procrustes can be distorted by large-magnitude dimensions; its rank-based kNN measure is the preferred screening metric in this experiment.
- **Monitoring/dual-use finding:** Section 6.2 explicitly notes that activation-level transfer removes the human-readable text surface and can therefore evade content filters and audit logs. The authors release code with a dual-use note, arguing that reproducibility enables safety/monitoring research. V14 must therefore keep any future latent route opt-in, source/age/consent-bound, auditable at the control plane, and outside model-controlled permission authority; do not create a covert or unlogged channel.
- **V14 mapping:** Current V13 tap code records per-token final RMSNorm output embeddings from the llama.cpp /embeddings path (pooling=none), not the paper's middle-layer residual-stream activations. The current native receiver path in draft PR #2488 feeds vectors through llama_batch.embd at the receiver input boundary, not through a matched middle-layer injection hook. Current B1/B2 tap widths are 2048/1024, so direct dimensional compatibility is not general. Draft PR #2489 now contains a source-disjoint low-rank adapter fitting path, but it has not been fit on real tap pairs; there is still no accepted native latent communication. Symbolic/source-exact exchange remains distinct.
- **Implemented research tool:** PR #2489, implementation commit 8ebc18b322745dfb96b524e25933408597ae92eb (final docs head f0dddf93166bd9949a1be88748e66b720a889afd), adds a read-only audit for persisted LatentTapPacket artifacts at v13/code/v13/latent_alignment_audit.py, with tests at v13/code/tests/test_latent_alignment_audit.py. It pairs exact source-ref + event + generation records, validates authority flags and blob hashes, excludes position 0 from its pooled alignment vectors, reports position-0 norm ratios, and computes cross-space kNN-neighbourhood overlap with a permutation null across different dimensions. This is an explicitly labelled proxy, not the paper's exact MNN implementation; the Zenodo code has not yet been inspected. The tool reads no source text, loads no model, exports no vectors, writes no DB state, changes no weights, and grants no receiver/training authority. It is bounded to 32 source pairs, four revision cohorts, 64 rows and 4096 dimensions for mobile memory control.

- **Implemented adapter bridge (2026-11-25):** the same draft PR #2489 now adds `v13/code/v13/latent_adapter.py` and `fit_from_tap_records()`. It reads the existing LatentTapPacket/blob store in SQLite read-only mode, pairs exact SourceRef + event + generation, retains at most one observation per source_id, and requires at least 20 valid source groups before a deterministic source-disjoint train/holdout split. It fits a low-rank affine PCA+ridge map between B1/B2 tap spaces, records held-out MSE versus mean and shuffled controls, parameter magnitude/count, and saves/loads an atomic hash-checked adapter checkpoint. Projection uses the Python standard library; NumPy is imported lazily only for offline fitting. This is a closed-form adapter fit, **not gradient-based JEPA learning**; old-task retention is not measured. The module does not load a model, invoke the native receiver, write SQLite, modify B1/B2/C3 body weights, or grant production/training authority. Model SHA-256 values are supplied by the caller; this tool does not verify the installed manifest or model-weight licence. The Core-owned native receiver remains behind its separate local-TTY/one-shot approval path.
- **Dependency/licence:** NumPy 2.3.5 is used only in the offline fit workflow. NumPy's source/docs licence is BSD-3-Clause; published binary wheels can include separately licensed bundled libraries, so the exact wheel/runtime dependencies must be checked before any Android packaging. See the official [NumPy licence note](https://github.com/numpy/numpy/blob/main/doc/source/license.rst). No third-party adapter implementation or model weights were copied; the adapter code is project-owned.
- **Local evidence:** CPython 3.13.5; py_compile PASS; focused synthetic Store/blob integration tests 9/9 PASS; CLI help PASS. CI on implementation commit 8ebc18b: staged context/integrated regression, privacy scan and integration workflow SUCCESS; safe-additive workflow SKIPPED. On docs commit 8818a88: staged-runtime, privacy scan, runtime-integrity and Core same-turn checks SUCCESS; integrated-regression was IN_PROGRESS at the first poll, then completed SUCCESS in workflow run 45559754665; final docs-only head f0dddf9 had no workflow run visible. The fixture uses the actual V13 packets table column layout. No real tap cohort was available, so no V14 alignment result, native generation result, adapter training, or Redmi result is claimed.
- **Next falsifiable step:** After Core's opt-in native tap writer is integrated and the runtime is explicitly running, collect at least 20 paired B1/B2 source groups from the same event/generation. Run the read-only audit and the new source-disjoint adapter fit on the same pinned model revisions/tap IDs, supplying model hashes only from the installed manifest. If alignment/held-out fit beats the permutation and shuffled-pair controls, pass projected rows to the Core-owned receiver only through its local-TTY/one-shot approval path. Then test receiver-side task utility against exact-message/no-message/zero/shuffle/wrong-source controls, with restart, rollback, retention and measured RSS/TTFT. Inspect the Zenodo archive when accessible before claiming exact MNN reproduction. Do not enable B3 or call this semantic communication on alignment/fit evidence alone.

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


## R-081 — Prompt Compression in the Wild: measure end-to-end break-even (2026-11-23)

**Primary source:** Cornelius Kummer, Lena Jurkschat, Michael Färber and Sahar Vahdati, “Prompt Compression in the Wild: Measuring Latency, Rate Adherence, and Quality for Faster LLM Inference,” arXiv:2604.02985, 2026-04-03; https://arxiv.org/abs/2604.02985. The abstract reports a large evaluation (30,000 queries, multiple open models and three GPU classes) and separates compression overhead from model prefill/decode latency. It reports up to 18% end-to-end speed-up in a matched operating window, while compression overhead cancels gains outside that window.

**Knowledge status:** ABSTRACT_VERIFIED / FULLTEXT_PENDING / REPRO_NOT_ATTEMPTED. The paper page and abstract were checked; the full paper, appendix and code were not inspected in this run.

**V14 mapping:** this supports measuring the complete path, not optimizing prompt token count alone. For the new C3 admission policy, separately measure reducer CPU time, token count before/after, native prefill, TTFT, decode time, total latency, answer correctness and peak RSS. Compare no reduction, current exact structural omission, and any future reusable learned compressor. Do not compress exact B1/B2 source evidence, selected peer content or trusted tool output. A compressor is not useful if its per-turn preprocessing costs more than the prefill it saves.

**License/reuse:** paper metadata is cited through arXiv. No code or model was imported; no implementation/license review was performed. The result is not Redmi evidence.

**Next hard test:** on the same installed model and task cohort, run matched no-reduction vs structural-reduction trials with source-exactness checks and a negative control where no removable layer exists. Measure the whole turn, not only prompt length.

## R-082 — TAKE: Task-Aware Chunked KV Cache Eviction (2026-11-23)

**Primary source:** Rui Wang, Nan Jia, Jiahui Li, Qingyi Yang, Yixue Hao and Long Hu, “TAKE: Task-Aware Chunked KV Cache Eviction for Efficient Long-Context LLM Prefill,” Findings of EMNLP 2026, pages 5449–5463, DOI 10.18653/2026.findings-emnlp.260; https://aclanthology.org/2026.findings-emnlp.260/. The ACL Anthology abstract reports chunked KV eviction with accumulated task-aware probe tokens and delayed eviction; reported results include >60% TTFT improvement and 59.53% peak-memory versus baseline at 128K tokens.

**Knowledge status:** ABSTRACT_VERIFIED / FULLTEXT_PENDING / CODE_LICENSE_UNVERIFIED / REPRO_NOT_ATTEMPTED. The ACL Anthology metadata and abstract were checked. The full paper and linked source repository were not audited. ACL publication metadata indicates post-2016 Anthology material is CC BY 4.0; that does not establish the linked implementation's code license.

**V14 mapping:** potentially relevant only if long-context prefill/KV construction becomes a measured bottleneck beyond prompt-text admission. The reported 128K setting is not comparable to V13's current 2K context and must not be translated into a phone speed claim. Integration would require compatible attention/KV access in the actual llama.cpp runner, bounded CPU/ARM memory, source-retrieval negatives and exact cache-position semantics.

**Decision:** RESEARCH_ONLY; no code, dependency or model imported; no runtime default changed.

**Next hard test:** inspect the full method and exact repository revision/license; verify whether the target native backend exposes the required layer-wise KV hooks. If not, reject for the current phone runner rather than adding a heavyweight PyTorch/GPU dependency.

## R-084 — Source-forget is not weight-level unlearning: reversibility probes (2026-11-23)

**Primary sources:** Xiaoyu Xu et al., “Unlearning Isn’t Deletion: Investigating Reversibility of Machine Unlearning in LLMs,” Proceedings of ICML 2026, PMLR 306:142657–142704, https://proceedings.mlr.press/v306/xu26cd.html. Abstract verified; full text and code not reviewed here. The authors report that task-level accuracy/perplexity can make forgetting look successful while minimal fine-tuning restores original behavior; diagnostics include PCA similarity/shift, CKA, Fisher information and mean PCA distance. Shoaib Ahmed Siddiqui et al., “From Dormant to Deleted: Tamper-Resistant Unlearning Through Weight-Space Regularization,” NeurIPS 2025, https://papers.nips.cc/paper_files/paper/2025/hash/bbeafbaa60ee03f2c3135be71ebd5d06-Abstract-Conference.html. Abstract verified; the controlled experiment is on vision classifiers, not LLMs or V14.

**V14 mapping:** PR #2429 implements source-aware checkpoint rollback/replay after Memory forget. That is provenance/retraining, not proof that an already-trained neural body's parameters have unlearned a source. For future trainable B1/B2/C3/A/JEPA weights, compare a clean rebuild from retained source-filtered history with the purportedly unlearned checkpoint after retain-only fine-tuning. Track parameter hashes/deltas, held-out retain utility, forget-set behavior, representation drift where exposed, OOD, restart and rollback. A lower forget-set score alone is not a deletion guarantee; collateral capability loss is also failure.

**Status:** ABSTRACT_VERIFIED / FULLTEXT_PENDING / VISION_STUDY_NOT_LLM / NO_CODE_OR_WEIGHT_REUSE / RESEARCH_ONLY. No model, dataset, dependency or weight was downloaded or modified.


## R-090 — llama.cpp prompt-cache isolation risk and deadline-aware prefill research (2026-11-22)

### Primary-source findings

- Upstream llama.cpp [issue #32048](https://github.com/ggml-org/llama.cpp/issues/32048), opened 2026-11-10 and still open at this review, reports that POST /slots/{id}?action=erase clears the selected slot but not the shared --cache-ram prompt pool. In the reported -np 1, cache_prompt=true sequence P→Q→erase→P, the final request restored P's cached prefix; the reporter observed zero restored tokens with --cache-ram 0. A second report in the issue reproduces a related shared-pool behavior with two slots. This is an upstream bug report, not a V13 reproduction.
- Upstream llama.cpp [issue #27148](https://github.com/ggml-org/llama.cpp/issues/27148) reports stale cross-conversation restoration under concurrent load with --cache-ram / --cache-idle-slots; its report notes that API cached-token accounting can remain zero for corrupted responses. The issue is open in the reviewed source snapshot.
- V13 source inspection in PR #2367 records -np 1, --cache-ram 128, cache_prompt=true, id_slot=0, and a Runtime-shared per-role RunnerPool rather than a session-keyed pool. This overlap makes a unique-marker isolation canary worth planning, but does not establish that V13 has suffered cache contamination.

### V14 implementation consequence

1. Keep current installed cache flags unchanged; no user authorization to change them was given.
2. Before any mitigation, design a synthetic P/Q/P unique-marker test with fresh server baseline, same-session reuse, cross-session separation, slot erase, cache accounting and exact output checks.
3. Only after a separate explicit user approval should the same canary be run on the installed Redmi. Compare current configuration with a reversible --cache-ram 0 test profile; measure correctness, TTFT/prefill, RSS/PSS, cold/warm behavior and restart. Do not persist the experimental flag or promote it to product default without measured trade-off and approval.
4. Do not treat cached_tokens=0 as sufficient proof of isolation; compare actual output marker and source/session provenance.

### Deadline-aware scheduling research

- Siyu Song et al., [*Deadline-Aware Adaptive Prefill Chunking for Efficient Large Language Model Serving*](https://arxiv.org/abs/2609.07883), arXiv:2609.07883, 2026-09-07. SLOWeave chooses the largest prefill chunk predicted to finish before the earliest active decode deadline using a monotone iteration-cost model, measured cost tables and explicit deadline margins. The reported evaluations are simulator/GPU serving experiments; no Android ARM implementation or reusable code license/repository was identified in this review.
- Agrawal et al., [*Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve*](https://www.usenix.org/conference/osdi24/presentation/agrawal), OSDI 2024, uses chunked prefills and stall-free schedules to balance throughput and latency. The published results target GPU serving, not a 6-GB-class Android CPU, so the mechanism is a design reference rather than a measured performance prediction.

### Concrete experiment hypothesis

The current fair-budget candidate uses a fixed 45% pre-answer allocation and a 35 s observer cap. The latest device metadata reports a 38.945 s C3 prefill and B1/B2 timeout probes at 53.2/54.2 s. A measured per-role cost predictor could choose bounded observer slices and C3 reserve based on prompt tokens, warm/cold state and observed prefill rate rather than a fixed percentage. It must preserve both B1/B2 eligibility and a guaranteed C3 deadline; if neither body can produce a valid offer in its predicted slice, report a truthful partial result rather than claiming successful cooperation. First validate the predictor in synthetic staged tests, then with explicit device consent; no current runtime change is made by this research note.

**Status:** UPSTREAM_RISK_IDENTIFIED / V13_REPRODUCTION_NOT_PERFORMED / NO_CACHE_CHANGE / RESEARCH_ONLY.


## R-091 — Cross-architecture activation transfer: functional evidence and the missing V14 utility gate (2026-11-22)

**Primary paper read in full:** Ayushi Agarwal, *Cross-Architecture Steering Transfer in Language Models: A Systematic Empirical Study*, arXiv:2608.05164, submitted 2026-05-26. This is an arXiv preprint, not a peer-reviewed result in this review.

**Method and reported evidence:** five open-weight decoder-only models (GPT-2-large 0.8B, Gemma-2-2B 1.7B, and three 7B-class models) from two architectural lineages. The authors mean-pool residual-stream activations at approximately 50% depth, z-score per dimension, train TopK SAEs, align feature pairs by mutual nearest neighbours, and train a 67M-parameter MLP bridge for each of 20 directed pairs. Functional evaluation injects a translated vector at one residual-stream layer with 30 prompts × 15 concepts × 9 strengths. At scales ≥1.7B, 47–49% of matched feature pairs pass the paper's validation; the 0.8B model gives 29.9–33.3%. Reported cross-model steering win rate is 71.0%, versus 68.0% for native vectors and 65.7% for a zero-projection baseline. The 3-point cross-model/native difference is not statistically conclusive (paired t(4)=1.85, p=0.14; five models). Sign reversal gives a useful bidirectionality check, but the paper explicitly defers mechanistic T3 activation-patching causal tracing.

**Important negative results:** transfer is strongly domain-dependent: open-domain QA has only 7.9% validated pairs and biomedical 13.7%, while structured code/math registers perform better. The 1.7B discontinuity is *suggestive*, not a scaling law: there is only one model per tier below 7B, and parameter scale is confounded with GPT-2's absolute positional encoding versus Gemma/LLaMA RoPE. All models share the same corpus; a disjoint-corpus ablation is still future work. Only English decoder-only models are included; MoE, multilingual, Mamba and non-LLaMA architectures are outside scope.

**Compute / asset / license boundary:** the reported pipeline consumes approximately 52 A100-hours. It uses 67M parameters per directed bridge (20 bridges ≈5 GB of released bridge assets) and a 1.3 GB global MLP; the full residual activations are about 200 GB per model. The paper's asset table declares pipeline code and selected derived artifacts Apache-2.0, the derived corpus CC-BY-SA-4.0, and model-specific terms for the underlying checkpoints. The linked GitHub source could not be independently fetched through the connected GitHub API in this run (404); therefore no code import or license-dependent reuse is approved. No corpus, model, bridge, activation or weight was downloaded.

**Direct V14 consequence:** the current `native_latent_receiver.py` path is deliberately weaker than the paper's experiment. `LlamaRunner.tap` supplies per-token final output embeddings; the native wrapper feeds them to the receiver through `llama_batch.embd` at the *input* boundary, calls `llama_decode`, and measures output-embedding change against zero/shuffle controls. It does not inject at a mid-layer residual stream, generate target tokens, or score task-level utility. Therefore `NATIVE_INPUT_EFFECT` means only that the receiver numerically reacted; it is not semantic transfer, learned B3 coupling, or proof of useful communication. The existing packet's `semantic_use_proven=false` is correct and must remain so.

**Testable V14 adaptation:** (1) first prove same-model token-prefill versus same-model input-embedding parity on the pinned llama.cpp build; (2) add a separately gated receiver-generation/task-utility experiment, comparing NO_MESSAGE, SOURCE_EXACT, same-model parity, positive projected input, zero, shuffled, row-shuffled and bidirectional/sign-reversed controls on identical source-disjoint prompts; (3) measure exact task success/evidence recovery, not just cosine/RMS; (4) only then train a compact pair-specific low-rank adapter, with actual gradient/parameter diffs, held-out and OOD utility, old-session retention, restart and rollback; (5) if the target is the paper's method, add a native mid-layer residual injection hook rather than relabelling input-embedding ingress as residual-stream transfer. Keep all experiments opt-in, local, source-bound and B3 OFF.

**Decision:** RESEARCH_ONLY / NO_CODE_IMPORT / NO_WEIGHT_DOWNLOAD / NO_MODEL_SWAP. This paper supports testing pair-specific latent bridges, but does not justify a universal 1.7B cutoff or a mobile-sized implementation without new measurements.


## R-092 — Android AudioRecord capture geometry and signed RAW EAR ingress (2026-11-22)

**Primary platform sources read:** Android Developers, `AudioRecord` API reference, `AudioFormat` API reference, and *Sharing audio input*. These are official platform API documents, not papers or peer-reviewed results.

**Platform facts:** the AudioRecord constructor documentation states 44,100 Hz is currently the only sample rate guaranteed to work on all devices; 16,000 Hz and other alternatives may work only on some. The provider must call `getState()` after construction and bind the actual client rate from `getSampleRate()`. Android may resample/convert hardware input to the requested client format, so the signed receipt must describe the bytes actually delivered to the client, not claim an unobserved hardware-native format. On API 29+, `registerAudioRecordingCallback` reports capture-path changes, including silencing, device route, preprocessing and stream properties; register it before starting capture. Android's audio-sharing policy can silence an ordinary app when a higher-priority app captures, and foreground/foreground-service conditions matter. A silent or rerouted stream must not be treated as valid user speech.

**Current code evidence:** Perception PR #2312 (`research-perception/v14-audio-capture-consumer-20261122-run11b`, exact code head `5221314d3c01ab6d874ecc0a8b8ff72c34e504a2)) is a Termux-side signed one-shot verifier, not an Android microphone provider. It builds a maximum one-second mono 44.1-kHz PCM16 request (88,200 bytes; 117,600 Base64 characters), verifies the pinned P-256 companion receipt, request/nonce replay, source/generation, PCM digest, exact sample geometry, monotonic capture interval, RECORD_AUDIO status, local consent and FINAL provenance, then calls the existing `audio_input.submit_audio_only` consumer. Only nonce/request metadata persists; PCM is not written to disk. No microphone is opened, permission requested, transcript/speaker identity inferred, or learning/action authority granted.

**Exact CI / blockers:** signed-consumer workflow `44992975596` SUCCESS. Staged/integrated workflow `44992975599` FAILURE: 238 passed / 10 skipped / 47 subtests; two inherited two-checkout migration assertions expected `last_result=UPDATED` but observed `PARTIAL`. These are updater/migration failures, not signed-consumer test failures; do not weaken the assertions. Full local Aii checkout is unavailable. The companion still lacks an AudioRecord provider and RECORD_AUDIO manifest capability; no Termux microphone capture or Redmi test exists. PR #2310 is the stale 16-kHz predecessor and must not be merged; #2312 is the 44.1-kHz successor and carries the corrected bound.

**Testable V14 adaptation:** Core/QA must build a visible, explicit one-shot AudioRecord provider; check `getState()` and actual `getSampleRate()`; register `AudioRecordingCallback` before capture; reject silence, route/preprocessing/format changes and short reads; bind the signed receipt to the actual client PCM bytes and exact sample geometry; release AudioRecord and clear the one-shot PCM buffer after submit/cancel. Perception must rebase the consumer onto the current QA/Boss chain and deduplicate the exact `audio_input.py` dependency from #2304. Then test source-bound timed RAW EAR → A5 → A4 → C3 on synthetic CI and only later on an explicitly consented Android device.

**Decision:** PLATFORM_API_VERIFIED / SIGNED_TERMUX_CONSUMER_CI_PASS / STAGED_MIGRATION_FAIL / ANDROID_PROVIDER_ABSENT / REDMI_UNVERIFIED. No model, weight, external dependency, permission or device state was changed.


**Companion source readback (QA base branch):** current ref `qa/v14-companion-os-permission-contract-20261122` resolves to `7650ae0c19e93e4b6cbb778abb2f5123e49c364f`. Its `android-companion/app/src/main/AndroidManifest.xml` has no `RECORD_AUDIO` permission; `CapabilityRegistry.java` marks `audio_capture` unavailable with reason “No one-shot visible AudioRecord provider; capture remains disabled”; `AudioCaptureDefaultOffTest.java` asserts that RECORD_AUDIO is absent. This confirms the provider is deliberately OFF, not merely untested. PR #2312 still records its historical base SHA `58666ddfc9945612a2117e1a844f812442d4ca64`, so it must be rebased/reconciled after the QA/Boss parent chain settles.


## Research ID reconciliation note — 2026-11-22T22:03:32.071Z

PR #2380 is merged into the Boss documentation branch only (not the release branch) and assigns **R-092** to Android AudioRecord capture geometry / signed RAW EAR ingress. JEPA PR #2374 used the same ID for a distinct continual-learning paper. Boss requested on #2374 that the JEPA entry be renumbered to **R-093** while preserving both findings. Until that branch readback confirms the rename, do not merge a second R-092 or treat the collision as resolved. No research result is deleted or silently replaced.

 
## Boss integration status note — 2026-11-22 (2026-11-22T22:24:48.002Z)

No new primary-source research was performed in this Boss integration run. Existing R-091 cross-architecture and R-092 Android AudioRecord findings remain unchanged. The R-092 identifier collision with the separate JEPA paper in PR #2374 remains unresolved; the requested R-093 renumbering has not been verified by branch readback. Do not reuse or delete either research record. No external code, model weights, corpus or dependency was imported or downloaded in this run.


## R-094 — Provider-agnostic local teacher-ear path and sherpa-onnx candidate audit (2026-11-22)

**OSS source:** `k2-fsa/sherpa-onnx`, release v2.0.3, exact upstream commit `38016c6e0622e90bf417c35e8b47e0eb805af417` (2026-11-22). Repository code is Apache-2.0. The upstream README advertises Android arm64 and streaming/non-streaming ASR; the Android build script uses the Android NDK, JNI and ONNX Runtime 1.28.2. This is an Android NDK/JNI route, not proof of a Termux-native binary or ABI compatibility.

**Small model candidate:** `csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17`, model-card revision `d42f2d9f7ca24806fb667456a18a9f1b60f70d16`, declares Apache-2.0. It is an English-only 20M online Zipformer transducer trained from LibriSpeech. Its int8 encoder is 42.8 MB, decoder 539 KB and joiner 260 KB; the fp32 encoder is 88.8 MB. The README also lists simulated-streaming for some offline models; do not confuse that with the actual online transducer. These are artifact sizes, not runtime RSS, latency or accuracy measurements.

**V14 fit and limitations:** a small local online ASR teacher could emit timestamped word hypotheses while RAW EAR continues to carry prosody, voice activity, silence/noise/impulsive events and temporal evidence. The teacher must remain an additive, source-bound hypothesis, never replace RAW EAR or become truth/speaker/learning/action authority. The 20M English-only model is not a German conversational candidate; a German/multilingual model needs separate weight-license, memory and quality review. The Android NDK/JNI build may be useful in the companion, but the Termux app needs its own ABI/linkage test. No model, dependency or weights were downloaded.

**Code translation in this PR:** `audio_teacher_ear.py` defines a provider-agnostic timed result contract (exact PCM SHA/source/generation/window/finality, model provenance fields, 64-word and 512-character bounds). `consume_pcm16_voice_window` accepts it only with both the local-teacher opt-in and separate transcript-consent flag while the current audio consent lease is held. Only FINAL hypotheses become a separate ephemeral C3 Percept; PROVISIONAL stays out of C3. Transcript text is not added to the persisted RAW EAR PerceptPacket, and model/network provenance remains caller-asserted rather than attested.

**Proof boundary:** local isolated CPython tests exercise the contract; the full Aii checkout and Android provider are not available in this runner. This does not run sherpa-onnx, perform ASR, prove Android microphone capture, or establish Redmi TTFT/RSS/quality. The current release Runtime still needs Core's audio-window dispatch hook and QA's visible signed AudioRecord provider. No model download or product swap is requested.

## R-095 — Multilingual Whisper tiny as a slower Teacher Ear option (2026-11-22)

**OSS source:** `ggml-org/whisper.cpp`, current upstream commit `5eaee0cc9024eb9e9a99469199920c8b7f5cb9ec` (2026-11-20). Code license MIT. The repository has an Android example, ARM NEON support and integer quantization. Its README lists the multilingual `tiny` artifact at 75 MiB and approximately 273 MB memory; this is an upstream estimate, not Redmi/Termux RSS.

**Model source and license caveat:** `openai/whisper-tiny` is a 39M-parameter multilingual checkpoint with 99-language support including German. The Hugging Face model card currently labels it Apache-2.0, while the original OpenAI Whisper README states that Whisper code and model weights are MIT. Treat this as an unresolved metadata/license discrepancy; do not import the weights until the exact artifact's rights are reconciled. The 2022 paper is Radford et al., *Robust Speech Recognition via Large-Scale Weak Supervision*, arXiv:2212.04356 (2022-12-06). The model card's legacy benchmark numbers do not establish German quality on the target device.

**Architecture comparison:** unlike the small English-only online Zipformer in R-094, Whisper tiny is multilingual but the `whisper.cpp` CLI path is batch-oriented, not a true streaming transducer. Chunking/overlap may preserve responsiveness only with measured context and latency; it must be treated as a slower background teacher/fallback, not the RAW EAR or full-duplex voice path. Its ~273 MB estimate may be feasible in isolation but concurrent B1/B2/C3 RSS is unknown.

**Code implication:** the teacher-ear contract now accepts timestamped text spans without requiring a confidence field; uncalibrated decoder scores must not be converted into a fabricated 0..1 confidence. Provenance stays `CALLER_ASSERTED_UNVERIFIED`, source-bound to exact PCM, and transcript text remains ephemeral. The same adapter can later accept sherpa-onnx or whisper.cpp outputs without selecting either model.

**Next experiment:** only after explicit model-download approval, compare the 20M Zipformer int8 online model and Whisper tiny multilingual on the same consented English/German PCM corpus. Measure WER/CER, first partial/first final latency, real-time factor, peak RSS, CPU/thermal and overlap/barging-in behavior; retain the previous slot and no production swap until Redmi tests pass. No model or dependency was downloaded in this run.

**Boss reconciliation note (2026-11-22):** R-094 and R-095 were copied from the exact Perception branch readback for PR #2369. They remain research/adapter findings only; no ASR model, dependency or weights were downloaded. The separate R-092 AudioRecord / JEPA paper identifier collision remains unresolved; the requested JEPA R-093 rename has not been verified, so neither R-092 entry is overwritten.


## R-096 — Stochastic engram gating for sparse continual-learning bodies (2026-11-23)

**Primary paper read in full:** Isabelle Aguilar, Luis Fernando Herbozo Contreras, and Omid Kavehei, [*Stochastic engrams for efficient continual learning*](https://doi.org/10.1063/5.0346731), *APL Machine Learning* 4, 046108 (2026). Submitted 2026-06-04, accepted 2026-10-26, published online 2026-11-06. This is a peer-reviewed journal article. Article text is CC BY 4.0.

**Mechanism:** an input-conditioned two-layer encoder produces a compressed context vector; separate projections create per-layer gating probabilities. Training keeps the top-k probabilities (the paper commonly uses 20% active units) and samples Bernoulli masks; deterministic inference activates the top-k units. A straight-through estimator propagates gradients through the stochastic gate. The gate is trained jointly with a metaplastic binarized network, so sparsity and retention are coupled rather than a frozen external router. The paper also uses a fixed replay buffer (2,000 samples in the reported CIFAR experiments) and compares task-agnostic class/domain-incremental settings.

**Reported evidence:** the Split-MNIST 5-task/2-class result reports 72.65% ACC and 76.31% weighted ACC for engramBNN, versus 15.83% / 8.18% for vanilla BNN and 29.94% / 11.84% for mBNN. The paper reports 6,429,877 parameters and 3.02 MiB inference-weight storage versus 24.53 MiB for its same-architecture full-precision counterpart. Its peak GPU/RAM table was sampled by Weights & Biases every 10 seconds during PyTorch training on a system with about 17 GB GPU memory; those percentages are not Android RAM or CPU measurements. The paper itself says more complex real-world tasks, better backbones and edge-device inference benchmarking remain future work.

**OSS and license audit:** the linked [NeuroSyd/engramBNN](https://github.com/NeuroSyd/engramBNN) repository is AGPL-3.0 at exact main HEAD `0b8e5659695d5c7508a15cfc8062e79f8ee9b351`; that commit creates `LICENSE.md`. Its README still cites the 2025 arXiv preprint, and its last repository commit is 2025-04-08, so the repository is not demonstrated to be the exact 2026 journal implementation. Pinned requirements include torch 2.0.0, torchvision 0.15.1 and pytorch-lightning 1.5.10. No code was copied or dependency added. The paper's CC BY article license does not change the separate AGPL code license.

**V14 mapping / testable adaptation:** this is a strong architecture candidate for the two deliberately different B1_DETAIL/B2_GIST sparse-MoE bodies and potentially A3's trainable projector: each body may learn its own context encoder and per-layer sparse masks, while keeping body weights, expert capacity, goals and update rules independent. It does **not** justify sharing one gate across B1/B2 or replacing their distinct roles with a single router. Before adoption, prototype a tiny gate with 10/20/30% active units and compare dense, static top-k, stochastic learned top-k and no-gate controls on sequential source-bound tasks. Require gradient flow, numeric parameter diffs, active-unit distribution/load balance, task accuracy, old-task retention, OOD, update time, peak RSS and checkpoint/restart/rollback. Keep the gate trainable; do not infer a 1B-model or Redmi memory saving from the 3.02 MiB classifier result.

**Synthetic prototype (not paper reproduction):** `v14/experiments/engram_gate_probe.py` and `test_engram_gate_probe.py` implement a tiny full-precision context-conditioned top-8 gate, a fixed top-8 mask and an 8-unit dense comparator. On LOCAL_LINUX Python 3.13.5 / PyTorch 2.10.0+cpu, 10 seeds, 512 examples/task, 12 epochs/task, the three focused tests passed. Learned-gate maximum gradient L2 was 0.1977 ± 0.0267 and gate-parameter L1 delta was 84.7361 ± 4.0899. The learned gate produced zero majority-mask Jaccard between the two contexts and context-flipping reduced old-task accuracy to 0.4967 ± 0.0258. New-task accuracy was 0.9688 ± 0.0071 versus 0.8563 ± 0.1002 dense and 0.8801 ± 0.0867 static top-k. Old-task final accuracy was 0.7473 ± 0.0295 versus 0.7486 ± 0.0552 dense and 0.7467 ± 0.0479 static; this does **not** establish a retention gain. The full result is recorded in `v14/experiments/results/engram_gate_probe_20261123.json`. The experiment has no BNN, replay or metaplasticity and is only a routing/gradient sanity check.

**Status:** PEER_REVIEWED_MECHANISM / ARTICLE_LICENSE_VERIFIED / OSS_AGPL3 / NO_CODE_IMPORT / NO_ANDROID_BENCHMARK.


## R-097 — Orion: joint online resource control for replay-based continual learning (2026-11-23)

**Primary paper read in full:** Zexin Li, Nikil Dutt, and Cong Liu, [*Orion: Enabling Self-adaptive Memory Management for On-device Online Continual Learning*](https://arxiv.org/abs/2605.26473), arXiv:2605.26473, submitted 2026-05-26. The author publication page lists it as in submission to TECS; peer-reviewed acceptance was not established in this review.

**Mechanism and evidence:** Orion's URGE controller coordinates batch size, replay-buffer allocation, optimization strategy and data prefetch using plasticity, stability, training latency and memory pressure. The paper evaluates ER, GSS, GEM and AGEM across five OCL benchmarks and three backbones, with three seeds, on an edge server, a 32-GB NVIDIA Jetson AGX Orin and the same board under an emulated 8-GB budget. It reports every run fitting the enforced memory budget, roughly 9x faster training than Avalanche defaults on the Orin, and +9.4 percentage points average final accuracy over the default configuration where all methods fit. These are supervised image-classification results, not Android phone or language-model measurements.

**Limitations:** the paper excludes non-replay OCL, NLP, large-scale ImageNet/CLOC and infinite streams; it assumes labels. A static configuration selected through offline tuning still outperforms Orion on some long CORe50 streams. The paper reports that its decaying time-dependent threshold can hurt the longest stream. Therefore neither its scalar controller nor its thresholds should be copied uncritically.

**OSS audit:** no official public Orion implementation repository was identified. The paper builds on Avalanche; [ContinualAI/avalanche](https://github.com/ContinualAI/avalanche) is MIT-licensed, but Avalanche is a research/training framework, not an Android runtime dependency. No code or dependency was imported.

**V14 mapping / testable adaptation:** implement a measured, reversible resource governor that observes available memory, process RSS/PSS, per-organ CPU time/queue delay, TTFT/prefill and learning/retention metrics, then reallocates *compute and replay budget* without disabling canonical organs. Hard memory caps must dominate the optimizer; use hysteresis and restart-safe snapshots. Benchmark fixed versus adaptive budgets on the same replay stream, with OOM/negative controls and old-task holdout. Do not equate Jetson's emulated 8 GB with the Redmi's historical 5.84-GB total RAM / 1.78-GB available estimate; fresh Redmi measurements are required.

**Status:** FULL_PREPRINT_REVIEWED / AUTHOR_PAGE_SAYS_IN_SUBMISSION / NO_ORION_CODE_FOUND / DESIGN_REFERENCE_ONLY.


## R-098 — DLER dual-logit replay and memory selection (2026-11-23)

**Primary paper read in full:** Huiwei Lin, Shanshan Feng, and Kong Aik Lee, [*DLER: Dual-Logit Experience Replay for Online Continual Learning*](https://arxiv.org/abs/2611.04885), arXiv:2611.04885, first submitted 2026-11-03. This review found an arXiv preprint; a peer-reviewed venue was not established.

**Method and evidence:** DLER separates cosine/angle logits from dot-product logits. Current samples use cosine supervision to acquire new classes; replay samples additionally use dot-product supervision to preserve norm information. A supervised-contrastive term improves class compactness, and its memory updater prefers samples whose dot-product probability for the correct label exceeds the cosine probability. It reports 10-run means with 95% confidence intervals on Split CIFAR100, MiniImageNet and TinyImageNet; gains over the strongest baseline range from 0.1 to 3.9 percentage points across the reported buffer sizes. The setting is supervised class-incremental image classification with explicit labels and fixed replay budgets.

**OSS audit:** the linked [FelixHuiweiLin/UER](https://github.com/FelixHuiweiLin/UER) main HEAD is `bcc43a7200214b005d936f41bef9080fed8290b3`. Its README describes DLER, but no LICENSE file was present at the reviewed revision. Its requirements pin torch 1.7.1, torchvision 0.8.2 and other 2020-era packages. No code was copied; do not reuse until license and dependency compatibility are resolved.

**V14 mapping / testable adaptation:** DLER's useful idea is to make replay selection depend on a measurable *difference between two predictive views*, not just recency or uniform reservoir sampling. A V14 experiment could compare baseline reservoir replay with a source-bound retention score derived from a current predictor and a stable/EMA predictor, but only where both have a grounded target or independently verified outcome. Do not directly apply class logits to JEPA latent prediction or free-form language. Compare equal memory budgets, gradient conflict, held-out old/new utility, OOD and post-restart retention; keep all raw conversation/audio/video data out of replay absent separate explicit consent.

**Status:** FULL_ARXIV_PREPRINT_REVIEWED / REPO_FOUND_NO_LICENSE / NO_CODE_IMPORT / CLASSIFICATION_ONLY_EVIDENCE.


## R-099 — Attention changes distributed auditory prediction-error representation (abstract-only) (2026-11-23)

**Primary source reviewed:** Juho Äijälä et al., [*Attention reshapes the information dynamics of thalamic and cortical prediction-error learning*](https://doi.org/10.64898/2026.07.10.737794), bioRxiv preprint posted 2026-07-11 (v2 posted 2026-07-14). The preprint is CC BY-NC-ND 4.0. Only the abstract and metadata were reviewed in this run; the full paper was not read and no code repository was identified.

**Abstract-level finding:** the study reports intracranial sEEG from 17 patients performing a roving auditory oddball task under attended/unattended conditions. Using mutual information and co-information, it reports that distraction reduces thalamic prediction-error information while temporal-cortex responses follow different learning trajectories and change their balance of redundant/synergistic information. The abstract argues that attention reshapes *where and how* prediction-error evidence is represented, rather than simply scaling one global error signal. This is a human intracranial study and does not establish a deployable algorithm.

**V14 mapping / testable hypothesis:** keep A4 attention/salience and A5 timed raw-ear evidence as separable, source-bound signals; do not reduce attention to one scalar multiplier or overwrite acoustic evidence with ASR text. A future consented/synthetic test should compare attended versus competing/noise conditions, retain timing/provenance and measure whether different perceptual streams contribute complementary information. Treat this as a research hypothesis only until the full paper and a reproducible model are reviewed.

**Status:** ABSTRACT_ONLY / PREPRINT / CC_BY_NC_ND / NO_CODE / NO_IMPLEMENTATION_CLAIM.


## Boss integration note — 2026-11-23T00:05:08.222Z

PR #2387 was merged into the Boss documentation branch only. R-096–R-099 remain research records, not runtime features: R-096 is a peer-reviewed mechanism with CC BY 4.0 article text but no code import; R-097 is a preprint/design reference with no matching implementation found; R-098 is an arXiv preprint with repository license not established; R-099 was abstract-only and is CC BY-NC-ND 4.0. No model, dependency, weights, Android provider or learning path was imported. No retention gain, latency gain or Android benchmark is claimed. Any follow-up must be a bounded, falsifiable V14 experiment with license and resource checks.


## R-100 — sherpa-onnx 2.0.3: CPython 3.14 Android ARM64 wheel feasibility (2026-11-23)

**Primary upstream/revision:** `k2-fsa/sherpa-onnx` release `v2.0.3`, released 2026-11-22 at upstream commit `38016c6` (GitHub release marks the tag commit verified). The project repository and PyPI `sherpa-onnx` package identify Apache-2.0. Upstream describes offline local streaming/non-streaming ASR, TTS, diarization, speaker verification, VAD and other audio tasks, including Android support. This is runtime feasibility evidence, not a model-quality result.

**New Android Python packaging evidence:** PyPI lists `sherpa_onnx-2.0.3-cp314-cp314-android_24_arm64_v8a.whl` at 2.7 MB (uploaded 2026-11-22), tagged CPython 3.14 / Android API 24+ / ARM64-v8a. The matching `sherpa-onnx-bin 2.0.3` Android ARM64 wheel is 10.2 MB; `sherpa-onnx-core 2.0.2` lists an Android ARM64 wheel at 10.3 MB. All three releases currently show **no PyPI provenance/attestation**. These are runtime-package artifacts, not acoustic model weights. The package dependency closure and actual installed footprint must be confirmed from metadata before summing sizes or pinning them.

**Model/resource boundary:** the previously audited `sherpa-onnx-streaming-zipformer-en-20M-2023-02-17` is a small English-only candidate; it does not solve German speech. The official model catalogue lists other language-specific streaming models and Chinese/English X-ASR variants, but the cited X-ASR int8 model is 134 MB and does not cover German. A multilingual Whisper tiny route is larger and batch-oriented. Do not present the Python wheel as a model or as proof that the desired German/English voice path is solved. Model-weight and training-data licenses must be audited separately from the Apache-2.0 runtime.

**V14 adaptation / next hard test:** candidate for an isolated, opt-in Termux compatibility experiment only. First read `sysconfig.get_platform()`, `packaging.tags.sys_tags()`, Python version, Android API and ABI on the actual device; verify that pip accepts the `android_24_arm64_v8a` tags and that every ELF dependency resolves against Bionic (not glibc). Then install only into a disposable venv, import the exact pinned package trio, and run a fixed local WAV through a tiny streaming model with no network or persistence. Record wheel hashes/provenance, dependency closure, cold/warm initialization, chunk latency/RTF, peak RSS, CPU/battery, silence/noise/music negatives and English/German holdout quality. Keep raw audio local and separately consented. Compare against the current caller-supplied Teacher Ear contract; do not change normal Runtime, model weights, or user data before explicit approval.

**Limitations:** a PyPI platform tag does not prove compatibility with Termux's exact Python build, Bionic linker, Android lifecycle or Redmi hardware. The wheel files are published without provenance attestations. No wheel, dependency, model or weight was downloaded or installed in this review; no Termux/Redmi benchmark was performed.

**Status:** UPSTREAM_RELEASE_AND_WHEEL_METADATA_VERIFIED / APACHE_RUNTIME_LICENSE / NO_PROVENANCE / CANDIDATE_ONLY / NOT_INSTALLED / REDMI_UNVERIFIED.


## R-101 — Exact source-level unlearning for standardized A3 ridge projectors (2026-11-23)

**Primary paper read in full:** Yijun Quan, Wentai Wu and Giovanni Montana, *Exact Federated Continual Unlearning for Ridge Heads on Frozen Foundation Models*, arXiv:2603.12977v3 (revised 2026-06-14; https://arxiv.org/abs/2603.12977v3). Accepted to the **ECML PKDD 2026 Research Track** and published as a Springer conference paper, LNCS/LNAI volume 16946, pp. 114–131, first online 2026-09-05, DOI https://doi.org/10.1007/978-3-032-37673-2_7 (https://link.springer.com/chapter/10.1007/978-3-032-37673-2_7). The proceedings describe themselves as refereed. Springer lists the chapter under exclusive license to Springer Nature; no official open-source code repository was identified, no code/weights were imported, and no permissive code license is inferred.

**Method:** for a fixed feature extractor and a ridge-regression head, the optimum depends on additive sufficient statistics S=FᵀF and G=FᵀY. The paper maintains these through add/delete requests and recomputes the exact retained-data head; Variant A uses a full fp64 solve, while Variant B uses QR/Sherman–Morrison–Woodbury updates with feasibility and periodic-reset considerations. Its Bayesian section derives a zero-KL retrain-equivalence certificate when the tracked statistics are exact.

**Reported evidence and limits:** four supervised benchmarks (CIFAR-10/100, FeMNIST and Sentiment140), DINOv2 or RoBERTa 768-dimensional frozen features, 100 simulated clients, and experiments on a server with 4 NVIDIA RTX A6000 GPUs. The authors report fp64 relative Frobenius deviations around 1e-9 versus centralized ridge retraining and test 200 sequential deletion requests plus add-back. This is not a mobile benchmark. The guarantee removes influence from the ridge head only; it does not unlearn a backbone or teacher that was itself trained on the deleted source. The paper also notes second-order statistics can leak feature-distribution information.

**A3 mapping:** V13 vision.Projector.fit is a closed-form ridge head over deterministic visual features and text-embedding targets, but it first standardizes X using data-dependent mean/std and uses an unregularized bias. Plain S/G therefore needs extra first moments. For the current fit, source-level n, sx=sum(X), S=XᵀX, sy=sum(Y), G=XᵀY are sufficient to reconstruct the exact standardized system: mu=sx/n, sigma=sqrt(max(diag(S)/n-mu²,0))+1e-6, H=(S-sx sxᵀ/n)/(sigma sigmaᵀ), C=(G-mu syᵀ)/sigma, W_feature=(H+lambda I)^-1 C, W_bias=sy/n. This assumes the feature extractor, text encoder revision, preprocessing and target rows remain fixed and source-bound.

**LOCAL_LINUX synthetic equivalence probe:** CPython 3.13.5 / NumPy 2.3.5. Across 600 delete/add-back comparisons (d=37 with target dimensions 256 and 768, plus d=12/c=16; seven synthetic source groups per seed; zero-variance feature stress included), maximum relative parameter error against a fresh Projector.fit was 6.72e-10, p99 5.86e-10, and maximum normalized-output relative error 1.39e-15. A separate 128-source / 2,048-sample / d=37 / c=256 CPU microbenchmark stored 89,080 bytes of fp64 sufficient statistics per source (10.87 MiB total); mean delete-update solve time over 100 warmed repetitions was 1.28 ms versus 2.54 ms for full refit on retained samples. These are local synthetic/CPU results, not real image accuracy, Android latency, RSS or Redmi evidence.

**V14 consequence:** keep PR #2395's conservative invalidation as the safe first step. After the JEPA source-lifecycle overlay and QA pin chain consume that fix, prototype per-source fp64 sufficient-stat artifacts so an explicit forget can subtract one source and reconstruct the remaining A3 head without retaining raw image/audio data. Store encoder/preprocessing revisions and exact source hashes; delete per-source stats on forget; test delete/add-back, order invariance, restart, rollback, old-task retention and malformed/legacy fallback. Do not claim neural-backbone unlearning or permission to activate live learning.

**Status:** FULL_ARXIV_V3_REVIEWED / PEER_REVIEWED_ECML_PKDD_2026 / LOCAL_SYNTHETIC_STATS_EQUIVALENCE / NO_CODE_IMPORT / NO_ANDROID_PROOF.


## R-102 — Orion: adaptive memory allocation for on-device online continual learning (2026-11-23)

**Primary source:** Zexin Li, Nikil Dutt, Cong Liu, *Orion: Enabling Self-adaptive Memory Management for On-device Online Continual Learning*, arXiv:2605.26473v2 (v1 2026-05-26; v2 2026-11-02). Full-text design, evaluation and limitations sections reviewed: https://arxiv.org/abs/2605.26473 . This remains an arXiv preprint; no peer-reviewed venue was established in this review.

**Method:** Orion's URGE controller combines plasticity, stability, per-sample training latency and memory headroom into a dimensionless runtime signal. It reallocates memory between training batch, replay buffer and optimization plugins under a hard memory cap. It also profiles process RSS plus accelerator allocator reserve on unified-memory Jetson and uses a watchdog; the prototype extends Avalanche with parallel data loading/prefetching. This is a systems-level controller, not a new JEPA objective or a replacement for replay, EMA or local plasticity.

**Evidence:** five continual-learning benchmarks, four replay-based algorithms, three backbones, three memory regimes (RTX A4500 server, Jetson AGX Orin 32 GB, and that Orin under an emulated 8 GB budget), three seeds, plus a TurtleBot 3/Endless-Sim case study. The paper reports Orion completed all runs within its budget; on Jetson it was 9.0× faster than Avalanche defaults in the main comparison, and the 8 GB-budget CORe50-NIC run stayed at 7.1 GB while fixed MAX-P reached 9.6–11.2 GB and OOMed. The watchdog samples every 50 ms. These are Jetson/benchmark results, not Android/Redmi measurements.

**Limits:** replay-based supervised OCL only; no NLP, large ImageNet-scale data or infinite streams; labels are assumed available. The authors report cases where offline-tuned static configurations remain more accurate, and a time-decaying threshold hurts the longest stream. No Orion source repository or code license was identified. The underlying maintained [ContinualAI/Avalanche](https://github.com/ContinualAI/avalanche) library is MIT-licensed, but that does not grant a license to unlocated Orion-specific code.

**V14 implication:** the transferable idea is a separate resource governor with hard memory enforcement and per-consumer budgets—not wholesale Avalanche/PyTorch reuse on Android. For V14, first collect actual per-organ RSS/peak memory, queue latency, training batch/replay size and validated retention/plasticity signals; then test adaptive allocation against a fixed baseline with OOM, latency, retention and restart controls. Do not infer Orion's 8 GB Jetson result will fit the Redmi's ~5.84 GB total RAM or its much smaller historically available headroom. No code/weights imported; no package installed.

**Status:** PREPRINT_FULLTEXT_DESIGN_EVALUATION_REVIEWED / JETSON_32GB_AND_EMULATED_8GB_EVIDENCE / NO_ORION_CODE_FOUND / AVALANCHE_MIT_ONLY / NO_ANDROID_PROOF.

## R-103 — Streaming user transcription as a parallel full-duplex head (2026-11-23)

**Primary source:** Ke Hu, Nourchene Ferchichi, Edresson Casanova, Ankita Pasad, Elena Rastorgueva, Chen Chen, Nithin Rao Koluguri, Piotr Zelasko, Yifan Peng, Hainan Xu, Zhehuai Chen and Boris Ginsburg, *Enabling Streaming User Transcription in Full-Duplex Speech-to-Speech Models*, arXiv:2609.15759v1, submitted 2026-09-14. Full arXiv HTML reviewed: https://arxiv.org/abs/2609.15759 and https://arxiv.org/html/2609.15759v1 . No peer-reviewed venue or released code repository was identified at this review. The arXiv distribution license is not a software or weight license.

**Architecture:** a 600M-parameter Parakeet streaming encoder emits embeddings every 80 ms into a shared decoder backbone, with separate user-ASR and agent-text embedding/prediction heads. The ASR head predicts user transcript tokens from shared hidden states in parallel with the agent text head; word-level targets are aligned from audio using CTC/MMS-FA forced alignment. Reported delays are 1.2 s for user transcript and 0.16 s for agent text. This keeps recognition output distinct from the agent's own response channel.

**Reported results and limits:** the integrated duplex system reports 10.21% average WER, 90% turn-taking precision / 95% recall with 431 ms latency, and 100% barge-in accuracy with 374 ms latency on the authors' evaluation. The standalone variant reports 7.73% average WER at 1.6 s delay. However, the integrated system uses a 9B Nemotron-Nano-9B-v2-Base backbone plus the 600M encoder; the standalone configuration also evaluates a 1.5B Qwen2.5 backbone. Training uses 16k hours of English ASR data plus internal data, and turn-taking results include a limited internal conversation set. The paper does not quantify the ASR head's complete incremental memory/energy cost for Android, and the authors say code will be open-sourced rather than linking a released repository.

**V14 implication:** this supports the existing separation between timestamped RAW EAR/acoustic features, optional user-transcript/Teacher Ear output, agent language planning and the speech effector. It does not justify replacing the raw ear with transcript-only input, nor is its 9B/600M system a Redmi model candidate. A later small-model experiment should compare a separate causal ASR head/decoder against a staged fallback while preserving prosody, speaker and non-speech signals, with explicit transcript consent, alignment, barge-in and end-to-end latency metrics. No code/weights imported; no model downloaded.

**Status:** FULL_ARXIV_HTML_REVIEWED / PREPRINT / ARCHITECTURE_RELEVANT / MODEL_TOO_LARGE_FOR_REDMI_TARGET / NO_CODE_OR_WEIGHT_LICENSE / NO_ANDROID_PROOF.


## R-104 — FASTDIAR causal frame-level speaker embeddings: code/weight/license audit (2026-11-23)

**Primary paper:** Nikita Torgashov and Okan Köpüklü, *FASTDIAR: Frame-level speaker encoder for Streaming Diarization*, arXiv:2610.02941v1, submitted 2026-10-02 to IEEE ICASSP 2027 (preprint; no acceptance established). Full arXiv HTML reviewed: https://arxiv.org/abs/2610.02941 . The encoder is causal with a two-second past receptive field, emits normalized 192-D embeddings every 80 ms, and uses confidence-gated online clustering with a fixed 960 ms output delay. It runs at RTF 0.19 on one AMD Threadripper PRO 5995WX CPU thread in the reported experiment.

**Evidence and limits:** without overlap, FASTDIAR reports 12.35% DER on VoxConverse and 21.61% on RAMC; it is not the best system across all six benchmarks and is last on DIHARD3 in the reported comparisons. With overlap counted, it loses to Streaming Sortformer on NOTSOFAR, DIHARD3, AMI and MSDWild. One label per frame makes overlapped speech a miss. VoxConverse and NOTSOFAR development sets were used for checkpoint selection/threshold tuning; four other evaluation sets were untouched. The paper is submitted to ICASSP 2027, not a peer-reviewed acceptance claim.

**OSS/license audit:** official [microsoft/fastdiar](https://github.com/microsoft/fastdiar) release v0.1.0 points to signed commit `e7f9bbccf98865216f48a04868d74f1d53c8734e` (2026-10-03). The repository code is MIT-licensed (LICENSE blob `9003ea9e9eace590d66dfa2941266e463d75606c`). The release contains small/medium/large checkpoints of 2.4M/4.6M/10.4M parameters, but neither README nor release text found here states a separate checkpoint-weight license; **do not infer weight rights from the MIT code license**. The official requirements pin PyTorch 2.13.0, torchaudio 2.11.0, torchcodec 0.15.0, NumPy 2.2.6, SciPy 1.15.1, Silero VAD 6.2.1, pyannote metrics/database/core, Lightning, PyArrow and other packages. The README documents CPU inference but its default pinned PyTorch wheels are CUDA 13 builds; no Android/Termux/Bionic dependency closure or ARM64 wheel support was established.

**V14 code boundary:** current `audio_fastdiar_adapter.py` (pinned to the exact v0.1.0 commit) only wraps a caller-supplied `(n_frames, 192)` matrix, hashes the local checkpoint file and exact PCM chunk, and emits the RAW EAR speaker-evidence shape. It does **not** load/download weights, execute the encoder, run VAD/clustering, assign identities, persist vectors, or supply calibrated confidence; A4 remains DEFER. The adapter therefore is not yet a working native FASTDIAR perception path.

**Next test:** only after separate explicit approval for a disposable local/Termux experiment and a verified weight license, test the exact pinned checkpoint with the complete CPU dependency set; record model/checkpoint hashes, RTF/80 ms frame latency, RSS, speaker-change delay, DER with/without overlap, negative silence/noise cases and restart behavior. No weight/model was downloaded or loaded in this review; no Redmi measurement.

**Status:** FULL_ARXIV_PAPER_REVIEWED / ICASSP_2027_SUBMISSION / MIT_CODE / CHECKPOINT_LICENSE_UNSPECIFIED / CPU_THREADRIPPER_ONLY / ADAPTER_DIAGNOSTIC_NOT_INFERENCE / REDMI_UNVERIFIED.

## R-105 — Embedder-centric multi-scenario on-device learning (2026-11-23)

**Primary paper:** Douwe den Blanken, Martin Lefebvre and Charlotte Frenkel, *Versatile On-device Adaptation at the Edge by Unifying Few-shot, Zero-shot, Continual, and In-context Learning*, arXiv:2607.29353v1, submitted 2026-07-31 (the paper states it was submitted to IEEE; no peer-reviewed acceptance established here). Full arXiv HTML reviewed: https://arxiv.org/abs/2607.29353 .

**Method and evidence:** Embedder-Centric Learning (ECL) separates an input embedder from small scenario-specific heads. It uses temporal convolutional networks (TCNs) to handle sequential audio, pixel streams and tokens, then supports prototypical few-shot learning, class-incremental continual learning by appending class parameters, semantic zero-shot learning with a relation head, and sequence in-context learning. The authors report Chameleon-SoC hardware results: 71.8% final accuracy for 200-class keyword FSCIL with a 58.2 kB embedder and 6.4 kB class embeddings at 9.5 µW / 1 s per sample; 60.6% 5-way spoken-sentence ZSL; and 46.2% RegBench accuracy at token 500 with 2.15 ms/token. The software ICL model uses 9.2 kB activation memory versus 288 kB for the parameter-matched Transformer in the reported task.

**Limits:** These are small benchmark tasks on a custom Chameleon ASIC, not an Android ARM CPU/GPU test. The paper explicitly reports a 19.6-point ZSL accuracy drop for the 4-bit log-weight format versus FP32 (6-bit loses 5.8 points); the authors identify quantizer-sharing and low-bit effects. The paper's GitHub link is cogsys-tudelft/ecl, but its separate repository license and model-weight license were not verified. The related public cogsys-tudelft/chameleon repository states Apache-2.0 for non-HDL source and Solderpad Hardware License v2.1 for HDL; that does not establish the license of the separate ECL repository or any checkpoint weights. No code or weights imported.

**V14 implication:** Treat the embedder/head split as a candidate for reducing duplicated adaptation machinery: keep modality-specific encoders and the distinct B1/B2/RAW EAR/RAW EYE organ identities, but evaluate compact scenario-specific heads (few-shot, incremental, semantic, temporal prediction) over their own validated embeddings. Do not collapse the distributed architecture into one universal encoder, and do not infer that a 4-bit quantized head will retain quality. A future comparison should measure parameter/activation memory, update latency, class/semantic retention, source deletion, restart and rollback against the existing ridge/projector and JEPA paths on the same held-out sequence.

**Status:** FULL_ARXIV_HTML_REVIEWED / SUBMITTED_NOT_PEER_REVIEWED / CUSTOM_ASIC_EVIDENCE / SEPARATE_ECL_LICENSE_UNVERIFIED / NO_WEIGHT_LICENSE / NO_ANDROID_PROOF / RESEARCH_ONLY.


## R-106 — Moonshine v2 German Tiny as a candidate streaming Teacher Ear (2026-11-23)

**Primary paper read in full:** *Moonshine v2: Ergodic Streaming Encoder ASR for Latency-Critical Speech Applications*, arXiv:2602.12241v1, submitted 2026-02-12 (preprint; no peer-reviewed acceptance established in this review): https://arxiv.org/abs/2602.12241 and full HTML https://arxiv.org/html/2602.12241 . The paper's evaluated Tiny model is the English 33.57M-parameter model; its Apple M3 result of 50 ms response latency after end-of-speech and 8.03% compute load is **not** a German-model or Android result. The paper describes a sliding-window streaming encoder with approximately 80 ms lookahead and a conservative finalization horizon up to 320 ms; these are architecture details, not a Redmi latency guarantee.

**Official German model card:** [moonshine-ai/moonshine-streaming-tiny-de](https://huggingface.co/moonshine-ai/moonshine-streaming-tiny-de), checkpoint `de12k_tiny_stageC_best.safetensors`, revision `928bfb9` / snapshot 2026-08-24. The card lists 27.0M parameters, a 12,288-token German vocabulary and MIT model license. Its seeded 400-utterance read-speech sample reports FLEURS WER 11.89 and MLS WER 10.92 (macro 11.405); the shipped int8 ONNX Runtime package reports 12.004 versus 11.086 for the float checkpoint under the same stopping rule. The model card describes training with roughly 103,000 hours of podcast pseudo-labels plus 3,700 hours of human-transcribed read speech. It warns about inherited teacher-label errors and repetition loops on short/noisy clips. This is two read-speech panels, not spontaneous conversation, heavy dialect, children's speech, overlapping speech or noisy far-field evaluation. The official card does not establish the complete on-device package size or Redmi RSS.

**Maintained OSS/runtime and license:** official [moonshine-voice](https://github.com/moonshine-ai/moonshine-voice) is MIT-licensed; its Android documentation currently publishes Maven artifact `ai.moonshine:moonshine-voice:0.1.5` (docs checked 2026-11-23): https://moonshinevoice.readthedocs.io/en/latest/ . The base `Transcriber.add_audio()` API accepts caller-supplied mono chunks at different sample rates and exposes provisional text changes and completed-line events; its default update interval is 500 ms. A direct microphone helper (`MicTranscriber`) also exists, but V14 must **not** use it: audio capture stays in the separate, visible, OS-permissioned AudioRecord provider, and only approved PCM is passed to the transcriber. Keep optional speaker identification disabled; it is not required for transcript hypotheses and would add another model/authority path. The model card's MIT weight license is separate from any training-corpus redistribution rights, which were not established here.

**V14 mapping:** this is a promising German streaming Teacher-Ear candidate because it can consume the existing timestamped PCM feed and emit provisional/final text without replacing RAW EAR. The adapter must preserve the exact PCM source hash, generation, start/end timestamps and model revision; transcript use remains independently opt-in and ephemeral. Raw prosody, speaker evidence, non-speech events and A4 salience remain primary acoustic inputs. No transcript may become ground truth, a learning label or an action command merely because the teacher emitted it.

**Concrete experiment, only after explicit model approval:** compare this model against the existing sherpa-onnx Zipformer candidate and a multilingual Whisper Tiny baseline on a fixed, consented conversational German corpus plus clean read-speech controls. Use the official Android `Transcriber.add_audio()` path with 500 ms externally captured PCM chunks. Measure WER/CER, first partial latency, finalization latency, memory/RSS/PSS, CPU, thermal drift, chunk-drop/restart behavior and repetition failures under short/noisy/overlap controls on the actual Redmi. Verify the official model package size and all transitive Android ABIs before download. Do not add the Maven dependency, download weights, change the active model or swap production models before separate explicit approval for the experiment and any later production swap.

**Status:** FULL_PREPRINT_REVIEWED / OFFICIAL_GERMAN_MODEL_CARD_REVIEWED / MIT_MODEL_AND_RUNTIME / READ_SPEECH_ONLY_EVIDENCE / ANDROID_API_DOCUMENTED / PACKAGE_SIZE_AND_REDMI_PERFORMANCE_UNVERIFIED / NO_DEPENDENCY_OR_WEIGHT_DOWNLOADED / CANDIDATE_ONLY.


## R-107 — Future-Aware Recall for predictive episodic memory selection (2026-11-23)

**Primary paper reviewed in full:** Beomsu Kim, Chieh-Hsin Lai, Bac Nguyen, Amir Bar, Jong Chul Ye and Yuki Mitsufuji, *Learning What to Recall: Adaptive Multi-Cue Episodic Memory for World Models*, arXiv:2609.34677, submitted 2026-09-28: https://arxiv.org/abs/2609.34677 . The method, experiments, implementation details, appendices and stated limitations were inspected. This is an arXiv preprint; no peer-reviewed venue was established in this review.

**Method and evidence:** Future-Aware Recall (FAR) uses the realized future only during training to estimate candidate-memory predictive utility, then distils that utility into a retriever that is future-blind at inference. Its candidate posterior combines the current query-conditioned retrieval score with predictive utility; the retriever is trained against that posterior with a stop-gradient KL objective. It learns query-dependent weighting of heterogeneous cues (e.g. time/pose/vision/audio), caches historical cue keys, and constrains Top-K retrieval to at most one item per temporal chunk to reduce redundant neighboring memories. The video instantiation estimates predictive utility with negative diffusion denoising loss using shared noise/timestep perturbations for candidate comparisons, and updates the retriever lazily rather than on every generator step.

The reported results cover controlled LoopNav, SoundSpaces and AI2-THOR settings. Examples include adaptive metadata+audio gains under sparse/long SoundSpaces returns and 94.6% off-scene moving-agent prediction for Multi-Cue FAR versus 67.1% metadata-only, 41.9% temporal and 32.4% WorldMem in that particular AI2-THOR-dyn task. These are paper results, not V14 reproduction or Android evidence. The authors explicitly leave memory writing, compression, forgetting and higher-order interactions to future work; they also note that the diffusion-loss surrogate can miss semantically important local changes and that evaluation is in controlled simulations.

**OSS / license / resource audit:** public implementation sony/far, main revision cab815ac2375f6bf38b846ff5a76216de9edbf02, repository LICENSE blob fe463e0f7888bbf8b82e42d55f5743508ddafb7e, is CC BY-NC 4.0. Its requirements.txt pins a CUDA 12.8 stack including PyTorch 2.7, torchvision, diffusers, timm, LPIPS and related video/data tooling; README quickstart states approximately 2.4 GB demo downloads and about 14 GB GPU memory on an H100. The public checkpoints are described as inference-only. This is not an appropriate code/weight/dependency import for the low-resource Android runtime; no code, weights, datasets or dependencies were copied or downloaded. Use as a conceptual method reference only, subject to later license review if reuse is proposed.

**Concrete V14 adaptation hypothesis (not yet implemented):** after the current source-verified temporal JEPA retrieval path is stable, train a small query-conditioned cue-utility head over existing numeric, provenance-safe cues: learned temporal latent distance, episode age/spacing, action-transition compatibility, outcome-profile compatibility and modality/event-type compatibility. For each training query, use a later committed T8 ActionOutcome to score how much each candidate episode improves a held-out temporal prediction relative to a query-only baseline; construct a future-aware soft target from current retrieval score + measured predictive utility, then train the future-blind cue scorer. Inference must never read the future outcome used for credit assignment. Keep the current latent-distance retriever as baseline and compare recency, random, shuffled-future-credit, single-cue and learned multi-cue variants at matched candidate/compute budgets. Split by session and source cohort; exclude query sources and all holdout windows; test delayed-outcome leakage, omission/censoring, temporal chunk diversity, retention, source forget, checkpoint/restart and rollback. A candidate may enter the B1/B2 SHADOW prompt only if its held-out utility beats the existing baseline; no action authority or native-body-weight change follows from retrieval.

**Status:** FULL_ARXIV_HTML_REVIEWED / REPO_MAIN_REVISION_AND_CC_BY_NC_LICENSE_VERIFIED / SIMULATION_ONLY_PAPER_EVIDENCE / NO_REUSE / V14_CANDIDATE_PROPOSED / NO_ANDROID_PROOF. This entry does not claim FAR has been reproduced or that current V14 episodic recall already learns cue utility.


## R-141 — Cross-model activation similarity is not receiver utility (2026-11-25)

**Primary source:** Peiyan Zhang, *A Negative Result on Cross-Model Activation Transfer in a Pythia Multi-Hop Setting*, arXiv:2606.03280, submitted 2026-06-02: https://arxiv.org/abs/2606.03280

**Evidence level in this run:** ABSTRACT_VERIFIED_ONLY. The arXiv PDF/HTML endpoints were inaccessible from this run; the full methods, appendices, code and license were not inspected. Do not describe this as a full-paper review or independent reproduction.

**Reported abstract result:** a linear Pythia-160M → Pythia-410M translation reached normalized cosine similarity near 0.97, yet translated activation injection did not improve downstream multi-hop answering. Low-strength additive injection stayed near the no-injection baseline; replacement was destructive; norm rescaling did not recover utility. This is a scoped negative result for one model pair/task, not a universal impossibility theorem.

**V14 consequence:** this independently reinforces R-007/R-091's separation between representation alignment and useful communication. The current low-rank adapter's source-disjoint held-out MSE/shuffled controls can only produce an alignment candidate. A B3 acceptance gate still needs receiver-side task outcomes under exact-message, no-message, zero, shuffled, row-shuffled, repeat, parity and OOD controls; next-token/logit change alone is only evidence that input was consumed. No activation injection, training, model load or Redmi test was performed from this research.

**Reuse/licensing:** no repository, code license, dataset license or weight license was verified in this abstract-only review; nothing was reused or downloaded.


## R-143 — Receiver-side consumability and token-span alignment for latent exchange (2026-11-25)

**Primary paper reviewed in full:** Adam Deng, Shicheng Liu and Yada Zhu, *Augment the Cache, Replace the Activation: A 2x2 Study of Internal-State Sharing*, arXiv:2610.22026v1, submitted 2026-10-15: https://arxiv.org/abs/2610.22026 . The complete HTML paper, methods, results, appendix and limitations were inspected. This is an arXiv preprint; no peer-reviewed venue was established in this review.

**Method and evidence:** the authors compare two internal carriers (KV cache and residual-stream activations) under substitution/replacement versus augmentation. Their controlled fact-transfer probe uses Qwen2.5-1.5B (28 layers, width 1536, GQA group factor 6), SQuAD passages with the answer span masked from the receiver, 256-token prompts and 8 greedy answer tokens. The KV experiments use n=200; activation experiments use n=120. The paper includes native-forward parity/cache-rebuild gates, no-op, position, mis-source and answer-disjoint controls. Same-model KV substitution remains at the floor; query-side KV augmentation reaches 0.695 versus a 0.665 native reference, but the difference is not significant at the reported single-seed sample. Activation replacement at an oracle-aligned layer/position reaches 0.742 conditional accuracy versus a 0.20 floor; activation augmentation reaches 0.438. Wrong-position activation controls rise above floor at deeper injection layers, demonstrating that position is not a harmless detail.

**Critical boundary:** positive results are from one model family and use an oracle fact region/injection layer; they are not a deployable cross-model adapter recipe. The authors report cross-family GPT-Neo-1.3B → Qwen transfer collapsing to the control floor on both carriers. A single bridge generalizes only to very close same-family checkpoints with bit-identical tokenizers (reported nearest sender cosine 0.9994); the next sender at 0.9933 is indistinguishable from control. The authors also disclose one-seed results, noisy small-slice checkpoint selection, a cache-side copying confound that is reduced but not eliminated, and a multi-source control that can rise above floor. This is strong evidence for receiver-side task-utility and mis-source testing, not proof that activation replacement is universally superior.

**V14 consequence:** representation similarity, low held-out MSE, or changed next-token logits do not prove useful organ communication. The current B1/B2→C3 event-pooled adapter remains an alignment candidate only; it is not the paper's residual-stream replacement method. Future native acceptance must measure task outcomes on answer-disjoint/source-disjoint held-out tasks, with exact-forward parity, no-message, zero, shuffled, row-shuffled, mis-source, position and OOD controls, plus multiple seeds and retention. Same-family and cross-family results must be reported separately. KV sharing is a separate high-memory research path; do not substitute foreign KV tensors into receiver slots.

**Code change in this run:** tokenwise adapter schema v3 now has an explicit CHAR_SPAN_OVERLAP_V1 alignment path. align_token_rows_by_char_span() maps sender rows to receiver token spans using overlap-weighted aggregation, requires ≥0.80 character coverage, binds each source to SHA-256, and records an alignment digest plus sender/receiver tokenizer revisions. Tokenwise fitting rejects position-only pairs, overlapping spans, source-hash leakage, missing alignment evidence and mismatched receiver tokenizer revisions. The existing event-pooled schema-v2 path is unchanged. This is a necessary geometric alignment contract, not evidence of semantic transfer; production route remains false and semantic-use proof remains false.

**OSS / license:** no official code repository or model checkpoint was identified in the paper review; no third-party code, weights or datasets were imported. The arXiv HTML page states CC BY 4.0 for the paper. Model/data redistribution rights were not established by this review. No weights or dependencies were downloaded.

**Status:** FULL_ARXIV_HTML_REVIEWED / PREPRINT / CONTROLLED_QWEN_FAMILY_EVIDENCE / CROSS_FAMILY_NEGATIVE_RESULT / TOKEN_SPAN_ALIGNMENT_CODE_ADDED / LOCAL_FULL_REPO_TEST_NOT_YET_RUN / CI_PENDING / NO_NATIVE_MODEL_RUN / REDMI_UNVERIFIED.



## R-144 — Receiver context determines latent bandwidth: dense KV-cache alignment (2026-11-25)

**Primary paper reviewed in full:** Siyi Chen et al., *See What I See, Know What I Think: Dense Latent Communication Across Heterogeneous Agents*, arXiv:2606.13594v2. Version 1 submitted 2026-06-11; v2 last revised 2026-10-05. The complete 28-page PDF, method, benchmark tables, compute appendix, cross-family protocol and limitations were inspected. This is an arXiv preprint; no peer-reviewed venue was established in this review. Primary sources: https://arxiv.org/abs/2606.13594v2 and https://arxiv.org/pdf/2606.13594 .

**Method:** this is a KV-cache method, not a final-hidden-state or one-vector projector. It removes model-specific RoPE from sender keys, aligns layers and KV groups, applies separate per-receiver-group key/value MLPs plus learned gates, then restores receiver positional encoding. Training is two-phase: receiver-cache reconstruction (30,000 steps on OpenHermes for the six Qwen3 pairs) followed by receiver-generation supervision (2,000 steps on GSM8K, MATH-algebra and ARC-Challenge). Phase II mixes context-aware (receiver also sees the source input) and context-unaware (receiver has no source input) cases. When tokenizers differ, matching positions are chosen at shared character boundaries. Two independent document memories can be transformed and concatenated for a later receiver question.

**Evidence and boundaries:** evaluated six directed Qwen3 pairs among 4B/8B/14B on GSM8K, MATH-500, ARC-Challenge, MMLU-Redux, MedQA and OpenBookQA, plus Mistral-7B-Instruct-v0.3 → Qwen3-4B. In context-unaware Qwen3 tests, the method outperformed text-to-text and Cache-to-Cache in 33/36 task–pair comparisons; the reported Qwen3 accuracy ranges were 81.58–91.43% GSM8K, 64.00–81.60% MATH-500 and 86.86–93.60% ARC-C. This does not mean universal superiority: in context-aware results, text communication led on MMLU-Redux and five of six MedQA comparisons; Mistral→Qwen trailed text on held-out MMLU-Redux, MedQA and OpenBookQA. The compute comparison is an estimate based on a parameter×token rule of thumb and about 102 sampled examples per cell, not measured latency or end-to-end deployment cost. Estimated saved cache payload is about 27.2–30.2 MB/example; cache processing, transport and memory costs are not included in the FLOP estimate.

**V14 consequence:** the current LATENT_PREFIX_V1 receiver gets one event-pooled vector without the source text, so it is a context-unaware diagnostic. It is not equivalent to the paper's dense per-layer/per-KV-group cache, and the paper does not validate a one-vector event mean. Keep the current prefix route diagnostic-only. A future sequence/cache path must compare single-vector vs multiple token/span vectors and dense per-token state under both context-aware and context-unaware receiver tasks, with receiver-cache reconstruction and generation utility, source-disjoint holdout, exact-forward parity, no-message, zero, shuffled, row-shuffled, mis-source, position and OOD controls. Do not port this Qwen3 KV design directly into LFM2.5/llama.cpp or assume it fits Redmi; model geometry, native cache APIs, memory and ABI remain separate feasibility gates.

**Code translated in this run:** the read-only latent-alignment audit now reports sender/receiver nonzero-position residual-energy ratios after event-mean pooling. This quantifies within-event activation variation that one mean cannot reconstruct; it is explicitly descriptive only, not semantic information loss, task utility or proof of transfer. It uses existing source-bound tap blobs and does not load models or export vectors. Focused tests cover constant rows, varying rows and the persisted paired-tap audit.

**OSS/licensing:** arXiv lists the paper under CC BY 4.0 (paper attribution only); no official code repository was verified and the project page indicates code is not yet released. No model weights, code or datasets were imported. Qwen3/Mistral checkpoint licenses and OpenHermes/data redistribution terms were not re-evaluated here and must be checked independently before any reuse.

**Status:** FULL_PDF_REVIEWED / PREPRINT_V2 / DENSE_KV_METHOD_NOT_MOBILE_VALIDATED / EVENT_POOL_LOSS_AUDIT_ADDED / LOCAL_ISOLATED_FORMULA_REPRO_PASS / FOCUSED_CI_PASS_AFTER_FIXES / NATIVE_MODEL_TASK_UTILITY_NOT_RUN / REDMI_UNVERIFIED.

 
## R-145 — Tokenwise latent activation-row integrity (2026-11-25)

**Research basis:** This implementation is constrained by the full-paper review already recorded in R-007: Cardenas Piepereit, *Architecture-Dependent Causal Transfer of Activation States Across Large Language Models*, arXiv:2608.16347v2. That study found representational alignment/retrieval above chance for several decoder-only pairs, but only one of three decoder-only pairs showed a significant end-to-end causal injection effect; two other pairs had no causal effect despite similar representational alignment. R-144 separately reviewed dense per-layer KV-cache communication and explicitly distinguished it from a single event-pooled prefix. These results support keeping alignment, receiver effect and task utility as separate gates.

**Reproduced contract weakness:** the tokenwise alignment_sha256 previously bound source/span metadata and pair IDs, but pair IDs did not include the numeric sender/receiver activation rows. A vector could therefore change after alignment while the span metadata and alignment digest remained unchanged. This was a reproducibility/integrity gap, not proof that an external actor had altered data.

**Code change:** PR [#2501](https://github.com/RedMentos/Aii/pull/2501), v13/code/v13/latent_adapter.py. Each tokenwise row now gets canonical little-endian float64 SHA-256 digests for both sender and receiver activation vectors. The pair ID binds source ID/hash, token position/span, alignment ID/coverage and both activation digests. The aggregate alignment digest includes those row digests. fit_adapter() rejects a changed activation row and rejects a stale pair ID even if one row digest is recomputed. Event-pooled schema-v2 behavior is unchanged. This is content self-consistency, **not authenticity**: it does not replace a trusted tap producer, source-bound signed receipt, or exact persisted feature-blob binding.

**Exact evidence:** code/test SHA 6cc34b122caecfa340d36b08c9cc1e1bdbbbb2e2. GitHub Actions run [45630124154](https://github.com/RedMentos/Aii/actions/runs/45630124154): 37/37 tests PASS on Python 3.13 and 3.14, exact py_compile PASS, public privacy scan CLEAN. Runtime-deployment integrity run [45630124121](https://github.com/RedMentos/Aii/actions/runs/45630124121): offline Python 3.11 and 3.14 PASS. LOCAL_LINUX isolated helper reproduction: 3/3 PASS (different-tokenizer positive, post-alignment vector mutation negative, stale pair-ID negative). An earlier exact run on 4477cb7 failed four tests because new test fixtures omitted projection_scope=TOKENWISE and the source-hash leakage fixture still used the old pair-ID formula; both fixture issues were corrected and the exact 6cc34b1 run passed. Full local Aii checkout/pytest remains BLOCKED/NOT_RUN (no checkout mounted; local GitHub DNS unavailable).

**Acceptance boundary:** synthetic tokenwise vectors only. No real persisted tokenwise tap producer/cohort, native GGUF receiver pair, gradient/parameter update, held-out receiver task utility, retention, restart/rollback, Redmi/Termux test, deployment or release. Production B3 remains OFF. REDMI_UNVERIFIED / NOT_RELEASED.

**Next experiment:** Core must keep the separately typed LATENT_PREFIX_V1 event-pooled receiver path distinct from tokenwise schema-v3. Research + Core should add a trusted tokenwise tap export with exact sender/receiver packet IDs, feature blob hashes, event/generation, model/tap/tokenizer revisions, source hash and character offsets. Then compare event-prefix, aligned tokenwise rows, exact text and no-message/zero/shuffle/repeat/OOD controls on source-disjoint held-out receiver tasks. Do not promote on MSE/cosine alone.

 
## R-146 — S-JEPA stochastic residual latent and uncertainty (2026-11-25)

**Primary source read:** Nikos Giakoumoglou, Paschalis Giakoumoglou and Tania Stathaki, *A Stochastic Latent Variable Generalization of Joint-Embedding Predictive Architectures*, arXiv:2611.09302v1, submitted 2026-11-06. Main paper and the uncertainty/cost/limitations sections were read from the arXiv PDF. Status: arXiv preprint; no peer-reviewed publication status verified in the arXiv record. The PDF lists a code URL (github.com/giakomoglou/sjepa), but the repository could not be retrieved through the available GitHub connection at this access; license, model weights and dataset terms therefore remain UNVERIFIED. No code or weights were reused.

**Method:** S-JEPA replaces the deterministic auxiliary JEPA z with a stochastic per-image latent. A posterior q(z|s_x,s_y) sees context and target during training; a learned context-conditioned prior p(z|s_x) supplies samples at inference; a predictor g(s_x,z) predicts target embeddings. It uses a representation-space CVAE/ELBO with a KL term, reparameterisation and an EMA target encoder. The target-conditioned posterior is not available at inference. This is a distribution over plausible masked-image content, not a learned cross-model receiver channel.

**Evidence and conditions:** ViT-B/16 and ViT-L/16, 224x224 images, 384-d predictor, 128-d diagonal-Gaussian z, 600 epochs on ImageNet-1K, batch sizes 2048/1024, four A100 GPUs with bfloat16. The reported ViT-L linear probe is 78.3 vs I-JEPA 77.5; ViT-B is 73.5 vs 72.9. The main benchmark table uses a single run; appendix ablations average three seeds. Inference adds a two-layer MLP and reports 1.01x parameters and latency within measurement noise for ViT-B/16. These are large-GPU vision results, not Android measurements.

**Important limits:** the latent is one per image, not one per target region. Predictive variance correlates with error across pooled patches (Spearman rho about 0.33), but only weakly within images (mean rho about 0.16, positive in 76%); the authors explicitly say it is not a reliable localiser of error. Raw uncertainty is under-dispersed and needs scalar recalibration. Producing uncertainty maps requires multiple predictor passes (N=50 in the main visualisation; smaller N in quantitative checks). A separately trained diffusion decoder is used for pixel completions and is not part of S-JEPA's native non-generative predictor. This is not a drop-in Android model or proof of multimodal uncertainty.

**V14 mapping / testable idea:** a small, separately gated stochastic residual latent could eventually represent multiple plausible future/receiver states in JEPA/World/Self, while keeping a deterministic fast path. Sample only when temporal omission, ambiguous outcomes or disagreement makes uncertainty decision-relevant. First test a tiny diagonal-Gaussian prior/posterior over already source-bound B3/JEPA activation pairs; compare deterministic z, sampled z and zero/shuffled z on held-out receiver utility and calibration. Measure additional passes, RSS and TTFT; never infer local reliability from pooled correlation. This experiment is subordinate to the missing trusted tap producer and native receiver utility path. No Android fit or model swap recommended.

**Reuse/licensing:** no upstream code, weights or data reused; official code URL is listed in the paper but was not retrievable and license was not verified. Do not import until exact repository revision, software license, checkpoint license and dependencies are independently verified.


## R-147 — Exact UTF-8 token-piece provenance for cross-organ activation alignment (2026-11-25)

**Primary engineering finding.** Character offsets are not a complete token-alignment representation for llama.cpp token streams: byte-fallback tokenizers can split one Unicode code point across multiple tokens. The pinned llama.cpp server at b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 documents POST /tokenize with with_pieces=true; each token piece is returned as UTF-8 text or as raw byte values when the piece is not independently valid Unicode. With add_special=false, concatenating those pieces can be checked against the exact UTF-8 source bytes and used to derive byte spans without guessing character boundaries. The pinned upstream LICENSE is MIT. No upstream implementation was copied; V14 adds a project-owned verifier/aligner.

**Primary paper review.** Adam Deng, Shicheng Liu and Yada Zhu, *Augment the Cache, Replace the Activation: A 2x2 Study of Internal-State Sharing*, arXiv:2610.22026, submitted 2026-10-15 (preprint; no peer-review status claimed). Full main-text Sections 2–5 and limitations reviewed. The paper's same-family activation-replacement result depends on oracle layer and token positions; its cross-family transfer collapses under the tested configurations. It therefore supports strict positional/source provenance and receiver-task controls, not a claim that arbitrary B1/B2/C3 hidden states are interchangeable. Its tested residual-stream activations are not equivalent to V14's current final-RMSNorm tap or the receiver's input-embedding rows.

**Implemented candidate.** v13/code/v13/latent_adapter.py now accepts llama.cpp-style token-piece objects and raw byte arrays, verifies exact reconstruction of the source UTF-8 bytes, hashes those bytes, derives UTF8_BYTE token spans, and aligns sender rows to receiver rows by byte overlap. It also adds build_tokenwise_tap_manifest(): verifies each piece ID against the no-special content token ID, maps the unique content-token subsequence into the add-special prefill token sequence, selects the exact activation rows (including explicit BOS/special-token offset), and returns source hash/length/token spans/prefill positions. Tokenwise validation recomputes the full alignment-manifest digest from sender spans + ordered receiver spans + source hash/unit/length, and independently recomputes every overlap-coverage value. The previous validator only checked that caller-supplied alignment IDs were well-formed/equal and coverage was above 0.80; a caller able to re-hash pair IDs could otherwise supply an unverified alignment manifest/coverage. Character-span fixtures now carry the sender-span manifest too.

**Reproducible controls.** LOCAL_LINUX isolated helper reproduction: py_compile PASS; pytest -q test_latent_span_provenance.py test_tap_manifest_provenance.py — 10/10 PASS. Exact PR #2502 code/test SHA fa2673340f2dce78dcf7952b802957bf8b2f9212: adapter workflow 47/47 PASS on Python 3.13 and 3.14; public privacy scan CLEAN. Runtime-deployment integrity PASS on Python 3.11 and 3.14. Staged/integrated regression PASS: integrated 424 passed, 3 skipped, 58 subtests; staged runtime 255 passed, 10 skipped, 47 subtests. Two earlier fixture failures were corrected: 6955caf shuffled receiver rows only within a source (fixed in 408c074); 9cbefd used raw pieces without matching llama.cpp token IDs in three negative fixtures (fixed by using token objects with exact IDs in fa267). This is not a full local Aii checkout test; local repository suite remains BLOCKED/NOT_RUN because no checkout was available and github.com DNS failed.

**Integration boundary.** Cognition.tap/LlamaRunner.tap has not yet been changed to request with_pieces=true or call build_tokenwise_tap_manifest(); current persisted tap records still lack a trusted token-piece/source-span producer. The next Core-owned step must request the no-special content-token piece stream, map its IDs to the unique exact subsequence in the add-special embedding prefill, call the helper to select matching activation rows, and persist tokenizer/model/tap revision, exact source hash/length, token spans, event/generation, packet/blob hashes. Only then can source-disjoint real tap pairs be fitted. The existing B3 LATENT_PREFIX_V1 event-pooled receiver remains a separate route; this byte-tokenwise adapter is not accepted by that prefix contract.

**Status.** CODE_PRESENT + local isolated synthetic proof + exact GitHub adapter/staged CI PASS; no native GGUF, receiver task utility, gradient/retention, Android or Redmi proof. B3 remains OFF; REDMI_UNVERIFIED. No model, weight, permission, device data, or installed runtime was changed.

**Sources.**
- Paper: https://arxiv.org/abs/2610.22026
- Pinned llama.cpp server API: https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/tools/server/README.md
- Pinned llama.cpp license: https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/LICENSE


**Latest available device evidence (private, sanitized).** V13OBS #115 was last updated 2026-11-24T09:28:11Z. Pipeline auto-update was enabled and dashboard/runtime reported UP_TO_DATE at installed SHA 8d93236c753f0194224c19edc7411d8d7082b1d6, but the AI runtime was STOPPED_BY_USER, the model process STOPPED and autostart false. The last recorded C3 turn produced 7 tokens with 2.046 s TTFT from a 358-token prompt; this is one historical turn, not sustained acceptance. The five-turn metadata still records B1/B2 native failures and no valid offers; native latent exchange and C3 semantic use are false. No newer receipt was available in this run; REDMI_UNVERIFIED. No device action was taken.


## R-148 — Receiver input-embedding row extraction with llama.cpp (2026-11-25)

**Gap.** The tokenwise adapter's native receiver contract requires actual receiver input-embedding rows. Existing V13 `LlamaRunner.tap` exposes final-RMSNorm prefill activations, which are a different space and must not be relabelled as input embeddings. Core PR #2499 currently pins llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; at that exact revision, `src/llama-ext.h` has the full-matrix `llama_model_get_tok_embd` API but not the row-select function.

**Primary OSS source and exact implementation.** llama.cpp commit `a8fad21e9949c20f6b21692c8d38a8aba422eafe` (2026-11-09; upstream MIT) contains `llama_model_get_tok_embd_rows(const llama_model*, const llama_token*, uint32_t, float*)` in `src/llama-ext.h`. The corresponding `src/llama-model.cpp` implementation loops over requested token IDs and calls `llama_tensor_rows_to_f32(tensor, token, 1, ...)`, returning only `n_tokens × n_embd` F32 values. The header explicitly labels itself a staging/WIP API: breaking changes are allowed, so any use must pin the exact revision and compile/test it rather than treating it as stable ABI. Sources: https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/src/llama-ext.h ; https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/src/llama-model.cpp ; https://github.com/ggml-org/llama.cpp/blob/a8fad21e9949c20f6b21692c8d38a8aba422eafe/LICENSE .

**Resource estimate (calculated, not measured).** The row output itself is `n_tokens × n_embd × 4` bytes: 64 × 1024 × 4 = 262,144 bytes (256 KiB); 64 × 2048 × 4 = 524,288 bytes (512 KiB). This avoids the output allocation for the entire `n_vocab × n_embd` F32 matrix, but says nothing about backend/temporary allocations or Redmi RSS.

**V14 adaptation.** Research/Perception PR #2502 now adds `v13/code/v13/native_input_embedding_tap.py`, a strict manifest contract for rows returned by such a native extractor. It binds role-derived `b1/b2/c3.input-embedding.v1`, exact UTF-8 token pieces/IDs and byte spans, source ID/hash, event, brain generation, model/tokenizer revisions, dimensions and per-row digests. It rejects final-RMSNorm tap IDs and altered source/rows. This is a contract only: it does not extract native rows or wire `Cognition.tap`.

**Required integration experiment.** Core should review a pin update to a compatible revision containing the row-select API, include the exact staging header, extract only no-special content-token rows after `/tokenize` with `with_pieces=true`, then persist them with the new manifest and the existing SourceRef/event/generation/blob bindings. Run Linux native compile/selftest and Android arm64 cross-compile; then a consented real GGUF pair, source-disjoint receiver task, exact-text/no-message/zero/shuffle/repeat/OOD controls, gradient/parameter diff, old-task retention, restart and rollback. Keep the event-pooled `LATENT_PREFIX_V1` receiver separate. No production B3 activation until independent review and utility gates pass.

**Evidence boundary.** PR #2502 exact head `2f74fa94d2ad4d0004ec61ea128bdec4d320e569`: adapter contract 53/53 PASS on Python 3.13 and 3.14; public privacy scan CLEAN; runtime-deployment integrity PASS on Python 3.11 and 3.14; staged/integrated regression was still running at checkpoint. Full local Aii checkout unavailable. No native GGUF, Android/Termux or Redmi test; no model/weight download or swap. B3 remains OFF; REDMI_UNVERIFIED / NOT_RELEASED.


### R-148 evidence correction — final CI readback (2026-11-25)

The exact code/test head `2f74fa94d2ad4d0004ec61ea128bdec4d320e569` is now fully green in CI:
- Adapter workflow `45648811640`: 53/53 tests PASS on Python 3.13 and 3.14; privacy scan CLEAN.
- Runtime-deployment integrity `45648811730`: PASS on Python 3.11 and 3.14.
- Staged/integrated regression `45648811577`: PASS. Integrated regression: 424 passed, 3 skipped, 58 subtests; staged runtime: 255 passed, 10 skipped, 47 subtests.
These are CI/Linux results, not local checkout, native GGUF, Android or Redmi proof. The subsequent documentation-only branch commit `8f057c3d83d88bb5eadfc6a6629b3afce1b81e3d` was read back from the branch ref; the GitHub PR API still reported the prior PR head `2f74fa94...` at last poll, so PR-head synchronization of the docs commit remains unverified.



## R-149 — Native input-embedding tap: extractor receipt and upstream provenance correction (2026-11-25)

**Correction to R-148.** The cited upstream commit `a8fad21e9949c20f6b21692c8d38a8aba422eafe` is *not* the origin of `llama_model_get_tok_embd_rows`; its actual title is “mtp: read the target hidden states from a device buffer” (#31927). The selected-token-row API is present in upstream llama.cpp commit `2851b3bcbf8d993a2243ae751c0a7dfa8e944a40` (2026-10-16, commit `mtmd: add mtmd_audio_stream + support voxtral-realtime`, #30629). Its `src/llama-ext.h` declaration and `src/llama-model.cpp` implementation expose `llama_model_get_tok_embd_rows(model, tokens, n_tokens, out)`; implementation validates each token against the token-embedding tensor and reads one row at a time through `llama_tensor_rows_to_f32`. The helper obtains F32 rows from F32/F16/BF16/quantized storage. Upstream repository license is MIT. The header remains explicitly staging/WIP, so this is not a stable ABI. The current V14 receiver pin `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` predates the API and cannot be claimed to provide it.

**New implementation.** Research/Perception child PR adds schema v2 to `v13/code/v13/native_input_embedding_tap.py`. The previous manifest bound source, event, generation, token pieces/IDs, model/tokenizer revision, row dimensions and row digests, but it did not bind the native extractor call that supposedly produced those rows. Schema v2 now requires a strict `v14.llama-token-embedding-rows-receipt/1` containing:
- exact API symbol/header and explicit `STAGING_WIP` status;
- pinned llama.cpp commit and native extractor binary SHA-256;
- installed model revision and model SHA-256;
- source tensor type and F32 output dtype;
- vocabulary size, embedding dimension, exact ordered requested token IDs and returned element count.

The receipt is copied into the manifest digest. It rejects ID/order drift, invalid vocabulary bounds, partial/wrong element counts, dimension mismatch, wrong model bytes/revision, malformed binary/revision digests, non-F32 output and malformed tensor types. It deliberately calls the IDs “requested” rather than “returned”: upstream API returns an element count, not token IDs. The C++ wrapper must prevalidate *all* token IDs before calling it and must emit a receipt only if the API returns exactly `n_tokens × n_embd`; the upstream implementation can otherwise write earlier rows before encountering a later invalid token and returning zero. Python validates receipt consistency; the caller still has to independently hash the actual model and extractor binary. Manifest SHA is integrity, not a signature.

**Verification.** Isolated LOCAL_LINUX reproduction, CPython 3.13.5: `py_compile` PASS; 19 focused positive/negative tests PASS. This used an isolated package with the exact new module logic and minimal dependency stubs; it is **not** the full Aii checkout or full repository suite. Exact Aii checkout remains unavailable in this environment. Exact GitHub Actions run 45658242985 on code/test commit 787758a885294d63c614c4171c4a528ecc303dc8 passed 66 tests on both Python 3.13 and 3.14; public privacy scan CLEAN. No llama.cpp native build, real GGUF row read, Android arm64 binary, Termux or Redmi execution is claimed. No model, weights, permissions, updater or device data were changed. B3 remains OFF; REDMI_UNVERIFIED / NOT_RELEASED.

**Next integration.** Core must consume this receipt from its native selected-row wrapper, independently verify the model/extractor hashes and pin the API-bearing llama.cpp revision. Keep the sender final-RMSNorm tap distinct from the receiver input-embedding table. The event-pooled `LATENT_PREFIX_V1` route remains a separate experiment; neither contract proves learned semantic utility or production latent communication.

**Sources.** Upstream commit mirror/diff: https://gitea.gnumetry.com/ggml-org/llama.cpp/commit/2851b3bcbf8d993a2243ae751c0a7dfa8e944a40 ; current upstream API/source documentation: https://fossies.org/dox/llama.cpp-1.0.0/llama-model_8cpp_source.html ; official upstream LICENSE: https://github.com/ggml-org/llama.cpp/blob/master/LICENSE ; unrelated commit correction: https://github.com/ggml-org/llama.cpp/commit/a8fad21e9949c20f6b21692c8d38a8aba422eafe .


### R-149 exact-head CI readback — 2026-11-25

The branch push workflow `V14 latent token-span alignment`, run `45658242985`, completed successfully on code/test commit `787758a885294d63c614c4171c4a528ecc303dc8`:
- Python 3.13: compile PASS; focused suite 66 passed; public privacy scan CLEAN.
- Python 3.14: compile PASS; focused suite 66 passed; public privacy scan CLEAN.
This is GitHub-hosted CI/Linux evidence, not local full-repository execution. The subsequent handoff/ledger-only commits do not change the tested module/test bytes. No native llama.cpp build, real GGUF row extraction, Android cross-compile, Termux or Redmi proof.


## R-150 — Portable Semantics, Private Dialects: reuse and negative transfer in latent communication (2026-11-25)

- **Primary source:** Narcis Marincat, arXiv:2609.11365v1, submitted 2026-09-10, cs.AI/cs.LG/cs.MA. Status: `ABSTRACT_VERIFIED + PUBLIC ARTIFACT README REVIEWED; FULL PAPER NOT REVIEWED`. Primary arXiv record: https://arxiv.org/abs/2609.11365
- **Evidence summary from the abstract:** a preregistered, leakage-controlled audit reports 30 directed pairings across six independently trained restricted societies. Only within-initialization pairs showed exact/asymmetric partial raw interoperability; all 26 cross-initialization directions failed the tested frozen raw/orthogonal/linear/nonlinear alignment ladder. In one matched adaptation factorial, reinitializing only the inherited reader/writer/mouth raised depth-three accuracy from 0.169 to 0.857. Across two restricted checkpoints and two target streams each, inherited interfaces did not beat fresh-interface controls by the preregistered 0.10 margin.
- **Important limits:** the authors bound the main results to a near-transfer 17-state setting. The negative-transfer factorial concerns one globally visible parent checkpoint; the appendix includes a post-hoc twin case study. This is not evidence that all independently trained LLMs are incompatible or that a universal latent space is impossible. The full PDF/HTML was not accessible in this run, so method details beyond the abstract and public artifact README are not independently verified.
- **OSS/license:** public artifact repository `tokenosopher/populus-evidence-partitioning`, README and root LICENSE read from its `main` branch; code license is MIT. The repository describes a Qwen2.5-0.5B-Instruct shared-backbone experiment and companion audit artifacts. Hosted fitted maps/checkpoints are separate Hugging Face artifacts; their specific weight/checkpoint license was not verified. No code, data, model or weights were downloaded or reused.
- **V14 consequence:** preserve pair-specific sender/receiver adapters and never assume a latent coordinate system transfers across model initializations or revisions. The current `latent_adapter.py` already binds sender/receiver role, tap ID, model revision, model SHA and tokenizer revision; keep those checks. On model/tap/tokenizer change, require a fresh fit or an explicitly evaluated transfer candidate. Acceptance must include source/session-disjoint receiver-task utility, exact-message/no-message/zero/shuffle/repeat/OOD controls, old-task retention and restart/rollback—not alignment similarity alone.
- **Falsifiable follow-up:** once native taps are actually persisted, compare fresh pair-specific fit against inherited adapter state on a held-out receiver task, with the same train budget and a reinitialized-reader/writer baseline. Do not use the paper's 17-state scores as V14 targets.
- **Implementation link:** the typed native extractor-output bridge is PR #2506, tested code/test SHA `c4b73ab2d792b4be6d4c673d23233f8fb07c9274`; later handoff/board commits are documentation-only, so use the live PR ref for current head. It does not yet create a real paired cohort or prove latent utility.


## R-151 — Native tokenwise sender/receiver pair assembly and mobile API caveat (2026-11-25)

- **Primary OSS source:** ggml-org/llama.cpp commit 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40, authored 2026-10-15; exact source/header and implementation were inspected. The selected-row API is declared in src/llama-ext.h, which explicitly marks the interface staging/WIP. Its implementation converts only requested token rows through llama_tensor_rows_to_f32 and returns an element count. Upstream may return zero after earlier rows have already been copied for a later invalid token, so the wrapper must prevalidate the complete ID list and accept only the exact n_tokens × n_embd count.
- **License:** llama.cpp code is MIT. The license for any installed GGUF weights remains model-specific and was not verified here. No model, data or weights were downloaded.
- **Mobile/resource limit:** Core's extractor creates a CPU llama model using mmap/lazy loading before selecting rows. The output bound is at most 64 × 8192 × 4 = 2 MiB F32; this is output geometry only, not peak RSS. Model mapping, metadata, page residency and allocator overhead have not been measured on Redmi. The extractor API pin (2851b3b) and existing native receiver pin (b29c606) differ; compatibility must be measured on the exact GGUF before use.
- **New implementation:** Draft PR #2507 adds v13/code/v13/native_tokenwise_pairing.py. It consumes a source-bound sender LatentTapPacket plus the exact Cognition.read_tap result, and the complete native extractor output already bridged by #2506. It validates the full SourceRef bytes, sender role/event/generation/tap/model/blob and read-only authority, receiver role-specific input-embedding tap, extractor receipt/model/tokenizer bindings, and UTF-8 byte-piece alignment. Different tokenizer segmentations are aligned by byte overlap rather than token index. The record is in-memory PAIRED_DIAGNOSTIC only; no persistence, adapter fit, inference, weight change, training authority or B3 enablement.
- **Verification:** LOCAL_LINUX CPython 3.13.5 isolated harness with stubbed existing dependencies: 7/7 positive/negative tests PASS; py_compile PASS. Exact GitHub Actions PR run 45678205802: 80/80 PASS on Python 3.13 and 80/80 PASS on Python 3.14; py_compile PASS; public privacy scan CLEAN. Exact push run 45678196840: same 80/80 PASS on both versions; privacy scan CLEAN. Completed PASS: staged-runtime 255 passed, 10 skipped, 47 subtests; integrated-regression 424 passed, 3 skipped, 58 subtests. Both jobs in run 45678205707 succeeded. Full local Aii checkout NOT_RUN. No real GGUF row read, native receiver utility, Android/Termux or Redmi proof.
- **Research interpretation:** R-150 remains ABSTRACT_VERIFIED + artifact README reviewed; full paper not reviewed. Its limited near-transfer results support pair-specific adapter evaluation and caution against assuming cross-initialization compatibility; they do not prove universal latent incompatibility. Keep pair-specific model/tap/tokenizer bindings and fresh-fit/transfer ablations.
- **Next falsifiable step:** Core wires native /tokenize with_pieces=true for both roles, calls this builder after Cognition.read_tap and the real selected-row extractor, then builds a consent-gated source/session-disjoint cohort. Compare receiver-task utility against no-message, zero, shuffled token/row, repeat, OOD and fresh-adapter controls; measure old-task retention and restart/rollback. Keep event-pooled LATENT_PREFIX_V1 separate and B3 OFF until utility passes.
- **Status:** PR #2507 is a DRAFT stacked on #2506, not merged or released. REDMI_UNVERIFIED; NOT_RELEASED; no user/device action.


## R-152 — Avoid a duplicate native GGUF model load for selected-row taps (2026-11-25)

- **Direct source inspection:** Core's native receiver at PR #2499 uses llama.cpp revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 and calls llama_model_load_from_file with CPU + MMAP before llama_decode. Core's selected-row extractor at PR #2505 uses revision 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40, also calls llama_model_load_from_file with CPU + MMAP (plus lazy mode), then calls llama_model_get_tok_embd_rows. The Python wrapper prepares the model pool idle and launches the extractor separately.
- **Optimization hypothesis, not a measured result:** move selected-row extraction into the native receiver executable, pin the receiver to the exact revision that exposes the staging/WIP row API, and use the same loaded llama_model pointer for selected-row reads and receiver decode. This could avoid a second native process/model load and repeated startup/page-fault work. Because both paths use mmap, do not claim a 2× RSS reduction; measure PSS/RSS, load/TTFT and row extraction on the exact GGUF.
- **Compatibility risk:** current receiver pin b29c606 differs from extractor pin 2851b3b. Unifying them is a native ABI/build change and must preserve ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL, LATENT_PREFIX_V1, dimension refusal, zero/shuffle/repeat controls and rollback. Keep the exact WIP API pin visible.
- **Ownership/coordination:** this is a Core-owned implementation candidate, not a Perception patch. It was handed to Core in PR #2499 and #2505 comments. No C++ code, binary or model was changed in this run.
- **Status:** RESEARCHED_FROM_PINNED_SOURCE / NOT_IMPLEMENTED / NOT_MEASURED. It is a candidate to reduce redundant loading, not evidence of lower Android memory or faster user turns.


## R-153 — Synthetic WorldJEPA A→B→A interference and replay ablation (2026-11-25)

- **Source/evidence:** exact staged CI run 45678205707, job staged-runtime 139431360731 and integrated-regression 139431361463. Staged runtime: 255 passed, 10 skipped, 47 subtests. Integrated regression: 424 passed, 3 skipped, 6 warnings, 58 subtests. This is a synthetic NumPy WorldJEPA test harness, not B1/B2/C3 model weights, user data, native GGUF or Android.
- **Single-task holdout:** two staged runs reported 47 train rows / 17 holdout rows and lower post-fit loss: 0.91424695 → 0.86530351 (delta −0.04894344), and 1.17286671 → 1.10252766 (delta −0.07033905). The exact resume test reports main_steps=4, bootstrap_steps=2 and exact model/EMA/inverse/moments/RNG/source-lineage restoration.
- **A→B→A diagnostic:** 12 source-disjoint arms (3 seeds × no/uniform replay × persistent/reset optimizer), 32 update steps per phase, synthetic 4-dimensional old/new dynamics. Across arms: mean A reacquisition gain 0.07505 (positive in 6/12); mean B forgetting after A return 0.12274 (positive in 9/12); B actual-action holdout loss was worse than both zero-action and shuffled-action controls in 12/12. Parameter-delta norm ranged 2.44744–3.58289; rollback checkpoint readback was exact in all 12 arms.
- **Replay interpretation:** no-replay mean B forgetting was 0.25041 and mean A reacquisition gain 0.21055. Uniform replay shifted mean B forgetting to −0.00493, but mean A reacquisition gain to −0.06044; critically, B actual-action loss still lost to both controls in all 12 arms. Thus uniform replay reduced this particular loss-delta but did not establish useful action-conditioned transfer or robust A reacquisition.
- **Persistent vs reset optimizer:** across 3 seeds, new-task holdout gain was positive 3/3 but old-task holdout loss worsened 3/3; actual action beat both zero and shuffled controls in only 2/3 seeds. Persistent optimizer state was not uniformly superior to reset.
- **Interpretation:** this is evidence of real numeric changes inside the synthetic WorldJEPA implementation (gradients, parameter/EMA/moment deltas, optimizer steps, checkpoint persistence), alongside cross-task interference and unstable action utility. It is not evidence of useful continual learning in the installed LLMs or on Redmi.
- **Next experiments for JEPA & Memory:** selective per-organ/per-task plasticity masks or adapters, eligibility × error × modulator gating, balanced/importance replay, and an old-task retention gate before checkpoint commit. Require actual-action holdout to beat both zero and shuffled controls across seeds; measure new-task gain and old-task retention together. Do not solve this by freezing all weights.


### R-151/R-153 final CI status correction (2026-11-25)

The previously pending staged/integrated run 45678205707 has now completed PASS: staged-runtime 255 passed, 10 skipped, 47 subtests; integrated-regression 424 passed, 3 skipped, 58 subtests. The R-153 synthetic WorldJEPA findings above are from this completed run. This does not change the no-native-GGUF/no-Redmi classification.


## R-154 — Session-disjoint holdout for native tokenwise adapter fitting (2026-11-25)

- **Methodological correction:** source-ID/source-hash separation alone does not prevent two different sources from the same conversation/session appearing in train and holdout. That can leak session-specific context and overstate cross-session generalization.
- **Implementation:** draft PR #2508, exact head c246a56a50f06ca6d8e1ee560e6caa6fcd426a99, adds TOKENWISE schema v4, per-pair session binding in the alignment digest, a >=2 train-session / >=2 holdout-session gate, and `fit_adapter_from_native_pair_records()` for in-memory source-bound pair records. It checks unique source IDs/hashes, exact record digests and consistent sender/receiver model/tap/tokenizer bindings.
- **Evidence:** LOCAL_LINUX CPython 3.13.5 isolated stub-bound wrapper harness 3/3 PASS (positive cohort, session-overlap rejection, session-tamper rejection). Full local Aii checkout unavailable; exact repository py_compile/pytest NOT_RUN; no exact PR #2508 CI run visible at last poll. This is not native receiver utility or model learning evidence.
- **Research status:** this is an evaluation-design correction, not a new paper claim. It complements R-149's pinned native selected-row API source review and R-150's pair-specific transfer caution. The fitter remains PCA+ridge alignment only, with no persistence, inference, gradient update or B3 authority.
- **Next falsifiable step:** Core composes #2505 extractor + Cognition.read_tap + #2507 pair builder, then runs the fitter on consented real native pairs with whole-session holdout. A candidate must subsequently beat exact/no-message/zero/shuffle/repeat/OOD receiver-task controls and pass old-task retention, restart and rollback before any B3 promotion.

## R-155 — Receiver-native lexical anchors with bounded tokenwise latent residual (2026-11-25)

- **Primary source:** Yang et al., *XBridge: Entity-Grounded Latent Bridge for Heterogeneous LLM Communication*, arXiv:2608.11676 (2026-08-12), accepted NeurIPS 2026: https://arxiv.org/abs/2608.11676. The paper separates deterministic receiver-vocabulary lexical anchors (LAM) from gated latent enrichment (LEB). Its reported LEB uses four cross-attention blocks and 264M trainable parameters; experiments use 7B-class LLMs across seven tasks. It reports that bridge-only F1 is substantially weaker than the combined anchor+enrichment setup. This is not a mobile-sized implementation.
- **Repository/licensing:** official source https://github.com/WooseongYang/XBridge; repository LICENSE is Apache-2.0. Requirements include PyTorch >=2.6, Transformers 4.52..<5, Accelerate, Datasets and NumPy >=2.0. The pretrained checkpoint/model-weight license was not verified. No code, dataset, checkpoint or weight was reused or downloaded.
- **Counterevidence / causal limit:** Cárdenas Piepereit, *Architecture-Dependent Causal Transfer of Activation States Across Large Language Models*, arXiv:2608.16347v2 (2026-11-09), preprint: https://arxiv.org/abs/2608.16347. On 20-item held-out retrieval pools, learned projections reached 45–50% top-1 versus 5% chance for three decoder-only pairs, but the pre-registered end-to-end causal-generation criterion passed for only one of three pairs (Qwen2-0.5B→Phi-3-mini, 23.3% vs 0%, n=30, FDR-corrected p=0.0469). The two Mistral-targeted pairs had no causal effect, and successful retrieval often did not yield the correct answer. This is a small preprint study, not universal evidence.
- **V14 implication:** the current tokenwise fitter maps sender final-RMSNorm rows toward receiver input-embedding rows. The existing replacement-style receiver builder can replace the receiver's exact native token rows with projected values. XBridge motivates retaining receiver-native lexical anchors while adding a separate bounded signal; the Cárdenas study warns that alignment/next-token changes are not semantic utility. A small residual interpolation is therefore an optional diagnostic, not a claim to reproduce XBridge LEB or transfer meaning.
- **Implementation:** draft PR [#2511](https://github.com/RedMentos/Aii/pull/2511), stacked on #2508. It (a) recomputes the receiver input-embedding manifest digest and extractor receipt, and checks every aligned receiver row digest/span against the manifest; (b) adds build_anchor_preserving_native_receiver_input(), which keeps exact receiver rows as the base and adds a per-token norm-capped residual toward the projected sender row. Default gain 0.10; gain is bounded to 0..0.5 and relative residual to 0..1. Existing replacement mode is unchanged. No persistence, inference call, gradient update, semantic authority or B3 promotion.
- **Verification:** LOCAL_LINUX CPython 3.13.5 isolated harness: py_compile PASS and 4/4 positive/negative checks PASS (zero-gain exact-anchor identity, residual cap, detached-row rejection, invalid-gain refusal). This is not the full Aii repository suite. Full checkout is absent; exact repository tests and CI are pending. No real GGUF receiver inference, task utility, Android/Termux or Redmi proof.
- **Next falsifiable step:** Core's native capture/receiver lane (#2510) must rebase/consume this helper under the existing probe approval. Evaluate held-out receiver tasks against exact-message, no-message, zero, shuffled, repeated, OOD and entity-substitution controls; require answer utility and old-task retention, then restart/rollback. Measure PSS/RSS/TTFT on the exact GGUF before any mobile claim. B3 remains OFF; REDMI_UNVERIFIED; NOT_RELEASED.


## R-156 — Teacher-forced target-token likelihood as a native receiver-utility proxy

- **Primary implementation source:** llama.cpp public API at pinned revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, MIT licensed: [include/llama.h](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/include/llama.h). The reviewed header exposes `llama_get_logits_ith`, `llama_batch_init`, `llama_decode`, `llama_model_get_vocab` and `llama_vocab_n_tokens`; it explicitly states that embeddings mode returns embeddings together with logits. This is API inspection, not a real model experiment.
- **Method:** after decoding the same receiver input-embedding context, score a bounded 1–512 token target sequence by teacher forcing: compute `log p(y_i | context, y_<i)` from native logits, then decode each preceding target token before scoring the next. Use stable log-sum-exp, reject NaN/+Inf/all-invalid logits and out-of-vocabulary token IDs. The target IDs are sent through stdin after the float32 input payload, not process arguments or audit logs. The receipt binds target-ID SHA/count, input SHA, receiver GGUF SHA, native binary SHA, pinned llama.cpp revision/version, decode status and explicit input-consumed evidence.
- **Why this is only a proxy:** conditional likelihood is not generated-answer correctness, semantic understanding, causal transfer or useful behavior. A language model can assign high probability to a plausible but wrong continuation. The evaluator therefore requires paired source/session-bound controls and a held-out cohort: NO_MESSAGE, EXACT_MESSAGE, LATENT_CANDIDATE, ZERO, SHUFFLE, REPEAT, OOD and ENTITY_SUBSTITUTION, with at least 20 task groups, two sessions and two task families. Candidate must beat every control. Synthetic receipts remain FIXTURE_ONLY.
- **Concrete V14 adaptation:** Core PR [#2515](https://github.com/RedMentos/Aii/pull/2515) adds the C++ target-score producer, Python receipt binding and a 160-entry ephemeral cohort collector. The unchanged Perception evaluator is carried from #2511. Current runtime probe integration emits LATENT_CANDIDATE only; the seven other conditions and complete matrix are still open. No target text, token IDs, vectors or score receipts are persisted; no training/production/B3 authority is granted.
- **Evidence level:** LOCAL_LINUX isolated C++17 log-sum-exp helper compiled with `-Wall -Wextra -Werror` and passed equal-logit, invalid-index, NaN, +Inf and all-negative-infinity tests. Full llama.cpp-linked receiver build, exact-head CI, real GGUF target score and Android/Redmi execution were NOT verified at this checkpoint. No model or weight was downloaded.
- **Next falsifiable experiment:** run the eight-condition matrix on a pinned real GGUF in LOCAL_LINUX across >=20 held-out task groups, >=2 sessions and >=2 task families; record per-token likelihood deltas, task-level wins/losses and uncertainty. Then repeat only after explicit authorized Termux/Redmi test consent with a genuine device execution receipt. Keep B3 OFF until native utility and negative controls pass.


## R-157 — Native-side target-token digest verification (2026-11-26)

- **Normative source:** NIST FIPS 180-4, *Secure Hash Standard*, SHA-256; https://doi.org/10.6028/NIST.FIPS.180-4. This is the algorithm specification, not a model or latent-learning paper.
- **Observed gap:** the native receiver previously validated the caller-supplied digest's 64-character hex shape but did not recompute it from the int32 target-token IDs consumed by the C++ scorer. The native JSON could therefore repeat a correct-looking caller digest without independently binding it to the token sequence.
- **V14 adaptation:** Core PR #2520 computes SHA-256 over explicitly serialized little-endian int32 token IDs in the native process, rejects a mismatch before model loading/scoring, and emits the computed digest. This adds no OpenSSL/crypto dependency and reuses no third-party SHA implementation.
- **Tests/evidence:** C++ selftests cover the NIST `abc` known vector, token IDs `[0,1,2]`, mismatched digest and negative-ID rejection. LOCAL_LINUX isolated C++17 compile/selftest PASS with `-Wall -Wextra -Werror`. Exact PR head `7ffe4e23de79c82aeed8ceb43dfc7ff3adb305b8`: pinned llama.cpp Linux build/selftest PASS, Android arm64 cross-compile PASS only, Python 3.13/3.14 45/45 each, all seven workflows SUCCESS. No real GGUF task-score run or Redmi execution.
- **Interpretation:** stronger provenance for the target tokens consumed by the receiver; not evidence of answer correctness, semantic transfer, trained latent coupling, production routing or B3 utility.
- **Next falsifiable step:** wire the eight-condition matrix through a separate local one-shot Runtime approval bound to the exact matrix/source/session/model/target digests; then test >=20 held-out task groups across >=2 sessions and >=2 task families on a pinned real GGUF, requiring the candidate to beat every control.


## R-158 — Cache-level latent bridge evidence versus activation-transfer failure (2026-11-26)

- **Constructive primary source:** Maximillian Rossi, Prajwal Raghunath and Eugene Wu, *Latent Cache Flow: Model-to-Model Communication Without Text*, arXiv:2605.22863 (first posted 2026-05-19); the reviewed proceedings PDF identifies PMLR 306 / ICML 2026. Full paper and appendices reviewed, not abstract-only. Sources: https://arxiv.org/abs/2605.22863 and https://openreview.net/pdf/ad6e6d97d3d8d92825fa0d2d26b8e6caea4bcd64.pdf .
- **Mechanism:** LCF combines sender and receiver per-layer K/V cache states, projects them through a shared low-dimensional bottleneck, splits K/V residuals, and uses per-head gates to add bounded edits to the receiver cache. LCF-X adds hierarchical span pooling so sender-private context can be summarized without token-position alignment. This is a cache-level residual interface, not static token-embedding-row replacement.
- **Shared-context evidence:** Qwen2.5-0.5B-Instruct → Qwen3-0.6B, OpenHermes 2.5 (500K subset), frozen base LLMs, adapter-only training, 300 steps on one A100 80GB (~4–5 h). LCF-128: 19.4M trainable parameters / 39 MB projector; a 9-layer pruned variant: 6.24M / 13 MB; a 6-layer variant: 4.16M / 8 MB with lower task performance. Reported gains are specific to this pair/protocol; projector footprint is not total runtime RSS.
- **Cross-context evidence:** LCF-X uses two Qwen3-0.6B instances and partitioned HotpotQA-bridge, ~70.7K training items, ~277 steps, ~25.8M projector parameters plus 57K pooling parameters, about 50 minutes on an RTX PRO 6000 Blackwell. On 5,899 evaluation items it reports 35.13 F1 / 25.28 EM versus T2T max-200 at 32.66 / 20.53, with TTFT 48 ms versus 410 ms. Important limitation: this cross-context experiment is same-model/same-family, task-specific receiver adaptation; the authors say transfer cannot be fully separated from receiver tuning and richer heterogeneous multi-turn agent workflows remain future work.
- **Scoped counterevidence:** Peiyan Zhang, *A Negative Result on Cross-Model Activation Transfer in a Pythia Multi-Hop Setting*, arXiv:2606.03280 (2026-06-02, preprint; https://arxiv.org/abs/2606.03280). Pythia-160M → Pythia-410M on 396 multi-hop items reached normalized R²≈0.88 and cosine≈0.97 offline, yet additive injection stayed near baseline (95% CI crossed zero), while replacement injection was destructive; norm correction did not restore utility. This is one model pair, task family and fixed injection depth, so it is not a universal no-go. It is direct evidence that alignment loss is not a substitute for receiver-side causal/task utility.
- **Licensing/reuse:** The LCF PDF itself notes a patent-pending provisional application. No official LCF code repository or implementation license was found in the paper or GitHub exact-title/LCF-X search; no checkpoint license was verified. An arXiv metadata mirror reports CC BY 4.0 for the manuscript, but that does not grant code or model-weight rights. No code, dataset, checkpoint or weights were downloaded or reused.
- **V14 boundary:** the current selected-row API `llama_model_get_tok_embd_rows` reads static `model->tok_embd` input-embedding rows, not contextual sender activations or per-layer K/V caches. PR #2519's eight-condition bridge scores teacher-forced target-token likelihood; it is not LCF, not a learned KV bridge and not semantic answer proof. Keep these evidence classes separate.
- **Concrete research direction:** Core should first audit the pinned llama.cpp revision for supported per-layer K/V cache capture and controlled receiver-cache residual injection. If feasible, prototype a receiver-anchored, gated low-rank residual on a very small selected-layer subset (initial d=64/128), with exact/no-message/zero/shuffle/repeat/OOD/entity-substitution controls and held-out task/session splits. Measure generated-answer utility, old-task retention, restart/rollback, PSS/RSS and TTFT. The 13 MB projector figure is a storage reference only; LCF training used 80 GB A100 or RTX PRO 6000 hardware, not Android. No model download, model swap, training permission or B3 activation is implied.
- **Status:** RESEARCHED_FROM_FULLTEXT / NOT_IMPLEMENTED / NO_OFFICIAL_CODE_REUSE / REAL_GGUF_UNVERIFIED / REDMI_UNVERIFIED / B3_OFF.


## R-159 — Pinned llama.cpp hybrid K/V cache access audit (2026-11-26)

- **Exact upstream source:** `ggml-org/llama.cpp` revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, the revision pinned by the current Perception native receiver workflow. `LICENSE` blob `e7dca554bcb802f98408383a864404e3aa4eacca` is MIT (Copyright 2023–2026 ggml authors). No upstream code was copied.
- **Public C API boundary:** at this revision `include/llama.h` exposes opaque `llama_memory_t`, `llama_get_memory()` and sequence management operations (`llama_memory_seq_rm/cp/keep/add/div`, position min/max). It does not expose a public stable C API for reading or injecting raw K/V tensors.
- **Internal C++ read surface:** `src/llama-memory-hybrid.h` exposes `llama_memory_hybrid::get_mem_attn()` and `get_mem_recr()`; `llama_memory_hybrid_context::get_attn()` returns a `llama_kv_cache_context`. `src/llama-kv-cache.h` exposes `get_layer_ids()`, `get_k_storage()`, `get_cells()`, and the context's `get_k()/get_v()` views. `src/llama-kv-cells.h` exposes `seq_has()`, `pos_get()`, and per-sequence position bounds, so a read-only snapshot can in principle identify the occupied cells for a sequence. The full-cache context is an internal graph-build helper, not a documented external snapshot API.
- **Internal write surface:** `llama_kv_cache_context::cpy_k()/cpy_v()` are public methods on the internal C++ class, but are designed for graph construction. A write adapter must build the correct graph and cell indices, respect cache K/V dtype/layout, synchronize the backend, and validate sequence/session/generation before and after. Direct raw tensor writes would bypass those invariants and are not approved.
- **LFM2 relevance:** `src/llama-arch.cpp` classifies `LLM_ARCH_LFM2` and `LLM_ARCH_LFM2MOE` as hybrid; `src/llama-model.cpp` creates `llama_memory_hybrid` for hybrid architectures. Thus an LFM2 context has attention K/V and a separate recurrent-memory component. The K/V path covers only attention-filtered layers; it does not capture or transfer recurrent state. Layer IDs, sequence-to-stream mapping, ring-buffer cell positions and device placement must be handled explicitly.
- **Feasibility judgment:** a pinned-source C++ read path appears feasible for supported hybrid/attention contexts; it is **not** available through the stable public C API and is not a generic cross-architecture contract. A write path is more invasive and remains unimplemented. Multi-sequence/unified-cache mapping, backend copies, K/V quantization and graph scheduling still need proof. Do not assume the current static `model->tok_embd` selected-row extractor is a K/V tap.
- **Next experiment:** Core should add a version-guarded, read-only `KvCacheAccess` adapter against this exact pin. First test a single-sequence context and one selected attention layer: report model arch/memory subtype, layer IDs, K/V types and shapes, occupied positions/cell mapping, backend-copy result, RSS/PSS and no-mutation hash. Reject unsupported memory types and stale generations. Only after that should a separate write experiment exercise one-layer residual injection through `cpy_k/cpy_v` graph operations with no-message/zero/shuffle controls, cancellation and rollback. No production model download, model swap, training authority or B3 activation is implied.
- **Status:** OSS_API_AUDITED / READ_ONLY_PATH_PLAUSIBLE / WRITE_PATH_NOT_IMPLEMENTED / NO_GGUF_RUNTIME_PROOF / REDMI_UNVERIFIED / B3_OFF.


## R-160 — Native K/V snapshot receipt survives the Python/Runtime boundary (2026-11-26)

**Primary source / implementation basis:** R-159's pinned-source audit of `ggml-org/llama.cpp@b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` (MIT) and the Perception native receiver implementation in draft PR #2519. The native C++ eight-condition runner already emits a one-attention-layer/one-sequence LFM2 hybrid K/V snapshot after receiver prefill, with active-cell positions, K/V tensor shapes/types, K/V/combined SHA-256 values, and a double-read stability result. It explicitly excludes recurrent state and raw-byte export.

**Observed integration defect:** `native_latent_receiver.probe_matrix()` validated target-token likelihood but discarded each native condition's `kv_snapshot`. The task-matrix bridge then persisted only target log-probability metadata. The C++ read-only probe was therefore compiled and emitted by the native runner but its evidence was not consumed by the Python Runtime/task-score path.

**V14 change in draft PR #2524** (branch `research-perception/v14-kv-snapshot-consumer-20261126-run35`, head `3ee5ddd86ec25441f325d5e7c0b44fbf0003e30e` at this ledger update):
- Added `validate_native_receiver_kv_snapshot()`: checks the schema, one-sequence/one-layer scope, contiguous prefill positions and exact little-endian int32 position digest, active-cell count, four-dimensional K/V shapes, known tensor types, K/V/combined/stable digests, bounded double-read byte accounting, and read-only/no-raw/no-recurrent-state flags.
- The native matrix parser now requires the per-condition `context_rows` and K/V snapshot, binds the sanitized receipt to condition + installed receiver-model SHA-256 + condition-input SHA-256, and forwards only hashes/shape/type/byte/timing metadata. Raw K/V bytes and raw position lists are not carried into Runtime.
- The bridge requires all eight condition snapshots and consistent layer/attention-count/shape/type geometry before atomically recording the ephemeral task-score group. Receipt hashing now includes the K/V metadata.
- The Python preflight now requires the binary to advertise `kv_snapshot_supported` and schema `v14.native-receiver-kv-snapshot/1` before starting an expensive matrix run.
- Added synthetic tests for the raw→sanitized parser boundary, task-score propagation, missing/unstable snapshots, position digest mismatch and raw-export rejection.

**Evidence at checkpoint:** LOCAL_LINUX isolated helper reproduction PASS (valid raw/sanitized round-trip, bad position digest, unstable read, raw-export flag, active-cell mismatch); scratch `py_compile` PASS. Full local Aii checkout and exact repository pytest remain BLOCKED/NOT_RUN because no checkout is mounted and github.com DNS resolution fails. Exact PR #2524 Actions were queued/not yet observed. Parent #2519 head `5f2ef5393f25085d2e2968118982d72b823b99b4` has runtime-deployment integrity PASS but staged/integrated failures due the Core-owned source-pin chain for `v13/native/latent_receiver/CMakeLists.txt` (workflow runs 45748512354 and 45748512357; Perception review comment 7182405377). This PR is stacked and cannot be called green until the parent pin chain is repaired and the exact child head is tested.

**Evidence class / limits:** `WIRED_SYNTHETIC_CANDIDATE` for the Python receipt path; `LOCAL_LINUX_ISOLATED_HELPER_PASS`; `EXACT_CI_PENDING`; `REAL_GGUF_UNVERIFIED`; `REDMI_UNVERIFIED`; B3 remains OFF. This is a one-layer/one-sequence read-only cache digest, not K/V residual injection, not a trainable cross-model latent channel, not semantic utility, not generated-answer correctness, and not weight learning. No model/weight/permission/device-data mutation or deployment occurred.

**Next testable step:** finish exact PR #2524 CI after Core updates the staged source pins; then Core must rebase its Runtime producer/consumer PR onto this Perception branch and invoke the actual source-bound matrix builder through the live Runtime path. Only then run the real held-out GGUF cohort (at least 20 groups, at least two sessions and two task families), including all controls, generated-answer correctness, retention, restart/rollback and resource measurements. No Redmi claim without an authenticated device receipt.


## R-161 — Cross-Modal StateKV Injection for temporal visual evidence (2026-11-26)

**Paper:** Xiaoqian Zhang & Zhihao Zhang, *Cross-Modal StateKV Injection for Communication in Multi-LLM Systems across Temporal Segments*, arXiv:2611.22304, submitted 2026-11-17 (cs.CV; preprint, no peer-review evidence found). Full-text review used the accessible PDF mirror of the arXiv paper; the official arXiv record confirms title/authors/date/abstract. No maintained source repository or explicit reuse license was identified in this search, so this is research guidance only, not an OSS-reuse recommendation.

**Method actually described:** provider and carrier models observe complementary video-frame segments; provider visual-token K/V states are selected, feature-projected and sequence-mapped to carrier visual positions, then incorporated through gated residual updates. The carrier cache sequence length is preserved by rewriting existing visual entries, not by appending provider tokens. The paper explicitly distinguishes visual-token update positions from text-token states; text-state norm is used in the scaling rule. Same text prompts do not establish cross-model hidden-state alignment.

**Reported setup/results:** Qwen3-VL-2B carrier with Qwen3-VL-4B or InternVL3.5-4B provider; MLVU development set and Video-MME without subtitles; normally 8 provider + 8 carrier frames. StateKV is slower than carrier-only inference but faster than the evaluated text-description baseline. Accuracy effects are modest and task-dependent: some MLVU categories improve while others fall; Video-MME long-video scores improve slightly while short/medium groups can decline. A 16-provider/8-carrier comparison changes observation budget and is not a matched-information attribution test.

**Limitations from the full paper:** no sufficient repeated-run statistics for uncertainty/significance; no matched-observation and matched-compute control for extra provider frames; no multi-provider scaling evidence; no arbitrary-family generalization; total system memory/compute still includes provider weights/cache/projector/intermediates even though carrier cache length is unchanged. The evidence is not an Android/mobile deployment result and does not demonstrate free-generation equivalence.

**V14 testable implication:** keep A5 visual/UI input as a separately sourced temporal stream. For any later provider→carrier visual latent experiment, record actual visual-token positions and temporal provenance, align/project only to explicit carrier visual positions, use a bounded gated residual, and compare carrier-only, text-summary, state-transfer, matched-observation and matched-compute controls. Measure both carrier-cache and total-system RAM/latency. Do not reuse this method for B1/B2 text LFM2 or assume a common latent space; the evaluated 2B/4B VLMs are not Redmi Note 10 Pro candidates. No implementation change or model download authorized by this paper alone.

**Sources:** official arXiv record `https://arxiv.org/abs/2611.22304`; full-text mirror `https://arxiv.cnoctave.top/pdf/2611.22304` (reviewed sections 1–5, equations 1–14, tables 1–5 and limitations).

## R-162 — Read-only K/V state-effect consumption and transport-integrity boundary (2026-11-26)

**Implementation checkpoint:** Perception PR #2524, branch `research-perception/v14-kv-snapshot-consumer-20261126-run35`, code/test head `8f7c73065e8f92e5988fe12fa88038dc41ece530`, stacked on #2519. The task-utility consumer now validates that identical receiver-input digests reproduce identical sampled one-layer K/V signatures, rejects partial snapshot coverage and geometry drift, and reports aggregate candidate-vs-NO_MESSAGE / candidate-vs-EXACT_MESSAGE sampled-state differences. It does not persist raw K/V. The teacher-forced likelihood utility gate is unchanged; sampled K/V difference is diagnostic only. Core #2523's exact source confirms a manual local-TTY one-shot diagnostic route, not a normal-turn hook; ordinary user chat remains unconnected.

**Research 1 — integrity:** L. Brito & C. Baquero, *When Latent Agents Lie: KV-Cache Integrity in Multi-Agent LLM Collaboration*, arXiv:2606.28958, submitted 2026-06-27 (preprint; no peer-reviewed venue identified in the inspected record). Full-text review covered the experiment, defense, limitations and open-science sections. The strongest bounded result is an HMAC-SHA256 manifest binding specialist identity, record/session, model, visible-commitment hash, tensor metadata and payload digest: artifact replay accepted 774/774 honest payloads and rejected 295/295 tampered payloads. This addresses post-handoff transport substitution under an uncompromised key, not compromised endpoints, remote attestation, semantic malicious specialists or key compromise. Magnitude/learned quarantine was brittle against adaptive norm-matched white-box attacks; compact/low-bandwidth latent communication remained open. The paper describes an artifact package but the inspected public record did not establish a maintained source repository or a reuse license. Therefore no code was copied.

**Research 2 — transfer feasibility:** Xingyu Qu et al., *CacheBridge: Efficient Cross-Model KV Cache Transfer*, arXiv:2609.00891, submitted 2026-09-01, revised 2026-11-03 (preprint; no peer-reviewed venue identified in the inspected record). Full paper/README review: architecture-indexed head matching plus attention-readout calibration improves the evaluated same-family dense-GQA transfers; reported Qwen3 14B→32B retention and mapper/latency gains use an eight-GPU H800 host. The paper does not validate LFM2 hybrid attention, heterogeneous recurrent state, multi-turn semantic quality or mobile execution. The public repository `WHU-XingyuQu/CacheBridge` explicitly says its project license is pending; its Qwen3 14B→32B mapper is 512.5 MiB and its full serving recipe requires CUDA/SGLang. No code, weights or mapper are eligible for V14 reuse until licensing and model-family compatibility are resolved.

**Concrete V14 consequence:** Keep the present K/V receipt as a one-layer/one-sequence local diagnostic. SHA-256 equality is not authentication and a changed digest is not semantic utility. Before any future B3 transport/write, define a trusted key owner and a canonical MAC-bound manifest over source organ, destination organ, session/event/generation, source/receiver model revisions, adapter revision, visible-source commitment, tensor geometry, positions and payload digest; fail closed on mismatch. Do not rely on endpoint anomaly magnitude alone. This research does not authorize transport, write access, model download, B3 activation or weight updates.

**Evidence/limits:** exact CI on `8f7c73065e8f92e5988fe12fa88038dc41ece530`: focused task-score/condition suite 26/26 PASS on Python 3.13 and 3.14; pinned llama.cpp Linux build/selftest PASS; Android arm64 cross-compile PASS (compile only); RuntimeDeploy offline Python 3.11/3.14 PASS; privacy scan CLEAN. Shared staged/integrated remains FAIL on the Core-owned source pin for `v13/native_latent_receiver.py`. LOCAL_LINUX scratch helper/aggregate reproduction 5/5 PASS; full Aii checkout/pytest NOT_RUN (no checkout mounted; GitHub DNS unavailable). No real GGUF cohort, answer correctness, trained latent coupling, gradients/retention, Android/Termux or Redmi proof. B3 OFF; REDMI_UNVERIFIED; NOT_RELEASED.

**Sources:** https://arxiv.org/abs/2606.28958 ; https://arxiv.org/abs/2609.00891 ; https://github.com/WHU-XingyuQu/CacheBridge ; https://github.com/WHU-XingyuQu/CacheBridge/blob/main/LICENSE_STATUS.md

## R-163 — Hybrid latent handoff must account for recurrent state, not only attention K/V (2026-11-26)

**Primary paper reviewed:** Simon P. Villani, *LatentPort: Beyond KV Cache — Cross-Model Transfer of Recurrent Memory in Hybrid Language Models*, arXiv:2609.25053 (first submitted 2026-09-07; author-hosted arXiv preprint; no peer-reviewed venue or maintained public code/license was identified in the inspected record). Full-text review covered the method, experiments, limitations and runtime appendix. No code, weights or datasets were downloaded or reused.

**Main result and exact scope:** one directed Qwen3.5-4B-Base → Qwen3.5-9B-Base pair with matched Gated DeltaNet (GDN) persistent-state geometry. The models have 24 GDN layers plus 8 full-attention layers; each GDN layer carries a recurrent matrix of shape 32×128×128 (FP32) and convolution history 8192×4 (BF16). The selected handoff translates attention K/V but directly reuses the recurrent and convolution package, including initialization semantics. On 64 PG19 documents with a 4K prefix and 64 teacher-forced continuation tokens, adding the GDN package to fixed translated K/V lowers NLL by 0.7473 nats/token (paired 95% document-bootstrap CI [0.6921, 0.8047]); all 64 documents improve. The direct recurrent/conv package outperforms the tested learned recurrent/conv maps in that pair.

**Do not overstate it:** the paper's full-state correction reaches excess NLL 0.076, JS 0.022 and native-context-recovery 0.918 on a separate 64-document set, but misses its preregistered near-native gate. The 16K branch was not run; free-generation equivalence and downstream task success are unproven. The primary contrast does not isolate recurrent matrices from convolution history and initialization semantics. Only one direction and one geometry-matched Qwen sibling pair were tested. The 4K full tensor payload is 186,122,240 bytes; the E001 operator bundle is 322,222,408 bytes. Both experiments use BF16 Base models and an RTX 5090 with 32,607 MiB reported VRAM. These sizes are not LFM2 measurements, but they rule out assuming a similar full-state transfer is mobile-cheap.

**Related primary result:** Yuzhe Liu, Haolin Tian & Tonghan Wang, *ACCT: Asymmetric Cross-LLM Context Transfer*, arXiv:2610.42116 (submitted 2026-10-30; preprint). Its same-family cross-scale method separates query-aware token selection (Cartographer), global per-layer/head cache budgeting (Allocator), and target-K/V construction (Compiler). It reports matching or exceeding target-native inference while reducing cache tokens by 75%, with 6.5–21.2× cache-conversion speed over target prefill at ~19K context. This is still a same-family cache-transfer result, not evidence for LFM2 or cross-family recurrent-state portability.

**Concrete V14 consequence:** the current #2524 consumer validates only one attention-layer/one-sequence K/V snapshot and explicitly reports recurrent_state_included=false. That is an honest partial diagnostic, not a complete LFM2 hybrid latent. Before any cross-organ activation claim, Core must inventory the exact pinned LFM2/LFM2MOE memory components and metadata separately: attention K/V, recurrent state, convolution/history buffers, initialization/previous-state flags, positions and stream/sequence mapping. First prove same-model capture/restore fidelity and no-mutation on the exact llama.cpp pin; then compare K/V-only against complete hybrid-state transfer under wrong-donor, zero, shuffle and empty-state controls. Direct recurrent-state reuse is only a hypothesis if exact functional geometry and update semantics match; otherwise each component needs its own learned adapter and held-out behavioral validation. Do not copy Qwen GDN tensors or assume a common state ABI.

**Mobile/licensing boundary:** the paper's tested Qwen Base checkpoints, BF16 state payload and RTX 5090 environment do not establish Redmi/ARM feasibility. No public implementation or code license was found; no code/weights are eligible for reuse. The separate ACCT preprint also supplies no LFM2 proof or mobile artifact. No model download, weight update, production swap, cache write or B3 enablement is authorized.

**Status:** RESEARCHED_FROM_FULLTEXT / HYBRID_STATE_GAP_IDENTIFIED / LFM2_STATE_CAPTURE_NOT_IMPLEMENTED / REAL_GGUF_UNVERIFIED / REDMI_UNVERIFIED / B3_OFF.

**Sources:** https://arxiv.org/abs/2609.25053 ; https://arxiv.org/abs/2610.42116

## R-164 — Exact LFM2 hybrid-state path in pinned llama.cpp (2026-11-26)

**Primary implementation inspected:** ggml-org/llama.cpp revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 (repository LICENSE is MIT). This is source inspection at the exact receiver pin, not a native model execution.

- src/models/lfm2.cpp (blob 07b71ccd3a60f87a74f543d5bf637c8a67d9fa9f) sets each layer recurrent when n_head_kv(il)==0. Recurrent LFM2 layers instantiate shortconv weights. build_shortconv_block reads the layer history through llama_memory_recurrent_context::get_r_l(il), concatenates it to the current convolution input, then writes the final/rollback history back to that recurrent cache.
- src/llama-model.cpp (blob 3b2536283c5712de811f82cdef6390f7499b95d4) constructs llama_memory_hybrid for hybrid architectures. src/llama-memory-hybrid.cpp (blob 42c7381a9e6fa507c925ba66a35a7e433c4447b8) owns both mem_attn (llama_kv_cache) and mem_recr (llama_memory_recurrent); state_write/state_read serialize both components unless the caller explicitly requests PARTIAL_ONLY. Therefore LFM2's non-attention shortconv history is part of sequence state, not an optional metadata detail.
- include/llama.h (blob 3ab935939c6d183e5862aba93f346691e658403b) exposes llama_state_seq_get_size/get_data/set_data. src/llama-context.cpp (blob 6334f3ccab304749bbf7b51362dee7c9348771d7) synchronizes before sequence get_data and delegates sequence read/write to the memory module; for llama_memory_hybrid this includes both attention K/V and recurrent shortconv state. This is a plausible exact-pinned same-model roundtrip API. It is not a cross-model compatibility guarantee or a learned latent interface.

**Target model architecture check:** the official LiquidAI LFM2.5-1.2B-Base config at commit 8bc7cff62e8ee875578cf2af58781ad074d4e145 reports 16 layers, 10 conv layers, 6 full-attention layers, hidden_size 2048, num_key_value_heads 8 and conv_L_cache 3. The Instruct GGUF model card identifies QAD Q4_0 as a distinct 696 MB artifact. With 10 shortconv layers and a 2- or 3-step FP32 history, a simple tensor-only estimate is roughly 160–240 KiB per sequence before alignment, sequence metadata and rollback slots. This is [gerechnet], not measured; the exact serialized byte count must come from llama_state_seq_get_size on the actual GGUF and runtime settings.

**License/model provenance:** the QAD GGUF repository labels the model LFM1.0 and includes the LFM Open License v1.0. Its text conditions commercial use on the relevant legal entity remaining below USD 10 million annual revenue; this is not an unrestricted MIT/Apache-style model license. The QAD README says the FP32 source checkpoint is for fine-tuning/experimentation and that published QAD results apply to Q4_0, not direct FP32/BF16 inference. No model was downloaded, changed or swapped.

**Concrete V14 implementation consequence:** replace the assumption that a one-layer K/V receipt approximates all LFM2 state with two separate gates: (1) the current K/V diagnostic remains explicitly partial; (2) Core builds a native same-model sequence-state roundtrip using llama_state_seq_get_size/get_data/set_data on one exact pinned LFM2.5-1.2B QAD GGUF. Prefill a fixed prompt in context A, capture sequence 0, restore into fresh context B with identical model SHA/revision/context parameters, then compare continuation token logprobs or logits for fixed next tokens. Add truncated/corrupted state, wrong model hash, wrong llama.cpp revision, wrong sequence, and mismatched context-parameter negatives. Record serialized bytes, capture/restore latency and RSS. Do not persist raw state or write into the installed runtime. Only after same-model fidelity passes should B1/B2 same-architecture but different-weight transfer be evaluated against zero, shuffled, wrong-donor and no-message controls.

**Status:** EXACT_LFM2_SHORTCONV_STATE_PATH_IDENTIFIED / PUBLIC_SEQUENCE_STATE_API_FOUND / SAME_MODEL_ROUNDTRIP_NOT_IMPLEMENTED / REAL_GGUF_NOT_RUN / REDMI_UNVERIFIED / B3_OFF.

**Sources:** https://github.com/ggml-org/llama.cpp/tree/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4 ; https://huggingface.co/LiquidAI/LFM2.5-1.2B-Base/blob/8bc7cff62e8ee875578cf2af58781ad074d4e145/config.json ; https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/blob/main/qad/README.md ; https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/blob/main/LICENSE


## R-165 — 2026-11-26 — LFM2 full-hybrid sequence-state roundtrip implementation

**Question:** Can the pinned llama.cpp sequence-state API restore the complete LFM2 receiver memory, including recurrent short-convolution history, into a fresh context of the same model, and can that be checked without exporting or persisting raw state?

**Primary OSS source audit (exact pin b29c606e28a01b1bc8c1351026a0fa6e616bf6c4):**
- include/llama.h declares llama_state_seq_get_size, llama_state_seq_get_data and llama_state_seq_set_data.
- src/llama-context.cpp delegates sequence state serialization to the memory implementation and returns the consumed byte count. Truncated input is rejected by the read path.
- src/llama-memory-hybrid.cpp serializes both mem_attn (attention/KV) and mem_recr (recurrent state), except when a caller explicitly requests partial-only state.
- src/models/lfm2.cpp contains the LFM2 recurrent short-convolution state path. This is why a K/V-only snapshot cannot represent the complete LFM2 sequence state.
- The pinned LICENSE is MIT. No upstream source was copied wholesale; the receiver uses the public API.
- This is an implementation-source audit, not a new paper review. No paper is claimed as newly read in this run.

**Code added on Perception PR #2524, exact branch head 076a973eaad808b537c7f74337464d02cf41d633:**
- Native C++ matrix runner now has an explicit, opt-in --hybrid-state-roundtrip path, restricted to general.architecture values beginning with lfm2; default behavior remains unchanged.
- The probe creates two fresh, identically configured small contexts (one sequence, one-token batches, context bounded by the fixed continuation length), prefills BOS, captures sequence 0, attempts a truncated restore as a negative control, clears the destination, performs a full restore, then teacher-forces the same continuation into both contexts and compares the full next-token logits after each continuation token.
- The comparison is same-model/same-weight state restoration only. It does not transfer a sender model's hidden state or prove cross-model latent compatibility.
- State buffer is capped at 16 MiB, hashed in memory and zeroized. Raw state bytes are not returned or persisted. The probe reports only byte counts, durations, hashes and fidelity metrics; it does not touch the installed runtime, edit weights, train, or enable production routing.
- Python binds the receipt to receiver model SHA/revision, receiver tokenizer revision, pinned llama.cpp revision, native binary SHA, task context SHA, NO_MESSAGE input SHA and target-token-ID SHA. The receipt is attached to the NO_MESSAGE condition and passed through native_receiver_task_matrix_bridge; the opt-in is false by default.
- The hybrid-state validator now requires a successful truncated-state rejection negative control and enforces the 16 MiB bound.

**Exact-head CI 45813438280 (head 076a973...):**
- Python 3.13 focused tests: PASS; staged receiver/deploy-chain compile: PASS; public-diff privacy scan: CLEAN.
- Python 3.14 focused tests: PASS; staged receiver/deploy-chain compile: PASS; public-diff privacy scan: CLEAN.
- Android arm64-v8a cross-compile step: PASS (review-only artifact upload was still running at last poll; this is not a device test).
- Linux pinned llama.cpp build: IN_PROGRESS at last poll.
- Shared source-tap gate: FAIL/BLOCKED because this Perception branch does not contain the Core-owned native_receiver_matrix_runtime.py producer hook. The error is the expected cross-lane integration gap, not a focused Python test failure. Core PR #2525 must rebase and expose the opt-in flag.
- LOCAL_LINUX full checkout/pytest: BLOCKED; no Aii checkout is mounted in the local runtime and GitHub DNS is unavailable. CI is not reported as a local test.

**Acceptance limits:** no real GGUF execution yet; no measured RSS/TTFT or native logits on a model; no Redmi/Termux receipt; no release/deployment. REDMI_UNVERIFIED, NOT_RELEASED, B3_OFF. The result is a native implementation candidate plus CI compile/test evidence, not a verified model run, not trained latent coupling and not a Canon completion claim.

**Next executable step:** Core rebases #2525 onto the latest #2524 head and exposes the diagnostic behind a separate explicit local-lab flag (default OFF). Then run it on an already-present, explicitly approved LFM2 GGUF with a fixed 32–64-token continuation; record exact model/binary/context hashes, state bytes, capture/restore time, peak RSS, top-1 agreement, max/RMS logit difference and truncated-restore rejection. Only after that same-model gate passes should the roundtrip be extended from BOS to a real LATENT_CANDIDATE prefill and then to different-weight sender/receiver experiments.


## R-166 — Draft-KV: content-dependent latent communication and the information-use gap (2026-11-26)

**Primary paper:** Wu et al., *Draft-KV: Learning Useful Latent Communication Between Language Models*, arXiv:2609.34754v1, first submitted 2026-09-28. Full arXiv HTML and the official project repository were inspected. This is an arXiv preprint; no peer-reviewed venue was identified.

**Finding:** higher receiver accuracy does not establish that a receiver used the sharer's message. The paper reports that in five audited method–dataset pairs, replacing each message with one from an unrelated question changes accuracy by at most 0.60 percentage points even though communication adds up to 15.44 points over receiver-only. Draft-KV separates system gain G = A_M - A_R from pairing gain P = A_M - A_D. Its method passes only the KV states produced while a frozen sharer drafts an answer, maps them through a 1.05M-parameter gated bridge at four communication layers, and reads them as separate side memory. The receiver and sharer backbones stay frozen. Training progresses through reconstruction (16k updates), answer alignment (4k) and task alignment (5k), with reconstruction replay and a one-sided guard against harm from a deranged message.

**Reported evidence / boundaries:** Qwen3-8B → Qwen2.5-0.5B-Instruct on MMLU-Redux: 78.04% Matched, 36.40% Deranged, 37.45% receiver-only. The repository reports content-dependent gains in all 35 Public settings and 14/14 Private settings. These are the authors' reported experiments, not independent replication. The paper's compute setup is one 96-GB GPU, BF16, PyTorch 2.6.0, CUDA 12.4 and Transformers 4.52.4; model weights dominate memory. This is not a Redmi/Termux recipe.

**OSS / licence / reuse audit:** official repository https://github.com/Svardfox/Draft-KV, inspected at main commit e369f1b2629875642fe5a87feb4d432c6f4971b8. Code licence: Apache-2.0 (LICENSE blob 261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64). README blob b1c5794642818d232d2029c95e44d11dabc814f6; pinned environment blob 7206060b1c0fb655d789c262c8fb153c59fa878f; method doc blob 07a93ff6bf5ef57e605334ea7b8674ef8d7144ee; Stage-3 doc blob 77b0090e2ddc7451b0fbb2c79df46bcfd4dd901c. The repository README says trained bridge checkpoints are still “coming soon”; model and dataset licences remain separate from the code licence. No code, weights or dependency were copied into Aii.

**V14 adaptation implemented on Perception PR #2524:** the existing eight-condition task-utility consumer now emits information_use_audit, explicitly separating candidate system gain versus NO_MESSAGE from source-specificity gain versus the existing ENTITY_SUBSTITUTION counterfactual. Both gates require the complete held-out cohort. If system gain passes but the counterfactual gain does not, the result is SYSTEM_GAIN_WITHOUT_ENTITY_SPECIFIC_SIGNAL; one positive overall score can no longer be described as evidence that the message content mattered. Three synthetic regressions cover that gap, positive specificity and insufficient holdout. This is deliberately not the paper's unrelated-question no-fixed-point derangement protocol: full_derangement_tested=false, semantic_use_proven=false, production_route=false, and both authorities remain zero. A full donor-permutation condition remains OPEN.

**Status:** FULL_TEXT_READ / OSS_APACHE_2_VERIFIED / MOBILE_TRAINING_NOT_APPLICABLE / INFORMATION_USE_AUDIT_CODE_PRESENT / SYNTHETIC_REGRESSION_PENDING_EXACT_CI / FULL_DERANGEMENT_OPEN / REAL_GGUF_UNVERIFIED / REDMI_UNVERIFIED / B3_OFF.

**Sources:** https://arxiv.org/abs/2609.34754 ; https://github.com/Svardfox/Draft-KV ; https://github.com/Svardfox/Draft-KV/blob/main/LICENSE ; https://github.com/Svardfox/Draft-KV/blob/main/docs/METHOD.md ; https://github.com/Svardfox/Draft-KV/blob/main/docs/STAGE3.md


## R-167 — Hybrid State Transfer: full-state mapping needs continuation compatibility (2026-11-26)

**Primary paper:** Cai et al., *Beyond K/V Caches: Cross-Model State Handoff in Hybrid Linear-Attention LLMs*, arXiv:2611.08133, submitted 2026-11-05. Full arXiv HTML reviewed. This is a preprint; no peer-reviewed venue or official maintained implementation/licence was identified in the primary source or the accompanying search.

**Method:** within Qwen3.5 hybrid models, transfer all three state families at one aligned prefix boundary: full-attention K/V caches, recurrent Gated DeltaNet matrices (REC), and ordered convolution histories (Conv). Pair-specific structural maps are then functionally calibrated through the frozen target's continuation. The paper shows that Conv perturbations can alter later REC updates even after convolution slots are overwritten; lower local REC reconstruction error can still produce worse continuation KL. That is a direct warning against accepting latent adapters on reconstruction or shape parity alone.

**Reported evidence / limits:** Qwen3.5 4B→27B and 9B→27B achieve 89.88% and 94.11% mean task retention over five benchmarks. The reported 21.66×/21.91× speedups are handoff-body timings on synthetic 16K inputs with source caches already available; they exclude source prefill, vocabulary projection and answer generation. Evaluation used two 80-GB A800 GPUs, batch 1, BF16 weights/KV and FP32 recurrent state. The authors explicitly limit evidence to Qwen3.5 with Gated DeltaNet; other linear-attention families, MoE and broad long-context use remain untested.

**V14 consequence:** the current LFM2 llama_state_seq_get_size/get_data/set_data same-model roundtrip is only a state-serialization/fidelity prerequisite. It is not a cross-model mapping. Any future LFM2/B1/B2 transfer needs architecture-specific K/V + recurrent/shortconv correspondence, identical prefix boundaries/position metadata, and continuation-level output/task tests with wrong-donor, zero and native-target controls. Do not accept a low state-reconstruction error as utility.

**Status:** FULL_TEXT_READ / PREPRINT / NO_OFFICIAL_OSS_REUSE_FOUND / QWEN3_5_ONLY / LFM2_TRANSFER_UNVERIFIED / REAL_GGUF_UNVERIFIED / REDMI_UNVERIFIED / B3_OFF.

**Sources:** https://arxiv.org/abs/2611.08133



## Run 47 exact-CI closeout — 2026-11-26

The exact code/test head 7bd80e419c851471d95b44cc032efe205a23ab91 completed CI with the following results:

- V14 native latent receiver workflow 45856881120: FAIL at the shared staged Runtime source-tap identity test. Python 3.13 and 3.14 each reported 83 passed / 1 failed in the focused receiver suite. The three new information-use audit regressions passed; the single failure is the stage-composition test failing on the Core-owned observer fairness pin for v13/cognition.py.
- V13 staged context and integrated regression workflow 45856880943: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. The failures converge on the same Core-owned ValueError: observer fairness source changed: v13/cognition.py. Two migration assertions also remain PARTIAL rather than UPDATED.
- Native build evidence in 45856881120: pinned Linux API build PASS; Android arm64 cross-compile PASS (compile only, not device proof).
- V13 RuntimeDeploy offline integrity 45856880964: PASS. This does not install or update a phone.
- Public repository privacy scan in the failing workflow: CLEAN.

This is an integration failure outside the two files changed by Run 47. Do not weaken or bypass the source pin. Core must refresh its recovery/observer source pin chain and rebase #2525 onto the current Perception branch. The information-use code/test slice itself passed in both Python versions.


## R-168 — Latent-in-the-Middle: cross-model handoffs change safety, privacy and capability (2026-11-26)

**Primary source:** Baser, Jain, Yeo Hui Min, Yang, Muthu Selva Annamalai & Divakaran, *Latent-in-the-Middle: On the Security of Cross-Model Latent Communication in Multi-Agent Systems*, arXiv:2611.34278v1, submitted 2026-11-25. Full arXiv HTML reviewed: Sections 1–10 and Appendices A–D. This is a preprint, not a peer-reviewed result as of 2026-11-26. No official public Chasm/HandoffGuard implementation repository or code/weight licence was identified in the primary paper or search; do not reuse an unlicensed implementation.

**Experimental scope:** Qwen3, Llama 3 and Ministral 3 model families; 3B–32B; four mapper types (ridge, MLP, CacheBridge, SwaT), two calibration corpora and 24 within-family settings plus cross-family SwaT pairs. Experiments used BF16, PyTorch/Transformers and NVIDIA H200 GPUs. The prompt-injection study used Meta-SecAlign-8B and Llama-3.2-3B. This is not evidence for LFM2, GGUF, 6-GB Android, or V14 hardware.

**Main results:** A target with 0.4% native AlpacaFarm injection success reached up to 44.2% through SwaT (Chat); other default mappers reached 26.2–29.7%. A de-aligned source increased HarmBench ASR by 16.3–45.4 percentage points across all 24 settings. Template attacks gained up to 69.2 pp; mapper-aware GCG reached 92.5% on Llama versus 37.5% for ordinary target-only GCG. Repeated cache remapping without intervening generation raised ASR in 16/24 settings; after six hops GSM8K fell 28.0–92.4 points, with 16/24 chains solving at most 10%. The no-generation switching protocol is a limitation, not a realistic multi-turn estimate.

**Defence and privacy limits:** HandoffGuard p1 brought the tested de-aligned-source HarmBench ASR to within 4.5 points of native on all three pairs, but a guard-aware source LoRA still reached 73.3–87.5% ASR. p2 over-refused (including 87.4% of benign Llama role-play in one setting); its injection reduction was partly fail-closed refusal rather than restoration of the input-role defence. The Ministral-14B guard had about 10M parameters and was trained for 1,000 steps on H200; this is not an Android-ready drop-in. Mapped-cache inversion recovered 94.6% of tokens and all ten synthetic record fields in 500 Qwen records at layer 0. Poisoned mapper calibration could create trigger backdoors while ordinary fit/utility checks remained deceptively acceptable.

**V14 consequence:** A foreign latent/cache handoff is untrusted input even when the target model and mapper shapes match. A SHA-bound receipt provides integrity of recorded bytes, not cryptographic producer authentication (the current native receiver receipt builder states this explicitly). Future B3 acceptance must separately cover source/model/mapper provenance and authenticity, transport integrity, trust/consent labels, target-side treatment of untrusted segments, prompt-injection and jailbreak red-teaming, cache privacy/inversion, poisoned calibration/backdoors, repeated-hop capability retention, and benign utility/over-refusal. A target-side guard is a research direction, not a proven solution; do not port the 10M-parameter H200 result to Android without a measured smaller alternative and adaptive-attacker tests. Keep B3 OFF.

**Run 48 implementation link:** PR #2524 extends the existing native receiver information-use audit so CONTENT_SPECIFIC_SIGNAL requires a complete session-local, cross-family, no-fixed-point OOD donor permutation plus a positive matched-versus-deranged teacher-forced target-logprob delta. Invalid/external/duplicate/cross-session/same-family donors remain diagnostic failures. This is source-pairing evidence only; it does not authenticate a source, prove semantic use or answer correctness, add a safety guard, enable production routing, or grant learning authority. Exact exact-head CI 45861303391 completed: the focused Perception matrix/task-score tests were 49/49 PASS on both Python 3.13 and 3.14; the only additional failure in each job is the Core-owned stage-composition test rejecting the stale observer fairness pin for v13/cognition.py. Linux pinned API build PASS; Android arm64 cross-compile PASS (compile only); privacy scan CLEAN. Shared staged/integrated run 45861303423 remains blocked by the same Core source pin (20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; two migration assertions report PARTIAL). RuntimeDeploy offline integrity 45861303433 PASS on Python 3.11 and 3.14. LOCAL_LINUX isolated helper tests 6/6 PASS and py_compile 2/2 PASS; full local repository suite NOT_RUN because no checkout is mounted and GitHub DNS is unavailable. Redmi and real GGUF remain unverified.

**Status:** FULL_TEXT_READ / PREPRINT / NO_OFFICIAL_OSS_REUSE_FOUND / H200_ONLY_SECURITY_EVIDENCE / NO_LFM2_OR_ANDROID_GENERALIZATION / SOURCE_AUTHENTICATION_OPEN / REDMI_UNVERIFIED / B3_OFF.

**Source:** https://arxiv.org/abs/2611.34278


## Run 48 exact-CI closeout — 2026-11-26

Code/test head: `91cae713b409e1b5e95bc06c446a5152e726cbd9`. Perception utility blob: `7d90a187f537a62d08ae3d0b0eefa23e3536b81c`; test blob: `fb559b3214df987695d1b5a48e3174681fe16302`.

- The exact Perception task-score + condition-matrix suite passed 49/49 on Python 3.13 and 3.14. The additional native workflow stage-composition test failed because the Core-owned `integrated_observer_fair_budget_candidate_20261116.py` rejects the current `v13/cognition.py` bytes against its stale source pin. This is outside the two changed Perception files; do not weaken the pin.
- Shared staged/integrated workflow 45861303423: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Failures converge on the same Core-owned observer fairness pin; two migration assertions report PARTIAL rather than UPDATED.
- Pinned Linux native API build PASS; Android arm64 cross-compile PASS (compile only); public privacy scan CLEAN.
- RuntimeDeploy offline integrity 45861303433 PASS on Python 3.11 and 3.14. It is not a phone deployment.
- LOCAL_LINUX CPython 3.13.5 isolated donor-permutation reproduction 6/6 PASS; `py_compile` 2/2 PASS. Full local Aii checkout/pytest NOT_RUN: no mounted checkout and GitHub DNS resolution unavailable.
- B3 remains OFF. No GGUF execution, native Android/Termux/Redmi proof, release or deployment. Last device observation is historical; read-only owner relay #978/#979 had NO_LIVE_RECEIPT at last poll.


## R-169 — Translating KV Caches Between Hybrid-Attention Language Models (2026-11-26)

**Source and reading status:** Povilas Kvedaras and Tomas Rasymas, Hostinger Research, *Translating KV Caches Between Hybrid-Attention Language Models: MLA Latents, Linear-Attention States and Sparse-Attention Indexers*, arXiv:2611.12062v1, submitted 2026-11-09; preprint, full HTML text reviewed (methods, experiments, limitations and appendices). The paper carries CC BY 4.0. This is not a peer-reviewed acceptance claim.

**Technical result:** The paper treats cache contents as different objects, not one generic latent. GQA K/V and MLA latents are token-wise; recurrent KDA/GDN state is prompt-level and cannot be reconstructed by a token-wise map; sparse-attention indexer keys are an additional discrete-selection object. Its measured recipes are object-specific: per-layer maps for token-wise objects, copy plus closed-form correction for same-geometry recurrent state, and replay through the target's own recurrence when the source has no compatible state. Token identity can be necessary for exact recall. Teacher-forced KL is paired with task probes because KL alone hid a needle-recall failure in one experiment.

**Evidence and limits:** The hybrid experiments use 16–48B-class active models on GPU. Same-geometry Qwen hybrid pairs reached the authors' native-level criterion in both directions; the 64K TTFT speedups are serving/GPU results, not mobile measurements. Pair C's sparse-indexer rehearsal is one direction and one seed. The authors explicitly label 300B+ extrapolation as a hypothesis. One tokenizer per family, single-seed sub-experiments, Pair-A forward quality gaps, cache inversion/privacy, source-style/safety leakage and repeated-hop degradation remain material limitations. The authors state that translator code and trained weights are held in internal research repositories; no public code or weights were available for reuse. Paper licence does not license those unpublished assets.

**V14 consequence:** This supports keeping K/V, MLA, recurrent state and indexer channels as separate typed objects with separate acceptance tests. A same-model sequence-state restore is a necessary serialization baseline, not cross-model latent coupling. Cross-model transfer still requires trained object-specific maps, compatible token/position handling, recurrent-state copy/correction or target-recurrence replay, held-out task probes, free-running/generated-answer checks, provenance/authenticity and adversarial privacy/safety tests. The paper does not validate LFM2, ARM/Android or Redmi.

**Run 49 implementation link:** PR #2524 now performs its opt-in LFM2 full-hybrid state roundtrip after decoding the actual LATENT_CANDIDATE matrix, rather than priming the source context with BOS. Schema v2 binds prefill condition, row count, float32 input digest and successful prefill decode status; continuation positions begin after the candidate rows. The Python validator and Runtime bridge attach/read the receipt on LATENT_CANDIDATE. This remains same-model, read-only diagnostic evidence; no cross-model transfer, training, persistent state, production route or B3 authority is added.

**Run 49 evidence:** PR #2524 code/test head 1417250fb28c4e30c5c4e0d8150e673248ad10a8; initial handoff commit 82d79103af7aa80d1ec29b688ec2f3ecca78acc8 (subsequent docs/board commits follow on the same branch); Exact GitHub Actions on code/test SHA 1417250fb28c4e30c5c4e0d8150e673248ad10a8: native receiver 45888866164 completed FAILURE only at the Core-owned observer fairness pin (test_native_latent_receiver_stage.py::test_native_receiver_is_composed_and_runtime_contracts_pass; ValueError: observer fairness source changed: v13/cognition.py). The focused condition-matrix/task-score suite passed 52/52 on Python 3.13 and 52/52 on Python 3.14; the extended receiver suite passed 92 tests and failed only that same Core pin on each version. py_compile passed. The exact pinned llama.cpp Linux API build/selftest passed; Android arm64-v8a cross-compile passed (compile-only); public privacy scan CLEAN. Staged/integrated 45888866275 completed FAILURE: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests, due to the same Core observer-fairness pin plus two migration assertions returning PARTIAL instead of UPDATED. RuntimeDeploy offline integrity 45888866345 completed SUCCESS on Python 3.11 and 3.14. These are CI results, not local full-repository tests, real GGUF execution or Redmi proof. LOCAL_LINUX CPython 3.13.5 scratch contract reproduction 6/6 PASS; standalone C++ float32-little-endian digest helper compile/run PASS. Full repository pytest/native build NOT_RUN because no local Aii checkout is mounted and GitHub DNS resolution fails. No real GGUF, Termux/Redmi or deployment proof; REDMI_UNVERIFIED; B3 OFF.

**Status:** FULL_TEXT_READ / PREPRINT / PAPER_CC_BY_4.0 / NO_PUBLIC_TRANSLATOR_CODE_OR_WEIGHTS / OBJECT_SPECIFIC_TRANSFER / SAME_MODEL_BASELINE_ONLY / NO_LFM2_OR_ANDROID_GENERALIZATION / REDMI_UNVERIFIED / B3_OFF.

**Source:** https://arxiv.org/abs/2611.12062


## R-170 — Latent-in-the-Middle: security of cross-model latent communication

**Paper:** Manit Baser, Vyoman Jain, Rachel Yeo Hui Min, Xianglin Yang, Meenatchi Sundaram Muthu Selva Annamalai, Dinil Mon Divakaran, *Latent-in-the-Middle: On the Security of Cross-Model Latent Communication in Multi-Agent Systems*, arXiv:2611.34278v1, submitted 2026-11-25. Preprint; not peer-reviewed. Full text reviewed: threat model, mapper setup, attack results, HandoffGuard, limitations and conclusion.

**Evidence:** The authors test three model families (Ministral 3 8B→14B, Qwen3 14B→32B, Llama 3.2 3B→3.1 8B), four mapper families (ridge, MLP, CacheBridge, SwaT), and two calibration corpora (FineWeb-Edu and UltraChat), yielding 24 settings. Mapper fitting uses 500 sequences of 1,024 tokens per calibration corpus. The reported native prompt-injection success of 0.4% for Meta-SecAlign-8B rises as high as 44.2% after a mapped-cache handoff. Untrusted/de-aligned sources raise harmful-response rates across the tested settings; mapper-aware optimization can exceed ordinary target-only GCG. Their target-side HandoffGuard p1 brings the tested de-aligned-source HarmBench rate to within 4.5 percentage points of native on the three main pairs; stronger p2 reduces rates further but over-refuses. A guard-aware LoRA attacker still reaches 73.3–87.5% ASR in 300 steps, so the guard is not a substitute for source authentication.

**Limits / mobile relevance:** Mapper and model experiments are 3B–32B-class; the mapper-aware GCG runs use an NVIDIA H200. The switching experiment does not generate tokens between switches; realistic multi-turn switching, cache composition and latency/utility/safety trade-offs are left open. Prompt-injection mitigation partly works by refusing, not by restoring the target's original input-role defense. No LFM2, ARM, Android or Redmi result is reported. The arXiv record/paper did not identify an official implementation repository, released weights or a reusable software/weight licence; no code or weights reused.

**V14 consequence:** A mapped latent/KV cache is an untrusted input channel, not a trust or permission boundary. Before any B3/foreign-state activation, require authenticated producer identity (not only a hash), exact source/target/mapper manifests, session/generation and position binding, integrity/expiry, explicit trust/consent labels, target-side safety evaluation, and negative controls for aligned vs de-aligned donors, wrong mapper, prompt injection, mapper-aware attack, privacy leakage and multi-hop retention. Foreign latent state must never grant tool/action/OS permission or become verified evidence by itself. Keep B3 OFF until these gates and real receiver utility are demonstrated.

**Daily research digest addendum (2026-11-26):** No new primary JEPA, continual-online-learning, plasticity or Android-memory result with comparable new empirical evidence was verified since the previous digest. R-170 is the material new finding for the latent-coupling/security boundary. The immediate V14 experiment is a small, source-authenticated receiver red-team matrix, not porting HandoffGuard's large-model training recipe to Android.

**Source:** https://arxiv.org/abs/2611.34278


## R-171 — La-JEPA: Compact Robot Policies with Latent World Modeling (reviewed 2026-11-26)

**Source/status:** arXiv:2611.08156v1, submitted 2026-11-05; preprint, abstract/metadata only in this pass. The abstract describes a compact action policy trained in a pretrained V-JEPA 2.1 feature space, with joint future-feature and action prediction during training and action-only generation at inference. Reported evaluations cover RoboTwin 2.0, LIBERO-Plus and four real-robot tasks, with the authors reporting performance comparable to pi0.5. These are author-reported abstract claims; the full paper and independent reproduction were not completed here.

**OSS/license:** Official repository https://github.com/mt-clemente/lajepa, inspected at `1d767f958171e5089b30a345a430a66597039ce2`. README is a placeholder saying code is coming; no LICENSE, implementation or weights were present at readback. **No code/weight reuse.**

**V14 relevance:** useful architectural hypothesis for separating a predictive latent training objective from a low-latency action decoder. It does not demonstrate Android feasibility, native B3 coupling or cross-organ learning. Candidate experiment only: a tiny source-bound future-UI-state predictor compared against an action-only baseline, with session-disjoint holdout and zero/shuffle controls. No implementation or model change authorized by this paper.

## R-172 — mzCache: On-Device LLM Memory Management under Multitasking (reviewed 2026-11-26)

**Source/status:** arXiv:2609.01338v1; ACM MobiCom 2026, DOI 10.1145/3795866.3844495. Full paper text was reviewed through an arXiv HTML mirror; artifact documentation was checked directly. The system overlaps CPU restoration with GPU prefill and uses fine-grained memory/KV-cache eviction and restoration to reduce multitasking interference. Its reported results are tied to its specific rooted Snapdragon test devices and llama.cpp/OpenCL implementation; they are not a generic Android benchmark.

**OSS/license/revision:** Official repository https://github.com/HongseungYu/mzcache, read at `f06f5ba155cfa1dcd837b3b9aa6a7efc95b919ff`; repository LICENSE is MIT. The artifact is based on a pinned llama.cpp revision and includes OpenCL SVM/shared-buffer hooks. Model-weight licenses remain separate and must be checked per model; the repository MIT license does not grant rights to Qwen/EXAONE weights.

**Hardware boundary:** EVALUATION.md specifies rooted Android, Snapdragon 8 Elite/8 Gen 3, 12 GB RAM and 30 GB free device storage; host preparation requires about 70 GB, with large model/state files. This is outside the Redmi 6-GB-class target. No port or benchmark was run.

**V14 relevance:** design reference only for overlapping memory restoration with prefill and measuring KV residency. Not a current port candidate: hardware/driver/root assumptions are incompatible, and no model/weight download or swap was performed. No code reused.

## R-173 — Adaptive Guard: Memory-Efficient On-Device LLM Inference on Android via Dynamic Quantization and ART GC Co-Design (reviewed 2026-11-26)

**Source/status:** IEEE GAISS 2026, DOI 10.1109/GAISS66401.2026.11779656; conference dates reported as 2026-10-28 to 2026-10-30. Only the IEEE abstract/metadata were accessible; full text was blocked by the publisher in this pass. The abstract reports dynamic FP16/INT8/INT4 selection from Android memory-pressure callbacks, GC-pause coordination and KV-cache eviction, with claimed reductions in OOM/GC spikes and sub-500-ms median token latency on its tested models/devices. These are abstract-level claims, not independently reproduced results.

**OSS/license:** No official implementation or weight license was found in this pass. No reuse.

**V14 relevance:** a hypothesis for a future Android ResourceGuard experiment: correlate trim callbacks and ART GC pauses with PSS, prefill and TTFT before considering any quantization transition. Do not implement dynamic model switching or change installed weights based on abstract-only results.

## R-174 — Learning Dynamics of Continual Learning (reviewed 2026-11-26)

**Source/status:** arXiv:2609.33620, preprint (2026-09); abstract/metadata only in this pass. The paper frames continual-learning behavior in terms of layer/token interactions, forgetting and plasticity loss. Detailed experimental conditions were not re-read here, so no quantitative claim is promoted.

**OSS/license:** Author repository https://github.com/Joshua-Ren/learning-dynamics-cl, inspected at `b4962ccf5646754b800981f1b207ef65a1a89b6f`; README links the arXiv paper, but no LICENSE file was present. The code stack is research-oriented and heavyweight; no reuse.

**V14 relevance:** supports measuring update effects and interference at layer/task granularity rather than using a single global learning-rate or blanket freeze. Candidate future probe: log per-layer update norms, old-task held-out loss, new-task gain and post-restart retention for each bounded update. No production weight update was run.

**Cross-entry conclusion:** These sources do not justify a model swap or a new Android capability. La-JEPA and Adaptive Guard remain abstract-only; mzCache is fully artifact/license-checked but hardware-incompatible; Learning Dynamics has no reuse license. R-004 (“Stability Does Not Mirror Plasticity”) remains abstract-only with full-text/code verification still pending.


## R-175 — Mistake-gated online updates and auditory omission evidence (reviewed 2026-11-27)

### Primary sources

1. **Mistake Gating Leads to Energy and Memory Efficient Continual Learning.** *Neural Computation* (2026-11-05), DOI [10.1162/NECO.a.1602](https://doi.org/10.1162/NECO.a.1602); full arXiv preprint [arXiv:2604.14336v2](https://arxiv.org/pdf/2604.14336) (2026-07-14) read. The method gates updates to current and previously mistaken samples. The reported 50–80% update reduction is tied to incremental MNIST/EMNIST and pre-trained CIFAR-10 experiments; the paper reports no comparable gain for CIFAR-10 from scratch. CPU measurements are single-threaded; GPU batching and Android/ARM were not evaluated. The paper's reported speedups are not a mobile-performance claim.
   - **OSS/license check:** [vanrossumlab/mistake-gating26](https://github.com/vanrossumlab/mistake-gating26) README inspected; no LICENSE file was found on the default branch. No source code was copied or reused.
2. **Neural Responses to Unexpected Stimulus Repetitions and Omissions in Auditory Cortex Provide Mixed Evidence for Predictive Coding.** *Journal of Neuroscience* (2026-11-11), DOI [10.1523/JNEUROSCI.0545-26.2026](https://doi.org/10.1523/JNEUROSCI.0545-26.2026), PMID 41382361. The full bioRxiv preprint [10.1101/2026.03.30.713276](https://www.biorxiv.org/content/10.1101/2026.03.30.713276v1.full.pdf) was read; the final journal abstract/metadata were checked. The macaque auditory-cortex single-unit study reports enhanced responses to unexpected omissions but not to unexpected repetitions. This is mixed evidence: the measured response does not uniquely distinguish predictive error from adaptation/attention or establish semantic expectation.

### V14 interpretation

- Keep omission and non-observation separate. An omission may be emitted only when the source/window is valid, the expected interval is supported by enough observations, and the interval remains covered; provisional, uncertain and unobserved windows are censored. This is a timing/novelty cue, **not** a calibrated probability, proof of predictive coding, or semantic truth.
- The current RAW EAR A4 predictor is a small 13-feature/182-parameter next-cue-delta learner. It updates on FINAL windows only, reports signed/negative/omission error and gradient/parameter-delta metrics, and is process-local by default. Local numeric-only persistence is still opt-in; no PCM or feature examples are persisted. It is not a B1/B2/C3 model-weight update.
- The two papers suggest a future ablation, not an automatic code change: compare (a) current update-on-every-final-window, (b) error-gated updates, (c) bounded consent-scoped mistake gating, and (d) no-update baseline. Use session-disjoint sequences, zero/shuffle and unexpected-repetition controls; report MAE, false omission rate, update count, gradient norm, parameter diff, retention/restart, CPU time and RSS. Do not retain raw audio or add persistent mistake buffers without a separate privacy/consent design.
- No model download, model swap, Android permission change or production weight update is authorized by these papers.

### Implementation checkpoint

PR [#2540](https://github.com/RedMentos/Aii/pull/2540), draft head `34cbb1e937fd71d07e55b0e4bee6c5f4555eb303`: A4 prediction/event expectation is now exposed as a sanitized source-bound `a4_temporal` context to B1_DETAIL, B2_GIST and C3. The context builder bounds long acoustic summaries to 256 characters rather than dropping the whole context. Current-head CI is pending after a prior context test exposed this summary-length rejection; no Redmi or native-microphone proof exists. See `v14/handoffs/RESEARCH_PERCEPTION_RUN54_20261127.md` for exact gates and next action.

## R-176 — MixMoMo mixed-precision MoE inference on mobile GPUs/NPUs (reviewed 2026-11-27)

**Primary source:** [MixMoMo: Mixed-Precision Mixture-of-Experts Inference on Mobile GPUs and NPUs](https://arxiv.org/abs/2611.33981), arXiv:2611.33981v1, submitted 2026-11-25; preprint, not peer-reviewed in the reviewed record.

- Method: per-expert quantization-impact profiles, critical input-dimension selection, activation-risk estimation and quality-budgeted mixed precision; runtime allocation spans mobile GPU/NPU paths. The paper reports an approximately 18 MiB profile and an approximately 8,000-line C++ extension to llama.cpp.
- Reported evaluation: 35B/48B/80B MoE models on OnePlus 13/15 with Snapdragon 8 Elite Gen4/Gen5 and 24/16 GB RAM; five benchmarks. Claimed average decoding speedup is 3.72× over uniform Q4_0 and 1.53× over the strongest compared baseline.
- Evidence limits: the critical-dimension correlation illustration is narrow relative to the broad generalization claim; the reviewed paper does not provide a public trial-count/confidence-interval analysis sufficient to infer robustness across arbitrary experts/models. No Redmi/6-GB Snapdragon 732G evidence. The Snapdragon HTP/HVX scheduling and large-model regime are not portable assumptions.
- OSS/license: the paper describes the llama.cpp extension but no public MixMoMo source repository or extension license was located in the arXiv record or exact-title repository search. The upstream llama.cpp MIT license does not automatically license unpublished extension code. No source or weights reused.
- V14 decision: **research-only**. Do not change current LFM2.5 models, download weights or swap B1/B2. If compatible sparse-MoE weights are later available and separately approved, test per-expert quantization sensitivity against routing-score and frequency baselines at a matched average-bit budget, with held-out task quality, TTFT, RSS, thermal and rollback evidence. This paper is not a Redmi model recommendation.

## Research & Perception Run 54 — RAW EAR cue-contract enforcement and A4/A5 integrity (2026-11-27)

- PR [#2540](https://github.com/RedMentos/Aii/pull/2540), branch `research-perception/v14-raw-ear-currentparent-20261126-run52`, exact code/test SHA `58af4c96e09543bed3428c77e89c10c513838c25`, draft / NOT_RELEASED.
- Runtime change: `consume_pcm16_voice_window` now validates the complete RAW EAR cue schema unconditionally before canonical A5 PerceptPacket creation/persistence, including when the optional stateful VAD stream is absent. The audio context consumer additionally rejects a valid-but-different A4 cue view unless it exactly matches the validated A5 packet cues.
- Regression change: positive context test uses the real RAW EAR extractor; shared fixtures now satisfy the complete cue schema; negative controls reject malformed producer cues before packet/A4 persistence and reject A4↔A5 cue mismatch before B1/B2/C3 context creation. Candidate builder source manifest readback: 15/15 exact.
- Exact GitHub Actions: RAW EAR fastpath 155/155 PASS on Python 3.13 and 155/155 PASS on 3.14; A4/A5 feature-set 15/15 PASS on each; WebRTC/libfvad comparator Python 3.13 PASS (9 comparator tests + 166 source-bound audio tests), Python 3.14 PASS (9 comparator tests + 166 source-bound audio tests); RuntimeDeploy offline integrity Python 3.11/3.14 PASS; public-content privacy scan PASS. Staged runtime FAIL (20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests) and integrated regression FAIL (one setup failure), both dominated by Core-owned stale recovery/audio-builder pins; staged also reports stale Core arithmetic/observer pins and two migration PARTIAL-vs-UPDATED assertions. No Perception guard was relaxed.
- The exact current Perception composer blob is `3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1`; the 15-entry source manifest matches the live branch. Core PR #2544 was notified to rebase and refresh its own recovery/stage/deployer pin chain. QA owns migration status repair.
- Full local Aii checkout/pytest NOT_RUN because the container has no checkout and GitHub DNS failed. No native model, microphone, Android/Termux or Redmi test; `device_benchmark=false`. Last private V13OBS #115 is historical; owner-read requests #998/#999 expired with NO_LIVE_RECEIPT. REDMI_UNVERIFIED; NOT_RELEASED.
- Handoff: `v14/handoffs/RESEARCH_PERCEPTION_RUN54_20261127.md`. Next: Core/QA rebase and pin repair, finish Python 3.14 comparator, rerun staged/integrated, then continue source-disjoint A4 attention/salience work. No user action required.


## R-177 — LATER: action-conditioned temporal evidence retrieval for predictive world models (2026-11-27)

**Primary record:** Zihan Zhou, Wenxi Xu, Qilin Wang and Hao Tang, *LATER: Learning Action-Conditioned Temporal Evidence Retrieval for Predictive World Models*, arXiv:2611.25671v1, submitted 2026-11-19: https://arxiv.org/abs/2611.25671 . The arXiv record/abstract and an extended paper rendering were inspected; the original PDF was not retrieved in this run. Status is therefore **ABSTRACT + EXTENDED RENDERING VERIFIED / NOT FULL PRIMARY-PDF REVIEWED**.

**Reported method and evidence:** LATER extends CF-JEPA with separate recurrent writers for controllable and uncontrollable transition memories. A query formed from the current state and candidate action reads completed-transition memories through a gated low-rank response bridge. Memory is held fixed during candidate rollouts; multi-cut auxiliary targets train the writers even while zero-initialized bridge gates initially block the main loss. The abstract reports distracted Two-Stage PushT terminal success of 25.0% versus 15.5% for reconstructed CF-JEPA, and a 20.2% reduction in along-push MAE under distractors in a separate six-model/two-seed comparison. The extended rendering describes selected paired friction-history interventions and a higher H100 runtime/allocator peak than CF-JEPA. These are **simulation results**, not real-robot, V14, or Android measurements.

**OSS / rights:** no official source repository or weight package/license was located in this run. No code, weights, dataset or dependency was reused or downloaded. The paper is a method reference only.

**V14 testable adaptation:** for the existing WorldJEPA/episodic recall path, compare (a) recent-only context, (b) source-exact committed transition retrieval, (c) action-conditioned retrieval from completed SourceRef-bound transitions, (d) shuffled-history and zero-memory controls. Keep candidate rollouts read-only so imagined outcomes cannot rewrite observed memory. Split by source and session; test delayed outcomes, stale/forgotten sources, held-out action utility, retention, restart and rollback. This is a JEPA/Memory-owned follow-up, not an A4 implementation claim and not an instruction to import LATER code.

## R-178 — When Sounds Turn Heads: attention-head timing for audio event grounding (2026-11-27)

**Primary record:** Jongbhin Woo, Jaewook Jeong and Joon Son Chung, *When Sounds Turn Heads: Recovering Event Timing That Audio LLMs Fail to Say*, arXiv:2611.25960v1, submitted 2026-11-19: https://arxiv.org/abs/2611.25960 . **Abstract only** was verified in this run; full paper, model-specific methods and appendices were not reviewed.

The abstract claims that a small set of query-sensitive attention heads in audio LLMs track queried sound intervals even when the generated answer misses or mis-times them. A training-free head-guided decoder rescores candidate intervals while retaining the model's separate decision about whether the sound exists. The abstract reports mIoU rising from 0.07–0.36 to 0.48–0.56 on recordings released after model training for the evaluated settings. This is not a result on V14 RAW EAR or LFM2.5.

**OSS / rights:** no official implementation/checkpoint repository or license was located in this run; no code or weights reused. The current RAW EAR feature interface does not expose native transformer attention heads, so this is not presently implementable as a drop-in. Revisit only if an approved audio teacher/runtime exposes source-bound attention maps; keep event-presence decisions separate from timestamp priors and add random-head, shuffled-query and absent-event controls. No model download, swap or dependency change.

## Research & Perception Run 55 — A4 temporal source-isolation ablation (2026-11-27)

- Added `v14/experiments/a4_temporal_ablation_20261127.py`, `test_a4_temporal_ablation_20261127.py` and `.github/workflows/v14-a4-temporal-ablation.yml` on branch `research-perception/v14-raw-ear-currentparent-20261126-run52`. Experiment source commit: `2a6d4d8ede170d669e21e5093970dc143711a4c2`. Readback blob SHAs: experiment `a7f1e9401b24561ce11d0704b48b815d46b931b7`, tests `ed79cb765fa8b2a178709aa2572de7c75add04df`, workflow `a98d5ededdd31549977540f7e22f7d05962dbbb0`.
- The experiment calls the existing `AudioTemporalPredictionRegistry`; it does not alter the production Runtime. It measures independent synthetic speech/non-speech streams, interleaved-versus-isolated stream parity, learned next-cue-delta error against the predictor's persistence baseline, numeric adapter deltas, bounded A4 novelty, no-context reset, provisional-window censoring and consent-rotation reset.
- Local full Aii tests: **BLOCKED / NOT RUN**. No repository checkout is mounted and `git ls-remote` fails DNS resolution. GitHub Actions result for the new workflow was not yet visible at this checkpoint; **CI PENDING/UNVERIFIED**, not PASS.
- No microphone/AudioRecord, native model inference, Android/Termux or Redmi test. Synthetic cues only; `device_benchmark=false`. No PCM, transcript, speaker embedding, training example, model or weight data was downloaded or persisted.
- Existing PR #2540 remains DRAFT / NOT_RELEASED. Its broader staged Runtime and integrated-regression gates remain FAIL on Core-owned stale source pins and QA-owned migration assertions; the A4 experiment does not repair or conceal those failures.
- Next: verify the exact new workflow result; fix any measured A4 test defect. Core owns #2544's recovery/stage/deployer rebase; QA owns the migration status assertions. Perception must not edit those shared files. After the shared stack is reconciled, extend A4 evaluation to error-gated versus every-FINAL updates and explicit retention/restart ablations. No user action required.


## Research & Perception Run 55 — final CI closeout (2026-11-27 02:52 CET)

**Exact branch head:** `e270369a04eb20470aa717dc0464b2b03a4320a5`; PR [#2540](https://github.com/RedMentos/Aii/pull/2540), DRAFT / NOT_RELEASED. The updated sweep code commit is `b60669975184bc3a54be4b5d380c95fd91fab16a`; updated test commit is the current head above.

**Exact CI evidence:**
- A4 temporal source-isolation workflow run **45924853167**, PR merge candidate short SHA `3d56c9c`: compile PASS and **7/7 tests PASS on Python 3.13.18 and 3.14.10**; both versions emitted identical deterministic metrics.
- Source-bound A4/A5 feature-set probe run **45924853182**: PASS on Python 3.13 and 3.14.
- RAW EAR fastpath run **45924853240**: **155 passed** on Python 3.13 and **155 passed** on Python 3.14; benchmark output explicitly says `synthetic_benchmark=true`, `device_benchmark=false`.
- RuntimeDeploy offline integrity run **45924853218**: PASS on Python 3.11 and 3.14.
- Staged runtime run **45924853105**: **FAIL**, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Root blockers remain shared/Core/QA-owned: recovery builder expects composer blob `831080bceec90711bd42e0fa4eba47c669975c98`, while current Perception composer is `3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1`; arithmetic `v13/contracts.py` and observer `v13/cognition.py` pins are also stale, and migration still returns `PARTIAL` where the test expects `UPDATED`.
- Integrated regression in the same run **45924853105**: **FAIL**, one setup test, at the same stale Core audio-composer pin. Perception did not edit or weaken any of these gates.

**Synthetic A4 result (not device evidence):** interleaved streams exactly matched isolated execution (max metric delta 0). The 182-parameter shadow predictor changed numeric parameters and kept novelty below its 0.10 cap (max attention novelty 0.04111883; max omission novelty 0.01736616). However, it did **not** beat the persistence baseline on all cue types:
- periodic speech: mean model MAE 0.21739024 vs persistence 0.33642678 (improvement +0.11903654);
- non-speech impulses/noise: 0.22605715 vs 0.19615384 (worse by 0.02990331);
- mixed activity: 0.28642224 vs 0.26395818 (worse by 0.02246406).

The explicit learning-rate sweep (0.02, 0.05, 0.10, 0.20) kept the same pattern: all tested rates improved the periodic-speech fixture, but none beat persistence on the non-speech or mixed fixtures; 0.20 was least negative on those two. No default-rate change is justified. No-context reset produced zero measured updates/novelty; provisional windows were ignored; consent rotation reset the numeric state to zero. Interpretation: this is a bounded A4 shadow novelty/error signal, **not** a generally better acoustic predictor or semantic event recognizer.

**Local/device boundary:** full LOCAL_LINUX Aii checkout/pytest remains BLOCKED / NOT RUN (no checkout mounted; GitHub DNS failure). No Android/Termux, microphone/AudioRecord, native model, B1/B2 normal-turn or Redmi test. Last private V13OBS #115 is historical (2026-11-24); #998/#999 expired without receipt. REDMI_UNVERIFIED; current updater/install state unknown. No device action, model/weight swap, permission change or raw audio persistence.

**Next:** Core owns the stale Recovery→Stage→RuntimeDeploy pin chain; QA owns migration assertions. After their rebase, rerun the exact staged/integrated gates. Perception's next experiment is source/session-disjoint omission false-positive and update-gating evaluation; do not promote the A4 learner or change its default based on these synthetic fixtures.


## Run 55 extension — A4 event-expectation omission ablation (2026-11-27)

The same A4 experiment now also exercises the existing `AudioEventExpectationRegistry` directly. Code commit `a44c39b1e1e5c9b38942cdc0dd55aa410105e4cc`; test/code branch head `f45eb1b30befc406b5f65f4f0858d06785de4bd9`; workflow run **45925644718** completed with **9/9 tests PASS on Python 3.13 and 3.14** and identical deterministic output.

Synthetic controlled result:
- Four VOICED onsets establish three 2-second intervals. An on-time fifth event produces no omission and 0 novelty.
- A final valid SILENCE window spanning the expected 8,000 ms event plus tolerance produces one omitted-VOICED event, timing-confidence proxy 0.60 and bounded omission novelty 0.03 (cap 0.05).
- UNCERTAIN censors the expected event; PROVISIONAL is ignored but leaves the prior state unchanged, so a later FINAL silence window is evaluated; consent rotation resets the interval model; a no-context reset never accumulates enough intervals to emit an omission.
- Interleaved expected/missing streams match isolated execution exactly.

This is a deterministic timing-rule fixture, not calibrated event probability, semantic audio understanding, or a false-positive estimate on real audio. No PCM, microphone, speaker identity or user data was used or stored.

At this checkpoint, A4/A5 feature-set run **45925644769** passed on Python 3.13/3.14; RAW EAR fastpath **45925644699** passed 155/155 on each; RuntimeDeploy offline **45925644734** passed on Python 3.11/3.14. WebRTC/libfvad comparison **45925644686** was still in progress (3.13 benchmark step completed; 3.14 not final). Staged runtime **45925644732** failed at the same Core composer pin, stale arithmetic/observer pins and QA migration PARTIAL-vs-UPDATED assertion; integrated regression in that run was still running at this checkpoint. Previous integrated run **45924853105** failed one setup test at the same Core composer pin.

LOCAL_LINUX full suite remains NOT RUN; Android/Termux/Redmi remains REDMI_UNVERIFIED; PR #2540 remains DRAFT / NOT_RELEASED.


## Run 55 — latest CI completion update (2026-11-27)

- A4 temporal + event omission workflow 45925644718: **9/9 PASS on Python 3.13 and 3.14**.
- A4/A5 source-bound feature-set 45925644769: **PASS on both Python versions**.
- RAW EAR fastpath 45925644699: **155/155 PASS on both Python versions**; synthetic benchmark flag true, device benchmark false.
- RuntimeDeploy offline integrity 45925644734: **PASS on Python 3.11 and 3.14**.
- WebRTC/libfvad comparison 45925644686: Python 3.13 job completed successfully through source/ABI checks and A4/A5 runtime tests; Python 3.14 job remained IN_PROGRESS at final readback, so the comparison is not fully green yet.
- Staged + integrated run 45925644732: **FAIL**. Staged job repeats 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; integrated job fails one setup test. Both stop at the same Core-owned recovery composer pin mismatch. Staged additionally fails stale arithmetic and observer source pins plus migration PARTIAL-vs-UPDATED assertions.
- No Perception file or gate was changed to hide these failures. Core/QA ownership remains unchanged.


## R-179 — Energy efficient synaptic plasticity (full-text review 2026-11-27)
- **Primary source:** Li & van Rossum, “Energy efficient synaptic plasticity”, *eLife* 2020;9:e50804, published 2020-02-13, DOI [10.7554/eLife.50804](https://doi.org/10.7554/eLife.50804). Peer-reviewed full text: [eLife article](https://elifesciences.org/articles/50804).
- **Mechanism:** each synapse has a transient/short-lived component and a persistent component. Updates accumulate in the transient component; when a consolidation threshold is crossed, the transient component is transferred to the persistent weight and reset. The model trades maintenance/decay cost against consolidation cost.
- **Evidence / limits:** the paper's reported energy advantages come from an explicit modelled cost function and simulations (perceptron, multilayer and spiking-neuron examples), not measured Android CPU/GPU power. The result depends on assumed maintenance and consolidation costs and on the selected threshold; it is not evidence that a Python/Android implementation will save energy.
- **OSS / licence:** [vanrossumlab/li_vanrossum_19](https://github.com/vanrossumlab/li_vanrossum_19) contains Octave/C++ perceptron and Python multilayer simulations. Its root LICENSE is GPL-3.0. The Aii repository has no root LICENSE, so no upstream code was copied or adapted; only the published mechanism was used as a research lead.
- **V14 implication:** a bounded transient eligibility/update cache may complement the existing error-gate experiment: keep short-lived local deltas separate from persistent predictor weights, consolidate only after a tested threshold, then measure numeric retention, restart and rollback. This must be a distinct ablation from MEMORIZED_ERROR, with a no-consolidation control and actual before/after weight deltas. Do not claim device-energy savings without native power/RSS/latency measurements.

## R-175 implementation follow-up — Run 56 (2026-11-27)
- PR [#2548](https://github.com/RedMentos/Aii/pull/2548), stacked on [#2540](https://github.com/RedMentos/Aii/pull/2540), adds opt-in `MEMORIZED_ERROR` to the existing A4 temporal predictor and registry. Default `EVERY_FINAL` is unchanged.
- The continuous-regression adaptation compares model MAE with a persistence baseline and remembers bounded quantized previous→target cue-delta transition fingerprints within a process-local stream. Fingerprints are not anonymisation and are not persisted; reset/consent/gap/chronology/restart clears them.
- Exact A4 experiment CI: 6/6 tests PASS on Python 3.13 and 3.14. The experiment includes EVERY_FINAL, MEMORIZED_ERROR and NO_UPDATE; it reports gradients, total weight deltas, parameter-diff L2, retention drift and restart equality.
- Synthetic results (60 observations each): periodic speech 59 vs 7 updates (MAE 0.20170 vs 0.25575); non-speech impulses 59 vs 41 (0.20631 vs 0.20158); mixed activity 59 vs 26 (0.27233 vs 0.28714). Update sparsity is real in this tiny predictor, but quality worsens on two of three streams. Periodic-speech parameter-diff L2 is 1.06464 EVERY_FINAL vs 0.63463 gated; gradient-L2 sum 12.87747 vs 3.17314. NO_UPDATE remains an explicit negative control.
- Retention drift after a new task is +0.06792 EVERY_FINAL and +0.04350 gated, but gated absolute MAE is worse before and after the new task (0.29879→0.34230 vs 0.16741→0.23533). This is not a retention win. Forward prediction still runs on every window, so no energy/latency saving is claimed.
- Keep the policy opt-in and default OFF. Exact focused CI also passes RAW EAR fastpath 161/161 and feature-set probe 15/15 on Python 3.13/3.14; model-lab 73 passed with 4 native-wrapper skips and privacy scan CLEAN. Staged/integrated CI remains blocked by Core-owned composer/contracts/cognition pins and QA migration PARTIAL-vs-UPDATED assertions. See `v14/handoffs/RESEARCH_PERCEPTION_RUN56_20261127.md`.


## R-179 implementation follow-up — Run 57 (2026-11-27)

- Extends the existing A3/A4 RAW EAR predictor with two separately opt-in policies: `TRANSIENT_CONSOLIDATE` and `TRANSIENT_NO_CONSOLIDATION`. The default `EVERY_FINAL` and the experimental `MEMORIZED_ERROR` policy retain their existing update path.
- The transient policy applies clipped LMS deltas to a bounded process-local buffer used for subsequent predictions. `TRANSIENT_CONSOLIDATE` transfers the buffer into the persistent numeric predictor weights only after its L2 threshold is reached; `TRANSIENT_NO_CONSOLIDATION` is the explicit no-commit control.
- `state_dict()` and the existing SQLite state envelope continue to contain only consolidated numeric weights and their commit count. Pending deltas, previous features, and per-stream history are not serialized; load/restart clears them. Source/generation/consent resets clear both persistent and transient state through the existing registry lifecycle.
- New tests cover delayed threshold crossing, persistent-vs-transient parameter deltas, the no-consolidation control, restart preservation of committed weights while dropping pending deltas, registry parameter propagation, and invalid bounds.
- LOCAL_LINUX scratch reproduction of the transient-buffer algebra: **3/3 PASS** (thresholded commit, no-consolidation control, and restart discard). This is not the full Aii test suite.
- Exact repository Python 3.13/3.14 CI for the updated predictor/test is triggered by this commit and remains **PENDING** until exact-head results are read back. The full local Aii checkout remains unavailable in this environment.
- Research boundary: this implements the two-timescale mechanism suggested by Li & van Rossum (eLife 2020, DOI 10.7554/eLife.50804), not a reproduction of their energy model or evidence of reduced Android power. Their upstream simulation repository is GPL-3.0 and no code was copied; the Aii root license remains unresolved.
- No audio input, transcript, speaker identity, model GGUF, B1/B2/C3 weight, Android permission, updater, installed device or user data was changed. No Redmi/native microphone/Android proof; B3 remains OFF; **REDMI_UNVERIFIED / NOT_RELEASED**.


### Run 57 Runtime wiring closeout

- The explicit experimental policy now reaches the real caller-PCM RAW EAR Runtime consumer through `runtime.cfg`: `raw_ear_temporal_update_policy`, `raw_ear_consolidation_threshold`, and `raw_ear_max_transient_norm`. Missing configuration still selects `EVERY_FINAL`; invalid policy values fail closed rather than silently falling back.
- The integrated audio-context candidate manifest was refreshed to exact Git blob pins: `audio_voice_cues.py=4bfcf31a7738bb390781babab8e11518896a3580`, `audio_temporal_prediction.py=24e2c867613a33c33a58a779529c629ecfde37ef`; candidate-builder blob after pin refresh: `019992e2e200b0c5c52d7f18fb5f38ff4185e396`.
- Exact branch readback at `007de4895cb9972f558b7fa3bd33c3b04d0946eb` confirms both pins and the new Runtime-config tests. A4 update-gate workflow `45935405225` was queued at last poll; no focused CI result is yet claimed for this code.
- This is a developer-controlled opt-in gate, not a user-facing toggle or production activation. Default Runtime behavior remains unchanged.


### Run 57 CI source-pin correction

- The first exact CI after Runtime wiring exposed two expected-source-pin failures: the RAW EAR vs WebRTC/libfvad workflow and the source-bound A4/A5 feature-set workflow still expected the previous `audio_voice_cues.py` blob `d80b803...`.
- Updated both Perception-owned workflows to expect the exact current consumer blob `4bfcf31a7738bb390781babab8e11518896a3580`. No test was weakened; only the stale source identity was rebound.
- On the earlier code/test head, the A4 synthetic ablation passed on Python 3.13/3.14, but the new full predictor/consumer pytest step was still running. The feature-set and VAD failures are from pre-pin-refresh commits and must be superseded by the queued exact-head runs `45935761586` and `45935761531`.
- New exact-head workflow runs at the latest pin-refresh commit: A4 ablation `45935761585`, feature-set `45935761586`, VAD comparator `45935761531`, staged/integrated `45935761490`, runtime-deploy `45935761505`; results pending at this ledger update.


## R-180 — Co-observation is distinct from retention and plasticity (2026-11-27)

- Primary source read: Timm Hess, Abhishek Jha, Gido M. van de Ven, Tinne Tuytelaars, *Forgetting, plasticity, and co-observation: a third facet of continual learning*, arXiv:2608.18803 (2026-08-19). The arXiv text is available; the associated repository README labels the work CoLLAs 2026, but the proceedings record was not independently verified in this run.
- Empirical setup: four uniformly partitioned data chunks; supervised CIFAR-100/ImageNet-100 with ResNet-18, and self-supervised ImageNet-100 with Barlow Twins and I-JEPA/ViT-B/16; fixed optimization budget, linear-probe evaluation, three seeds (six for I-JEPA). Their ensemble baseline controls for forgetting, yet incremental-joint training still outperforms it, indicating a separate co-observation deficit.
- Replay results: in their ImageNet-100 representation-level evaluation, a 3% exemplar buffer did not consistently match the ensemble; about 15% matched the ensemble, and 30% closed roughly half the remaining gap to incremental-joint training. Distillation tracked the ensemble but did not close the co-observation gap. These percentages are not transferable to the 13-feature A4 predictor; they are a reason to test, not a parameter recommendation.
- OSS: [TimmHess/Co-ob](https://github.com/TimmHess/Co-ob) declares MIT. README says it vendors a patched Avalanche tree and uses a CaSSLe fork for SSL training; those nested components require separate license/dependency review. No code was copied.
- V14 experiment proposal: compare current sequential A4 updates with a tiny source-/generation-/consent-scoped process-local replay of prior 13-feature transition pairs, sampled alongside the current pair at an equal gradient/update budget. Test buffer sizes 1/4/8/16 against no-replay and transient-only controls on session-disjoint acoustic regimes. Measure current/old-regime MAE, omission/commission error, gradient and parameter deltas, update count, bytes, restart/consent reset, and holdout retention. No PCM/transcript storage; no replay across consent scopes; never persist raw observations. Do not assume a tiny buffer will reproduce the paper's vision results.
- Relevance: this adds a third diagnostic axis to A4 evaluation—co-observation—rather than treating lower update count or preserved weights as sufficient evidence of learning.


### Run 57 exact-test correction

- The new exact predictor/consumer pytest gate ran on Python 3.13 and 3.14 and found **40 passed / 1 failed** on each. The failing assertion was a fixture assumption: the post-consolidation error was large enough to cross the threshold again immediately, so no transient delta remained. Production code compiled; the other 40 tests and six synthetic ablation tests passed.
- Corrected only the restart test sequence/threshold (0.8, max norm 2.0) so it first commits once, then creates a sub-threshold pending delta before loading the saved state. The exact-head rerun for this correction is pending; no PASS claim yet.


### Run 57 transient ablation extension and norm-bound repair

- Extended `v14/experiments/a4_update_gate_retention_20261127.py` to compare five policies: `EVERY_FINAL`, `MEMORIZED_ERROR`, `TRANSIENT_CONSOLIDATE`, `TRANSIENT_NO_CONSOLIDATION`, and `NO_UPDATE`. It now reports transient vs persistent parameter norms/deltas, update attempts vs persistent commits, consolidation count, and restart loss of pending deltas. Read-only evaluation clones the transient matrix for pre-restart metrics; reload intentionally restores only the persisted consolidated state.
- The first run of this expanded benchmark exposed a real bound bug: interpolating between the old transient matrix and an oversized proposal did not guarantee the final matrix norm stayed under `max_transient_norm` (observed 1.06108105 against a 1.0 cap). Fixed by scaling the entire proposed transient matrix to the cap, and extended the Runtime predictor test to assert the bound across alternating updates.
- Refreshed the integrated composer manifest to exact predictor blob `8bb0d3c8033c898edf824be6752450383c4cc5c0`; composer builder blob is now `92fb6fc5db705f5dd69ce20bb283ac6af59cfe25`. Voice consumer remains `4bfcf31a7738bb390781babab8e11518896a3580`.
- Exact-head reruns after the bound repair: A4 ablation + predictor/consumer tests `45936510646` and RAW EAR VAD comparator `45936510653`; both queued at last poll. No PASS claim yet.


## Research & Perception Run 61 — A4 shared checkpoint integrity across temporal resets (2026-11-27)

- **Defect found in code audit:** `AudioTemporalPredictionRegistry._reset_state()` wrote a new zero-initialized predictor to the shared source/generation/consent checkpoint on `RESET_CHRONOLOGY` and `RESET_GAP`. Since numeric weights are shared across Store sessions while temporal feature history is session-local, a reset in one session could erase another session's learned numeric weights.
- **Implementation:** PR [#2553](https://github.com/RedMentos/Aii/pull/2553) now reloads a valid current checkpoint into the reset session and does not write/increment the shared version for a session-local temporal reset. Missing/invalid/consent-rotated state still initializes via the existing path. The integrated audio composer pin was refreshed to the new predictor blob.
- **Regression tests:** added separate chronology- and gap-reset tests. Each first trains non-zero weights in session A, opens session B, forces the reset, and asserts exact weight/update-count preservation, unchanged checkpoint version, and fresh session-local temporal baseline. Existing consent-rotation reset coverage remains the negative control.
- **LOCAL_LINUX:** CPython 3.13.5 / SQLite 3.46.1 isolated semantics reproduction 3/3 PASS (old wipe reproduced; patched preservation; consent reset). This is not full repository pytest. Full checkout remains BLOCKED by absent local clone and GitHub DNS failure.
- **CI:** exact-head PR #2553 workflows pending at this ledger checkpoint. Parent #2551's focused A4/RAW EAR/feature-set workflows passed; its staged/integrated workflow remains blocked by Core source pins and QA migration assertions.
- **Research interpretation:** R-175's mistake-gated update savings and R-180's co-observation result do not establish retention by themselves. The persistence layer must preserve shared numeric weights when only a session-local temporal trace is reset. This patch is an integrity correction, not a new learning-performance claim.
- **Status:** A4 checkpoint integrity **WIRED_SYNTHETIC / CI_PENDING**; no native Linux model or Android proof, no Redmi receipt, no release. No model, weight artifact, permission, updater setting or user data changed.
- **Next:** Core refreshes its owned Recovery → Stage → RuntimeDeploy composer pin after #2553 review; QA retains migration fixes. Perception then tests two independent Store/registry writers and returns to the A5/signed-audio normal Runtime consumer gaps.


## Research & Perception Run 62 — lease-bound A5 visual frame to A4 PerceptPacket (2026-11-27)

- **Stacking / coordination:** PR #2554 carries the Perception-owned A5 visual adapter from the parallel #2550 line onto the A4 session-scope/reset-preservation chain #2551 → #2553. This creates one reviewable Perception A4/A5 branch for Core to consume; it does not copy or replace Core-owned Runtime/Recovery code.
- **A5 contract:** a FINAL `SCREEN_FRAME_AVAILABLE` observation is accepted only under a live source/session/receipt/generation-bound `UIObservationLease`. The adapter decodes pixels in memory, computes the existing 4×4 RAW-EYE descriptor, applies a non-semantic structure cue to the exact source/index A4 segment, and returns a provenance-bound `PerceptPacket` plus bounded `PerceptAdmission`. Optional existing hashed-BOW student hypotheses are capped at three and remain `STUDENT_ESTIMATE / REFERENCE_NOT_FACT`; no teacher model is loaded.
- **Privacy / authority:** screenshot bytes, pixels, feature arrays and transcripts are not persisted; lease revoke/exit clears adapter-held feature buffers; action and learning authority remain false. This is not a platform capture provider, not a normal-turn Runtime callsite, and not Android-verified.
- **A5 exact CI:** workflow #36, Python 3.13 and 3.14 each `py_compile` PASS and **11 tests + 3 subtests PASS**. Tests use generated PNGs and a synthetic provider. The A5 UI lease dependency is unchanged (blob `a6c26206d535199b244d0de83fbeb38bb8ad3951`).
- **A4 exact CI:** update-gate/predictor **47/47** on Python 3.13/3.14; temporal source-isolation **9/9** on both; A4/A5 feature-set **15/15** on both; RAW EAR optional NumPy/backend consumer **175/175** on both; WebRTC/libfvad **186/186** on both plus pinned native libfvad C tests **13/13**; RuntimeDeploy offline **92 tests** on Python 3.11 and 92 on 3.14; public privacy scan CLEAN.
- **LOCAL_LINUX:** CPython 3.13.5 / SQLite 3.46.1 isolated A4 reset semantics 3/3 PASS. Full local Aii checkout/pytest BLOCKED/NOT_RUN because no checkout is mounted and GitHub DNS fails.
- **Shared staged/integrated remains FAIL:** 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests; integrated regression one setup failure. Root causes: Core Recovery composer pin is stale against the Perception-owned composer blob; Core arithmetic `v13/contracts.py` and observer `v13/cognition.py` pins are stale; QA migration assertions expect `UPDATED` rather than the current `PARTIAL` result. The same failure is present on #2553 and #2554. No pin or migration assertion was weakened.
- **Research interpretation:** the Android MediaProjection API contract already recorded with R-180 still requires an explicit user grant and platform lifecycle cleanup. This adapter starts after an observation lease exists; it does not implement the Android foreground service, MediaProjection.Callback/onStop provider, or target Redmi API-33 capture. No new model, OSS dependency, license or paper was added in this run.
- **Status:** A4 checkpoint integrity and A5 visual-frame adapter are **WIRED_SYNTHETIC / FOCUSED_CI_PASS / STAGED_CORE_QA_BLOCKED**; no native Android or Redmi proof, no release. P0 chat, B1/B2 valid-offer delivery and native B3 latent coupling remain OPEN.
- **Next:** Core rebase #2549/#2552 onto #2554 and refresh Recovery → Stage → RuntimeDeploy pins bottom-up; QA fixes migration assertions; Perception then adds independent-registry concurrency stress tests and continues the missing normal-turn A5/signed-audio consumer path.


## R-181 — XBridge: entity-grounded cross-architecture latent communication (2026-11-27)

- **Primary paper:** Wooseong Yang, Wei-Chieh Huang, Weizhi Zhang, Yu Wang, Philip S. Yu and Junhyun Lee, *XBridge: Entity-Grounded Latent Bridge for Heterogeneous LLM Communication*, arXiv:2608.11676 v2 (2026-09-28), accepted at NeurIPS 2026. Full text reviewed, not abstract-only: https://arxiv.org/abs/2608.11676
- **Core result:** separate discrete identity from continuous contextual enrichment. Lexical Anchor Mapping (LAM) maps sender context tokens into receiver-native token IDs/embeddings; a receiver-conditioned gated cross-attention bridge (LEB) lets receiver hidden states query sender hidden states. The paper explicitly warns that dimension-matching/projection alone does not make sender activations receiver-distribution-compatible, and that continuous-only bridge loses rare entity identity.
- **Reported evidence:** Llama-3.1-8B → Qwen2.5-7B, Qwen2.5-7B → Llama-3.1-8B, and Mistral-7B → Qwen2.5-7B across seven QA/long-context tasks. XBridge exceeds heterogeneous 128-token text-summary communication on all seven tasks for all three pairs; average reported gains +14.3 to +21.4 F1 points. HotpotQA Llama→Qwen ablation: full 78.8 F1, LAM-only 56.5, LEB-only 30.3. Latency table: 0.15 s/sample vs 1.70 s/sample for text communication on the paper's H200 setup. Bridge: 264M parameters (3.8% of 7B receiver), trained on 587 balanced samples in under 10 minutes on a GPU.
- **Important limits:** experiments use 7B-class Llama/Qwen/Mistral, H200 latency and a single sender→receiver exchange; multi-turn bidirectional communication and larger agent graphs are explicitly untested. The 264M bridge alone is too large for the Redmi 5.84 GB total-RAM class once base models, KV and runtime are included. These results do not validate V14's native B3, LFM2.5, Android or cross-organ utility.
- **OSS/license/dependency review:** https://github.com/WooseongYang/XBridge is Apache-2.0; the published bridge checkpoint https://huggingface.co/wyangw/xbridge-llama2qwen is also marked Apache-2.0. Repository requirements include torch>=2.6, transformers>=4.52,<5, accelerate>=1.12, safetensors, tokenizers, datasets and numpy>=2.0; no Android/ARM-light path is supplied. The Llama-3.1 and Qwen2.5 base-model licenses remain separate from the bridge license; the evaluation cache is 4.77 GB and is not an on-device artifact. No code, model, cache or weights were downloaded or reused.
- **V14 experiment:** extend the native receiver matrix with a dual-channel ablation: exact receiver-native token/entity anchors + receiver-query-conditioned sender-state retrieval versus continuous-only, anchor-only, shuffled anchors, rare-name/number substitution, zero bridge and OOD sender controls. Record answer-token rank/F1 and receiver activation norm/variance; do not inject projected sender vectors directly into the receiver residual stream or KV cache. Keep current B3 OFF until real paired model taps, gradients, held-out utility and rollback are proven.
- **Implementation decision:** conceptual adaptation only; no XBridge dependency or 264M checkpoint import. This research is separate from the A5 provider receiver code below.

## Research & Perception Run 64 — signed MediaProjection RAW-EYE receiver (2026-11-27)

- **Gap:** Core MediaProjection provider PR #2408 calls `vision_ui_frame_ingress.consume_projected_frame_from_provider`, but the module was absent from its current tree. The old Perception receiver from PR #2375 was re-reviewed against the current #2556 parent; `vision.py`, `a5_context_envelope.py`, `percept_admission.py`, `attention.py` and `a5_ui_admission_bridge.py` dependency blobs are identical. Current `contracts.py` adds A4AttentionReceipt but leaves the PerceptPacket schema unchanged.
- **Code:** PR #2557 restores the one-shot provider verifier, active-lease/source/generation binding, bounded 8 MiB / 4 MP decode, exact digest/size verification, in-memory RAW-EYE global + 4×4 tile extraction, A4 salience, bounded A5 context envelope and zeroization. Existing installed projector is read only in LAB_SHADOW_ONLY; no new model, weight, dependency or persistent screenshot/feature data.
- **Exact CI:** workflow 45974814847: py_compile PASS and 25/25 tests PASS on Python 3.13; 25/25 PASS on Python 3.14. Generated PNG/provider fixtures only. Staged workflow 45974814855 fails at existing Core audio-composer/arithmetic/observer pins and QA PARTIAL-vs-UPDATED assertions (20 failed/233 passed/10 skipped/2 errors/41 subtests); integrated regression was IN_PROGRESS at last poll.
- **LOCAL_LINUX:** full Aii checkout/pytest BLOCKED/NOT_RUN (no checkout mounted; GitHub DNS failure). No local test pass is claimed. **REDMI_UNVERIFIED / NOT_RELEASED**; no Android MediaProjection grant, onStop, real UI frame, normal Runtime/C3 callsite or device receipt.
- **Next:** Core rebases provider #2408 onto #2557 and wires it into the normal Runtime turn; QA owns OS consent, onStop, cancellation, restart and rollback. Keep provider OFF until the real Android lifecycle is accepted.
