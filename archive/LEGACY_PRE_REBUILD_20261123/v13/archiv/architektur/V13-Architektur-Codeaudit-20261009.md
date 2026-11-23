# V13 / Inquisition — Architektur aus dem gesicherten Code

Stand der Quelle: **09.10.2026, 00:28:45 CEST**. Grundlage: `V13-WORK-RESCUE-20261009.zip`, darin das vollständige `V13-Redmi-Start.zip`. Das Bild bildet diesen gespeicherten Stand ab. Änderungen im parallel arbeitenden Chat sind nicht sichtbar. In diesem Auftrag wurde der Projektcode nur gelesen, nicht weiterentwickelt.

## Wie das Bild zu lesen ist

- **DA:** im ausdrücklich genannten Text-/Operator-Umfang vorhanden; kein Beleg für die vollständige Canon-Fähigkeit.
- **TEIL:** ein konkreter Teilpfad existiert, die breitere Fähigkeit oder ihr Nutzennachweis ist offen.
- **LAB:** isolierter nativer Versuch; keine daraus abgeleitete Produktions-/Trainings-/B3-Freigabe.
- **PLAN:** laut Canon noch zu implementieren oder gesperrt.

Die Pfeile oben zeigen die wesentlichen Informationswege, nicht einen vollständigen Funktionsaufrufgraphen. Die Fabrics wirken quer über A/B/C. Der untere Lernbereich listet alle zehn unabhängigen externen neuronalen Komponentenpfade. Ob ein bestimmtes Artefakt auf dem Telefon aktiv ist, hängt von dessen lokaler Generation und der ausdrücklichen Freigabe ab; das lässt sich aus dem Quellarchiv allein nicht feststellen.

## Tatsächlicher Antwortpfad

`runtime.py::_turn` nimmt exakten Quelltext entgegen, prüft feste Regeln und Ressourcen, erzeugt das Percept und aktualisiert den Executive-State. Es ruft bei Bedarf Memory und `runtime.py::_route` auf. Der Router kombiniert Operator-Vorgaben, bestätigte Verfahren, deterministische Scaffold-Routen, einen freigegebenen externen Route-Head und natives Needle-Control mit einer begrenzten Agreement-Kalibrierung.

Die Routen sind `simple`, `detail`, `gist`, `both`. Wake/Halt können die Beobachterauswahl und einen begrenzten Re-entry beeinflussen. Die Body-Aufrufe erfolgen im gezeigten Vordergrundpfad nacheinander; es gibt maximal einen zusätzlichen B1-Aufruf. Frische Angebote werden als Hypothesen in den Antwortkontext aufgenommen. Eine symbolische Nachricht ist damit kein direktes Teilen nativer Hidden States.

| Route | Nativer Final-Generator |
|---|---|
| simple | C3_LANGUAGE |
| detail | B1_DETAIL |
| gist | B2_GIST |
| both | B1_DETAIL mit ausgewählten Angeboten |
| Ressourcen-PRESSURE | C3_LANGUAGE als begrenzter Fallback |
| Exakte freigegebene Regel / explizites Copy | Quellenkopie über C5, keine Modellgeneration |

Die Antwort wird gestreamt und dauerhaft gespeichert. `ActionIntent`, `CorollaryCopy`, `ActionOutcome` und die digitale World-Beobachtung verbinden Absicht und Ergebnis. Bei Fehler/Deadline kann C1/C5 einen quellengebundenen Systembericht liefern. Hintergrund-Angebote nach dem Commit ändern die bereits gespeicherte Antwort nicht.

**JEF ist das Subsystem C0–C7**, nicht allein Needle3. C3 ist ein Sprachorgan innerhalb von JEF. B1/B2 können weiterhin selbst finale Inhalte generieren, während C5 die Ausgabeautorität hält.

## Modelle und Zustände

| Rolle | Gepinnter Basispfad im aktuellen Installer | Umfang |
|---|---|---|
| B1_DETAIL und B2_GIST | LFM2.5-1.2B-Instruct-QAD-Q4_0 | Dieselben ~695.8 MB Modellbytes, verschiedene Rollen/Views und Zustände; kein implementiertes Sparse-MoE-Paar |
| C2_CONTROL | Cactus-Compute/needle3, CQ2 | ~35.3 MB Modell; strukturierte Kontrolle und frozen Embeddings |
| C3_LANGUAGE | LFM2.5-230M-QAD-Q4_0 | ~149.1 MB Modell; freie Sprache, eingeschränkte Qualität |
| Vergleich/Teacher | Explizit ausgewähltes lokales Modell; gesonderter gepinnter SmolLM2-Vergleich | Kein stillschweigender Produktionswechsel und keine Teacher-Wahrheitsautorität |

Die Größen sind Dateigrößen, **keine residenten RAM-Messungen**. Native Backbones bleiben im regulären Lernpfad eingefroren. Der derzeitige B2-Langzustand besteht aus erneut geprüften Quellen und früheren Angeboten: standardmäßig vier Slots und 768 serialisierte Kontextzeichen. B1 nutzt einen kurzen vorherigen Hypothesenzustand. Das ist keine persistente native KV-Kontinuität. Die Default-Kontextgrenze pro Rolle beträgt 2048 Tokens; 90 Sekunden sind die konfigurierbare absolute Deadline, kein gemessener Latenzanspruch.

A3 trainiert einen kleinen Raw-Text-Projektor: UTF-8-N-Gramme → 512D Raw-Features → 16D Latent, mit getrennten Alignment-/Reconstruction-Zielen. Seine gemessenen frozen Targets stammen hier aus Needle-Embeddings (3072D). Dieser enge Referenzpfad ist vorhanden, obwohl ältere A2/A3-Katalogzeilen noch pauschal „unavailable/no alignment“ sagen. Ein allgemeiner multimodaler A2-Teacher oder native A3→Body-Injection ist damit nicht fertig.

## Die zehn externen Lernpfade

| Artefakt | Eingang und Ziel | Tatsächlicher Consumer / Grenze |
|---|---|---|
| route | Frozen Needle, explizite vierklassige Human-Labels | Runtime-Routing; kein Needle-Backbone-Training |
| wake | Frozen Needle-Kontext, Wake-Labels | Body-Auswahl none/detail/gist/both |
| halt | Frozen Needle-Kontext, Halt-Labels | Begrenzte halt/continue-Entscheidung |
| control_calibration | Tatsächlicher erster nativer Control-Vorschlag + Labels | Kleine Agreement-Kalibrierung; keine allgemeine semantische Wahrheitssicherheit |
| output_adapter | Tatsächlicher C3-State + voller nativer Wortschatz, Human-Ziel | Externes Delta für den ersten Token; Folgetokens ohne dieses Delta |
| a3_student | Raw-Text, frozen semantische Targets + Raw-Reconstruction | Percept-Features und JEF-Shadow-Vergleich; kein freigegebener Body-Receiver |
| b1_predictor | Read-only B1-2048D-Tokenstates | Lokaler t+2-Predictor und Tap-Auswertung; keine Body-Gewichtsänderung |
| b2_predictor | Read-only B2-2048D-Tokenstates | Entsprechender separater B2-Predictor |
| world_predictor | Tatsächliche digitale State/Action/Outcome-Paare | Aktion-konditionierte Latent-Prognose in `World.forecast`; keine externe Weltkausalität |
| memory_retrieval | Frozen Needle Query/Memory-Paar-Features + Human-Relevanz | Begrenzte quellengebundene Memory-Auswahl; C3-Endnutzung bleibt im neueren Test fehlerhaft |

Die Komponenten besitzen getrennte Artefakte/Generationen. Der Ablauf ist Shadow-Optimierung → Gradienten-/Held-out-/Support-/Retention-Prüfung → freigabefähiger Kandidat oder `EVALUATED_FAIL` → einzelne Operator-Freigabe → tatsächlicher Consumer → Neustart/Rollback. `RECORD_ONLY` führt kein Training aus. Die existence eines Lernpfads bedeutet keine autonome Aktivierung.

Body-/World-Zusatzpredictors besitzen Stop-Gradient-/Target-EMA-Mechanismen. Ein Route-Classifier oder eine Timing-Statistik wird deshalb nicht als vollständiges JEPA bezeichnet. F7 regelt gemessene langsame Budgets/Lernraten/Normen; eine durchtrainierte neuronale Metaplastizität existiert nicht.

## Native Schnittstellen: echte Fortschritte, enger Nachweis

| Native Experiment | Erhaltener Nachweis | Weiterhin offen |
|---|---|---|
| Same-causal-prefill observer | 5/5 feste Observer-on/off-Paare: echter 1024D-C3-State, 65 536 Logits/Verteilungen und Fortsetzung invariant | Produktionsintegration, Kompatibilität mit früheren Embedding-Heads, Latenzgewinn, Redmi |
| Pause/resume | Zwei tatsächliche Varianten im selben Prozess/Kontext; kein zweites Prefill, begrenzter erster Bias, drei unbeeinflusste Fortsetzungsschritte | Produktionsnutzung, Lernen, Geschwindigkeit, Redmi |
| Final-norm receiver | Baseline/Zero identisch; begrenztes Nonzero verändert volle Logits/Verteilung | Gelernter Projektor, sinnvolle Semantik, B3-Kalibrierung/OOD, Freigabe |
| Native final-RMSNorm-Parameterexperiment | Tatsächliche FP32-Masteränderung, numerische Prüfungen, frischer Reload/Rollback | Qualitäts-Gates verwerfen die gemessenen Kandidaten; kein akzeptiertes Runtime-Body-Training |
| Mid-layer receiver | Kompilation + 32 Guards, Ziel `l_out-6` → `norm-7` | Tatsächlicher nativer Effekt und jede semantische Nutzenaussage |

C3s neue 1024D-Live-State-Schnittstelle und die bestehenden 2048D-Body-Taps sind unterschiedliche Ports. Beide einfach als „latente Bridge fertig“ zusammenzufassen wäre falsch. Im Runtime-Callosum bleiben `latent_authority=0` und `receiver_effect_proven=False`; die numerischen Diagnosen ändern das nicht.

## Grenzen und nächste geplante Fähigkeiten

- **STEP2:** Der ursprüngliche vollständige 70-Zeilen-Lauf hatte 54 fehlerhafte Restart-State-Invarianten. Das neue feste v3-Kollektiv erreicht im gespeicherten Stand 42/70 strukturell gültige Zeilen und 138 native FINAL-Aufrufe. Der vollständige Nenner und validierte komplementäre Qualität fehlen. 42/70 ist kein Architektur-Fertigkeitsgrad.
- **Retrieval:** Neuere erhaltene Evidenz: 27/28 Prüfungen; C3 bekommt den exakten Quellenwert im ungekürzten Kontext, verwendet ihn aber nicht korrekt. B1 verwendet ihn. Ältere erfolgreiche Teilproofs ersetzen diese neuere Grenze nicht.
- **C3-Lernen:** First-Token-Lifecycle auf bekannten Greeting/Thanks-Familien vorhanden. Kein Nachweis allgemeiner deutscher Sprachqualität, Mehrpositionsadaption oder unbekannter semantischer Fälle.
- **Memory/Sleep:** Exact/Episodic Memory, native Replay, hypothetischer Dream, bestätigte Quellenindizes und exakte Human-Verfahren existieren. Parametrische semantische/Skill-Weight-Konsolidierung und autonome Schlafphasen sind offen.
- **Volle JEPA-Architektur:** Native trainierbare Sparse-Experts/aktive Scheiben, Quantisierungs-Train-Master, Body-local und bidirektionale A↔B-Cross-Ziele, B1↔B2-Projectors/Receiver-Kalibrierung sowie Executive-Latent-State müssen noch umgesetzt/validiert werden. Breite rekursive Inquisition und gelernte Admission/Salienz bleiben geplant.
- **Ressourcen:** Durable Queue, Abbruch, Linux-RSS/PSS-Monitoring und Modell-/Quellenprüfungen existieren. Aktueller Redmi-Dauerlauf, Thermik/Energie und genaue KV-Druckmessung fehlen. Historisches Redmi-SMOKE ist kein aktueller Vollnachweis.
- **Ausbau:** Vision/Audio/Sensorports, weitere Effectors und App-Aktionen, Full-Duplex, Teacher-Removal und höhere Ages bleiben gesperrt/geplant.
- **Sicherheit:** Exakte Operator-Regeln, Widerruf/History-Lineage und sichere Unicode-Anzeige existieren. Ein kleines allgemeines neuronales Modell, das sämtliche semantischen Antworten nachprüft, fehlt.

Die erhaltene Logdatei `docs/current-unit-deadline-lock-20261008.log` enthält **314 bestandene Softwaretests**. Das ist historische gespeicherte Evidenz. Für dieses Bild wurden weder die Suite noch native Modelltests erneut ausgeführt. Ein passender Gesamt-Collector auf exakt allen aktuellen Quellen und ein Zielgerät-Nachweis werden nicht allein aus älteren einzelnen PASS-Artefakten abgeleitet.

## Quellen und Nachweisgrenze

Gelesen wurden unter anderem `v13/runtime.py`, `cognition.py`, `learning.py`, `store.py`, `executive.py`, `output_policy.py`, `student_worker.py`, `world_worker.py`, `consolidation.py`, die Modell-/Komponenten-/Objective-Specs, die nativen C++-Portbeschreibungen, `BUILD_STATE.json`, die offenen Aufgaben und konkrete erhaltene Proof-Reports.

Canon: `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`. Die nummerierte Komponentenmatrix unten folgt dem aktuellen 30-Komponenten-Registry. Ältere F1–F7-Aliasse im langen Canon unterscheiden sich davon; die Zuordnung erfolgt anhand von Aufgabe/Schema/Owner und nicht nur nach dem Buchstabenpräfix.

`V13-Architektur-Evidenz-20261009.json` enthält die Hashes des Quellarchivs, der überprüften Quellfamilien und ausgewählter Proof-Reports. Hashes erlauben Identifikation, ersetzen aber keinen aktuellen Runtime-Test. Diese Datei bewahrt keine ungespeicherte Arbeit des anderen Chats.

## Alle 30 Komponenten mit Code-Zuordnung

| ID | Aufgabe | Geprüfter Teilumfang / Grenze | Implementierungsdateien |
|---|---|---|---|
| A0 | Raw sources | Exact text only; other modalities unavailable | `v13/store.py` |
| A1 | Segmentation | Text boundaries only | `v13/cognition.py` |
| A2 | Frozen input teacher | Enger frozen Needle-Targetpfad in A3 vorhanden; allgemeine Input-Teacher-Lane offen. Registry-Zeile veraltet. |  |
| A3 | Student projector | Textalignment/Reconstruction und JEF-Shadow implementiert; native Body-Receiver und Multimodalität offen. Ältere Limit-Zeile veraltet. | `v13/student_worker.py`, `v13/learning.py`, `v13/cognition.py` |
| A4 | Perceptual attention | Bounded text views; no learned salience or region requests | `v13/cognition.py` |
| A5 | Percept source binding | Text identity path | `v13/cognition.py`, `v13/store.py` |
| B1 | Detail body | Native dense body; sparse expert training unavailable | `v13/cognition.py`, `v13/runners.py` |
| B2 | Gist body | Bounded persisted source context; semantic complementarity unproven | `v13/cognition.py`, `v13/runners.py` |
| B3 | Callosum | Source-exact/Control/Symbolic-Pakete implementiert; isolated native numeric Receiver-LAB vorhanden; gelernte Produktionsbridge OFF. | `v13/cognition.py` |
| B4 | Active workspace | Explicit source slots; no trained latent admission | `v13/cognition.py`, `v13/store.py` |
| B5 | Fabric interfaces | State/recall interfaces; no learned access policy | `v13/memory.py`, `v13/world.py` |
| C0 | Shell and permissions | Local operator origin and text gate; external actions off | `v13/operator.py`, `v13/runtime.py` |
| C1 | Executive continuity | Bounded source-validated explicit executive task/state/action continuity and actual native context consumer. No learned executive latent objective or broad taskcompletion claim. | `v13/executive.py`, `v13/runtime.py` |
| C2 | Structured control | Actual Needle, external route head and approved first-native-proposal agreement calibration; general semantic confidence/native confidence-head training unproved | `v13/runners.py`, `v13/learning.py`, `v13/control_calibration_worker.py`, `v13/runtime.py` |
| C3 | Language organ | Real baseline local free language; limited model quality; human-approved external first-native-token rowdelta now implemented; native base frozen, general language/semantic OOD and phone proof remain open | `v13/runners.py`, `v13/runtime.py`, `v13/output_adapter_worker.py`, `v13/learning.py` |
| C4 | Focal coalition | Bounded fresh offers and one reentry; no learned competition | `v13/cognition.py` |
| C5 | Action/report intent | Single local text report owner | `v13/executive.py`, `v13/runtime.py`, `v13/store.py`, `v13/output_policy.py` |
| C6 | Egress port manager | Text only | `v13/store.py`, `v13/runtime.py` |
| C7 | Effectors | TTY text; speech/image/UI/motor unavailable | `v13/ui.py` |
| F1 | Attention/gain/admission | Deterministic source/freshness gates; learned gain unavailable | `v13/cognition.py` |
| F2 | Salience/interrupt/reflex | Preemption/cancel/resource guard; learned salience unavailable | `v13/runtime.py`, `v13/resources.py` |
| F3 | Memory/context/provenance | Source-backed exact/episodic memory plus approved learned Needle pair relevance; repeated cue-family native proof only, no learned fact truth or semantic/skill consolidation; Human-approved repeated-confirmation compaction and exact authored procedural cues now executable; no native weight merge or novel semantic generalization | `v13/memory.py`, `v13/store.py`, `v13/retrieval_worker.py`, `v13/learning.py`, `v13/consolidation.py` |
| F4 | Self/body/world prediction | Observed digital state/timing plus approved external action-conditioned latent predictor; no external-world causal truth, native body training or automatic semantic consolidation | `v13/world.py`, `v13/world_worker.py`, `v13/learning.py` |
| F5 | Action selection/safety/corollary | Actual local text-action ordering; no general action competition | `v13/store.py`, `v13/runtime.py` |
| F6 | Learning/eligibility/modulation | Ten independent external component paths with actual frozen inputs/native taps, explicit source-bound targets, gradients, scoped calibration/retention/ablations and individual approval. Full body/cross/executive JEPA, active sparse-expert training and native base masters remain unavailable. | `v13/learning.py`, `v13/learning_worker.py` |
| F7 | Metaplasticity/homeostasis/stability | Measured slow per-component shadow-budget feedback, atomic restart/idempotence, stability tags, bounded damping/reopening. No neural metaplasticity training, native shared-layer interference, source truth or autonomous commit authority. | `v13/resources.py`, `v13/learning_worker.py`, `v13/proofs.py`, `v13/plasticity.py`, `v13/learning.py` |
| F8 | Age/human control/rules | Individual artifact approval/rollback, rule generations, Age0 only | `v13/operator.py`, `v13/store.py` |
| F9 | Replay/dream/consolidation | Actual episodic replay and hypothetical dream; no autonomous consolidation; Human-approved repeated-confirmation compaction and exact authored procedural cues now executable; no native weight merge or novel semantic generalization | `v13/runtime.py`, `v13/consolidation.py` |
| F10 | Runtime/cache/scheduling/governor | Actual durable accepted queue, transactional schema migration, bounded continuous native RSS/PSS and cancellation. Current Redmi thermal/energy/KV and long-duration proofs remain open. | `v13/pressure.py`, `v13/resources.py`, `v13/runners.py`, `v13/runtime.py`, `v13/store.py` |
| F11 | Metrics/calibration/retention | Real metrics/proofs; general calibration/OOD/semantic utility open | `v13/verification.py`, `v13/proofs.py` |
