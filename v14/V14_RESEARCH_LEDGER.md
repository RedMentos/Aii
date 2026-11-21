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

- **Transferable Latency Prediction for Fast LLM Screening on Heterogeneous Edge Devices**, Xiaolong Tu et al., arXiv:2607.21602, posted 2026-05-11. Full arXiv text reviewed; peer-reviewed venue/status not independently confirmed. The paper models each run as a hardware-runtime-model-prompt configuration, separates prefill and decode, and fuses static descriptors with dynamic telemetry. It reports Pixel 8/8 Pro and Jetson/Orange Pi/RTX 3090-class experiments. Its reported cross-device calibration improvements are evidence that latency predictors need target-device calibration, not that Pixel numbers predict Redmi results. Critical caveat from the full text: it records generated-token count and per-run runtime telemetry, then describes random request-level train/test partitioning; it is unclear whether the dynamic predictor receives telemetry from held-out test executions. That creates a possible test-telemetry leakage issue for the claimed pre-execution screening use case. The within-device test sets are small (11 and 41 requests), and the paper itself notes a Pixel 8 Pro total-latency case where the static baseline beats the full predictor. Treat the headline R-squared gains cautiously; this project adopts only the phase-separated measurement schema, not the predictor or its screening claims. Concrete V14 adaptation: retain separate prefill-to-first-token, TTFT, decode throughput, RSS/PSS, runtime revision, prompt suite and device/thermal context for every candidate run. Source: https://arxiv.org/abs/2607.21602
- **DVFS for Small Language Model Inference on Mobile Edge Devices**, Jiesong Chen et al., arXiv:2609.13153, posted 2026-07-08. Full arXiv text reviewed; preprint status, no peer-review claim. DVFSLM reports up to 12.4% lower energy/token than built-in governors and up to 8.4% versus GearDVFS, with QoS gains, on NVIDIA Jetson AGX Orin and Orin NX. Its prototype coordinates GPU/EMC frequencies and a CPU threshold. Those hardware controls are not a safe or available assumption for ordinary Redmi/Termux CPU inference; no DVFS code is adopted. Source: https://arxiv.org/abs/2609.13153

### Candidate provenance and licensing

- Current C3 baseline from v13/code/specs/models.json: LiquidAI/LFM2.5-350M-GGUF, pinned revision 657e078c94084481950a2d555a941481f715536b, QAD_Q4_0, 219312832 bytes, LFM Open License 1.0.
- Prior C3 candidate from the same registry history: LiquidAI/LFM2.5-230M-GGUF, revision cdf97bd8205908758f44aec508d68ac1aef98f5c, QAD_Q4_0, 149081056 bytes, SHA256 e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292. Official model page and LICENSE checked 2026-11-21: LFM Open License 1.0, not Apache-2.0; Section 5 conditions Commercial Use on not exceeding its defined threshold (annual revenue USD 10 million or more) and does not license Commercial Use by a Legal Entity that exceeds that threshold; it states a qualified non-profit exception for non-commercial/research purposes. Model source: https://huggingface.co/LiquidAI/LFM2.5-230M-GGUF
- Candidate file is 70231776 bytes (~32.0%) smaller than the current 350M file. This is only a disk-size fact. No new baseline-vs-candidate Redmi TTFT/RSS/PSS comparison exists, and no download or swap was performed. Historical issue #1904 reports a Redmi C3 230M run answering 2 instead of 4 for 2+2; this is a direct quality warning against treating 230M as a trusted replacement.

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

PR #2142 (https://github.com/RedMentos/Aii/pull/2142) is open, ready for review and mergeable at last readback, based on c3c32c05a0374e970d274f8a777a7ab85c067d66. Code-bearing checkpoint 64ff26aa51f3a9ec4c6a169588ef41004b7ba2a0 adds a focused V14 experiment workflow at .github/workflows/v14-model-lab.yml. Exact branch CI PASS: workflow run 44849343250, job model-lab, on exact PR head 6aadf841434bcc43fbde1827a4ed2ef9d61bc4b0. It compiled both Python files, validated the candidate JSON, and ran 13 tests in 0.020s on GitHub Linux/Python 3.13.18. This is exact-commit CI, not native inference. Native model execution and Redmi proof remain NOT_RUN/REDMI_UNVERIFIED.


### Shared V14 handoff updated — 2026-11-21

V14_WORK_BOARD.json now marks V14-005 IN_PROGRESS_PARTIAL and links PR #2142 plus exact CI run 44849343250. V14_USER_NEXT_ACTION.md now records the lab candidate, license, no-download/no-swap boundary, exact CI, native NOT_RUN and Redmi UNVERIFIED. The current shared base is c3c32c05a0374e970d274f8a777a7ab85c067d66; latest fully CI-green code-bearing merge is 3db6d1f00fceab9e7755bc8f4c25882ef7f19258 (#2137); previous fully updater-gate-green code SHA was 5b9171a457f32cafa6cc05fb88e80ef8b4dad08e. The newer merge has exact merge-push CI GREEN: staged-runtime 240 passed/10 skipped/47 subtests, integrated regression 415 passed/3 skipped/58 subtests, and V14 T8 real-Store workflow 44847403231 PASS. No Redmi installation receipt exists. The code/manifest CI-tested commit is 6aadf841434bcc43fbde1827a4ed2ef9d61bc4b0; later candidate-manifest edits are wording/status-label only and locally JSON-validated; other changes are documentation-only.


### QA correction — 2026-11-21: bind model-lab evidence to the executable LlamaRunner actually uses

- QA identified that V13 `LlamaRunner.__init__` honors `V13_LLAMA_SERVER`, while the first model-lab report hashed only `home/bin/llama-server`. A different override could therefore run one binary while the report attributed the result to another.
- Fixed in PR #2142: `verified_runner_binary()` resolves and checks `runner.binary` against the installed, hash-verified executable before any task starts; after generation it checks `runner._loaded_binary` (the actual `cmd[0]` selected at load) and aborts if it differs. The report now records the resolved executable name, size and SHA256 from the runner itself, plus whether launch identity was verified. Baseline and candidate runs must use the same digest.
- Three negative/positive regressions added: different `V13_LLAMA_SERVER` override is refused before generation; an override resolving to the installed binary is accepted; a changed loaded executable aborts and reaps the runner. Current test file has 16 tests total.
- LOCAL_LINUX isolated helper regression: `py_compile` PASS; 5/5 identity checks PASS. This is a focused helper-level test, not the full repository suite. Full checkout remains BLOCKED by local GitHub DNS failure.
- Initial exact-head run 44853309109 exposed only a test assertion-message mismatch: the helper correctly rejected the changed executable, but the regression expected a different wording. The assertion was aligned without weakening the fail-closed check. The corrected exact code/test SHA `f5c5265a89258a6fd1ab5d25c20c733d21bb2ab4` passed model-lab run 44853451281 on GitHub Linux/Python 3.13.18: compile, manifest validation and 16/16 tests.
- Native GGUF inference NOT_RUN; no candidate file downloaded; no model, manifest, permission, memory or user data changed. Redmi REDMI_UNVERIFIED; NOT_RELEASED.
- Next falsifiable step: exact-head CI and independent review; only then, if the pinned 230M file is already present, perform both orders on the authorized idle Redmi. If absent, ask separately before isolated download. No production swap from this diagnostic comparison.


### A5 RAW EAR review note — remaining feature gap, 2026-11-21

Review of the merged A5 source and Core staged consumer confirms the present acoustic path is deliberately bounded and consent-rechecked, but its measured feature vector is still only RMS/peak/zero-crossing rate. The canonical packet explicitly labels pitch, speaker, speech probability and prosody as unmeasured. The staged consumer rechecks the consent provider at packet admission, context creation and each B1/B2/C3 read; raw PCM and the callback remain process-local in the candidate overlay. This is a useful partial A5 path, not full voice/perception completion.

Next implementation hypothesis: add a low-cost framed acoustic feature layer (energy contour, autocorrelation F0/voicing confidence, pause/speech-nonspeech probability, spectral centroid/rolloff and prosodic slope) with explicit per-window time/finality and source digest. Avoid person identification; use only a non-identifying speaker-change/turn-boundary cue if consented. Benchmark CPU/RSS on ARM before considering it for Redmi. Do not mark Android microphone, speech decoding, diarization, full-duplex or live prosody as implemented from these synthetic PCM tests.


### A5 timed-audio contract review — 2026-11-21: preserve provisional/final state across Runtime

Review of Core PR #2144 found a real promotion risk at the Runtime boundary:
- The staged `audio_window` exact-field schema has no `finality` field.
- The overlay calls `consume_pcm16_window(...)` without its `finality` argument; the existing bridge defaults that argument to `FINAL`.
- Consequently a caller-supplied partial/provisional audio window cannot remain `PROVISIONAL` through the normal Runtime path. The downstream `audio_to_admission()` and `Percept.final` gate can exclude provisional packets only if the producer passes the correct state.
- Review comment posted on Core PR #2144 requesting an explicit validated `PROVISIONAL|FINAL` field, pass-through, and tests: provisional remains visible to A4 as provisional but is not admitted to B1/B2/C3; final may be admitted; revocation still blocks each consumer.
- Consent rechecks are present in the staged path at admission, context creation and per-consumer reads. This is a positive partial result, not microphone/Android proof.
- The current base RAW EAR extractor still reports RMS/peak/zero-crossing rate only. Pitch, voicing, speech/non-speech probability, prosody and speaker-change cues are explicitly unmeasured. Avoid claiming complete RAW EAR/voice from the PCM fixture.
- No Core-owned code was changed in this review. Next Perception implementation should add low-cost time-windowed energy/F0/voicing/prosody signals and a non-identifying speaker-change cue, then benchmark CPU/RSS/latency on ARM before wiring. Native Redmi and microphone remain UNVERIFIED.


### Research candidate — low-cost RAW EAR VAD/prosody, 2026-11-21

**Primary paper read:** Zheng-Hua Tan, Achintya Kumar Sarkar, Najim Dehak, *rVAD: An Unsupervised Segment-Based Robust Voice Activity Detection Method*, Computer Speech & Language 59 (2020), pp. 1–21, DOI [10.1016/j.csl.2019.06.005](https://doi.org/10.1016/j.csl.2019.06.005); arXiv preprint first posted 2019-06-09 ([arXiv:1906.03588](https://arxiv.org/abs/1906.03588)). Full method and experiment sections inspected.

- Method: two-pass denoising, pitch-anchored segment extension and posterior-SNR-weighted energy-difference VAD. The low-compute rVAD-fast variant substitutes spectral flatness for pitch.
- Reported evidence: Aurora-2 average FER 11.26% for default rVAD vs 12.87% for rVAD-fast. rVAD-fast was about 14x/17x faster in the paper's desktop timing experiment (Intel i7-4790, 16 GB RAM), not on Android. On noisy RedDots white-noise trials, rVAD-fast breaks down (e.g. 0 dB EER about 99.34% versus 34.46% for rVAD); it works much better on babble/market/car noise. This is a direct reason not to use spectral-flatness-only VAD as the sole voice gate.
- V14 use: candidate for a non-authoritative speech/non-speech hint and voiced/unvoiced segmentation, not speaker identification, truth, or action authority. Keep raw acoustic features and VAD output separate; VAD must not delete non-speech events that may carry prosody/emotion/interaction cues.
- Code/license caveat: paper links MATLAB and Python rVAD-fast ZIPs, but their source license was not verified from the linked downloads; do not copy/reuse until exact source and license are inspected.

**Maintained OSS candidate:** [dpirch/libfvad](https://github.com/dpirch/libfvad), standalone WebRTC VAD fork, repository labels it BSD-3-Clause and documents Autotools/CMake plus `make check`. It also carries a separate [PATENTS](https://github.com/dpirch/libfvad/blob/master/PATENTS) file with Google's additional patent grant/termination language; preserve and review that file with the BSD license. Upstream WebRTC API accepts 8/16/32/48 kHz and 10/20/30 ms frames ([pinned upstream source example](https://webrtc.googlesource.com/src/%2B/f8e91dfdf4ddb91fe8308e33e4d960994612217a/common_audio/vad/webrtc_vad.c)). This is a VAD baseline only, not pitch/prosody or speaker diarization. No exact libfvad revision, Android ABI build, Termux packaging, RSS or Redmi latency has yet been verified.

**Concrete next experiment:** compare current RMS/peak/ZCR-only RAW EAR against (1) a small framed F0/voicing + energy-contour feature extractor and (2) optional libfvad VAD. Use synthetic voiced tone, unvoiced/noise, silence, burst noise and mixed speech-like frames; measure CPU time/RSS and false-accept/false-reject under multiple noise conditions. First compile the pinned C source for aarch64/Termux; do not claim Android support from Linux CI. Preserve PROVISIONAL/FINAL timing and never drop non-speech packets merely because VAD says non-speech.
