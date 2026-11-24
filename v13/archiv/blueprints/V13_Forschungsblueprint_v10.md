# V13 Forschungsblueprint

V13 soll ein dauerhaft lernendes System aus zwei unterschiedlichen vortrainierten MoE-Modellen, einem kleineren dichten Kontrollmodell, gemeinsamem latenten Arbeitsraum und einer rückgekoppelten Wahrnehmungs-, Handlungs- und Lernarchitektur werden. Der erste Zielkörper ist ein Redmi Note 10 Pro mit angenommenen 6 GB RAM. Die Gerätevariante muss durch eine lokale Diagnose bestätigt werden. Die vollständige Architektur ist bislang weder auf diesem Gerät ausgeführt noch als überlegen nachgewiesen.

Diese Fassung verbindet den übergebenen v9-Entwurf mit einem Quellenabgleich bis zum 14. September 2026, präziseren Schnittstellen und einem überprüfbaren Entwicklungsweg. Sie enthält sieben technische Abbildungen und ein getestetes Softwarefundament. **Age 0 lernt bereits in begrenzten Bereichen, während Lernregeln, Grenzen und Zuständigkeiten zunächst fest bleiben.** Spätere Öffnung betrifft einzelne Kompetenzen und Rechte; sie bedeutet keine pauschal steigende Lernrate.

## 1. Ergebnis und Lesepfad

**Kurzfassung:** Die Gesamtidee bleibt erhalten. Architekturziel, spezifizierte Funktion, vorhandene Implementation und nachgewiesene Wirkung werden ausdrücklich unterschieden.

Die Forschungsfrage lautet: Verbessern komplementäre Repräsentationen und erfahrungsgebundene lokale Anpassungen die Qualität, Retention und Ressourcennutzung eines kleinen dauerhaft betriebenen Systems? Darauf gibt es noch keine belastbare V13-Antwort. Aktuelle JEPA-, Latent-Reasoning- und Continual-Learning-Arbeiten liefern Bausteine, aber keine fertige kombinierte Lösung.

Vier Entscheidungen tragen den Entwurf:

- Native Sprachmodelle zunächst mit ihrer gelernten Token- und Routerkonfiguration erhalten; neue Kommunikationswege neutral beginnen und gezielt trainieren.
- Lokale Aktivität als Lernberechtigung erfassen. Eine lokale Ableitung liefert die Gewichtsänderung; positive Eigenbewertung ersetzt kein Trainingsziel.
- Erfahrung, aktuelle Zustände, Lernkandidaten, EMA-Targets und produktive Inferenzsnapshots getrennt versionieren.
- Android- und Modellfähigkeit vor der umfangreichen Integration prüfen.

| Kennzeichnung | Bedeutung |
|---|---|
| LOCKED | Übernommenes Architekturziel oder aktuelle ausdrückliche Vorgabe |
| BOOT | Technische Anfangsentscheidung; änderbar und zu messen |
| RESEARCH | Konkrete Hypothese mit notwendigem Versuch |
| OPEN | Messung, Schnittstelle oder Daten fehlen noch |
| QUELLE | Aussage eines benannten Papers, Modells oder Herstellers |
| GERECHNET | Ableitung aus angegebenen Größen |
| GETESTET | Im gelieferten Softwareumfang ausgeführt; kein Gerätebenchmark |

Kapitel 2 sichert den Canon. Kapitel 3 bis 5 begründen Forschung und Modellwahl. Kapitel 6 bis 13 spezifizieren das System. Kapitel 14 bis 17 führen zur Implementation und Abnahme. Drei vertiefende Forschungsanhänge enthalten zusätzliche Herkunfts- und Methodenbelege. Diese Ausgabe ist ein unabhängiger Research Blueprint, keine offizielle OpenAI-Freigabe.

## 2. Canon und bereinigte Widersprüche

**Kurzfassung:** Zwei verschiedene MoE-Hälften, direkter Austausch, echte lebenslange Gewichtsanpassung und ein zyklisches System bleiben LOCKED. Konkrete Modelle und Zahlen bleiben BOOT.

Grundlage sind der vollständig gelesene v9-Blueprint, der Starter, die Grafik und der strukturell ausgewertete historische JSON-Export. Dessen 379 Nachrichten enthalten auch kopierte KI-Pläne, Alternativantworten und Terminalprotokolle. Eine wiederholte Behauptung ist kein Messnachweis. Die Formulierungen zu bf16-Mastern und einer Scheibe pro Schritt stammen aus einer historischen Assistantantwort, `$.messages[221].prompt`. Die selektive Lernidee bleibt erhalten; bf16 ist keine unveränderliche Hardwarevorgabe.

| Bisher unklar oder zu stark | Präzisierung in v10 |
|---|---|
| Höheres Top-k bedeutet automatisch Gist | Top-k, Expertgröße und Repräsentationsauflösung sind unterschiedliche Achsen. |
| Acht Tokens gruppieren beschleunigt den Body achtfach | Zunächst Hidden States zu groben Workspace-Slots verdichten; native Tokenrechnung bleibt. |
| Gleiche Vektorlänge verbindet fremde Modelle | Eigene Readouts, Alignment und trainierter Empfangspfad sind erforderlich. |
| Eligibility mal Fehler ist schon ein Gewichtsupdate | Beteiligungsdaten begrenzen die Lernfläche; lokaler Loss und Ableitung liefern die Richtung. |
| EMA ist Lernen oder Konsolidierung an sich | Target-EMA, Studentlernen und Body-Konsolidierung sind getrennte Vorgänge. |
| Kleiner Loss beweist ein besseres Gehirn | Verhalten, neue Fähigkeiten, Retention und tatsächliche Nutzung separat messen. |
| KV ist exakter Langzeitspeicher | Exakte Quellen sind Memory; KV und rekurrente Zustände sind abgeleitet und versionsabhängig. |
| Dreaming liefert neue Fakten | Simulation liefert Hypothesen; externe Evidenz entsteht dadurch nicht. |
| Inaktive Pfade verändern sich niemals | Keine erfahrungsspezifischen Updates ohne Beteiligung; Homeostasis ist eigene Wartung. |
| Training kostet die Inferenz nichts | Vorrang umsetzen; Restwartezeit und thermische Nachwirkung messen. |
| Nahezu alles lernbar heißt alle Grenzen frei | Lernparameter bleiben von Rechten und expliziten Nutzerregeln getrennt. |

Ein unveränderlicher Snapshot während einer Antwort ist kein dauerhaft eingefrorener Body. Später darf eine validierte andere Version live gehen. Die Gesamtarchitektur wird auch nicht auf drei Text-API-Aufrufe oder ein unverbundenes Minilernnetz reduziert.

## 3. Vergleich mit dem Gehirn

**Kurzfassung:** V13 übernimmt Organisationsprinzipien. Gist, Callosum, Thalamus und Cerebellum beschreiben hier Funktionen, keine anatomisch genaue Gehirnkopie.

| Bezug | Wissenschaftlicher Anhaltspunkt | Übernahme für V13 |
|---|---|---|
| Aktivität und Modulation | Zeitlich begrenzte Dopaminwirkung auf aktive synaptische Strukturen [1] | Beteiligung und spätes Feedback einer Episode zuordnen |
| Mehrere Lernzeiten | Modelle gekoppelter schneller und langsamer Speicherzustände [2] | Schnelle Anpassung von langsamer Stabilisierung trennen |
| Homeostasis | Aktivitätsabhängige synaptische Skalierung in Zellkulturen [3] | Dominanz, Normen und Updatefrequenz begrenzen |
| Komplementäres Gedächtnis | CLS: schnelle Aufnahme und langsame Integration [4] | Neue Erfahrungen speichern und mit alten Beispielen mischen |
| Replay | Reaktivierung erfahrungsbezogener Muster im Schlaf [5] | Reale Episoden im Idle bearbeiten |
| Kontextabhängige Kopplung | Thalamische Beiträge zu präfrontaler Aufmerksamkeitskontrolle [6] | Kleine Admission-/Routingfunktion |
| Aktionskontrolle | Differenzierte striatale Outcome-/Aktionssignale [7] | Vorschlag, Auswahl, Ausführung und Ergebnis trennen |
| Schnelle Rückkopplung | Reziproke kortiko-zerebelläre Aktivität in untersuchten Aufgaben [8] | Kleines aktionsbezogenes Vorhersagesystem |
| Eigene Verursachung | Corollary-Discharge-Pfade übertragen Bewegungsinformation [9] | Auftragskopie und erwartetes Ergebnis erfassen |

Die Übertragungen sind Designentscheidungen. Ein Software-Tag ist keine Synapse. Ein Workspace oder die Bezeichnung Conscious Core beweist kein Bewusstsein. Eine Gleichsetzung von linker/rechter menschlicher Hemisphäre mit Detail/Gist wird nicht verwendet. Für V13 zählt messbare komplementäre Verarbeitung; Modellnamen allein erzeugen sie nicht.

### Fliegenhirn und Verkörperung

FlyWire beschreibt eine umfangreiche Verdrahtung des adulten Fliegenhirns, nicht dessen vollständige Dynamik oder alle Lernregeln. [10] Flyvis verbindet Konnektomvorgaben mit trainierter Dynamik und prüft Aktivitätsvorhersagen im visuellen System. [11] Der Eon-Eigenbericht vom März 2026 beschreibt die Kopplung vorhandener Gehirn- und Körpermodelle und benennt zugleich Controller, eingeschränkte Verhaltensweisen und fehlende Plastizität. [12]

Die relevante Lehre ist die gemeinsame Prüfung von Struktur, Dynamik, Körper und Aufgabe. Ein Loop ist nützlich, wenn Aktionen folgende Beobachtungen verändern und Lernen spätere Entscheidungen verbessert. Das frühere YouTube-Video wurde nicht inhaltlich erschlossen; seine Identität mit einem dieser Projekte wird nicht behauptet.

## 4. Aktuelle KI-Forschung

**Kurzfassung:** Neue Arbeiten werden nach ihrem konkreten Beitrag ausgewählt. Ihre Mechanismen werden nicht ungeprüft in vorhandene Bodies eingebaut.

| Arbeit / Stand | Beitrag | Konsequenz für V13 |
|---|---|---|
| I-JEPA, 2023 [13] | Repräsentationsvorhersage aus Kontext | Zielansichten, Masken und Gradientenbesitzer definieren |
| V-JEPA 2, 2025 [14] | Wahrnehmung und aktionsbedingte Prediction | World-Lernen von Sprache und Action-Policy trennen |
| V-JEPA 2.1, 2026 [15] | Dichte und intermediäre Merkmale | Feine Information bei Gist-Kompression separat erhalten und testen |
| LeJEPA, 2025 [16] | Explizite Repräsentationsregularisierung | Anti-Collapse als eigener Vergleichsarm |
| e-prop, 2020 [17] | Lokale Sensitivitäten und Lernsignale | Participation-Tag ist nicht mathematischer Eligibility-Vektor |
| Titans / TTT, 2024–2025 [18,19] | Lernende Zustände innerhalb trainierter Dynamik | Fast Memory getrennt von langfristigen Bodygewichten behandeln |
| DreamerV3, 2025 [20] | World Model, Actor und Critic mit eigenen Zielen | Predictionerror und Handlungsnutzen nicht vermischen |
| Coconut, Revision August 2026 [21] | Rückführung von Hidden States | Latentempfang trainieren und budgetgleich vergleichen |
| Kritische Coconut-Analyse, 2025 [22] | Shortcuts und Interventionen | Kein allgemeiner Reasoningbeweis aus einem Benchmark |
| FOREVER, ACL 2026 [23] | Replayplanung nach Modelländerung | Später Retention und Gewichtsbewegung für Replay nutzen |
| LoRA / QLoRA [24,25] | Kleine trainierbare Gewichtsänderungen | Mobiles Trainingsbackend bleibt separat nachzuweisen |
| BLIP-2 / ReFT [26,27] | Trainierte Brücken und Representation-Eingriffe | Alignment und Injection erhalten eigene Abnahmen |

Coconut berichtet aufgabenabhängige Gewinne, keinen allgemeinen Sieg über sprachliches Denken. Die kritische Untersuchung verwendet andere Aufgaben und Einstellungen. Gemeinsam begründen sie einen direkten V13-Versuch mit trainierter Brücke, ohne Brücke und mit budgetgleichem Textkanal.

DeepSeek-V4.1-Flash und GLM-5.3-Flash sind in offiziellen Repositorien dokumentiert. Ihre asymmetrische Verarbeitung beziehungsweise sparse/lineare Attention liefern Anregungen für Kosten- und Kontexttrennung. [28,29] Ihre Übernahme in kleinere Bodies benötigt eigene technische Arbeit und Training. Unveröffentlichte interne Architekturen proprietärer Modelle werden nicht geraten.

## 5. Modelle und Bibliotheken

**Kurzfassung:** Die bisherigen Kandidaten sind real. Für mobile Quantisierung, direkten Latent-Zugriff und lokales Lernen zusammen ist noch kein fertiger V13-Laufweg nachgewiesen.

| Rolle / Kandidat | Dokumentierte Struktur | Integrationsstatus |
|---|---|---|
| Gist: MobileMoE-S-QAT | 1,3B total, 272M aktiv, 60 geroutete Experten, Top-4, gemeinsamer Experte [30] | Custom-Architektur; Redmi-Port und V13-Hooks offen |
| Detail: ETET Preview Language Body | 1,42B; 24 Layer, letzte 8 mit je 3 Experten und Top-1 [31] | Standard-Llama-Loader ignoriert laut Card Experten; eigener korrekter Loader nötig |
| Judge: Qwen3.5-0.8B | Dichte FFN und hybride Attention [32] | Inferenzpfade vorhanden; Kontrollheads und ihre Nutzung bleiben V13-Arbeit |
| Gist-Alternative: Granite 3.1 1B-A400M | Config: 32 Experten, Top-8, Hidden Size 1024 [33] | Etablierter MoE-Vergleichskandidat, keine stille Canon-Ersetzung |

MobileMoE nennt 0,71 GB für den gepackten kleinen Checkpoint. Der dokumentierte Transformers-Pfad materialisiert INT4 beim ersten Forward als BF16: Dateigröße ist keine RAM-Zusage. Der Zugang verlangt Zustimmung; die Lizenz ist auf nichtkommerzielle Forschung ausgerichtet. [30] ETET ist eine Preview und unterscheidet Apache-2.0 für Gewichte von AGPL v3 für Code. [31] Das Startpaket verteilt weder Modelle noch fremde Trainingsdateien.

Das Gist-Ideal weniger/größerer Experten ist durch 60 kleine Experten nicht erfüllt. Höheres Top-k behebt den Geometrieunterschied nicht. LOCKED bleibt funktionale Asymmetrie; RESEARCH bleibt endgültige Expertgeometrie. Der 0,8B-Judge kann zudem erhebliche Kosten verursachen und ist nicht automatisch klein gegenüber den aktivierten Hälften.

| Fähigkeit | llama.cpp | ExecuTorch | MNN |
|---|---|---|---|
| Android-Inferenz allgemein | Android-/Termux-Weg dokumentiert [34] | MobileMoE-Arbeit nutzt mobile Kernel [35] | Android und Qwen3.5 dokumentiert [36] |
| Fremdes MoE | Familien-/Konvertersupport nötig | Export, Operatoren, Kernel nötig | Konverter und Dispatch nötig |
| Hidden Export / Injection | Konkrete native Integration prüfen | Graphschnittstellen exportieren | Modulinputs/-outputs prüfen |
| Lokaler V13-Backward | Aus Chat-Support nicht ableitbar | Eigenen Trainingsgraph prüfen | Eigenen Trainingsgraph prüfen |
| Gesamte V13-Abnahme auf Redmi | Offen | Offen | Offen |

BOOT vergleicht MobileMoE und Granite als mögliche Gist-Laufwege. ETET bleibt gesonderter Detail-Portierungskandidat. Ein Dense-Modell darf Diagnose-/Vergleichsarm sein, zählt aber nicht als zweite MoE-Hälfte. Falls ein Port scheitert, folgen gezielte Portierung, Suche nach einem passenden anderen MoE oder vorübergehende Experimente auf stärkerer Hardware. Das wäre jeweils noch keine fertige Redmi-Version.

## 6. Gesamtsystem und Modulverträge

**Kurzfassung:** Ein Scheduler wählt den nächsten begrenzten Schritt in einer rückgekoppelten Topologie. Persistente Zustände haben klare Besitzer.

![Zyklische Architektur](diagrams/01_architektur.png)

Module liefern versionierte Ergebnisse und Änderungsvorschläge, statt gemeinsam unkontrolliert einen Vektor zu überschreiben. Eine Episode kann nach einem Output weitergehen. Jeder Ausführungsabschnitt hat dennoch ein Zeit-/Ressourcenende. Nach Shutdown wird aus gesichertem Zustand fortgesetzt; ein ständig aktiver CPU-Loop ist nicht nötig.

| Modul | Eingabe und Ergebnis | Lernen / Anfangsverhalten |
|---|---|---|
| Sensory Port | Originaldaten in Observation mit Quelle, Zeit, Modalität | Text zuerst; weitere Modalitäten separat |
| Relay | Kandidatensignale in Admission-/Routingvorschläge | Feste Prioritäten; später kleiner Controller |
| Gist / Detail | Native Hidden States in grobe / feine Slots | Readouts/Adapter zuerst, Body-Slices später |
| Callosum | Ausgerichtete Nachricht in echten Empfangspfad | Zwei Richtungen, getrennte Optimizer |
| Workspace | Slots und Write-Requests | Herkunft, Konflikte, TTL, Versionen |
| Dense Judge | Workspace und Kontrollstate in Vorschläge/Output | Gemeinsamer Modellstate, kleine Köpfe |
| Cautiousness | Konflikt, Quelle, OOD in Kontrollmerkmale | Extern kalibrieren; keine Wahrheitsgarantie |
| Inquisition | Workspace in Hypothese/Rekonstruktion | P1/P2 sind Rollen eines kleinen Raums |
| World Model | Zustand, Aktion, Body in Folgebeobachtung | Reale Folgen; mehrere Futures später |
| Action Gate | Vorschlag und Fähigkeiten in erlaubte Aktion | Rechte/Budget zuerst fest |
| Fast Forward | Konkrete Aktion in Effekt-/Kostenprognose | Status, Dauer, betroffene Objekte |
| Corollary Copy | Ausführung in internen Auftragsdatensatz | Herkunft bleibt erhalten |
| Memory | Events in exakte und abgeleitete Einträge | Admission, Retrieval und Retention |
| Local Learner | Episode und Target in Kandidat | Lokaler Gradienten-/Optimizerbesitz |
| Meta/Homeostasis | Langsame Statistiken in Stellgrößen | Feste Regeln; spätere begrenzte Freigabe |
| Sleep Controller | Bedarf und Ressourcen in Replayjobs | Unterbrechbar, unabhängige Abnahme |
| Self/Body Schema | Fähigkeiten und Betriebslage | Kompetenzschätzung getrennt von Permissions |

In Schnittstellen heißt der historische Conscious Core `judge_core`. Der Name beschreibt Koordination und sprachliche Ausgabe, keinen Bewusstseinsbefund.

## 7. BodyPorts, Callosum und Repräsentationen

**Kurzfassung:** Die Kommunikationsbrücke muss bei beiden Modellen lesen und im jeweils anderen Body wirksam eingreifen können.

Ein `BodyPort` stellt native Tokenisierung, Forward, Readout, Nachrichteneinspeisung, Routertelemetrie und gegebenenfalls lokalen Backward bereit. Jede Fähigkeit erhält eine Capability-Deklaration und einen tatsächlichen Testbericht. Fehlende Fähigkeiten heißen `unsupported`; zufällige Antworten ersetzen sie nicht. Das Startpaket prüft Deklarationen, implementiert noch keinen Modellport.

Ein Latentpaket führt mindestens `sender_body`, `model_revision`, `projector_revision`, `layer`, `shape`, `dtype`, `source_spans`, `observation_ids`, `position_map`, `origin`, Zeit, Ablaufzeit und Schemaversion. Der Empfänger prüft diese Angaben. Fremde Zustände werden an lokalen Backward-Grenzen zunächst abgetrennt.

Gemeinsame Zuordnung erfolgt über UTF-8-Quellenspans oder Event-IDs. Beide Tokenizer haben eigene Positionskarten. Tokens mit gleicher Nummer sind nicht derselbe Inhalt. Gist-Slots umfassen mehrere Spans; Detail bewahrt feine Referenzen für Namen, Negation, Zahlen und Einheiten.

BOOT: acht native Tokens als Poolingrahmen und acht Workspace-Slots zu 256 Dimensionen sind Versuchsdefaults. Pooling erfolgt nach dem nativen Forward. Echte mehrskalige native Verarbeitung braucht weiteres Training. Ein später 4096-dimensional erweiterbares Schema enthält heute nicht schon mehr Information als seine tatsächlich verwendeten 256 Dimensionen.

Die Readouts bilden `z_A = R_A(h_A)` und `z_B = R_B(h_B)`. Gerichtete Cross-Attention erzeugt eine Nachricht, die ein trainierter Prefix-/Residualadapter empfängt. Anfangs schützt ein geschlossenes Gate das Vorwissen vor zufälligen neuen Parametern. Paarige Ansichten, Teacher-Ziele und Literalitätsaufgaben trainieren die Brücke.

Vier Abnahmen: native Ausgabe bei geschlossener Brücke erhalten; gerichtete Nachrichten beeinflussen den Empfänger; vertauschte Nachrichten schneiden schlechter ab; passende Kommunikation verbessert ungesehene Aufgaben bei gleichem Budget. Ohne diese Ergebnisse existiert eine Schnittstelle, noch keine nachgewiesene Kooperation.

## 8. Lokale Plastizität und Lernrichtung

**Kurzfassung:** Aktivität bestimmt die erlaubte Lernfläche. Ein überprüfbares lokales Ziel und dessen Gradient liefern die Änderung. Modulatoren steuern Berechtigung und Stärke.

![Lokale Plastizität](diagrams/02_lokale_plastizitaet.png)

Encoderparameter, Predictorparameter und passende Targetparameter werden getrennt geführt. Die Target-View darf Zukunftsinformation enthalten, die beim Vorhersagen im Eingang noch nicht verfügbar war. Ein zweiter Kanal darf diese Information nicht unbemerkt zum Predictor zurückleiten.

```text
z          = encoder(stop_gradient(local_input))
prediction = predictor(z, allowed_context)
target     = stop_gradient(target_encoder(target_view))
loss       = prediction_loss + representation_penalty + retention_loss
candidate  = local_optimizer_step(allowed_parameters, gradient(loss))
```

Dieser Vertrag ist noch keine universell richtige Lossfunktion. Vor dem Experiment werden Distanz, Normalisierung, Masken, Datenmischung, Horizont und Regularisierung festgelegt. Beispielgewichte im Predictive Loss sind nichtnegativ. Bei leerer gültiger Batch gibt es keinen Schritt. Ein schlechtes Outcome wird nicht zu negativem JEPA-Loss, der absichtlich schlechtere Vorhersage trainiert.

| Lernfläche | Erstes Target | Abnahme über den Loss hinaus |
|---|---|---|
| Gist-/Detail-Readout | Passende gehaltene/spätere Eventrepräsentation | Retrieval, Negation, Zahlen, neue Episoden |
| Callosum A nach B | Ausgerichtete B-Ansicht; B im Schritt konstant | Empfänger nutzt Information |
| Callosum B nach A | Entsprechende A-Ansicht; A konstant | Asymmetrie bleibt erhalten |
| World-/Forward-Predictor | Beobachteter Folgezustand, Status | Besser als letzter Zustand / häufigster Ausgang |
| Judge-Konfidenz | Unabhängig geprüfte Korrektheit | Kalibrierung und Fehlentscheidungen |
| Halting | Zusatznutzen gegen Zusatzkosten | Qualität bei gleicher Zeit |
| Action-/Routing-Policy | Definierter Erfolg oder passender Advantage | Echte Taskerfüllung und Kosten |
| Translator-Gate | Teacher-/Body-only-Vergleich | Gehaltene Qualität bei weniger Hilfe |

### Participation und spätes Feedback

Der BOOT-Trace ist ein Beteiligungsdatensatz, kein vollständiger synaptischer Eligibility-Vektor. Er bindet Pfad, Episode, Modell-/Snapshotversion, Zeit und lokale Datenreferenzen. Der kleine lokale Ableitungsgraph wird beim Lernen neu berechnet. e-prop motiviert diese Trennung; die Spiking-Netz-Herleitung wird nicht ungeprüft auf Transformer übertragen. [17]

Kurze Traces verfallen. Nachts wird eine gespeicherte Episode erneut abgespielt und erzeugt neue Beteiligung. Ein dauerhafter Konsolidierungstag ist deshalb ein anderes Objekt. Bei veränderten Produzentengewichten werden Originaldaten neu enkodiert oder passende Snapshots geladen. Alte Hidden States gelten nicht still als aktuell.

Nicht berechtigte Parameter dürfen durch Momentum, Weight Decay oder gemeinsamen Quantisierungsexport nicht unbemerkt driften. Optimizerzustände und Exportpartitionen werden entsprechend isoliert. Die Aktivierungsunion über viele Tokens kann dennoch viele Experten enthalten; Sparsität pro Token garantiert keinen kleinen Trainingsmaster für eine Episode.

### Kollaps, Quellen und Credit

Zwei Modelle können im selben Fehler übereinstimmen. Cosinusähnlichkeit ist ein Konsistenzmerkmal, keine Wahrheitswahrscheinlichkeit. Varianz/effective rank, Cross-view-Retrieval, Quellenentailment und spätere Aufgabenleistung werden getrennt geprüft. Kleine korrelierte Batches reichen als Kollapstest nicht; ein diverser unabhängiger Satz ist nötig.

Gute Gesamtausgänge verteilen nicht automatisch richtiges Credit an jeden aktiven Experten. BOOT nutzt konservative Beteiligungsmasken und passende lokale Ziele. Spätere Gegenproben können Beiträge schätzen. Exakte langfristige kausale Credit-Zuordnung im ganzen System bleibt RESEARCH.

## 9. EMA, Konsolidierung und langsame Regler

**Kurzfassung:** Schnell lernender Student, langsames Target und produktiver Body besitzen eigene Zustände. Kein Lernvorgang verändert den Forward mitten in einer Antwort.

Target-EMA lautet `target_new = rho * target_old + (1-rho) * student_new`, mit `0 <= rho < 1`. Sie gilt für kompatible Encoderparameter. Predictor wird nicht in Encoder und Gist nicht in Detail gemittelt. Student, Target und Optimizer gehören zu einem isolierten Kandidaten; verfehlte Abnahme verwirft sie gemeinsam.

Body-Konsolidierung ist ein eigener Vorgang. Ein LoRA-Delta lautet `delta_W = scale * B @ A`; die Faktoren sind keine Backbonekopie. [24] Ein validierter Kandidat kann `W_new = W_old + alpha * delta_W` sein. Nach vollständigem Merge wird der übernommene Adapter entfernt/rebasiert; bei Teilmerge bleibt nur der entsprechende Rest. Andernfalls wirkt dieselbe Änderung doppelt.

Phone-Lernen beginnt bei kleinen Projektionen, Predictors und Adaptern. Ausgewählte Body-Slices folgen nach Backward-, Ressourcen- und Exportprüfung. Ein höherpräziser Master oder persistenter Delta bleibt maßgeblich. Bei jedem Minischritt nur den INT4-Export neu zu laden kann kleine Änderungen vernichten. QLoRA ist kein Nachweis, dass beliebige Android-Inferenzkernel diese Trainingseigenschaften besitzen. [25]

Metaplastizität führt pro Modul Kompetenzstabilität, Updateempfindlichkeit und Wiederöffnungsbedarf. Homeostasis begrenzt Normen, Dominanz und Ressourcen. Ihre Anfangsregeln sind fest und langsamer als lokale Lernschritte, damit nicht mehrere Regler dieselbe Schwankung verstärken. Erfolgreiche Expert-Spezialisierung darf erhalten bleiben. Wiederöffnung seltener Pfade ist ein eigener geloggter Wartungsversuch.

## 10. Age als getrennte Freigabeachsen

**Kurzfassung:** Es wächst, was das System kontrollieren darf. Die Öffnung ist pro Fähigkeit reversibel und von unabhängiger Kompetenz abhängig.

![Age-Freigaben](diagrams/03_age_freigaben.png)

| Stage | Verhalten | Voraussetzung für weitere Öffnung |
|---|---|---|
| Age 0 | Begrenzter LLM-artiger Ablauf, wenig Memoryänderung, schmale echte Lernfläche, feste Regeln | Native Funktion, Quellenbindung, Retention, Betriebsstabilität |
| Age 1 | Mehr interne Routen, kleine Adapter, kurze Replayjobs, einfache geprüfte Tools | Nutzen einzelner Erweiterungen |
| Age 2 | Gezielte Inquisition, World-Lernen, prozedurales Memory, Body-only-Shadow | Ungesehene Aufgaben bestehen |
| Age 3 | Eigenständigere Replayplanung und validierte Self-Edits | Längere Stabilität und kalibrierte Unsicherheit |
| Age 4 | Relevante Initiative und selbst vorgeschlagene Lernziele | Gute Auswahl, Kostenkontrolle, erlaubter Umfang |
| Age 5 | Breite mögliche Plastizität, neue Bodies und Strukturen | Fortlaufende Parität, Retention und Ressourcenprüfung |

Die Runtime führt pro Subsystem Kompetenz, Retention, Kalibrierung, Ressourcenstabilität und Permissions. Ein globales Age-Label fasst dies lesbar zusammen. Ein neues Bildmodul darf jung sein, ohne die Sprache zurückzusetzen. Probleme mit Tools schließen deren Freigaben, nicht pauschal jedes Gedächtnis.

BOOT hält Lernflächen, Lossgewichte, Lerngeschwindigkeit, EMA, Trace-TTL, Updategrenzen und Jobbudget zunächst fest. Die tatsächlichen neuronalen Hyperparameter werden im ersten Lernexperiment bestimmt. Die mitgelieferte Scalar-Demo verwendet kleine Testwerte; diese sind keine Empfehlung für Milliardenmodelle.

Stage-Aufstieg bleibt deaktiviert, solange unabhängige Aufstiegstests fehlen. Später zählen neue und alte Aufgaben, Quellenbindung, Kalibrierung und Ressourcen über mehrere Episoden. Zustimmung des eigenen Judges reicht nicht. Rückstufung stellt gezielt engere Rechte oder frühere Parameterstände her. Nutzerregeln und Berechtigungsverwaltung sind kein frei lernbarer Teil des Age-Systems.

## 11. Memory und digitaler Aktionskreis

**Kurzfassung:** Exakte Erfahrung und komprimierte Bedeutung erfüllen verschiedene Aufgaben. Eigene Aktion, Erwartung und beobachtetes Ergebnis bleiben unterscheidbar.

![Memory und Dreaming](diagrams/05_memory_dream.png)

REAL enthält tatsächliche Beobachtungen oder Äußerungen, aber keine automatische Weltwahrheit. Eine Useraussage kann falsch sein. WELT enthält quellengebundene Zustandsannahmen, FREI Simulationen, LANG akzeptierte Kondensate, RULES explizite Regeln und PROTOCOL Betriebslogs. Ein Log beweist eine Ausführung, nicht die Wahrheit jedes Toolinhalts.

Workspace-Slots halten Claim-/Quellenreferenzen, Erzeugungsart, Unsicherheit, Zeit, Version und Ableitung. Widersprüchliche Quellen dürfen nebeneinander bestehen. Zusammenfassungen überschreiben keine Originale. Normale Korrektur ist ein neues Ereignis. Datenlöschung und Aufbewahrung bilden einen eigenen administrativen Lebenszyklus; Append-only bedeutet keine Pflicht zur ewigen Speicherung.

Causal Memory unterscheidet `OBSERVED_AFTER`, `PREDICTS`, `SUPPORTS`, `CONTRADICTS` und `SELF_GENERATED_BY`. `CAUSES` braucht stärkere Interventions-/Versuchsgrundlagen. Eine passende Vorhersage nach einer Aktion beweist allein noch keine Kausalität.

### Erstes vollständiges Lernexperiment

Ein digitaler Testkörper bietet eine begrenzte Dateiaufgabe in einem eigenen Versuchsverzeichnis. Gist bildet das grobe Ziel ab; Detail bindet Namen, Inhalt und Bedingungen. Der Workspace hält Plan und Belege. Das Action Gate wählt eine im Versuch erlaubte Operation.

Vorher entstehen Action-ID, Auftragskopie und erwarteter Folgezustand. Danach liest der Body den tatsächlich eingetretenen Zustand. Der Trace bindet beteiligte Pfade. Der Forward-Learner trainiert die Vorhersage, die Action-Policy ein getrenntes Erfolgssignal. Ein neuer ungesehener Fall prüft anschließend Verbesserung und Retention.

Der Versuch ist klein, aber vollständig rückgekoppelt. Er ersetzt nicht das weitere Sprach- und Weltlernen. Die beiliegende Scalar-Demo führt dieses Modell-/Toolexperiment noch nicht aus.

## 12. Replay, Dream, Translatoren und Body-Swap

**Kurzfassung:** Lernhilfe sinkt nur bei gehaltener Kompetenz. Freie Simulation bleibt als solche gekennzeichnet.

Replay hat vier Zwecke: episodische Wiederaufnahme, prozedurale Übung, semantische Integration und kontrafaktische Erkundung. Sleep A konsolidiert reale Erfahrung, Sleep B erzeugt begrenzte Alternativen, Sleep C führt Stabilitätswartung durch. Diese Softwarephasen sind keine genaue Abbildung menschlicher Schlafstadien.

P1/P2 arbeiten im kleinen `Z_Inq`. P1 erzeugt zielbezogene Alternativen/Störungen; P2 rekonstruiert, prüft oder holt Grounding zurück. Anfangs ist die Störfamilie fest. Sichtbare Evidenz wird nie überschrieben. Später kann P1 schwierigere plausible Varianten erzeugen, muss aber gegen bedeutungslose Störungen begrenzt werden. Gemessen wird Tasknutzen gegenüber gleichem Budget ohne Inquisition.

Future-Modes repräsentieren später unterschiedliche kohärente Zukünfte. Unvereinbare diskrete Ausgänge werden nicht einfach gemittelt. Mehrere Modes benötigen Coverage-, Diversitäts- und Kalibrierungstests, bevor ihr Konsens als Kontrollmerkmal dient.

![Translatoren und Body-Swap](diagrams/06_translator_body_swap.png)

Ein neuer Sensor braucht einen passenden Transducer. Ein Sprachmodell versteht Pixel nicht dadurch, dass man einen Übersetzer ausschaltet. Ein Heavy Teacher kann durch gepaarte Beispiele und lernende Adapter zunehmend ersetzt werden: assisted, Body-only im Shadowvergleich, dann kompetenzabhängige Auswahl. OOD-Fälle dürfen Hilfe wieder einschalten.

Body-Swap sichert Episoden, Skills, Regeln, Self/Body Schema und getestete Zustände. Der neue Body erhält Tokenizer-/Positionskarten und Read/Write-Projektionen. Transfer erfolgt mit geeigneter Distillation, Replay und kompatiblen Adaptern. Beliebige LoRA-Faktoren werden nicht zwischen fremden Architekturen kopiert. Native KV-/rekurrente Zustände werden erneuert.

Der alte Body bleibt bis zu bestandener Parität verfügbar. Sprache, Quellen, Tools, Kosten und wichtige Fähigkeiten werden geprüft. Brain-History kann erhalten bleiben; verlustlose Identität und identische innere Zustände sind keine Garantie.

## 13. Redmi-Laufzeit und Ressourcen

**Kurzfassung:** Softwareverwaltung ist gut umsetzbar. Ob die konkreten Bodies samt Hooks und Learnern gemeinsam sinnvoll laufen, ist ein frühes Messgate.

Der Referenz-Redmi besitzt laut Hersteller Snapdragon 732G, Adreno 618, LPDDR4X und UFS 2.2; mehrere RAM-/Speichervarianten existieren. [37] FP8, Adreno 740, LPDDR5X oder UFS 3.1 aus früheren anderen Geräteplänen werden nicht übertragen. Die Grafik ist kein Hardwarebeleg.

![Android-Laufzeit](diagrams/04_android_laufzeit.png)

| Posten | Rechenbeispiel | Grenze |
|---|---|---|
| Nominelle Gewichte dreier Bodies | (1,3 + 1,42 + 0,8) Mrd. mal 0,5 Byte = 1,76 GB | GERECHNET: ideale 4-Bit-Daten ohne Skalen und Laufzeitspeicher |
| Dieselben Größen in BF16 | 3,52 Mrd. mal 2 Byte = 7,04 GB | Reine Gewichte übersteigen 6 GB; konkrete Checkpoints/Anteile prüfen |
| 10 Mio. trainierbare Parameter | FP32-Master, Gradient, Adam-Momente: 16 Byte/Parameter = 160 MB | Aktivierungen, Targets, Export und Snapshot zusätzlich |
| Workspace-Default | 8 mal 256 mal 4 Byte = 8192 Byte | Nur rohe Slots; Metadaten und Rechenmodule extra |

Ein einfaches GQA-KV-Modell ist `2 * layers * tokens * kv_heads * head_dim * bytes_per_value`. Hybride/recurrente Bodies benötigen eigene Formeln. Context-Maxima aus Modellcards sind keine sinnvollen Phone-Startwerte. BOOT startet mit kurzen Testkontexten und misst den Anstieg.

Residente, pro Token aktivierte und trainierte Gewichte sind drei verschiedene Mengen. Paging spart möglicherweise RAM, aber Flashverkehr, Vorläufe und Aktivierungen bleiben. `mmap` macht kalte Experten nicht kostenlos. Fehlende Hardwarekernel können einen theoretisch sparsamen Pfad langsam machen.

### Scheduler, Commit und Cache

Foreground liest einen festen Snapshot. Der separate Learner arbeitet zunächst nur im Idle; Paralleltraining auf dem Redmi bleibt deaktiviert. Eine neue Anfrage verhindert neue Lernschritte. Ein laufender Schritt endet am nächsten sicheren Punkt, dessen Restdauer reale Wartezeit ist.

Nach lokaler und Verhaltensprüfung wird der Kandidat exportiert und an einer Ruhegrenze übernommen. Student, Target, Optimizer und Projektionen müssen zusammenpassen. Abgebrochene Exporte bleiben unveröffentlicht; die vorherige Version bleibt für Recovery verfügbar.

Cache-Identität bindet Bodyrevision, Quantisierung, Adapter, Tokenizer, Template, Positionen, Backendformat, Prefix und eingespeiste Latents/Projektoren. Auch PEFT dokumentiert inkompatible Basis-/Adaptercaches. [38] BOOT verwirft bei Änderungen den ganzen betroffenen Modellcache. Exakte Quelldaten bleiben erhalten und können neue Latents erzeugen.

Gemessen werden TTFT, Tokenrate, Ende-zu-Ende-Zeit, RSS/PSS, Reserve, Page Faults, Export-/Lernzeit, Unterbrechungsverhalten und Temperatur soweit zugänglich. Kalte und warme Wiederholungen sind nötig. Android kann Prozesse beenden; resume-fähige Jobs sind realistischer als ein garantiert immer laufender Hintergrundprozess.

Workstation-Konsolidierung bleibt optional. Sie erhält ein begrenztes Paket aus Episoden, Versionen und erlaubten Lernbereichen. Rücktransfer braucht lokalen Shadowtest. Zwei Geräte dürfen nicht gleichzeitig dieselbe aktive Zustandsdatei ändern.

## 14. Baufolge und konkrete Ausgänge

**Kurzfassung:** Modellfähigkeit und nützliche Latent-Kommunikation werden zuerst bewiesen. Danach wird der geschlossene Lernkreis erweitert.

![Baufolge](diagrams/07_baufolge.png)

| Meilenstein | Implementation | Abnahme |
|---|---|---|
| M0 Fundament | Contracts, Ledger, Eligibility, feste Age 0, Vorrang, Snapshots, Diagnose | Gelieferte modellfreie Tests |
| M1 Modellharness | Echte Loader, Tokenizer, Gewichtsprüfung, Routerreport, Ressourcenkurve | Vollständiger Load, native Referenz, Gerätebudget |
| M2 BodyPorts/Brücke | Tensorhooks, Positionskarten, Projektionen, trainierter Empfang | Neutralität, gerichteter Einfluss, Held-out-Nutzen |
| M3 Denkraum | Workspace, Relay, Judge-Heads, Cautiousness, P1/P2 | A/B tragen bei, Quellen bleiben, Halting funktioniert |
| M4 Lernkreis | Digitaler Body, Aktionskopie, World-/Forward-Lernen, lokale EMA | Spätere Prediction/Aktion besser; alte Aufgaben erhalten |
| M5 Lebenszeitbetrieb | Replay, Sleep, Commits, Age-Evidenz, Restart | Mehrtagestest, Unterbrechungen und Rückstufung |
| M6 Erweiterung | Modalitäten, Body-Slices, Meta-Controller, Body-Swap | Eigene Paritäts-/Kostenprüfung je Erweiterung |

Die Canon-Schritte B0 bis B19 werden nicht gestrichen. Android, Versionsdisziplin und Tests rücken nach vorn. Die Aufwandseinheit ist ein bestandenes Experiment, keine erfundene Zahl von Entwicklungstagen.

M1 protokolliert je Modell `inspect`, `load`, `native_forward`, `route_report`, `read_hidden`, `write_latent_probe` und `measure` getrennt. Fehlende oder unerwartete Expertgewichte stoppen die Abnahme. `strict=False` ohne Kontrolle der erwarteten Schlüssel ist keine Modellprüfung. Dies ist bei ETET besonders wichtig.

Ein bestandener Textforward öffnet den Hooktest. Ein bestandener Hooktest öffnet einen kleinen Brückenlernversuch. Sinkender Brückenloss öffnet erst nach Verhaltensvergleich den Runtimeeinsatz. So entsteht ein konkreter Codepfad ohne verborgene Erfolgsvoraussetzungen.

## 15. Evaluation

**Kurzfassung:** Jede zusätzliche Funktion zeigt ihren Nutzen gegen einen fairen Vergleich. Softwaretests und KI-Evaluation werden getrennt berichtet.

Baselines umfassen jeden Body einzeln, Judge allein, zwei Bodies ohne Brücke und einen kontrollierten Tokenkanal. Quellen, Zeit, Kontext- und Ausgabelimits sind vergleichbar. Ein größeres System gewinnt nicht allein durch mehr Rechenschritte.

| Hypothese | Versuch | Konkretes Scheitern |
|---|---|---|
| Gist/Detail ergänzen sich | Eine Hälfte / Brücke abtragen | Gleiche Qualität ohne Komponente |
| Latents tragen Information | Passende gegen vertauschte/Nullnachrichten | Kein inhaltsspezifischer Einfluss |
| Lokales Lernen hilft | Neue Fakten/Skills nach Update und Restart | Nur unverbundener Miniloss sinkt |
| Lernen schützt Altes | Neue und alte Aufgaben sequenziell | Unvertretbare Retentionsverluste |
| JEPA ist nichttrivial | Änderungen, harte Negative, Rang-/Varianztest | Kollaps oder Zukunftsleck |
| Dreaming hilft | Reales gegen gemischtes Replay | Mehr falsche Claims / schlechtere Kalibrierung |
| Age-Öffnung lohnt sich | Festes gegen gezielt geöffnetes Profil | Mehr Kosten ohne gehaltenen Nutzen |
| Mobile Vorrangregel wirkt | Anfragen während/nach Lernjobs | OOM, thermischer Einbruch, zu lange Restwartezeit |

Splits erfolgen nach Episode/Quelle; nahezu gleiche Chatfragmente landen nicht in Train und Test. Native Englischfähigkeit und vorhandenes Deutschwissen werden zuerst gemessen. Spätere deutsche Antworten sind sonst kein Nachweis neu gelernten Deutschs. Neu vermittelte Kunstfakten und kontrollierte Toolregeln machen tatsächliches Lernen besser prüfbar.

Ein Forschungsbericht nennt Code-/Checkpointhash, Daten, Seeds, Baseline, Budget, Fehlerfälle und Unsicherheit. Eine kleine Smoke-Suite dient Fehlersuche, nicht dem Nachweis allgemeiner Intelligenz. Schwellen für Promotion, Noninferiorität und Betrieb werden vor der Abnahme festgelegt und nicht nachträglich passend gemacht.

## 16. Gelieferter Code und Copy-Paste-Start

**Kurzfassung:** Ausführbarer Code für wichtige Verwaltungsinvarianten ist vorhanden. Geladene Modelle, trainierter Callosum und neuronales JEPA fehlen noch.

GETESTET auf Linux x86_64 mit Python 3.12: 20 Tests für Quellpflicht, synthetische Herkunft, aktive/verfallene Traces, Versionsbindung, Budget null, Inferenzvorrang, Validierungsablehnung, atomare SQLite-Versionierung, Cacheinvalidierung, Rollback und Neustart. Der Code verwendet nur die Standardbibliothek und ist für Termux vorbereitet. Das konkrete Redmi wurde nicht getestet.

Die Scalar-Demo verändert ausschließlich `demo.*`-Parameter anhand einer expliziten kleinen SGD-Ableitung. Ein unbeteiligter Pfad bleibt unverändert. Dies ist kein JEPA-/Sprachlernergebnis. Die Capabilityprüfung findet fehlende Deklarationen; passende Metadaten allein beweisen noch keinen Backendtest.

Nach Download von `V13_v10.zip`, in Termux:

```bash
pkg update
pkg install python unzip
termux-setup-storage
mkdir -p ~/v13-v10
unzip -n ~/storage/downloads/V13_v10.zip -d ~/v13-v10
cd ~/v13-v10/V13_v10/starter
python -m unittest discover -s tests -v
python -m v13.doctor
python -m v13.demo
```

`termux-setup-storage` öffnet die Android-Freigabe für den Downloadordner. Bei abweichendem Dateinamen nur den ZIP-Pfad anpassen. Die Demo nutzt eine temporäre Datenbank, lädt keine Modelle und startet keinen autonomen Agenten. Optional: `python -m v13.doctor > device_report.json` für den nächsten Implementationsschritt.

Die Diagnose liest Geräteklasse, ABI, Python, RAM und freien Speicherplatz. Sie misst noch keine GPU-/NPU-Leistung und keine Modelllatenz. M1 baut auf diesen Daten und einem tatsächlich kompatiblen Modellport auf.

## 17. Offene Entscheidungen

| Punkt | Benötigter Nachweis | Weg bei Scheitern |
|---|---|---|
| ETET auf Redmi | Korrekter MoE-Forward im Ressourcenbudget | Portierung oder anderer echter Detail-MoE |
| MobileMoE-QAT | Gepackte Kernel statt teurer Materialisierung | Passender Export/Runtime oder Granite-Vergleich |
| Latent-Alignment | Gerichtete nützliche Kommunikation | Anderes Brückentraining; kein Dummy-Erfolg |
| Lokale Body-Plastizität | Benannte Gewichte wirken nach Export | Adapter zuerst, tiefe Konsolidierung später |
| Anti-Collapse | Nichttriviale Repräsentation und Kompetenz | Zielansichten, Anker, Regularisierung ändern |
| Age-Schwellen | Unabhängige Kompetenzdaten | Keine automatische Promotion |
| Fast Forward / World | Verschiedene Horizonte bringen Nutzen | Zunächst getrennte Köpfe eines kleinen Moduls prüfen |
| Body-Swap | Fähigkeiten und Historie erhalten | Alten Body weiterbetreiben, Transfer verbessern |

Für das vollständige V13 fehlen insbesondere native Modellports, trainierte Cross-Modell-Projektionen, reale Body-Lerner und langfristige Gerätemessungen. Dies sind konkrete Forschungsaufträge. Der Canon beschreibt das Zielsystem; bestanden ist jeweils nur der dokumentierte Meilenstein.


## Quellen

Onlineabgleich bis 14.09.2026. Laufende Repositorien werden vor Implementationsversuchen auf konkrete Revisionen gepinnt. Autoren-/Herstellerangaben sind keine eigene Replikation. Die Forschungsanhänge benennen Grenzen des Volltextzugriffs.

[1] Yagishita et al. (2014). A critical time window for dopamine actions on the structural plasticity of dendritic spines. Science. DOI 10.1126/science.1255514. [Quelle](https://pubmed.ncbi.nlm.nih.gov/25258080/).

[2] Benna & Fusi (2016; Preprint 2015). Computational principles of synaptic memory consolidation. Nature Neuroscience. DOI 10.1038/nn.4401. [Quelle](https://www.nature.com/articles/nn.4401).

[3] Turrigiano et al. (1998). Activity-dependent scaling of quantal amplitude in neocortical neurons. Nature. DOI 10.1038/36103. [Quelle](https://pubmed.ncbi.nlm.nih.gov/9495341/).

[4] McClelland, McNaughton & O’Reilly (1995). Why there are complementary learning systems in the hippocampus and neocortex: Insights from the successes and failures of connectionist models of learning and memory. Psychological Review. DOI 10.1037/0033-295X.102.3.419. [Quelle](https://pubmed.ncbi.nlm.nih.gov/7624455/).

[5] Wilson & McNaughton (1994). Reactivation of hippocampal ensemble memories during sleep. Science. DOI 10.1126/science.8036517. [Quelle](https://pubmed.ncbi.nlm.nih.gov/8036517/).

[6] Schmitt et al. (2017). Thalamic amplification of cortical connectivity sustains attentional control. Nature. DOI 10.1038/nature22073. [Quelle](https://pubmed.ncbi.nlm.nih.gov/28467827/).

[7] Nonomura et al. (2018). Monitoring and Updating of Action Selection for Goal-Directed Behavior through the Striatal Direct and Indirect Pathways. Neuron. DOI 10.1016/j.neuron.2018.08.002. [Quelle](https://pubmed.ncbi.nlm.nih.gov/30146299/).

[8] Zhu et al. (2023). Activity map of a cortico-cerebellar loop underlying motor planning. Nature Neuroscience. DOI 10.1038/s41593-023-01453-x. [Quelle](https://www.nature.com/articles/s41593-023-01453-x).

[9] Sommer & Wurtz (2002). A pathway in primate brain for internal monitoring of movements. Science. DOI 10.1126/science.1069590. [Quelle](https://pubmed.ncbi.nlm.nih.gov/12029137/).

[10] Dorkenwald et al. (2024). Neuronal wiring diagram of an adult brain. Nature. DOI 10.1038/s41586-024-07558-y. [Quelle](https://www.nature.com/articles/s41586-024-07558-y).

[11] Lappalainen et al. (2024). Connectome-constrained networks predict neural activity across the fly visual system. Nature. DOI 10.1038/s41586-024-07939-3. [Quelle](https://pubmed.ncbi.nlm.nih.gov/39261740/).

[12] Eon Systems (10.03.2026). How the Eon Team Produced a Virtual Embodied Fly. [Quelle](https://eon.systems/updates/embodied-brain-emulation).

[13] Assran et al.: Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture. [Paper](https://arxiv.org/abs/2301.08243).

[14] Assran et al.: V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning. [Paper](https://arxiv.org/abs/2506.09985).

[15] Mur-Labadia et al.: V-JEPA 2.1: Unlocking Dense Features in Video Self-Supervised Learning. [Volltext](https://arxiv.org/html/2603.14482v3).

[16] Balestriero, LeCun: LeJEPA: Provable and Scalable Self-Supervised Learning Without the Heuristics. [Volltext](https://arxiv.org/html/2511.08544v1).

[17] Bellec et al.: A solution to the learning dilemma for recurrent networks of spiking neurons. [Paper](https://www.nature.com/articles/s41467-020-17236-y).

[18] Behrouz, Zhong, Mirrokni: Titans: Learning to Memorize at Test Time. [Paper](https://arxiv.org/abs/2501.00663).

[19] Sun et al.: Learning to (Learn at Test Time): RNNs with Expressive Hidden States. [Volltext](https://arxiv.org/html/2407.04620v1).

[20] Hafner et al.: Mastering diverse control tasks through world models. [Paper](https://www.nature.com/articles/s41586-025-08744-2).

[21] [Hao et al. Training Large Language Models to Reason in a Continuous Latent Space. 2024; Revision 23.08.2026](https://arxiv.org/html/2412.06769v4).

[22] [Zhang et al. Do Latent Tokens Think? 2025](https://arxiv.org/html/2512.21711v1).

[23] [Feng et al. FOREVER: Forgetting Curve-Inspired Memory Replay for Language Model Continual Learning. ACL 2026](https://arxiv.org/html/2601.03938v2).

[24] Hu et al.: LoRA: Low-Rank Adaptation of Large Language Models. [Paper](https://arxiv.org/abs/2106.09685).

[25] Dettmers et al.: QLoRA: Efficient Finetuning of Quantized LLMs. [Paper](https://arxiv.org/abs/2305.14314).

[26] Li et al.: BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models. [Paper](https://arxiv.org/abs/2301.12597).

[27] Wu et al.: ReFT: Representation Finetuning for Language Models. [Paper](https://arxiv.org/abs/2404.03592).

[28] [DeepSeek. DeepSeek-V4.1-Flash Model Card. September 2026](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash).

[29] [Z.ai. GLM-5.3-Flash Model Card. August 2026](https://huggingface.co/zai-org/GLM-5.3-Flash).

[30] [Meta. MobileMoE-S-QAT Model Card. August 2026; Quantization und Exporting the INT4 Checkpoint to BF16](https://huggingface.co/facebook/MobileMoE-S-QAT?hardware=p100).

[31] [RheoEcho. ETET-1.0-24E-1.8B-A1B-Preview; Language Model Details, Usage, License. 2026](https://huggingface.co/RheoEcho/ETET-1.0-24E-1.8B-A1B-Preview).

[32] [Qwen. Qwen3.5-0.8B Model Card. 2026](https://huggingface.co/Qwen/Qwen3.5-0.8B).

[33] [IBM Granite. Granite-3.1-1b-a400m-instruct config.json; laufendes Repository](https://huggingface.co/ibm-granite/granite-3.1-1b-a400m-instruct/blob/main/config.json).

[34] [ggml-org. llama.cpp Android; laufende Dokumentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).

[35] [Chen et al. MobileMoE: Scaling On-Device Mixture of Experts. 2026](https://arxiv.org/html/2605.27358v1).

[36] [Alibaba. MNN, Platform support; laufendes Repository](https://github.com/alibaba/MNN).

[37] [Xiaomi. Redmi Note 10 Pro Specs; Herstellerdatenblatt](https://www.mi.com/global/product/redmi-note-10-pro/specs/).

[38] Hugging Face PEFT: LoRA / Activated LoRA, Abschnitt „Using (and reusing) cache for generation“. [Dokumentation](https://huggingface.co/docs/peft/v0.20.0/package_reference/lora).

Projektquellen: V13_CANONICAL_BRAIN_BLUEPRINT_v9.0.md, Abschnitte 0–98; V13_NEW_CHAT_STARTER.txt; V13 – Der Weg zum lebendigen Geist.png; historischer JSON-Export AI-Consciousness-Blueprint-Theses-(Copy)-(Copy)-(Copy)-(Copy)-(Copy)-(Copy)-(Copy).json. Relevante JSON-Pfade stehen im Herkunftsaudit. Nur die tatsächlich vorhandenen Uploads wurden als gelesen behandelt.
