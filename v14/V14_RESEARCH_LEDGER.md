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


## 2026-11-21 — Research & Perception: latency-aware C3 model lab (V14-005)

### Primary research reviewed

- **Transferable Latency Prediction for Fast LLM Screening on Heterogeneous Edge Devices**, Xiaolong Tu et al., arXiv:2607.21602, posted 2026-05-11. Full arXiv text reviewed; peer-reviewed venue/status not independently confirmed. The paper models each run as a hardware-runtime-model-prompt configuration, separates prefill and decode, and fuses static descriptors with dynamic telemetry. It reports Pixel 8/8 Pro and Jetson/Orange Pi/RTX 3090-class experiments. Its reported cross-device calibration improvements are evidence that latency predictors need target-device calibration, not that Pixel numbers predict Redmi results. Concrete V14 adaptation: retain separate prefill-to-first-token, TTFT, decode throughput, RSS/PSS, runtime revision, prompt suite and device/thermal context for every candidate run. Source: https://arxiv.org/abs/2607.21602
- **DVFS for Small Language Model Inference on Mobile Edge Devices**, Jiesong Chen et al., arXiv:2609.13153, posted 2026-07-08. Full arXiv text reviewed; preprint status, no peer-review claim. DVFSLM reports up to 12.4% lower energy/token than built-in governors and up to 8.4% versus GearDVFS, with QoS gains, on NVIDIA Jetson AGX Orin and Orin NX. Its prototype coordinates GPU/EMC frequencies and a CPU threshold. Those hardware controls are not a safe or available assumption for ordinary Redmi/Termux CPU inference; no DVFS code is adopted. Source: https://arxiv.org/abs/2609.13153

### Candidate provenance and licensing

- Current C3 baseline from v13/code/specs/models.json: LiquidAI/LFM2.5-350M-GGUF, pinned revision 657e078c94084481950a2d555a941481f715536b, QAD_Q4_0, 219312832 bytes, LFM Open License 1.0.
- Prior C3 candidate from the same registry history: LiquidAI/LFM2.5-230M-GGUF, revision cdf97bd8205908758f44aec508d68ac1aef98f5c, QAD_Q4_0, 149081056 bytes, SHA256 e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292. Official model page and LICENSE checked 2026-11-21: LFM Open License 1.0, not Apache-2.0; Section 5 does not grant Commercial Use to a Legal Entity whose annual revenue is USD 10 million or more; the license states a qualified non-profit exception for non-commercial/research purposes. Model source: https://huggingface.co/LiquidAI/LFM2.5-230M-GGUF
- Candidate file is 70231776 bytes (~32.0%) smaller than the current 350M file. This is only a disk-size fact. No Redmi TTFT/RSS/PSS/quality comparison exists, and no download or swap was performed.

### Executable experiment added

- v14/experiments/model_candidates.json: exact candidate revision, file size/hash and license provenance.
- v14/experiments/model_compare.py: read-only, sequential C3 comparison through the existing V13 LlamaRunner/llama-server path. It refuses a busy coordinator lock, verifies baseline/candidate GGUF size/hash and baseline registry revision, runs four exact-output tasks (2+2, source extraction, abstention, constraints), captures prefill/TTFT/decode/RSS/PSS metrics, redacts raw output, and never downloads, edits the installed manifest or swaps weights. Both run orders are supported to expose order/thermal bias. No active LoRA, user memory or Context OS prompt is applied, so this is an isolated C3 probe rather than E2E acceptance.
- v14/experiments/test_model_compare.py: 13 tests cover sequential runner use, exact-match negative controls, missing candidate, hash/revision failures, lock contention, symlinks, role/order bounds, native error/reaping, output redaction, same-artifact rejection and reverse order.

### Evidence state

- LOCAL_LINUX / Python 3.13.5 isolated implementation copy: py_compile PASS; 13/13 synthetic unit tests PASS. The tests use a fake runner; they are not native model inference.
- Full repository checkout/test discovery BLOCKED: local git could not resolve github.com. GitHub readback confirms the three experiment files exist on the research branch; exact PR CI remains pending.
- Native Linux/Termux model inference NOT RUN. Candidate GGUF and local V13 home are not present in this execution environment.
- Redmi status REDMI_UNVERIFIED; no authorized live device receipt.
- Release/deployment NOT_RELEASED; no UPDATE_REQUEST, download, install, weight swap or updater action.

### Next step

Review and run the exact branch tests in CI. If the pinned 230M GGUF is already present on the authorized Redmi, run both orders while V13 is idle and compare TTFT/prefill, decode, RSS/PSS and task checks. If absent, obtain separate explicit consent before downloading it to an isolated lab slot; keep the 350M production model unchanged. B1/B2 model comparisons remain separate work and are not claimed complete.


### PR / CI checkpoint — 2026-11-21

PR #2142 (https://github.com/RedMentos/Aii/pull/2142) is open, ready for review and mergeable at last readback, based on c3c32c05a0374e970d274f8a777a7ab85c067d66. Code-bearing checkpoint 64ff26aa51f3a9ec4c6a169588ef41004b7ba2a0 adds a focused V14 experiment workflow at .github/workflows/v14-model-lab.yml. Exact branch CI PASS: workflow run 44848887759, job model-lab, on head commit 3e13188a414b1cc3ff327fe9897a07d0d5ff8900. It compiled both Python files, validated the candidate JSON, and ran 13 tests in 0.042s on GitHub Linux/Python 3.13.18. This is exact-commit CI, not native inference. Native model execution and Redmi proof remain NOT_RUN/REDMI_UNVERIFIED.


### Shared V14 handoff updated — 2026-11-21

V14_WORK_BOARD.json now marks V14-005 IN_PROGRESS_PARTIAL and links PR #2142 plus exact CI run 44848887759. V14_USER_NEXT_ACTION.md now records the lab candidate, license, no-download/no-swap boundary, exact CI, native NOT_RUN and Redmi UNVERIFIED. The current shared base is c3c32c05a0374e970d274f8a777a7ab85c067d66; last fully updater-gate-green code SHA remains 5b9171a457f32cafa6cc05fb88e80ef8b4dad08e; newer merged code-bearing SHA 3db6d1f00fceab9e7755bc8f4c25882ef7f19258 (#2137) now has exact merge-push CI GREEN: staged-runtime 240 passed/10 skipped/47 subtests, integrated regression 415 passed/3 skipped/58 subtests, and V14 T8 real-Store workflow 44847403231 PASS. No Redmi installation receipt exists. The branch's code-bearing CI-tested commit is 3e13188a414b1cc3ff327fe9897a07d0d5ff8900; later changes are documentation-only.
