# V14 / INQUISITION–JEPA — Neuer integrierter Architektur-Canon
**Fassung:** 14.0-preconstruction, 2026-11-19  
**Geltung:** Architektur und Funktion des Gesamtsystems. **Nicht** die Behauptung, diese Version sei bereits lauffähig.  
**Teil 1 von 2:** Vollständige Architektur. Teil 2 ist der anschließende Forschungs-, Lizenz- und Implementierungsplan.  
**Prämisse:** Nichts aus V13 wird still gestrichen; Neuordnung und Verbesserungen ändern nicht die Benutzerziele. Der komplette ursprüngliche v10.16.1-Canon und die Drive-Roadmap bleiben als vollständige Originale im V14-Master erhalten.

## 0. Ziel, Versionslogik und unverhandelbare Regeln

V14 ist ein lokal verfügbares, entwicklungsfähiges Multi-Organ-System. Ziel ist nicht ein Chatbot mit ungewöhnlichen Modulnamen, sondern eine **tatsächlich verbundene** Architektur, in der Wahrnehmung, verschiedene Denkauflösungen, kleine Steuer- und Sprachorgane, Gedächtnis, Welt-/Selbstmodell, Handlungsfähigkeit und fortlaufende Gewichts- und Speicheranpassung unterschiedlich, aber rückgekoppelt arbeiten. Das Fernziel der selbstständigen Verbesserung ist ein Forschungsziel und **kein belegter AGI-Status**.

**Preservation Rule:** V13 v10.16.1 und jede spätere explizite Entscheidung bleiben funktionale Anforderungen. Wenn V14 etwas anders baut, muss eine Mapping-Zeile zeigen: alte ID → neue ID → gleiche Funktion → Grund der Änderung → Test/Empfänger → Rückfallpfad. Eine Funktion darf als „nicht verfügbar“, „nur Lab“, „SHADOW“, „experimentell“ oder „aktiv“ markiert werden; sie darf nicht einfach verschwinden. Doppelte Vorschläge werden zusammengeführt, ohne ihre einzigartigen Mechanismen zu verlieren. Das Original wird integral archiviert, damit niemand aus einer Neufassung still einen verkleinerten Zielumfang ableiten kann.

**Build-first:** zuerst **alle Organports und den durchgehenden realen Pfad** zusammenbauen, dann die komplexesten Lern-/Latent-/Mobile-Eigenschaften schrittweise auf echtem Verhalten härten. Vorhandene Komponenten wiederverwenden; Code eines Dritten nur unter belegter, kompatibler Lizenz. Ein frühes Experiment darf im vollständigen Graphen sichtbar sein, auch wenn die erweiterte Gewichts- oder Latent-Funktion noch nicht funktioniert. Freigaben schützen den produktiven Nutzer, sie sind kein Verbot, experimentelle Teile isoliert zu bauen.

**Evidenzklassen** sind Teil jedes Claims: ARCHITECTURE_SPEC, SCAFFOLD, SYNTHETIC_TEST, LINUX_NATIVE, ANDROID_NATIVE, ANDROID_20TURN, TRAIN_RUNNER_PROOF, RETENTION_UTILITY, APPROVED_ACTIVE. Wer lediglich Token an C3 übergeben hat, darf weder „semantisch benutzt“ noch „Latent Bridge“ behaupten. Wer einen JEPA-Loss erzeugt, darf noch nicht „kontinuierlich neues Wissen gelernt“ behaupten. Wer einen Controller konfiguriert, darf nicht „Werkzeug ausgeführt“ behaupten.

**Moral und Kontrolle:** lokale Privatsphäre als Standard, keine unauthorisierten Eingriffe in Apps/Geräte/Netzwerke, kein stilles Gewichtslernen aus provisionalen Daten, nachvollziehbare Zustimmung für riskante oder externe Aktionen, Revisionslog und Notaus. Forschung und betriebliche Funktion werden getrennt von produktiver Berechtigung.

## 1. Physischer Betrieb, Modellklassen und Skalierung

Das **Redmi Note 10 Pro / Android 13 / Termux / aarch64 / 6-GB-Klasse** bleibt das verpflichtende erste Testziel, nicht eine willkürliche Beschränkung der Architektur. Große Körper werden anfangs gemeinsam oder sequentiell über native Runner betrieben, nicht blind vierfach geladen. Existierende Versuchsmodelle: B1_DETAIL/B2_GIST auf LFM2.5-1.2B-Quantisierungen, C3_LANGUAGE auf LFM2.5-230M-Quantisierung, C2_CONTROL auf Needle-3; alle sind **austauschbare, versionsgebundene Organe**, keine ewige Identität. Langfristig sind zwei unterschiedlich spezialisierte sparse MoE-Körper (je nach realem RAM/Qualität) sowie klein gehaltene C-Steuer-/Sprachorgane geplant. Prüfe echte RSS/PSS, KV, Prefill, Tok/s, Thermik und Tokenizer vor jedem Swap. Modellkarten, GGUF-Umwandlung und Gewichts-Lizenzen sind separat zu dokumentieren.

Ein einzelner RunnerPool hält Residenz, Hot-/Warm-/Cold-Zustand, Abbruch und Wiederaufnahme, Timing/Tokenmetriken, Modellrevisionen und Grenzen. **Age ist kein Zeit- oder Rechenbudget.** Thermik/RAM/CPU/Deadline bilden ein unabhängiges Resource-Control-System. „Hallo“ darf sofort eine billige Ausgabe erhalten, während die großen Organe weiterhin beobachten können; spätere Befunde werden als Quell-/Korrektursignal protokolliert, nicht als unzulässige zweite Nutzerantwort ausgesendet. Schneller Output, echtes organisches Denken und tieferes Lernen sind gleichzeitig Architekturziele, keine Wahl zwischen zwei von ihnen.

## 2. Globaler Ereignisgraph statt starrer Chatpipeline

A0/A1/A2/A3/A4/A5 liefern wahrnehmungsgebundene Ereignisse. B1/B2 nehmen diese in verschiedenen Auflösungen auf. B3/B4 und **Enlightened Space** ermöglichen begrenzte, typisierte, direkt wie indirekt rückgekoppelte Nachrichten zwischen allen beteiligten Organen. JEF/C1–C5 bindet Ziele und entscheidet über Fokussierung, Rückfrage, Werkzeuge und eine äußere Antwort. C6/C7 geben Text, später Audio/andere Aktionen aus. Gleichzeitig wirken F1–F7 als querliegende Fabrics: Aufmerksamkeit, Unterbrechungen, Gedächtnis/Welt/Selbst, Lernen/Plastizität, Age/Rechte, Quell-/Regelbindung und Runtime/Ressourcen. Die Verbindungen dürfen später asynchron und gleichzeitig feuern; in Age-0 ist sequentielle Hardware-Ausführung keine konzeptionelle Entkopplung.

**Ein reales Event** hat EventID, SessionID, GenerationID, SourceRef mit Hash/Span/Modalität, Zeitstempel, ModelRevision(s), Producer/Consumer, Authority, aktuelle Lern- und Aktionsrechte, Zustandsversion, Abbruchstatus und Verwendungsbeleg. Pakete heißen zum Beispiel PerceptPacket, QueryPacket, OfferPacket, MessagePacket, FocusPacket, ActionProposal, OutcomePacket, ExperiencePacket, PredictionPacket, DistillationPacket und LearningCommit. Für jede Kante sind Schema, Berechtigung, „wer liest wirklich“, Rollback und Telemetrie festgelegt.

**Datenfluss** und **Lernfluss** sind verschiedene Kanten: „B1 spricht mit C3“ darf sofort stattfinden, aber „C3 lernt aus B1“ bedarf eines neuen zulässigen Experience-Events und eines tatsächlichen update-fähigen Modells. Umgekehrt kann JEPA im Hintergrund trainieren, während die sichtbare Ausgabe längst beendet ist.

## 3. A-Plane: Wahrnehmung und studentische Kompression

**A0**: verlustarmer, qualitäts-/zeitstempelgebundener Quellenadapter für Text; später Audio-Samples, Bildframes und sensorische Aktionen. **A1**: Eventgrenzen, Segmente und Zeitachsen statt ausschließlich feste Zeichenblöcke. **A2**: gefrorene Teacher/Semantikreferenz, optional im Cloud-Lab, niemals vorgetäuscht als aktives Handy-Modell. **A3**: lernbarer kleiner Projektor/Resampler, der Wahrnehmung in V14-interne Darstellungen umsetzt, mit eigenen Train-Master/Checkpoint und Teacher→Student-Transfer. **A4**: Salience/Attention-Requests für präzise erneute Wahrnehmung; kein ungenehmigter Datenzugriff. **A5**: verbindliches PerceptPacket. 

Text-only muss Ende-zu-Ende mit natürlichen Fehlerfällen laufen. Audio und Video werden über dieselben Port-Verträge ergänzt, ohne die Textorgane neu zu erfinden. Für Audio gelten Live-Partial, Sprecher-/Turngrenzen, Roh-Wellenform-Quellbindung, STT/TTS als optionale Werkzeuge, zeitliche Sicherheit und Nutzer-Einwilligung. Bild- und Tonmodelle sind physisch optional, aber **funktional im Canon vorhanden**. Das A3-Lernrecht ist separat von B1/B2-/C3-Gewichten.

## 4. B-Plane: zwei autonome Hemisphären, nicht zwei identische Prompts

**B1_DETAIL**: kurze Zeitfenster, exakte Einzelheiten, lokale Kausalität, Rechen-/Regel-/Quellenprüfung, optional höhere räumliche/temporale Auflösung. **B2_GIST**: längere Zeitfenster, semantische Gruppierung, Pläne, Zusammenhänge, Gedächtniskontext und grobe Vorhersagen. Beide können jeweils selbst denken, lernen, vorhersagen und auf externen Zustand wirken, aber mit bewusst verschiedenen Zeitskalen, Token-/State-Sichten, Trainingszielen und Output-Typen. Sie dürfen nicht durch identisches Modell + identischen Prompt zur Scheinarchitektur verkommen; ein gemeinsamer Basis-Checkpoint im ersten Labor ist ausdrücklich eine **Zwischenstufe**.

Jeder Body besitzt private Zustände, eigene Encoder/LoRA-/spätere MoE-Komponenten, eigene schnelle/slow EMA-Ziele und lokal begrenzte Fehler-/Eligibility-Lernsignale. Beide erhalten Quellen und JEF-Ziele, können sich direkt austauschen, sich widersprechen oder einen fokalen Re-entry auslösen. Observer-Passes laufen physisch parallel nur bei gemessener Stabilität; sonst sequentiell, asynchron oder sampled. **Kein Body wird zum bloßen Übersetzer oder zum zweiten Chatbot für den Nutzer.** Outputs sind strukturierte Hypothesen, Unsicherheit, Quellspannen, Vorhersagen, Gegenhypothesen und Kosten.

Der langfristige sparse-MoE-Pfad schützt zunächst Shared/Router-Werte; trainiert werden begrenzte Experten/Projektoren/LoRAs, kontrolliert mit Retention-/Expert-Load-Messungen. Alte Modelle dürfen neue Modelle schrittweise unter realer Nachweisführung anlernen; Swaps werden rollbackbar.

## 5. B3 Callosum und das systemweite Enlightened Space

**B3** verbindet B1 und B2 direkt, aber bildet **nicht** die Gesamtheit der Organ-Kommunikation. Seine Stufen: NO_MESSAGE als Ablation, SOURCE_EXACT, CONTROL, SYMBOLIC, L1-Shadow-Latent, L2-receiver-validated-Latent, L3-eingebettete native Receiver-Wirkung und nur bei nachweislichem Gewinn ACTIVE. Latents entstehen aus **echten** Senderaktivierungen und einem trainierten kleinen Encoder/Selector/Projector, ggf. mit EMA und Empfänger-Adapter, nicht aus Zufallsvektoren oder JSON-Text, der „latent“ genannt wird. Private KV/Hidden States bleiben privat; nur kalibrierte komprimierte Nachrichten wandern. OOD, Kollaps, Alignment, Rolle und Utility/Byte werden gemessen. Receiver-Revision, Modellgeneration und Approval bestimmen Wirkung.

**Enlightened Space** verbindet A, beide Bodies, B3, B4, JEF/C1/C2/C3/C4/C5, Welt, Selbst, Gedächtnis, JEPA, Werkzeug, Outcome und Konsolidation über typisierte, autorisierte Nachrichten. Es ist ein **mehrstufiger gemeinsamer Arbeitsraum**, kein drittes Sprachmodell. Jede Nachricht hat konkrete Empfänger, Haltbarkeit und Lesequittung. Ein zentraler Broker darf routingtechnisch klein bleiben, aber die Intelligenz und das Lernen liegen verteilt. Der Workspace bietet schnelle, mittlere und langsame Integrationszeiten; lokale private Zustände werden nicht automatisch veröffentlicht.

Empfänger-Evidenz wird in drei Stufen erfasst: (1) Nachricht angekommen, (2) richtige native Konsumenteneingabe / Latent-State-Injektion belegbar, (3) überprüfbare Entscheidung/Qualität verändert. Nur (3) rechtfertigt Wirkungsclaims. Hier liegt eine zentrale V14-Aufgabe, weil V13 häufig (1) mit (3) verwechselte.

## 6. C-Plane / Jeff-JEF: ein Managementsystem, kein allmächtiger Master

**C1**: kleiner beständiger Executive-State mit Zielstapel, aktiven Fragen, Zeitachsen, Generation, Aufgabe, Zustandsversion und privaten KV-/Broadcast-Verweisen. **C2_CONTROL**: sehr kleines, natives strukturiertes Steuer-/Routingorgan (Needle-Klasse), das Tools, Routen, Fokus, Gewissheit und Projektionen vorschlägt; es überschreibt weder SourceRefs noch Nutzerrechte. **C3_LANGUAGE**: kleines freies Sprach-/Reportorgan, das ausgewählte Hypothesen, bestätigte Sources und Tool-Outcomes als einzigen outward stream ausdrückt. **C4_FOCAL**: kompetitive Koalition, Unsicherheit, Inquisition P1/P2, gezielte Rückfrage in B1/B2, Unterbrechung, Arbeitsgedächtnis. **C5**: Actions/Tool/Report Broker, Abstinenz/Rückfrage/Antwort, vorhergesagte Wirkung und Rechte. **C6/C7**: Text, später Sprache, Interface und genehmigte Effektor-Aktionen.

JEF selbst soll lernen: Router, Query-Formulierung, Ressourcenverteilung, Vorhersage von erfolgreicher Reparatur, Wahl von Teacher/Memory/Tools und Nutzen der Body-Angebote. Ein kleines JEF soll nicht allein alle tiefen semantischen Aufgaben lösen müssen. C2 und C3 haben eigene Trainingsziele und erhalten optional distillierte Verlaufs-/Fehlersignale. Sie sind nicht lediglich „Zusatzkopf über B1“.

Ausgabe muss bei Teilausfällen erhalten bleiben: direkter Reflex für bekannte triviale Aufgaben, kleine C3-Native-Ausgabe, ggf. Body-Fallback, Partial/Cancel/Resume. Eine 30-Sekunden-Stille bei Hallo ist eine Funktionseinschränkung, keine zulässige Interpretation des Plans.

## 7. F1/F2: Aufmerksamkeit, Unterbrechung, Re-entry, Reflex

F1 steuert Sensorkanal, Neubesichtigung von Quellspannen, focal/global availability und begrenzte Verstärkung (Gain) je Subsystem. F2 erlaubt Salience-getriebene Interrupts, Late-Offers, Fehler-/Resource-Reflexe und intentionalen Kontextwechsel. Re-entry betrifft **gezielte** B1/B2-Fragen, nicht standardmäßig das vollständige Wiederholen aller Modell-Prefills. Lokale salience prediction und ihre beobachteten Fehler sind trainierbar. Keine Eingabe wird erfunden, wenn die UserQueue leer ist.

Ein schneller Reflex kann vorläufig helfen, aber Fehler oder Quellenkonflikte bleiben sichtbar und fließen in die weitere Koalition. Focal und Attention dürfen nicht mit Age oder thermischen Budgets verwechselt werden.

## 8. F3: Gedächtnis, Selbst, Welt und zeitliche Kontinuität

Es gibt mehrere getrennte Gedächtnisse: rohes Exact-Source-Archiv mit Widerruf, schnelles episodisches Fallgedächtnis, semantischen Graphen, längerfristige Gist-/B2-Zustände, Handlungs-/Ergebnisprotokolle, Skills und prozedurale Muster, Weltmodell-Transitions, Self-State/Capability-Selbsteinschätzung, private Executive-Fortsetzung und nichtidentische Self-Beliefs. Sie teilen IDs, **nicht** automatisch Wahrheitsstatus oder Lernberechtigung. Erinnerung bedeutet nachweisbar **wieder lesen und im Ergebnis benutzen**, nicht nur Datenbankeintrag.

Ein Weltmodell prognostiziert die Folgen eigener Aktionen und Differenzen zu gemessenen Ergebnissen; ein Selbstmodell speichert Beschränkungen, Ressourcen, eigene frühere Irrtümer, Kalibrierung und Fähigkeiten. „Selbstbewusstsein“ ist keine notwendige Statusbehauptung. Corollary/Efference-Copy wird **vor** externer Aktion geschrieben, danach wird Outcome gebunden und Prediction Error rückgeführt. Semantische und parametrische Lernpfade können diesen Fehler für getrennte Zielräume verwenden.

Second-attempt utility ist der zentrale Test: gleiches Problem später besser lösen; kontrollierte Paraphrase, verwandte aber neue Aufgabe, negative Übertragung, Abstinenz und Restart. Archivierung kann exakte Quellen günstiger machen, aber kein heimliches dauerhaftes Halten widerrufener privater Inhalte. **Memory Graph / raw path / unstructured perception** bleiben im Canon, auch wenn der Redmi Age-0-Lab-Pfad zunächst textuell ist.

## 9. F4: sieben voneinander unabhängige und kooperierende Lernarten

V14 besitzt mindestens diese real unterscheidbaren Lernwege:

1. **Fast Episodic / Retrieval / Skill**: Datenbank- und Indexzustände lernen aus zugelassenen Erfahrungen; kein Weight-Update erforderlich.
2. **A3 Perceptual JEPA/Teacher Distillation**: gefrorener Teacher → kleiner Student/Projector mit realer Latent Prediction, Stop-Gradient, Stabilitätskontrolle.
3. **B1/B2 Body JEPA**: Student/View-Predictor, EMA-/frozen target, Fehler×Eligibility×Modulation, trainierbarer Adapter oder spätere selektive Gewichte.
4. **World/Self JEPA / Transition Model**: vorangehender State + Aktion → zukünftiges Latent/Outcome; lokale, episodische und lange Vorhersagen, identitäts-/provenance-getrennt.
5. **JEF/C2/C3 Policies**: Routing, Query-, Wake-, Action-Head, Sprach-Output-Kalibrierung und Quellenverwendung. Eigene Zustände und Objectives.
6. **Replay, Sleep, Dream**: offline auf echten Ereignissen, gezielter Repetition und Quellregel; Deduplikation, rare-event, uncertainty und Gegenbeispiele; Dream-Counterfactual nicht als echte Beobachtung ausgeben.
7. **On-policy Self-Distillation + Teacher/Student Co-Learning**: optionaler neuer Pfad mit zweitem Konsumenten für LLM-Tokenverteilungen, Lehrerhinweise und kontrollierte Weight-Delta-Prediction (siehe §10).

**Vereinte Lehrsteuerung** bedeutet nicht „eine einzige JEPA lernt alles“. Locality-/Anchor-/Metaplasticity-/Homeostasis-/Drift-/OOD-/Anti-Collapse-Regeln wirken je Head unterschiedlich. Updates werden nach Eligibility, realem Prediction Error, Quellenvertrauen, Zielmodulator und Freigaberechten begrenzt. Sprachliche Belohnung oder freundliche Texte ersetzen kein beobachtetes Outcome. Training benutzt **echte trainierbare Mastergewichte/Adapter**, niemals einen GGUF-Readonly-Pfad als Scheinparameter. Jedes Lernexperiment hat Trainingsrevision, Datengrenzen, Optimizer- und RNG-Checkpoint, Zielmodell, EMA, Rollback und Baseline.

## 10. Neue Distillation×JEPA-Schleife: Mini-Distillation als Lernrichtungsprüfer

**Forschungsstatus:** eigenständige V14-Hypothese auf Basis von 2026er On-Policy-Self-Distillation, SDFT, JOLT, SeOPD, representation-level prediction und JEPA. Nicht als fertiges Paper-Ergebnis oder bestehende Funktion ausgeben.

Bei jeder *zugelassenen* Erfahrung X erzeugt das aktive System eine Vorhersage/Antwort und protokolliert den organischen State. Ein kontextuell informierter Teacher (wahlweise: derselbe Modell-Checkpoint mit überprüfter zusätzlicher Lösung/Outcome, ein voriger stabiler Checkpoint, ein kleiner unabhängiger Teacher, eine verifizierte Quelle, menschlich bestätigte Korrektur, B1/B2-komplementäre View) prognostiziert eine wünschenswerte Ausgabe oder Repräsentation. Ein lokaler **Learning-Direction Head** schätzt, welche Zielräume/Adapter-Subspaces/Expert-Regionen vom nächsten Update profitieren könnten. Der Teacher darf keine verbotenen oder unbestätigten Inhalte zu „Wahrheiten“ erklären.

Drei getrennte Prognosen:
- **PREDICT_STATE**: JEPA Student z_t und Aktion/Quellkontext → Ziel-Latent z_{t+1}^{target}, mit Stop-Gradient/EMA auf dem Target.
- **PREDICT_DELTA**: kleiner Meta-Head nimmt Fehlervector, Teacher-Student-Differenz, Eligibility, Retention-Kontext, OOD und Modulatoren → *Vorschlag* einer begrenzten Update-Maske/-Skala für trainierbare LoRA/Projector/Policy-Parameter. Kein unkontrolliertes direktes Editieren von Base-GGUF.
- **PREDICT_UTILITY**: zweiter Head sagt voraus, wie stark die vorgeschlagene Änderung auf einem unabhängigen kleinen Holdout/Retention-Set helfen oder schaden wird. Nach einem echten Shadow-Update wird die prognostizierte Nutzenänderung mit der gemessenen verglichen und auch dieser Head lernt.

Die Lernberechnung kann als getrennt gewichtetes Objektiv aus JEPA latent prediction, (on-policy) Teacher–Student Divergenz, Outcome-/Reward-Term, Anchors/Retention und Meta-Prediction bestehen. **Wichtig:** „Distillation statt Backprop“ ist technisch nicht generell korrekt: Distillation spezifiziert ein **Trainingssignal**, keine alternative physikalische Regel, wie Modellgewichte geändert werden. Der kleine Predictor braucht noch einen Optimizer, lokale Updates oder einen getrennt validierten credit-assignment-Mechanismus; B-JEPA ebenso. Eligibility×Error×Modulation kann lokale Lernsignale lenken, ersetzt ohne Beleg aber keinen korrekten Gradienten für beliebige Deep Layers.

Die V14-Experimente vergleichen mindestens: JEPA-only, Distillation-only, JEPA+Distillation, zusätzlich Delta-Head, zusätzlich Nutzen-Prädiktor, no-teacher, random-teacher, teacher-frozen vs co-trained, provenance-off (nur im isolierten Negativkontroll-Test), replay-on/off, EMA frozen-vs-live, sowie die vorliegende V13-Baseline. Ergebnisvariablen: held-out task score, second-attempt, generalisation, forgetting, calibration, B1/B2 role separation, bytes/PSS, energy, first-token latency, OOD failures, trainability/restart, causal receiver impact. Ein Head darf aktiv erst nach echtem Nutzen, Retention und Widerruf/Rollback werden; **die Implementierung im Lab soll trotzdem sofort erfolgen können.**

**Stepping-Stone-Learning (STONE, 2026-11-13) als zusätzliche Lehrdaten-Auswahl:** Bei einer schwierigen selbst erzeugten Frage dürfen Shepard/JEF/B1/B2 mehrere **einfachere verknüpfte Aufgaben** generieren, per wiederholtem eigenen Lösungsversuch Konsistenz prüfen und diese verifizierten lokalen Teilaufgaben als *privilegierte Teacher-Hinweise* an die Mini-Distillation übergeben. Ohne externe überprüfte Ergebnisse ist Konsistenz **keine Wahrheit**. Der JEPA-Predictor sagt weiterhin latente Zustände voraus und PREDICT_DELTA/PREDICT_UTILITY bewertet eventuelle Gewichtsänderungen; STONE ersetzt weder diese Köpfe noch Replay/Outcomes. Forschungspaper: [STONE arXiv:2611.18916](https://arxiv.org/abs/2611.18916). Originalcode-Lizenz nicht nachgewiesen; bis dahin nur eigenständige technische Adaption.

**Unterscheide Active Learning (welche Daten fragen/auswählen) von Online Learning (fortlaufend aus Daten updaten).** Beide gehören dazu: Shepard/Curiosity/Value-of-Information wählt lehrreiche Fälle, die Learner-Pfade konsumieren genehmigte Erfahrungen; nicht jeder neugierige Gedanke wird automatisch Trainingsdaten.

## 11. Lernzyklus im zeitlichen Detail

T0 Quelle ingress und Rechte; T1 A5 mit Hash/Segment; T2 JEPA-/Welt-/JEF-Predictions **vor** Aktion; T3 B1/B2/KV/private States und typisierte Enlightened-Space-Offers; T4 Focal/Query/Action; T5 erster sichtbarer Output; T6 externe, wenn erlaubte, Wirkung; T7 Beobachtung, Verifikation und User-Feedback; T8 atomisch committe Outcome+Experience+PredictionDiff+Lineage; T9 wähle mit Curiosity/Value/Retention Kandidaten; T10 isolierte Mini-Batches für Fast-Memory, lokale JEPA, Body/World/Policy und optional On-policy Self-Distillation; T11 Nutzen-/Holdout-Check plus PREDICT_UTILITY-Fehlermessung; T12 sichere trainierbare Deltas, EMA/Optimizer/RNG und atomischen Checkpoint; T13 nach Rechten genehmigte Aktivierung, sonst Shadow; T14 Abbruch, Rollback, Replay, Schlaf; T15 nach späterem Encounter tatsächliche Second-Attempt-Verbesserung messen.

Die Lernrechte sind granular: observe ≠ propose ≠ train-shadow ≠ apply-to-model ≠ publish/active ≠ act-external ≠ self-edit. Die Lernwarteschlange blockiert nie user-visible output. Power-/Thermal-Ressourcen und ausbleibende Nutzerfragen ändern nur Scheduling, nicht den Status der strukturellen Lernrechte. Falls trainierbarer Native-Runtime-Pfad fehlt, funktioniert die Gesamtarchitektur weiter mit den übrigen Lernarten, aber der fehlende Pfad bleibt sichtbar.

## 12. F5 Age / Laborreife / Benutzergenehmigung

**Official Age** repräsentiert dokumentierte erreichte Entwicklung; **Lab/Test Age** gibt dem Nutzer die Möglichkeit, Rechte/Werkzeuge/Lernpfade experimentell bis höherer Stufe zu testen, ohne eine offizielle Beförderung oder eine automatische Freigabe fremder Aktionen vorzutäuschen. Age 0 ist der Startzustand und kann RECORD_ONLY, einzelne manuelle SHADOW-Experimente, ausdrücklich genehmigte Updates und Output erlauben, jeweils nach Rechte-/Datenquelle. X10 ist ein Labor-Auswahlwert, kein Ersatz für die Reifeprüfung und kein „10× Token-Zeit“. Ein Modell kann getauscht werden, ohne alle Memories oder Age zurückzusetzen; altes→neues Handover benötigt separate Genehmigung/Tests.

Alle Stufen haben Freeze/Stop/Reset, vorhersagbare Hysterese, erklärbare Caps, unabhängige per-Head Rechte, Consent Receipts, Not-Aus, Widerruf und kontrollierte Rücknahme von freigegebenen Deltas. Entwicklungsrechte sind nicht das Gleiche wie Memory Authority, Tool Authority und öffentlich sichtbarer Reifegrad. Entwicklung darf im SHADOW weiterlaufen, ohne den Nutzer zu täuschen.

## 13. F6 Privacy / Provenance / Wahrheit und Gewissenhaftigkeit

Quellen sind durch ID, Hash, Bereich, Zeitpunkt und Lösch-/Gültigkeitsstatus gebunden. Exact-Quote-Transport beweist keine semantische Wahrheit; Model-Hypothesen bleiben Hypothesen. Messbare reale Outcomes, verifizierte Nutzerrückmeldung und bestätigte Quellen sind getrennte Evidenztypen. Kein Modell darf untrustworthy Source-Strings zu Steuerbefehlen hochstufen. Bei einem widerrufenen SourceRef müssen abhängige Caches, Trainingsanwärter, Derived Memories und aktivierbare Deltas identifizierbar sein; bei irreversiblen Weight-Änderungen wird die Grenze offen dokumentiert und eine Rücknahme/Restore bevorzugt.

V14 ist lokal und grundsätzlich privat. Remote-Bridge nur opt-in, Auth-Schlüssel niemals in öffentlichem Git; keine raw Chats/Audio/Telefonlogs in PRs. Public Repo enthält Design, Code, synthetische Tests und redigierte Messübersichten; private Daten verbleiben privat. Drittquellen unterliegen Lizenz/Datenschutz/Robots/Terms separat. Moralische Beurteilung und Sicherheitskontrolle sind begründete Rechte- und Wirkungsprüfung, nicht automatisch „jede ungewöhnliche Meinung blockieren“.

## 14. F7 Runtime, Cache, Geschwindigkeit und Robustheit

Ein eigener Layer verwaltet ModelSlots/Runner, KV/State Cache, Kompression/Residenz, Token/Graph-Kosten, TaskQueue, begrenzte asynchrone Lernjobs, Akku/Hitze, Timeout-Abbruch, PartialOutput und Source-Snapshot. Eingänge arbeiten bounded; ein inaktiver großer Body darf den C3-Kurzoutput nicht töten. Ein schneller einfacher Turn **muss als echter End-to-End-Test** gemessen werden. Wiederverwendung von präfixabhängigem Cache bei hybriden/rekurrenten LFM-Modellen muss mit der **genauen** Runner-Version überprüft werden. Kleines native C3 vs kleines alternatives Modell im identischen Kontext testen; nach Funktionsbeleg nicht immer neu routen.

Linux-CI, Android/Termux, APK/WebUI, Hardware-ABI und wirklich laufende GGUF sind getrennte Evidenz. Ein Installer hat atomische Stage/Activate/Rollback, konfliktfreie Snapshot-Migration, intakte Datenbank und sichtbaren Status. Dashboard-Buttons dürfen nach normaler Aktualisierung funktionieren, kein Refresh-Trick als Betriebsbedingung. Auto-Update darf nicht die Genehmigung für Lern-/Werkzeugrechte implizieren.

## 15. Selbstoptimierung, Architekturänderung und RSI-Forschung

Self-edit ist langfristiger Bestandteil, **nicht** mit dem aktuellen Lab-Distillation-Head gleichzusetzen. Der Systems-Improver kann eigene Fehlermuster/Grenzen sammeln, Alternativen aus bestehendem Open-Source-Code finden, eine überprüfbare Änderung mit Quellen/Lizenz/Sicherheitsplan vorschlagen, isoliert Tests ausführen, Effizienz/Qualität vergleichen, anschließend eine kontrollierte Freigabe anfordern und bei Verschlechterung zurückrollen. Code-/Weight-Edits sind getrennte Rechte. Kleine Modelle können andere *kleine trainierbare Heads* vorschlagen oder verändern, aber nur unter Source-/Holdout-/Identity-Bindung; eigene Kontrolle allein ist keine objektive Qualitätsprüfung.

Architekturverbesserung kann Ports, Datenschemata, Tools, Modelle, Scheduler, Projektoren, Router, Dimensions-/LoRA-Größen und Fusionmechanismen betreffen. Jede Maßnahme behält eine Provenance/Run-Manifest/ablation/second-attempt-Grenze. Kein ungeprüfter automatischer Push auf die Hauptrelease-Branch.

## 16. Bedienelemente und alltägliche Nutzung

Eine lokale Benutzeroberfläche (Termux + WebUI, später APK) erlaubt eine normale Unterhaltung, Bild-/Audio-Upload, Quellen-/Memory-Einsicht, Modellstatus, native token/prefill/first-output timing, Auswahl von Lab-Age, Lernen/Shadow/Official-Mode, Werkzeugfreigaben, Layer-/Organ-Status, Warteschlange, Hintergrundexperimente, Schlaf, Cancel/Pause/Resume/Unload/Shutdown, klare Fehler und Rollback. Ein „:doctor“ beschreibt echte native Modelle/Benchmarks/Weights, keine unverbindlichen Pakete. Die User-Ausgabe bleibt ein zusammenhängender Stream; intern dürfen mehrere Organe gleichzeitig rechnen.

Beispiel-Pflicht-Session: „hi“ (sofort nutzbar), genaue Quellfrage, langer Vergleich, Korrektur mit Gedächtnis, zweite Antwort nach Restart, B1/B2 komplementärer Fall, Tool-Vorschlag + Zustimmung, World/JEPA-Shadow-Lernzyklus, analoger Next-Encounter und echter Low-RAM-Fallback. Für jeden Fall zeigt die Diagnose, welche Organe **tatsächlich** gelaufen sind.

## 17. Modulare Verträge und Mindest-API

Jedes Organ implementiert ein OwnerPort: identity/revision, accepts(event,rights), observe(event,context), produce_packet(), consume_packet(), predict(), propose_learning(), apply_shadow(), checkpoint(), restore(), revoke(), unload() und metrics(). Nicht jede Methode muss in einer Phase aktiv sein; fehlende Methoden liefern ehrlich typisierte UNAVAILABLE mit Grund. Datenschemata in maschinenlesbarer Registry, keine heimlichen Python-Dict-Vertragsänderungen.

Gemeinsame schmale Typen: SourceRef; Percept; Hypothesis/Offer; Message/WorkspaceView; Goal/Plan/ActionProposal; Outcome; MemoryRecord/WorldTransition/SelfState; TeacherView; PredictedLatent; UpdateProposal; TrainReceipt; RetentionVerdict; ActivationReceipt. Native Runner sind Ports, kein Ersatz für die Organe. Training läuft im lokalen **Lab-Worker**, nicht in unvorhersehbaren Nebeneffekten eines Output-Generators. Kein Produktivpfad darf nur ein Mock bleiben.

## 18. Reihenfolge: erst verbundenes Ganzes, dann Verbesserungen

**Integration A:** alle bestehenden V13-Dateien / alte Patches erfassen, Source-Graph und Live-Consumer bestimmen, fehlende Consumer markieren. **Integration B:** einen realen Turn durch A→B1/B2→B3/B4/Enlightened Space→JEF/C2/C3→C5→Output, mit echten Laufzeitmodellen, echten SourceRefs und Trace. **Integration C:** persistent memory, self, world, Rückmeldungen, Outcome und Second-Attempt. **Integration D:** JEPA/A3/Body/World/Predictor/Replay/Distillation im Lab mit echten Deltas und Restart (auch wenn einzelne Lernpfade nur Shadow sind). **Integration E:** Tools, Selbstoptimierungs-Planer und Age-Rechte. **Integration F:** Audio/Vision, native Sparse/MoE, Distillation×JEPA-Head und optimiertes Scheduling. **Integration G:** vollflächige Android-Nutzung und langfristige Testreihen. Mehrere unabhängige Agenten dürfen A–F parallel vorantreiben; nur das Release/Merge und Shared Contracts werden koordiniert.

Vorhandenen Code und fertige Drittanbieterbibliotheken priorisieren. Nicht jedes Problem einzeln neu erfinden. Tests unmittelbar nach einer neuen Verbindung; keine wochenlange Schleife an einem synthetischen Test statt Fortschritt am funktionalen Graphen. Die vollständige technische Quellen-/Lizenz-/Meilensteinmatrix steht in Teil 2.

## 19. Kompatibilität mit **allen** V13-IDs und bisherigen Arbeitspaketen

Dieser neue lesbare Aufbau **ersetzt nicht** die v10.15/v10.16 IH-H0–H36, W0–W10, Layer 1–9, L1–L8, 0P/0R Path/KnobSpec, G-/R-/H-/Z-/AG-Pflichten und die alten WP-A..V/AG/N/T/U/S-Serien. Sie werden als direkt eingebettete, vollständig erhaltene Quellteile in der Masterdatei geliefert. V14-Änderungen müssen dort auf die vorherigen IDs zurückverweisen; unbekannte Aliasnamen bleiben gemäß alter Alias-Firewall, nicht als neues paralleles Design. Das Gesamtsystem umfasst auch die weniger auffälligen Pflichten: C5/C6-Finalizer, Status/Logging, Abbruch, Datenschutz, neue Sensorik, Schemaregistry, Build/Lint, Modulation, temporale Signale, Re-entry, Prediction-Ablation, Quelle→Gewicht-Lineage, dynamische Gist-Compression und lokale Echtzeitbedienung.

Die spätere GitHub-Arbeit vom Oktober/November (einschließlich der vielen Candidate-Module, nativen C3-/B3-Piloten, QA-Patches und der 2026-11-19 Build-first-Korrektur) ist **nicht** durch bloßen Merge in dieses Dokument „fertig“. Ihre Existenz, getestete Effekte, offene Implementierung und Reuse-Entscheidung sind im Forschungs- und Arbeitsplan separat zu erfassen. Der aktuelle V13-Release-Branch bleibt bis zur ersten funktionalen V14-Probe unangetastet.

## 20. Abnahmekriterien, ohne künstliche Zielverkleinerung

V14 hat ein vollständiges Architektur-Gerüst, wenn jeder im ursprünglichen Canon definierte Knoten und jede Kante in der Registry mit Source/Target, Status, konkretem Port/Consumer, Owner, Rechteplan, Telemetrie und nächstem Schritt erscheint. V14 ist **funktional text-only**, wenn alle Hauptorgane in einer realen Nutzersitzung ihren erwarteten Auftrag ausführen, ihre Outputs in den richtigen Konsumenten ankommen und das System trotz einzelner Shadow-Pfade antwortet. **JEPA Weight Learning** ist erst belegt, wenn echte trainierbare Gewichte/Adapter sich ändern, Holdout/Retention gemessen, Revisions-/Checkpoint-IDs gespeichert und ein verwertbarer veränderter Consumer nach Neustart nachgewiesen ist. **Full Canon** ist erst vollständig, wenn die zusätzlich späteren Modalitäten, selbstständige Entwicklungspfade und alle vorgeschriebenen Experimente abgeschlossen sind. Diese drei Zustände werden nicht vermischt.

**Nächster Teil:** Forschungs-, Upstream-Reuse-, Lizenz- und konkreter Implementierungsplan – direkt folgend im V14-Master.
