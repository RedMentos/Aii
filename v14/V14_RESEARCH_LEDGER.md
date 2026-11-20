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


## Neue Recherche — 2026-11-21 (Primärquellen, noch keine Adoption)

| ID | Primärquelle / Datierung | Tatsächlicher Kenntnisstand 2026-11-21 | Konkrete V14-Idee / Hypothese | Nächster harter Test |
| --- | --- | --- | --- | --- |
| R-007 | **V-JEPA 2.1: Unlocking Dense Features in Video Self-Supervised Learning**, arXiv:2603.14482, Erstfassung 2026-03-15 / Revision 2026-06-11; https://arxiv.org/abs/2603.14482 ; Code: https://github.com/facebookresearch/vjepa2 | ABSTRACT_VERIFIED; Einleitung und zentrale Methodikpassagen geprüft, Volltext nicht vollständig auditiert. Die Arbeit sagt, dass Masked-only Prediction lokale Struktur schwach erhalten kann; zusätzliche Vorhersage sichtbarer Kontext-Tokens und tiefe Self-Supervision über mehrere Encoder-Layer verbessern in den berichteten Vision-/Videoaufgaben dichte und globale Features. Große ViT-G-Modelle bis 2B Parameter; kein Redmi-Beleg. | Für A1/A4 lokale räumlich-zeitliche Details und globale Ereignis-/Gist-Repräsentationen getrennt messen, statt zu erwarten, dass ein einzelner globaler Pool beide zuverlässig erhält. Das ist eine Wahrnehmungs-Hypothese, kein Beleg für B1/B2-LLM-Latentkopplung. | Kleine ARM-taugliche A-plane Probe: masked-only vs masked+visible-context vs multi-layer auxiliary loss; lokale Objekt-/Ereignis-Lokalisierung, globales Ereignisverständnis, Speicher und TTFT vergleichen. |
| R-008 | **A Lightweight Library for Energy-Based Joint-Embedding Predictive Architectures (EB-JEPA)**, arXiv:2602.03604, 2026-02-03; https://arxiv.org/abs/2602.03604 ; https://github.com/facebookresearch/eb_jepa | ABSTRACT_VERIFIED; GitHub-README und LICENSE geprüft. Enthält Image-, Video- und action-conditioned Video-JEPA samt Two-Rooms-Planungsbeispiel; Repository-Lizenz Apache-2.0. README sagt, die Beispiele seien auf einzelne GPUs und Stunden Training ausgelegt; Default-Konfigurationen sind H100-orientiert. Kein Android-/ARM-Proof und keine direkte V14-Integration. | Als lesbare Referenz für Energie-/Anti-Collapse-Regularisierung und action-conditioned latent prediction verwenden. Nur einzelne mathematische Ideen oder kleine isolierte Referenztests übernehmen; nicht die PyTorch/GPU-Trainingspipeline in die Redmi-App ziehen. | Auf kleinem synthetischem Zustands-/Aktionsdatensatz Loss-Komponenten und Collapse-Metriken reproduzieren; danach Parameter-/RAM-/CPU-Kosten gegen aktuellen lokalen World-Predictor messen. |
| R-009 | **Experience Replay Addresses Loss of Plasticity in Continual Learning**, arXiv:2503.20018, 2025-03-25; https://arxiv.org/abs/2503.20018 | ABSTRACT_VERIFIED; Einleitung und Architektur-/Ergebniszusammenfassung geprüft, Volltext nicht vollständig auditiert. Die Autoren berichten in ihren getesteten Regression-, Klassifikations- und Policy-Evaluation-Tasks, dass Replay mit Transformer-Architektur den Plasticity-Verlust vermied; MLPs und RNNs blieben in ihren Experimenten trotz Replay betroffen. Der In-Context-Learning-Mechanismus wird ausdrücklich als Hypothese diskutiert, nicht als bewiesene Erklärung. | Unser bestehender OnlinePredictor ist ein kleiner linearer Predictor mit Reservoir-Replay. Seine Replay-/Retention-Tests beweisen daher gerade **nicht**, dass er zukünftige Lernfähigkeit erhält. V14-004 muss Retention und künftige Adaptierbarkeit separat messen; ein kleiner Transformer-/Adapter-Receiver ist eine zu testende Alternative, kein vorweggenommener Sieger. | Langstrom-Protokoll: periodisch neue, disjunkte Aufgaben einführen; nach jeder Phase (a) alte Holdout-Retention, (b) Lernfortschritt auf einer frischen Aufgabe bei gleichem Updatebudget, (c) Parameter-/Gradientenaktivität und Kosten messen. Linear+Replay vs kleiner Transformer+Replay vs kein Replay. |
| R-010 | **Plasticity of Growing and Elastic Neural Networks in Online Continual Learning**, arXiv:2608.01475, 2026-08-02; https://arxiv.org/abs/2608.01475 | ABSTRACT_VERIFIED; Einleitung und Versuchsaufbau teilweise geprüft. Adaptive Growing-/Elastic-Varianten konnten in den berichteten Online-Permuted-MNIST/FashionMNIST-Setups Plastizität erhalten; Elastic-Varianten kombinierten Wachstum mit Pruning und nahezu konstanter Größe. Keine Evidenz für Android-LLMs oder sparse-MoE-Körper. | Späteres Adapter-/Head-Labor: begrenztes strukturelles Wachstum nur bei messbarem Utility-Gewinn, Pruning nur nach Holdout-/Retention-Nachweis und mit Rollback. Harte RAM-/Storage-Budgets bleiben außerhalb des lernenden Modells. | Feste Adapterzahl vs bounded grow-only vs bounded grow+prune unter identischem Speicherbudget; neue Task-Anpassung, alte Retention, Peak-RSS, Checkpointgröße und Rollback vergleichen. |
| R-011 | **Data-driven Clustering and Merging of Adapters for On-device Large Language Models (D2C)**, arXiv:2601.17441, 2026-01-24; https://arxiv.org/abs/2601.17441 | ABSTRACT_VERIFIED; Methodenausschnitt geprüft. D2C gruppiert mehr Task-LoRAs als Speicherplätze verfügbar sind und nutzt wenige Beispiele je Task für iterative Clusterzuordnung vor dem Adapter-Merge. In der geprüften Quelle ist eine nicht-exklusive arXiv-Distributionslizenz angegeben; kein verifiziertes OSS-Code-/Gewichtslizenzpaket gefunden. Daher **kein Code-Reuse**. | Modell-Labor kann später Adapter-Slots nach gemessener Aufgabenähnlichkeit verwalten, ohne automatisch Base-Weights zu mergen. Jede Zusammenlegung braucht disjunkte Validierung, Konflikt-/Safety-Tests und getrennten Rollback. | Erst synthetische LoRA-Deltas mit bekannten Konflikten: random/K-means/D2C-Zuordnung; danach Holdout-Qualität und Speicherbudget. Keine Produktionsänderung ohne Lizenz- und Modellkartenprüfung. |

### Konsequenz für den aktuellen Implementierungspfad

- PR #2135 verbessert Commit-Konsistenz und Exactly-once-Verarbeitung des existierenden linearen OnlineWorld-Predictors. Das ist **Persistenzkorrektheit**, kein Nachweis gegen Loss of Plasticity.
- Für V14-004 fehlt weiterhin der Langzeit-Test der *zukünftigen Lernfähigkeit* nach vielen Updates. Der nächste echte Lernschritt sollte diesen Holdout-/Plasticity-Benchmark an den vorhandenen Consumer anschließen, bevor ein anderer Optimierer oder eine Architektur übernommen wird.
- EB-JEPA ist Apache-2.0 als Repository, aber seine GPU-orientierten Trainingsbeispiele sind kein Android-Reuse-Kandidat ohne Dependency-/RAM-Port. V-JEPA 2.1/D2C werden hier als Forschungsreferenzen geführt, nicht als freigegebene Gewichte oder Code-Abhängigkeiten.
