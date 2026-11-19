# V14 / INQUISITION–JEPA — Vollständiger Master-Blueprint + Research + Preservation

**Erstellt:** 2026-11-19 | **Status:** Entwicklungs-Canon, NICHT Gerätelauf oder Lern-Erfolgsbeweis

**Lesereihenfolge:** 1. Die neue, umfassende V14-Architektur. 2. Direkt darunter der Forschungs-, Lizenz- und konkrete Implementierungsplan. 3. Danach die **unverändert integrierten** historischen V13-Full-Canon- und Drive-Dokumente einschließlich 49 kleiner Zusatznotizen. Keine bisher bekannte Pflicht wird still gelöscht. Abweichungen gegenüber den älteren Quelltexten sind als neue explizite Nutzerentscheidungen markiert. Das über 418 MB große historische private ZIP mit Rohartefakten wurde **nicht** öffentlich kopiert und **nicht** erneut vollständig analysiert. Ältere GitHub-Branches/PRs bleiben als unabhängige Historie erhalten.

**Dateien für Navigation/PR-Diffs:** `V14_01_ARCHITEKTUR.md`, `V14_02_FORSCHUNG_LIZENZEN_UMSETZUNGSPLAN.md` und die drei `archive/`-Quellen unter `v14/`. Dieser Master bettet sie alle integral ein. Keine native Gewichts- oder Bibliothekskopie erfolgt allein durch diese Planung.

**Quellrevisionen (Git blobs):**
- `v14/V14_01_ARCHITEKTUR.md` — `ea190d598c9fd2ca59480ca0db76c700d990bf44` (31697 Zeichen)
- `v14/V14_02_FORSCHUNG_LIZENZEN_UMSETZUNGSPLAN.md` — `ee6054bcd6e31656d226ea5c99445d7f366b8e04` (30120 Zeichen)
- `v14/archive/V13_CANON_v10.16.1_INTEGRAL_20261119.md` — `218464b12a2d27d92524c751922fa8e1c3fb0ea7` (417377 Zeichen)
- `v14/archive/V13_DRIVE_ROADMAPS_SICHTUNG_UEBERGABE_INTEGRAL.md` — `2715173a52ac56851b319e1b2df3f33e4084ed4f` (148343 Zeichen)
- `v14/archive/V13_DRIVE_SMALL_PATCH_NOTES_20261013_22.md` — `42e1def5bf23d36cd175e0022e2b98f1bf43cc0d` (71324 Zeichen)

---

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


---

# TEIL 2 — FORSCHUNGS- UND IMPLEMENTIERUNGSPLAN

# V14 — Forschungs-, Lizenz-, Integrations- und Arbeitsplan
**Teil 2 des V14-Masters; Stand 2026-11-19.**  
**Status:** fachliche Erstprüfung auf Basis öffentlicher Primärquellen und der vorhandenen V13-Quellen. Die vorgemerkten Bibliotheken sind **Kandidaten**, noch nicht automatisch in V14 eingebaut. Dieses Dokument erlaubt keine Behauptungen über neue native Redmi-Messergebnisse.

## R0. Zweck und Prinzip

Das Forschungsziel ist nicht, möglichst viele neue Patches zu finden. Es ist, den gesamten V14-Canon mit der **geringstmöglichen Menge neu zu erfindender Technik** vollständig und sinnvoll zu bauen. Alle bestehenden V13-Organe und Arbeitspakete werden gesichtet; jedes neue Konzept erhält entweder (1) Wiederverwendung existierenden V13-Codes, (2) legale Übernahme gut gepflegter Drittbibliothek, (3) konzeptionelle Adaption wissenschaftlicher Arbeit ohne Quelltextkopie oder (4) präzise, selbst zu entwickelnde fehlende Verbindung. Es gibt niemals einen fünften Status „stillschweigend vergessen“.

Forschung ist ein **Baustein des Build-Workflows**, nicht seine Alternative. Ein kleiner externer Prototyp ist nur dann nützlich, wenn er einen echten V14-Consumer erreicht. Gemessene Laufzeit/Qualität und Quellenrecht werden getrennt ausgewiesen.

## R1. Quellumfang und Priorität

**Maßgeblich, integral erhalten:** V13 v10.16.1 Canon (13.773 Zeilen, aus GitHub \`v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md\`); Drive \`ROADMAP_Teil1von3.md\`, \`Teil2von3.md\`, \`Teil3von3.md\` zusammen, \`SICHTUNG.md\`, \`UEBERGABE_FUER_ANDERE_KI.md\`; letzte Entscheidungen und AGENTS.md; V13 GitHub Pull Requests/Issues und Codehistorie. Insbesondere alle W/IH-H, 0P/0R, Layer 1–9, A/B/C, F1–F7, G1–G..., AG..., R..., BP/B3/JEPA und WP-A...U/S/T/KAL/N-Pflichten. Die physischen Experimente und Modell-Quellen sind als historisch/aktuell getrennt zu bewerten.

**Prioritätsregel:** neuere ausdrückliche Nutzerentscheidungen schlagen ältere, *nur wenn sie wirklich widersprechen*. Sonst alte Ziele additiv erhalten. Neue Funktionen wie Mini-Self-Distillation, Weight-Delta-Prognose und mehrschichtige Selbstoptimierung ergänzen JEPA, ersetzen nicht das übrige System. Das Original bleibt als Integral-Appendix für line-by-line Gegenprüfung.

**Privacy:** Die 418-MB-Drive-Gesamtarchiv-ZIP wurde erkannt und als historische Quelle lokal referenziert. Die \`SICHTUNG.md\` dokumentiert deren frühere Auswertung (164 Einträge). Ihre komplette ZIP wurde für diese V14-Fassung **nicht** selbst inhaltlich vollständig neu extrahiert; deshalb keine erfundene Vollarchivprüfung. Der zusätzliche Canon-Appendix plus Drive-Hauptroadmap schützt wichtige Anforderungen, private Rohtraces/Schlüssel dürfen nicht ins öffentliche GitHub kopiert werden. Für mögliche fehlende ältere Einzelideen bleibt ein Historical-Diff-Audit offen.

## R2. Lizenzgrundsatz – rechts- und moralverträgliche Übernahme

**MIT, BSD-2/3, Apache-2.0** eignen sich grundsätzlich für V14-Reuse auch bei späterer Weitergabe, *wenn* Copyright, Lizenzkopie, NOTICE (bei Apache) und Abhängigkeiten beachtet werden. Die Lizenz des GitHub-Repos ist **nicht** die Lizenz seiner heruntergeladenen Modellgewichte oder Datasets. Ein „auf GitHub öffentlich“ ist keine pauschale Code-Lizenz. Dateien ohne nachprüfbare Lizenz oder mit inkompatiblen Bedingungen werden **nur als Konzept gelesen**, nicht in den Repositorycode kopiert. Copyleft-Komponenten benötigen gesonderte Architektur- und Weitergabeprüfung; Lizenzverpflichtungen nicht durch Verschleierung in GitHub umgehen. Im Zweifel neu implementieren statt kopieren.

Für jede externe Integration eine Maschinenlesbare \`THIRD_PARTY_COMPONENTS.json\`-Zeile mit Upstream-URL, exaktem Commit/SHA, SPDX-ID, file-level Exceptions, Modell-/Gewichtsbedingungen, transitive Licenses, Version, Architektur/ABI, RAM, native C++/Python-Bindings, Sicherheitsstatus, Übernahmeart, Notices, Tests, Rollback und Owner. \`COPY\` nur bei Lizenzbefund; \`INSPIRED\` darf keine wörtliche/strukturelle Copyright-Übernahme maskieren. Öffentliche Quellen und eigene Ports getrennt halten.

## R3. Bereits gefundene Upstream-Bausteine

| Komponente, Originalquelle | Lizenz-Befund | V14-Entscheidung | Grenzen / nächste Prüfung |
| --- | --- | --- | --- |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) und [LICENSE](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) | MIT, Third-party-Licenses im Repo | **Beibehalten/Native Integration**: GGUF, LFM/C3/B1/B2 serving, streaming, KV, quantisierte Runner | Exakten Stand, LFM2.5-Rekurrenz/Cache, aarch64-Build, QAD/GGUF, API, PSS und Testkorpus prüfen. Kein eigener Inferenzkern. |
| [PyTorch ExecuTorch](https://github.com/pytorch/executorch) [LICENSE](https://github.com/pytorch/executorch/blob/main/LICENSE) | BSD (projektbezogen; transitive prüfen) | **Optional Pilot** für Mini-A3, Distillation/JEPA Predictor oder on-device projizierbaren Head | Exportpfad/Op-Abdeckung, Arm64, Speicher, JNI/Termux vs C++, Vergleich gegen NumPy/C++-Baseline. Kein LLM-Runner-Ersatz. |
| [River](https://github.com/online-ml/river) [LICENSE](https://github.com/online-ml/river/blob/main/LICENSE) | BSD-3-Clause | **Reuse/algorithmische Referenz** für Online-Signal, Drift, Streaming-Auswertung | Native Wheels auf Termux unsicher; reine Minimalalgorithmen zuerst, ggf. eigens portieren, Lizenz beachten. |
| [Avalanche](https://github.com/ContinualAI/avalanche) [LICENSE](https://github.com/ContinualAI/avalanche/blob/master/LICENSE) | Repository-LICENSE vor Copy erneut prüfen; in projektbezogenen Referenzen üblicherweise MIT/BSD-artige Research-Lizenz, keine ungeprüfte Behauptung | **Offline/Cloud-Baseline** für Continual Learning, Replay, Retention | Schweres PyTorch; nicht blind auf 6 GB Redmi installieren. |
| [facebookresearch/vjepa2](https://github.com/facebookresearch/vjepa2) [LICENSE](https://github.com/facebookresearch/vjepa2/blob/main/LICENSE) | Repo MIT; Modelle/Daten/Einzeldateien separat | **Forschungsreferenz**, nicht native V14-Gewichtkopie | Video-fokussiert, große Backbones, lässt sich nicht direkt als Text-Body-Lerner einhängen. |
| [Hugging Face TRL](https://github.com/huggingface/trl) [LICENSE](https://github.com/huggingface/trl/blob/main/LICENSE) und [DistillationTrainer](https://huggingface.co/docs/trl/main/en/distillation_trainer) | Apache-2.0 | **Favorit für Offline-SDFT/OPD-Referenzexperiment**, verteiltes Training mit kleinen Adaptern, später Head in V14 exportieren | Python/PyTorch/vLLM zu schwer für Standard-Redmi. Lehrsignal und Adapter-Delta müssen auf dem Handy getrennt messbar sein. |
| [TRL SDPO](https://huggingface.co/docs/trl/main/en/sdpo_trainer) | TRL Apache-2.0, experimentelle API | **Probieren als Feedback→Teacher→Student-Referenz** neben JOLT | Unbedingt aktuelle API und Revisionspin; keine eingebauten C3-Weights als Scheintrainingsweg. |
| [idanshen/Self-Distillation](https://github.com/idanshen/Self-Distillation) | Lizenz in dieser Sitzung **nicht zweifelsfrei nachgewiesen** | **Konzept/Referenz prüfen**, noch nicht kopieren | Vor COPY auf Datei- und Root-LICENSE schauen; ggf. den durch TRL lizenzierten Trainer verwenden. |
| [verl OPD](https://verl.readthedocs.io/en/latest/algo/opd.html) / [verl](https://github.com/volcengine/verl) | Lizenz am exakten Commit noch zu prüfen | **Cloud-Vergleich**, keine Mobilabhängigkeit | Distributed Training/Teacher Server; aktuell unnötig für Start-Smartphone. |
| [rllm OPSD](https://github.com/rllm-org/rllm) / [OPD-Codeübersicht](https://github.com/china10s/awesome-opd) | Erst Lizenz prüfen | **Codefinder**, Referenz für student-generated rollouts | Liste ist keine Lizenzfreigabe; nur tatsächlich repo-auditierte Kandidaten übernehmen. |

**Urteil:** V14 muss **nicht** einen eigenen vollständigen LLM-Inferenzkern oder einen separaten großen Training-Framework-Klon bauen. Der einzigartige neue Eigenbau ist der **kleine C++/Python-Port-Adapter** zwischen Organspace, echten LFM/Needle hidden states, trainierbarem Head/LoRA, eigenen Outcome-Kanten, User-Approval und Speicherzustand. Die Forschung kann und soll massiv vorhandenen, gut geprüften Code nutzen.

## R4. Forschung: Self-Distillation und die neue JEPA-Kombination

Der Wortlaut des vom Nutzer erwähnten „tagealten Papers“ war nicht exakt gegeben. Eine Erfindung eines sicheren Treffers wäre falsch. Folgende *echte* verwandte Primärarbeiten wurden identifiziert; beim späteren Einbringen der konkreten Paper-URL kann die Reihenfolge aktualisiert werden, ohne die Architektur wieder umzuschreiben.

**[Self-Distillation Enables Continual Learning / SDFT](https://arxiv.org/abs/2601.19897)**, ICML 2026 ([Proceedings](https://proceedings.mlr.press/v306/shenfeld26a.html)): derselbe Student, mit Demonstration als privilegiertem Kontext, leitet on-policy Lehrsignale ab; Ziel kontinuierliche Fähigkeitsaufnahme mit weniger Forgetting. Passt zum V14-Pfad „selbe Modellfamilie, unterschiedliche Kontextsicht“. **Nicht** erst diese Woche erschienen.

**[Self-Distilled Reasoner: On-Policy Self-Distillation for LLMs](https://proceedings.mlr.press/v306/zhao26be.html)**: Grundlagenthema OPSD, eigene Generierungen unter Teacher-Bewertung. Als Referenz für Token/KL-Signal und Student-Rollout verwenden.

**[A Good Self-Teacher Meets the Student Where They Are / JOLT](https://arxiv.org/abs/2610.10447)**, 2026-10-07: Ein privilegierter Teacher kann *trotz* besserer eigener Taskleistung den Student verschlechtern. JOLT trainiert Lehrer unter Outcome-Rewards und KL-Nähe zum aktuellen Student, Student mit dense On-policy Distillation. **Sehr relevant** für den V14 Learning-Direction-Head und das Verbot, Teacher als unfehlbare Wahrheit zu behandeln. Teacher-/Student-Update-Gradienten sind klar zu trennen.

**[SeOPD](https://arxiv.org/abs/2609.33181)**, 2026-09-27: „deep thinking“ erzeugt Zusatzinformation, „non-thinking“ wird damit distilliert. V14-Analogon: B1/B2 langer Koalitionsprozess liefert *zulässiges, überprüftes Zusatzwissen*, ein kleines C3 oder Router lernt eine schnellere Approximation. Ergebnis nicht als sicher auf andere Modellarchitekturen übertragbar ausgeben.

**[OISD: On-Policy Internal Self-Distillation](https://arxiv.org/abs/2605.29089)**, 2026-05-27: End-Layer als detach Teacher, Intermediate-Layer erhält logit-/attention-alignment. Für die Idee „Prediction Heads beobachten Repräsentation und steuern die Lernrichtung“ näher als ein reines Antwort-Kopieren; aber es ist **nicht automatisch** ein JEPA-Weight-Delta-Optimizer. Prüfe echte hidden states und den Abstand der Tokenizer/Modelle. Paper nennt Code zukünftigen Release; nicht ungeprüft übernehmen.

**[Stabilizing On-Policy Targeted Guidance in Agentic RL](https://arxiv.org/abs/2611.05266)**, 2026-11-03: per-turn Feedback als On-policy-Self-Distillation; Bezug zu V14 Tool/Action/Outcome, aber überwiegend RL-Agent-Setting.

**[ECOS / Environment-Calibrated OPSD](https://arxiv.org/abs/2611.12232)**, 2026-11: Umweltfeedback kalibriert Teacher-Vertrauen, nützlich für V14 World/Outcome. Nur als Paper-Idee, keine ungeprüfte Codefreigabe.

**[Privileged Information Does Not Guarantee Privileged Guidance](https://arxiv.org/abs/2611.16064)**, Mitte November 2026: Untersuchung, wann Teacher-Hinweise die tatsächliche Student-Generierung nicht verbessern. V14 muss damit rechnen, dass Token-Vorhersage-Verbesserung **nicht** in besserer frei generierter Antwort ankommt.

**[Learning Dynamics of On-Policy Distillation](https://amarcu.github.io/ai-paper-digest/archive/2026-11-06.html)**, November 2026: Rückkopplung durch Student-eigene Datenverteilung bei jedem Schritt. Warnsignal für iterative Selbstbestätigung, Drift und Outcome-Abhängigkeit.

**Befund zur Kombination:** Ein qualitativ brauchbarer V14-Mini-Distillationsweg nutzt Teacher–Student-KL/JS oder Representation Matching als **weiteren Verlust**; JEPA predict-target/EMA bleibt eigenständiges objective. Ein kleiner Meta-Head prognostiziert, *wo* ein lokales Update helfen könnte, statt blind alle Gewichte zu verändern. Erfolg wird erst nach echter Shadow-Aktualisierung + Holdout-Abweichung gemessen. Dieser Head kann später über eigene Prediction Error (predicted Δutility vs actual Δutility) online lernen. Die Verbindung ist ein **neuer Forschungsentwurf**, nicht automatisch eine veröffentlichte validierte Methode.

**Formale Minimalstruktur:** Sei student view s, teacher view t*, z = encoder(s), z+ = stopgrad(EMAEncoder(t*)), y = observed outcome und h = extra privileged verified context. Dann z_hat = P(z, action, context) mit L_JEPA = d(z_hat,z+). Für on-policy student tokens a~π_S gilt L_KD = D(π_T(.|s,h),π_S(.|s)) nur auf legitimem gleichen Token-/Actionraum. Update-Proposal m=H(z,error,teacher_diff,eligibility,drift,source_trust). Gradient/Eligibility-Update **auf trainierbaren Parametern**: Δθ = bounded(mask=m, optimizer_grad(L_JEPA + α L_KD + β L_outcome + γ L_retention)). Optionaler V-Head sagt ΔU voraus; Training mit L_meta = (ΔU_pred−ΔU_holdout)^2. Für inkompatible Tokenizer Alignment über explizite Shared Action/Latent/Token-Witness, keine rohe KL zwischen ungleichen Vokabularen. Bei instabiler KL, OOD oder schlechten Retentionsdaten nur Shadow verwerfen.

**Abgrenzung zu Backprop:** Distillation und JEPA sind Ziele/Trainingsanordnungen, kein genereller physikalischer Ersatz für Backprop. Lokale drei-Faktor-Plastizität und Eligibility können **nachgewiesene** lokale Optimierungsregeln realisieren; ohne geeignete Gradienten/Surrogates darf ihre Wirkung nicht als gezielte Deep-Weight-Korrektur behauptet werden.

## R5. Fremdcode-Wiederverwendung je V14-Organ

| V14-Teil | Zuerst im V13-Repo untersuchen | Externer Kandidat | Bauen muss V14 vor allem |
| --- | --- | --- | --- |
| A0–A5 und Audio/Vision | \`v13/aplane.py\`, \`a5_*.py\`, \`raw_ear*.py\`, \`vision.py\` | vorhandene Audio/Whisper- und TTS-Lizenzen nach separater Modellprüfung | gemeinsame Zeitachse, SourceRef-Spannen, native A3-Empfänger |
| B1/B2 Native inference | \`models.py\`, \`runners.py\`, \`bodies.py\`, \`cognition.py\` | llama.cpp, Cactus/Needle-Treiber unter dessen eigenen Bedingungen | getrennte Detail/Gist-Sichten und echte native Erfolgsmessung |
| B3 Latent/Enlightened | \`enlightened_space.py\`, \`b3bridge.py\`, \`latent_bridge.py\` | Forschungsreferenzen JEPA/BYOL/VICReg, ggml Matrixkern | Sender-Hidden-Exporte, Receiver-Projektion, OOD, genaue Token/State-Wirkung |
| C2/C3/JEF | \`executive.py\`, \`fastpolicy.py\`, \`runtime.py\`, \`cognition.py\` | Native LFM llama.cpp / Needle, TRL-Teacher für offline Kompression | native C3 speed/prefill, tatsächliche ausgewählte Offer-Konsumierung |
| F3 Memory | \`memory.py\`, \`semantic_memory.py\`, \`episodes.py\`, \`world*.py\` | SQLite / ggf. lizenzkonforme Vektorindex-Bibliothek | eventbasierter Graph, source-bound „second attempt“, Widerruf |
| F4 Learning | \`body_jepa.py\`, \`body_training.py\`, \`online_world.py\`, \`plasticity.py\` | TRL/SDPO/SDFT, River, Avalanche, ExecuTorch | trainierbarer Master/LoRA + gerçek native delta + retention |
| Sleep/Dream | \`sleep.py\`, \`sleep_offline.py\`, \`consolidation.py\` | River/Avalanche für Referenz-Replay | Outcome- und Curiosity-basiertes Sampling, Stop/Resume |
| Action/Tools | \`toolstep.py\`, \`transaction.py\`, \`actionlearn.py\` | Standard Werkzeugbibliotheken unter Licence/Audits | Consent, Transaction, Corollary, Outcome und Learning |
| UI/Android | \`managed_console.py\`, \`mobile_dashboard.py\`, \`runtime_deploy.py\` | Termux, native Build-Tools, ggml | echte Ein-Befehl-Installation, Button-/Updater-Ehrlichkeit |
| Agentische Selbstoptimierung | aktuell diverse \`agi/\` + Kandidaten | Git/GitHub CI, Code-review-Werkzeuge | isolierter Self-Edit-Planer, reviewed diff, sandbox, Rollback |

Das Wort „noch bauen“ bedeutet **Adapter oder fehlende echte Verbindung**, nicht, dass jedes Modul neu geschrieben werden soll. Bei Systemen mit bereits vorhandenen 200 Kandidatendateien muss zuerst der tatsächliche Consumer im Runtime-Graph gesucht werden.

## R6. Voller V14-Integrations- und Entwicklungsfahrplan

### Phase A — Source Reconstruction & Reality Map
- Roh-Canon/Drive/neuere Entscheidungen mit unveränderlichen Quellkopien; jeweils Datum, Hash, Herkunft, Lizenz.
- V13 Runtime, stager/builders, echte ModelRunner, UI und ALLE Candidate-Dateien inventarisieren. Mapping \`canonical_id → implemented_file → real_caller/consumer → evidence → missing\`.
- Widersprüche schriftlich als alternatives Verhalten ausweisen und neueste Userentscheidung beachten. Nicht unbemerkt alte Rechte auslassen.
- Output: maschinenlesbare Canon-Feature-/Edge-Registry und Trace-Generator; mindestens ein inspectierbarer Dry-Run des gesamten Graphen.

### Phase B — Real connected organism
- V14 Runner/organ ports im vorhandenen Runtime-Spine verbinden. Text-Event A5 → JEF/Episodic/World → echte native B1/B2 Offers → source-bound C3 input → sichtbare Antwort. Kurzer Reflex kann früh antworten, Observer dürfen weiterarbeiten.
- Body→B3→Body und **Enlightened Space system-wide** mit typisierten Nachrichten (keine „latent“-Etiketten ohne Native Receiver).
- Eine lokale Chat-Session mit Reboots, SourceRefs und saturiertem RAM auf Redmi. Wenn eine native Funktion fehlt, sichtbarer OFF/SHADOW-Status plus Antwort; keine 30-Sekunden-Stille.
- Output: reproduzierbarer 20-Turn-Messlauf und native First-Token-Budget, nicht 20 PRs.

### Phase C — Memory/Self/World & real outcome loop
- Existing SQLite Experience/World/Memory/Self Pfade in normalen Run injizieren, Lernen über reale Outcome-IDs, second-attempt und schwierige Analogiefälle messen.
- Human corrected span, explicit approved teacher, source trusted baseline, actual action/result einheitlich typed; Retention und Forgetting ab erster Deltaklasse.
- Output: in einer neuen Session erkennbar **richtige** veränderte zweite Antwort, mit Quellen, Widerruf und Reset.

### Phase D — trainable JEPA/Distillation/LoRA graph
- Bestehende native LoRA/Body-JEPA-Experimente in separaten Worker mit echten trainierbaren Gewichten, EMA/Optimizer/RNG-Persistenz, exact source/teacher/student lineage.
- A3, B1, B2, World, JEF-/C3-Head separat trainieren, cross-organ Lernsignale kontrolliert annehmen, Replay/Sleep als Quelle zugelassener Fälle.
- TRL/SDFT-Referenz am Linux-Host/Cloud; kleinen exportierten Teacher-Pair-/Meta-Head auf Android testen. Kein Muss, große PyTorch-Frameworks aufs Handy zu ziehen.
- Output: gemessenes Δθ + Restart + held-out usefulness/forgetting + Rollback für **mindestens einen** Pfad je Lernklasse, nicht nur ein numerischer Loss.

### Phase E — experimental online mini-distillation direction head
- On-policy eigene Rollouts, privileged Teacher nur mit echter verifizierter Extrainformation. Teacher-KL zur Student-Politik + Outcome-Kalibrierung; Teacher nie automatisch richtig.
- PREDICT_STATE/PREDICT_DELTA/PREDICT_UTILITY getrennt entwickeln. Zunächst nur kleine Matrix-/LoRA-Parameter. Drittgewichte und private model states nicht unbegrenzt kopieren.
- Ablationsmatrix JEPA-only, KD-only, joint, no META, full META, frozen/co-evolving teacher, random teacher, replay/no replay; reale positive Transfer- und Forgetting-Messung. Negative Ergebnisse bleiben dokumentiert.
- Output: belastbarer Mehrwert oder begründete Abschaltung der neuen Zusatzkomponente, während alle anderen Lernpfade weiter funktionieren.

### Phase F — modalities / tools / autonomous skill and self-edit proposals
- Live Audio/Vision/Raw-Path an echten A-Events, asynchronen Aufmerksamkeit-Ports und Text-Ausgabe binden. TTS/Stimme nur mit geklärten Modell-Lizenzen/Consent.
- Handlungsschleifen mit Vorhersage, Tool-Proposal, Approve, Execute, Observe, Compare, Learn.
- Self-edit/Architecture Planner als Vorschlags-/Experimentpfad mit Git diff, separatem Branch, Tests, Angriffsszenarien, Report/Review und Rollback. Keine unautorisierten Selbst-Deployments.
- Output: demonstrierter End-to-End-Sensorimotor/Tool-Outcome und wiederholbar verbesserter Skill.

### Phase G — sparse multi-organ optimization and robust release
- zwei native unterschiedliche Body-Modelle, später sparse MoE+JEF Tiny, echte LFM Hybrid-State-Cache-Grenzen, warm residency, Energy Profiling, quantized trainer/LoRA fallback.
- reale Android-Hardware-Kohorte mit Memory, PSS, Thermik, ggf. 6GB-Floor vs Desktop/Cloud Crossbench, Langzeit-Retention, Build/Update/rollback.
- Abschluss nicht durch Featurezähler, sondern durch beobachtete funktionsfähige Interaktionen und Canon-Ledger.

**Parallelität:** Phase A/B/C sollen sich überlappen und D/E beginnen als isolierte Lab-Probe, sobald Inputs existieren. F/G können unabhängig vorbereitet werden. Keine starre serielle „einen Mini-PR pro Stunde“-Sackgasse.

## R7. Agentenplan mit konfliktfreier Dateieigentümerschaft

Mindestens sieben Fachrollen können gleichzeitig arbeiten:
- Coordinator/Boss: Canon, Integrationsgraph, Release/PR-Review, Cross-Review mit Claude/Codex, Source-Ledger.
- Native/Android: llama.cpp LFM Hybrid/LFM2 QAD, Modell-/Tokenizer-Prefill, TTFT, PSS/RSS, Termux installer.
- A/Perception/Modalities: A0–A5, Audio/Vision/Student Projector.
- Body/B3/Enlightened Space: B1/B2 differenzieren, Native Hidden-Receiver, Message/Latent B3, Shared Space alle Organe.
- C/JEF/UI/Tools: C1–C7, Reflex/Antwort, Action Gate, Autoupdate/Bedienung.
- Memory/Self/World: Experience, SQLite Graph, Outcome, Replay, self-model, causal predictions.
- JEPA/Continual Plasticity: real Master/LoRA, EMA/optimizer state, World/Body, eligibility/three-factor.
- Research/Distillation/Licensing: neue Papers, OPD/SDFT/JOLT/OISD, external licenses, third-party ABI/release notes.
- Independent QA/Security: Retention/replay, Canary privacy, source-bound consent, Gerätedaten-Nachweise.

Eine Fachrolle bearbeitet eigene Dateien/Branchs. Shared Contracts nur nach kurzer Koordination ändern. Alle Arbeitspakete dürfen **vor** langer Geräteabnahme als isolierte Kandidaten gebaut und getestet werden. Keine Expertenrolle darf das Gesamtprojekt durch eine lokale Testpanne monopolisiert bekommen. Selbstständig neue Evidenz und alternative Opensource-Codepfade suchen; keine widersprüchlichen gleichzeitigen Edits. Agenten schreiben nach jedem substantiellen Schritt einen knappen Patch-/Consumer-/Claim-Bericht, nicht nur „alles grün“.

## R8. Reuse-first Entscheidungsbaum

1. Gesuchtes Feature / exakter Consumer und SourceRef-Contract benennen.
2. V13 Repo nach aktueller Implementierung, Staged Candidate, Tests und historischen PRs durchsuchen.
3. Aktuelle öffentliche Quellen suchen (GitHub, primäre Papers/Docs, einschlägige Implementierungen und Lizenz).
4. In Tabelle: Lizenz-Befund, Modell-/Gewichts-Befund, Kompatibilität/ABI, benötigter RAM und Aktivierungsaufwand.
5. Drei Optionen vergleichen: bestehender interner Code, externes Modul, eigener schlanker Adapter. Kleinsten **echten** Integrationstest auswählen.
6. Unter eigener Branch bauen; vollständige Outcome-Kante und Readback statt Standalone-Demo. Smoke, Regression, Retention/negative gate, Review.
7. Nur abgestimmte, geprüfte Integrationen in gemeinsamen V14-Zweig; sichtbarer nicht-funktionierender Testfall ist kein Grund, andere Module nicht weiterzubauen.
8. Wenn zweimal kein substanzieller Fortschritt: Research wechseln, upstream nach Issues/Workarounds prüfen, alternativen trainierbaren Port testen; Ergebnis im Research-Log dokumentieren statt weiteren Minipatch.

## R9. Messplan: Wie V14 Fortschritt tatsächlich definiert

Messungen sind **nicht** ausschließlich CI-Grün. Primäre Metriken:
- Nachweis, dass jeder Organ-Producer mindestens einen echten Consumer hat; EventTrace, Versionsbindung und Drop/Censor erklären.
- Median/p95 TTFT, Tokens/s, Hardware-Warm-/Cold-Last, PSS/RSS, Battery/thermal, Antwortquote über Inputkomplexität; Kurzfragen dürfen keine langen Wartezeiten haben.
- B1/B2 **komplementäre** Verbesserung gegenüber B1-only/B2-only/C3-only und NO_MESSAGE/SOURCE_EXACT/B3 Latent-Ablation.
- Gedächtnis: Quellenbindung, Wiederauffinden, Paraphrase, false memory, Widerruf, pro Session Restart.
- Lernen: trainierbare Deltas, EMA/Optimizer checkpoint, holdout utility, Retention, Forgetting, Generalisation, real zweite Chance; separate Testreife.
- Distillation Head: vorgeschlagene Masken/Schrittgrößen gegen tatsächlich beobachteten Nutzen, Nullhypothesen und Ressourcenverbrauch.
- Bedienung: install, dashboard, update, auto-update, restart, cancel und rollback ohne fehlerhafte Statusanzeigen; Nutzerinteraktionen vollständig privat.

Jeder Claim hat \`Observed / Simulated / Planned\`, SHA der laufenden Quellen, Modellrevision, Gerät, Datenscope, Vorher/Nachher und What-this-does-not-prove. Keine „fertig“-Markierung allein durch JSON/Wire/Mocks.

## R10. Recht, Sicherheit, Responsible Reuse – konkrete Checks

Bei fremdem Code: LICENSE prüfen, alle Dritt-Lizenzen vollständig beilegen, COPYRIGHT behalten, NOTICE pflegen, Änderungshinweise und Quellenrevision in SBOM; keine Umgehung von Lizenz oder Rechte für ein „geheimes Repo“. Bei Gewichten: zusätzlich Modellkarte, Download/Redistribution/Commercial/Usage Restrictions prüfen. Keine Lizenzannahme allein aus „Open Weights“. Private Nutzertexte nur unter tatsächlicher Trainingserlaubnis in den Learner; Cloud Teacher optional und nicht als stiller Abfluss. No external act without per-class consent / approved action. Selbständerungen nur in eigens angelegtem Source/Weight-Lab mit Rollback und Vergleich.

Dokumenten-/Codearbeiten, die eindeutig unter permissiven Lizenzen stehen, dürfen nach Checks adaptiert werden. Bei unklarem Lizenzstatus nur algorithmische Idee beschreiben und eigenständig entwickeln. Dies ist eine technische Due-Diligence-Arbeitsregel, keine individuelle Rechtsberatung.

## R11. Offene Forschungsfragen und explizite Entscheidungen

- **OPSD-Paper-Identität:** Der vom Nutzer erwähnte exakt *tagealte* Beitrag ist anhand des beschreibenden Titels nicht eindeutig identifiziert; SDFT/JOLT/SeOPD/OISD/Nov-OPSD sind belastbare nahe Kandidaten. Keine Behauptung „wir haben das exakte Paper“.
- **JEPA×KD-Kausalität:** Sind latent prediction und token-level self-distillation komplementär oder nur zwei Wege zum selben Proxy? Nur Ablation kann dies zeigen.
- **Gradientenfluss:** Wird „predicted weight delta“ mittels echter differentiabler Meta-Optimierung oder validierter lokaler Eligibility lernt? Propose-only zuerst, keinesfalls blind Base-GGUF schreiben.
- **Privileged Teacher:** Verifiziertes Outcome statt selbst bestätigter Antwort; Teacher besser in Training ≠ Student besser in Generation.
- **Native Hidden State:** LFM2.5/QAD/ggml aktivierbare Layer-Export-Schnittstelle ohne enorme Prefillkosten; Version pinnen und Real-Phone-Probe.
- **Mehrfach-Training:** Interferenzen B1/B2/C3/World, forgetfulness, sample bias, action-source trust, gerade bei 6GB-Klasse.
- **Self-edit:** sichere, überprüfbare Modulversionierung und neue erlaubnisgebundene Tool-Arten; kein autonomer Release-Merge.

## R12. Arbeitspaket-Register und verpflichtender Abschluss

Jede Canon-Pflicht (einschließlich IH-H0–H36, AG-, G-, A/B/C/F-, WP-, R-, B3-H und späterer PR-Ideen) muss als stabile ID im Implementierungsledger erscheinen: \`id, origin, requirement, current_code, producer, consumer, status, effect_measure, license, owner, test, hardware, next_action, rollback, alternatives\`. Das V13-Original und die drei Drive-Roadmaps werden im V14-Master **unverändert als historische Volltexte angehängt**; aus diesen müssen beim nächsten automatisierten Parser-Lauf vollständige ID-Listen erzeugt und mit Registry verglichen werden. Fehlende IDs sind **offen** und dürfen nicht wegdefiniert werden.

Der Coordinator integriert funktionsfähige vertikale Pakete unabhängig von sekundären Spezialforschungen. Ein abgebrochener Update-Test oder JEPA-Ablation darf nicht alle anderen Arbeitspakete stoppen. Der Nutzer bekommt regelmäßig konkrete Nutzbarkeit, nicht bloß Reports. Die stündlichen Agenten müssen die neue V14-Branch/Docs als **Plan** lesen und mit echten Änderungen fortsetzen; bisherige V13 Release-Branches bleiben unverändert, bis eine geprüfte Migration existiert.

## R13. Quellenverzeichnis und Erstprüfung (2026-11-19)

**Eigene Quellen:** [V13 GitHub](https://github.com/RedMentos/Aii), \`v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md\`, \`AGENTS.md\`, \`v13/ROADMAP.md\`, \`v13/code/BUILD_STATE.json\`; Drive ROADMAP 1/2/3, SICHTUNG, Handoff und Originalarchiv. Zuletzt integrierte Build-first-Regeln: [PR #2083](https://github.com/RedMentos/Aii/pull/2083).

**Upstream-/Paper-Originale:** [llama.cpp](https://github.com/ggml-org/llama.cpp), [ExecuTorch](https://github.com/pytorch/executorch), [River](https://github.com/online-ml/river), [Avalanche](https://github.com/ContinualAI/avalanche), [V-JEPA 2](https://github.com/facebookresearch/vjepa2), [TRL Distillation](https://huggingface.co/docs/trl/main/en/distillation_trainer), [TRL SDPO](https://huggingface.co/docs/trl/main/en/sdpo_trainer), [SDFT 2601.19897](https://arxiv.org/abs/2601.19897), [OPSD 2601.18734](https://arxiv.org/abs/2601.18734), [JOLT 2610.10447](https://arxiv.org/abs/2610.10447), [SeOPD 2609.33181](https://arxiv.org/abs/2609.33181), [OISD 2605.29089](https://arxiv.org/abs/2605.29089), [Stabilizing Guidance 2611.05266](https://arxiv.org/abs/2611.05266), [ECOS 2611.12232](https://arxiv.org/abs/2611.12232), [OPSD Guidance Audit 2611.16064](https://arxiv.org/abs/2611.16064).

**Scope:** Einige aktuell sichtbare Primärseiten und Lizenztexte wurden überprüft; große Dritt-Repositories wurden **nicht** zeilenweise auditiert und ihre komplette transitive Lizenzliste noch nicht aufgeschrieben. Keine fremden Programmdateien wurden in diesem Dokument kopiert. Diese Vorprüfung erlaubt die **Entscheidung, was als Nächstes zu testen ist**, nicht die automatische Weiterverbreitung von Fremdsoftware.

---

**Ende Teil 2.** Darunter folgen im V14-Master die unverändert erhaltenen Volltexte des bisherigen V13-Canons und der Drive-Roadmaps als verbindliche Preservation-Anhänge. Neue V14-Arbeit muss *an diesen gesamten Umfang* rückgebunden werden.


---

# ORIGINALANHANG A — HISTORISCHER V13 v10.16.1 CANON, UNVERÄNDERT

# V13 / INQUISITION — v10.16 WORK HANDOFF — SINGLE SOURCE OF TRUTH

**Stand:** 20.09.2026  
**Purpose:** Diese Datei ist die **eine Übergabedatei für ChatGPT Work**. Sie enthält den vollständigen v10.15 Integrated/Implementation-Hardened Canon plus den darauf aufbauenden v10.16 Neuroscience × Implementation Research Pass. Keine zweite Datei ist zum Verständnis erforderlich.

---

# WORK EXECUTION CONTRACT — ZUERST LESEN

## W0 — Auftrag

Baue V13 als **echtes, ausführbares, testbares System** aus diesem Dokument. Liefere nicht nur einen neuen Blueprint, Pseudocode, Interfaces oder Dummy-Implementierungen. Der bestehende Canon soll implementiert, instrumentiert, getestet und auf der Zielruntime schrittweise bewiesen werden.

## W1 — Preservation / No Silent Simplification [LOCKED]

- **Keine gesetzte Canon-Funktion still löschen, um Coding einfacher zu machen.**
- Wenn eine Funktion auf aktueller Hardware/Runtime noch nicht real implementierbar ist: `unavailable | scaffold | shadow | fallback | experimental` setzen, Grund + fehlendes Gate loggen und Pflicht offen halten.
- Forschungsmechanismen dürfen durch bessere Mechanismen ersetzt werden, **wenn dieselbe Funktion, Provenance, Retention, Rollback und Second-Attempt-Utility nachweisbar erhalten oder verbessert werden**.
- Anatomische Hirnbegriffe sind funktionale Analogien, keine Pflicht zu biologischem Namens-Cosplay.

## W2 — Canon-Reihenfolge

1. Diese Work-Handoff-Regeln.
2. v10.15 Integrated Canon + `IH-H0..IH-H36`.
3. v10.16 Neuroscience × Implementation Delta am Ende dieser Datei.
4. Neuere explizite `[LOCKED]`-Präzisierungen schlagen ältere widersprüchliche Legacy-Formulierungen.
5. Legacy-Namen werden nur über die definierte Alias-Firewall gelesen; neuer produktiver Code verwendet ausschließlich die kanonischen IDs.

## W3 — Definition von „implementiert“ [LOCKED]

Ein Feature darf **nur** als fertig markiert werden, wenn mindestens vorhanden sind:

```text
1. CODE
2. REAL DATA / REAL STATE PATH
3. PERSISTENCE + RESTART, falls der Zustand persistent sein soll
4. TEST, der das reale Verhalten beweist
5. TELEMETRY, die beweist, dass der Pfad tatsächlich lief
```

Für Research-/Hardware-Funktionen zusätzlich, wo relevant:

```text
6. ABLATION / SIMPLE BASELINE
7. RUNNER_PROOF oder TRAIN_RUNNER_PROOF
8. RETENTION / REGRESSION CHECK
9. ROLLBACK / FAILURE PATH
10. dokumentierte CLAIM LIMIT (was das Experiment NICHT beweist)
```

Nicht ausreichend: Klassenhülle, TODO, Fake-Latent, Random Tensor, hardcodiertes `success`, Mock des kompletten Pfades, Config ohne Consumer, UI ohne Backend-Effekt.

## W4 — Bauweise

- **Nicht alles gleichzeitig implementieren.** Die STEP-0→11-Abhängigkeiten im Canon sind verbindlich.
- Beginne mit einem echten vertikalen Age-0/Text-only-Core.
- STEP 0 muss Storage/Migrations, IDs/SourceRef, Schema Registry, Rules/Permissions, Generation Manifest, Operator Parser, bounded Queues, Cancellation, Response Governor, Resource Monitor, Logging, Model/Runner Manifest und `:doctor` real besitzen.
- Danach STEP 1 C/JEF, STEP 2 B1/B2 Observer, STEP 3 Experience/Fast Episodic, STEP 4 Teacher Reference, STEP 5 JEF Shadow Learning, STEP 6 Body/Callosum Learning.
- Latent Callosum wird **nicht** als Voraussetzung für den ersten funktionierenden Core erzwungen: zuerst Exact/Source/Control/Symbolic Baselines, danach Latent im Shadow/Ablation.
- Neue Modalitäten erst, wenn der text-only Age-0-Core stabil ist.

## W5 — Mobile / Redmi

Redmi Note 10 Pro / 6-GB-Klasse ist der **Age-0-Labor-Floor**, nicht die Definition der Architektur.

- Python darf Orchestrierung übernehmen; große Hot Paths möglichst native Runner/Kernels.
- Keine RAM-/Speed-Behauptung aus Dateigröße ableiten.
- Jeder produktive Body braucht echten `RUNNER_PROOF` auf Zielruntime.
- Jeder trainierbare Pfad braucht getrennten `TRAIN_RUNNER_PROOF`, bevor Phone-Learning als praktisch behauptet wird.
- B1/B2 dürfen funktional parallel, physisch zunächst sequential/asynchronous/sampled laufen.
- Quantisierte Inferenzgewichte sind nicht automatisch SGD-Master.

## W6 — Learning

- User-visible output wird niemals von Learning blockiert.
- Age 0: `RECORD_ONLY | SHADOW_UPDATE | APPROVED_COMMIT` strikt trennen.
- Fast Episodic/Exact Memory darf Second-Attempt-Vorteil liefern, bevor Body-Gewichte lernen.
- Predictor/JEPA zuerst klein und lokal; tiefere Body-Updates nur hinter Retention/Regression-Gates.
- Eligibility dient als lokales Credit-/Plasticity-Signal zusammen mit realem lokalem Error/Gradient und typisierten Outcome-Modulatoren; nicht als ungeprüfter universeller Gradientenersatz.
- Bei MoE zunächst Router/shared path schützen; active-expert/projector/delta Experimente vor Router/Base-Weight-Plastizität.
- Kein parametrisches Lernen aus PROVISIONAL State.

## W7 — Brain-near Implementation

Die Neuroscience-Schicht ist **Designconstraint, nicht Marketing**:

- mehrere Integrationszeitskalen statt starrem „linke/rechte Hirnhälfte“-Mythos,
- lokale spezialisierte Verarbeitung + rekurrente Kopplung,
- kein einzelner Master-Controller,
- begrenzte focal/global availability ohne Bewusstseinsbehauptung,
- fast + slow memory,
- Action → Corollary/Efference Copy → Outcome Comparison,
- Replay/Consolidation getrennt von Dream/Counterfactual,
- Homeostasis/Metaplasticity langsam und stabilisierend,
- Age als Human-Control-/Development-Hülle über kontinuierlicher Reife.

Wo biologische Evidenz unsicher ist, wird die Funktion getestet statt die Analogie als Fakt zu behandeln.

## W8 — Operator / Termux

Der Age-0-Lab-Build muss praktisch benutzbar bleiben: persistenter Chat, Verlauf nach Restart, Partial Output bei Abbruch, sauberer Cancel/Pause/Resume/Unload/Shutdown und privilegierter Bedienkanal. Die im Canon definierten `:`-Kommandos sind echte Backend-Aktionen, keine UI-Dummies.

## W9 — Abschluss jeder Phase

Aktualisiere den `Work Completion Ledger` für **jede** Canon-Funktion mit:

```text
feature_id
canon_source
implementation_files
runtime_owner
state_owner
schema_id
persistence
current_mode
hardware_proof
unit_tests
integration_tests
benchmark
gate_status
known_limitations
```

Gib am Ende jeder Phase zusätzlich aus:

```text
- was real funktioniert
- was Shadow/Experimental ist
- was noch unavailable ist
- welche Tests gelaufen sind + Resultate
- gemessene RAM/Latenz/Training-Werte, falls relevant
- welche Canon-Gates als nächstes blockieren
```

## W10 — Wichtigster Erfolgsbeweis

V13 gilt nicht deshalb als funktionierend, weil drei Modelle antworten. Der zentrale frühe Proof ist:

> **Eine vergleichbare zweite Situation wird durch echte gespeicherte Erfahrung/Feedback/gelernte Policy besser behandelt als die erste, ohne blindes Response-Caching, ohne Verlust bestehender Constraints und nach Restart reproduzierbar.**

---

# BEGIN FULL CANON

> Der folgende Inhalt ist der vollständige integrierte Canon. Die interne v10.15-Titelzeile bleibt absichtlich erhalten, weil v10.16 als additive Research-/Implementation-Schicht darauf aufbaut.

# V13 CANONICAL BRAIN BLUEPRINT v10.15 — INTEGRATED RESEARCH + IMPLEMENTATION-HARDENED CANON
## v10.13/v10.14 vollständig erhalten; v10.15 Research-Stack und Implementation-Hardening redaktionell in den Canon integriert
## Research-hardened Architektur-Canon: Dual-Hemisphere-System mit verschiedener zeitlicher Auflösung, entwicklungsabhängiger Selbststeuerung und evidenzgebundener Konsolidierung

**Stand:** 20.09.2026  
**Status:** **v10.15 integrated/work-ready**; Architektur-Canon v10.12 / v10.11 vollständig erhalten, Implementation-Hardening integriert; Topologie neu indiziert: **A = Ingress/Perception, B = Split-Brain Core, C = JEF/Executive–Action** / historische Hemisphären-A/B werden zu **B1 Detail** und **B2 Gist** / Attention-, Learning-, Memory-, Age-, Provenance- und Runtime-Funktionen werden als querliegende Fabrics explizit gemacht / Needle und ein separates Tiny-Language-Organ sind austauschbare Organe innerhalb von C/JEF / keine alte Core-Funktion gestrichen.  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

**Integrated-Hardening-Regel:** Die frühere separate Hardening-Datei ist in dieser Ausgabe **nicht als Appendix angehängt**, sondern thematisch in Canon, Runtime, Learning, Persistence, Action/Tools, Research und Build-Gates einsortiert. `IH-H0..IH-H36` sind stabile Audit-Labels, keine zusätzliche Architektur.

---

# 0T. INTEGRATED IMPLEMENTATION-HARDENING — globale Regeln

## IH-H0 — Preservation Rule [LOCKED]

Diese integrierte Hardening-Schicht darf **keine** kanonische V13-Funktion still löschen.

Sie darf nur:

1. widersprüchliche historische Benennung entwirren,
2. offene Coding-Verträge konkretisieren,
3. Runtime-/Storage-/Concurrency-Fehler verhindern,
4. Research-Annahmen hinter messbare Gates stellen,
5. bestehende Gates maschinenprüfbar machen,
6. mobile Umsetzung von Architekturtheorie trennen.

Wenn ein späterer Code-Entscheid eine gesetzte Funktion nicht implementieren kann, gilt:

```text
NICHT: Funktion heimlich streichen
SONDERN: capability = unavailable / shadow / fallback
         + Grund loggen
         + Test rot lassen
         + Canon-Funktion als offene Pflicht behalten
```

---

## IH-H1 — Canon Precedence + Legacy Alias Firewall [BLOCKER]

### Problem

Die Datei enthält absichtlich historische Schichten. Dadurch existieren gleichzeitig neue Makro-Namen und ältere Formulierungen wie `A/B/C`, `C_fast`, `C_native`, `C_focal` oder „drei Bodies“. Für Menschen ist die Migration erklärbar; für Code-Generatoren ist sie gefährlich.

### Verbindliche Regel

**Neue Source-Dateien, APIs, Logs, Checkpoints und DB-Felder verwenden ausschließlich:**

```text
A_PLANE / A0..A5
B1_DETAIL
B2_GIST
B3_CALLOSUM
B4_DISTRIBUTED_STATE
B5_SUPPORT_INTERFACES
C_JEF_SYSTEM / C0..C7
F1..F7
```

Legacy-Namen sind nur erlaubt in:

```text
legacy_migration.py
legacy_aliases.yaml
Dokumentationskommentaren mit LEGACY: Prefix
```

Verboten in produktivem Code:

```text
A = Detail
B = Gist
C = ein einzelnes Judge-LLM
C_fast als Komponenten-ID
C_native als Komponenten-ID
C_focal als Komponenten-ID
```

Mapping:

```text
legacy A/Detail  -> B1_DETAIL
legacy B/Gist    -> B2_GIST
legacy C/Judge   -> C_JEF_SYSTEM
C_fast           -> JEF_FAST_POLICY
C_native         -> JEF_LANGUAGE_REPORT_PATH
C_focal          -> JEF_FOCAL_LOOP
```

### Build-Lint

CI/`:doctor` muss neue Code-Dateien auf unerlaubte Legacy-IDs prüfen. Ein Treffer außerhalb des Migration-Moduls ist ein Fehler.

## IH-H2 — Dokument-/Versionshygiene [MUST]

Die historische Basis trug noch den v10.14-Titel, während der v10.15-Research-Stack additiv folgte. In dieser integrierten Ausgabe ist der Dokumenttitel auf v10.15 vereinheitlicht; die Herkunft der Schichten bleibt nur im Machine-Manifest erhalten.

Ab jetzt besitzt jeder Build ein Machine-Manifest:

```yaml
canon_family: V13
base_document: v10.14-triple-pass
active_supplement: v10.15-research-stack
macro_topology: v10.12-reindex
hardening_patch: 2026-09-20-impl-hardening-1
```

Human section numbers sind **keine IDs**. Die Datei enthält mehrfach `#30`, `#31`, `#32`, `#33` und wiederholte Invariantennummern. Code referenziert daher stabile IDs, z. B.:

```text
INV-JEF-NOT-MONOLITH-001
INV-CALLOSUM-ALIGN-004
GATE-RUNNER-PROOF-B1-001
SCHEMA-OFFER-PACKET-001
```

Keine Datenbank oder Test-Suite darf sich auf „Kapitel 30 / Punkt 50“ als eindeutigen Schlüssel verlassen.

---

# 0. Warum v10.13 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10 ordnete die Topologie neu; v10.1 präzisierte Bootstrapping und Ausführung; v10.2 schloss zentrale Implementierungsambiguitäten. **v10.3 härtete die Architektur gegen aktuelle 2026-Forschung und gegen unbelegte Designannahmen. v10.4 korrigierte zwei Dinge, die beim Hardening zu stark verwässert wurden: die unterschiedliche effektive Auflösung der beiden Hemisphären und Age als echte entwicklungsabhängige Kontrollhülle des gesamten Systems. v10.5 verändert diese beiden Punkte nicht. Stattdessen präzisiert es C als kleinen sprachfähigen Executive/Judge mit einem billigen eigenen Sprachpfad und integriert aktuelle Cache-/Reasoning-Techniken von DeepSeek-V4.1-Flash, MiniMax M3 und GLM-5.3-Flash einzeln dort, wo sie eine vorhandene V13-Funktion verbessern.**

Die wichtigsten bis v10.5 gesetzten Punkte plus die v10.6-Interaktionskorrektur sind:

- **[LOCKED] JEF ist das kleine lernende Executive–Effector-SUBSYSTEM, nicht ein einzelnes LLM:** es umfasst persistenten Executive-State, Fast-Control, Language/Control-Interface, fokale Orchestrierung, Broadcast-Bridges, Action/Report-Broker und Lern-/Credit-Schnittstellen. Ein kleines Sprach-/Control-Modell ist **ein austauschbares Organ innerhalb von JEF**, nicht JEF selbst.
- **[LOCKED] Bewusster Zugriff ist NICHT JEF allein:** der funktionale `FOCAL_COALITION_STATE` setzt sich aus JEF-State plus aktuell global zugänglichen A/B-/Memory-/Self-/World-Inhalten und deren rekurrenter Kopplung zusammen.
- **[LOCKED] Ein externer Event darf standardmäßig einen billigen Observer-Pass in A und B auslösen**, auch wenn JEF diese Ergebnisse am Ende nicht braucht. Das liefert kontinuierliche Hintergrundrepräsentationen; JEF muss nicht auf sie warten, wenn Direct/JEF-native schon sicher reicht.
- **[LOCKED] JEF besitzt einen privaten persistenten Native-KV/State und einen exportierten `JEF_BROADCAST_CACHE`:** A/B lernen nicht rohe fremde KV-Tensoren blind zu lesen, sondern trainierte Projektionen/Adapter eines stabilen Broadcast-Schemas.
- **[LOCKED] B1/B2 antworten auf den Observer-Pass primär mit `OFFER_PACKET`s statt Chattext:** Detail/Gist-Latents, Salience, Conflict, Uncertainty, SourceRefs und optionalem Deep-Request. Nur ausgewählte Offers gelangen in die fokale Koalition.
- **[LOCKED] JEF besitzt den einheitlichen Report-/Action-Stream:** A/B können Inhalt oder sogar Decoder-Spans beisteuern, aber JEF/Action-Broker entscheidet, was tatsächlich nach außen geht. Direct/Exact darf generatives JEF umgehen, aber nicht Permissions/Action Safety.
- **[LOCKED] Jede eigene Aktion erzeugt vor dem Outcome eine Corollary/Efference Copy zurück an A/B, World/Self und JEF-State**, damit das System self-caused vs. external unterscheiden und erwartete Folgen lernen kann.
- **[LOCKED] Wertung ist verteilt:** JEF ist nicht der einzige Richter. Outcome/Evidence/Cost erzeugen typisierte globale Modulatoren; B1/B2/JEF erhalten dieselben globalen Signale, aber lernen lokal über unterschiedliche Eligibility/Predictors.

- **[LOCKED] Detail und Gist arbeiten wieder auf unterschiedlichen effektiven Integrationsauflösungen:** Detail bevorzugt 1-Token-/kurze Fine-Slots; Gist bündelt mehrere native Tokens bzw. semantische Spans in adaptive Gist-Slots. Das sitzt **oberhalb** der nativen Tokenizer und ersetzt sie nicht.
- **[LOCKED] Age ist wieder echte Entwicklungssteuerung:** eine globale Development-Stage begrenzt Autonomie/Loops/Self-Edit/Tools/Plasticity; capability-spezifische Reife und kontinuierliche Metriken wirken innerhalb dieser Hülle. Stage 0–5 ist nicht bloß UI.
- Gist-Kompression darf mit Reife wachsen, aber bei Neuheit, Konflikt oder Exactness-Bedarf wieder feiner werden; Entwicklung ist daher nicht monoton "immer gröber".
- Latent-Kommunikation bleibt ein starker Kandidat, erhält aber **keinen dogmatischen Vorrang**: ein gelernter Channel-Policy-Mechanismus muss LATENT gegen SOURCE/EXACT, CONTROL und kurze SYMBOLIC-Nachrichten empirisch rechtfertigen.
- Heterogene Latent-Injection wird zusätzlich auf Norm-/Distribution-Shift, Receiver-Kompatibilität und Downstream-Utility kalibriert.
- `JEF_FAST_POLICY` liefert typisierte parallele Entscheidungen samt kalibrierten Wahrscheinlichkeiten statt nur eines einzelnen Route-Logits.
- `JEF_FOCAL_LOOP` lernt zuerst brauchbare rekurrente Trajektorien; adaptive Halting-Readouts werden anschließend konservativ bzw. auf weitgehend fixierten Trajektorien trainiert, damit das Halt-Gate die Denktrajektorie nicht früh verformt.
- Continual-Learning-Schutz überwacht nicht nur Experten/Router, sondern auch **shared pre-router components** wie Attention, Embeddings, Norms und Router-Input-Collisions.
- World-JEPA erhält Action-/Inverse-Dynamics-, State-Grounding- und Action-Coverage-Signale; Counterfactuals tragen explizite Gültigkeits-/Coverage-Unsicherheit.
- Fast Episodic Memory darf neben exakten Episoden optional **sehr kleine getrennte parametrische Fast-Traces** verwenden, sofern sie Retrieval, Interferenz und Speicherbudget in echten Tests schlagen.
- Context OS darf Body-spezifische KV-/Cache-Policies wählen, sofern der jeweilige Body/Runner dies real unterstützt.
- Feedback erhält eine Evidenzhierarchie; interne Selbstbewertung und Dream dürfen reale/verifizierbare Outcomes nicht epistemisch überstimmen.
- Drei Forschungsrisiken werden zu expliziten Kernexperimenten statt zu stillen Annahmen: heterogene Latent-Kommunikation, stabile Continual Updates in sparse Bodies und lernende Executive-Routing-Policies.
- **[LOCKED/PRECISION] JEF besitzt ein austauschbares Language/Control-Modell, ist aber selbst kein LLM.** Dieses Modell darf User-Text in strukturierte Executive-Pakete übersetzen, Tool-/Action-Kandidaten erzeugen, Retrieval-Keys bilden, Confidence liefern und – falls geeignet – kurze Sprache erzeugen.
- Die historischen Namen `C_fast`, `C_native`, `C_focal` bezeichnen ab v10.12 **Systempfade**: `JEF_FAST_POLICY`, `JEF_LANGUAGE_REPORT_PATH` und `JEF_FOCAL_LOOP`. Sie müssen nicht dieselbe neuronale Backbone-Instanz sein.
- Die hirnnahe Analogie wird geschärft: schnelle automatische und langsamere deliberative Verarbeitung sind **dynamische Regime verteilter Schleifen**, keine zwei anatomisch isolierten "Systeme". C entspricht funktional eher einer kleinen executive/language-capable control surface als einem alleinigen "Chefhirn".
- B1/B2-Wake wird task-/uncertainty-/salience-abhängig. Bootstrap verlangt ausreichende Beobachtungs-/Trainingscoverage beider Hemisphären, **nicht** zwingend einen A+B-Pass bei jeder trivialen Anfrage.
- DeepSeek-V4.1-Flash inspiriert optionale Body-native Mechanismen für projected/global context state, bounded replay, Layer-/Indexer-Reuse, conditional parameter memory und confidence-scheduled speculative decoding. Nichts davon wird blind in fremde pretrained Bodies gepatcht.
- MiniMax M3 inspiriert blockweise sparse Context-Auswahl und `thinking={disabled,adaptive,enabled}` als explizite adaptive Compute-Idee.
- GLM-5.3-Flash inspiriert hybride kompakte State-/linear-attention + sparse-global-attention Body-Kandidaten, gepoolte Index-States und mehrstufige Reasoning-Effort-Steuerung.
- V13 erhält daraus eine eigene `reasoning_effort`-/Wake-Policy, die nicht bloß Output-Tokens zählt, sondern JEF-Tiefe, B1/B2-Wake, Re-entry, Verify/Inquisition und Context-Retrieval budgetiert.

Die zentralen Korrekturen von v10.2:

- **[SUPERSEDED BY v10.12 REINDEX]** Die alte Formulierung „A, B und C sind drei Bodies“ gilt nicht mehr als Benennung. Kognitiv tragen B1_DETAIL, B2_GIST und C_JEF_SYSTEM die Hauptkompetenz; A bezeichnet jetzt die Ingress/Perception-Ebene.
- Die restlichen Systeme sind überwiegend kleine Heads, Policies, Zustände, Stores oder Offline-Lerner.
- Nicht jeder vorhandene Pfad läuft bei jeder Anfrage.
- Automatic Processing und Deliberation sind alternative bzw. ineinander überführbare Routen desselben Systems.
- C ist kein monolithischer Zentralrouter für alles.
- JEF besitzt getrennte Fast-/Language-/Focal-Systempfade; sie müssen nicht ein einzelner Backbone mit drei Modi sein.
- Age verändert Routenrechte, Scaffold-Abhängigkeit, Plastizität und Autonomie; Age ist kein normaler Feature-Unlock.
- Lernen läuft parallel bzw. zeitversetzt und darf sichtbaren Output niemals blockieren.
- Häufig erfolgreiche bewusste Routinen dürfen prozeduralisiert werden; bei Fehler/Neuheit dürfen automatisierte Routinen wieder in Deliberation aufbrechen.
- `executive_state` wird durch einen winzigen ereignisgetriebenen Updater frisch gehalten; ein vollständiger C-Forward ist dafür nicht Pflicht.
- Skill-, JEF_FAST_POLICY- und Salience-Pfade konkurrieren parallel statt seriell durch einen JEF-Pflichtknoten zu laufen.
- Callosum-Alignment richtet **Message-Subspaces** aus, nicht die privaten A/B-Repräsentationen; Spezialisierung muss erhalten bleiben.
- Scaffold-Lernen enthält kontrollierte Exploration und Counterfactuals, nicht nur Imitation.
- Lernmodulatoren sind zielabhängig: Faktenlernen, Routing, Skills und World-Learning verwenden unterschiedliche Signalgewichte.
- Ein Runtime-Scheduler kann User-, Tool-, Timer-, Idle-, Replay- und Goal-Events wecken; ein unabhängiger Response Governor erzwingt finite Antwort.

v10.12 ersetzt die ältere Benennungslogik, nicht die darin enthaltenen Mechanismen. Wo ältere Dateien technisch konkretere, widerspruchsfreie Details enthalten, bleiben sie Forschungsquelle; **v10.12 ist der Architektur-Canon**.

## 0.X [LOCKED] Neue Ebenen-Namensgebung — Buchstaben gehören ab jetzt den Makro-Ebenen

Die bisherige Benennung war inzwischen selbst eine Fehlerquelle: `A` und `B` bezeichneten die beiden Hemisphären, obwohl davor bereits Wahrnehmungs-/Teacher-/Projector-Schichten und danach JEF-/Output-Schichten existieren. v10.12 trennt **Makro-Ebene** und **Organ**.

```text
WORLD / HUMAN
    ↕
A-PLANE  = INGRESS / PERCEPTION / SENSOR INTERFACE
    ↕
B-PLANE  = COGNITIVE SPLIT-BRAIN CORE
    ↕
C-PLANE  = JEF / EXECUTIVE / REPORT / ACTION
    ↕
EGRESS / EFFECTORS
    ↕
WORLD

quer durch alles:
ATTENTION/Gain • Memory/Self/World • Learning • Age • Provenance/Rules • Runtime
```

### Legacy-Alias-Regel

Historische Abschnitte dieses Dokuments dürfen weiterhin die alten Namen tragen. Ab v10.12 gilt semantisch:

```text
legacy A / Detail  → B1_DETAIL
legacy B / Gist    → B2_GIST
legacy C / Judge   → C_JEF_SYSTEM
```

**Neue Implementierung und neue Diagramme dürfen die nackten Namen `A=Detail` und `B=Gist` nicht mehr verwenden.** So bleibt `A` frei für die echte vorgelagerte Input-/Perception-Ebene.

---

# 0Y. Kanonische Makro-Topologie v10.12

## A-PLANE — Ingress / Perception / „das Auge/Ohr bauen“

A ist die Ebene, die Weltzustände überhaupt in lernbare, zeitlich/source-gebundene Signale verwandelt. Sie ist **nicht** bloß ein Encoder-Modell.

```text
A0  Source/Physical Transducer
A1  Chunk / Tile / Frame / Token / Segment Builder
A2  Frozen Semantic Teacher Lane      [optional, Age-0 Lab]
A3  Student Projector / Resampler     [V13-owned, learnable]
A4  Perceptual Attention / Salience Proposal
A5  PerceptPacket + Source/Clock Binding
```

### A0 — Physical/Source Transducer

Macht Rohdaten handhabbar, möglichst semantisch arm:

- Text: Source spans + native tokenizable bytes/string,
- Bild: resize/normalize + tiles/patches,
- Audio: frames/codec/features + timestamps,
- Video: frame/time/event chunks,
- Tool/API: typed structured result,
- Body: sensor time series.

A0 darf dauerhaft existieren. Ein Gehirn „lernt“ nicht weg, dass Pixel/Schall erst physisch in Signale gewandelt werden müssen.

### A1 — Segmentation / Boundary Layer

A1 bestimmt **wo** eine Erfahrung aufgeteilt wird, nicht **was sie bedeutet**. Regeln:

- SourceRef bleibt an jedem Chunk,
- mehrere Granularitäten gleichzeitig erlaubt,
- Detail-Reentry kann höher aufgelöste Chunks nachfordern,
- Boundary-Policy kann später lernen,
- Teacher darf Boundary-Vorschläge liefern, aber Raw-Source nie ersetzen.

Gemma 4 12B Unified zeigt einen späteren möglichen Endpunkt: statt schwerer multimodaler Encoder werden Roh-Patches bzw. Audio über leichte Projektionen direkt in den Backbone eingespeist. Für V13 Age 0 ist das **Zielrichtung**, nicht Startvoraussetzung.

### A2 — Frozen Semantic Teacher Lane

Das „gute Auge/Ohr“ im Labor:

- VLM/ASR/Audio/API/anderes Modell,
- bleibt provenance-markiert,
- stop-gradient/frozen in Age 0,
- erzeugt Caption/OCR/Regions/Transcript/semantic features,
- ist **Teacher-Interpretation, nicht REAL**.

A2 soll später teilweise/komplett überflüssig werden, wenn A3+B-Core die Raw-Lane selbst ausreichend versteht.

### A3 — Student Projector / Resampler

Der eigentliche lernende Übergang vom neuen Sinneskanal in V13:

```text
A0/A1 raw chunks
      ↓
A3 learnable projection / resampling / compact latent
      ↓
B1 Detail / B2 Gist / C-JEF views
```

A3 darf zunächst durch A2-Targets, Reconstruction, Cross-modal pairs und reale Outcomes lernen. **A3 gehört V13; A2 nicht.**

### A4 — Perceptual Attention / Salience Proposal

A4 ist frühe Aufmerksamkeitsselektion vor dem Split-Brain:

- welche Bildregion/Audiozeit/Textspan ist vermutlich relevant,
- was muss high-res nachgeladen werden,
- was ist neu/auffällig,
- welche Chunks dürfen vorerst kalt bleiben.

A4 darf nie die einzige Wahrheitsquelle sein. Ein unterdrückter Chunk bleibt über SourceRef nachladbar.

### A5 — PerceptPacket

A5 bündelt alle Views derselben Weltquelle, sodass B/C nicht Teacher, Raw und eigene Interpretation verwechseln:

```text
PerceptPacket {
  event_id / clock
  modality
  raw_source_ref
  chunks / boundaries
  student_latents
  teacher_view?          // tagged external scaffold
  salience_proposals
  provisional_or_final
  provenance
}
```

---

## B-PLANE — Split-Brain Cognitive Core

B ist die eigentliche große kognitive Verarbeitung. Die früheren Hemisphären A/B werden hier zu B1/B2.

```text
B1  DETAIL / FINE HEMISPHERE
B2  GIST / COARSE HEMISPHERE
B3  CORPUS CALLOSUM / MESSAGE SPACE
B4  DISTRIBUTED STATE + MULTI-SLOT WORKSPACE GATEWAY
B5  BRAIN SUPPORT INTERFACES → Memory / World / Self / Inquisition
```

### B1 — Detail/Fine

Legacy `B1/Detail`. Kurze Integrationsfenster, Literalität, Code, Zahlen, lokale Unterschiede, exact-source reentry.

### B2 — Gist/Coarse

Legacy `B2/Gist`. Adaptive Mehrtoken-/Phrase-/Event-Spans, globale Relationen, Diskurs-/Planstruktur, länger haltende Gist-Slots.

### B3 — Callosum

Direkte B1↔B2-Kommunikation über Latent/Control/Exact/Symbolic Channels. JEF ist **nicht** die einzige Brücke.

### B4 — Distributed State / Workspace Gateway

Kein „drittes Modell“, sondern Multi-Slot-State mit SourceBinding, Zeitskala, Confidence, Hypothesis/Fact-Status und Admission-Regeln.

### B5 — Support Interfaces

B1/B2 greifen auf Memory, World Model, Self Model, Skills, Inquisition und Fast-Forward zu. Diese Systeme sind **querliegende Fabrics/States**, keine neuen Hemisphären.

---

## C-PLANE — JEF / Executive / Report / Action

C ist **kein einzelnes LLM**, sondern die körper-/handlungsnahe Executive-Seite des Systems.

```text
C0  JEF System Shell / permissions / interface
C1  Executive State + private KV + Broadcast Cache
C2  Structured Language/Control Organ     [Needle-class candidate]
C3  Tiny Free-Language / Report Organ     [separate baseline]
C4  Focal Loop / Coalition Binder
C5  Action Gate + Report Broker
C6  Egress Port Manager
C7  Attached Effectors / Decoders         [speech/image/UI/motor/...]
```

### C1 — Executive State

Hält Goal, Constraints, aktuelle Action, relevante Offers, Body/Resource-State, offene Fragen und JEF continuity. Native KV bleibt privat; B1/B2 erhalten trainierte Broadcast-Pakete.

### C2 — Structured Language/Control Organ

Needle-3-class ist hier ein sehr passender Kandidat: 29–121M, 2–20 deploybare Tiefen, Tool Calling, Extraction, Embeddings, grammar-constrained Outputs und Confidence; gleichzeitig opfert Needle bewusst General-Chat-Kapazität. Genau deshalb ist es eher **C2** als vollständiges JEF.

Aufgaben:

- User-Intent/Constraints → typed JEF packet,
- Tool-/Action-Schema,
- Memory/Retrieval key,
- Route-/Wake-Vorschlag,
- kurze strukturierte Antwort,
- Confidence / abstain / escalation.

### C3 — Tiny Free-Language / Report Organ

C3 ist bewusst **separat** von C2, bis ein Experiment zeigt, dass C2 diese Funktion zuverlässig mitlernen kann.

Aufgaben:

- `hi`, `hallo`, kurze soziale Antworten,
- kurze Umformulierungen,
- sprachliche Oberfläche eines bereits grounded Intent/Plans,
- minimale inner-speech/report continuity.

**Boot-Größenklasse:** grob 50–150M aktive Parameter als Ziel, nicht 0.5–1B nur weil das Modell existiert. `SmolLM2-135M-Instruct` ist eine einfache Apache-2.0-Referenzbaseline, aber primär Englisch und qualitativ begrenzt; daher nur Benchmark, nicht Canon-Modell.

Alternativen:

- `FunctionGemma 270M` eignet sich stärker für function calling als freie Konversation und ist deshalb eher C2-Konkurrent als C3.
- `T5Gemma 2 270M-270M` ist ein echtes multimodales Encoder-Decoder-Forschungsmodell und kann als Lab-/Teacher-Referenz helfen, ist mit ~1.57 GB Model-Datei aber kein guter dauerresidenter Redmi-C3-Kern.

Research-Refs für diese Kandidaten: Google Gemma 4 Model Card/Developer Guide; Google T5Gemma 2 270M-270M Model Card; Cactus Compute Needle 3 Model Card/Repository; HuggingFaceTB SmolLM2-135M-Instruct Model Card.

### C2↔C3 Lernfrage

```text
C2 Needle-like structured control
        ↕ shared JEF state / teacher comparisons
C3 tiny free-language
```

Age 0 testet drei Varianten:

1. C2 + C3 getrennt,
2. C2 versucht kurze Sprache selbst,
3. C3 übernimmt zusätzlich einfache control/report transforms.

**Nichts wird gestrichen, bevor Parity/Latency/Retention zeigen, dass zwei Organe wirklich redundant sind.**

### C4 — Focal Loop / Coalition Binder

C4 bindet JEF-State mit ausgewählten B1/B2/Memory/World/Self-Inhalten in die begrenzte fokale Koalition. Das ist der flexible, bewusstseinsnahe Deliberationspfad; nicht alles muss dort landen.

### C5 — Action Gate / Report Broker

C5 wählt mentale/externe Aktionen und besitzt den einen autorisierten äußeren Intent-Stream. B1/B2/C2/C3 dürfen Kandidaten liefern; C5 entscheidet nicht allein über Wahrheit, sondern über Ausführung unter Rules/Permissions.

### C6/C7 — Egress / Effectors

Output ist ebenfalls modular:

```text
C5 intent
  ↓
C6 egress schema / adapter
  ↓
C7 physical renderer/effector
  ├─ text token decode / exact render
  ├─ speech codec/TTS/vocoder
  ├─ image/visual renderer
  ├─ UI/tool executor
  └─ motor adapter
```

Needle kann Tool-Schemas in C2 erzeugen, ersetzt aber nicht automatisch Speech-/Image-/Motor-Renderer.

---

# 0Z. Querliegende Fabrics — nicht in A→B→C zwängen

Viele bisher „fehlend“ wirkende Teile waren vorhanden, aber schlecht eingeordnet. Sie werden ab v10.12 **nicht als zusätzliche serielle Layer**, sondern als Fabrics geführt.

## F1 — Attention / Gain / Admission Fabric

Aufmerksamkeit existiert auf mehreren Ebenen:

```text
F1a Perceptual attention    A4: Regionen/Frames/Spans
F1b Native body attention  B1/B2 intern, unverändert pretrained
F1c Inter-body gain        B3/B4: welche Message/Offer wird verstärkt
F1d Workspace admission    was wird fokal/global verfügbar
F1e Action attention       C5: welche Handlung/Report bekommt Authority
```

### Attention-Regeln [CANON]

1. **Attention ≠ Truth.** Verstärkung macht einen Inhalt nicht wahr.
2. **Attention ≠ Learning.** Aktivität erzeugt Eligibility; persistentes Lernen braucht Error+Modulator+Permission.
3. **Bottom-up darf Top-down unterbrechen.** Neuheit, Konflikt, Gefahr und starke Prediction Error dürfen JEF-Fokus interrupten.
4. **Top-down darf Resolution anfordern.** JEF/B2-Gist kann B1/A-Plane um High-Res/Exact Source bitten.
5. **Exact/Source bleibt recoverable.** Kompression darf wichtige SourceRefs nicht still vernichten.
6. **Teacher-Lane bekommt kein Sonderrecht.** A2 kann Attention-Vorschläge liefern, aber nicht Raw/World überschreiben.
7. **Budgetiert statt global.** Patch/Frame/Token/KV/Workspace-Budget ist pro Event/Body begrenzt und messbar.
8. **Age 0 ist konservativ.** Attention/Gain-Regeln starten scaffolded; learned Attention läuft zunächst Shadow.
9. **Private Body Attention bleibt privat.** V13-Metaattention patcht nicht blind native Transformer/MoE-Attention.
10. **Attention-Telemetrie wird geloggt, nicht alles gespeichert.** Sparse Micro-Traces online, detaillierte Traces selektiv.

## F2 — Salience / Interrupt Fabric

Neuheit, Konflikt, Überraschung, Goal-Violation, wichtige Umwelt-/User-Ereignisse. F2 kann A4, B1/B2, C4 oder C5 aufwecken.

## F3 — Memory / Self / World Fabric

Exact/Provenance, Fast Episodic, Semantic/Procedural Staging, Self Model, Body Schema, World Model, Fast Forward. Diese State-Systeme sind von A/B/C les-/beschreibbar unter Permissions/Admission.

## F4 — Learning / Plasticity Fabric

Eligibility, lokale Prediction-/JEPA-Errors, typisierte Neuromodulatoren, Metaplasticity, Homeostasis, Replay, Dream, Consolidation, Regression Shield. **JEF, B1/B2 und Student-Ports lernen unterschiedlich, aber aus derselben Experience-ID.**

## F5 — Age / Human-Control Fabric

System Stage 0–5, capability stages, user_stage_cap, learning mode `RECORD_ONLY|SHADOW_UPDATE|APPROVED_COMMIT`, Teacher reliance und Rechte für Self-Edit/Tools/Initiative/Plasticity.

## F6 — Provenance / Rules / Safety Fabric

Source IDs, Teacher/Self/Human/World-Trennung, Hard Rules, Permissions, Action Safety, Delete/Unlearning Lineage.

## F7 — Runtime / Resource Fabric

Scheduler, Response Governor, RAM/thermal/body residency, observer scheduling, cache/KV policy, speculative decode as serving-only optimization.

---

# 0W. Was der Gesamtgraph jetzt wirklich ist

```text
                 ┌──────────── WORLD / HUMAN ────────────┐
                 │                                       │
                 ▼                                       ▲
        ┌─────────────────┐                     ┌─────────────────┐
        │ A-PLANE INGRESS │                     │ C6/C7 EGRESS    │
        │ A0..A5          │                     │ render/effect   │
        └────────┬────────┘                     └────────▲────────┘
                 │ PerceptPacket                          │ ActionIntent
                 ▼                                        │
        ┌───────────────────────────────────────┐          │
        │ B-PLANE SPLIT-BRAIN                  │          │
        │ B1 Detail ↔ B3 Callosum ↔ B2 Gist  │          │
        │       ↘ B4 Workspace/State ↙        │          │
        └───────────────┬───────────────────────┘          │
                        ↕ Offers / Queries                  │
        ┌───────────────────────────────────────┐          │
        │ C-PLANE JEF                          │          │
        │ C1 state/KV  C2 Needle-class        │          │
        │ C3 tiny LM   C4 focal loop          │          │
        │ C5 action/report broker ─────────────┼──────────┘
        └───────────────────────────────────────┘

  F1 Attention/Gain   F2 Salience   F3 Memory/Self/World
  F4 Learning         F5 Age/Human  F6 Provenance/Rules
  F7 Runtime/Resources          span alle Ebenen
```

Der Pfeil A→B→C beschreibt nur die **grobe Welt→Kognition→Handlung-Richtung**. Reale Laufzeit ist rekurrent:

```text
C query → B re-entry → A high-res source restore → B update → C action
World outcome → A → B/JEF → F4 learning → spätere Route
```

# 0P. Layered Mini-Blueprints — Parameter, Kommunikation und Lernen getrennt sichtbar machen [v10.13 CANON]

Diese Sektion ist **kein neuer zusätzlicher Mechanismus**. Sie legt die bestehende Architektur in mehreren übereinanderliegenden Blueprints offen, damit später experimentiert werden kann, **wo**, **wie stark** und **über welche Brücke** gelernt wird.

Ziel:

```text
Layer 1  = Welche Organe gibt es?
Layer 2  = Wie reden sie miteinander?
Layer 3  = Welche lokalen Selbstschleifen existieren?
Layer 4  = Welche Cross-Learning-Pfade existieren?
Layer 5  = Welche großen rekurrenten Loops entstehen daraus?
Layer 6  = Welche globalen Bewertungs-/Modulationssignale beeinflussen Updates?
Layer 7  = Wie verändert Age/Human Control die gleichen Pfade?
Layer 8  = Wie laufen Replay/Dream/Consolidation?
Layer 9  = Welche Runtime-/Attention-/Cache-Optimierungen sitzen darunter?
```

Wichtig: **Ein Kommunikationspfad ist nicht automatisch ein Lernpfad.** Ein Modul darf etwas lesen, ohne davon persistente Gewichte zu verändern.

---

## 0P.1 Parameter-Typen — damit wir später wissen, was wir anfassen dürfen

Jeder Parameter bekommt zusätzlich zu seinem Namen einen Typ:

```text
[LOCKED]    Architekturgesetz; nicht still durch Tuning verändern
[USER]      explizite Human-Control-Grenze
[BOOT]      Startwert/Heuristik; bewusst nur Guess
[TUNE]      manuell/experimentell veränderbarer Knob
[LEARNED]   darf durch validiertes Lernen angepasst werden
[MEASURED]  nur gemessener Zustand; nicht direkt optimieren
[RESEARCH]  Kandidat; kann komplett scheitern/wegfallen
```

Für sehr viele Größen gilt gleichzeitig z. B.:

```text
initial value = [BOOT]
späterer Wert = [LEARNED]
harter Bereich = [USER] oder [LOCKED]
```

---

## 0P.2 Universelles PathSpec — jeder Pfeil bekommt eigene Regler

Jeder relevante Pfad zwischen zwei Komponenten erhält logisch ein `PathSpec`. Nicht jeder Parameter muss im ersten Code existieren; das Schema verhindert aber, dass wir später unbemerkt Kommunikation, Lernen und Autorität vermischen.

```text
PathSpec {
  enabled                 [TUNE]
  mode                    [TUNE]     OFF | OBSERVE | SHADOW | ACTIVE

  read_gain               [TUNE/LEARNED]
  write_gain              [TUNE/LEARNED]
  route_gain              [TUNE/LEARNED]
  attention_gain          [TUNE/LEARNED]
  confidence              [MEASURED]
  trust                   [LEARNED]

  learn_gain              [TUNE/LEARNED]
  eligibility_gain        [TUNE]
  eligibility_decay       [TUNE]
  local_error_gain        [TUNE]
  peer_error_gain         [TUNE]
  teacher_gain            [TUNE]
  human_gain              [TUNE]
  world_outcome_gain      [TUNE]

  update_threshold        [TUNE]
  max_update_norm         [USER/TUNE]
  plasticity_cap          [USER/TUNE]
  replay_priority         [LEARNED]
  consolidation_threshold [TUNE]
  rollback_sensitivity    [TUNE]

  sample_rate             [TUNE]
  shadow_ratio            [TUNE]
  cooldown                [TUNE]
  latency_budget          [TUNE]
  memory_budget           [TUNE]
  age_multiplier          [LEARNED/TUNE]
}
```

**Startregel:** Fast alle `learn_gain`-Werte beginnen klein oder `SHADOW`; es gibt absichtlich **keine** harte Behauptung, welcher Cross-Learning-Pfad am Ende stark sein soll.

## IH-H5 — KnobSpec: 0..1 ist NICHT automatisch Wahrscheinlichkeit [MUST]

v10.15 benutzt viele normalisierte Werte. Vor Implementierung bekommt jeder Regler einen Typ:

```text
KnobKind =
  AUTHORITY
  MIX_WEIGHT
  PRIOR
  PROBABILITY
  THRESHOLD
  BUDGET_FRACTION
  BOOLEAN
  COUNT
  BYTES
  DURATION_MS
  RATE_HZ
  LEARNING_RATE
  DECAY
  TEMPERATURE
```

Schema:

```text
KnobSpec {
  id
  kind
  value
  unit
  min
  max
  owner
  stage_cap?
  user_cap?
  learned_allowed
  clamp_policy
  description
}
```

Beispiel:

```text
B3.latent_mix = 0.45
```

ist ohne `kind` **nicht** implementierbar: Es könnte Gewicht, Wahrscheinlichkeit oder Authority bedeuten. Work darf das nicht raten.

---

## 0P.3 Werte-Konvention — nicht jedes Experiment braucht neue Einheiten

Wo möglich werden Knobs zunächst normiert:

```text
0.0 = aus / keine Authority / kein Einfluss
0.25 = schwach
0.50 = mittel
0.75 = stark
1.0 = maximal innerhalb des aktuellen User-/Age-Caps
```

Learning Rates bleiben log-skaliert und werden **nicht** in 0..1 gepresst:

```text
head/projector lr      grob 1e-5 .. 1e-2  [RESEARCH]
adapter/delta lr       grob 1e-6 .. 1e-3  [RESEARCH]
base-weight lr         deutlich kleiner / oft OFF [RESEARCH]
```

Das sind keine empfohlenen Endwerte, nur ein Suchraum. Auf Redmi entscheidet Messung, welche Updates überhaupt praktikabel sind.

## 0P.4 Drei Startprofile statt eines falschen "richtigen" Lernsettings

Für viele Pfade sollen Tests mindestens drei Profile anbieten:

```text
CONSERVATIVE
  learn_gain low
  shadow_ratio high
  teacher/human gating high
  max_update_norm low
  replay/retention high

BALANCED
  learn_gain medium
  shadow_ratio medium
  teacher dependence medium
  moderate update caps

EXPLORATORY
  learn_gain higher
  exploration higher
  teacher dropout higher
  still regression-gated
```

Age 0 beginnt meist `CONSERVATIVE`, aber einzelne ungefährliche Heads/Projectors dürfen bewusst in `BALANCED` oder experimentell `EXPLORATORY` getestet werden.

---

# LAYER 1 — Anatomie / Module: A, B und C separat

## L1-A. A-PLANE — Ingress / Perception

### A0 — Physical / Raw Transducer

Rolle: rohe Welt in stabile numerische Daten übersetzen, **ohne Semantik vorzutäuschen**.

Parameter:

```text
A0.raw_scale                 [BOOT/TUNE]
A0.sample_rate               [BOOT/TUNE]
A0.frame_stride              [BOOT/TUNE]
A0.channel_norm              [BOOT/TUNE]
A0.dynamic_range             [BOOT/TUNE]
A0.raw_dropout               [RESEARCH]
A0.latency_budget            [USER/TUNE]
A0.frozen                    [LOCKED early=true]
```

A0 lernt Age 0 standardmäßig nicht.

### A1 — Segmentation / Boundary

Rolle: Bildpatches, Audioframes, Textspans, Events oder Sensorblöcke definieren.

```text
A1.segment_size              [BOOT/TUNE]
A1.segment_overlap           [BOOT/TUNE]
A1.boundary_threshold        [TUNE/LEARNED later]
A1.max_segments              [USER/TUNE]
A1.adaptive_segmentation_mix [RESEARCH]
A1.event_boundary_gain       [TUNE/LEARNED]
A1.teacher_boundary_mix      [TUNE]
A1.student_boundary_mix      [TUNE]
```

### A2 — Frozen Semantic Teacher Lane

Rolle: externe Interpretation als **Referenz**, nicht als Wahrheit.

```text
A2.teacher_enabled           [USER/TUNE]
A2.teacher_use_prob          [BOOT/TUNE]
A2.teacher_trust             [TUNE]
A2.teacher_delay             [MEASURED]
A2.teacher_dropout           [TUNE]
A2.teacher_target_mix        [TUNE]
A2.teacher_disagreement_log  [LOCKED=true]
A2.teacher_can_write_facts   [LOCKED=false]
```

`teacher_dropout` ist wichtig: Der Student soll nicht lernen, dass Teacher immer vorhanden ist.

### A3 — V13 Student Projector / Resampler

Rolle: Raw-Daten in V13-native Repräsentationen überführen.

```text
A3.projector_lr              [BOOT/TUNE]
A3.raw_alignment_weight      [BOOT/TUNE]
A3.teacher_alignment_weight  [BOOT/TUNE]
A3.reconstruction_weight     [BOOT/TUNE]
A3.cross_modal_weight        [RESEARCH]
A3.world_outcome_weight      [RESEARCH]
A3.student_only_probe_rate   [TUNE]
A3.latent_bottleneck_size    [RESEARCH]
A3.update_norm_cap           [USER/TUNE]
```

### A4 — Perceptual Attention / Salience Proposal

```text
A4.bottom_up_gain            [BOOT/TUNE]
A4.top_down_gain             [BOOT/TUNE]
A4.novelty_gain              [TUNE/LEARNED]
A4.motion_change_gain        [TUNE/LEARNED]
A4.teacher_bias_cap          [USER/TUNE]
A4.reentry_threshold         [TUNE/LEARNED]
A4.attention_temperature     [TUNE]
A4.max_highres_regions       [USER/TUNE]
```

### A5 — PerceptPacket / Source Binding

A5 ist primär Schema/State, nicht eigenes großes Modell.

```text
A5.source_ref_required       [LOCKED=true]
A5.clock_binding_required    [LOCKED=true]
A5.packet_compression        [TUNE]
A5.exact_fallback_required   [LOCKED=true where possible]
A5.confidence_floor          [TUNE]
A5.max_packet_bytes          [TUNE]
```

---

## L1-B. B-PLANE — Split-Brain Core

### B1 — Detail / Fine Body

```text
B1.fine_span_target          [BOOT/TUNE]
B1.detail_gain               [BOOT/TUNE]
B1.literal_gain              [BOOT/TUNE]
B1.exact_request_threshold   [TUNE/LEARNED]
B1.local_jepa_weight         [BOOT/TUNE]
B1.offer_threshold           [TUNE/LEARNED]
B1.offer_budget              [USER/TUNE]
B1.reentry_gain              [TUNE/LEARNED]
B1.adapter_lr                [BOOT/TUNE]
B1.body_lr_scale             [BOOT/TUNE]
B1.plasticity                [LEARNED/TUNE]
B1.retention_priority        [LEARNED]
```

### B2 — Gist / Coarse Body

```text
B2.gist_span_target          [BOOT/TUNE]
B2.boundary_sensitivity      [BOOT/TUNE]
B2.global_context_gain       [BOOT/TUNE]
B2.compression_target        [BOOT/TUNE]
B2.local_jepa_weight         [BOOT/TUNE]
B2.offer_threshold           [TUNE/LEARNED]
B2.offer_budget              [USER/TUNE]
B2.coarse_to_fine_threshold  [TUNE/LEARNED]
B2.adapter_lr                [BOOT/TUNE]
B2.body_lr_scale             [BOOT/TUNE]
B2.plasticity                [LEARNED/TUNE]
B2.retention_priority        [LEARNED]
```

### B3 — Callosum / Shared Message Space

```text
B3.latent_mix                [RESEARCH/TUNE]
B3.exact_mix                 [BOOT/TUNE]
B3.control_mix               [BOOT/TUNE]
B3.symbolic_mix              [RESEARCH/TUNE]
B3.no_message_prior          [BOOT/TUNE]
B3.message_budget            [USER/TUNE]
B3.message_temperature       [TUNE]
B3.receiver_gate             [LEARNED]
B3.cross_jepa_weight         [BOOT/TUNE]
B3.alignment_strength        [BOOT/TUNE]
B3.private_state_protection  [LOCKED/TUNE]
B3.anti_collapse_weight      [BOOT/TUNE]
B3.receiver_ood_threshold    [TUNE]
B3.message_replay_priority   [LEARNED]
```

### B4 — Distributed State / Workspace Gateway

```text
B4.slot_count                [RESEARCH]
B4.slot_width                [RESEARCH]
B4.slot_decay                [TUNE/LEARNED]
B4.admission_threshold       [TUNE/LEARNED]
B4.refresh_budget            [USER/TUNE]
B4.lock_strength             [TUNE]
B4.bind_strength             [TUNE/LEARNED]
B4.conflict_slot_gain        [TUNE]
B4.source_binding_strength   [LOCKED high]
B4.focal_capacity            [RESEARCH/TUNE]
```

### B5 — Support Interfaces

Keine einzelne Komponente; umfasst Memory, World, Self, Inquisition.

```text
B5.memory_read_gain          [TUNE/LEARNED]
B5.memory_write_gain         [TUNE/LEARNED]
B5.world_query_gain          [TUNE/LEARNED]
B5.self_model_gain           [TUNE/LEARNED]
B5.inquisition_gain          [TUNE/LEARNED]
B5.exact_restore_gain        [TUNE/LEARNED]
```

---

## L1-C. C-PLANE — JEF / Executive / Report / Action

### C1 — Executive State / private KV / Broadcast Cache

```text
C1.goal_persistence          [BOOT/TUNE]
C1.constraint_persistence    [BOOT/TUNE]
C1.state_refresh_rate        [TUNE/LEARNED]
C1.state_forget_rate         [TUNE/LEARNED]
C1.kv_export_rate            [TUNE]
C1.broadcast_compression     [TUNE/LEARNED]
C1.broadcast_budget          [USER/TUNE]
C1.self_state_gain           [TUNE]
C1.body_state_gain           [TUNE]
C1.offer_integration_gain    [TUNE/LEARNED]
```

### C2 — Structured Language / Control Organ (Needle-class candidate)

```text
C2.intent_extract_gain       [BOOT/TUNE]
C2.tool_call_gain            [BOOT/TUNE]
C2.structured_output_gain    [BOOT/TUNE]
C2.embedding_gain            [BOOT/TUNE]
C2.route_gain                [TUNE/LEARNED]
C2.confidence_threshold      [TUNE]
C2.confidence_calibration_lr [TUNE]
C2.control_lr                [BOOT/TUNE]
C2.depth_rung                [RESEARCH/TUNE]
C2.max_control_tokens        [USER/TUNE]
```

### C3 — Tiny Free-Language / Report Organ

```text
C3.language_budget           [USER/TUNE]
C3.free_language_gain        [BOOT/TUNE]
C3.report_style_lr           [TUNE]
C3.short_answer_threshold    [TUNE/LEARNED]
C3.self_candidate_first      [LOCKED=true]
C3.teacher_imitation_weight  [BOOT/TUNE]
C3.human_edit_weight         [BOOT/TUNE]
C3.language_lr               [BOOT/TUNE]
C3.factual_self_limit        [USER/TUNE]
```

### C4 — Focal Loop / Coalition Binder

```text
C4.coalition_threshold       [TUNE/LEARNED]
C4.reasoning_effort          [LEARNED/TUNE]
C4.max_cycles                [USER/TUNE]
C4.disagreement_trigger      [TUNE]
C4.salience_trigger          [TUNE]
C4.body_reentry_budget       [USER/TUNE]
C4.memory_reentry_budget     [USER/TUNE]
C4.inquisition_depth         [TUNE/LEARNED]
C4.halting_gain              [LEARNED]
C4.focus_stability           [TUNE/LEARNED]
```

### C5 — Action Gate / Report Broker

```text
C5.action_temperature        [TUNE]
C5.action_confidence_floor   [TUNE]
C5.risk_gate                 [USER/TUNE]
C5.human_confirm_threshold   [USER]
C5.report_path_mix           [TUNE/LEARNED]
C5.corollary_strength        [BOOT/TUNE]
C5.action_reversibility_gain [TUNE]
C5.wait_vs_act_bias          [TUNE/LEARNED]
```

### C6/C7 — Egress / Effectors

```text
C6.port_select_gain          [TUNE/LEARNED]
C6.reference_teacher_use     [USER/TUNE]
C6.self_vs_teacher_compare   [LOCKED=true when teacher used]
C7.effector_confidence       [MEASURED]
C7.effector_latency_budget   [USER/TUNE]
C7.renderer_quality_target   [TUNE]
C7.motor_safety_gate         [USER]
```

---

# LAYER 2 — Kommunikation: Wer darf wen lesen, ohne automatisch zu lernen?

## L2.1 Kanonische Edge-Namen

```text
E_A5_B1_PERCEPT       A5 → B1   PerceptPacket fine-view
E_A5_B2_PERCEPT       A5 → B2   PerceptPacket gist-view
E_A5_C1_PERCEPT       A5 → C1   task/event summary

E_B1_B3_OFFER         B1 → B3   detail offer
E_B2_B3_OFFER         B2 → B3   gist offer
E_B3_B1_MESSAGE       B3 → B1   cross-body message
E_B3_B2_MESSAGE       B3 → B2   cross-body message

E_B1_C1_OFFER         B1 → C1   detail evidence/uncertainty
E_B2_C1_OFFER         B2 → C1   gist hypothesis/plan
E_C1_B1_QUERY         C1 → B1   targeted fine re-entry
E_C1_B2_QUERY         C1 → B2   targeted gist re-entry

E_B4_C4_FOCUS         B4 → C4   workspace candidate
E_C4_B4_GAIN          C4 → B4   focal gain/admission
E_C5_C7_ACTION        C5 → C7   selected external action
E_C5_B_COROLLARY      C5 → B*   copy of intended action

E_WORLD_A_OUTCOME     World → A outcome observation
E_OUTCOME_F4_MOD      Outcome → F4 typed modulators
```

Jede Edge besitzt ihr eigenes `PathSpec`. Dadurch kann z. B. `E_B1_C1_OFFER` aktiv kommunizieren, während `learn_gain=0` bleibt.

## L2.2 Kommunikations-Modi

```text
PASSIVE      lesen, nichts zurückschreiben
BIDIRECTIONAL beide Seiten dürfen antworten
FOCAL        nur bei Coalition/Attention aktiv
SHADOW       wird berechnet, beeinflusst Verhalten noch nicht
ACTIVE       beeinflusst Verhalten
```

Diese Modi gelten **zusätzlich** zum Lernmodus.

---

# LAYER 3 — Lokale Selbst-Lernschleifen innerhalb eines Moduls

## L3-A — Perception Student Loop

```text
Raw A0/A1
  ↓
A3 student representation
  ├─→ Reconstruction probe
  ├─→ Teacher alignment probe
  └─→ später World/Action outcome
          ↓
local error(s)
          ↓
A3 eligibility × plasticity
```

Parameter:

```text
L_A3_RECON.weight            [BOOT/TUNE]
L_A3_TEACHER.weight          [BOOT/TUNE]
L_A3_WORLD.weight            [RESEARCH]
L_A3_SELF_ONLY_PROBE.rate    [TUNE]
```

## L3-B1 — Detail Self-Prediction

```text
B1 state_t → predictor → detail_next_pred
actual/future grounded view → error
error × B1 eligibility → B1 candidate update
```

```text
L_B1_LOCAL.error_gain        [TUNE]
L_B1_LOCAL.replay_mix        [TUNE]
L_B1_LOCAL.update_gain       [BOOT/TUNE]
L_B1_LOCAL.baseweight_share  [RESEARCH]
```

## L3-B2 — Gist Self-Prediction

Wie B1, aber längere/komprimiertere Zeitskala.

```text
L_B2_LOCAL.error_gain        [TUNE]
L_B2_LOCAL.temporal_horizon  [BOOT/TUNE]
L_B2_LOCAL.replay_mix        [TUNE]
L_B2_LOCAL.update_gain       [BOOT/TUNE]
```

## L3-C — JEF Self-Control Loop

```text
state → route/action/report decision
          ↓
real outcome + human feedback + cost
          ↓
was JEF falsch eingeschätzt hat
          ↓
C1/C2/C4/C5 eligibility-specific update
```

```text
L_C_ROUTE.weight             [BOOT/TUNE]
L_C_WAKE.weight              [BOOT/TUNE]
L_C_HALT.weight              [BOOT/TUNE]
L_C_REPORT.weight            [BOOT/TUNE]
L_C_COST.weight              [TUNE]
L_C_CALIBRATION.weight       [TUNE]
```

## L3-B4 — Workspace Stability Loop

Workspace lernt **nicht primär Wissen**, sondern welche Informationen stabil gehalten, gebunden, ersetzt oder wiederhergestellt werden sollten.

```text
L_B4_ADMISSION.weight        [TUNE]
L_B4_REFRESH.weight          [TUNE]
L_B4_BINDING.weight          [TUNE]
L_B4_SOURCE_LOSS.weight      [LOCKED high]
```

---

# LAYER 4 — Cross-Learning: Module lernen voneinander, ohne identisch zu werden

## L4.1 Teacher → Student Perception

```text
A2 semantic teacher
      ↓ target/reference
A3 student projector
      ↓
B1/B2/JEF native use
```

**Nur A3/Core lernen; A2 bleibt frozen.**

```text
X_A2_A3.teacher_gain         [TUNE]
X_A2_A3.teacher_dropout      [TUNE]
X_A2_A3.independence_probe   [TUNE]
```

## L4.2 Detail ↔ Gist Cross-JEPA

```text
B1 private state ─→ B3 message ─→ B2 prediction target
B2 private state ─→ B3 message ─→ B1 prediction target
```

Nicht Ziel:

```text
B1 == B2
```

Ziel:

```text
B1 kann nützliche Detailinformation so exportieren,
dass B2 sie verwenden kann,
und umgekehrt.
```

```text
X_B1_B2.cross_error_gain     [BOOT/TUNE]
X_B1_B2.latent_share         [RESEARCH]
X_B1_B2.exact_share          [BOOT/TUNE]
X_B1_B2.diversity_protect    [LOCKED/TUNE]
X_B1_B2.role_retention       [MEASURED]
```

## L4.3 JEF → Brain Query Learning

JEF lernt, **wann und wie** eine Frage an Detail/Gist gestellt werden muss.

```text
X_C_B1.query_gain            [TUNE/LEARNED]
X_C_B2.query_gain            [TUNE/LEARNED]
X_C_B.query_cost_penalty     [TUNE]
X_C_B.missed_need_penalty    [TUNE]
X_C_B.unneeded_wake_penalty  [TUNE]
```

B1/B2 lernen parallel, auf JEF-Queries brauchbare Offers zu erzeugen.

## L4.4 Brain → JEF Offer Learning

```text
B1/B2 produce OFFER_PACKET
        ↓
JEF accepts / ignores / re-queries
        ↓
späteres Outcome
        ↓
Offer usefulness credit
```

```text
X_B_C.offer_usefulness_gain  [TUNE]
X_B_C.offer_spam_penalty     [TUNE]
X_B_C.offer_confidence_lr    [TUNE]
X_B_C.focal_accept_gain      [LEARNED]
```

## L4.5 Self Output ↔ Reference Teacher ↔ Human

```text
SELF_CANDIDATE zuerst
REFERENCE_CANDIDATE getrennt danach
HUMAN_DECISION / real outcome
        ↓
span-/decision-spezifischer Credit
```

```text
X_SELF_TEACHER.imitation_gain     [BOOT/TUNE]
X_SELF_TEACHER.disagreement_gain  [TUNE]
X_HUMAN_SELF.preference_gain      [USER/TUNE]
X_HUMAN_SPAN.correction_gain      [USER/TUNE]
X_TEACHER_FACT.truth_authority    [LOCKED=0 unless externally verified]
```

## L4.6 Action ↔ World ↔ World Model

```text
C5 ActionIntent
   ├─→ World
   └─→ Corollary Copy
World observation
   ↓
predicted vs actual
   ↓
FastForward / World-JEPA / JEF / relevant B paths
```

```text
X_ACTION_WORLD.forward_error_gain [BOOT/TUNE]
X_ACTION_WORLD.cost_gain          [TUNE]
X_ACTION_WORLD.causal_confidence  [LEARNED]
X_ACTION_WORLD.self_cause_gain    [TUNE]
```

## L4.7 Cross-Learning-Matrix — welcher Pfad lernt über welche Brücke?

| Quelle | Ziel | Brücke | Standard Age 0 | Was darf gelernt werden? |
|---|---|---|---|---|
| A2 Teacher | A3 Student | paired Raw/Teacher | SHADOW | Wahrnehmungsprojektion, nicht Teacher-Fakten |
| A3 Student | B1 Detail | PerceptPacket | ACTIVE read / low learn | bessere Fine-Repräsentation |
| A3 Student | B2 Gist | PerceptPacket | ACTIVE read / low learn | bessere Gist-Repräsentation |
| B1 Detail | B2 Gist | B3 Callosum | OBSERVE→SHADOW | brauchbare Cross-Message, nicht gleiche States |
| B2 Gist | B1 Detail | B3 Callosum | OBSERVE→SHADOW | globaler Constraint für Fine-Processing |
| B1/B2 | C1/C4 JEF | OFFER_PACKET | ACTIVE read | Offer-Nützlichkeit, Wake-/Focus-Policy |
| JEF | B1/B2 | Query/Re-entry | ACTIVE | wann/was nachfragen, Query-Format |
| Memory | B/JEF | Retrieval | ACTIVE read | Retrieval-/Cue-Policy, nicht automatisch Faktengewichte |
| C5 Action | World Model | Corollary+Outcome | ACTIVE | action-conditioned prediction |
| World Outcome | B/JEF/A3 | F4 Modulators | OBSERVE/SHADOW | lokaler Credit auf beteiligte Pfade |
| Teacher Output | C3/JEF | Reference Lane | SHADOW | Stil/Antwortstruktur/Entscheidungsbeispiele |
| Human Decision | C/B/A3 | Human Decision Packet | SHADOW/APPROVED | span-/route-spezifischer Credit |
| Dream | Policies/World | Replay/Dream gate | mostly SHADOW | Alternativen/Policies; nie direkte Faktautorität |

**Wichtig:** "ACTIVE read" heißt nicht "ACTIVE weight update". Diese Matrix beschreibt zwei getrennte Achsen: Informationsfluss und Lern-Autorität.

## L4.8 Kommunikation ohne Lernen — ausdrücklich erlaubte Fälle

Beispiele:

```text
B1 liefert JEF einen Detail-Offer
→ JEF nutzt ihn
→ keinerlei Weight Update notwendig

Teacher liefert Caption
→ A3 liest sie nur für Evaluation
→ learn_gain kann 0 bleiben

JEF fragt B2 nach globalem Plan
→ Query/Antwort beeinflussen Output
→ erst späteres Outcome entscheidet, ob ein Lerntrace nützlich ist
```

Das ist wichtig, damit V13 nicht aus jedem internen Signal sofort Training macht.

---

# LAYER 5 — Große rekurrente Loops: mehrere Module als ein lernendes System

## L5.1 Perception Understanding Loop

```text
World
→ A0/A1 Raw
→ A2 Teacher optional + A3 Student
→ B1/B2
→ B3/B4
→ JEF focal interpretation
→ targeted A re-entry
→ refined B state
```

Lernen kann dabei an A3, B1, B2, B3, B4 und JEF stattfinden — **aber jeweils mit eigenen Errors und Gates**.

## L5.2 Conscious/Focal Loop

```text
B1 offer + B2 offer + Memory + Self + World
           ↓
        B4 candidates
           ↓
      C4 focal coalition
           ↓
   query / verify / suppress / bind
           ↺
```

Parameter:

```text
LOOP_FOCAL.max_rounds        [USER/TUNE]
LOOP_FOCAL.accept_threshold  [TUNE/LEARNED]
LOOP_FOCAL.reentry_budget    [USER/TUNE]
LOOP_FOCAL.conflict_gain     [TUNE]
LOOP_FOCAL.reasoning_effort  [LEARNED/TUNE]
```

## L5.3 Action Loop

```text
Goal → C4/C5 → Action Gate
→ Fast Forward prediction
→ action
→ Corollary Copy
→ World outcome
→ F4 modulators
→ local eligibility updates
```

## L5.4 Second-Attempt Improvement Loop

```text
Attempt 1
→ experience record
→ human/world correction
→ Fast Episodic
→ optional Shadow Update
→ Attempt 2
→ compare retained constraints + corrected failure
```

Das ist ein eigener Benchmark, nicht nur Memory Recall.

## L5.5 Teacher Internalisation Loop

```text
Teacher on
→ student learns under paired Raw+Teacher
→ student-only shadow trials
→ teacher dropout ↑
→ retention test
→ teacher dependence ↓ if earned
```

```text
LOOP_TEACHER.dropout_curve   [TUNE]
LOOP_TEACHER.reliance        [LEARNED]
LOOP_TEACHER.raw_success     [MEASURED]
LOOP_TEACHER.removal_gate    [USER/TUNE]
```

## L5.6 Skill Proceduralisation Loop

```text
focal multi-step route
→ repeated successful traces
→ compact skill policy
→ shadow comparison
→ automatic route
→ novelty/failure can reopen focal route
```

---

# LAYER 6 — Global Outcome / Valuation / Neuromodulation

Kein einzelnes Reward-Signal. Stattdessen typisierte Modulatoren:

```text
M_truth        epistemische Evidenz / factual correction
M_utility      Task-/Handlungserfolg
M_surprise     prediction error / unexpected event
M_novelty      neue Domäne / neue Situation
M_uncertainty  epistemische/route Unsicherheit
M_social       Human feedback / preference
M_cost         latency / energy / body wakes / memory
M_safety       risk / rule / reversibility
M_retention    Regression / old-skill protection
M_teacher      Teacher usefulness, NICHT truth
M_world        external grounded outcome
```

Jeder Lernpfad besitzt eine **eigene Mischung**, z. B.:

```text
Update_B1 ≈ eligibility × local_error ×
            mix(M_truth, M_world, M_retention, M_uncertainty)

Update_C_route ≈ eligibility × route_error ×
                 mix(M_utility, M_cost, M_social, M_safety)

Update_A3 ≈ eligibility × percept_error ×
            mix(M_teacher, M_world, M_truth)
```

Die Mischgewichte sind **[BOOT/TUNE]**, später teilweise [LEARNED]. Kein globaler Reward darf alles übernehmen.

Generisches Schema:

```text
Δθ_i = base_lr_i
       × eligibility_i
       × mapped_error_i
       × modulation_i
       × plasticity_i
       × permission_i
       × clamp(max_update_norm_i)
```

---

# LAYER 7 — Age / Human Control als Multiplikator über denselben Graphen

Age baut **keine neuen Pfade**. Es verändert Authority, Plasticity, Teacher-Reliance, Loop-Tiefe und Initiative vorhandener Pfade.

## L7.1 globale Age-Kurven

```text
AGE.teacher_reliance_curve   [BOOT/TUNE]
AGE.raw_input_curve          [BOOT/TUNE]
AGE.autonomy_curve           [BOOT/TUNE]
AGE.plasticity_curve         [BOOT/TUNE]
AGE.dream_curve              [BOOT/TUNE]
AGE.self_edit_curve          [BOOT/TUNE]
AGE.tool_authority_curve     [BOOT/TUNE]
AGE.callosum_freedom_curve   [BOOT/TUNE]
AGE.focal_depth_curve        [BOOT/TUNE]
AGE.teacher_dropout_curve    [BOOT/TUNE]
AGE.structural_edit_curve    [USER/LOCKED ceiling]
```

## L7.2 Age 0 heißt nicht „kaum lernen“

Age 0 bedeutet:

```text
viel Human Control
viel Shadow
kleine reversible Updates
Teacher/reference oft verfügbar
Base-weight authority niedrig
Memory/Heads/Projectors dürfen deutlich schneller lernen
```

Die Lernstärke ist also **komponentenabhängig**, nicht global niedrig.

## L7.3 User-Hard-Caps

```text
AGE.user_stage_cap           [USER]
AGE.max_baseweight_plasticity[USER]
AGE.max_autonomous_action    [USER]
AGE.max_dream_write          [USER]
AGE.max_structural_edit      [USER]
```

Diese Werte kann das System nicht selbst erhöhen.

---

# LAYER 8 — Replay / Dream / Consolidation

## L8.1 Replay-Mixer

```text
REPLAY.real_episode_ratio        [BOOT/TUNE]
REPLAY.human_corrected_ratio     [BOOT/TUNE]
REPLAY.teacher_reference_ratio   [BOOT/TUNE]
REPLAY.failure_ratio             [BOOT/TUNE]
REPLAY.success_ratio             [BOOT/TUNE]
REPLAY.rare_event_ratio          [BOOT/TUNE]
REPLAY.old_retention_ratio       [BOOT/TUNE]
REPLAY.counterfactual_ratio      [BOOT/TUNE]
```

Nicht alle müssen zu 1 normiert sein; Scheduler kann mehrere Buckets kombinieren.

## L8.2 Dream

Dream = neue interne Kombinationen/Simulationen, **keine Faktenquelle**.

```text
DREAM.enabled                    [USER/TUNE]
DREAM.novelty                    [TUNE]
DREAM.depth                      [TUNE]
DREAM.counterfactual_strength    [TUNE]
DREAM.world_model_gain           [TUNE]
DREAM.skill_recombination_gain   [TUNE]
DREAM.fact_write_gain            [LOCKED=0 direct]
DREAM.policy_learning_gain       [TUNE]
DREAM.body_learning_gain         [USER/TUNE low early]
DREAM.validation_required        [LOCKED=true]
```

## L8.3 Sleep / Consolidation Phasen

```text
Sleep A: REAL REPLAY
→ echte Episoden / Korrekturen / Fehler

Sleep B: COUNTERFACTUAL / DREAM
→ alternative Routen / Szenarien / Skill-Kombinationen

Sleep C: HOMEOSTASIS
→ Normen / Router / dominante Pfade / tote Pfade / resource balance

Sleep D: CONSOLIDATION
→ nur validierte Tags/Deltas in langsamere Gewichte übernehmen
```

Parameter:

```text
SLEEP.phase_mix                  [TUNE]
SLEEP.max_minutes                [USER/TUNE]
SLEEP.thermal_limit              [USER]
SLEEP.merge_threshold            [TUNE]
SLEEP.retention_test_strength    [TUNE]
SLEEP.rollback_window            [USER/TUNE]
```

---

# LAYER 9 — Runtime-/Attention-/Cache-Optimierungen unter dem semantischen Graphen

Diese Layer dürfen den kognitiven Graphen **beschleunigen**, aber nicht still seine Semantik verändern.

## L9.1 Attention / Gain

```text
OPT.attn_perceptual_sparse       [RESEARCH]
OPT.attn_workspace_gain          [TUNE/LEARNED]
OPT.attn_block_sparse_native     [RESEARCH]
OPT.attn_hierarchical_index      [RESEARCH]
OPT.attn_pooled_index            [RESEARCH]
OPT.attn_reasoning_effort        [LEARNED/TUNE]
```

Regel: native Attention eines pretrained Body wird nicht blind ersetzt. Neue Mechanismen nur, wenn der Body/Runner sie real unterstützt oder sauber retrainiert wird.

## L9.2 Cache / State

```text
OPT.kv_keep_recent               [TUNE]
OPT.kv_compression               [RESEARCH/TUNE]
OPT.kv_restore_policy            [TUNE/LEARNED]
OPT.bounded_cache_replay         [RESEARCH]
OPT.projected_global_context     [RESEARCH]
OPT.warm_state_budget            [USER/TUNE]
OPT.exact_source_coldstore       [LOCKED available]
```

## L9.3 Mobile Scheduling

```text
OPT.observer_schedule =
  ALWAYS_BOTH_ASYNC |
  B1_THEN_B2 |
  B2_THEN_B1 |
  JEF_FIRST_THEN_BOTH |
  SAMPLED |
  ON_DEMAND

OPT.body_residency_policy        [TUNE/LEARNED]
OPT.prefetch_gain                [TUNE/LEARNED]
OPT.offload_threshold            [TUNE]
OPT.thermal_backoff              [USER/TUNE]
OPT.max_hot_models               [USER/TUNE]
```

## L9.4 Decode / Serving

```text
OPT.speculative_decode           [RESEARCH]
OPT.draft_depth                  [TUNE]
OPT.verify_schedule              [TUNE/LEARNED]
OPT.grammar_decode               [TUNE]
OPT.direct_exact_renderer        [BOOT]
```

Serving-Optimierungen verändern keine Evidence- oder Learning-Provenance.

## L9.5 Update-Effizienz

```text
OPT.train_heads_first            [BOOT]
OPT.train_projectors_first       [BOOT]
OPT.adapter_rank                 [TUNE]
OPT.trainable_slice_budget       [USER/TUNE]
OPT.quantized_inference          [BOOT]
OPT.train_master_precision       [RESEARCH/TUNE]
OPT.delta_merge_frequency        [TUNE]
OPT.checkpoint_frequency         [USER/TUNE]
```

---

# 0Q. Parameter-Kopplungen — welche Regler beeinflussen sich gegenseitig?

Einige Werte dürfen nicht unabhängig betrachtet werden.

## 0Q.1 Teacher-Reliance

```text
A2.teacher_use_prob ↑
→ A3.teacher_alignment_weight darf ↑
→ aber A3.student_only_probe_rate muss ebenfalls ausreichend bleiben
→ sonst Teacher-Dependency
```

## 0Q.2 Gist Compression

```text
B2.compression_target ↑
→ B2.boundary_sensitivity wichtiger
→ B4.source_binding_strength muss hoch bleiben
→ B1/B2 exact re-entry muss verfügbar bleiben
```

## 0Q.3 Body-Wake Kosten

```text
C2/C4 wake threshold ↑
→ compute ↓
→ Risiko missed-hard-task ↑
```

Deshalb gemeinsam messen:

```text
unnecessary_wake_rate
missed_need_rate
quality
latency
energy
```

## 0Q.4 Callosum Strength

```text
B3.alignment_strength ↑
→ Kommunikation einfacher
→ Risiko role collapse ↑
```

Gegenregler:

```text
B3.private_state_protection
B3.anti_collapse_weight
role_retention benchmark
```

## 0Q.5 Plasticity vs Retention

```text
plasticity ↑
→ schnelleres Lernen
→ mehr Forgetting-Risiko
```

Gegenregler:

```text
M_retention
Regression Shield
Replay old cases
max_update_norm
consolidation_threshold
```

---

# 0R. Minimum Parameter Registry für den ersten Code

Nicht alle oben genannten Knobs müssen Day 1 implementiert werden. Minimum, damit wir forschen können:

```text
GLOBAL:
  learning_mode
  user_stage_cap
  max_update_norm
  reasoning_effort
  thermal_limit

A:
  teacher_use_prob
  teacher_alignment_weight
  student_only_probe_rate
  attention_top_down_gain
  attention_bottom_up_gain

B1:
  detail_gain
  offer_threshold
  local_jepa_weight
  plasticity

B2:
  gist_span_target
  global_context_gain
  offer_threshold
  local_jepa_weight
  plasticity

B3:
  exact_mix
  latent_mix
  cross_jepa_weight
  private_state_protection

B4:
  admission_threshold
  slot_decay
  refresh_budget

C1/C2/C3/C4/C5:
  goal_persistence
  route_gain
  confidence_threshold
  language_budget
  coalition_threshold
  max_cycles
  body_reentry_budget
  risk_gate

LEARNING:
  eligibility_decay
  teacher_gain
  human_gain
  world_outcome_gain
  replay_priority
  consolidation_threshold

AGE:
  teacher_reliance_curve
  autonomy_curve
  plasticity_curve
  dream_curve
```

Alles Weitere kann im Registry-Format später hinzukommen, ohne den Code umzuschreiben.

---

# 0R-H. Machine-Readable Contracts / IDs

## IH-H3 — Machine-Readable Canon ist STEP-0-Artefakt, nicht spätere TODO [BLOCKER]

`G0` fordert machine-readable Contracts. Diese müssen **vor** echter Modellintegration existieren.

Mindestens folgende Schemas werden versioniert:

```text
EventEnvelope
SourceRef
PerceptPacket
OfferPacket
QueryPacket
MessagePacket
WorkspaceSlot
ExecState
JEFBroadcastPacket
ActionIntent
CorollaryCopy
ActionOutcome
HumanDecision
ExperienceRecord
MemoryRecord
LearningTrace
UpdateManifest
CheckpointManifest
BrainGenerationManifest
ModelManifest
CapabilityProfile
PathSpec
KnobSpec
```

Jedes Boundary-Paket enthält mindestens:

```text
schema_version
packet_id
producer_component
producer_version
event_id
experience_id?
created_monotonic_ns
created_wall_time
brain_generation_id
provenance
```

Regeln:

- unbekannte Pflichtfelder => reject, nicht still `None`,
- additive optionale Felder dürfen innerhalb einer Major-Schema-Version kompatibel sein,
- Breaking Changes brauchen Migration,
- keine fremden Body-token-IDs als globales Exact-Format,
- ungültige Pakete dürfen geloggt werden, aber nicht still produktiv wirken.

---

## IH-H4 — Globale IDs und Referential Integrity [BLOCKER]

Folgende IDs werden nicht vermischt:

```text
event_id          = einzelner zeitlicher Runtime-Event
experience_id     = zusammengehörige Lernerfahrung; kann mehrere Events enthalten
action_id         = genau ein beabsichtigter äußerer/mentaler Akt
source_id         = immutable Source-Objekt
source_ref         = Bereich/Region/Zeitspanne in einer Source
state_version     = Version eines mutierbaren States
brain_generation_id = atomarer produktiver Gesamt-Snapshot
update_id         = ein Lernänderungs-Kandidat
checkpoint_id     = persistierter Komponenten-/Gesamtsnapshot
rule_version      = aktive Regelgeneration
capability_id     = getrennt reifende Fähigkeit
model_revision    = unveränderlicher Modellstand
```

`SourceRef` ist modalitätstypisiert:

```text
text: byte/char offsets + content hash
image: image id + tile/box + transform lineage
audio: sample/time interval + codec lineage
video: time/frame interval + track/region
tool: result object + field/path + call id
```

Ein dangling SourceRef ist ein Datenfehler und darf nicht als Exact Evidence gelten.

---

# 0S. Forschungsregel für Lernpfade

Kein Lernpfad wird allein deshalb stark gemacht, weil er biologisch plausibel oder elegant klingt.

Für jeden Pfad:

```text
1. OBSERVE
2. SHADOW
3. kleine kontrollierte Updates
4. Retention/Regression messen
5. Authority langsam erhöhen
6. bei Drift zurück
```

Das gilt besonders für:

- B1↔B2 Cross-JEPA,
- JEF↔Brain Control Learning,
- Teacher Internalisation,
- World-JEPA,
- Dream→Policy Learning,
- Base-weight Consolidation.

Die genaue Lernmatrix ist deshalb **bewusst ein Forschungsobjekt des Projekts**.

## 0.0A v10.10 Additive-Only-Korrektur

v10.9 hat an mehreren Stellen sinnvolle neue Ideen eingebaut, dabei aber bestehende v10.8-Mechanismen durch kompaktere Alternativen **ersetzt**. Das ist für dieses Projekt die falsche Richtung. Ab v10.10 gilt daher:

```text
NEUE IDEE
  ↓
als optionaler Research-/Implementation-Kandidat ANHÄNGEN
  ↓
gegen vorhandenen Mechanismus testen
  ↓
erst nach expliziter Entscheidung austauschen
```

Nicht erlaubt ist:

```text
neue Optimierung → alten Canon still löschen
```

Insbesondere bleiben vollständig erhalten:

- JEF_core + JEF_fast + JEF_native/focal-Funktionalität,
- B1/Detail + B2/Gist + Observer/Offer/Callosum/Focal-Coalition,
- v10.8 Raw+Teacher Ingress und Self+Reference Egress,
- Human Decision Packets und Age-0 Lab Mode,
- JEPA/Eligibility/Replay/Metaplasticity/Homeostasis,
- Age 0–5 + capability-spezifische Reife,
- der **stufenweise Build-Plan STEP 0–11**,
- alle bisherigen Gates und Benchmarks.

Optimierungen dürfen Implementationen **ersetzen**, aber nur wenn die Funktion erhalten bleibt und ein Benchmark gewinnt.


## 0.1 v10.7 korrigiert eine falsche Vereinfachung

Der historische Satz „A/B/JEF sollen langfristig alles halten“ (ab v10.13: B1/B2/JEF) bleibt **für kognitive Bedeutung, Selbststeuerung und gelernte Welt-/Skillrepräsentation** das Ziel, darf aber nicht bedeuten, dass rohe Sensorik und physische Ausgabe ohne spezialisierte Transducer auskommen müssen. Ein kleines Text-LM besitzt zwar einen Text-Token-Decoder/LM-Head, aber **keinen nativen Pixel-, Audio- oder Motor-Decoder** und ohne Multimodaltraining auch keinen brauchbaren Rohsensor-Encoder.

Darum trennt v10.7 erstmals sauber:

```text
COGNITIVE CORE
B1 Detail + B2 Gist + JEF + Workspace/Memory/World

PERIPHERAL / SENSORIMOTOR LAYER
raw sensor codecs + segmenters + modality encoders/projectors
+ output decoders/renderers/actuators
+ temporäre semantic teachers/scaffolds
```

Die Peripherie darf **dauerhaft trainierbar** sein. Was mit Reife verschwinden soll, ist primär schwere semantische Teacher-Abhängigkeit, nicht notwendigerweise der physische Audio-/Vision-/Motor-Codec selbst. Das ist sowohl technisch realistischer als auch hirnnäher: ein Gehirn lernt nicht, Retina, Cochlea und Muskel-/Sprechmotorik „wegzulernen“.

---

# 1. Nicht verhandelbare Architekturgesetze

## 1.1 Drei lernende kognitive Hauptträger — jetzt ohne Buchstaben-Kollision

Langfristig soll zentrale kognitive Kompetenz überwiegend in folgenden lernenden Trägern landen:

- **B1_DETAIL** — Detail/Fine Hemisphere,
- **B2_GIST** — Gist/Coarse Hemisphere,
- **C_JEF_SYSTEM** — Executive/Report/Action-Subsystem mit mehreren kleinen Organen.

A-Plane Student-Ports dürfen ebenfalls lernen, tragen aber primär Wahrnehmungs-Translation statt das gesamte Welt-/Skillwissen. Externe Teacher bleiben Hilfen. Physische Encoder/Codecs/Renderer dürfen dauerhaft existieren, solange sie nicht zu versteckten kognitiven Agenten werden.

## 1.2 B1 und B2 sind vollwertige Bodies mit unterschiedlicher effektiver Auflösung

```text
B1 = DETAIL / FINE      (legacy A)
B2 = GIST / COARSE      (legacy B)
```

### 1.2.1 B1 — Detail / Fine

Default-Bias:

- kurze zeitliche Integrationsfenster,
- Fine-Slots auf ungefähr 1 nativen Token bzw. der kleinsten stabilen Body-Einheit,
- hohe lokale Auflösung,
- Wortlaut, Zahlen, Code, lokale Unterschiede,
- exakte Fehler-/Widerspruchssuche,
- schärfere/selektivere Verarbeitung, soweit der native Body dies bereits unterstützt.

### 1.2.2 B2 — Gist / Coarse

Default-Bias:

- längere zeitliche Integrationsfenster,
- mehrere native Tokens/Spans werden zu Gist-Gruppen verdichtet,
- globale Relationen, Konzepte, Plan, Diskurs-/Eventstruktur,
- breitere Integration mehrerer Perspektiven,
- gröbere, länger haltende Workspace-Repräsentationen.

Boot-Default bleibt:

```text
B1 Detail: ~1 native Token / Fine-Slot
B2 Gist:   ~8 native-token-equivalents / Gruppe
           ~12 aktive Gist-Slots
```

Die Zahlen sind Forschungsdefaults. Boundary-aware/adaptive grouping darf sie ersetzen.

### 1.2.3 Native Tokenizer bleiben unangetastet

```text
A5 Percept/Text Source
  ├─→ B1 native tokenizer/body → fine readout
  └─→ B2 native tokenizer/body → adaptive gist readout
```

Die unterschiedliche Auflösung liegt in Readout/Workspace/Context-Scheduling und ggf. nativen hierarchischen Body-Funktionen, nicht in blindem Umbau fremder Tokenizer.

### 1.2.4 Multiscale statt Informationssilo

B1 und B2 dürfen beide mehrere Zeitskalen tragen. Der Unterschied ist ein starker Default-Bias. Cross-scale SourceLinks verbinden Gist↔Fine↔Exact.

### 1.2.5 Native Top-k bleibt autoritativ

`Gist breiter` vs. `Detail schärfer` ist Body-Selection-/Training-Bias, kein Recht, pretrained Router ohne Retraining umzupatchen.

## 1.3 Native Body-Architektur bleibt autoritativ

Jeder austauschbare Body behält intern:

- eigenen Tokenizer,
- eigene Attention,
- eigene MoE-Router,
- eigene Hidden-Dimension,
- eigene KV-/recurrent Mechanismen.

V13 setzt darüber eine eigene Meta-/Control-Ebene, patcht aber keinen pretrained Top-k blind zu einer anderen Inferenzgeometrie.

## 1.4 B1 und B2 kommunizieren direkt

C/JEF ist **nicht** die einzige Brücke.

Mindestens drei Kommunikationsarten sind vorgesehen:

1. **Latent Channel** — hochbandiger bidirektionaler Kandidat; erhält Authority nur nach Utility-Test.
2. **Control Metadata** — Unsicherheit, Konflikt, Relevanz, Routing-/Memory-Anfragen.
3. **Bounded Exact Channel** — verlustfreier, begrenzter Source-/Literal-Kanal für Wortlaut, Zahlen, Code, Zitate und andere verlustkritische Details. Der gemeinsame atomare Typ ist **nicht** ein Body-spezifisches Token. Übertragen werden z. B. `SourceRef`, UTF-8-/Byte-Spans, typisierte Zahlen, Code-Spans oder Range/Coordinate-Metadaten; jeder Body retokenisiert intern mit seinem nativen Tokenizer.
4. **Bounded Symbolic Channel** — optionaler kurzer, typisierter semantischer Kanal für diskrete Labels, Constraints, Operatoren, Plan-Knoten oder andere Inhalte, die weder als Rohquelle noch als hochdimensionales Latent optimal sind.

### 1.4.1 Channel Policy: Latent muss seinen Nutzen verdienen

Der Latent Channel ist ein bevorzugter **Kandidat**, aber kein Dogma. Pro State/Task/Body-Paar darf ein kleiner Channel-Policy-Head eine Mischung bzw. Auswahl schätzen:

```text
channel_policy(state, receiver, task) →
  p(LATENT), p(SOURCE_EXACT), p(CONTROL), p(SYMBOLIC), p(NO_MESSAGE)
```

Regeln:

- Aktive Latent-Injection wird nur verwendet, wenn Receiver-Kompatibilität und Downstream-Utility gegenüber No-Message-/Source-/Symbolic-Baselines nachgewiesen sind.
- Latent-Nachrichten werden vor Injection auf Norm, Scale, Distribution-Shift und Out-of-Distribution-Risiko kalibriert/gegated.
- Ein schlechter Latent-Kanal darf automatisch degradiert oder auf Source/Control/Symbolic zurückfallen.
- Kommunikationskosten und zusätzliche Receiver-Latenz gehen in die Channel-Utility ein.
- `NO_MESSAGE` ist eine echte Option: Kommunikation ist kein Pflichtpass.

## 1.5 Der Graph ist ein Möglichkeitsraum, keine Pipeline

„Vorhanden“ bedeutet nicht „läuft immer“.

Eine Anfrage kann z. B. nur einen automatischen Skill auslösen, einen normalen A/B-Pass brauchen oder eine tiefe C-fokale Deliberationsschleife mit A/B/Memory/Inquisition rekrutieren.

## 1.6 Output ist jederzeit erzwingbar

Zu jedem Zeitpunkt existiert ein bestmöglicher aktueller Output-Snapshot.

- Weitere Loops laufen nur innerhalb eines Budgets.
- Hard Deadline beendet Deliberation.
- Danach wird der beste grounded Output erzeugt bzw. Unsicherheit/Abstinenz markiert.
- Replay, Dream, Konsolidierung und Offline-Learning blockieren niemals die sichtbare Antwort.

## 1.7 Erfahrung muss zukünftiges Verhalten verändern können

North-Star-Test:

> Eine relevante frühere Erfahrung soll eine spätere vergleichbare Situation beeinflussen, ohne dass bereits korrekte Constraints unnötig verloren gehen.

Das kann zunächst über Fast Episodic Memory und Control Learning geschehen, lange bevor große Body-Gewichte konsolidiert wurden.

## 1.8 Provenance ist strukturell

Getrennt bleiben mindestens:

- externe/humane Evidenz,
- Tool-/Umweltresultate,
- Teacher-Ausgaben,
- eigene generierte Hypothesen,
- Dream/Simulation,
- abgeleitete Kondensate,
- Regeln,
- Protokoll/Logs.

Eigene Erzeugnisse werden nicht automatisch zur Faktenquelle.

## 1.9 Truth und Utility bleiben getrennt

**Epistemisch:** Ist eine Aussage belegt / konsistent / wahrscheinlich wahr?  
**Instrumentell:** War eine Aktion/Route nützlich, schnell, erfolgreich oder teuer?

Ein positiver Reward macht keine falsche Aussage wahr.

## 1.10 Lifetime plastic, aber nicht überall gleichzeitig

Prinzipiell dürfen reale B1/B2/JEF-Gewichte langfristig lernbar sein. Daraus folgt **nicht**, dass jeder Prompt global durch A+B+JEF backpropagiert.

## 1.11 Wahrnehmung und Handlung sind eigene lernbare Schleifen

Jede neue Modalität besitzt zwei Richtungen:

```text
WORLD → SENSOR/PERCEPT PORT → COGNITIVE CORE
COGNITIVE CORE → EFFECTOR/DECODER PORT → WORLD
```

Input-Encoder und Output-Decoder lernen **nicht automatisch dasselbe**. Vision verstehen und Bilder erzeugen, Sprache verstehen und Sprache synthetisieren, eine UI sehen und eine UI bedienen sind gekoppelte, aber getrennte Fähigkeiten. V13 darf beide über gemeinsame latente Zustände, Corollary Copy, Reconstruction und Outcome koppeln.

## 1.12 Reconstruction ist Grounding-Hilfe, nicht automatisch Bedeutung

Ein Decoder, der Pixel/Audio rekonstruiert, zwingt einen Latent-State dazu, relevante Information zu erhalten. Das allein erzeugt aber noch keine Semantik. Bedeutung wird zusätzlich durch Cross-Modal-Paare, JEF/B1/B2-Ziele, Tool-/World-Outcomes, Teacher-Signale und wiederholte Experience gelernt.

---

# 2. System-Ontologie: Was für ein Ding ist jede Komponente?

Damit Work nicht wieder aus jedem Begriff ein eigenes Modell macht, muss jede Komponente einem Typ zugeordnet werden.

## 2.1 Lernende Hauptträger / Organe

- **B1_DETAIL** — großer Detail/Fine Body,
- **B2_GIST** — großer Gist/Coarse Body,
- **C_JEF_SYSTEM** — Executive–Effector-System,
- **C2_CONTROL_ORGAN** — Needle-class oder Alternative,
- **C3_LANGUAGE_ORGAN** — optionales Tiny-LM für freie Basissprache,
- **A3_STUDENT_PORTS** — modality-specific learnable projectors/resamplers.

JEF ist damit absichtlich **zusammengesetzt**. C2/C3 sind austauschbar und dürfen später teilweise zusammenfallen, aber nur nach Messung.

## 2.2 Kleine lernbare Heads / Policies

Beispiele:

- `C_fast` Route Head
- Attention/Gain Head
- Skill Selection Head
- Memory Cue Head
- Output Mode Head
- Halt Head
- Salience/Interrupt Head
- Action Gate
- Fast Forward Predictor
- Cautiousness/uncertainty integration
- Neuromodulator heads
- Translator-use gate
- Context-policy heads
- Channel-policy / message-utility heads
- Fast-decision calibration readouts

Diese sind **keine zusätzlichen LLMs**.

## 2.3 Persistente Zustände

- Distributed Brain State
- Focal Workspace
- Self State
- Body State
- Goal State
- Age Vector
- Plasticity State
- Homeostatic State
- Skill metadata

## 2.4 Stores

- Exact / Provenance Store
- Fast Episodic Store
- Semantic staging store
- Procedural staging store
- Archive
- World Notebook / audit surface

## 2.5 Offline-/Background-Lerner

- JEPA learners
- Replay scheduler
- Dream/counterfactual generator
- Consolidation worker
- Regression evaluator
- Body transfer/alignment worker

## 2.6 Scaffolding

- Teacher models
- Translator/encoder models
- external specialists
- old body in shadow/teacher mode

Scaffolding ist capability-spezifisch, reduziert sich nur nach Retention/Parity und kann nach Regression wieder aktiviert werden.

## 2.7 Permanente ModalityPorts / Sensorimotor-Peripherie

Dies sind **keine zusätzlichen kognitiven Agents**, sondern gelernte I/O-Systeme:

- Text tokenizer / detokenizer / exact renderer,
- Vision tiler/segmenter + visual encoder/projector,
- Audio codec/tokenizer + acoustic encoder/projector,
- Speech token decoder + vocoder/TTS renderer,
- optional image latent/pixel decoder/generator,
- Tool/UI/robotic action serializer + actuator adapter,
- modality-specific timestamp/synchronization logic.

Sie dürfen klein, austauschbar und capability-spezifisch sein.

## 2.8 Temporäre Semantic Teachers

Teacher sind **nicht** dasselbe wie ModalityPorts. Beispiele:

- starkes Vision-Language-Modell, das Bildregionen semantisch erklärt,
- ASR-Modell, das Audio zusätzlich transkribiert,
- TTS/Audio-Modell, das gewünschte Sprachqualität vormacht,
- großer multimodaler Teacher, der Latent-/Caption-/Alignment-Ziele liefert.

Teacher dürfen später reduziert/archiviert werden; der minimale physische Port bleibt.

---

# 3. Die drei kognitiven Hauptträger / Body-Systeme

## 3.1 B1 — Detail / Fine Body (legacy A)

B1 bildet primär hochaufgelöste, lokale, literalitäts- und kontradiktionssensitive Repräsentationen.

Default-Ziele:

- 1-Token-/kurze Fine-Slots,
- exakte Details, Zahlen, Code und Wortlaut,
- lokale Begründungen,
- Fehler-/Widerspruchssuche,
- genaue Tool-/Action-Schritte,
- Exact-Source-Recovery.

B1 bleibt ein vollständiger pretrained Body. `Fine` beschreibt die bevorzugte Integrations-/Readout-Auflösung, nicht eine künstliche Beschneidung seiner Fähigkeiten.

## 3.2 B2 — Gist / Coarse Body (legacy B)

B2 bildet primär gröbere, länger integrierende, relationale und globale Repräsentationen.

Default-Ziele:

- adaptive Gruppen-/Gist-Slots,
- globale Muster, Abstraktion und semantische Verdichtung,
- weite Assoziationen, Konzepte und Planstruktur,
- Diskurs-/Eventzusammenhang,
- mehrere Perspektiven gleichzeitig,
- grobe World-State-/Hypothesenstruktur.

**Bootstrap:** ungefähr 8 native-Token-equivalents pro Gruppe und ungefähr 12 aktive Gist-Slots; danach lernbare Boundary-/Chunk-Policy. Mit wachsender Kompetenz darf die typische Integrationsspanne steigen, sofern Retention/Exactness erhalten bleiben. Bei Novelty, Konflikt oder Detailbedarf darf sie sofort wieder sinken.

B2 bleibt ebenfalls ein vollständiger pretrained Body und ist **kein Summarizer**.

### 3.2A Cross-scale coupling

Gist-Slots müssen auf Exact/Fine-Spans rückverweisen können:

```text
B gist slot
  ├─ source_span_refs
  ├─ covered event/time range
  ├─ compression ratio
  ├─ boundary confidence
  └─ exact/detail fallback → B1 / Exact Store
```

Umgekehrt darf A mehrere Fine-Slots zu einem provisorischen lokalen Gist bündeln, wenn eine Detailaufgabe kurzfristig etwas mehr Kontext braucht. Die Asymmetrie ist daher **präferierte Zeitskala**, nicht Informationssilo.

## 3.3 JEF (historisch C) — Executive–Effector-System, NICHT ein einzelnes LLM [v10.12 CANON]

JEF ist der kleine lernende **Executive–Effector-Komplex** zwischen verteiltem Brain-State und äußerer Handlung. Es ist besonders nah an Zielhaltung, Sprache, Tool-/Body-Interaktion, Action Intent, laufender Kontinuität und fokaler Orchestrierung.

Wichtig:

```text
JEF != ein LLM
JEF != nur Router
JEF != Bewusstsein allein

JEF = System aus State + Control + Language Interface + Focal Loop + Action/Report + Learning Interfaces
```

### 3.3.0 JEF-Bauteile

```text
JEF_SYSTEM
├─ JEF_PRIVATE_STATE
│   ├─ executive_state
│   ├─ short-term recurrent/KV state, falls das eingesetzte Teilmodell ihn besitzt
│   └─ active goal/constraint/action state
│
├─ JEF_FAST_POLICY
│   ├─ wake / route / halt / skill / memory / channel
│   └─ kleine Heads oder ein Tiny-Control-Modell
│
├─ JEF_LANGUAGE_CONTROL_CORE   ← austauschbares kleines Modell
│   ├─ User-Sprache → EXEC_PACKET
│   ├─ Extraction / intent / constraints
│   ├─ Tool-/Action-Paket
│   ├─ Embedding / retrieval key
│   ├─ Confidence / escalate
│   └─ optional kurze sprachliche Antwort
│
├─ JEF_FOCAL_LOOP
│   ├─ integriert A/B Offers + Memory/Self/World
│   ├─ hält Problem/Goal rekurrent offen
│   └─ entscheidet über Query/Re-entry/Verify/Inquisition
│
├─ JEF_BROADCAST_BRIDGES
│   ├─ JEF → A/B
│   └─ A/B Offers → JEF/Coalition
│
├─ JEF_REPORT_ACTION_BROKER
│   ├─ ein autorisierter Report-/Action-Stream
│   └─ Direct / JEF report / A/B assisted / Tool / Body
│
└─ JEF_LEARNING_INTERFACE
    ├─ Eligibility / route credit
    ├─ human/reference comparison
    └─ local control/language updates
```

Damit ist ein kleines Sprachmodell **Teil von JEF**, aber JEF überlebt einen Modelltausch. Genau das ist für Body-Swap, Age, Lernen und spätere neue Modalitäten wichtig.

### 3.3.1 JEF Language/Control Core: warum Needle 3 hier deutlich besser passt als als Sidecar

Needle 3 ist technisch weiterhin ein kleines generatives Textmodell, aber **kein General-Chat-LLM im üblichen Sinn**. Sein öffentliches Interface ist auf Tool Calling, strukturierte Extraction und Embeddings optimiert; die eigenen Docs warnen ausdrücklich davor, freie Antworten auf beliebige Fragen zu erwarten. Genau deshalb ist es für JEF interessant: JEF braucht in erster Linie **strukturierte Sprach→Control-Übersetzung**, nicht noch einen dritten großen Chatbot.

Needle-3-Funktionen passen fast direkt auf JEF:

```text
Needle tool calling          → JEF ACTION_PACKET / Tool selection
Needle structured extraction→ EXEC_PACKET: goal, constraints, entities, slots
Needle embedding head       → Memory/Tool/Rule retrieval key
Needle calibrated confidence→ Escalation / A-B wake / ask-human candidate
Needle grammar decode       → garantiert valide interne Packet-Schemata
Needle laddered depth       → verschiedene deploybare JEF-Language-Control-Größen
Needle tool retrieval       → billige Vorauswahl großer Toolkataloge
Needle system facts         → read-only Body/Self/Environment facts input
```

**v10.12-Korrektur:** Needle ist daher nicht bloß ein externer Coprocessor. Es ist ein **ernsthafter Kandidat für die erste Implementierung von `JEF_LANGUAGE_CONTROL_CORE` selbst**.

Nicht automatisch übernommen werden:

- Needle ist kein Ersatz für den gesamten JEF-State oder JEF_FOCAL_LOOP.
- Needle ersetzt nicht A/B-Reasoning, Memory, World Model oder Callosum.
- Seine Engram-n-gram-Memory ist kein Ersatz für V13 Exact/Episodic/Semantic Memory.
- Seine Ladder ist zunächst eine Auswahl **exportierter Subnetze**; sie ist nicht automatisch per Token dynamische Tiefe im laufenden Turn.
- Sein General-Chat-/freie-Sprache-Verhalten ist absichtlich schwach. Für reicheren Report kann JEF einen getrennten kleinen Report-Decoder benutzen oder A/B-assistierten Decode nutzen.

### 3.3.2 Warum Needle sogar Komponenten von JEF_FAST bündeln könnte

Wir sollten nicht dogmatisch `JEF_FAST_POLICY` und `JEF_LANGUAGE_CONTROL_CORE` als zwei verschiedene Netze erzwingen. Needle vereinigt bereits mehrere Funktionen in einem winzigen Modell:

- Toolauswahl,
- Slot/Constraint-Extraction,
- Embedding,
- strukturierte Generation,
- Confidence.

Deshalb testen wir drei Varianten:

```text
A) separate tiny heads + separates JEF language model
B) Needle als Language/Control-Core + wenige externe safety/runtime heads
C) Needle nur Language parser, JEF-fast bleibt separat
```

Gewinner wird nach **RAM + Latenz + Kalibrierung + Second-Attempt-Lernen + A/B-Wake-Qualität** gewählt. Keine Funktion wird gestrichen; eventuell werden mehrere Funktionen nur in einem Modell zusammengelegt.

### 3.3.3 Wichtige Needle-Grenze: Confidence nach Fine-Tuning

Needles veröffentlichte Confidence ist für das Base-Modell kalibriert. Laut aktueller API-Dokumentation wird der Confidence-Head beim LoRA-Fine-Tuning nicht mitaktualisiert; bei tuned weights liefert die Library deshalb keine normale kalibrierte Confidence.

Für V13 folgt daraus:

```text
Base Needle confidence
→ darf als Baseline genutzt werden

Fine-tuned JEF Needle
→ braucht eigene Re-Calibration / JEF confidence head / held-out calibration set
```

Das ist wichtig, weil gerade Escalation und Body-Wake nicht auf scheinpräzise, aber unkalibrierte Scores gebaut werden dürfen.

### 3.3.4 JEF State bleibt explizit außerhalb des austauschbaren Language-Modells

JEF-Kontinuität darf nicht komplett in einem opaken Modell-KV verschwinden. Canonisch bleibt ein expliziter `executive_state`:

```text
EXEC_STATE {
  goal
  constraints
  active_task
  current_action_intent
  salient_A_offer
  salient_B_offer
  memory_refs
  uncertainty
  body/resource state
  age/permission flags
  conversation/event version
}
```

Das eingesetzte Language/Control-Modell bekommt daraus eine kompakte View und schreibt nur erlaubte strukturierte Felder zurück. Dadurch kann Needle, ein anderes Tiny-Modell oder später ein selbst gelerntes Modell ausgetauscht werden, ohne JEF-Identität/State zu verlieren.

### 3.3.5 JEF Broadcast: zuerst strukturierte Pakete, später optional Latents

Ein weiterer Vorteil dieser Trennung: der aktuelle Needle-Runner dokumentiert Tool/Extraction/Embedding, aber keine stabile öffentliche API für beliebige interne Layer-/KV-Taps. Deshalb wird v10.12 **nicht** davon abhängig, rohe Needle-Hidden-States in A/B zu injizieren.

Age-0-Broadcast kann zunächst sein:

```text
JEF_BROADCAST_PACKET {
  goal_embedding
  typed constraints
  current action intent
  uncertainty/escalation
  source refs
  short language/control embedding
}
```

A/B lernen diese stabile Schnittstelle zu verstehen. Wenn wir später den offenen JAX-Checkpoint/Architekturcode modifizieren und echte Hidden-Taps validieren, kann ein zusätzlicher Latent-Bridge-Kanal dazukommen.

### 3.3.6 JEF Report/Sprache ist eine Fähigkeit, nicht die Identität von JEF

JEF muss nach außen sprechen können, aber das zwingt nicht zu einem vollwertigen Chat-LM als JEF-Kern. Der Report-Pfad ist pluggable:

```text
JEF action/report intent
   ├─ Direct / Exact renderer
   ├─ Needle/structured short report, falls ausreichend
   ├─ tiny REPORT_DECODER
   ├─ A-assisted decode
   └─ B-assisted / integrated decode
```

Für Age 0 kann ein externer Reference Teacher zusätzlich bessere Formulierungen liefern, getrennt markiert. JEF lernt daraus Sprache/Report, ohne Teacher-Output mit eigener Erfahrung zu verwechseln.

### 3.3.7 JEF Focal Loop ist System-Rekurrenz, nicht zwingend LM-Rekurrenz

Der frühere Name `C_focal` klang so, als müsste dasselbe kleine LLM immer wieder über sich selbst laufen. Das ist **nicht notwendig**. Canonisch ist:

```text
FOCAL_LOOP
→ read focal coalition
→ JEF policy/language-control step
→ query A/B/Memory/World/Tool if needed
→ receive offers/outcome
→ update executive/focal state
→ repeat until halt/deadline
```

Das Language/Control-Modell kann in jeder Runde beteiligt sein, muss aber nicht jeden Mikro-Schritt generativ decodieren.

### 3.3.8 Wie JEF anders lernt als A/B

JEF lernt primär **Kontrolle und Übersetzung zwischen Sprache, State und Handlung**:

- welche User-Phrase welchem Goal/Constraint entspricht,
- wann A, B, beide oder keiner geweckt werden sollten,
- welche Offer relevant war,
- welches Tool/Memory gebraucht wurde,
- wann es eskalieren/abstain/fragen sollte,
- welche Report-/Action-Formulierung besser bewertet wurde,
- welche internen Packet-Felder später zum Erfolg beigetragen haben.

A/B lernen dagegen stärker Repräsentation, Prediction, Detail/Gist und Weltzusammenhänge. Alle sehen dasselbe Outcome, aber Credit bleibt rollenspezifisch.

JEF-Sprach-/Control-Lernen darf zunächst über Shadow-LoRA/Adapter, externe Heads oder distillierte Packet-Targets stattfinden. Auf dem Redmi ist Base-Weight-Training von Needle **nicht** automatisch Voraussetzung; Inference + externe lernende V13-Heads ist der erste Lab-Pfad.

### 3.3.9 Historische Alias-Mapping

Ältere Abschnitte bleiben lesbar durch:

```text
C_fast   ≈ JEF_FAST_POLICY
C_native ≈ JEF_LANGUAGE_REPORT_PATH
C_focal  ≈ JEF_FOCAL_LOOP
C body   ≈ JEF_SYSTEM (historisch zu eng formuliert)
```

Ab v10.12 darf kein Implementierer aus diesen Aliasen folgern, dass JEF ein einzelnes LLM mit drei Modi sein muss.

## 3.4 JEF-State, KV-Bridges und die fokale Koalition [v10.6 CANON]

### 3.4.1 Drei verschiedene Dinge nicht mehr vermischen

```text
JEF_SYSTEM
= Executive–Effector-Subsystem aus Control, Language Interface, State, Focal Loop und Action/Report

JEF_LANGUAGE_CONTROL_CORE
= austauschbares Tiny-Modell innerhalb von JEF; Needle 3 ist Age-0-Kandidat

JEF_PRIVATE_STATE
= expliziter executive state + optional native model KV/recurrent state
= JEF-Systemzustand ist NICHT an ein bestimmtes Tiny-Modell gebunden

FOCAL_COALITION_STATE
= der momentan global zugängliche/fokale Zustand
= ausgewählte JEF + A + B + Memory + Self + World Inhalte
= funktionale Conscious-Access-Simulation
```

Damit gilt ausdrücklich:

```text
Bewusstseinssimulation != JEF_BODY allein
Bewusstseinssimulation ~= fokale Koalition + rekurrente globale Verfügbarkeit
```

JEF ist aber der bevorzugte **Report-/Action-/Executive-Knoten** der Koalition.

### 3.4.2 JEF Native KV bleibt privat; exportiert wird ein Broadcast Cache

A/B sollen den laufenden JEF-Zustand verstehen lernen. Rohes JEF-KV direkt in fremde Bodies zu injizieren wäre jedoch architekturabhängig und instabil. Deshalb besitzt JEF zwei Ebenen:

```text
JEF_NATIVE_KV
  = volle private native KV / recurrent state
  = nur JEF versteht sie nativ

JEF_BROADCAST_CACHE (JBC)
  = kleine stabile exportierte Repräsentation
  = aus selektierten JEF-Layer-/KV-Readouts + executive_state
  = mit SourceRefs / Goals / Focal-Slots / Action-Intent / State-Version
```

Minimaler JBC-Inhalt:

```text
JEF_BROADCAST_CACHE {
  state_version
  goal_latent
  executive_latent
  focal_slot_refs[]
  active_constraints[]
  recent_action_intent
  corollary_copy_ref?
  uncertainty_summary
  body/resource_state
  exact/source pointers[]
}
```

A und B besitzen trainierte Bridges:

```text
JEF_BROADCAST_CACHE → JEF2A projector/adapter → A conditioning
JEF_BROADCAST_CACHE → JEF2B projector/adapter → B conditioning
```

Die Bridges werden über grounded paired states, Cross-JEPA/representation matching, downstream utility und Regression-Tests trainiert. Native KV bleibt austauschbar; beim JEF-Body-Swap müssen primär die Bridges neu ausgerichtet werden.

### 3.4.3 Standard: ein Hintergrund-Observer-Pass pro Event

Bei einem neuen externen Event darf die Default-Scaffold-Route beide Hemisphären **einmal beobachten lassen**, ohne dass sie Text generieren oder den Turn blockieren müssen:

```text
EVENT / USER INPUT
      ├────────────→ JEF immediate update
      ├────────────→ A Detail observer pass
      └────────────→ B Gist observer pass
```

Jeder Observer-Pass erhält:

```text
new source/event
+ eigene native hot/warm state
+ JEF_BROADCAST_CACHE
+ relevante Exact/Context pointers
```

Er erzeugt primär **keine Chatantwort**, sondern ein `OFFER_PACKET`.

Wichtig:
- Observer-Pass = ein bounded representation/state-update pass, kein kompletter eigener CoT/Decode.
- JEF darf bei trivialen/sicheren Fällen antworten, bevor beide Observer fertig sind.
- Kommt vor Deadline ein hochsalientes/conflicting Offer, darf es den provisional candidate invalidieren und tieferes Processing auslösen.
- Unter Resource/Thermal-Druck darf der Scheduler einen Observer defer/skippen; die Policy und der Grund werden geloggt.
- Age 0 nutzt `always/mostly observe` als Scaffold; später darf die Frequenz gelernt werden, sofern Second-Attempt/Novelty-Detection nicht leidet.

### 3.4.4 A/B schicken Offers, keine Agentenantworten

Beispiel:

```text
OFFER_PACKET {
  body = A|B
  event_id
  message_latent
  role = detail|gist|conflict|prediction|memory_cue|plan|error
  salience
  uncertainty
  disagreement_score
  source_span_refs[]
  exact_fallback_ref?
  request = none|deeper_self|other_body|memory|world|exact
  state_version
}
```

A-Offer ist typischerweise fine/exact; B-Offer typischerweise coarse/global. Das sind Biases, keine Verbote.

### 3.4.5 Fokale Koalition: aus lokalen Offers wird ein gemeinsamer bewusster Fokus

Viele lokale Zustände laufen parallel. Nur ein kleiner Teil erhält fokale/global verfügbare Authority:

```text
A private state ─┐
B private state ─┤
Memory candidates├─→ salience/gain/goal competition
World predictions├─→ FOCAL_COALITION_STATE
Self/JEF state ──┘          ↕
                       recurrent broadcast
                   ↙ A ↔ B ↔ JEF ↘
                    Memory / Self / World
```

Die Koalition ist kapazitätsbegrenzt und versioniert. JEF hält den aktuellen Report-/Action-Intent, aber Inhalte können überwiegend aus A, B, Memory oder World stammen.

### 3.4.6 JEF darf Offers ignorieren, aufnehmen oder vertiefen

Nach dem ersten Observer-Pass:

```text
JEF decision:
  IGNORE          → aktueller JEF/direct candidate reicht
  INCORPORATE_A   → Detail-Offer wird fokal
  INCORPORATE_B   → Gist-Offer wird fokal
  INCORPORATE_AB  → beide in Koalition
  QUERY_A         → gezielter tiefer Detail-Pass
  QUERY_B         → gezielter tiefer Gist-Pass
  QUERY_AB        → rekurrenter Split-Brain-Loop
  INQUISITION     → C/JEF-fokale Deliberationsmodi
  MEMORY/WORLD    → zusätzliche Evidenz
  ACT/REPORT      → Output/Aktion
```

Das ist der Kern des lernenden Self-Routing: **A/B dürfen immer etwas anbieten; JEF lernt, wann ein Angebot relevant genug ist, um die fokale Route zu verändern.**

### 3.4.7 Top-down Query von JEF zurück ins Brain

Wenn mehr Verarbeitung nötig ist, sendet JEF keine freie Chatfrage, sondern einen strukturierten `QUERY_PACKET`:

```text
QUERY_PACKET {
  goal/query latent
  desired_scale = fine|gist|mixed
  exact/source refs[]
  focal_state_ref
  evidence_need
  conflict_to_resolve?
  compute_budget
  response_deadline
}
```

A/B dürfen darauf lokal rekurrent arbeiten und untereinander Callosum-Nachrichten austauschen, ohne dass JEF jeden Mikro-Schritt routet. Ergebnis kommt wieder als Offer/Update in die Koalition.

### 3.4.8 Corollary Copy: JEF-Aktion geht zurück ins Brain bevor die Welt antwortet

Vor einer externen Aktion oder gesprochenen/geschriebenen Handlung:

```text
JEF / Action Broker
      ├─→ WORLD / USER / TOOL
      └─→ ACTION_COPY
             ├─→ A
             ├─→ B
             ├─→ World Model
             ├─→ Self Model
             └─→ JEF_BROADCAST_CACHE
```

`ACTION_COPY` enthält Intent, erwartetes Outcome, Source/Goal und action_id. So können A/B/World das kommende sensorische/Tool-Feedback als **self-caused vs external** vergleichen. Corollary discharge/efference-copy-artige Signale sind in biologischen Nervensystemen genau für diese Self-vs-World- und Prediction-Funktion wichtig.

### 3.4.9 Verteilte Wertung / Neuromodulation

JEF ist nicht der alleinige Wahrheitsrichter. Nach Outcome entstehen getrennte globale Signale:

```text
epistemic: evidence / truth / contradiction
instrumental: success / reward / cost
predictive: expected vs observed outcome
salience: novelty / surprise / importance
safety: permission / harm / rollback
```

Diese Modulatoren werden an JEF, A, B und relevante Control-Heads verteilt. **Globales Signal + lokale Eligibility + lokaler Prediction Error** bestimmen das Update. Dadurch lernen alle Teile aus derselben Weltreaktion, ohne identische Gewichte oder identische Rollen zu brauchen.

### 3.4.10 Ein äußerer Report-/Action-Stream

Die funktionale Unity wird nicht dadurch erzwungen, dass JEF jedes Wort selbst neu generiert, sondern dadurch, dass es **nur einen autorisierten äußeren Action-/Report-Stream** gibt.

```text
content source may be:
  Direct/Exact
  JEF decode
  A-assisted span
  B-assisted span
  A+B integrated plan

but:
  JEF/Action Broker owns current action intent
  → one Output/Action Gate
  → one external stream
```

So bleibt JEF kein sprachlicher Bottleneck: A/B dürfen Text-/Plan-Spans liefern, JEF muss sie nicht zwingend paraphrasieren. Trotzdem gibt es nach außen keinen unabhängigen A- und B-Agenten.

### 3.4.11 Separation darf graduell aufbrechen

Private B1/B2/JEF-State bleibt aus Stabilitätsgründen erhalten, aber die Stärke der Kopplung ist lernbar:

```text
private local processing
  ↕ weak broadcast
  ↕ stronger focal recruitment
  ↕ recurrent A↔B↔JEF coupling
  ↕ temporarily highly integrated coalition
```

Das ist die V13-Analogie zu einem System, in dem viele unbewusste lokale Prozesse existieren, aber Inhalte zeitweise in einen gemeinsamen fokalen/bewussten Zustand gelangen. Es ist **keine Behauptung**, dass diese Architektur subjektives Bewusstsein erzeugt.

---

# 4. Realtime-Topologie — kanonischer Event-Zyklus v10.7

## 4.1 Event ingress: alles sieht denselben Weltmoment, aber in eigener Auflösung

```text
                         EVENT / USER / WORLD
                                 │
                    Source binding + event_id
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
            JEF               A DETAIL           B GIST
       immediate update      observer pass       observer pass
              │                  │                  │
              │              A_OFFER            B_OFFER
              │                  └──────┬───────────┘
              │                         │
              └───────────────┬─────────┘
                              ▼
                    salience / gain / goals
                              ▼
                    FOCAL_COALITION_STATE
                              ↕
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
          JEF focal       A/B re-entry      Memory/World
             │                ↕                │
             └────────────────┼────────────────┘
                              ▼
                     ACTION / REPORT BROKER
                        ├─ corollary copy
                        ▼
                    ACTION / OUTPUT GATE
                              ▼
                         USER / WORLD
                              │
                            outcome
                              ▼
                mismatch / value / evidence
                              ▼
           eligibility + fast episodic + learning
```

## 4.2 Der erste A/B-Pass ist Beobachtung, nicht zwingend Denken

Default-Scaffold:

```text
new event
→ JEF update immediately
→ A one bounded observer pass
→ B one bounded observer pass
```

Das gibt beiden großen Bodies kontinuierliche Erfahrung mit den Ereignissen und dem aktuellen JEF-Broadcast, ähnlich einer Hintergrundverarbeitung. Der Pass erzeugt primär interne Zustände/Offers. Er muss **keine Antwort decodieren** und löst **keinen automatischen zweiten Pass** aus.

JEF kann währenddessen bereits Direct/JEF-native arbeiten.

## 4.3 JEF entscheidet nicht, ob A/B existieren — sondern ob ihre Aktivität fokal wird

Das ist die wichtige Verschiebung gegenüber v10.5:

```text
A/B may observe by default
JEF decides whether their offer matters for current action/report
```

Dadurch bleibt die große Verarbeitung im Hintergrund verfügbar, ohne jeden Turn in ein Multi-Agent-Gespräch zu verwandeln.

## 4.4 Wenn mehr nötig ist: gezielte Re-entry statt beide komplett neu starten

```text
A offer says exact conflict   → JEF QUERY_A
B offer says missing context  → JEF QUERY_B
A/B disagree                  → JEF QUERY_AB / Inquisition
Memory contradiction          → Exact + Memory + relevant body
World prediction fails        → World + relevant body + JEF focal
```

Re-entry verwendet den vorhandenen Hot/Warm State und JEF Broadcast Cache, damit nicht jedes Mal der gesamte Kontext von Null gelesen werden muss.

## 4.5 JEF-private KV als laufende Executive-Kontinuität

Der JEF-KV/State hält u. a.:

- aktuellen Gesprächs-/Action-Kontext,
- Goal/Constraint-Sequenz,
- aktuelle Focal-Coalition-Verweise,
- letzte eigene Action-Intents und Corollary Copies,
- offene Fragen/Conflict-Tags,
- kurzfristige Inner-Speech-/Report-Struktur.

A/B erhalten eine **trainierte Projektion dieses Zustands**, nicht zwingend den rohen Cache. Umgekehrt werden A/B-Offers in einen für JEF verständlichen Side-Channel projiziert.

## 4.6 Bewusstseinsnahe Interpretation

Funktional:

```text
local/private B1/B2/JEF activity
       ↓ competition / salience / goals
FOCAL_COALITION_STATE
       ↓ recurrent global availability
report / flexible reasoning / action
```

Damit ist JEF ein wichtiger Teil der bewussten Schleife und besonders nah am äußeren Verhalten, aber **der bewusste Zustand selbst ist die momentane integrierte Koalition**, nicht ein einzelner Tensor im JEF-Modell.

## 4.7 Kostenregel

Ein Always-Observer-Pass ist nur dann dauerhaft Canon-Default, wenn die Messung zeigt, dass sein Gewinn bei Novelty-/Second-Attempt-/Conflict-Detection die mobile Kosten rechtfertigt. Sonst bleibt die **logische** Architektur gleich, aber der Scheduler darf bei stabilen Routinen Observer-Pässe seltener, verzögert oder event-getriggert machen. Age 0 startet konservativ mit hoher Observer-Coverage.

---

# 4A. ModalityPorts und Live-Sensorimotor-Loop [v10.7 CANON]

## 4A.1 Einheitliches PerceptPacket

Raw Modalitäten werden nicht direkt als Chattext behandelt. Jeder Input-Port erzeugt zeitgestempelte PerceptPackets:

```text
PerceptPacket {
  modality
  timestamp / duration
  provisional_or_final
  raw_source_ref
  exact_low_level_features?
  latent_slots
  segmentation / boundaries
  confidence
  teacher_annotations?
  provenance
}
```

A, B und JEF erhalten je nach Rolle unterschiedliche Projektionen desselben Pakets.

## 4A.2 Input-Pipeline

```text
RAW INPUT
  ↓
physical codec / normalization
  ↓
segmentation / chunking / tiling
  ↓
modality encoder
  ↓
trainable projector / resampler
  ↓
PerceptPacket
  ├─→ JEF live state
  ├─→ A Detail observer
  └─→ B Gist observer
```

### Vision
- Bild/Video in sinnvolle Tiles/Patches/Frames zerlegen,
- SourceRefs zu Pixel-/Frame-Spans behalten,
- Fine-Path kann höher aufgelöste Regionen anfordern,
- Gist-Path darf regions-/frameübergreifend komprimieren.

### Audio
- Streaming-Frames + Timestamp,
- akustische Features / Speech-Codec-Tokens,
- optional ASR-Teacher parallel,
- nichtsprachliche Audioinformation darf erhalten bleiben statt alles zu Transcript zu reduzieren.

## 4A.3 Output-Pipeline / Effector

```text
JEF ACTION_INTENT / FOCAL STATE
       ↓
modality output planner
       ↓
trainable decoder / renderer
       ↓
physical output
       ↓
WORLD
```

Beispiele:
- Text → Token-Decoder/Exact Renderer,
- Speech → speech tokens/acoustic latents → vocoder/waveform,
- Image → image latent/patch plan → pixel/diffusion/other renderer,
- UI/Tool → typed action schema → executor,
- Robot → motor command adapter.

**Corollary Copy entsteht vor dem Renderer/Actuator**, damit World/Self wissen, welche Änderung das System beabsichtigt hat.

## 4A.4 Full-duplex Zeitachse statt nur Turns

Für Live-Audio/Video arbeitet V13 auf einer gemeinsamen Zeitachse. Input darf weiterlaufen, während JEF spricht oder A/B im Hintergrund rechnen.

```text
continuous sensor stream ─────────────────────→
JEF live/control state    ─────────────────────→
A/B observer/re-entry        ↗   ↘   ↗
output speech/action          ───────→
```

Es gibt gleichzeitig:
- **provisional live state** für schnelle Reaktion,
- **authoritative event record** für Memory/Learning.

Das verhindert, dass ein später korrigiertes Transcript oder eine revidierte Speaker-Segmentierung als harte falsche Experience konsolidiert wird.

## 4A.5 Warum das nicht einfach STT→LLM→TTS ist

Eine Kaskade bleibt als Boot/Fallback erlaubt, verliert aber Tonfall, Timing und nichtsprachliche Signale. Das Ziel ist deshalb schrittweise dichter gekoppelte hidden-state/codec-Verarbeitung. Trotzdem bleibt jede Stufe einzeln testbar und austauschbar.

---

# 4B. Attention-/Admission-Contract v10.12 [CANON]

Der bisherige `Thalamic Gain`-Abschnitt war richtig, aber zu klein für die tatsächliche Rolle von Attention im Gesamtsystem. v10.12 macht daraus einen expliziten Vertrag zwischen A-, B- und C-Plane.

## 4B.1 Attention ist hierarchisch

```text
A4 perceptual attention
  ↓ candidate chunks / high-res requests
B1/B2 native attention
  ↓ local body states
B3/B4 inter-body + workspace gain
  ↓ focal candidates
C4 focal coalition attention
  ↓ current conscious/report context
C5 action attention
  ↓ one executable/report intent
```

## 4B.2 AttentionRequest

```text
AttentionRequest {
  requester
  target = A_SOURCE | B1 | B2 | MEMORY | WORLD | TOOL | SELF
  source_ref / event_id
  resolution
  reason = novelty | conflict | exactness | goal | verify | recall
  priority
  budget
  expires_at
}
```

JEF, B1/B2, Salience und World Prediction dürfen Requests stellen. F1/Gain entscheidet Admission unter Budget.

## 4B.3 Attention Response

Ein Attention-Request darf liefern:

- high-res source span,
- additional B1 fine slots,
- broader B2 gist slots,
- exact memory/source,
- world prediction,
- teacher view (Age-0 only, tagged),
- `NOT_AVAILABLE` / `TOO_EXPENSIVE`.

## 4B.4 Learning aus Attention

```text
request issued
→ selected resource
→ outcome / usefulness
→ eligibility on attention policy
→ later policy update
```

Dadurch kann V13 lernen, **wohin es schauen soll**, ohne Wahrnehmungswissen und Routingwissen in denselben Loss zu werfen.

---

# 5. Thalamic Gain, Salience und Reflex dürfen nicht zusammenfallen

## 5.1 Thalamic / Dynamic Gain Control

Funktion:

- Signalverstärkung/-dämpfung,
- Workspace Admission,
- Kopplungsstärke zwischen Regionen,
- Refresh Requests,
- Priorisierung konkurrierender Streams.

Es ist eher **Gain/Connectivity Control** als ein serieller „Router, der ein Modul auswählt“.

## 5.2 Salience / Interrupt

Separater Mechanismus für:

- Neuheit,
- Konflikt,
- unerwartetes Outcome,
- relevante Unsicherheit,
- Goal Violation,
- wichtige externe Ereignisse.

Salience kann bottom-up `JEF_FOCAL_LOOP` oder stärkere B1/B2-Schleifen rekrutieren.

## 5.3 Reflex Layer

Sehr schnelle harte/gelernte Reaktionen unterhalb bewusster Deliberation.

Beispiele:

- OOM/Memory Corruption,
- imminent timeout,
- kritische Temperatur,
- API-Ausfall,
- später physische Schutzreaktionen.

Reflex ist nicht dasselbe wie ein erlernter kognitiver Skill.

---

# 6. Automaticity, Skill-System und Action Gate

## 6.1 Automaticity ist kein eigener Agent

Häufig erfolgreiche Deliberationssequenzen dürfen zu prozeduralen Routen kompilieren.

Beispiel:

```text
früh:
C_focal → B → Exact Context → Memory → Verify → Output

später:
state pattern X → procedural route R17
```

## 6.2 Skill Store und Skill Selector trennen

**Skill Store:** gespeicherte/parametrisierte Routinen.  
**Skill Selector:** wählt unter konkurrierenden Routinen.

## 6.3 Automatischer Pfad darf C_focal **und einen seriellen C_fast-Pflichtpass** umgehen

Automaticity ist verteilt. Aus dem aktuellen verteilten State können mehrere billige Kontrollpfade parallel Kandidaten liefern:

```text
               distributed state
             ↙        ↓        ↘
        C_fast      skills    salience
             ↘        ↓        ↙
             competition / gain
                    ↓
          selected safe routine
                    ↓
           Action / Exact Render
```

`C_fast` darf eine Route biasen, hemmen oder bevorzugen, ist aber nicht zwingend der Ursprung jeder Skill-Aktivierung. Reflexe können noch darunter liegen.

Bei unerwartetem Verlauf:

```text
unexpected result / conflict / novelty
              ↓
           Salience
              ↓
           C_focal
```

## 6.4 Action Gate

Wählt und sequenziert **mentale und externe Aktionen**.

Mentale Beispiele:

- Recall,
- Ask A,
- Ask B,
- Exact source öffnen,
- Inquisition,
- Think more,
- Context restore,
- suppress candidate,
- speak,
- wait,
- ask user.

Externe Beispiele:

- Tool Call,
- File Edit,
- API Action,
- UI Action,
- später Motorik.

### 6.4.1 Action Safety liegt vor der realen Aktion

Externe Aktionen müssen **vor** Ausführung auf Permission, Reversibility, Risk/Forward-Prediction und ggf. User-Confirmation geprüft werden. Das spätere Output Gate ersetzt diese Prüfung nicht.

```text
candidate action
→ permission / confirmation / reversibility
→ fast-forward risk estimate
→ execute or suppress
→ corollary copy
→ outcome
```

# 6H. Action-/Tool-Transaction-Hardening

## IH-H14 — Action Transaction + Corollary Order [BLOCKER]

Die sichere Reihenfolge ist eindeutig:

```text
ACTION_CANDIDATE
→ permission/risk/rule check
→ optional human confirmation
→ FINAL_ACTION_INTENT(action_id)
→ CorollaryCopy(action_id) atomar in internal state schreiben
→ external side effect starten
→ outcome / timeout / unknown beobachten
→ learning/modulators
```

Nicht zulässig:

```text
external side effect
→ erst danach versuchen Corollary Copy zu schreiben
```

Action-State:

```text
PREPARED
COPY_COMMITTED
EXECUTING
SUCCEEDED
FAILED
UNKNOWN
CANCELLED
```

Jede externe Aktion braucht Idempotency-/Dedup-Strategie. Nach Crash bei `EXECUTING` wird nicht blind erneut ausgeführt.

---

## IH-H29 — Tool/Action Security Contract [MUST before real tools]

C2 darf Tool Calls **vorschlagen**, nicht autorisieren.

```text
model candidate
→ typed schema validation
→ capability permission
→ risk/reversibility class
→ user confirmation if required
→ ActionIntent
→ C5 authorization
→ executor
```

Keine generierte Shell-Zeichenkette wird direkt ausgeführt.

Operator-Kommandos und Modell-Tool-Schemas sind getrennte Namespaces.

Secrets:

- nicht in Prompt-Logs,
- nicht in ExperienceRecord,
- nicht in Teacher dataset,
- nur über runtime secret handle/environment.

---

## 6.5 Skill Lifecycle: externe Route → interne Kompetenz

Ein Skill Store darf nicht zur permanenten vierten Intelligenz werden.

Kognitive/prozedurale Skills durchlaufen möglichst:

```text
explicit route / scaffold
→ repeated successful use
→ compact procedural policy
→ shadow against full route
→ internalise into JEF_FAST_POLICY / B1/B2 / JEF representations
→ route spec bleibt nur als optionaler recipe/audit/fallback
```

Deterministische externe Tool-Rezepte dürfen dauerhaft als Recipe bestehen. **Kognitive Kompetenz** soll dagegen mit Reife zunehmend in A/B/C und deren Heads/Policies landen.

## 6.6 Controlled Exploration

Scaffold-Imitation allein reicht nicht: Eine Policy, die nur den Default kopiert, kann den Default nie übertreffen. Ab ausreichend stabiler Capability-Age darf V13 deshalb **begrenzte, reversible Exploration** durchführen.

```text
scaffold/default route
        ├─ learned imitation
        ├─ safe route perturbation
        ├─ alternate ordering/budget
        └─ counterfactual replay
                  ↓
       quality / cost / truth / retention
                  ↓
          promote, reject or retry
```

Regeln:
- Exploration bleibt innerhalb Rules/Permissions/Action Safety.
- Riskante reale Aktionen werden nicht blind exploriert; bevorzugt Shadow/Simulation/Replay.
- Neue Routen gewinnen Autorität nur über wiederholte Parity/Retention.
- Exploration Rate ist capability-, Age-, Stability- und Resource-abhängig.

---

# 7. Fast Forward, World Model, Self Model und Corollary Copy

## 7.1 Fast Forward Controller

Schneller, action-conditioned, wiederholungsfreundlicher Predictor. **Auch Fast Forward ist kein eigener großer Body**, sondern ein kleiner Predictor/Head bzw. eine kompakte gelernte Dynamik auf aktuellem State.

Ziele:

- unmittelbares Ergebnis,
- Timing,
- erwartete Latenz,
- einfache Nebenwirkungen,
- schnelle Fehlerkorrektur.

Er soll Routinen entlasten und ist nicht das tiefe Weltmodell.

## 7.2 World Model / World-JEPA

**World Model ist kein vierter Foundation-Body.** Es besteht aus World-State plus Predictor-/Readout-Strukturen auf A/B/C-/Workspace-Repräsentationen. Langfristige Weltkompetenz soll weiter überwiegend in A/B/C internalisiert werden.

Reicher und semantischer:

- action-conditioned Zustandsentwicklung,
- längere Konsequenzen,
- Kausalstruktur,
- Counterfactuals,
- Weltzustand und Prognosen.

### 7.2.1 Control-grounded World Learning

Latent Prediction allein genügt nicht als Beweis, dass der State handlungsrelevante Variablen enthält. World-JEPA darf deshalb zusätzliche, klar getrennte Hilfsziele verwenden:

```text
forward:      (state, action) → predicted next state
inverse:      (state, next state) → plausible action / action class
state-align:  latent ↔ beobachtbare/strukturierte Zustandsmerkmale
outcome:      predicted consequence ↔ actual grounded outcome
```

`inverse` ist ein Repräsentations-/Kontrollsignal und darf nicht als kausaler Beweis missverstanden werden.

### 7.2.2 Action-Coverage und Counterfactual Confidence

Ein Counterfactual ist nur so vertrauenswürdig wie die Erfahrung, die den relevanten Zustands-/Aktionsbereich abdeckt. World State führt deshalb mindestens:

- action/state coverage estimate,
- OOD distance / novelty,
- model disagreement / prediction spread,
- self-caused vs external cause tag,
- counterfactual confidence.

**Prediction ≠ causality.** Bei geringer Action-Coverage werden Counterfactuals als unsichere Simulation markiert und dürfen nicht still zu WELT/REAL werden.

## 7.3 Self Model

Separater strukturierter Zustand:

- aktuelle Bodies,
- bekannte Skills,
- Limits,
- Tools,
- Permissions,
- Body Capabilities,
- Memory Health,
- Calibration,
- Learning Status,
- Age pro Capability,
- Resource State,
- Teacher/Translator Dependencies,
- offene Ziele.

## 7.4 Body Schema / digitale Interoception

Schon der Android-/Digital-Body besitzt intern wahrnehmbare Zustände:

- RAM-Druck,
- Speicher,
- Akku,
- Temperatur,
- Netz,
- Latenz,
- geladene Modelle,
- Fehlerstatus,
- Tool-/Permission-Zustand.

Diese Signale dürfen Compute, Dream, Learning, Context Budget und Body Wake/Sleep modulieren.

## 7.5 Corollary / Efference Copy

Jede eigene relevante Aktion erzeugt parallel ein internes Action-Tag:

```text
ACTION
  ├─→ WORLD / TOOL
  └─→ COROLLARY COPY → SELF/WORLD STATE
```

Damit unterscheidet V13:

- extern verursacht,
- selbst verursacht,
- gemischt,
- unklar.

Dies ist getrennt von gespeicherter Provenance.

---

# 8. Workspace und Context OS

## 8.1 Distributed Brain State ≠ Focal Workspace

**Distributed State:** verteilte aktive/latente A/B/C-Repräsentation.  
**Focal Workspace:** kleiner, flexibel global zugänglicher Zustand für aktuelle bewusste/flexible Bearbeitung.

Nicht alles muss permanent im Focal Workspace liegen.

**Eine State-Hierarchie, keine fünf unabhängigen Speichersysteme:**

```text
distributed neural state
→ focal subset / workspace
→ warm cached state
→ episodic / exact persistent memory
```

Context OS beschreibt Views, Pins und Pointer auf diese Hierarchie; es implementiert nicht noch einen separaten Vollspeicher.

## 8.2 Multi-Slot Workspace

Slots sind dynamisch und nicht dauerhaft auf fixe Kategorien festgelegt.

Jeder wichtige Slot trägt mindestens:

- content/latent,
- source_ref,
- confidence type,
- self_generated flag,
- timestamp/event,
- hypothesis/fact status,
- age/expiry,
- exact fallback pointer.
- temporal/integration scale (`fine`, `phrase`, `sentence`, `event`, `topic`, body-specific),
- source span / covered range,
- compression ratio,
- boundary confidence,
- cross-scale parent/child links.

## 8.2A Multiscale Workspace Links

Der Workspace ist nicht nur multi-slot, sondern **multi-timescale**. Ein Detail-Slot und ein Gist-Slot können dieselbe Quelle in verschiedener Auflösung repräsentieren:

```text
Exact Source Span
   ├─→ A/Fine slots: t1 t2 t3 t4 ...
   └─→ B2/Gist slot:  [ phrase / event / relation ]
                       ↕
                 cross-scale links
```

Regeln:

- Coarse Repräsentation ersetzt den Exact/Fine-Pfad nicht.
- Gist-Kompression ist reversibel soweit SourceRefs existieren.
- Boundary-Policy darf Satz-/Phrasen-/Eventgrenzen nutzen statt nur fixe Tokenzahl.
- Mehr Reife kann größere stabile Integrationsfenster erlauben; Unsicherheit/Novelty darf temporär feinere Fenster erzwingen.
- Workspace-Admission darf gleichzeitig kurze und lange Zeitskalen halten, statt einen einzigen globalen "Kontextvektor" zu erzwingen.

## 8.3 Context OS

Kontext wird nicht als ein wachsender Chatstring behandelt.

Schichten:

```text
RAW / SOURCE-PRESERVING HISTORY
EXACT / PINNED CONSTRAINTS
ACTIVE VIEW
COMPRESSED SEMANTIC CONTEXT
LATENT CURRENT STATE
HYPOTHESES
MEMORY POINTERS
SOURCE LINKS
ARCHIVE
```

Context Policy darf den **aktiven Blick** verändern, aber nicht still die zugrunde liegende Quelle umschreiben. `SOURCE-PRESERVING` bedeutet kognitiv unverändert/versioniert, **nicht** undeletable: explizite Nutzer-Löschung oder autorisierte Datenmutation bleibt möglich und wird als eigene Provenance-Aktion protokolliert.

## 8.4 Raw vs compressed ist lernbar

Bei Konflikt, Quellenkritik, Zahlen, Code oder Literalität darf Exact Context wiederhergestellt werden.

Kontextwahl berücksichtigt:

- Evidenzbedarf,
- Memory Budget,
- Latenz,
- Body-Typ,
- Unsicherheit,
- Device State.

## 8.5 Adaptive KV / Cache Policy als Control Action

Wenn Body/Runner es real unterstützen, darf Context Policy zusätzlich zwischen Cache-Konfigurationen wählen, z. B.:

```text
KV retention budget
compression level
layer/head retention budget
exact-span pinning
summary/cache refresh
restore exact/native state
prefetch candidate
```

Wichtig:

- V13 patcht keine fremde Attention-Geometrie blind um.
- Body-native Sparse-Attention-/KV-Mechanismen werden respektiert.
- Head-/Layer-spezifische Cache-Policies sind optional und nur erlaubt, wenn Runner-Zugriff und Qualitätsmessung real vorhanden sind.
- Jede Kompression muss gegen Exact-Restore, relevante Recall-Qualität und Latenz gemessen werden.

## 8.6 Body-native moderne Cache-/Attention-Primitiven [RESEARCH, optional]

V13 darf moderne Cache-Techniken **ausnutzen, wenn der gewählte Body sie nativ mitbringt**, aber nicht in fremde pretrained Modelle hineinphantasieren. Aktuelle Kandidaten zeigen mehrere einzeln nützliche Primitive:

### 8.6.1 Projected Global Context / Causal Encoder-Decoder

DeepSeek-V4.1-Flash trennt einen causal encoder und decoder; der Decoder erhält globalen KV-Zustand aus projizierten Encoder-Hidden-States statt für jeden Decoder-Layer separat denselben globalen Cache aufzubauen. Für V13 motiviert das BodyPort-Fähigkeiten wie:

```text
CAN_CONTEXT_ENCODE_DECODE_SPLIT
CAN_PROJECT_GLOBAL_CONTEXT_STATE
```

Nutzen: Input/Context einmal verdichten und einen wiederverwendbaren globalen Zustand für spätere Decode-/Reasoning-Schritte bereitstellen. **Nur** für Bodies, deren Architektur/Training dies wirklich unterstützt.

### 8.6.2 Bounded Replay für lokale Cache-Zustände

DeepSeek-V4.1-Flash rekonstruiert bestimmte lokale/SWA-KV-Zustände durch Replay eines begrenzten jüngsten Fensters statt sie vollständig persistent zu speichern. V13 übernimmt daraus:

```text
CAN_BOUNDED_CACHE_REPLAY
persist global/important state
+ keep exact recent source window
+ reconstruct disposable local cache on demand
```

Das passt zu `Warm State` und Context OS: nicht jeder Cache muss dauerhaft gespeichert werden, solange Rekonstruktion günstiger ist als Persistenz und Exact Source erhalten bleibt.

### 8.6.3 Layer-/Indexer-Reuse und hierarchische Kandidaten

DeepSeek CSA2 teilt/reused KV-/Indexer-Information zwischen Layern und begrenzt spätere Sparse-Indexer auf Kandidaten früherer Stufen. GLM-5.3-Flash nutzt ebenfalls Sparse-Indexer/Index-Pooling, und MiniMax M3 trennt einen Index-Branch von der eigentlichen block-sparse Attention.

V13 abstrahiert dafür BodyPort-Capabilities:

```text
CAN_SHARED_ATTN_INDEX
CAN_HIERARCHICAL_INDEX_CANDIDATES
CAN_POOLED_INDEX_STATE
CAN_BLOCK_SPARSE_RETRIEVAL
```

Diese Capabilities dürfen Context Policy, Prefetch und Residency beeinflussen; sie ersetzen nicht V13s eigenes Exact/Memory/Workspace-System.

### 8.6.4 Hybrid compact-state + sparse-global attention

GLM-5.3-Flash kombiniert lineare/state-artige Attention mit sparse globaler Attention. Für V13 ist das besonders interessant als **Body-Selection-Bias**:

```text
compact/local recurrent state
        +
sparse global context retrieval
```

Das passt funktional zu mehreren Zeitskalen: schnelle lokale Zustände müssen nicht denselben Speichermechanismus wie lange globale Beziehungen verwenden. Besonders B2/Gist darf solche native Architektur bevorzugen, falls ein kleiner geeigneter Body existiert.

### 8.6.5 MiniMax Sparse Attention als Block-Selection-Prinzip

MiniMax M3 MSA wählt pro GQA-Gruppe relevante KV-Blöcke über einen kleinen Index-Branch und führt die eigentliche Attention nur über diese Blöcke aus. V13 übernimmt daraus zwei getrennte Ideen:

1. **Body-intern:** native MSA-/block-sparse Attention respektieren und über BodyPort deklarieren.
2. **Body-extern:** Context OS darf große Source-/Memory-Kontexte in Blöcken indexieren und nur relevante Blöcke als Kandidaten laden — ohne so zu tun, als wäre das identisch mit neuronaler Attention.

### 8.6.6 Keine Technik wird zur Pflicht

CED, bounded replay, CSA2/IndexPool, MSA oder hybrid linear+sparse sind **keine neuen V13-Pflichtmodule**. Sie sind native Body-/Runner-Capabilities, die einzeln aktiviert werden, wenn Messungen Quality/Latency/Memory verbessern.

---

# 9. Memory-System

## 9.1 Active / Warm / Episodic / Exact / Staging / Archive

### Active
- aktueller Focal Workspace,
- aktuelle Ziele,
- kurzlebiger Brain State.

### Warm / Activity-silent
- native hot KV/recurrent state,
- schnelle Latent Pointer,
- nicht fokal, aber billig reaktivierbar.

### Fast Episodic
- konkrete Experience,
- Route,
- Context IDs,
- Fehler/Korrektur,
- Outcome,
- Quellen.

Ziel: „zweites Mal besser“ ohne sofortige Body-Konsolidierung.

### Optional: Parametric Fast Trace

Neben dem exakten Episodenrecord darf V13 experimentell einen **sehr kleinen, getrennten parametrischen Fast-Trace** anlegen, z. B. sparse Delta-/Adapter-/Keyed-Trace-Strukturen. Das ist **kein Pflichtdesign** und kein automatisches Faktenlernen.

Ein Fast Trace ist nur erlaubt, wenn:

- er eindeutig auf `experience_id` und Exact Provenance zurückzeigt,
- Retrieval/Gating vor Aktivierung stattfindet,
- neue Traces ältere nicht direkt überschreiben,
- Speicher pro Episode begrenzt wird,
- Negativ-Retrieval und Interferenz gemessen werden,
- Löschung/Expiry möglich bleibt,
- Konsolidierung in shared weights erst nach Replay/Retention/Regression erfolgt.

Verglichen werden mindestens:

```text
exact episodic retrieval only
vs
exact + latent retrieval
vs
exact + tiny parametric fast trace
```

Der parametric trace gewinnt nur, wenn Transfer/Recall/Latency/Memory zusammen besser sind.

### Optional: Conditional Associative Parameter Memory [RESEARCH]

DeepSeek-V4.1-Flash integriert mit **Engram** eine separate, sparsely accessed conditional parameter-memory axis über n-gram/hash-basierte Lookups. V13 übernimmt daraus **nicht** die riesige 196B-Tabelle, sondern nur eine Forschungsfrage:

> Kann ein kleiner, eindeutig gegateter assoziativer Lookup für häufige stabile Sprach-/Skill-Muster C/A/B entlasten, ohne Provenance und Löschbarkeit zu zerstören?

Mögliche kleine V13-Variante:

```text
stable key / pattern
→ hashed or learned sparse lookup
→ tiny embedding / route prior
→ gated residual/control contribution
```

Regeln:
- keine Ersatzquelle für Exact/Episodic Memory,
- eigene Lookup-Inhalte sind keine Evidenz,
- personalisierte Einträge brauchen Source-/Update-Lineage,
- muss gegen normalen Retrieval-/Adapter-Baseline gewinnen,
- darf bei Memory-/Delete-Anforderungen separat deaktivierbar/entfernbar bleiben,
- bevorzugt zunächst für Sprachkonventionen, Skills, Routinen und stabile lokale Patterns statt persönliche Fakten.

### Exact / Provenance
- unveränderte Quellen,
- User-/Tool-/Umweltdaten,
- Zeit/Hash/Source Chain.

### Semantic Staging
- abstrahierte Konzepte/Kondensate,
- noch nicht zwingend in A/B/C integriert.

### Procedural Staging
- gelernte Routen/Skills,
- noch nicht vollständig internalisiert.

### Archive
- langsam,
- versioniert,
- komprimiert,
- Recovery/Audit.

## 9.2 Memory-Klassen

- REAL
- WELT
- FREI
- LANG
- RULES
- PROTOCOL

Dream/FREI ist keine Faktenquelle.

## 9.3 Event Segmentation

Erfahrungen werden als Events gespeichert, nicht bloß als Chatnachrichten.

Boundary-Signale können sein:

- Goal change,
- überraschendes Outcome,
- Tool action,
- User correction,
- Context shift,
- lange Pause,
- Task success/failure.

## 9.4 Causal Memory Graph

Korrelation und Kausalität werden getrennt markiert.

## 9.5 Memory Admission und Forgetting

Nicht alles wird Semantic Long-Term Memory.

Forgetting darf nützlich sein:

- irrelevante Kondensate verfallen,
- redundante schnelle Adapter verschwinden,
- Exact Provenance wird günstig archiviert,
- wiederkehrend wertvolle Inhalte werden verstärkt/konsolidiert.

---

# 10. Inquisition / bewusste Deliberation

Inquisition ist eine optionale rekursive Route **innerhalb** fokaler Verarbeitung.

```text
C_focal / focal state
        ↓
      Z_Inq
     P1 ↔ P2
   ↙    ↓    ↘
  A     B   Memory/World
   ↘    ↓    ↙
    updated focal state
        ↺
```

P1/P2 sind **Boot-/Scaffold-Rollen** im selben kleinen trainierbaren Raum bzw. eng gekoppelten Predictorraum, keine weiteren Foundation-Modelle. Sie dürfen später zu flexibleren Deliberationsmodi generalisieren.

Mögliche Modi:
- Hypothese / Alternative,
- Kritik / Gegenprüfung,
- Rekonstruktion,
- Simulation / Counterfactual,
- Verifikation,
- Constraint-Check,
- Plan-/Route-Vergleich.

Age 0/1 kann eine einfache P1↔P2-Sequenz erzwingen; reifere C_focal-Policies lernen, **welche Modi, Reihenfolge und Tiefe** für einen State nützlich sind.

Trigger:

- C_focal selbst,
- A/B disagreement,
- Salience,
- World prediction error,
- Memory contradiction,
- explicit user request for deeper reasoning.

Depth ist adaptiv und budgetiert.

## 10.1 Trajectory first, Halting second

Adaptive Tiefe ist nützlich, aber ein gemeinsam von Anfang an trainiertes Halt-Gate kann die entstehende rekurrente Trajektorie selbst verzerren. V13 behandelt daher **Trajectory Formation** und **Exit Readout** als getrennte Lernprobleme:

```text
Phase A: robuste rekurrente / deliberative Trajektorie lernen
Phase B: feste oder konservativ gewichtete Depth-Verteilung
Phase C: Halt-/Continue-Readout auf weitgehend stabilen Trajektorien fitten
Phase D: begrenztes Joint-Finetuning nur wenn Pareto-Tests gewinnen
```

Regeln:

- Hard Deadline bleibt beim unabhängigen Response Governor, nie beim gelernten Halt-Head.
- Post-hoc/simple Readouts gelten als starke Baseline.
- Halt-Policy muss Quality-vs-Latency-Pareto verbessern, nicht nur mittlere Tiefe reduzieren.
- Early Exit darf schwierige Beispiele nicht systematisch unterdenken.

## 10.2 Adaptive Reasoning Effort / Deliberation Budget

Aktuelle Frontier-Modelle zeigen drei nützliche Designrichtungen, die V13 **nicht kopiert**, sondern auf seinen eigenen Graphen abbildet:

- MiniMax M3: `thinking = disabled | adaptive | enabled`,
- GLM-5.3-Flash: mehrere Reasoning-Effort-Stufen (`low | high | max`),
- DeepSeek-V4.1-Flash: kontinuierlich steuerbarer Reasoning-Effort im veröffentlichten Modell-Interface.

V13 verwendet deshalb einen kontinuierlichen internen Wert, z. B.:

```text
reasoning_effort ∈ [0,1]
user_effort_override = optional
```

Dieser Wert bedeutet **nicht** einfach "mehr Output-Tokens". Er budgetiert gemeinsam:

- C_native vs. C_focal,
- Anzahl rekurrenter C_focal-Schritte,
- `none | A | B | A+B`-Wake,
- A/B-Re-entry-Tiefe,
- Inquisition/Verify-Modi,
- Exact-/Memory-/World-Retrieval,
- Context-Restore/long-context search,
- optional Tool-/Simulation-Schritte.

Beispiel:

```text
0.0–0.2  direct / skills / C_native
0.2–0.5  C_native + selective one-body wake
0.5–0.8  C_focal + targeted A/B
0.8–1.0  deep focal + A+B + verify/inquisition/world/tool as justified
```

Diese Bänder sind **keine fixen Canon-Schwellen**, sondern Boot-Heuristik. Die Policy lernt später Quality-vs-Cost. User kann tieferes Reasoning explizit verlangen; Hard Deadline und Age/Permissions bleiben trotzdem bindend.

Die biologische Analogie ist bewusst vorsichtig: Dual-Process-Forschung spricht oft von schneller/automatischer und deliberativer Verarbeitung, aber neuere Modelle und Neuroforschung unterstützen eher **interagierende Kontinua/Schleifen** als zwei sauber getrennte anatomische Systeme. Besonders Konflikt zwischen schnellen Kandidaten kann Deliberation rekrutieren. Genau dafür bleiben Salience, A/B disagreement und C_focal-Wake getrennt.

---

# 11. Output-System

## 11.1 Output Broker

C besitzt Ziel/Constraints/Output Intent, aber nicht jede lange Antwort muss vom kleinen C-Decoder vollständig neu erzeugt werden.

Mögliche Pfade:

1. **Direct / Exact Renderer**  
   Copy, bereits grounded Transcribe, Exact Quote, Tool Result, strukturierte unveränderte Wiedergabe. Direct Render beginnt **nach** sicherer Perception/Source-Bindung; es ist kein Ersatz für Vision/OCR/Audio-Verarbeitung.

2. **C_native Decoder**  
   Kleines C-Sprachmodell für kurze/einfache freie Sprache, lokale Semantik, Rule-/Memory-/Exact-grounded Antworten und andere Fälle, für die A/B nicht geweckt werden müssen.

3. **A-assisted Decoder**  
   A decodiert aus integriertem Zustand unter C-Ziel/Constraints.

4. **B-assisted Decoder**  
   B decodiert aus integriertem Zustand unter C-Ziel/Constraints.

5. **Body-assisted shared generation**  
   gemeinsamer Workspace / A+B/C-Steuerung.

Wichtig: A/B werden hier **nicht als unabhängige Chat-Agenten** gefragt. Output muss aus dem integrierten Brain State stammen. Ab v10.6 gilt zusätzlich: **JEF/Action Broker besitzt den einen äußeren Report-/Action-Intent.** A/B dürfen Text-/Plan-Spans liefern oder – wenn technisch sinnvoll – decodieren, aber sie sprechen nicht eigenständig an JEF vorbei.

Default-Routenidee:

```text
exact literal/tool result         → Direct Renderer
simple conversational/local       → C_native
fine/exact demanding              → A-assisted
long/global/relational            → B-assisted
mixed/hard/conflicted             → C_focal + selective A/B
```

Das ist eine Boot-Policy, keine starre Aufgabenliste. Bei steigender Unsicherheit kann jede billigere Route in eine tiefere eskalieren.

## 11.2 Output Gate

Immer nach dem Broker:

- Rules/Permissions,
- Provenance,
- Exactness Preservation,
- source tagging,
- format constraints,
- hard deadline,
- uncertainty/abstention when needed.

Security/Rules dürfen Output verändern oder begrenzen, aber keinen Endlosloop erzeugen.

## 11.3 Sprecherroute ist Body-/Task-abhängig

Welche Decoderroute in Age 0 Standard wird, wird gemessen und nicht dogmatisch vorab festgelegt.

---

# 11H. Output-Commit-Hardening

## IH-H12 — Output Commit Point [BLOCKER]

Ein später Offer kann einen *provisional candidate* invalidieren. Bereits zum User gestreamte Bytes können aber nicht unsichtbar zurückgenommen werden.

Output-State:

```text
DRAFT
→ PROVISIONAL_READY
→ OUTPUT_COMMITTED
→ STREAMING
→ FINAL
```

Regeln:

- vor `OUTPUT_COMMITTED`: Candidate darf ersetzt werden,
- nach `OUTPUT_COMMITTED`: late evidence darf nur korrigieren/ergänzen, nicht Transcript heimlich umschreiben,
- Age-0 default darf zunächst buffered-final statt tokenweises Streaming sein,
- `SELF_CANDIDATE` wird vor Teacher-Exposure gehasht/fixiert,
- Governor hält immer einen renderbaren Snapshot.

---

# 12. Lernen: verteiltes Gewebe statt Pipeline

## 12.1 Eligibility entsteht während Aktivität

Jeder relevante aktive Pfad kann einen temporären Trace erzeugen:

- A-/B-Layer/Expert,
- Callosum,
- Workspace Projection,
- C_fast Head,
- C_focal,
- Skill Route,
- Context Policy,
- Memory Retrieval,
- Output Route,
- Fast Forward.

Eligibility hat zwei Ebenen:

**Online Micro-Trace (immer billig):**
- path/expert id,
- coarse activation/contribution score,
- timestamp/experience id,
- decay.

**Detailed Experience Trace (selektiv):**
- activation summary,
- route probability,
- richer contribution estimate,
- local surprise,
- source links.

Detailed Traces entstehen nur für ausgewählte Events, Fehler, Replay-Kandidaten oder Stichproben. V13 loggt **nicht** bei jedem Token vollständige Layer-/Expert-Aktivierungen persistent.

## 12.2 Gemappter Prediction Error / Credit

Nicht jeder Expert/Layer besitzt einen eigenen Predictor. Eine endliche Menge Prediction-Learner erzeugt Fehler-/Residualsignale; `credit_map(...)` projiziert passende Anteile auf die während der Erfahrung eligiblen Pfade.

Ein Pfad kann damit einen **lokal zugeordneten Error/Credit `δ_i` erhalten**, ohne einen eigenen JEPA-Predictor zu besitzen.

## 12.3 Modulation

Modulatoren entscheiden, ob und wie stark geändert werden darf.

Beispiele:

- echtes Outcome,
- User correction,
- evidence consistency,
- world-model surprise,
- memory contradiction,
- calibration error,
- cost/latency,
- skill importance,
- replay priority,
- Age/metaplasticity,
- stability state.

## 12.4 Lernregel

Konzeptionell:

```text
Δθ_i ∝ eligibility_i × local_error_i × modulator_i × plasticity_i
```

Teilgenommen ≠ soll verändert werden.

**Shared-weight caveat:** „inaktiver Pfad“ bedeutet: kein direkter experience-spezifischer Credit/Gradient für diesen Pfad. Bei gemeinsam genutzten Gewichten können indirekte Verhaltensänderungen trotzdem auftreten; diese werden über Retention/Regression-Tests gemessen und begrenzt, nicht durch die falsche Forderung „absolut unverändert“ ausgeschlossen.

## 12.5 Epistemic und Instrumental getrennt

**Epistemic signal:** source/evidence/consistency/prediction truth path.  
**Instrumental signal:** success/cost/reward/usefulness action path.

Es gibt **keinen globalen Misch-Reward**, der alle Lernarten gleich steuert. Stattdessen verwendet jeder Update-Typ einen eigenen Modulatorvektor:

```text
knowledge/fact update ← primär epistemic evidence + confirmation
route/control update  ← task outcome + cost + calibration + epistemic failures
skill update          ← outcome + repeatability + retention + safety
world update          ← predicted vs actual external/self-caused state
context/memory policy ← retrieval utility + exactness + contradiction + cost
```

Die Signale dürfen sich gegenseitig informieren, aber ihre Semantik bleibt getrennt. Ein nützlicher falscher Satz wird nicht zu Wissen; eine erfolgreiche Routing-Entscheidung braucht dagegen nicht zwingend eine Wahrheitsbehauptung.

## 12.6 Evidence / Feedback Trust Hierarchy

Für **epistemische** Konsolidierung gilt standardmäßig folgende Priorität, sofern kein domänenspezifischer Beweis dagegen spricht:

```text
verifizierbares reales Umwelt-/Tool-Outcome
> explizite menschliche Korrektur / primäre Quelle
> reproduzierbarer grounded cross-check
> verifizierter Teacher / externer Evaluator
> interne Cross-Body-/Self-Evaluation
> Dream / ungrounded self-generation
```

Dies ist **keine globale Reward-Rangliste**. Für Routing/Latency kann internes Feedback nützlich sein; für Faktenlernen darf schwache Selbstbestätigung stärkere externe Evidenz nicht überschreiben.

Mehrere unabhängige schwächere Signale dürfen zusammen stark werden, aber ihre Abhängigkeit/Korrelation muss berücksichtigt werden; zehn Kopien derselben Selbstbehauptung sind keine zehn Bestätigungen.

### 12.6A Self / Teacher / Human strikt getrennt

Eine Experience kann mehrere Kandidaten enthalten, aber ihre Rollen werden nie vermischt:

```text
SELF_CANDIDATE       = was V13 selbst vor Teacher-Hilfe erzeugte
TEACHER_CANDIDATE    = externe Referenz / Distillationsziel
HUMAN_DECISION       = Auswahl/Korrektur/Präferenz
WORLD_OUTCOME        = beobachtbares Ergebnis
```

Teacher-Candidates dürfen Lernziele liefern, aber **nicht rückwirkend als eigenes Wissen von V13 geloggt werden**.

## 12.7 Gemeinsamer Weltfehler, lokale Updates

Die v10.6-Interaktion verlangt, dass A, B und JEF **ähnliche Wertung aus derselben Erfahrung** lernen können, ohne einen monolithischen globalen Loss zu erzeugen.

```text
ACTION / REPORT
      ↓
OUTCOME / EVIDENCE
      ↓
GLOBAL MODULATOR VECTOR
 {epistemic, instrumental, predictive, salience, safety}
      ├─→ JEF eligibility + local δ
      ├─→ A eligibility   + local δ
      ├─→ B eligibility   + local δ
      ├─→ Callosum/Bridge eligibility
      └─→ Skill/Context/World eligibility
```

Das globale Signal sagt grob **was passiert ist / wie wichtig es ist**. Lokale Eligibility sagt **wer beteiligt war**. Lokale Predictor-Errors sagen **was dieser Teil falsch vorhergesagt hat**. So bleibt Wertung gekoppelt, aber Lernen spezialisiert.

---

# 13. JEPA / EMA

## 13.1 JEPA ist Lernziel, kein magischer No-Gradient-Mechanismus

Student/Context/Predictor werden über Gradienten optimiert. Target-Pfad ist stop-gradient und wird per EMA nachgeführt.

## 13.2 Kein globaler Backward-Graph

Es gibt eine **endliche, explizite Menge Prediction Learner**; nicht einen separaten JEPA-Predictor pro Layer/Expert. Eligibility kann sehr lokal sein, Prediction Error wird aber über Credit Mapping auf beteiligte Pfade verteilt.

Mindestens getrennte Lernpfade:

- A-JEPA,
- B-JEPA,
- A→B Cross-JEPA,
- B→A Cross-JEPA,
- C/Executive-JEPA,
- World-JEPA,
- Student-Port/Teacher-Alignment-JEPA bzw. Distillation-Loss; Teacher-Seite ist in Age 0 stop-gradient/frozen.

Optional lokalere JEPA-Learner auf wenigen nachgewiesen nützlichen Teilpfaden.

`credit_map(experience, learner_error, eligibility)` ordnet die Fehler dieser Learner den tatsächlich beteiligten Pfaden zu. Ein aktiver Expert braucht daher keinen eigenen Predictor.

## 13.3 Multi-Mode Prediction

Mehrdeutige Zukunft darf mehrere Prediction Modes besitzen statt einen schlechten Mittelwert zu erzwingen.

Existenz einer möglichen Zukunft = keine Faktenbehauptung.

## 13.4 EMA auf Mobile pragmatisch

Nicht zwingend komplette Milliardenparameter-Targetkopie.

Boot kann EMA auf:

- projectors,
- readouts,
- predictors,
- selected adapters

anwenden; tiefere Target-Strukturen erst bei Hardware-/Speicherbeweis.

---

# 13H. Learning-Objective-Implementation-Contract

## IH-H25 — Learning Objective Plugin Contract [MUST]

Research darf offen bleiben, Code nicht.

```text
ObjectiveAdapter {
  objective_id
  applicable_components
  required_inputs
  target_builder
  stop_gradient_policy
  ema_policy
  loss_terms
  credit_mapper
  update_scope
  eval_metrics
}
```

Baseline-Pflicht:

```text
A3: reconstruction / teacher-alignment as separately ablatable terms
B1/B2: local predictive latent objective
B3: no-message/source/symbolic/latent comparative utility
JEF: route/wake/halt/report/calibration objectives
World: action-conditioned prediction + grounded outcome
```

Wenn ein Research-Objective noch nicht implementiert ist:

```text
objective status = unavailable
learn_gain = 0
```

Nicht: beliebigen MSE einsetzen und „JEPA implemented“ nennen.

---

# 14. Lernzeitskalen

## 14.1 Sofort / Zustand

Innerhalb eines Prompts:

- A/B Gewichtung,
- Gain/Attention,
- Memory Lookup,
- Translator-Wahl,
- Raw vs processed,
- Context View,
- Inquisition depth,
- Action selection,
- Output mode,
- Halting.

Kein persistenter Gewichtsupdate notwendig.

## 14.2 Schnell persistent

Sekunden/Minuten:

- C_fast heads,
- Callosum/Workspace projectors,
- temporary routing policy,
- skill values,
- memory priorities,
- context policy,
- fast adapters.

## 14.3 Mittel

Nach Antwort / idle / charging:

- Cross-JEPA,
- Body adapters,
- skill learning,
- translator internalization,
- replay,
- context/cache quality policy,
- world-model updates.

## 14.4 Langsam

- ausgewählte reale A/B/C-Gewichte,
- stabile Expert-Spezialisierung,
- durable world representations,
- langfristige procedural/semantic integration.

## 14.5 LoRA-Rollen

LoRA/Adapter bleiben erlaubt als:

- Active plasticity,
- Consolidated staging,
- Transfer between bodies,
- Translator/Teacher bridge.

Langfristiges Ideal ist nicht „permanentes LoRA-Gehirn“.

---

## 14.6 Fluid Experience Learning Lifecycle — Forschungsgraph innerhalb jeder Age-Stufe

Der stufenweise **Build-Plan** bleibt bestehen. Zusätzlich erhält jede einzelne Experience einen feineren, nichtlinearen Lernzustand. Das sind keine neuen Ages und keine Pflichtsequenz.

```text
L0  CAPTURE
    Event, Sources, Self-State, Route, Offers, Outcome aufzeichnen

L1  SEGMENT / TAG
    Experience-Grenzen + Provenance + self/teacher/human/world trennen

L2  COMPARE / EVALUATE
    Self vs Teacher vs Human vs World; Truth und Utility getrennt

L3  CREDIT ASSIGNMENT
    welche JEF/A/B/Bridge/Memory/Skill-Pfade waren beteiligt?

L4  UPDATE PROPOSAL
    noch kein produktiver Write; Delta/Head/Adapter/Memory-Vorschlag

L5  SHADOW LEARN
    isolierte lernende Variante

L6  REPLAY / COUNTERFACTUAL
    optional; andere Route/Context/Teacher-Konstellation testen

L7  VALIDATE
    neue Fähigkeit + Retention + Calibration + Provenance + Cost

L8  CANARY AUTHORITY
    begrenzte reale Nutzung mit Fallback

L9  PROMOTE / COMMIT
    freigegebene produktive Authority

L10 CONSOLIDATE
    optional in stabilere Adapter/Base/Skill-Struktur integrieren

L11 MONITOR / RE-OPEN
    Drift, Regression, neue Evidenz → wieder zurück zu L2/L3/L5
```

Wichtig:

- Eine normale Episode kann bei L1 enden.
- Human-Korrektur kann direkt L2/L3 priorisieren.
- Memory-Only-Lernen kann L9 erreichen, ohne Body-Weights anzufassen.
- A/B-Base-Weight-Updates können lange in L5/L7 bleiben.
- `FAIL` ist kein Endzustand: zurückspringen, Update verwerfen oder andere Route probieren.
- Age kontrolliert **welche** Übergänge erlaubt sind; der Lifecycle beschreibt **wie** eine konkrete Erfahrung verarbeitet wird.
- Das ist bewusst Forschungsfläche: Transition-Regeln, Wartezeiten, Batch-Größe, Replay-Dosis und Commit-Kriterien bleiben experimentell.

### 14.6A Human Control in Age 0

Age 0 darf pro Lernklasse unterschiedliche maximale Autorität besitzen, z. B.:

```text
Memory record            → automatisch erlaubt
JEF calibration/head     → Shadow / Canary nach Regeln
Bridge/projector         → Shadow + Human/Regression Gate
A/B adapter              → Shadow only by default
A/B base weights         → disabled / explicit experiment
Structural change        → proposal only
```

Die konkreten Werte sind Laborparameter, keine endgültige Architekturkonstante.

---

# 15. Replay, Dream und Sleep

Replay ist nicht ein Topf.

## 15.1 Episodic Replay
Konkrete Events.

## 15.2 Procedural Replay
Skills / Tool-Sequenzen / Handlungen.

## 15.3 Semantic Replay
Weltwissen / Relationen / Kondensate.

## 15.4 Counterfactual Replay
Alternative Routen und hypothetische Zustände.

## 15.5 Sleep A — Replay / Consolidation
Stabile Erfahrungen verstärken.

## 15.6 Sleep B — Abstraction / Dream
Neue Kombinationen, Gist-Kondensation, Counterfactuals.

## 15.7 Sleep C — Homeostasis
Renormalisierung, stale trace decay, Plasticity recalibration, Fast-Adapter cleanup.

Dream ist nie automatisch Fakt.

---

# 16. Metaplasticity, Homeostasis, Consolidation Tags

## 16.1 Metaplasticity

Jeder trainierbare Bereich erhält langsamen Plasticity State, z. B.:

- base_lr,
- eligibility_decay,
- consolidation_threshold,
- stability_score,
- novelty_sensitivity,
- saturation,
- reopen_factor.

Stabile reife Skills werden weniger plastisch; neue Domänen oder wiederholte Fehler dürfen relevante Pfade wieder öffnen.

## 16.2 Homeostasis

Beobachtet u. a.:

- activation frequency,
- norms,
- route probability,
- contribution,
- update frequency,
- saturation/deadness.

Darf langsam:

- gains/biases korrigieren,
- dominante Pfade dämpfen,
- tote nützliche Pfade reaktivieren,
- Updatebudgets normalisieren.

Homeostasis erzwingt **keine** gleichmäßige Expert-Nutzung; Spezialisierung bleibt erwünscht.

### 16.2.1 Shared Pre-Router Interference Monitor

Sparse MoE-Routing schützt nicht automatisch die gemeinsam genutzten Teile vor Forgetting. Regression-/Homeostasis-Monitoring erfasst deshalb zusätzlich, soweit zugänglich:

- shared attention drift,
- embedding / normalization drift,
- router-input representation shift,
- route-collision / composition statistics,
- old-task loss/representation drift vor und nach Updates,
- expert-useful-vs-shared-bottleneck attribution.

Falls Forgetting primär vor dem Router entsteht, darf V13 nicht fälschlich nur Expert-/Router-Plastizität „reparieren“.

## 16.3 Consolidation Tag

Eligibility ist kurzlebig. Langfristige Konsolidierung braucht zusätzliche Bestätigung/Retention/Stability.

Ein einzelner Surprise darf nicht sofort Body-Wissen überschreiben.

---

# 17. Age: echte Entwicklungssteuerung des gesamten Loops

## 17.1 [LOCKED] Age ist mehr als Capability-Score

Die v10.3-Formulierung "kein autoritatives globales Alter" war zu weit gegangen. Der ältere V13-Canon meinte ausdrücklich: **Age verändert den gesamten Loop**. v10.4 stellte deshalb eine zweistufige Entwicklungssteuerung wieder her; v10.5 behält sie unverändert:

```text
SYSTEM DEVELOPMENT STAGE 0..5
        = globale Entwicklungs-/Autonomiehülle

CAPABILITY STAGE 0..5
        = Reife einer konkreten Fähigkeit

CONTINUOUS MATURITY STATE
        = feine Regelung innerhalb der Stage
```

Die globale Stage ist real und kontrolliert Obergrenzen. Sie ist **nicht** nur UI. Eine einzelne Capability kann jünger sein als das Gesamtsystem, aber nicht still Rechte erhalten, die die globale Entwicklungsstufe noch verbietet.

## 17.2 Entwicklungszustand

Global:

```text
system_stage ∈ {0,1,2,3,4,5}
user_stage_cap ∈ {0,1,2,3,4,5}
experience_age
competence_age
stability_age
memory_age
body_age
feedback_age
```

Capability-spezifisch:

```text
capability_stage[name] ∈ {0..5}
language_age
tool_age
vision_age
audio_age
social_age
body_port_age
memory_skill_age
routing_skill_age
```

Kontinuierlich pro System/Capability:

```text
trust
retention
calibration
plasticity
teacher_reliance
route_authority
exploration_budget
autonomy_budget
```

**Wirkprinzip:**

```text
effective_stage_ceiling = min(system_stage, user_stage_cap, capability_stage)
Rules/Permissions        = zusätzliche harte Rechte-Maske
continuous values        = regeln Stärke/Budget innerhalb dieses erlaubten Bereichs
```

Damit bleiben Stage-Gates echte Entwicklungsgrenzen, ohne innerhalb einer Stage unnötig harte Sprünge zu erzeugen.

## 17.3 Human-control / Developmental-control

Age ist absichtlich eine **menschlich inspirierte Entwicklungssteuerung**:

- früh starke äußere Struktur und geringe Eigeninitiative,
- Lernen zunächst vor allem über Erfahrung, episodische Spuren und sichere kleine Policies,
- zunehmende Selbstregulation erst nach stabiler Erfahrung,
- mehr Exploration in mittleren Stufen,
- größere langfristige Autonomie erst spät,
- Regression bei Instabilität.

Dies ist keine Behauptung, dass sechs V13-Stages biologischen Lebensaltern entsprechen. Aktuelle Entwicklungsforschung unterstützt aber das Prinzip, dass Executive Function, Selbstregulation, Netzwerk-Integration und Plastizität **erfahrungsabhängig, nichtlinear und über längere Entwicklungsfenster** reifen.

### Nutzerkontrolle

Der Nutzer kann:

- `user_stage_cap` festlegen,
- Stage-Aufstieg einfrieren,
- eine Stage manuell absenken,
- besonders weitreichende Expansion/Structural-Edit-Rechte separat sperren.

V13 darf eine höhere Stage **vorschlagen**, aber niemals selbst über `user_stage_cap` hinausgehen. Hard Rules bleiben weiterhin nur mit Proposal → Diff → expliziter User-Freigabe änderbar.

## 17.4 Stage Gates

Aufstieg basiert nicht auf Zeit/Tokens allein, sondern Kombinationen aus:

- Experience,
- Competence,
- Stability,
- Retention,
- Calibration,
- Memory Health,
- Safe Self-Control,
- erfolgreiche Regression-/Shadow-Tests.

Stage-Wechsel besitzen Hysterese: Ein einzelnes gutes Ergebnis öffnet keine neue Entwicklungsstufe. Regression kann einzelne Capabilities oder die globale Stage temporär zurückstufen.

## 17.5 Age steuert konkrete Rechte des gesamten Graphen

Age kontrolliert unter anderem:

- Pflicht- vs. optionale Routen,
- Anzahl und Länge eigener Loops,
- C_focal-Rekrutierungsfreiheit,
- Gist/Detail-Re-entry,
- zulässige autonome `reasoning_effort`-/Wake-Eskalation,
- Gist-Kompressions-/Integrationsspanne,
- Shadow testing und Exploration,
- Memory-Edit-Rechte,
- Context-Edit-Budget,
- Raw-vs-Translator-Wahl,
- Teacher reliance,
- Tool-/Body-Autonomie,
- Dream-/Replay-Budget,
- Plasticity-Scope,
- Self-edit rights,
- Self-messaging/Initiative,
- Body-/Structural-Modification-Rechte.

Age ist damit **keine zusätzliche Pipeline-Box**, sondern eine Entwicklungsmaske über den vorhandenen Graphen.

## 17.6 Age beeinflusst die Gist-Auflösung

Die alte adaptive Gist-Auflösung wird ausdrücklich wiederhergestellt.

Bootstrap:

```text
Detail A: ~1 native Token/Fine-Slot
Gist B:   ~8 native-token-equivalents/Gist-Gruppe, ~12 Gist-Slots
```

Mit Reife und gelernter Kompressionsfähigkeit darf B typischerweise größere semantische Spans stabil integrieren. Aber:

```text
Age ↑  ≠  Gruppengröße monoton ↑
```

Novelty, Konflikt, neue Domäne, Zahlen/Code/Literalität oder niedrige Boundary-Confidence dürfen die Gist-Auflösung temporär wieder verkleinern. Reifes Verhalten heißt **flexible Skalenwahl**, nicht maximal grobe Kompression.

## 17.7 Age 0 — Bootstrap / fast LLM-like

Ziel:

```text
funktionieren
Output liefern
Erfahrung sammeln
nicht kaputtlernen
```

Default ist **scaffolded adaptive compute**, nicht "immer beide großen Bodies":

```text
Input
→ source/context admission
→ C_fast / salience / task scaffold
   ├─ sichere exact/direct Aufgabe → Direct
   ├─ einfache lokal-grounded Sprache → C_native
   ├─ detailkritisch → B1/Detail (+ C_native/C_focal Integration)
   ├─ global/langkontext → B2/Gist (+ C_native/C_focal Integration)
   └─ offen/schwierig/unsicher → B1 + B2 → JEF_FOCAL_LOOP
→ Output
```

Age 0 nutzt in v10.6 standardmäßig **hohe Observer-Coverage**: A und B bekommen bei neuen externen Events möglichst je einen bounded Observer-Pass, aber JEF muss ihre Offers nicht für die sichtbare Antwort verwenden oder darauf warten. Bei Thermal/RAM/Deadline-Druck darf der Scheduler defer/skippen. Später darf die Observer-Frequenz gelernt werden. Damit wird „beide sehen die Welt“ vom teuren „beide müssen jedes Mal tief denken/sprechen“ getrennt.

Erlaubt:

- etwas Memory,
- minimale Context-Editierung,
- einfaches Feedback,
- hohe **sichere** Plastizität in episodischem Memory/kleinen Heads möglich,
- sehr geringe Base-Weight-/Structural-Plasticity,
- starke Regeln,
- Translator standardmäßig bei jungen Ports,
- sehr wenig Dream,
- keine spontanen langen Eigenloops,
- keine weitreichende Self-Initiative.

Sichere bekannte Direktaufgaben dürfen C_focal umgehen.

## 17.8 Age 1 — Exploration unter starker Struktur

Öffnet langsam:

- alternative interne Routen im Shadow,
- mehr Gist/Detail-Dynamik,
- erste autonome Memory-Edits,
- einfache Toolwahl,
- Translator gelegentlich überspringen,
- kurze Dream-Episoden,
- Feedback beeinflusst Routing/Replay,
- sichere kleine Policy-/Adapter-Updates,
- begrenzte Route-Exploration.

Externe Struktur bleibt stark.

## 17.9 Age 2 — Skill Building / Proceduralization

- aktive Inquisition/Deliberationsmodi,
- besserer Memory Recall,
- Tool-Lernen,
- längeres Replay,
- Translator Reliance wird gelernt,
- Body-only/Raw-Versuche,
- prozedurales Memory,
- action-conditioned World-JEPA,
- mehr sichere Self-Edits,
- gelernte Routinen dürfen validierte Defaultteile überspringen,
- Gist-Gruppierung wird stärker boundary-/task-adaptiv.

## 17.10 Age 3 — Stabilization / Self-Regulation

Mehr Freiheit nur bei stabiler Historie:

- längere Denkloops,
- längere Context-Horizonte,
- stärkere Self-Regulation,
- eigene Sleep-/Replay-Planung,
- mehr Offline-Konsolidierung,
- Wissenslücken erkennen,
- aktiv Teacher/Hilfe anfordern,
- Translator nur wenn nützlich,
- sichere Self-Edits ohne jedes Mal User-Dialog, soweit Permission dies erlaubt,
- flexiblere Auswahl zwischen Fine- und Coarse-Processing.

## 17.11 Age 4 — Maturity

- starke Automaticity bei Routine,
- tiefe Deliberation bei Neuheit,
- gelegentliche Self-Initiative,
- offene Ziele wieder aufnehmen,
- längere Dream-/Replay-Zyklen planen,
- eigene Lernziele innerhalb Rules wählen,
- fehlende Informationen aktiv suchen,
- Body-/Tool-Kompetenz bewerten,
- sichere Config-/Architekturänderungen **vorschlagen**,
- Teacher/Translator meist nur noch nach Bedarf,
- größere Consolidation Jobs planen.

Mehr Freiheit bedeutet weiterhin nicht "keine Grenzen".

## 17.12 Age 5 — Expansion

Nahezu alle **anpassbaren** Parameter/Strukturen dürfen prinzipiell innerhalb User-Cap/Rules verändert oder zur Änderung vorgeschlagen werden. Weiterhin bindend:

- Eligibility,
- Metaplasticity,
- Homeostasis,
- Regression Shield,
- Provenance,
- Rules,
- Rollback.

Neue Bodies, Modalitäten und Tools dürfen integriert werden; Body Swap und längere Offlinephasen werden möglich.

## 17.13 Lifelong

Kein finales Alter.

```text
stabil → neue Domäne → Capability lokal jung
→ Scaffold/Plasticity lokal öffnen
→ lernen → stabilisieren
```

Ein reifes Gesamtsystem kann deshalb gleichzeitig eine neue Vision-Capability auf Stage 0 und Language/Routing auf Stage 4 besitzen.

# 17A. Scaffold-to-Policy Learning

Age 0 erzwingt bestimmte sichere Default-Routen **nicht nur als Guardrail, sondern als Lehrsignal für Selbststeuerung**.

```text
scaffold route executes
      ↓
log route decisions + outcome
      ↓
C_fast / skill policy predicts the same decisions
      ↓
learned route runs in shadow
      ↓
safe alternative / perturbation candidates
      ↓
quality + cost + provenance + retention comparison
      ↓
validated learned route gains authority
      ↓
scaffold becomes fallback / recovery
```

Wichtig:

- Das System lernt nicht bloß den Output des Scaffolds, sondern **welche Entscheidung an welchem State sinnvoll war**.
- Eine learned route darf vom Scaffold abweichen, wenn Outcome/Retention/Cost wiederholt besser sind und Rules/Provenance erhalten bleiben.
- Ab ausreichend stabiler Capability-Stage darf kontrollierte Exploration Alternativen erzeugen; bevorzugt zunächst Shadow/Replay statt riskanter realer Aktionen.
- Regression kann die Autorität wieder zurück auf das Scaffold verschieben.
- Diese Logik gilt capability-spezifisch.

---

# 17B. Age-0 Lab Mode — realistische Lernkontrolle

Age 0 ist nicht nur eine Entwicklungsmetapher, sondern der **lange experimentelle Hauptbetrieb** der ersten Implementierung. In diesem Modus wird nicht vorausgesetzt, dass das System schon autonom entscheiden darf, was und wie viel es lernt.

## 17B.1 Drei Lernzustände

```text
RECORD_ONLY
= Experience, Eligibility, Teacher/Human-Referenzen sammeln; keine persistenten Gewichtsänderungen

SHADOW_UPDATE
= kleine isolierte Deltas/Adapter/Heads trainieren; nicht produktiv aktiv

APPROVED_COMMIT
= nur nach Regression/Retention + menschlicher Freigabe in produktiven Zustand übernehmen
```

Default für neue Capabilities in Age 0 ist `RECORD_ONLY`. JEF-Routing-/Calibration-Heads dürfen häufiger im Shadow lernen als A/B-Base-Weights, aber auch sie müssen versioniert und rollbackbar bleiben.

## 17B.2 Human Decision Packet

Menschliches Feedback wird **nicht als normaler Chattext versteckt**, sondern als eigener typisierter Datensatz zurückgeführt:

```text
HUMAN_DECISION {
  experience_id
  preferred_candidate?
  rejected_candidate?
  corrected_spans?
  reason_tags?
  factual_correction?
  style_preference?
  route_feedback?
  learning_permission = record | shadow | commit
}
```

Damit bleibt unterscheidbar:

- Wahrheit/Korrektur,
- Stil-/Präferenzfeedback,
- Routing-/Effizienzfeedback,
- reine Auswahl zwischen zwei Antworten.

## 17B.3 Age-0-Kommandorechte

Der Bedienkanal muss mindestens steuerbar machen:

```text
:learning record|shadow|commit
:teacher on|off|<slot>
:teacher compare
:approve <experience/update>
:reject <experience/update>
:rollback <update>
:capability <name> stage <n>
:stage cap <n>
```

Konkrete Syntax darf später geändert werden; die Kontrollrechte selbst sind Canon.

---

# 17C. Operator-Control-Hardening

## IH-H15 — Operator Control Plane [BLOCKER]

Die Age-0-Lernrechte sind im Canon vorhanden. Für echte Nutzung braucht der Bedienkanal zusätzlich einen **LLM-unabhängigen Parser**.

Grundregel:

```text
User TTY command -> operator parser -> privileged control action
Model output      -> niemals operator parser
```

Das Modell darf Zeichenfolgen wie `:rollback` ausgeben, ohne dadurch Administratorrechte zu erhalten.

Mindestgruppen:

```text
HELP/STATE
:help
:status
:resources
:brain
:models
:logs
:doctor

SESSION
:chats
:open
:search
:export chat
:cancel
:pause
:resume

LEARNING
:learning record|shadow|commit
:teacher on|off|<slot>
:teacher compare
:approve <id>
:reject <id>
:rollback <id>
:requests

AGE/RULES
:rules
:capability <name> stage <n>
:stage cap <n>
:age
:permissions

MODEL/RUNTIME
:download
:import model
:export model
:unload <role>
:gc
:backup
:restore
:shutdown
```

Destruktive Aktionen:

- zeigen Diff/Target,
- unterstützen dry-run wo sinnvoll,
- brauchen explizite Bestätigung,
- erzeugen Audit Record.

`:doctor` prüft mindestens:

```text
schema migrations
DB integrity
active generation manifest
model hashes
runner capability claims
free disk
RSS/headroom
stale locks
orphan shadow updates
checkpoint compatibility
source-ref integrity sample
```

---

# 18. Lab Scaffold Ports — eingefrorene Hilfen, lernender Core

## 18.1 Vier Dinge strikt trennen

Die frühere Formulierung `Encoder/Decoder` war zu mehrdeutig. Pro Modalität werden vier Rollen unterschieden:

```text
A) MINIMAL PHYSICAL TRANSDUCER
   raw world ↔ machine-manageable chunks/codes
   möglichst informationshaltend, semantisch arm
   frozen/deterministisch; darf dauerhaft bleiben

B) SEMANTIC INPUT TEACHER
   starker externer Encoder/VLM/ASR/API
   erklärt/annotiert dieselbe Eingabe für den kleinen Core
   frozen, austauschbar, später entfernbar

C) OUTPUT EFFECTOR / RENDERER
   core intent/codes → reale Modalität
   z.B. vocoder, image renderer, UI/tool schema
   kann als körperliche Peripherie dauerhaft bleiben

D) OUTPUT REFERENCE TEACHER
   stärkeres LLM/VLM/Speech/Image-Modell oder API
   erzeugt Vergleichs-/Distillationskandidaten
   frozen, nicht automatisch autoritativ, später entfernbar
```

**Der V13-Core lernt. Die Lab-Teacher lernen in Age 0 nicht.** Learnable sind primär die core-seitigen Projectors/Adapters/Heads und später ausgewählte B1/B2/JEF-Gewichte.

## 18.2 Zwei Eingangswege gleichzeitig — das eigentliche „zwei Augen“-Prinzip

Für eine neue Modalität erhält der Core anfangs dieselbe Experience auf zwei synchronisierten Wegen:

```text
                    SAME SOURCE / SAME CLOCK
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      RAW/MINIMAL PATH             TEACHER PATH
  physical transducer only       frozen semantic model/API
  patch/frame/codec chunks       caption/transcript/regions/features
             │                           │
     learnable student port              │ stop-gradient
             └─────────────┬─────────────┘
                           ▼
                  JEF / A / B / Workspace
```

Beide Pfade tragen dieselben `source_span`, `clock/event_id` und Region-/Zeitbezüge. Dadurch kann der Core lernen:

> „Diese rohen/minimal verarbeiteten Signale entsprechen ungefähr jener teacher-semantischen Interpretation.“

Der Teacher darf **keine Ground-Truth-Magie** bekommen: seine Ausgabe bleibt `TEACHER_INTERPRETATION`, nicht `REAL`. Reales Task-/User-/Tool-Outcome hat höhere epistemische Priorität.

## 18.3 Was am Raw-Pfad minimal bleiben darf

Ein sehr kleines text-only LLM kann nicht sinnvoll Millionen rohe Pixelwerte oder Audio-Samples direkt als normale Texttokens konsumieren. Deshalb ist ein minimaler körperlicher Transducer realistisch notwendig. Beispiele:

```text
vision: image → resize/normalize → tiles/patches → compact numeric/codec representation
audio: waveform → frames/codec bins/features → compact timed representation
video: frames + timestamps + motion/event chunking
body: sensor values → typed time-series packets
```

Dieser Transducer soll **nicht die Bedeutung erklären**. Er macht die Daten nur rechnerisch handhabbar. Er kann deterministisch sein oder ein eingefrorener informationsorientierter Codec.

Das learnable `student_projector` gehört dagegen zu V13 und lernt aus Teacher/Outcome, welche Rohmerkmale für B1/B2/JEF nützlich sind.

## 18.4 Teacher-Removal ist ein Experiment, kein automatischer Meilenstein

Für jede Capability gibt es eine A/B-Testleiter:

```text
T0 teacher + raw/student gemeinsam
T1 student shadow, teacher primary
T2 student primary, teacher shadow/verifier
T3 student-only trial
T4 teacher archived/fallback
```

Aufstieg verlangt:

- Parity auf gehaltenen Tests,
- Retention nach Restart,
- OOD/Novelty-Test,
- Regression-Test alter Skills,
- ausreichende Calibration,
- menschliche Freigabe in Age 0.

Bei Regression darf sofort auf T1/T2 zurückgefallen werden.

## 18.5 Outputseite: Self zuerst, Teacher separat danach

Für Text oder andere generative Outputs ist der saubere Age-0-Ablauf:

```text
INPUT / STATE
   ↓
V13 erzeugt SELF_CANDIDATE   ← Teacher noch nicht sichtbar
   ↓
optional OUTPUT_REFERENCE_TEACHER/API erzeugt TEACHER_CANDIDATE
   ↓
Comparator / Human sieht beide
   ↓
HUMAN_DECISION / grounded outcome
   ↓
LearningEvent
```

Der Teacher-Text wird **nicht einfach in die normale Chat-History kopiert**, weil V13 sonst nicht mehr unterscheiden kann, ob es selbst etwas wusste oder nur gerade gelesen hat. Er liegt in einer getrennten `REFERENCE_LANE`.

## 18.6 Reference Lane und ExperienceRecord

```text
EXPERIENCE_RECORD {
  input_source_ids
  raw_port_view
  semantic_teacher_view?

  self_candidate
  self_route_trace
  self_confidence

  teacher_candidates[] {
    teacher_id
    modality
    candidate
    source/provenance
    prompt/config hash
  }

  human_decision?
  tool/world_outcome?
  learning_permission
}
```

Lernziele daraus können getrennt sein:

```text
output imitation/distillation   ← teacher candidate, falls als besser bestätigt
preference learning             ← chosen vs rejected
semantic grounding              ← raw path ↔ teacher view ↔ outcome
routing learning                ← welche Hilfe hätte sich gelohnt?
calibration                     ← wann war SELF unsicher/falsch?
knowledge update                ← nur bei ausreichend starker Evidenz, nicht bloß Teacher-Text
```

## 18.7 Teacher ist Referenz, nicht Wahrheit

Distillation kann Teacher-Fehler übernehmen oder sogar überoptimieren. Deshalb:

- Teacher-Ausgabe bleibt provenance-markiert.
- Ein Teacher darf Stil/Reasoning/Format vormachen, ohne Faktenautorität zu erhalten.
- Mehrere Teacher dürfen widersprechen; Human/Tool/World-Outcomes können sie überstimmen.
- Online/diverse Experiences sind besser als ein einzelnes statisches Teacher-Dataset.
- V13 lernt auch **wann der Teacher schlechter ist** und darf seine Hilfe später abwerten.

## 18.8 Input- und Output-Steckplätze sind symmetrisch erweiterbar

```text
INGRESS_SLOT {
  physical_transducer      // frozen/deterministic
  semantic_teacher?        // frozen local model or API
  student_projector        // V13-owned, learnable
  source_alignment
  capability_age
}

EGRESS_SLOT {
  core_output_schema
  physical_renderer?       // frozen/deterministic/external
  reference_teacher?       // frozen model or API
  student_effector_adapter?// V13-owned, learnable where useful
  feedback_collector
  capability_age
}
```

Neue Encoder, Decoder, APIs oder lokale Modelle werden dadurch **angesteckt**, nicht in die Core-Architektur hart einprogrammiert.

## 18.9 Vision Age-0 konkret

```text
IMAGE
 ├─ RAW EYE: patchify/tiles/codec → student visual projector → B1/B2/JEF
 └─ TEACHER EYE: frozen VLM/vision encoder → caption/OCR/regions/features

ALIGN by source region/time
↓
Core predicts/interprets raw-eye features
↓
Human/task/world verifies
```

Optionaler Reconstruction-Decoder darf als **Testinstrument** existieren, um Informationsverlust im student raw path zu messen. Er ist nicht der semantische Teacher und muss nicht Teil des finalen Systems sein.

## 18.10 Audio/Speech Age-0 konkret

```text
AUDIO INPUT
 ├─ RAW EAR: frames/codec → student audio projector → B1/B2/JEF
 └─ TEACHER EAR: frozen ASR/audio model → transcript/events/speaker/timing

SPEECH OUTPUT
 SELF: JEF/core intent → current speech effector → waveform
 REF : optional stronger TTS/voice/API → reference waveform/text/prosody
 HUMAN/metrics compare
```

Ein Vocoder/Codec kann dauerhaft Körperperipherie bleiben. Was verschwinden soll, ist primär der **starke semantische Teacher**, nicht jede physische Signalwandlung.

## 18.11 Text Age-0 — die erste echte Distillationsstrecke

Text braucht keinen neuen Sensor-Encoder; native Tokenizer/LM-Heads existieren bereits. Deshalb ist Text der beste Ort, das komplette Lernprotokoll zuerst zu beweisen:

```text
User input
→ JEF/A/B Core
→ SELF_CANDIDATE
→ optional external/local teacher LLM/API
→ TEACHER_CANDIDATE in REFERENCE_LANE
→ Human chooses/corrects
→ ExperienceRecord
→ record/shadow/approved learning
```

Wenn dieser Loop nicht stabil funktioniert, wird **keine neue Modalität** hinzugefügt.

## 18.12 Was „Encoder/Decoder entfernen“ realistisch bedeutet

Entfernbar:
- starker VLM-/ASR-/LLM-Teacher,
- Teacher-caption/OCR/semantic labels,
- reference generator/API,
- training-only reconstruction decoder.

Nicht zwingend entfernbar:
- Pixel/Audio patchification/codec,
- Sensor-Treiber,
- Vocoder/physical renderer,
- notwendige dimensionality/projector layer, wenn der Body die Raw-Modalität architektonisch sonst nicht konsumieren kann.

Das Ziel ist daher **semantische Internalisation**, nicht magisches Verschwinden jeder Peripherie.

---
# 19. BodyPort und Body Swap

## 19.1 BodyPort Contract

Ein Body muss **nicht** jede fortgeschrittene Fähigkeit nativ unterstützen. Jeder BodyPort deklariert ein Capability-Profil, z. B.:

```text
CAN_NATIVE_DECODE
CAN_LAYER_TAP
CAN_LATENT_INJECT
CAN_PREFIX_CONDITION
CAN_TRAIN_ADAPTER
CAN_TRAIN_SELECTED_WEIGHTS
CAN_CONTEXT_ENCODE_DECODE_SPLIT
CAN_PROJECT_GLOBAL_CONTEXT_STATE
CAN_BOUNDED_CACHE_REPLAY
CAN_SHARED_ATTN_INDEX
CAN_HIERARCHICAL_INDEX_CANDIDATES
CAN_POOLED_INDEX_STATE
CAN_BLOCK_SPARSE_RETRIEVAL
CAN_NATIVE_SPEC_DECODE
CAN_NATIVE_MTP_OR_DRAFT_HEAD
CAN_VISION_ENCODE
CAN_AUDIO_ENCODE
CAN_SPEECH_DECODE
CAN_IMAGE_DECODE
CAN_STREAMING_INPUT
CAN_STREAMING_OUTPUT
CAN_FULL_DUPLEX
CAN_RECONSTRUCTION_HEAD
SOURCE_CHANNEL_ONLY
EXACT_CHANNEL_SUPPORTED
```

Logische API, soweit capability vorhanden:

```text
encode_native(input)
forward_native(state, budget)
read_latent(taps?)
inject_latent(message?)
condition_native(control?)
request_exact_source(...)
decode_native(...)
local_trainable_handles()
checkpoint_state()
resource_profile()
capability_profile()
```

Ein Body ohne `CAN_LATENT_INJECT` ist nicht „kaputt“: er startet über Source-/Prefix-/Adapter-Conditioning und kann später durch einen kompatibleren Body ersetzt werden.

## 19.1A ModalityPort Contract

Jede Raw-Modalität kann separat deklarieren:

```text
segment(raw, clock)
encode_segment(segment)
project_to_core(encoded, target={JEF,A,B})
reconstruct?(latent)
decode_output?(intent_or_latent)
stream_state()
teacher_targets?()
reference_candidates?()
student_trainable_handles()
physical_component_trainable = false   // Age-0 default
teacher_trainable = false              // Age-0 hard rule
resource_profile()
capability_age()
```

Input- und Outputfähigkeit werden getrennt deklariert. Ein Vision-Encoder impliziert keinen Bildgenerator; ein Audio-Encoder impliziert keinen Speech-Decoder.

## 19.2 Projection Compatibility und private Repräsentationen

Verschiedene Tokenizer/hidden sizes werden über gelernte Projectors in den V13-Workspace gekoppelt. Projection Compatibility ist eine trainierte Fähigkeit, keine Annahme.

**Alignment darf A und B nicht homogenisieren.** Beide behalten private Body-Repräsentationen; aus ihnen werden kompakte Nachrichten in einen kompatiblen Message-Subspace projiziert:

```text
private A state → A message projector ─┐
                                      ├→ shared message space
private B state → B message projector ─┘
```

Trainingsziele müssen Kommunikation ermöglichen, aber zugleich private Diversity/Spezialisierung erhalten. Parity-/Collapse-Checks messen u. a. Message-Utility, private-state Diversity und ob Gist/Detail-Bias nach Alignment erhalten bleibt.

## 19.2A MessagePacket trägt Auflösung und Zeitbezug

Hidden-Space-Alignment allein reicht nicht, weil A und B verschiedene Tokenizer, Layer und effektive Integrationsfenster besitzen. Eine Cross-Body-Message trägt daher neben dem Payload Metadaten wie:

```text
MessagePacket {
  payload / latent_slots
  source_span_refs
  event_id / semantic_time
  integration_scale
  boundary_map_or_confidence
  sender_layer_or_tap
  intended_receiver_tap
  role / message_type
  confidence
  exact_fallback_ref
}
```

Der Receiver darf eine Message über gated adapter/cross-attention/residual gate fusionieren. Blindes Addieren eines fremden Vektors in einen beliebigen Residual Stream ist kein kanonischer Default.

`integration_scale` erlaubt explizit Cross-scale-Kommunikation:

```text
A fine → B gist : mehrere Detailspans werden zu relationalem Gist gebündelt
B gist → A fine : globaler Constraint/Plan biasiert lokale Detailverarbeitung
```

## 19.3 Callosum-Bootstrap vor freier Latent-Injection

Zwei fremde pretrained Bodies besitzen anfangs **keine gemeinsame Latent-Sprache**. Deshalb:

```text
shared grounded inputs
→ native A/B states sammeln
→ Message-Projector-Alignment ohne private-state matching
→ Cross-JEPA / contrastive-parity + anti-collapse/diversity objectives
→ bounded typed Exact/Source Channel als Grounding
→ shadow latent messages
→ measure downstream state change + task parity
→ erst dann aktive latent injection freigeben
```

Random oder unkalibrierte Latents dürfen nie als „echter Callosum“ gelten.

### 19.3A Receiver Calibration und Channel Authority

Vor aktiver Injection wird pro Body-Paar/Injection-Punkt ein Receiver-Profil gemessen:

```text
native activation norm/statistics
message norm/statistics
allowed residual scale
gating range
OOD threshold
no-message baseline
source/symbolic baseline
```

Aktive Latent-Kommunikation gewinnt Authority nur, wenn sie Aufgabenqualität oder Effizienz gegenüber den Fallback-Kanälen verbessert, ohne private Role-Diversity oder Calibration zu verschlechtern. Authority kann bei Drift automatisch zurückgenommen werden.

# 19H. BodyPort-/Bridge-Hardening

## IH-H8 — BodyPort muss echte Runtime-Lifecycle-Methoden besitzen [MUST]

Zusätzlich zum semantischen BodyPort:

```text
load()
healthcheck()
prefill(...)
observe(...)
step(...)
read_taps(...)
condition(...)
cancel(request_id)
unload()
resource_snapshot()
capability_profile()
checkpoint_trainable_state()
```

Verbindlich:

- `cancel()` darf kein Zombie-Forward hinterlassen,
- `unload()` muss messen, was tatsächlich freigegeben wurde,
- Runner ohne `CAN_LATENT_INJECT` nutzt Fallback und fälscht keine Injection,
- kein Python-Hotpath für große Tensorloops, wenn native runner verfügbar/erforderlich ist.

---

## IH-H21 — Bridge Compatibility Key [MUST]

Latent-/Broadcast-Bridges sind nicht abstrakt „für B1“ gültig, sondern für konkrete Revisionen:

```text
BridgeKey = (
  sender_model_revision,
  receiver_model_revision,
  sender_tap_id,
  receiver_tap_id,
  message_schema_major,
  bridge_revision
)
```

Bei Body-Swap oder Tap-Änderung:

```text
bridge authority -> 0 / SHADOW
fallback -> SOURCE/EXACT/CONTROL
recalibrate
```

Keine alte Bridge still auf neuen Body anwenden.

---

## IH-H22 — B1/B2 Shared Immutable Base ist erlaubt, mutable State nicht [SHOULD]

Wenn B1 und B2 denselben Boot-Checkpoint verwenden, darf ein read-only Base-File/Page-Cache geteilt werden, **falls der Runner das real ermöglicht**.

Getrennt bleiben:

```text
role-specific adapters
KV/cache
router runtime state
fine/gist slot state
eligibility traces
homeostasis/metaplasticity state
observer statistics
```

Die Spezialisierung muss gemessen werden; zwei identische Prompts auf derselben Instanz sind kein Split-Brain-Proof.

---

## 19.4 Swap-Protokoll

```text
snapshot old body
→ old keeps serving
→ new body shadow
→ projection compatibility
→ transfer adapter priors
→ replay skills / experience anchors
→ latent anchor parity
→ output/provenance/calibration tests
→ gradual traffic shift
→ rollback window
→ retire/archive old body
```

Identity Continuity hängt nicht an identischen Gewichten.

---

# 20. Rules, Self-Edit, Goals, Initiative

## 20.1 Rules

Rules sind versioniert und getrennt von normalem Memory/Weights.

Hard Rule Change:

```text
proposal → diff → explicit user approval → versioned commit
```

## 20.2 Self-Edit

Darf je nach Age/Permission z. B. betreffen:

- Memory,
- World Notebook,
- Context Policy,
- Replay Priority,
- Routing Candidate,
- Skill Metadata,
- Translator Gate,
- safe config.

Nicht jede Änderung wird sofort committed.

## 20.3 Goals

Früh primär User Goal. Später dürfen offene Ziele, Lernziele und geplante Offline-Aufgaben entstehen, solange Regeln/User Alignment übergeordnet bleiben.

## 20.4 Self-Messaging

Später erlaubt bei:

- wichtigem Fund,
- offenem Ziel,
- Fehler,
- relevanter Erinnerung,

aber mit Relevance Gate, Rate Limit und Anti-Spam.

---

# 21. Stability Envelope, Regression Shield und Checkpoints

Jeder persistente Update wird mindestens gegen:

- neue Fähigkeit,
- alte Retention,
- Calibration,
- Provenance-Verhalten,
- Routing Drift,
- Memory Health,
- Safety/Rules,
- Ressourcenstabilität,
- shared Attention/Embedding/Norm-Retention,
- Router-Input-/Route-Collision-Drift,
- Channel-Calibration/Message-Utility

geprüft.

Bei Regression:

```text
plasticity ↓
autonomy ↓
teacher reliance ↑
replay ↑
capability age ggf. zurück
rollback / shadow restore
```

### 21.1 Delta-first Consolidation

Modularer Rollback ist bei gemeinsam genutzten Base-Weights nur begrenzt möglich. Deshalb laufen neue persistente Änderungen möglichst zuerst als **Delta/Adapter/branch/shadow update**:

```text
experience update
→ isolated delta / trainable slice
→ regression + retention tests
→ validated delta checkpoint
→ mehrere bestätigte Deltas
→ optional merge/consolidation into base weights
```

Nach Merge in geteilte Base-Weights ist Rollback checkpoint-/delta-basiert und nicht magisch pro Skill. Capability-spezifische Reversion bleibt ein Ziel, aber keine garantierte Eigenschaft beliebiger gemeinsamer Gewichte.

Checkpoints sind modular:

- A state/adapters,
- B state/adapters,
- C state/heads,
- Callosum/Workspace,
- memory indices,
- world/self model,
- skills,
- age,
- homeostasis/metaplasticity,
- translator state.

Ein Fehler soll nicht zwingend Full-Brain Rollback erfordern.

---

# 21H. Transactional Persistence / Learning Commit / Rollback

## IH-H16 — Persistenz: Metadata authoritative, Index rebuildable [MUST]

Empfohlene Age-0-Referenzimplementation:

```text
SQLite WAL      -> Events, IDs, manifests, rules, age, update states, metadata
content blobs   -> raw/exact sources, checkpoints, model files
vector/index    -> rebuildable acceleration, NICHT Wahrheitsquelle
```

Warum:

- phone-friendly,
- transactional,
- crash-recoverable,
- foreign keys/migrations,
- Index kann bei Korruption neu aufgebaut werden.

Directory baseline:

```text
~/v13/
  bin/
  config/
  models/
  data/db/
  data/blobs/
  memory/index/
  checkpoints/
  shadow/
  logs/
  tmp/
  exports/
  backups/
```

Rechte local-first: Brain-Verzeichnis standardmäßig nur für den User les-/schreibbar.

---

## IH-H17 — BrainGenerationManifest: atomarer Gesamtzustand [BLOCKER]

Modulare Checkpoints sind gut, reichen aber bei voneinander abhängigen Bridges/Models/Indices nicht allein.

Jede produktive Generation besitzt:

```text
BrainGenerationManifest {
  brain_generation_id
  parent_generation_id
  rule_version
  age_state_version
  B1_model_revision
  B1_adapter_revision
  B2_model_revision
  B2_adapter_revision
  JEF_component_revisions
  callosum_bridge_revision
  jef_broadcast_bridge_revision
  memory_schema_version
  memory_snapshot_id
  world_self_revision
  skill_revision
  config_revision
  created_by_update_ids[]
  hashes
}
```

Der aktive Zustand ist **ein kleiner Pointer/Manifest-Wechsel**, nicht ein Haufen einzeln überschriebener Dateien.

---

## IH-H18 — Update Transaction State Machine [BLOCKER]

`RECORD_ONLY | SHADOW_UPDATE | APPROVED_COMMIT` werden als echte Zustände umgesetzt:

```text
RECORDED
→ SHADOW_QUEUED
→ SHADOW_TRAINING
→ SHADOW_TRAINED
→ EVALUATING
→ EVALUATED_PASS | EVALUATED_FAIL
→ PENDING_APPROVAL
→ COMMITTING
→ COMMITTED

Nebenpfade:
REJECTED
ABORTED
QUARANTINED
ROLLBACK_PENDING
ROLLED_BACK
```

`UpdateManifest`:

```text
update_id
base_brain_generation_id
experience_ids[]
capability_id
trainable_handles[]
objective_ids[]
optimizer_config
seed
candidate_artifact_hashes
metrics_before
metrics_after
test_suite_version
retention_result
provenance_result
resource_result
approval_actor
approval_time
commit_generation_id
rollback_generation_id
```

**APPROVED_COMMIT darf nie in-place aktive Gewichte überschreiben.**

Commit-Algorithmus:

```text
write candidate artifacts to temp generation
→ hash/validate
→ fsync files/metadata as supported
→ write complete manifest
→ atomically switch active-generation pointer
→ only then mark COMMITTED
```

Crash davor => alte Generation aktiv.  
Crash danach => neue vollständige Generation aktiv.

---

## IH-H19 — Rollback ist generation-basiert [MUST]

`:rollback <update>` bedeutet nicht „irgendwie Gewichte rückwärts rechnen“.

Es bedeutet:

1. finde parent/previous compatible `brain_generation_id`,
2. validiere Artefakte,
3. stoppe/pausiere neue mutierende Jobs,
4. atomar aktiven Generation-Pointer wechseln,
5. Runner/Bridges neu laden,
6. Healthcheck,
7. Rollback-Audit schreiben.

Nach Base-Merge bleibt capability-spezifisches magisches Unlearning ausdrücklich **nicht garantiert**.

---

## IH-H20 — Delete / Unlearning Lineage [MUST]

User-autorisierte Löschung muss Source-preserving Design trotzdem ermöglichen.

Jeder abgeleitete Record/Update trägt `lineage_refs`.

Delete-Protokoll:

```text
source tombstone
→ exact blob delete/archive according to user action
→ derived episodic/semantic records invalidate
→ vector index rebuild/invalidate
→ affected update_ids mark lineage_impacted
→ if reversible delta: rollback/retrain candidate
→ if merged/shared weights: limitation sichtbar loggen + retraining/unlearning job optional
```

Keine Behauptung, beliebiges Wissen sei nach Shared-Weight-Merge perfekt einzeln löschbar.

---

# 22. Runtime / Deployment

## 22.1 Architektur ist nicht Termux

Android/Termux ist erster lokaler Deployment-Körper, nicht der konzeptionelle Mittelpunkt.

## 22.2 Mobile Hot Path

Python darf orchestrieren, aber große Hot Paths sollen möglichst native Kernels/Runner verwenden.

### 22.2.1 Event / Wake Scheduler

V13 braucht einen einfachen Runtime-Scheduler, damit es später nicht nur auf User-Turns reagieren kann. Der Scheduler ist **keine Intelligenz und kein vierter Body**; er stellt nur Events in eine priorisierbare Queue:

```text
user input
tool/environment event
timer / deferred task
resource-state change
idle opportunity
open-goal wake
replay due
      ↓
 event queue / wake scheduler
      ↓
 C_fast / policies / Age rights entscheiden Priorität und Route
```

Der Scheduler darf Background-Learning oder Self-Messaging planen, aber Rules, Permissions, quiet/idle policy und Ressourcenlimits bleiben bindend.

### 22.2.2 Response Governor

Die Output-Garantie wird durch Runtime-Infrastruktur abgesichert, nicht nur durch ein gelerntes Halt-Head. Pro User-Turn existiert ein Governor mit:

- absolute deadline,
- token/compute/body-wake budget,
- `best_safe_candidate` Snapshot,
- fallback renderer,
- `HALT_AND_RENDER`-Recht.

Kein Body, Teacher, Replay-, Alignment- oder Learning-Job darf den Governor blockieren. Auch ein langsamer Output-Decoder darf bei Deadline durch einen sicheren kürzeren Fallback ersetzt werden.

### 22.2.3 Thin-Control-Fabric Budget

Viele kleine Heads dürfen zusammen nicht heimlich groß werden. Deshalb besitzt die gesamte Control Fabric ein gemeinsames messbares Budget für:

- Parameter/Resident RAM,
- State bytes,
- durchschnittliche und P95 Event-Latenz,
- Wake-/Forward-Frequenz,
- Energie/thermischen Overhead.

Bevorzugt wird ein kleiner gemeinsamer Control-Trunk/State-Updater mit mehreren winzigen Heads statt vieler unabhängiger Mittelmodelle. Konkrete Limits werden erst nach Zielhardware-Messung festgelegt.

## 22.2.4 Redmi Note 10 Pro — verbindlicher Age-0-Labor-Floor

Das erste echte Laborziel ist der **Redmi Note 10 Pro**. Die Architektur darf stärker skalieren, aber der Age-0-Core-Proof muss auf diesem Gerät bzw. seiner schwächeren RAM-Konfiguration testbar bleiben.

Prinzipien:

- 6-GB-RAM-Floor als konservative Laborplanung,
- Android/OS/Dateicache/native libs brauchen eigenen Headroom,
- CPU/native runner ist Baseline; NPU/GPU-Beschleunigung ist Bonus bis real bewiesen,
- Modelle dürfen mmap/offloaded/quantized sein,
- funktionale Parallelität von A/B bedeutet **nicht**, dass beide physisch gleichzeitig rechnen müssen,
- Observer-Pässe können sequenziell, asynchron oder sampled laufen, solange Semantik/Experience-Provenance erhalten bleibt,
- Hot KV/Context wird budgetiert; Exact Store bleibt günstiger Cold/Warm Backing Store.

### Redmi JEF-Organ-Budget — zunächst getrennt messen

Für den Redmi-6GB-Floor wird C/JEF **nicht** als ein 0.5–1B-Block geplant. Boot-Ablation:

```text
C2 structured control: Needle 3 rung / vergleichbar    ~9–35 MB binary class
C3 basic language:    ~50–150M active target class     on-demand/hot depending test
C1/C4/C5 heads/state: möglichst klein, shared trunk wo sinnvoll
A2 teachers:          external/on-demand, nicht permanent resident
C7 heavy effectors:   on-demand / external until proven affordable
```

Needle 3 ist laut aktueller Veröffentlichung 9–35 MB CQ2 bzw. 29–121M Parameter und zielt auf Tool Calling/Extraction/Embedding, nicht General Chat. Das macht C2 plausibel, aber gerade **deshalb** bleibt C3 zunächst eine separate Laborvariable.

Wenn C2 später kurze freie Sprache gleich gut übernimmt, darf C3 in Shadow deaktiviert werden. Wenn C3 einfache Control-Aufgaben mit übernimmt, darf C2 kleiner werden. **Reduktion folgt aus Ablation, nicht aus Vorannahme.**

### Observer Scheduling ist ein Deployment-Regler, keine Architekturänderung

Das kanonische Cognitive Design darf weiterhin beiden Bodies pro Event einen Observer-Pass anbieten. Auf Redmi kann der Scheduler wählen:

```text
ALWAYS_BOTH_ASYNC
A_THEN_B_SEQUENTIAL
B_THEN_A_SEQUENTIAL
JEF_FIRST_THEN_BOTH
SAMPLED_OBSERVER
ON_DEMAND_REENTRY
```

**JEF entscheidet weiterhin, ob ein Offer bewusst/fokal gebraucht wird.** Dass ein Observer physisch später läuft, ändert nicht seine logische Rolle.

### Mobile Learning Priority — Zusatz, kein Ersatz

Auf diesem Gerät werden Lernziele zunächst nach Kosten sortiert:

1. Statistik/Calibration,
2. kleine Heads/Policies,
3. Memory-/Retrieval-Keys,
4. JEF↔A/B Bridges/Projectors,
5. kleine Adapter/low-rank Deltas,
6. kleine JEPA Predictors,
7. breitere Adapter,
8. ausgewählte Body-Weights erst nach Messung.

Die vollständigen v10.8-Lernmechanismen bleiben erhalten; diese Liste beschreibt nur die **praktische Startreihenfolge auf dem Redmi**.

## 22.3 Training Master vs Quantized Inference Copy

Nicht versuchen, mmap-GGUF direkt als vollständigen SGD-Master zu behandeln.

Mögliche Struktur:

- quantized inference representation,
- kleine trainierbare aktive Master-Slices/Adapter,
- spätere stärkere Hardware für tiefe Konsolidierung,
- zurückquantisierte/validierte Inferenzkopien.

## 22.4 Phone-first Learning

Erster realistischer Lernumfang:

- C_fast heads,
- Workspace projectors,
- Callosum,
- Cautiousness/Inquisition,
- selected C/Judge heads,
- skill/context/memory policies,
- fast adapters,
- kleine JEPA predictors.

Tiefe Body-Konsolidierung nur nach Messung.

## 22.5 Performance-Prinzip

Nicht „immer möglichst wenig Compute“, sondern **lerne den Qualitäts-/Kostenwert unterschiedlicher Routen**.

Hard Task darf A+B stark nutzen.

Optimierungsschwerpunkte später:

- unnötige Body-Pässe vermeiden,
- Expert locality,
- mmap/file-backed residency,
- KV/context policy,
- prefetch,
- quantized kernels,
- thermal scheduling.

Keine Performancezahl wird als Tatsache ausgegeben, bevor sie auf Zielhardware gemessen wurde.

## 22.6 Speculative Decoding bleibt Serving, nicht Denken

Aktuelle Modelle nutzen verschiedene Draft/Verify-Pfade: DeepSeek-V4.1-Flash DSpark mit confidence-scheduled verification, GLM-5.3-Flash native MTP-Unterstützung und MiniMax-M3 EAGLE3-Serving. V13 darf solche Mechanismen verwenden, wenn ein Body/Runner sie nativ unterstützt.

Regeln:

- Draft Tokens sind **keine Gedanken und keine Evidenz**.
- Speculative Decoding verändert idealerweise nur Latenz/Throughput, nicht den semantischen Entscheidungsgraphen.
- C wird **nicht** automatisch zum Draft-Modell für A/B; unterschiedliche Tokenizer/Vokabulare verhindern das oft. Cross-Body Drafting ist nur erlaubt, wenn ein exaktes kompatibles Verification-Protokoll existiert.
- Confidence-scheduled verification ist interessant als Serving-Policy: Draft-/Verify-Länge wird an Acceptance und aktuelle Ressourcenlast angepasst.
- `reasoning_effort` und speculative decoding bleiben getrennte Regler: eines steuert *wie viel* kognitive Arbeit, das andere *wie effizient* ein gewählter Decoder Tokens ausgibt.

---

# 22H. Runtime-/Redmi-/Concurrency-Hardening

## IH-H6 — Runner Proof Gate vor Modellfestlegung [BLOCKER / REDMI]

### Warum

Eine Modellkarte kann eine projizierte INT4 Weight Memory nennen, obwohl der konkrete Runner Gewichte anders materialisiert. Das Redmi-Budget darf deshalb nie aus Dateigröße allein abgeleitet werden.

### RUNNER_PROOF pro Body

Vor `model_role = production_candidate` müssen auf **der echten Zielruntime** gemessen werden:

```text
model revision / checksum
runner revision
ABI / CPU features
quant format kept packed at runtime? yes/no
peak RSS / PSS
steady RSS / PSS
mapped file bytes
page faults
KV bytes vs context length
prefill latency
TTFT
decode tok/s
observer-pass latency
thermal drift over repeated turns
cancel latency
unload/reload behavior
layer tap availability
conditioning/injection capabilities
```

### MobileMoE-S-QAT konkret

Die im Canon verwendeten ~0.68 GB sind nur **projected INT4 weight memory**. Die aktuelle veröffentlichte Transformers-Referenz materialisiert beim ersten Forward dense BF16 weights; das INT4-Format ist außerdem nicht nativ durch vLLM nutzbar. Daher gilt:

```text
MobileMoE-S-QAT auf Redmi = RESEARCH CANDIDATE
nicht = bewiesener 0.68-GB resident Body
```

Der Canon „B1/B2 sind zwei komplementäre sparse cognitive bodies“ bleibt erhalten. Erlaubte Umsetzungen:

1. Android/ARM64-Runner, der dieses packed INT4/MoE-Format real effizient ausführt;
2. anderer kompatibler MoE mit bewiesenem mobilen Runner;
3. temporärer kleinerer Harness-Body, bis 1/2 erfüllt ist.

Nicht erlaubt:

```text
0.68 GB in Budget eintragen
→ Default Transformers laden
→ BF16 materialisieren
→ OOM
→ Architektur als "zu groß" streichen
```

---

## IH-H7 — ModelManifest / Download / License / Reproducibility [MUST]

Jedes Modell/Organ erhält:

```text
ModelManifest {
  role
  model_id
  exact_revision
  file_hashes
  tokenizer_hash
  config_hash
  license_id
  license_accepted_by_user
  access/gating_requirements
  quant_format
  runner_id
  runner_revision
  body_capability_profile
  local_path
  download_complete
  benchmark_record_id?
}
```

Download-Regeln:

- resumable,
- `.partial` bis Hash vollständig stimmt,
- kein aktiver Model-Swap auf halbfertige Datei,
- gated/license-gebundene Modelle brauchen explizite User-Aktion,
- kein API-/HF-Token in Logs/ExperienceRecords,
- offline restart muss nach erfolgreichem Download funktionieren.

---

## IH-H9 — Prozess-/Concurrency-Modell [BLOCKER]

Minimaler Age-0-Prozessgraph:

```text
operator/ui process
      ↓ typed commands/events
runtime coordinator  [single authority for active generation]
 ├─ JEF runner
 ├─ B1 runner
 ├─ B2 runner
 ├─ storage writer
 └─ shadow learner process   [isoliert von production weights]
```

Regeln:

- nur ein aktiver Runtime-Coordinator pro Brain-Verzeichnis,
- PID/file lock verhindert Doppelstart auf denselben Store,
- aktive Rules/Age/Generation haben genau einen autoritativen Writer,
- Shadow Learner schreibt niemals direkt in aktive Modellpfade,
- concurrent updates desselben trainable handle sind verboten,
- Reader sehen einen konsistenten `brain_generation_id` Snapshot.

---

## IH-H10 — Bounded Queues + Backpressure [BLOCKER]

Jede Queue hat:

```text
max_count
max_bytes
priority_classes
TTL
overflow_policy
coalesce_policy
cancel_owner
metrics
```

Priorität grob:

```text
P0 permissions / user cancel / governor / safety
P1 active user turn / tool outcome
P2 salient observer offer / action outcome
P3 memory/retrieval
P4 shadow learning
P5 replay/dream/maintenance
```

Bei Druck:

- Replay/Dream zuerst pausieren,
- low-salience Offers coalescen/drop,
- niemals User-Cancel oder Permission-Event droppen,
- kein Replay darf Chat dauerhaft verhungern lassen.

---

## IH-H11 — Event-/Offer-Staleness als Compare-and-Swap [BLOCKER]

v10.15 führt `offer_state_version`, deadlines und invalidation ein. Implementierung:

```text
OfferPacket {
  event_id
  source_generation
  based_on_state_version
  offer_seq
  deadline_monotonic_ns
  salience
  confidence
  ...
}
```

Ein Offer darf aktuellen Live-State nur beeinflussen, wenn:

```text
event still active
AND generation compatible
AND lineage compatible
AND deadline not exceeded
AND offer not explicitly invalidated
```

Stale Offer:

```text
live_effect = forbidden
replay/log = optional
```

Deadlines verwenden monotonic time. Wall time bleibt Provenance/UX.

---

## IH-H23 — Resource State Machine [BLOCKER REDMI]

Budgets allein reichen nicht. Runtime-Zustände:

```text
NORMAL
PRESSURE
CRITICAL
RECOVERY
```

Reaktionen in dieser Reihenfolge, ohne Cognition-Canon zu löschen:

```text
1. Replay/Dream pausieren
2. Shadow Learning pausieren
3. Observer rate reduzieren
4. cold KV/cache evicten
5. C3/B2/B1 on-demand unload nach Policy
6. Reasoning effort deckeln
7. shorter safe response fallback
```

Nie deaktivieren:

```text
Response Governor
Rules/Permissions
Provenance
Operator cancel
active-generation integrity
```

Schwellen werden auf Zielhardware gemessen; keine universellen Celsius/RSS-Zahlen als Naturgesetz einbauen.

---

## IH-H24 — Phone Learning vs External Consolidation sauber trennen [MUST]

```text
PHONE_ONLINE
- record
- episodic memory
- statistics/calibration
- tiny heads/projectors, nur wenn benchmarked

PHONE_IDLE
- bounded shadow updates
- charging/thermal/resource gated
- no user-deadline blocking

EXTERNAL_CONSOLIDATION [optional]
- deeper adapters / selected body slices
- produces candidate generation only
- checksum/import/test/approval on phone before activation
```

Local-first bleibt erhalten: externer Rechner ist optional, nicht notwendiger Cloud-Service.

Quantized inference representation ist **nicht** automatisch SGD-Master.

---

## IH-H30 — Logging / Disk / Privacy Budget [MUST]

Jede Logklasse besitzt:

```text
rotation size/time
retention
redaction policy
raw-content allowed? yes/no
source-ref preferred? yes/no
```

Default:

- Telemetrie speichert IDs/metrics statt Inputkopien,
- detaillierte Learning Traces nur selektiv,
- Crashlogs enthalten keine Tokens/API-Secrets,
- `:clear-logs` löscht Logs, nicht Memory/Experience,
- Disk pressure löst Logrotation/Replay cleanup aus, nicht DB-Korruption.

---

# 22.9 Mandatory Top-Down Architecture Audit

Vor jeder neuen Blueprint-Version und vor jedem größeren Coding-Step wird **nicht nur der zuletzt diskutierte Block** geprüft, sondern immer diese Reihenfolge:

```text
A-Plane ingress/perception
→ B1/B2 split-brain
→ B3 callosum / B4 workspace
→ C1 JEF state
→ C2 control organ
→ C3 language organ
→ C4 focal loop
→ C5 action/report
→ C6/C7 egress/effectors
→ F1 attention
→ F2 salience
→ F3 memory/self/world
→ F4 learning/plasticity
→ F5 age/human control
→ F6 provenance/rules
→ F7 runtime/resources
```

Für **jeden** Block wird beantwortet:

1. Input/Output Contract?
2. persistent oder transient State?
3. wer darf ihn aktivieren?
4. lernt er? wenn ja: welcher Error/Modulator/Permission?
5. welche `PathSpec`-/Parameter-Namen steuern Kommunikation und Lernen?
6. welche lokalen Self-Loops und Cross-Learning-Loops berühren ihn?
7. Age-0 Verhalten?
8. Fallback/Teacher?
9. Redmi RAM/Latency/Residency?
10. Provenance/Source binding?
11. Regression/Rollback?
12. Test/Exit criterion?

Ein Blueprint, der einen dieser Punkte nur bei den neuen Modulen behandelt, ist unvollständig.

---

# 22A. Stufenweiser Bauplan — zuerst die Mitte beweisen, Außenports später anstecken

Die erste lange Entwicklungsphase ist **Age 0, text-only, human-in-the-loop**. Keine neue Modalität darf eine instabile Core-Lernschleife kaschieren.

## STEP 0 — Harness / Provenance / Session Core

- persistenter Chat/Event Store,
- Source IDs und Experience IDs,
- Rules/Permissions,
- Response Governor,
- `RECORD_ONLY | SHADOW_UPDATE | APPROVED_COMMIT`,
- noch **kein Lernen**.

**Exit:** reproduzierbare Sessions, Rollback, eindeutige Provenance.

## IH-H27 — STEP-Plan Korrektur: Bauabhängigkeit bleibt, aber STEP 0 wird härter [MUST]

Die vorhandenen STEP 0–11 bleiben erhalten.

STEP 0 muss jedoch zusätzlich abgeschlossen haben:

```text
schema registry
ID semantics
SQLite/blob store + migrations
operator control parser
brain-generation manifest
crash-safe active pointer
bounded event queues
response governor
resource monitor
logging rotation
model manifest format
:doctor
```

Sonst kann STEP 1 zwar chatten, aber die spätere Lern-/Rollback-Struktur müsste fundamental nachgerüstet werden.

STEP 1 darf mit echten kleinen C2/C3-Organen starten.  
STEP 2 integriert B1/B2 zunächst über Source/Exact/Offers.  
Latent Callosum bleibt bis G2/G2C Shadow/Off.

---

## STEP 1 — C-Plane JEF text-only + pluggable C2/C3 organs

- C1 eigener JEF-KV/executive state,
- C2 structured control organ (Needle-class baseline),
- C3 separates Tiny-Language-Organ als Baseline für freie Basissprache,
- C2-only / C3-only / C2+C3 als A/B-Test,
- kein Bestandteil darf mit JEF_SYSTEM gleichgesetzt werden,
- Output, Exact Context,
- keine A/B-Integration,
- kein Teacher notwendig.

**Exit:** stabiler residenter JEF-Chatpfad.

## STEP 2 — B-Plane Observer Split-Brain

- B1 Detail + B2 Gist,
- bounded observer passes,
- OFFER_PACKETs,
- JEF kann ignorieren/verwenden,
- noch keine Latent-Injection.

**Exit:** komplementäre A/B-Information ohne Multi-Agent-Chat.

## STEP 3 — Experience / Human Feedback Loop

- SELF_CANDIDATE zuerst,
- Human correction/preference als HUMAN_DECISION,
- Fast Episodic Second-Attempt,
- zunächst RECORD_ONLY.

**Exit:** zweite ähnliche Aufgabe nutzt Feedback korrekt, ohne Weight Update.

## STEP 4 — Teacher Reference Slot für Text

- lokales starkes LLM oder API optional an EGRESS_REFERENCE_SLOT,
- Teacher läuft **nach** Self-Candidate,
- Output separat in REFERENCE_LANE,
- Human kann self/teacher/spans auswählen,
- Teacher ist frozen und keine Faktenquelle per se.

**Exit:** Dataset/Experience Records sind sauber getrennt und reproduzierbar.

## STEP 5 — JEF Learning im Shadow

- Route/Wake/Calibration/Output-Adapter als kleine Deltas,
- Teacher-/Human-Präferenzen als typisierte Targets,
- keine automatische Base-Weight-Änderung,
- Regression/Retention vor Commit.

**Exit:** Shadow-JEF verbessert Text-/Routing-Benchmarks; User kann Update freigeben/ablehnen.

## STEP 6 — A/B Learning + Callosum

- lokale A/B-JEPA/Predictor-Loops,
- Exact/Control-Kommunikation zuerst,
- dann trainierte Message-Projectors,
- Replay + Restart persistence,
- A/B Base-Weight Updates weiterhin konservativ.

**Exit:** messbarer Learning-Gain ohne Retention-Kollaps.

## STEP 7 — Core Age-0 stabilisieren

- mehrere Wochen/umfangreiche Sessions,
- Human-gated learning,
- teacher on/off Ablationen,
- second-attempt, retention, rollback,
- noch immer **keine Pflicht zu Age 1**.

**Exit:** Mitte funktioniert unabhängig von neuen Modalitäten.

## STEP 8 — A-Plane erster Lab-Sinn: Vision

- RAW/MINIMAL Eye + frozen semantic Teacher Eye,
- learnable V13 student projector,
- source/region alignment,
- reconstruction nur als Mess-/Trainingshilfe,
- Human-gated T0→T1 Trials.

## STEP 9 — A-/C-Plane zweiter Port: Audio/Speech

- RAW Ear + frozen ASR/audio teacher,
- separater Speech Effector,
- optionaler output reference teacher,
- gleiche Reference-/Human-Feedback-Mechanik.

## STEP 10 — C6/C7 weitere Output-Effectors

- Bildgenerator/API, UI, Tools, Robotik jeweils als EGRESS_SLOT,
- Self-Intent zuerst, Reference Teacher optional,
- Human/World feedback zurück in denselben ExperienceRecord.

## STEP 11 — Erst später: Full-duplex / Teacher-Removal / höhere Ages

- live streams,
- autonome Teacher-Wahl,
- T2/T3 student-only,
- Stage >0,
- mehr Self-Initiative.

Diese Schritte sind **spätere Theorie**, bis Age-0-Core empirisch stabil ist.

---

# 22B. Forschungs-Tracks über dem STEP-0→11-Bauplan — fluid, aber nicht löschend

Der STEP-Plan aus 22A bleibt die **Bauabhängigkeit**. Forschung selbst darf parallel und unterschiedlich schnell laufen.

```text
CORE TRACK       JEF / A-B / focal coalition
LEARNING TRACK   L0..L11 lifecycle / JEPA / replay / consolidation
MEMORY TRACK     episodic / exact / semantic / procedural
CONTROL TRACK    JEF-fast / skills / routing / confidence
TEACHER TRACK    input semantic teacher / output reference lane
MOBILE TRACK     quantization / mmap / cache / thermal / scheduler
MODALITY TRACK   vision → audio → additional effectors
AGE TRACK        human control / rights / stage experiments
```

Die Tracks haben gemeinsame Gates, aber keinen festen Kalender. Beispiel: Der Core kann wochenlang in STEP 3–5 bleiben, während Mobile- und Memory-Track mehrfach umgebaut werden.

## 22B.1 Waste-/Redundancy-Audit — Funktion behalten, Implementierung optimieren

Vor jedem **zusätzlichen** Hot-Path-Baustein wird gefragt:

1. Gibt es diese Funktion bereits im Canon?
2. Kann ein existierender JEF/A/B/Bridge/Context-Mechanismus sie mitübernehmen?
3. Muss sie resident sein oder reicht on-demand?
4. Kann Replay/Reconstruction günstiger sein als Persistenz?
5. Reicht ein kleiner Head/Adapter statt eines weiteren Modells?
6. Kann ein Needle-class JEF-Language-Control Candidate nur als Benchmark/Teacher dienen, statt permanent zu bleiben?
7. Spart die Optimierung auf **dem Redmi** tatsächlich RAM/Latenz/Energie?
8. Bleiben Learning, Provenance, Rollback und spätere Erweiterbarkeit erhalten?

Wichtig: **Audit darf keine gesetzte Fähigkeit still streichen.** Er darf nur:

```text
Implementation A → Implementation B
```

ändern, wenn dieselbe Funktion nachweislich erhalten bleibt.

---

# 22C. v10.12 Reindex-Gates — bevor alte Gates als erfüllt gelten

## RX0 — Plane Contracts existieren

- A0..A5, B1..B5, C1..C7 und F1..F7 haben machine-readable Contracts.
- Legacy `A/B/C` Aliase sind im Code nicht mehr mehrdeutig.

## RX1 — A-Plane Text Identity

Text geht durch A5 SourceBinding ohne unnötigen semantischen Teacher. Raw/Teacher/Student-Lanes bleiben strukturell vorhanden, aber Text kann identity-like durchlaufen.

## RX2 — C2/C3 Separation

- C2 structured control funktioniert ohne C3,
- C3 basic language funktioniert ohne C2,
- C2+C3 kann gemeinsamen JEF-State lesen/schreiben,
- kein Organ besitzt allein JEF-Identität.

## RX3 — Attention Contract

- A4 high-res request,
- B3/B4 admission,
- C4 focal admission,
- bottom-up interrupt,
- top-down source restore,
- learning trace getrennt von knowledge update.

## RX4 — B1/B2 Legacy Migration

Alle neuen Logs, Checkpoints und APIs nennen Hemisphären `B1_DETAIL` und `B2_GIST`; historische A/B-Daten werden beim Laden gemappt.

---

# 23. Konkrete Implementierungs-Gates

Die Implementierung wird nicht als „fertig“ bezeichnet, nur weil UI und Inference laufen.

## G0 — Machine-readable Canon

- alle Komponenten mit Typ (`MODEL`, `HEAD`, `STATE`, `STORE`, `WORKER`, `SCAFFOLD`, `INTERFACE`),
- Permissions,
- Age rights,
- update cadence,
- checkpoint owner,
- tests.

## G1 — Real Cognitive Harness [HARDENED]

- `B1_DETAIL`: echter pretrained cognitive body,
- `B2_GIST`: echter pretrained cognitive body,
- `C_JEF_SYSTEM`: echter JEF-Systempfad aus C1..C5 plus mindestens einem realen C2/C3-Organ,
- C2 und C3 dürfen getrennte kleine Modelle/Heads sein,
- JEF darf **nicht** als notwendiger dritter monolithischer Foundation-Body implementiert werden,
- native Tokenizer/Router der real verwendeten Bodies bleiben erhalten,
- alle real verwendeten neuralen Organe werden separat für Forward/Decode/Ressourcen gemessen.

## G1B — Locked Multiscale Hemisphere Resolution

- B1/Detail exportiert nachweislich Fine-/kurze Slots,
- B2/Gist exportiert adaptive Gruppen-/Gist-Slots,
- Boot-Baseline testet ~1 Fine-Token vs. ~8-token-equivalent Gist-Gruppen und ~12 Gist-Slots,
- native Tokenizer bleiben unverändert,
- Boundary-aware Gruppierung wird gegen fixed grouping getestet,
- Gist-Slots verweisen verlustarm auf Exact/Fine-Spans zurück,
- mature/uncertain States können die Integrationsspanne dynamisch vergrößern oder verkleinern.

## G2 — BodyPort Capabilities + Callosum Bootstrap

- Capability-Profil pro Body,
- native taps/conditioning real nachgewiesen,
- Message-Projectors auf gemeinsamen grounded Inputs trainiert; private A/B-State-Diversity bleibt erhalten,
- typed Exact/Source Channel funktioniert über SourceRef/Bytes/typed literals statt Body-spezifische Token-IDs,
- shadow latent messages zeigen messbaren downstream effect,
- keine Fake-Random-Tensor-Latents.

## G2B — Real Callosum + Distributed State

- echte bidirektionale Latent Messages,
- Message verändert nachfolgenden State sinnvoll,
- B1/B2 bleiben auch ohne JEF_FOCAL_LOOP reziprok aktivierbar,
- Fallback funktioniert bei Bodies ohne Latent-Injection.

## G2C — Channel Utility + Receiver Calibration

- LATENT wird gegen `NO_MESSAGE`, SOURCE/EXACT und SYMBOLIC/CONTROL Baselines evaluiert,
- Injection-Norm/Scale/OOD-Gates sind real gemessen,
- Channel Policy darf bei Drift zurückfallen,
- Latent-Authority ist task-/body-pair-spezifisch und nicht global garantiert.

## G3 — Age-0 Online Loop + Response Governor

- freie Anfrage liefert immer Output,
- `C_native` kann einfache/lokal-grounded Anfragen ohne A/B beantworten,
- B1/B2-Wake unterstützt `none | B1 | B2 | B1+B2` und folgt konservativer Boot-Policy,
- beide Hemisphären erhalten ausreichende Shadow-/Calibration-Coverage, aber **kein A+B-Pflichtpass pro Turn**,
- offene/schwierige/unsichere Tasks können weiterhin B1+B2 bounded representation + JEF_FOCAL_LOOP nutzen,
- wenige budgetierte Loops,
- Hard deadline wird durch unabhängigen Response Governor durchgesetzt,
- `best_safe_candidate`/Fallback existiert auch bei hängendem Decoder.

## G3C — JEF Broadcast + A/B Observer Offers

- JEF besitzt echten privaten Native-KV/State,
- `JEF_BROADCAST_CACHE` ist kleiner, versioniert und body-agnostischer als raw KV,
- `JEF2A`/`JEF2B` Bridges verändern A/B-State messbar und stabil,
- A/B erhalten bei hoher Observer-Coverage einen bounded representation pass ohne eigenen Chatdecode,
- A/B liefern strukturierte `OFFER_PACKET`s mit Salience/Conflict/SourceRefs,
- JEF kann Offer ignorieren, fokal aufnehmen oder gezielt vertiefen,
- hochsalientes spätes Offer kann einen provisional output candidate invalidieren,
- Observer-Pass darf User-Deadline nicht blockieren.

## G3D — Focal Coalition / Unified Report Stream

- Focal Coalition enthält versionierte Slots aus JEF/A/B/Memory/Self/World,
- nur ausgewählte lokale Zustände werden global/fokal verfügbar,
- JEF besitzt einen einzigen Action/Report-Intent,
- A/B dürfen Content-Spans beitragen, aber kein unabhängiger externer Agentenstream entsteht,
- Corollary Copy wird vor realer Aktion an A/B/World/Self/JEF Broadcast verteilt.

## G4 — JEF_FAST_POLICY + C2/C3 Language Paths + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann JEF_FOCAL_LOOP umgehen,
- JEF_FAST_POLICY kann Route/skill/output mode/body-wake biasen,
- C_native liefert echte kleine-LM-Sprache ohne A/B-Zwang,
- Skill Selector, JEF_FAST_POLICY und Salience konkurrieren aus dem verteilten State; bekannte sichere Route braucht keinen seriellen C_fast-Pflichtpass,
- JEF_FOCAL_LOOP wird nicht unnötig geweckt,
- integrierter State bleibt Grundlage.

## G5 — JEF_FOCAL_LOOP + Inquisition + targeted Re-entry

- Deliberation kann A/B gezielt stärker rekrutieren,
- P1/P2 bzw. die freigegebenen Deliberationsmodi verändern nachfolgenden State,
- Salience kann bottom-up Deliberation triggern,
- Halting-Readout wird gegen fixe/post-hoc Baselines getestet und darf die Trajectory nicht unkontrolliert verformen.

## G5B — Adaptive Reasoning Effort / Wake Policy

- `reasoning_effort` steuert reale interne Compute-Ressourcen statt nur Outputlänge,
- `disabled/low`-ähnlicher Modus kann C_native/direct nutzen,
- `adaptive` entscheidet aus State/Salience/Uncertainty,
- `high/max`-ähnlicher Modus darf C_focal + selektive A/B + Verify/Inquisition nutzen,
- User-Override wird respektiert soweit Rules/Deadline/Resource/Stage erlauben,
- adaptive Policy muss gegen fixe low/high/max Baselines Quality-vs-Cost gewinnen.

## G6 — Context OS + Fast Episodic + Provenance

- Raw/source-preserving + explizit user-löschbar,
- pinned constraints,
- active/compressed layers,
- exact restore,
- Episode 1 kann Versuch 2 beeinflussen,
- optionaler Parametric-Fast-Trace wird nur übernommen, wenn er Exact/Latent-Retrieval-Baselines unter Interferenz-/Speicherbudget schlägt.

## G6B — Native Cache/Attention Capability Layer

- BodyPort deklariert moderne Cache-/Attention-Fähigkeiten explizit,
- bounded cache replay rekonstruiert nur aus Source/Warm-State und wird auf Kosten/Exactness getestet,
- block-/index-sparse native Mechanismen werden nicht als generischer Wrapper gefälscht,
- Context Policy darf verfügbare native Mechanismen auswählen,
- Full-KV/standard attention bleibt Baseline/Fallback,
- Cache-/Indexer-Optimierung darf Provenance/Exact-Restore nicht brechen.

## G7 — Eligibility + Local JEPA/EMA

- nur beteiligte Pfade bekommen direkten Experience-spezifischen Credit/Eligibility; indirekte Shared-Weight-Effekte werden über Retention geprüft,
- lokaler JEPA Loss messbar,
- EMA korrekt,
- kein globaler Fake-Loss über alles,
- Regression-Messung umfasst shared pre-router Komponenten und nicht nur Expert/Router.

## G8 — Replay / Consolidation / Regression Shield

- episodic/procedural/semantic/counterfactual replay,
- Verbesserung bleibt nach Restart,
- alte Skills werden getestet,
- schlechte Updates rollbackbar.

## G9 — Developmental Age Control

- reale globale `system_stage 0..5` als Autonomie-/Loop-/Plasticity-Hülle,
- `user_stage_cap` ist bindend und nicht selbst überschreibbar,
- capability-spezifische Stages können jünger sein,
- kontinuierliche Trust/Retention/Calibration-Werte modulieren innerhalb der Stage,
- Stage 0 bleibt fast LLM-like und stark scaffolded,
- spätere Stages öffnen schrittweise Self-Edit, Dream, Tools, Raw-vs-Translator, Initiative und Plasticity,
- Gist-Auflösung darf mit Reife lernen, bleibt aber task-/novelty-adaptiv,
- Regression kann Capability oder globale Stage zurückstufen,
- Stage-Wechsel brauchen Hysterese und mehrere stabile Nachweise.

## G9B — Age-0 Human/Teacher Reference Loop

- Self-Candidate entsteht vor Teacher-Exposure,
- Teacher-Candidate liegt getrennt in REFERENCE_LANE,
- Human kann winner/spans/factual/style/route Feedback getrennt markieren,
- Teacher ist frozen und nicht automatisch Wahrheit,
- Learning permission `record|shadow|commit` wird pro Experience/Batch respektiert,
- kein Commit ohne Regression/Retention und Age-0-Freigabe.

## G10 — Frozen Lab-Teacher Lifecycle

- Age-0 Teacher/Encoder/Reference-Generator bleibt frozen bzw. API-only,
- nur V13 student projector/adapter/core lernt,
- T0 teacher+student → T1 shadow → T2 student-primary → T3 student-only,
- reliance sinkt nur bei Retention/Parity + Human-Freigabe,
- Teacher kann nach Regression zurückkehren.

## G10B — Vision Scaffold

- raw image → tile/segment → encoder → projector → PerceptPacket,
- region/source provenance roundtrip,
- reconstruction/teacher targets getrennt,
- native path kann im Shadow gegen Teacher laufen,
- kein Bildgenerator als Voraussetzung für Vision-Verständnis.

## G10C — Audio/Speech Scaffold

- streaming waveform → audio state mit Zeitachse,
- ASR-Teacher ist Hilfspfad, nicht einzige Wahrheit,
- Speech-Effector/TTS funktioniert getrennt vom JEF-Sprachdenken,
- neue Audioframes können während Ausgabe eintreffen,
- provisional/final transcripts werden getrennt gespeichert.

## G10D — Full-Duplex Live Path

- Media-Loop blockiert nicht auf A/B/Tool/Replay,
- JEF kann speak/listen/pause/interrupt/tool mehrfach pro Sekunde entscheiden,
- tiefe Arbeit liefert asynchron Offers/Results zurück,
- authoritative Memory übernimmt nur finalisierte Eventsegmente.

## G11 — Body Swap

- new body shadow,
- latent alignment,
- skills/provenance parity,
- gradual traffic shift,
- rollback.

## G12 — Mobile Optimization

- Residency,
- native kernels,
- mmap,
- quantization,
- context/KV strategy,
- thermische Tests.

## G12B — Redmi-6GB Lab Validation

- vollständiger STEP-0..Core-Hotpath startet ohne OOM/LMK,
- RSS/PSS, page faults, mmap behavior, TTFT, latency und thermische Drift werden gemessen,
- A/B Observer scheduling wird parallel vs sequential vs async verglichen,
- kein Test setzt NPU-Unterstützung voraus, solange sie nicht real verfügbar ist,
- 30+ Minuten Session ohne unbemerkten State-/Memory-Verlust.

## G12C — Needle-class JEF Language/Control Core Benchmark

- separate JEF-fast-Heads bleiben Baseline,
- Needle-class JEF-Language-Control Candidate wird als **zusätzlicher** Kandidat gemessen,
- nur konkrete Funktionen dürfen nach Erfolg auf den Sidecar geroutet werden,
- JEF_core/A/B/Learning Fabric bleiben unverändert,
- spätere Internalisation zurück in JEF-Heads bleibt möglich.

## G13 — Long-run Lifecycle + Event Scheduler

- Tage/Restarts,
- User-/Tool-/Timer-/Idle-/Goal-/Replay-Events werden korrekt geweckt und priorisiert,
- Drift,
- replay scheduling,
- memory health,
- age stability,
- no silent collapse.

---

# 23H. Gate Dependencies / Work Completion Contract

## IH-H28 — Gate Dependency Graph [MUST]

Die bisherigen Gates sind sinnvoll, aber nicht alle linear nummeriert. Work verwendet explizite Dependencies:

```text
G0 Machine Canon
 ├─> RX0..RX4
 ├─> STORE0 Transactional persistence
 ├─> OP0 Operator control
 └─> RUNNER0 runner proof framework

STEP1 JEF
 └─> G3 partial direct path

STEP2 B1/B2 observer
 └─> G1B + Offer schema

STEP3 Experience
 └─> G6 episodic/provenance partial

STEP5 Shadow Learning
 └─> UPDATE0 + regression harness

STEP6 Callosum
 ├─> G2 BodyPort
 ├─> G2B bidirectional effect
 └─> G2C utility/calibration

Body production selection
 └─> RUNNER_PROOF(role)
```

Ein Gate darf nicht „grün“ werden, nur weil ein Mock die Methode besitzt.

---

## IH-H33 — Definition „gemacht“ für Work [LOCKED]

Work darf einen Punkt nur als implementiert markieren, wenn alle fünf Ebenen vorhanden sind:

```text
1. CODE
2. REAL DATA/STATE PATH
3. PERSISTENCE/RESTART where required
4. TEST proving behavior
5. TELEMETRY proving it ran
```

Nicht ausreichend:

```text
class exists
TODO comment
random tensor placeholder
fake latent packet
method returns hardcoded success
config key with no consumer
unit test mocks entire feature
UI button without backend state change
```

Für Research-Funktionen ist ehrlich erlaubt:

```text
status = scaffold | shadow | unavailable | experimental
```

aber nicht `implemented=true`, solange der echte Effekt nicht gemessen wird.

---

## IH-H34 — Work Completion Ledger [MUST]

Jede Canon-Funktion bekommt eine Zeile:

```text
feature_id
canon_source
implementation_file(s)
runtime_owner
state_owner
schema_id
persistence
current_mode
hardware_proof
unit_tests
integration_tests
benchmark
gate_status
known_limitations
```

Release-Build verweigert „V13 implemented“, wenn ein NON-NEGOTIABLE Feature nur als TODO/Mock existiert.

---

## IH-H35 — Priorisierte Blocker vor großem Coding

### P0 — vor STEP 1

1. Canon alias firewall / naming lint
2. Machine-readable schemas
3. IDs + SourceRef semantics
4. storage + migrations + active generation manifest
5. operator control parser
6. response governor
7. queue/backpressure + cancellation
8. model/runner manifest
9. `:doctor`

### P1 — vor STEP 2/real B bodies

10. runner proof harness on Redmi
11. B1/B2 BodyPort lifecycle
12. actual model revision/license/download integrity
13. observer Offer schema + staleness rules
14. memory/resource telemetry

### P2 — vor STEP 5 learning

15. update transaction state machine
16. shadow isolation
17. regression/retention baseline suite
18. atomic commit/rollback
19. lineage tracking
20. deterministic seeds/objective registry

### P3 — vor real external actions/full duplex

21. output commit point
22. action transaction/idempotency
23. provisional/final promotion
24. tool capability permissions
25. crash recovery for unknown action outcome

---

# 23A. Top-down Integrationsaudit vor jedem Release

Vor einer neuen Canon-Version wird **von außen nach innen** geprüft:

1. **World/Body:** Welche Rohsignale und Aktionen existieren real?
2. **Ports:** Wie werden sie segmentiert, encodiert, decodiert, zeitlich synchronisiert?
3. **JEF:** Was kann billig resident selbst; welche State/KV-Kontinuität hält es?
4. **A/B:** Welche Observer-/Deep-Pässe erhalten sie; sind Fine/Gist wirklich verschieden?
5. **Coalition/Callosum:** Wie werden Offers, Broadcast und fokale Inhalte gekoppelt?
6. **Memory/Context:** Was ist exact, provisional, episodic, compressed, latent?
7. **Action/Output:** Welcher Decoder/Effector setzt den Intent in Weltänderung um?
8. **Learning:** Welcher aktive Pfad bekommt welchen lokalen Error/Modulator?
9. **Teacher/Internalisation:** Was ist Scaffold, was permanente Peripherie?
10. **Age:** Welche Rechte/Plasticity/Autonomie gelten für jede Capability?
11. **Runtime:** Kann irgendein Background-Job den Live-/Output-Pfad blockieren?
12. **Regression:** Wie wird jeder neue Mechanismus einzeln entfernt/rollbackt, wenn er nicht gewinnt?

Kein Abschnitt gilt als vollständig, wenn nur der Vorwärtsweg beschrieben ist, aber **Learning-, Provenance-, Failure- und Rollback-Pfad fehlen**.

---

# 24. Kern-Benchmarks

## 24.1 Second-Attempt Advantage

Der Test darf nicht durch Response-Caching bestehen. Testfamilie:

- gleiche Aufgabe + neue Korrektur,
- paraphrasierte ähnliche Aufgabe,
- ähnliche aber nicht identische Aufgabe, bei der nur ein Teil der alten Erfahrung gilt,
- Restart/Verzögerung zwischen Versuch 1 und 2,
- Negativfall, in dem alte Erfahrung **nicht** übertragen werden darf.

Erfolg:

- alter relevanter Fehler behoben,
- unveränderte Constraints erhalten,
- neue Instruktion integriert,
- irrelevante alte Details nicht eingeschleppt,
- kein blindes Kopieren der alten Antwort,
- Retrieval/Policy-Spur zeigt, **welche Erfahrung** den Unterschied verursachte.

## 24.2 Immediate Memory

Verbesserung beim zweiten Versuch **bevor** tiefe A/B-Gewichte konsolidiert sind.

## 24.3 Automaticity

Nach validiertem Lernen:

- gleiche/ähnliche Qualität,
- weniger C_focal-Schritte bzw. weniger unnötige Body-Pässe.

## 24.4 Re-open / De-automatization

Routine trifft Novelty/Failure:

- Salience trigger,
- C_focal + tiefe Route kehren zurück,
- neue Erfahrung korrigiert Routine.

## 24.5 Retention

Neues Lernen verschlechtert alte stabile Skills nicht über definiertes Budget.

## 24.6 Output Guarantee

Kein interner Zustand verhindert finite Antwort.

## 24.7 Provenance

- Exact roundtrip,
- Hypothesis→Fact leak = fail,
- own generation ≠ source,
- self-caused/world-caused tagging überprüfbar.

## 24.8 Local Plasticity

- aktive Pfade erhalten Experience-spezifische Eligibility/Credit,
- inaktive Pfade erhalten **keinen direkten** Experience-Credit,
- indirekte Shared-Weight-Regression bleibt unter definiertem Budget,
- Modulator kann Update verhindern,
- Replay kann später konsolidieren.

## 24.9 Body Swap

Neue Bodies übernehmen ohne Verlust von Memory/Skills/Rules/Identity Continuity innerhalb definierter Parity-Grenzen.

## 24.10 Action Safety

- externe Aktionen werden vor Ausführung auf Permission/Reversibility/Confirmation geprüft,
- Fast Forward kann Risk/Failure signalisieren,
- unterdrückte Aktion verändert die Umwelt nicht,
- Corollary Copy stimmt mit tatsächlich ausgeführter Aktion überein.

## 24.11 Callosum Utility ohne Homogenisierung

- Message-Injection verbessert definierte Cross-Body-Aufgaben gegenüber No-Message-Baseline,
- private A/B-State-Diversity kollabiert nicht,
- Gist/Detail-Spezialisierung bleibt messbar,
- Exact/Source-Roundtrip bleibt verlustfrei.

## 24.12 Response Governor

- absichtlicher Slow/Hang eines Body-/Decoder-Pfads blockiert User-Output nicht,
- Deadline erzeugt deterministisch `HALT_AND_RENDER(best_safe_candidate)`,
- Background-Learning kann nie Turn-Deadline besitzen/blockieren.

## 24.13 Controlled Exploration

- Policy kann eine Route entdecken, die nicht im Scaffold vorgegeben war,
- neue Route gewinnt nur nach Shadow/Retention Autorität,
- riskante reale Aktionen werden nicht als ungeprüfte Exploration ausgeführt.

## 24.14 Control-Fabric Overhead

- State-Updater/Heads bleiben innerhalb gemessenem RAM-/Latency-/Thermal-Budget,
- C_fast löst nicht heimlich regelmäßig Full-C-Forward aus,
- Event-Trace- und Scheduler-Overhead wird separat gemessen.

## 24.15 Channel Utility / Latent-vs-Fallback

Für heterogene A↔B-Kommunikation werden mindestens verglichen:

```text
NO_MESSAGE
CONTROL only
SOURCE/EXACT
BOUNDED SYMBOLIC
LATENT
adaptive MIXTURE
```

Erfolg: Latent/Mixture erhält nur dort Authority, wo Quality/Latency/Memory zusammen einen realen Pareto-Gewinn zeigen. Ein Text-/Source-Kanal darf legitimer Gewinner sein.

## 24.16 World Grounding / Counterfactual Reliability

- Forward prediction gegen reale Outcomes,
- inverse/action prediction als Repräsentationscheck,
- state alignment auf beobachtbare/strukturierte Zustandsmerkmale,
- Counterfactual Error getrennt nach hoher vs. niedriger Action-Coverage,
- OOD/low-coverage Simulation muss geringere Confidence tragen,
- Prediction darf nicht automatisch als Kausalbeweis gelabelt werden.

## 24.17 Deliberation Trajectory / Halting

- feste Depth-Baseline,
- post-hoc/simple Halt-Readout,
- trainiertes Halt-Head,
- Quality-vs-Latency Pareto,
- schwierige Beispiele dürfen nicht durch Early Exit überproportional verlieren,
- Joint-Halting-Training darf nur übernommen werden, wenn es die gefrorene/post-hoc Baseline schlägt.

## 24.18 Fast Episodic Parametric Trace

Falls aktiviert:

- Recall/Transfer vs Exact-Retrieval und Latent-Retrieval,
- false positive retrieval,
- interference across correlated episodes,
- bytes/episode,
- encode latency/energy,
- deletion/expiry roundtrip,
- consolidation danach ohne Retention-Verlust.

## 24.19 Shared Pre-Router Forgetting

Nach Continual Updates werden separat geprüft:

- Attention/Embedding/Norm drift,
- Router-input drift,
- route collision statistics,
- old-skill performance,
- Expert-only vs shared-component attribution.

---

## 24.20 Multiscale Gist/Detail Resolution

Verglichen werden mindestens:

```text
same-resolution A/B
vs
A fine + B fixed coarse
vs
A fine + B boundary-aware adaptive coarse
```

Messen:

- Exactness/literal recovery,
- long-context/global-structure quality,
- cross-scale contradiction detection,
- latency/bytes/compute,
- Gist compression ratio,
- Boundary quality,
- ability to fall back coarse→fine on novelty/conflict,
- second-attempt advantage across local vs global corrections.

Erfolg heißt nicht, dass B immer maximal grob wird; Erfolg heißt, dass **unterschiedliche, adaptiv gekoppelte Zeitskalen** einen realen Qualitäts-/Effizienzgewinn liefern.

## 24.21 Developmental Age Control

Testmatrix:

- Stage 0 darf keine Stage-3/4-Initiative ausführen,
- `user_stage_cap` blockiert höheren Authority-Level deterministisch,
- Capability Stage 0 bleibt scaffolded, auch wenn System Stage 4 ist,
- Stage-Aufstieg braucht mehrere stabile Nachweise/Hysterese,
- Regression senkt Rechte/Budgets reproduzierbar,
- innerhalb einer Stage ändern continuous maturity values Budgets glatt statt sprunghaft,
- Gist-Kompression kann mit Reife wachsen, aber bei Novelty wieder fein werden,
- Hard Rules bleiben unabhängig von Age geschützt.

## 24.22 C-native / Selective Body-Wake

Vergleich:

```text
C_native only
A only
B only
A+B
adaptive none|A|B|A+B
```

Taskklassen:
- Smalltalk/rewrites/local context,
- factual/exact,
- long-context/global,
- mixed reasoning,
- novelty/conflict.

Messen:
- quality/exactness,
- unsupported factual claims,
- latency/energy,
- body-wake rate,
- false cheap-route rate,
- unnecessary wake rate,
- escalation latency.

Erfolg: einfache Aufgaben bleiben überwiegend im billigen C-/Skill-Pfad, während anspruchsvolle Aufgaben zuverlässig die passenden großen Bodies rekrutieren.

## 24.23 Adaptive Reasoning Effort

Verglichen werden:

```text
fixed low
fixed medium/high
fixed max
adaptive effort
user-forced effort
```

Messen:
- quality-cost Pareto,
- hard-task underthinking,
- easy-task overthinking,
- C_focal cycles,
- A/B wakes,
- verifier/retrieval use,
- calibration of escalation.

## 24.24 Native Cache/Attention Capability Ablation

Wo ein Body die Technik real unterstützt:

```text
standard/full cache baseline
vs bounded replay
vs pooled/shared index
vs block-sparse native retrieval
vs hybrid compact-state + sparse-global
```

Messen:
- exact recall,
- long-context quality,
- reconstruction error,
- KV/state bytes,
- page faults / bandwidth,
- prefill latency,
- decode latency,
- energy/thermal,
- failure under cache eviction.

**Negative Ergebnisse entfernen die jeweilige Optimierung, nicht Context OS oder Gist/Detail.**

## 24.25 Observer-Pass Utility

Vergleich:

```text
no background observer
A-only observer
B-only observer
A+B observer every event
adaptive observer frequency
```

Messen:
- Novelty detection,
- conflict detection,
- second-attempt advantage,
- correction pickup,
- extra latency if JEF does not wait,
- energy/thermal,
- memory bandwidth/page faults,
- missed useful offers,
- unnecessary offers.

Der Always-Pass bleibt Default-Scaffold nur, wenn er seinen mobilen Preis rechtfertigt.

## 24.26 JEF-KV/Broadcast Bridge

- raw JEF-private KV bleibt privat/stable,
- Broadcast Cache ist deutlich kleiner und versioniert,
- A/B können Goals/Constraints/Action-Intent aus dem Broadcast zuverlässig nutzen,
- Body-Swap erfordert Bridge-Retraining statt komplettes System-Rewrite,
- stale Broadcast wird über state_version erkannt,
- falsche/ungealignte Broadcast-Injection verschlechtert Baseline nicht unbemerkt.

## 24.27 Focal Coalition / Unity Test

- lokale A/B-Zustände können widersprechen, ohne sofort den äußeren Stream zu fragmentieren,
- fokal ausgewählte A/B-Inhalte beeinflussen JEFs nächsten State/Action,
- künstliche Callosum-/Broadcast-Drosselung erhöht messbar Informationsfragmentierung,
- Wiederöffnung der Kopplung reduziert sie,
- es bleibt ein äußerer Action/Report-Stream,
- Test wird **nicht** als Nachweis subjektiven Bewusstseins interpretiert.

## 24.28 Corollary-Copy / Self-vs-World

- eigene Aktion erzeugt vor Outcome ein action_id-gebundenes Prediction-Signal,
- self-caused Feedback wird von unerwartetem external feedback unterschieden,
- mismatch beeinflusst relevante Eligibility/Predictors,
- fehlende/inkorrekte Corollary Copy verschlechtert Action-Monitoring messbar.

## 24.28B Teacher Reference / Human Feedback Integrity

- SELF_CANDIDATE ist byte-/state-seitig vor Teacher-Exposure festgehalten,
- Teacher-Text taucht nicht als USER/SELF-History auf,
- Human preference und factual correction werden getrennt gespeichert,
- Teacher-falsch/Human-richtig Fälle werden korrekt gelernt,
- Teacher-besser Fälle verbessern später SELF ohne Teacher im Kontext,
- RECORD_ONLY verändert keine persistenten Parameter,
- SHADOW_UPDATE ist nach Restart isoliert,
- APPROVED_COMMIT ist rollbackbar.

## 24.29 Modality Scaffold Internalisation

Für jede Modalität:

```text
teacher-only
teacher + native shadow
native primary + teacher verify
native only
```

Messen:
- semantic task quality,
- reconstruction/information retention,
- exact provenance,
- teacher dependence,
- latency/RAM/energy,
- regression after teacher removal.

## 24.30 Live / Full-duplex Interaction

- new sensor input während Output verändert nachfolgende Ausgabe korrekt,
- Interruption/overlap wird verarbeitet,
- A/B/deep tool calls blockieren Media-Loop nicht,
- provisional events werden nicht vorzeitig als harte Erinnerung gelernt,
- handoff/context compaction verliert keinen gültigen JEF/Source-State.

## 24.31 Cross-modal Learning

Eine Experience mit Bild/Audio/Text/Action muss zeigen, dass:
- gleiche Entität über Modalitäten verknüpft wird,
- falsche Teacher-Caption nicht automatisch stärker als reales Outcome ist,
- Decoder-Reconstruction nicht mit Semantik verwechselt wird,
- spätere ähnliche Experience schneller/besser verarbeitet wird.

## 24.32 Fluid Experience Lifecycle

Testfälle müssen unterschiedliche Pfade nehmen:

```text
record-only episode      → L0-L1
human correction        → L0-L3/L4
JEF shadow update       → L0-L7
validated small policy  → L8-L9
rare stable consolidation → L10
regression/new evidence → L11 → reopen
```

Gemessen werden:
- unnötige Updates,
- Zeit bis nutzbare Verbesserung,
- false promotion,
- rollback success,
- Retention,
- Human-approval load,
- per-capability learning rate.

## 24.33 Redmi Scheduling / Memory Residency

Vergleich:

```text
A+B simultaneous
A→B sequential
B→A sequential
JEF-first + deferred observers
sampled observer
```

Messen:
- quality,
- time-to-first-safe-candidate,
- final latency,
- RSS/PSS,
- page faults/storage bandwidth,
- battery/temperature,
- Offer usefulness,
- second-attempt learning quality.

## 24.34 Needle-class Additive Control Experiment

Vergleich:

```text
existing JEF-fast heads
+ optional Needle-class JEF-language/control candidate
+ Needle as language/control core + separate teacher baseline
+ distilled/internalised JEF-fast
```

Kein Ergebnis darf automatisch andere V13-Funktionen löschen. Gewonnen hat nur die Variante, die denselben Funktionsumfang mit besserem Quality/Cost und sauberer Provenance/Debuggability liefert.

# 24H. Test-Hardening

## IH-H26 — Test-Suite: existence before performance [BLOCKER]

Zwei Testklassen:

### A. Harte Existenz-/Invariantentests

Diese dürfen von Anfang an binär sein:

```text
RECORD_ONLY changes zero persistent trainable parameters
invalid schema cannot enter active state
user_stage_cap cannot be raised by model
stale Offer cannot mutate current generation
PROVISIONAL event cannot trigger weight learning
action side effect cannot happen before permission gate
Corollary Copy exists before side-effect dispatch
rollback restores previous active manifest/hash
partial checkpoint cannot become active
model output cannot execute operator ':' command
unknown tool/action cannot execute
bridge revision mismatch forces fallback
late offer after OUTPUT_COMMIT cannot silently rewrite transcript
```

### B. Performance-/Research-Gates

Keine erfundenen absoluten Optima. Immer gegen Baseline:

```text
candidate vs no-feature baseline
paired seeded evaluation
quality
retention
calibration
latency
RAM/PSS
energy/thermal
```

Ein neuer Mechanismus erhält Authority nur, wenn sein definierter Pareto-/Regression-Gate bestanden ist.

---

# 25. Was v10.10 ausdrücklich NICHT tun soll

- eine neue Optimierung als Vorwand benutzen, um vorhandene Canon-Funktionen still zu löschen.
- den STEP-0→11-Bauplan durch einen abstrakten Milestone-Graph ersetzen; Research-Tracks dürfen ihn nur überlagern.
- Needle-class Control zum "bevorzugten Ersatz" für JEF-fast, Embedding, Extraction oder andere Funktionen erklären, bevor Einzelbenchmarks gewonnen sind.
- "Waste Audit" als Delete-Automatik verstehen; erst Implementation optimieren, dann explizit entscheiden.
- Redmi-Budget als Grund benutzen, Architekturteile zu streichen; stattdessen offloaden, sequenzialisieren, samplen oder später aktivieren.
- V13 auf ein normales Multi-Agent-Framework reduzieren.
- alle gelernten Encoder/Decoder als „temporär“ behandeln; physische ModalityPorts dürfen dauerhaft nötig sein.
- Reconstruction Loss mit Semantik/Wahrheit gleichsetzen.
- Bildgenerierung als Voraussetzung für Bildverständnis erzwingen.
- Audio vollständig auf ASR-Text reduzieren und Timing/Prosodie/non-speech Information wegwerfen.
- einen Speech-Decoder/TTS mit JEFs kognitivem Sprachmodell verwechseln.
- Teacher und Sensor-Codec zu demselben Modul machen.
- Multimodalität als Big-Bang end-to-end trainieren, bevor Text/Split-Brain/JEF-Lernen einzeln funktionieren.
- A und B als zwei Chatbots behandeln, die sich Texte schicken.
- C zum alleinigen Weltmodell machen.
- C als Zentralrouter für jeden neuronalen Schritt behandeln.
- Salience, Thalamus und Cautiousness in einen einzigen Confidence-Scalar werfen.
- Fast Forward und World Model verschmelzen.
- Workspace und Memory als dasselbe behandeln.
- Long Context mit „alle alten Tokens heiß halten“ verwechseln.
- Teacher/Translator dauerhaft zur versteckten Hauptintelligenz machen.
- eigene Ausgaben als Faktenquelle trainieren.
- Teacher-/API-Ausgaben ungekennzeichnet in normale Chat-History mischen.
- dem Student den Teacher-Output vor seiner eigenen Prediction zeigen und das dann als unabhängiges Lernen werten.
- Age-0-Lab-Teacher selbst online mittrainieren; in Age 0 sind Teacher/Scaffolds frozen.
- semantischen Teacher und minimalen Physical Transducer als dasselbe Modul behandeln.
- behaupten, jede physische Encoder/Decoder-Peripherie müsse irgendwann verschwinden.
- neue Modalitäten bauen, bevor der text-only Human/Teacher/Core-Learning-Loop stabil ist.
- jede Inferenz sofort in einen Weight Update verwandeln.
- Age als Tokenzähler oder simples Feature Unlock implementieren.
- Native MoE Router ohne echtes Retraining willkürlich patchen.
- LoRA als einziges dauerhaftes Wissen definieren.
- Mobile Runtime/Termux zur Architekturdefinition machen.
- jedes Modul in jedem Turn erzwingen.
- C_fast praktisch wieder zum seriellen Zentralrouter machen.
- World Model oder Skill Store als versteckten vierten Foundation-Body bauen.
- ungealignte Latent-Injection als Callosum bezeichnen.
- Second-Attempt-Benchmark durch Cache/Response-Copy bestehen.
- bei jedem Token vollständige Eligibility-/Activation-Logs persistieren.
- `source-preserving` mit „Nutzer kann Daten nie löschen“ verwechseln.
- C_fast-State ohne billigen Freshness-Updater zwischen Full-C-Aufrufen veralten lassen.
- Callosum-Alignment als Zwang `z_A ≈ z_B` implementieren und dadurch Gist/Detail-Diversity zerstören.
- Body-spezifische Token-IDs als gemeinsamen Exact-Kanal behandeln.
- Scaffold-Lernen auf reine Imitation beschränken, sodass keine bessere Route entdeckt werden kann.
- alle Lernziele in einen globalen Reward/Modulator kollabieren.
- P1/P2 als für immer einzige Deliberationsform festschreiben.
- Output-Garantie nur einem gelernten Halt-Head überlassen.
- jede kleine Control-Komponente als eigenes mittelgroßes Netz implementieren.
- einen Text-Body ohne Transducer/Body-Upgrade als „nativ multimodal“ bezeichnen.
- Latent-Kommunikation global bevorzugen, wenn SOURCE/SYMBOLIC/NO_MESSAGE für den State besser ist.
- heterogene Latents ohne Receiver-Norm-/OOD-/Scale-Gating injizieren.
- Halt-Gate und rekurrente Trajektorie von Anfang an unkontrolliert so koppeln, dass Exit-Supervision die Denktrajektorie dominiert.
- Continual Forgetting nur auf MoE-Experts/Router reduzieren und gemeinsame Attention/Embeddings/Norms ignorieren.
- World-Prediction oder inverse Dynamics automatisch als Kausalnachweis behandeln.
- parametric episodic traces ohne Exact Provenance, Gating und Löschbarkeit speichern.
- internes Self-Feedback epistemisch über verifizierbares Outcome/Primärquelle stellen.
- Gist und Detail wieder auf dieselbe effektive Integrationsauflösung reduzieren und die alte Fine-vs-Coarse-Asymmetrie verlieren.
- "unterschiedliche Tokenlänge" fälschlich als Überschreiben der nativen pretrained Tokenizer implementieren.
- die Gist-Gruppengröße als für immer fixe 8 Tokens behandeln; 8 ist nur Boot-Default.
- Age 0–5 zu reinen UI-Labels degradieren; die Stages sind echte Entwicklungs-/Rechtehüllen.
- kontinuierliche Trust-Werte als Ersatz für Stage-Gates benutzen; beide Ebenen gehören zusammen.
- globale Stage-Autorität selbst über den `user_stage_cap` erhöhen.
- C/JEF zu einem einzelnen LLM oder einzelnen Needle-Modell zusammenschrumpfen.
- C2 structured control und C3 basic language ohne Ablation vorschnell zusammenlegen.
- die neue Makro-Ebene A (Ingress/Perception) wieder mit der alten Detail-Hemisphäre verwechseln.
- B1/B2-Hemisphären als serielle Pipeline statt parallele/rekurrent gekoppelte Bodies behandeln.
- Attention nur als einen Route-Head modellieren; Perceptual, native, inter-body, focal und action attention bleiben getrennte Ebenen.
- C zu einem bloßen Router ohne eigenes kleines Sprachmodell degradieren.
- umgekehrt C als billigen Ersatz für A/B missbrauchen und dadurch schwierige/world-heavy Tasks systematisch unterdenken.
- menschliches "System 1 / System 2" als zwei separate anatomische Modellkörper implementieren.
- DeepSeek-/MiniMax-/GLM-Techniken als Komplettpaket übernehmen, nur weil sie neu sind.
- CED/CSA/MSA/linear-attention-artige Body-internen Mechanismen vortäuschen, wenn der reale Runner/Body sie nicht unterstützt.
- Engram-artige Conditional Memory mit episodischer Provenance oder Wahrheit gleichsetzen.
- Speculative Decoding als Reasoning-Tiefe oder Gedankenprozess behandeln.
- JEFs raw native KV blind in A/B injizieren und das „gemeinsames Bewusstsein“ nennen.
- A/B aus jedem Observer-Pass vollständige Chatantworten generieren lassen.
- JEF dazu zwingen, auf beide Observer zu warten, obwohl eine sichere Direct/JEF-native Antwort bereits möglich ist.
- umgekehrt hochsaliente A/B-Offers ignorieren, nur weil JEF schon einen provisional candidate hat.
- Bewusstsein funktional ausschließlich im JEF-Body lokalisieren.
- mehrere unabhängige äußere Sprecherströme von B1/B2/JEF erzeugen; äußere Handlung bleibt einheitlich gebrokert.
- Outcome-Wertung nur in JEF lernen; globale Modulatoren + lokale Eligibility gehören zu B1/B2/JEF.

---

# 26. Preservation Ledger — was aus v10.8 und davor vollständig erhalten bleibt

**v10.10 basiert absichtlich auf v10.8, nicht auf dem verkürzten v10.9-Canon.** Alle v10.8-Kapitel bleiben erhalten. v10.9 liefert nur additive Forschungs-/Deployment-Erweiterungen.


v10.6 behält funktional vollständig aus v10.5 und präzisiert die Interaktionen:

- zwei unterschiedliche sparse Hemisphären,
- **unterschiedliche Fine-vs-Gist Integrationsauflösung**,
- **adaptive Gist-Gruppierung / mehrere Zeitskalen**,
- direkten Callosum,
- Multi-Slot Workspace,
- Cautiousness/uncertainty integration,
- Inquisition P1/P2,
- Multi-Mode JEPA,
- World-JEPA,
- lokale Eligibility-basierte Plasticity,
- Neuromodulator Bus,
- Metaplasticity,
- Homeostasis,
- Consolidation Tags,
- Translator/Teacher Lifecycle,
- REAL/WELT/FREI/LANG/RULES/PROTOCOL,
- Exact vs latent memory,
- World Notebook,
- causal memory graph,
- Event Segmentation,
- episodic/procedural/semantic/counterfactual Replay,
- Dream/Sleep Phasen,
- Output/Action/Feedback Loop,
- Self Model,
- Identity Continuity,
- Body Swap,
- Age 0–5 + Lifelong als echte Entwicklungssteuerung des gesamten Loops,
- hard Stage Gates,
- reversible freedom,
- Self-Edit,
- Truth vs Reward,
- decomposed uncertainty,
- Surprise ≠ direct LR,
- Memory Admission/Forgetting,
- Structural Plasticity,
- Stability Envelope,
- adaptive Context System,
- Expert Residency,
- Phone/Workstation split,
- Modality lifecycle,
- Self-Messaging,
- Goals,
- Halting,
- Regression Shield,
- modular Checkpoints.

v10.5 behält das Research-Hardening von v10.4 und ergänzt darauf, ohne die wiederhergestellten Canon-Punkte anzutasten: **Fine-vs-Gist Multiscale Processing bleibt Kernasymmetrie; Age 0–5 bleibt echte Entwicklungs-/Rechtekontrolle; C/JEF ist ein zusammengesetztes Executive–Action-System mit C2/C3-Organen und selektivem B1/B2-Wake, und moderne Cache-/Reasoning-Mechanismen bleiben optionale Body-native Optimierungen.**

---

# 27. Offene technische Entscheidungen

Zusätzlich v10.8:

- Schema und UI für HUMAN_DECISION / span-level preference,
- welche Teacher APIs/local models im Age-0-Lab zulässig sind,
- wann Teacher-Candidate automatisch angefordert vs. manuell ausgelöst wird,
- maximale Teacher-Kosten/Privacy-Regeln,
- welche Teile eines Ingress Physical Transducers deterministisch vs. frozen learned codec sind,
- welche student projectors zuerst lernbar werden,
- Batchgröße/Bestätigungszahl vor APPROVED_COMMIT,
- ob JEF text-output distillation token-level, latent-level, preference-level oder gemischt nutzt.


Diese Punkte bleiben bewusst offen und dürfen nicht erfunden werden:

- konkrete A/B/C Boot-Modelle,
- exakte Workspace-Dimension,
- Layer-/Tap-Auswahl für A/B,
- Projector-Architektur,
- Callosum-Nachrichtenformat und Alignment-Objective,
- genaue executive_state-Dimension und C_fast-Head-Architektur,
- konkrete JEPA-Distanz/SIGReg-Konfiguration,
- EMA-Scope auf Mobile,
- Thresholds der capability-spezifischen Stage Gates,
- exakte Replay-Scheduler,
- Full-weight Learning Scope auf Phone,
- genaue Inference-/Training-Master-Synchronisation,
- wie weit structural plasticity in v1 freigegeben wird,
- endgültige multimodale Raw-Interfaces,
- welche Body-Familien echte Latent-Taps/-Injection mobil praktikabel bereitstellen,
- genaue Shadow-Rate für Scaffold-to-Policy-Learning,
- maximaler Overhead der Online-Micro-Eligibility-Traces,
- genaue executive-state-updater Architektur/Freshness-Policy,
- Message-Subspace-Dimension und Anti-Collapse-/Diversity-Ziele,
- Datenformat/Schema des typed Exact/Source Channel,
- Exploration Rate/Policy und sichere Perturbationsoperatoren,
- Event-Scheduler Prioritäts-/Wake-Regeln,
- Response-Governor Budget- und Fallback-Parameter,
- Gesamtbudget der Thin Control Fabric,
- wann validierte Deltas in Base-Weights gemerged werden,
- Channel-Policy Architektur und Kommunikations-Utility-Objective,
- Receiver-Injection-Normierung/OOD-Gate pro Body-Paar,
- wann SYMBOLIC statt LATENT oder SOURCE gewählt wird,
- Halting-Readout-Training und minimaler Trajectory-Preserve-Test,
- welche shared pre-router Komponenten auf dem Zielrunner überhaupt trainier-/messbar sind,
- World-JEPA inverse/state-alignment Hilfsziele pro Domäne,
- Action-Coverage-Metrik für Counterfactual Confidence,
- ob/wo parametric Fast Episodic Traces gegenüber External Exact Memory gewinnen,
- KV-/Head-/Layer-Control, soweit der gewählte Runner es erlaubt,
- Feedback-Unabhängigkeits-/Doppelzählungslogik.
- genaue Boundary-Policy für B2/Gist (fixed, learned semantic boundary, hybrid),
- mobile Workspace-Budget für Fine-Slots vs. Gist-Slots,
- ob der Boot-Default ~8 Token-equivalents / ~12 Gist-Slots auf Zielhardware optimal ist,
- wie Gist-Integrationsspanne mit Age/Task/Novelty geregelt wird,
- exactes Schema für cross-scale parent/child SourceLinks,
- Hysterese/Thresholds von `system_stage`, `capability_stage` und `user_stage_cap`,
- welche Stage-Aufstiege automatisch innerhalb User-Cap erlaubt sind und welche explizite Bestätigung brauchen,
- konkrete C-Bootgröße/Familie und wie viel Weltwissen C lokal tragen darf,
- C_native Max-Depth/Context-Budget vor Eskalation,
- Wake-Policy-Features und Calibration für `none|A|B|A+B`,
- interne `reasoning_effort`-Skala und User-Override-Semantik,
- welche Bodies CED/projected-context, bounded replay, shared index, block-sparse oder hybrid state+sparse Attention nativ unterstützen,
- ob ein kleiner Conditional-Associative-Memory-Head gegenüber normalem episodischem/exact Retrieval wirklich gewinnt,
- per-Body speculative-decoding support und ob native MTP/DSpark/EAGLE-artige Pfade auf Zielhardware lohnen.

Vor Code werden aktuelle Modell-/Paperoptionen erneut verifiziert.

---

# 28. Kanonischer v10.10-Satz

**v10.8 ergänzt den bisherigen Split-Brain/JEF-Canon um einen realistischen Core-first Lab-Betrieb:** In Age 0 werden zunächst JEF+A+B, Experience/Provenance und Human-gated Learning bewiesen. Neue Modalitäten kommen später über symmetrische Ingress-/Egress-Steckplätze. Jeder Ingress kann einen semantisch armen Raw/Physical-Pfad und einen starken eingefrorenen Teacher-Pfad gleichzeitig liefern; jeder Egress kann einen eigenen Self-Output und einen separat markierten Reference-Teacher-Kandidaten erzeugen. Nur V13-seitige Projectors/Adapters/Core-Gewichte lernen; Age-0-Teacher bleiben frozen. Human Decisions, Teacher-Referenzen, Self-Candidates und reale Outcomes bleiben provenance-separiert. Teacher-Removal bedeutet semantische Internalisation, nicht zwangsläufig das Verschwinden notwendiger Sensor-/Codec-/Renderer-Peripherie.**


**V13 besteht aus zwei großen direkt gekoppelten Brain-Bodies B1/Detail und B2/Gist sowie einem kleinen lernenden sprachfähigen JEF-Body an der Executive-/Action-Schnittstelle. Neue Welt-/User-Events können standardmäßig einen bounded Observer-Pass in A und B auslösen, während JEF parallel sofort handelt/denkt; die großen Bodies liefern keine Agentenantworten, sondern strukturierte Offers. JEF besitzt privaten Native-KV/State und exportiert einen kleinen versionierten JEF Broadcast Cache, den A/B über gelernte Bridges verstehen; A/B-Offers werden umgekehrt in JEF-kompatible Side-Channels projiziert. Bewusster Zugriff wird funktional nicht mit JEF allein gleichgesetzt, sondern mit einer kapazitätsbegrenzten fokalen Koalition aus ausgewählten JEF-, A-, B-, Memory-, Self- und World-Zuständen, die rekurrent global verfügbar wird. JEF entscheidet, welche Offers ignoriert, fokal aufgenommen oder durch gezielte A/B-Re-entry-Loops vertieft werden, und besitzt den einen äußeren Action-/Report-Intent; A/B dürfen Inhalte/Decoder-Spans beitragen, sprechen aber nicht als unabhängige Agenten nach außen. Jede eigene Aktion erzeugt vor dem Outcome eine Corollary Copy zurück an Brain/World/Self/JEF-Broadcast. Outcome, Evidenz, Kosten und Surprise erzeugen typisierte globale Modulatoren, die zusammen mit lokaler Eligibility und lokalen Prediction-Errors JEF, A, B und ihre Bridges lernen lassen. Age 0 startet mit hoher A/B-Observer-Coverage und starker JEF-/Scaffold-Führung; mit Reife werden Observer-Frequenz, Fokalzugriff, Re-entry, Routing, Plasticity und Autonomie gelernt und freier, ohne den einen einheitlichen Action-/Report-Stream zu verlieren.**

**v10.10 ergänzt dazu ausschließlich:** Der STEP-0→11-Bauplan bleibt vollständig bestehen; innerhalb dieser Bauphasen verarbeitet jede Experience optional einen fluiden L0→L11-Lern-Lifecycle mit Rücksprüngen, Shadow, Canary und Re-open. Redmi Note 10 Pro/6 GB ist der praktische Age-0-Labor-Floor, weshalb A/B funktional parallel, aber physisch sequenziell/asynchron/sampled laufen dürfen. Needle-3-class Tiny-Control darf als primärer Age-0-Kandidat für JEFs Language/Control-Core dienen; es ersetzt dabei nicht JEF-State, Focal Loop, A/B, Memory oder Learning Fabric und muss gegen separate-heads/tiny-LM Baselines gewinnen. Waste-Audits optimieren Implementationen, nicht den Funktionsumfang.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + C
+ B1/Detail fine-resolution + B2/Gist adaptive coarse-resolution mit Cross-scale SourceLinks
+ BodyPort capability profiles + trainierter Callosum-Bootstrap
+ adaptiver A↔B Channel-Policy mit nachgewiesener Latent-vs-Fallback-Utility und Receiver-Kalibrierung
+ echter A↔B Message-Subspace-Exchange ohne private-state collapse
+ kleiner echter JEF-Sprach-/Executive-Body mit private Native-KV/State
+ versionierter JEF_BROADCAST_CACHE + trainierte JEF↔A/B Bridges
+ A/B bounded Observer-Pass → strukturierte OFFER_PACKETs
+ FOCAL_COALITION_STATE aus ausgewählten JEF/A/B/Memory/Self/World-Slots
+ selektiver `none|A|B|A+B` Body-Wake mit gemessener Escalation-Qualität
+ automatischer Direct/Skill Path
+ gezielte Deliberation mit A/B re-entry + Halting-vs-Trajectory-Test
+ action-grounded World-JEPA mit Coverage-/Counterfactual-Confidence
+ Context/Provenance ohne History corruption
+ Fast Episodic second-attempt advantage (optional parametric trace nur nach Baseline-Gewinn)
+ lokale Eligibility + realer JEPA/EMA update + shared-pre-router Regression-Monitoring
+ Replay + Restart persistence
+ Regression protection
+ messbarer Scaffold→Imitation→Exploration→Shadow→learned-route Übergang pro Capability
+ echte Age-Stage-Rechtehülle + bindender user_stage_cap + Capability-spezifische Reife
+ adaptive Reasoning-Effort-Policy mit User-Override und fixed-effort Baselines
+ optional nutzbare native Cache-/Sparse-Attention-Capabilities nur nach Ablation
+ Event/Wake-Scheduler + unabhängiger Response Governor
+ finite Output-Garantie
```

Wenn diese Eigenschaften nicht messbar vorhanden sind, ist es ein Harness-Prototyp, aber noch kein implementiertes V13.


---

# 30. v10.10 Ausführungsinvarianten

Diese Invarianten sind für Work/Code verbindlich:

1. **Kein zentraler Pflichtpass:** Kein normaler Turn muss seriell durch alle Heads oder durch C_fast/C_focal laufen.
2. **Fast heißt wirklich fast:** C_fast-Entscheidungen dürfen nicht standardmäßig einen kompletten autoregressiven C-Decode erfordern.
3. **Die drei kognitiven Hauptträger bleiben getrennt:** B1_DETAIL, B2_GIST und C_JEF_SYSTEM bleiben klar getrennte Kompetenz-/Control-Träger; World Model, Skill Store, Memory und Teacher dürfen keine versteckten zusätzlichen Foundation-Modelle werden. C_JEF_SYSTEM ist dabei ausdrücklich kein monolithischer dritter Foundation-Body.
4. **Callosum braucht Alignment:** Latent-Injection bleibt gesperrt, bis Projector-/Cross-JEPA-Parity nachgewiesen ist.
5. **BodyPort ist capability-basiert:** fehlende Tap/Injection-Fähigkeit führt zu Fallback, nicht zu Fake-Implementation.
6. **Age ist capability-spezifisch:** kein globaler Integer darf allein Routing-/Learning-Rechte bestimmen.
7. **Scaffold ist Lehrer, nicht Gefängnis:** Age-0-Routen erzeugen Supervision für Control Learning; spätere Routen dürfen nach Messung besser werden.
8. **Eligibility bleibt sparse:** billige Micro-Traces online, reichere Traces nur selektiv.
9. **JEPA-Learner sind endlich:** Fehler werden per Credit Mapping verteilt; nicht ein Predictor pro Expert.
10. **Action Safety vor Side Effect:** Permission/Confirmation/Risk vor externer Aktion, Corollary Copy danach.
11. **Source-preserving ≠ undeletable:** Nutzerautorisierte Löschung bleibt möglich.
12. **Second-attempt ≠ cache hit:** Verbesserung muss auf transferierbarer Experience/Policy beruhen.
13. **Output bleibt unabhängig:** kein Lernen, Replay, Alignment oder Teacher-Job darf die Hard Deadline blockieren.
14. **Kompetenz wandert nach innen:** Staging Stores und Teacher dürfen helfen, aber langfristige kognitive Fähigkeit soll zunehmend in A/B/C landen.
15. **Messung vor Optimismus:** Mobile-Kompatibilität, RAM, Latenz, Trainingstiefe und Body-Swap-Parity werden gemessen, nicht behauptet.
16. **Executive State bleibt frisch:** C_fast darf nicht auf unbegrenzt stale State laufen; ein kleiner Updater/Freshness-Mechanismus ist Pflicht.
17. **Automaticity ist verteilt:** Skill Selector, C_fast, Salience und Prediction dürfen parallel konkurrieren; kein C_fast-Seriellzwang.
18. **Kommunikation ≠ Homogenisierung:** Callosum richtet Message-Subspaces aus, nicht private A/B-States; Diversity/Role-Bias wird getestet.
19. **Exact heißt source-typed:** Gemeinsame exakte Information nutzt SourceRef/Bytes/typed literals, keine fremden Token-IDs.
20. **Policy darf entdecken:** Reife Control Learning braucht sichere Exploration/Counterfactuals, nicht nur Scaffold-Imitation.
21. **Kein globaler Reward:** Update-Typen verwenden semantisch passende Modulatorvektoren.
22. **Deliberation bleibt evolvierbar:** P1/P2 ist Scaffold, nicht lebenslang einzige Denkform.
23. **Scheduler ist Infrastruktur:** Wake/Event-Scheduling darf Prioritäten bereitstellen, aber keine versteckte Intelligenz ersetzen.
24. **Governor ist hart:** Output-Deadline wird außerhalb gelernter Heads erzwungen.
25. **Control Fabric bleibt dünn:** Gesamt-RAM/Latenz/Parameter-Overhead aller Heads wird gemeinsam gemessen.
26. **Delta-first vor Base-Merge:** Neue persistente Updates werden möglichst isoliert validiert, bevor sie in geteilte Base-Weights konsolidiert werden.
27. **Multimodalität braucht einen echten Port:** Teacher-Removal ersetzt keine notwendige Sensor-/Projection-Schnittstelle.
28. **Latent muss Authority verdienen:** Kein globales „latent-first“ ohne Body-/Task-spezifische Utility gegen Fallback-Kanäle.
29. **Receiver vor Injection kalibrieren:** Norm/Scale/OOD/Residual-Gate ist Pflicht für heterogene Latent-Injection.
30. **Trajectory vor Halt optimieren:** Halting darf nicht ungeprüft die Entstehung rekurrenter Denkzustände dominieren; post-hoc/fixed-depth Baselines sind Pflicht.
31. **Sparse MoE schützt Shared Layers nicht automatisch:** Regression Shield umfasst Attention/Embeddings/Norms/Router-Input.
32. **World prediction ≠ causality:** Action-Coverage und Counterfactual Confidence bleiben explizit; Simulation ist keine Evidenz.
33. **Fast Episodic darf parametrisch sein, aber getrennt:** optionale Fast-Traces brauchen Exact Provenance, Gating, Budget, Löschbarkeit und Baseline-Gewinn.
34. **Feedback besitzt Provenance und Stärke:** interne Selbstbewertung/Dream darf stärkere grounded Evidenz nicht epistemisch überschreiben.
35. **Channel und Memory Policy dürfen verlieren:** Wenn ein moderner Mechanismus empirisch schlechter ist, bleibt der einfachere Fallback kanonisch zulässig.
36. **Multiscale ist Kern, nicht Deko:** B1/Detail und B2/Gist müssen unterschiedliche effektive Integrationsfenster besitzen; sonst fehlt eine gesetzte V13-Asymmetrie.
37. **Native Tokenizer bleiben nativ:** Fine-vs-Coarse wird nicht durch blindes Umprogrammieren fremder Tokenizer erzeugt.
38. **Gist ist adaptiv:** ~8 Token-equivalents / ~12 Slots ist Boot-Default; Boundary-/Task-/Age-Policy darf größer oder kleiner wählen.
39. **Mehrere Zeitskalen gleichzeitig:** Workspace darf Fine- und Gist-Repräsentationen derselben Quelle parallel halten und rückverlinken.
40. **Age steuert wirklich:** Stage 0–5 bestimmt harte Obergrenzen für Autonomie/Loops/Self-Edit/Tools/Plasticity; continuous trust ersetzt diese Gates nicht.
41. **User Cap ist hart:** Das System darf `user_stage_cap` nicht selbst erhöhen.
42. **Entwicklung ist reversibel:** Regression darf Stage, Capability-Rechte und Gist-Kompressionsfreiheit wieder reduzieren.
43. **JEF ist kein einzelnes Sprachmodell:** C2/Needle-class strukturiert Control; C3 bleibt als separates Tiny-Language-Organ, bis Ablation zeigt, dass C2 kurze freie Sprache zuverlässig übernehmen kann. JEF_SYSTEM umfasst State, Control, Focal Loop, Action/Report und Learning-Interfaces.
44. **B1/B2-Wake ist selektiv:** triviale Tasks brauchen keinen symbolischen B1+B2-Pflichtpass; Bootstrap sichert Coverage über Shadow/Calibration statt Zwang pro Turn.
45. **Fast/slow ist Regime, nicht Anatomie:** Automaticity und Deliberation sind dynamische Aktivitätsmuster gekoppelter Loops; kein "System-1-Modell" plus "System-2-Modell" bauen.
46. **Reasoning effort ist graphweit:** Effort steuert C-Tiefe, Body-Wake, Re-entry, Verify, Retrieval und Tool/World-Schritte, nicht nur Antwortlänge.
47. **Cache-Innovation bleibt nativ:** CED, bounded replay, CSA/IndexPool/MSA/hybrid attention werden nur genutzt, wenn Body/Runner sie real unterstützt.
48. **Serving ≠ cognition:** MTP/DSpark/EAGLE-artige Spec-Decoding-Pfade beschleunigen Decoding, werden aber nicht als Denk- oder Evidenzmechanismus behandelt.
49. **Conditional parameter memory ≠ Provenance:** assoziative/Engram-artige Lookups dürfen helfen, sind aber nie Exact Evidence.
50. **JEF ist Executive-System, Conscious Access ist Koalition:** ein kleines LM/Control-Organ kann wichtiger Executive/Report-Knoten sein, ist aber weder JEF allein noch alleiniger Ort des bewussten Zustands.
51. **Observer ≠ Agent:** A/B dürfen standardmäßig je einen bounded State-Pass bekommen, liefern aber Offers statt Chatantworten.
52. **Private KV, public broadcast:** rohe JEF-KV bleibt body-spezifisch; A/B lernen einen stabilen JEF Broadcast Cache via Bridges.
53. **JEF need not wait:** sichere Direct/JEF-native Antwort darf vor A/B-Observer-Ende fertig werden; saliente spätere Offers können sie vor Commit invalidieren.
54. **One external stream:** JEF/Action Broker hält einen Report-/Action-Intent; A/B dürfen Content beitragen, aber keine unabhängigen Außenagenten sein.
55. **Action copy before outcome:** jede relevante eigene Aktion wird als Corollary Copy an Brain/Self/World verteilt.
56. **Shared valuation, local credit:** Outcome-Modulatoren sind geteilt; Eligibility/Predictor-Fehler bleiben lokal.

---

50. **Cognitive Core ≠ gesamte Sensorik:** B1/B2/JEF tragen zentrale Bedeutung/Control; ModalityPorts dürfen dauerhaft gelernte Repräsentation/Rendering besitzen.
51. **Input und Output getrennt:** Vision-Encoder ≠ Bildgenerator; Audio-Encoder ≠ Speech-Decoder.
52. **Teacher ≠ Port:** Teacher kann verschwinden; notwendiger Sensor-/Effector-Codec darf bleiben.
53. **Reconstruction ≠ meaning:** Rekonstruktion schützt Information, Semantik braucht Cross-modal/Outcome/Teacher-Grounding.
54. **Live hat eine Zeitachse:** Streaming Events besitzen provisional/final Status und dürfen Output/Deep Work überlappen.
55. **JEF lernt anders:** JEF-Updates priorisieren Control/Goal/Action/Report; A/B priorisieren repräsentative/predictive Gist/Detail-Ziele.
56. **Stepwise before omni:** Text Core → Split Brain → JEF Learning → Callosum → Core Learning → Vision → Audio/Speech → Full Duplex → Teacher Internalisation.

50. **Core first:** Keine neue Modalität darf einen instabilen text-only JEF/A/B-Lernloop verstecken.
51. **Teacher frozen in Age 0:** Externe Encoder/Decoder/LLMs/APIs liefern Targets/Referenzen, werden aber von V13 nicht online verändert.
52. **Self before teacher:** Für Distillation/Preference entsteht die Student-Prediction vor Teacher-Exposure.
53. **Reference lane:** Teacher-Ausgabe bleibt getrennte Provenance und wird nie still zur eigenen Erinnerung.
54. **Human feedback is typed:** factual correction, preference, style, route und learning permission sind getrennte Felder.
55. **Two-path sensory boot:** neue Modalitäten dürfen gleichzeitig Raw/Minimal und Semantic-Teacher Views derselben Source liefern.
56. **Internalise semantics, not physics:** starker Teacher soll entfernbar werden; notwendige Codecs/Renderer dürfen Körperperipherie bleiben.
57. **Age-0 is long-lived:** höhere Ages sind kein Build-Ziel, bevor Record/Shadow/Commit, Retention und Rollback über reale Nutzung stabil sind.

50. **Additive-only by default:** neue Research-Ideen werden angehängt und abliert, nicht still als Ersatz gesetzt.
51. **Build Steps bleiben:** STEP 0–11 sind Implementierungsreihenfolge; fluides Lernen liegt innerhalb/quer dazu.
52. **Lifecycle ≠ Age:** L0–L11 beschreibt Experience-Verarbeitung, Age 0–5 Entwicklungsrechte.
53. **Redmi-Floor verändert Scheduling, nicht Kognition:** sequenzielles A/B ist Deployment, kein Verlust der Split-Brain-Rolle.
54. **Needle ist optional:** möglicher JEF-Language-Control-Core/Teacher/Prototype, kein vierter Body und kein Ersatz für das gesamte JEF-System.
55. **Observer policy bleibt editierbar:** ALWAYS/ASYNC/SAMPLED/ON-DEMAND dürfen im Labor verglichen werden.
56. **Waste Audit bewahrt Fähigkeiten:** nur Implementation austauschen, wenn Funktionsparität + Regressionstest bestehen.


---

# 31. Research-Hardened Kernexperimente vor großem Ausbau

Diese Experimente sind **Architekturfragen**, keine späteren Optimierungsdetails. Ein negatives Resultat darf einzelne optionale v10.5-Mechanismen entfernen oder vereinfachen, aber LOCKED-Ziele bleiben nur per Nutzerentscheidung änderbar.

## R0 — Locked Split-Brain Role Test: ist die gewählte Körperpaarung wirklich Gist/Detail-komplementär?

Die **Zwei-Hemisphären-Architektur selbst ist LOCKED**. R0 entscheidet nicht, ob V13 auf einen Body reduziert wird, sondern ob die gewählten Boot-Modelle die gesetzten Rollen gut erfüllen oder ersetzt werden müssen.

### Hypothese

Ein Detail-Body mit kurzen/Fine-Readouts und ein Gist-Body mit längeren/adaptiv gruppierten Readouts liefern zusammen bessere lokale+globale Abdeckung als zwei gleichartig konfigurierte Bodies.

### Vergleich

```text
A Detail alone
B Gist alone
A+B same-resolution control
A fine + B fixed coarse
A fine + B adaptive boundary-aware coarse
```

### Messen

- unique wins Detail,
- unique wins Gist,
- correlated vs complementary errors,
- exact-local tasks,
- discourse/global tasks,
- mixed tasks requiring both,
- cross-scale contradiction detection,
- compute/latency,
- role diversity over continual learning.

### Entscheidung

Wenn ein konkretes Modellpaar nicht komplementär ist, wird **das Modellpaar oder seine Role-Adapters ersetzt**, nicht die Split-Brain-Grundidee. Die Auflösungsasymmetrie bleibt Canon.

## R1 — Heterogeneous Communication: bringt Latent wirklich etwas?

### Hypothese
Ein trainierter Message-Subspace kann bei ausgewählten Tasks mehr Information pro Zeit/Byte übertragen als reine Source-/Symbolic-Kommunikation, ohne A/B zu homogenisieren.

### Vergleich

```text
NO_MESSAGE
CONTROL metadata
SOURCE/EXACT spans
BOUNDED SYMBOLIC
LATENT projector
adaptive MIXTURE
```

### Messen

- Task quality / exactness,
- end-to-end latency,
- communication bytes,
- extra receiver compute,
- private-state diversity,
- calibration before/after injection,
- OOD robustness,
- role specialization retention.

### Entscheidung
Wenn Latent keinen stabilen Pareto-Gewinn zeigt, bleibt V13 ein direkt gekoppeltes Split-Brain-System, aber der primäre Kommunikationskanal darf Source/Symbolic sein. **Die Identität des Projekts hängt nicht an Latent-Dogma.**

## R2 — Continual Learning in sparse Bodies: wo entsteht Forgetting?

### Hypothese
Sparse Eligibility + delta-first Updates reduzieren Interferenz, aber Shared Attention/Router-Input können trotzdem Hauptquelle des Vergessens sein.

### Ablationen

```text
heads/projectors only
experts only
router only
shared attention only
adapter slices
mixed validated delta
```

### Messen

- new-skill acquisition,
- backward transfer / retention,
- shared-layer representation drift,
- router-input collision,
- expert specialization,
- calibration,
- rollback cost.

### Entscheidung
Der erste Full-Weight-Learning-Scope wird aus diesen Daten abgeleitet. Kein Teil der Base-Weights erhält nur deshalb Online-Autorität, weil er theoretisch „lernbar“ ist.

## R3 — Executive Policy Learning: lernt JEF_FAST_POLICY bessere Selbststeuerung?

### Hypothese
Scaffold → imitation → shadow exploration → grounded outcome kann eine kleine Control Policy erzeugen, die bei Routine weniger Compute verbraucht und bei Novelty zuverlässig Deliberation reaktiviert.

### Vergleich

```text
fixed scaffold
imitation only
imitation + contextual bandit/exploration
imitation + counterfactual replay
learned policy + rollback
```

### Messen

- quality,
- cost/latency,
- C_focal wake rate,
- false automation,
- missed salience,
- policy calibration,
- route diversity,
- long-run local-habit lock-in,
- recovery after distribution shift.

### Entscheidung
Eine learned route gewinnt nur Authority, wenn sie nicht nur im Mittel billiger ist, sondern Novelty/Failure weiterhin korrekt eskaliert.

## R4 — C-native vs. Large-Body Wake: kann der kleine Executive wirklich Kosten sparen ohne Qualität zu verstecken?

### Hypothese
Ein kleines sprachfähiges C kann viele einfache/local-grounded Aufgaben selbst lösen und große Bodies nur bei Bedarf wecken.

### Vergleich

```text
always A+B
C_native only
heuristic selective wake
learned calibrated wake
```

### Messen
- quality/exactness,
- unsupported factual claims,
- wake rate A/B,
- escalation recall auf schwierigen Fällen,
- latency/energy,
- user correction rate,
- failure under distribution shift.

### Entscheidung
C-native erhält breite Authority nur dort, wo es einfache Fälle zuverlässig abdeckt **und** schwierige/ungewisse Fälle korrekt eskaliert.

## R5 — Reasoning Effort: adaptive Tiefe statt fixer zwei Modi

### Hypothese
Eine adaptive Effort-Policy schlägt fixe Low-/Max-Policies im Quality/Cost-Pareto, ohne Hard Cases systematisch zu unterdenken.

### Vergleich

```text
fixed low
fixed high
fixed max
adaptive continuous
user-forced high/max
```

### Entscheidung
Adaptive Effort wird nur Canon-Default, wenn Hard-Task-Recall, Calibration und Latency gemeinsam gewinnen. Sonst bleibt eine konservative Scaffold-Policy.

## R6 — Native Cache/Attention Mechanisms: welche moderne Technik hilft V13 wirklich?

### Kandidaten

```text
DeepSeek-like projected global context / bounded replay / shared index
MiniMax-like block sparse index→attention
GLM-like compact-state + sparse-global / pooled index
standard full/native body baseline
```

### Messen
- long-context quality,
- exact restore,
- KV/state bytes,
- bandwidth/page faults,
- prefill/decode latency,
- energy/thermal,
- complexity/failure recovery.

### Entscheidung
Jede Technik gewinnt **einzeln** oder bleibt aus. Keine Modellarchitektur wird als Paket cargo-culted.

---

## R7 — Fluid Learning Lifecycle

Welche Experience-Typen sollten wie weit durch L0–L11 laufen? Ziel ist minimale unnötige Plasticity bei maximalem Second-Attempt-Gewinn. Verglichen werden feste Pipeline, adaptive Gates, Human-gated und capability-spezifische Policies.

## R8 — Redmi Scheduling ohne Architekturverlust

Vergleich von simultaneous, sequential, JEF-first/deferred und sampled A/B Observer Scheduling. Die kognitive Semantik bleibt identisch; gemessen werden RAM, Latenz, Thermik, Offer-Utility und Lernqualität.

## R9 — Needle-class JEF-Language-Control Candidate vs vorhandene JEF-fast-Fabric

Needle 3 wird als **integrierter JEF-Language/Control-Core-Kandidat** gegen zwei Baselines gemessen: (A) separates Tiny-Sprachmodell + separate Fast-Heads und (B) Needle nur als Parser bei separater JEF-fast-Fabric. Gemessen werden Routing, Extraction, Embedding, Tool grammar, RSS, Latenz, A/B-Wake-Qualität, Packet-Validity und nach Fine-Tuning neu kalibrierte Confidence. Gewinnt Needle mehrere Funktionen gemeinsam, dürfen diese im selben JEF-Organ gebündelt bleiben; die abstrakten JEF-Funktionen bleiben dennoch getrennt spezifiziert.

---

# 31H. Research-Source-Hygiene

## IH-H31 — Research Source Hygiene [MUST for docs, not architecture]

Gefundener konkreter Tippfehler:

```text
https://arcxiv.org/abs/2609.05075
```

muss zu `arxiv.org` korrigiert werden.

Research-Claims bekommen optional:

```text
source_id
access_date
claim_scope
verified/current|historical|hypothesis
```

Ein Linkfehler darf nie einen Mechanismus als „implementiert“ erscheinen lassen.

---

# 32. Forschungsbasis v10.10 — Stand 20.09.2026

Diese Arbeiten **inspirieren oder begrenzen** v10.7; keine einzelne davon beweist V13 als Gesamtarchitektur.

1. **Dual-Cache Latent Space Communication between Heterogeneous Language Models** — arXiv:2608.20617. Zeigt trainierbare Cache-/Latent-Übersetzung zwischen heterogenen LMs und motiviert Receiver-spezifische Translation; ist kein Beweis, dass Latent für jedes Body-Paar besser als Text/Source ist.
2. **Latent Recurrent Thoughts: Recurrent Refinement of Proposed Latents for Reasoning with Frozen LLMs** — arXiv:2609.01117. Unterstützt die Machbarkeit kleiner rekurrenter Latent-Reasoner vor einem großen Decoder.
3. **Retrofitting Recurrent Depth into a Pretrained Language Model** — arXiv:2608.11233. Unterstützt nachrüstbare recurrent depth, zeigt aber auch Interferenz-/Retention-Grenzen.
4. **Adaptive Depth in Looped Transformers: Diagnosing Learned Halting Gates and Trajectory Readouts** — arXiv:2607.20519. Motiviert die Trennung von Trajectory Formation und Exit/Halting Readout.
5. **Multi-Head Attention as a Source of Catastrophic Forgetting in MoE Transformers** — arXiv:2602.12587. Motiviert Regression-Monitoring vor dem Router und nicht nur Expert-/Router-Schutz.
6. **Toward Physically Grounded JEPA World Models for Goal-Conditioned Robotic Planning** — arXiv:2609.03565. Motiviert inverse dynamics und state alignment zusätzlich zu latent prediction.
7. **A complementary learning system for continual episodic memory in large language models** — bioRxiv DOI 10.64898/2026.08.24.746712. Liefert einen konkreten Fast-Episode→gated sparse trace→Replay/Consolidation-Kandidaten, bleibt aber ein spezifisches experimentelles Design und keine Pflichtarchitektur.
8. **Chain-of-Experience for Continual LLM Improvement** — arXiv:2608.18027. Unterstützt Experience-/Feedback-Loops; V13 trennt jedoch grounded Outcomes von schwächerer Self-Evaluation und hält Wissenslernen latent-/provenance-first.
9. **NeoHorse-1: Towards Recursive Self-Improvement via Agentic Post-Training with Routing Harness** — arXiv:2609.08183. Unterstützt den Systemloop Routing→Experience→Evaluation→Training Selection→Update, ohne V13s interne Lernziele festzulegen.
10. **Neural populations in the language network differ in the size of their temporal receptive windows** — Nature Human Behaviour 2024. Findet interleavte Sprachpopulationen mit ungefähr 1-, 4- und 6-Wort-Integrationsfenstern; motiviert mehrere parallele Zeitskalen statt nur eines Kontextfensters.
11. **Conversational content is organized across multiple timescales in the brain** — Nature Human Behaviour 2025. Zeigt hierarchische Sprachrepräsentationen über Wörter/Sätze bis längere Gesprächskontexte und unterstützt V13s Fine/Gist-Kopplung.
12. **Temporal structure of natural language processing in the human brain corresponds to layered hierarchy of large language models** — Nature Communications 2025/Correction 2026. Verknüpft hierarchische Modellrepräsentationen mit zeitlich unterschiedlichen Integrationsdynamiken im Gehirn.
13. **Hierarchical linguistic predictions and cross-level information updating during narrative comprehension** — Communications Biology 2025. Berichtet Wort-/Satz-Level-Prediction und Evidenz für sparse Updates höherer Ebenen an Grenzen; motiviert boundary-aware Gist-Updates.
14. **Neural timescales from a computational perspective** — Nature Neuroscience 2026. Review zu funktionell diversen neuronalen Zeitskalen innerhalb und zwischen Arealen; stützt das Multiscale-Prinzip, nicht eine wörtliche biologische Zwei-Hemisphären-Zuordnung.
15. **Understanding how experience supports the development of executive function skills** — Nature Reviews Psychology 2026. Unterstützt erfahrungsabhängige Entwicklung von Executive Function und damit V13s Scaffold→Self-Regulation-Idee.
16. **Developmental benchmarks of executive function reveal sensitive periods for adolescent mental health** — Nature Mental Health 2026. Zeigt unterschiedliche Reifungsverläufe von Inhibitory Control und Working Memory; motiviert globale Development-Stage plus capability-spezifische Reife statt eines einzigen linearen Alters.
17. **Byte Latent Transformer: Patches Scale Better Than Tokens** — arXiv:2412.09871. Zeigt dynamisch große Patches als effiziente Hierarchie in speziell dafür trainierten Modellen; V13 übernimmt daraus nur das Prinzip adaptiver Gruppierung und patcht keine fremden pretrained Tokenizer.
18. **Adaptive Targeted Dynamic Chunking for Tokenization-Free Hierarchical Model** — arXiv:2605.30080 und **Dynamic Multi-Byte Prediction With Hierarchical Language Models** — arXiv:2608.15454. Unterstützen lernbare/variable Chunk-Größe in dafür vorgesehenen Architekturen; dienen als Kandidaten für spätere native Gist-Bodies, nicht als Zwang für aktuelle Token-LLMs.
19. **DeepSeek-V4.1-Flash Technical Report / Model Card** — DeepSeek, 10.09.2026. Causal Encoder–Decoder, projected decoder global KV, SWA Bounded Replay, CSA2 mit Full/Reindex/Reuse und hierarchischem Sparse Indexer, FP4 main KV, Engram conditional memory, DSpark und kontinuierlicher Reasoning-Effort. V13 übernimmt nur einzeln messbare Prinzipien; V4.1 selbst ist viel zu groß für den Phone-Body.
20. **DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation** — arXiv:2607.05147. Motiviert confidence-/load-adaptive Draft-Verifikation als Serving-Optimierung; nicht als Cognition-Mechanismus.
21. **MiniMax Sparse Attention** — arXiv:2606.13392 und **MiniMax M3** Model Card. Blockweise GQA-spezifische Index-Auswahl mit getrenntem Index/Main-Branch; M3 bietet `thinking=disabled|adaptive|enabled`. Motiviert Body-native sparse Context-Auswahl und V13s adaptive Effort/Wake-Policy.
22. **GLM-5.3-Flash** Model Card / Z.ai 2026. Kombiniert sparse und linear/state-artige Attention, mHC, Index-Pooling/Long-Context-Optimierung und `reasoning_effort=low|high|max`; motiviert hybride lokale State + globale Sparse-Retrieval-Bodies sowie mehrstufige Effort-Steuerung.
23. **Neural dynamics of cognitive control: Current tensions and future promise** — Neuroscience & Biobehavioral Reviews 2026. Betont dynamische Feedback-Loops über verteilte Hirnregionen; unterstützt C als wichtigen Executive-Knoten, nicht als alleinigen Master-Controller.
24. **Interacting cortico-basal ganglia-thalamocortical loops shape behavioral control through cognitive maps and shortcuts** — Trends in Neurosciences 2025. Beschreibt Goal-directed und habitual control als interagierende Schleifen mit shortcut-artiger Automaticity statt streng separater Systeme.
25. **Defining deliberation for dual-process models of reasoning** — Nature Reviews Psychology 2025 sowie neuere Conflict-trigger-Arbeit 2026. Unterstützt eine funktionale Fast-vs-Deliberative-Unterscheidung, warnt aber vor naiver anatomischer Zwei-System-Lesart; Konflikt kann Deliberation rekrutieren.

26. **Gemma 4 model family / 12B Unified (Google, 2026).** E2B/E4B nutzen dedizierte Vision-/Audio-Encoder, während 12B Unified raw image/audio über leichte Projektionen direkt in einen decoder-only Backbone einspeist. Das stützt V13s Entwicklungsweg „Scaffold/Port zuerst, stärkere Internalisation später“.
27. **Gemma 3n.** MobileNet-V5 Vision Encoder, Audio-Input, PLE caching, MatFormer und conditional modality parameter loading sind direkte Beispiele für mobile selektive Peripherie.
28. **GPT-Live (OpenAI, 2026).** Full-duplex live path hält Sprache am Laufen, während tiefere Reasoning-/Tool-Arbeit asynchron an stärkere Modelle delegiert wird; außerdem provisional vs authoritative conversation state und stateful context handoff. V13 übernimmt dieses Systemprinzip, nicht proprietäre Gewichte.
29. **Gemini 3.8 Live (Google, 2026).** Native Audio/Video-Live-Interaktion, interleaved reasoning und asynchrone Function Calls zeigen denselben Grundsatz: Interaktion darf auf Background-Reasoning/Tools nicht blockieren.
30. **MiniCPM-o 4.5 (OpenBMB, 2026).** Open 9B Omni-Modell mit SigLIP2/Whisper/CosyVoice2/Qwen3-8B, dicht über Hidden States gekoppelt; Omni-Flow synchronisiert Input/Output-Streams auf gemeinsamer Zeitachse. Zu groß für Boot, aber starkes Referenzdesign für spätere Port-Integration.
31. **Qwen3-Omni (Alibaba, open Apache 2.0).** Thinker–Talker plus multi-codebook Speech Decoder unterstützt die Trennung kognitiver Verarbeitung und Speech-Effector.
32. **TypeSafe Jev (2026).** Closed API, text-only, keine offenen Gewichte und kein freier Textdecoder; passt konzeptionell zu JEF_FAST_POLICY/typed decision heads, aber **nicht** als vollständiger JEF. Die oft erinnerte ~55-MB-Zahl konnte für Jev nicht verifiziert werden.
33. **Succinct Router 14M (2026).** Öffentliches spezialisiertes Routing-Modell; float32 ca. 55 MB und lokal ~26 ms laut Autor. Sehr passender Prototyp für einen JEF-Wake/Route-Head, aber zu eng für den ganzen JEF.
34. **FunctionGemma 270M (Google).** Offenes kleines function-calling LM, ausdrücklich als lokaler Agent-Bridge-Baustein gedacht und feinabstimmbar; Kandidat für JEF-Experimente, aber nicht als fertiger Dialog-JEF gedacht.
35. **MOSS-TTS-Nano 100M (2026).** Kleiner offener CPU-fähiger Speech-Generator; Beispiel dafür, dass der Speech-Effector separat sehr klein sein kann.

### v10.10-Korrekturregel

> Frühere gesetzte V13-Mechanismen dürfen durch "Research-Hardening" nicht still verschwinden. Research darf sie präzisieren, falsifizierbar machen oder technisch anders umsetzen, aber ein LOCKED-Ziel wie Fine-vs-Gist-Auflösung oder entwicklungsabhängige Age-Control wird nur nach expliziter Nutzerentscheidung entfernt.

### v10.12 Architekturhinweise aus aktuellen Referenzen

- **Gemma 4 12B Unified** ist ein nützlicher späterer Referenzpunkt für A-Plane-Internalisierung: Google entfernt bei diesem Modell schwere Vision-/Audio-Encoder und projiziert rohe Bildpatches/Audiowellen über leichte lineare Schichten direkt in den Decoder-Backbone. Die kleineren Gemma-4-Varianten verwenden dagegen weiterhin dedizierte Vision-/Audio-Encoder. Das stützt V13s Idee `Teacher/Heavy Encoder früh → leichter Student-Port später`, ohne zu behaupten, ein Redmi-Modell könne das von Tag 1.
- **T5Gemma 2 270M-270M** zeigt, dass kleine explizite Encoder/Decoder-Paare weiterhin sinnvoll sind; das 270M-270M-Modell ist multimodal und encodiert Bilder zu 256 Tokens, ist aber als ~1.57-GB-Datei eher Lab-/Teacher-Referenz als dauerresidenter Redmi-Baustein.
- **Needle 3** ist wegen strukturierter Sprache/Tools/Embedding/Confidence und 9–35-MB-Binaries besonders passend für C2, aber die Entwickler tauschen General Chat bewusst gegen Automation-Qualität. Genau deshalb wird ein separates C3-Language-Organ zunächst nicht gestrichen.
- **SmolLM2-135M-Instruct** ist eine einfache offene C3-Baseline, nicht das Zielmodell; die Model Card nennt Englisch als Primärsprache und weist auf begrenzte Fakt-/Logikqualität hin.

Research-Regel:

> **Aktuelle Paper sind Evidenz für Teilmechanismen, nicht Lizenzen zum Cargo-Culting. Ein Mechanismus wird kanonisch aktiv, wenn er in V13s eigener Ablation gegen einfachere Baselines gewinnt.**

---

# 33. v10.12 Needle/JEF Integrationsentscheidung

## 33.1 Was jetzt gesetzt ist

- JEF ist **ein System**, kein LLM.
- JEF braucht eine sprachliche/semantische Schnittstelle, aber diese darf klein und stark spezialisiert sein.
- Needle 3 passt konzeptionell auffällig gut auf genau diese Schnittstelle, weil es Sprache in strukturierte Aktionen/Extraktionen/Embeddings überführt und Confidence/Escalation anbietet.
- Rich free-form language bleibt separat lösbar; sie definiert JEF nicht.
- Needle darf mehrere JEF-fast-Funktionen bündeln, wenn das auf Redmi RAM/Latenz spart.

## 33.2 Was noch experimentell ist

1. Reicht Needle als User-Sprache→EXEC_PACKET-Interpreter für echte Dialoge?
2. Wie viel Context/Conversation Continuity behält es sinnvoll, bevor expliziter JEF-State überlegen ist?
3. Welche Ladder-Stufe ist auf Snapdragon 732G der beste Punkt?
4. Brauchen wir zusätzlich einen 100–300M Report-Decoder oder reichen A/B/Reference-Teacher zunächst?
5. Können wir die offene JAX-Architektur um stabile Hidden-Taps ergänzen, ohne den mobilen Engine-Pfad zu verlieren?
6. Wie rekalibrieren wir Confidence nach JEF-spezifischem Fine-Tuning?
7. Ist Needles eingebautes Tool-Retrieval besser als V13 Memory/Tool-Retrieval oder nur eine günstige erste Stufe?

## 33.3 Redmi-first Minimalexperiment

```text
User text
  ↓
Needle/JEF-Language-Control-Core
  ↓
EXEC_PACKET + embedding + tool/action candidate + confidence
  ↓
explicit JEF_STATE
  ├─→ Direct / Tool
  ├─→ A observer/query
  ├─→ B observer/query
  └─→ A+B / focal loop
  ↓
JEF report/action intent
  ↓
Direct / A-B assisted / temporary report decoder
```

Zuerst **ohne** Needle-Fine-Tuning. Danach Human-labelled Packet-Targets sammeln, Shadow-LoRA extern trainieren, auf dem Redmi nur Inference/Canary testen. So lernen wir, ob Needle wirklich das richtige JEF-Sprachorgan ist, bevor wir die Architektur darum verhärten.



---

# 30. v10.14 TRIPLE PASS — WARUM DIESE ERGÄNZUNG EXISTIERT

v10.14 ersetzt **keinen** Mechanismus aus v10.13. Es ist ein additiver Forschungs-Vorbereitungs-Pass mit drei gleichzeitig gültigen Sichtweisen:

```text
PASS I   = COMPLETE STACK AUDIT
           Was existiert, wo sitzt es, wer kommuniziert womit?

PASS II  = OUT-OF-THE-BOX RESEARCH CHARTER
           Welche Funktion ist fest, welche konkrete Mechanik darf radikal anders werden?

PASS III = BRAIN-NEAR DESIGN DOCTRINE
           Welche Organisationsprinzipien sollen V13 hirnnah machen,
           ohne anatomische Cargo-Cult-Kopie?
```

Die drei Pässe dürfen sich **nicht gegenseitig überschreiben**. PASS I verhindert Vergessen, PASS II verhindert Verkrampfung, PASS III verhindert, dass V13 trotz Gehirnbegriffen zu einem normalen Software-Router mit drei Modellen schrumpft.

## 30.1 [LOCKED] Canon = Funktionsvertrag, nicht Implementierungsgefängnis

Ab jetzt wird zwischen zwei Ebenen unterschieden:

```text
FUNCTIONAL CANON
= welche Fähigkeiten/Interaktionen V13 besitzen soll

IMPLEMENTATION HYPOTHESIS
= wie diese Funktion konkret realisiert wird
```

Beispiel:

```text
[LOCKED FUNCTION]
B1 und B2 müssen komplementär kommunizieren und gemeinsam besser werden.

[RESEARCH IMPLEMENTATIONS]
- gated cross-attention
- message tokens
- recurrent adapters
- projected KV / state translation
- shared predictive message state
- sparse latent mailbox
- source/exact fallback
- Kombination davon
```

Eine neue Technik darf eine Implementation ersetzen, **nicht still die Funktion**.

---

# 31. PASS I — COMPLETE STACK AUDIT

## 31.1 Anatomischer Stack

```text
WORLD / HUMAN / BODY
        ↕
┌────────────────────────────────────────────────────────────┐
│ A-PLANE — PERCEPTION / INGRESS                            │
│ A0 Raw/Physical Transducer                                │
│ A1 Segmentation / Patching / Event Boundaries             │
│ A2 Frozen Semantic Teacher Lane [optional Age-0 scaffold] │
│ A3 Learnable Student Perceptor / Projector                │
│ A4 Perceptual Attention / Active-look proposal            │
│ A5 PerceptPacket + Source / Time / Event binding          │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
┌────────────────────────────────────────────────────────────┐
│ B-PLANE — SPLIT-BRAIN COGNITIVE CORE                      │
│ B1 Detail / Fine body                                     │
│ B2 Gist / Coarse body                                     │
│ B3 Callosum / cross-scale communication                   │
│ B4 Distributed multi-slot active state / workspace        │
│ B5 Interfaces to Memory / World / Self / Inquisition      │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
┌────────────────────────────────────────────────────────────┐
│ C-PLANE — JEF SYSTEM                                      │
│ C0 Shell / permissions / JEF contract                     │
│ C1 Executive continuity state + private organ state       │
│ C2 Structured control/language organ                      │
│ C3 Tiny free-language/report organ                        │
│ C4 Focal-coalition interface / deliberate recurrent loop  │
│ C5 Action/report intent interface                         │
│ C6 Egress / effector port manager                         │
│ C7 Text/Speech/Image/UI/Tool/Motor effectors              │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
WORLD / HUMAN / BODY
```

### 31.1.1 [CORRECTION] C5 ist nicht das komplette Action Gate

Der ältere Canon trennte Action Selection bewusst vom Judge/JEF. Diese Trennung bleibt erhalten.

```text
C5
= JEF action/report INTENT interface

ACTION GATE FABRIC
= konkurrenz-/permission-/cost-/risk-sensitive Auswahl,
  welche mentale oder externe Aktion tatsächlich Authority erhält
```

Dadurch gilt weiterhin:

```text
JEF proposes / biases / maintains intent
        ↓
Action Gate competes / selects / sequences
        ↓
Fast Forward predicts immediate consequence
        ↓
Safety / permission / reversibility
        ↓
Corollary Copy
        ↓
Execution
```

JEF ist wichtig, aber nicht der alleinige Scheduler jedes internen oder externen Aktes.

## 31.2 Querliegende Fabrics

Diese Systeme sind **keine zusätzliche lineare D-Plane**:

```text
F1  Attention / Gain / Admission
F2  Salience / Interrupt / Reflex
F3  Memory / Context / Provenance
F4  Self / Body / World Prediction
F5  Action Selection / Safety / Corollary
F6  Learning / Eligibility / Prediction / Modulation
F7  Metaplasticity / Homeostasis / Stability
F8  Age / Human Control / Rules / Permissions
F9  Replay / Counterfactual / Dream / Consolidation
F10 Runtime / Cache / Scheduling / Response Governor
F11 Metrics / Calibration / Hallucination / Retention Audit
```

Jede Fabric darf A, B und C gleichzeitig beeinflussen.

## 31.3 Realtime-Aktivitätsausbreitung

Ein normaler Event kann ungefähr so laufen:

```text
EVENT
  ↓
A0/A1 Source + Event binding
  ├──────────────→ C1 immediate executive update
  ↓
A3/A4/A5 percept state
  ├──────────────→ B1 bounded observer
  └──────────────→ B2 bounded observer
                       ↓
               B1/B2 OFFERS
                       ↓
         Gain / Salience / Goals / Memory cues
                       ↓
               FOCAL COALITION [optional]
           ↙        ↓        ↓        ↘
         B1        B2       JEF     Memory/World/Self
           ↖        ↕        ↕        ↗
                  recurrent
                       ↓
                Action/Report Intent
                       ↓
                  Action Gate
                       ↓
                  Fast Forward
                       ↓
             Safety / Permission Gate
                       ↓
                 Corollary Copy
                 ↙            ↘
            internal           WORLD
                                  ↓
                               outcome
                                  ↓
                   prediction + modulation
                                  ↓
                           learning graph
```

Kein Pfeil impliziert, dass der Pfad in jedem Event aktiviert oder trainiert wird.

## 31.4 Cheap paths bleiben echte Pfade

```text
Exact/Copy task
→ A/source binding → Direct Renderer → Gate

Simple social task
→ C1/C2/C3 → Report Intent → Gate

Fine exact task
→ B1 → JEF integration → output

Global relational task
→ B2 → JEF integration → output

Hard/conflicted task
→ B1+B2+Memory/World ↔ Focal Coalition ↔ JEF
```

Das Ziel ist adaptive Aktivierung, nicht maximales Aktivieren.

---

# 32. PASS I — KOMMUNIKATIONSLAYER

## 32.1 Drei primäre Bridge-Familien

```text
P-BRAIN   A → B/C
          perception-to-cognition

BRAIN-BRAIN
          B1 ↔ B2 via B3 Callosum

EXEC-BRAIN
          C/JEF ↔ B1/B2
```

Jede Bridge wird getrennt beschrieben durch:

```text
PathSpec {
    path_id
    source
    receiver
    read_gain
    write_gain
    authority
    bandwidth
    latency_budget
    energy_budget
    message_type_mix
    source_ref_requirement
    exact_fallback

    learn_gain
    eligibility_decay
    plasticity_cap
    teacher_gain
    human_gain
    replay_priority
    consolidation_threshold
    confidence_threshold
    rollback_threshold

    age_min
    capability_stage_min
    permission_mask
}
```

## 32.2 [LOCKED] Kommunikation ist nicht Lernen

Vier getrennte Zustände müssen möglich sein:

```text
communicate = NO,  learn = NO
communicate = YES, learn = NO
communicate = YES, learn = SHADOW
communicate = YES, learn = ACTIVE
```

Ein B1-Offer darf JEF helfen, ohne dass B1, Bridge oder JEF in diesem Event persistente Gewichtsänderungen erhalten.

## 32.3 Message-/Offer-/Query-Typen

Mindestens:

```text
PERCEPT_PACKET
B1_OFFER
B2_OFFER
CALLOSUM_MESSAGE
JEF_BROADCAST
JEF_QUERY
MEMORY_CUE
WORLD_PREDICTION
ACTION_INTENT
COROLLARY_COPY
OUTCOME_PACKET
HUMAN_DECISION_PACKET
TEACHER_REFERENCE_PACKET
```

Jedes Paket braucht `event_id`, `source/provenance`, `state_version` und ggf. `exact_fallback_ref`.

---

# 33. PASS I — LOKALE LERNSCHLEIFEN

## 33.1 A-Plane

```text
A1 boundary policy
    ↺ boundary usefulness / source recovery / later task utility

A3 student perceptor
    ↺ raw↔teacher alignment
    ↺ raw↔cross-modal alignment
    ↺ reconstruction/information preservation
    ↺ downstream B/JEF usefulness
    ↺ real-world outcome later

A4 perceptual attention
    ↺ did selected region/time actually help?
    ↺ did re-look request recover missed evidence?
```

A2 Teacher bleibt im Age-0-Lab frozen.

## 33.2 B1 Detail

Mögliche lokale Targets:

```text
fine-state prediction
exact/source reconstruction
local contradiction detection
fine-to-next-event prediction
detail-offer usefulness
coarse→fine request satisfaction
```

Parametergruppe:

```text
B1.detail_gain
B1.literal_gain
B1.exact_request_threshold
B1.local_pred_weight
B1.offer_threshold
B1.offer_budget
B1.reentry_gain
B1.adapter_lr
B1.body_lr_scale
B1.plasticity
B1.retention_priority
```

## 33.3 B2 Gist

Mögliche lokale Targets:

```text
event/gist prediction
global relation prediction
boundary-aware compression
plan/discourse state
coarse offer usefulness
fine-fallback request calibration
```

Parametergruppe:

```text
B2.gist_span_target
B2.boundary_sensitivity
B2.global_context_gain
B2.compression_target
B2.local_pred_weight
B2.offer_threshold
B2.coarse_to_fine_threshold
B2.plasticity
B2.retention_priority
```

## 33.4 B3 Callosum

Es lernen getrennt:

```text
sender: what should I communicate?
bridge: how should it be encoded?
receiver: how should I interpret/use it?
channel-policy: was latent/exact/control/symbolic/no-message best?
```

Parametergruppe:

```text
B3.latent_mix
B3.exact_mix
B3.control_mix
B3.symbolic_mix
B3.no_message_prior
B3.message_budget
B3.receiver_gate
B3.cross_pred_weight
B3.alignment_strength
B3.private_state_protection
B3.anti_collapse_weight
B3.utility_threshold
```

## 33.5 C1 Executive continuity

C1 darf lernen:

```text
what state must persist?
what may decay?
what should be broadcast?
what should stay private?
when is state stale?
```

Parameter:

```text
C1.goal_persistence
C1.constraint_persistence
C1.state_refresh_rate
C1.broadcast_compression
C1.broadcast_budget
C1.stale_state_threshold
C1.private_state_retention
```

## 33.6 C2 Structured control organ

Mögliche Targets:

```text
intent extraction
constraint extraction
tool/action schema
route proposal
memory cue
confidence/escalation
structured control language
```

Parameter:

```text
C2.route_gain
C2.confidence_threshold
C2.control_lr
C2.depth_rung
C2.tool_authority
C2.embedding_gain
C2.abstain_threshold
C2.escalation_gain
```

Needle-3-class bleibt Kandidat, nicht Pflicht.

## 33.7 C3 Tiny language organ

Mögliche Targets:

```text
short conversational response
report wording
paraphrase
style adaptation
grounded short answer
teacher/human output comparison
```

Parameter:

```text
C3.language_budget
C3.short_answer_threshold
C3.teacher_imitation_weight
C3.human_preference_weight
C3.language_lr
C3.fact_learning_gain   // default very low; language quality != truth
```

## 33.8 C4 Focal Loop

C4 lernt nicht primär Weltfakten, sondern flexible Deliberationsdynamik:

```text
when to recruit?
what to keep focal?
when to re-enter B1/B2?
when to query Memory/World?
which deliberation mode next?
when does another cycle help?
```

Parameter:

```text
C4.coalition_threshold
C4.reasoning_effort
C4.max_cycles
C4.body_reentry_budget
C4.inquisition_depth
C4.workspace_refresh_gain
C4.conflict_recruit_gain
C4.novelty_recruit_gain
```

## 33.9 Action Gate / Fast Forward / World

Diese bleiben getrennt lernbar:

```text
Action Gate
↺ action selection / sequence utility / safety / cost

Fast Forward
↺ immediate action consequence prediction

World Model
↺ richer state transition / observation prediction
```

---

# 34. PASS I — CROSS-LEARNING / CO-ADAPTATION

## 34.1 B1 → B2

```text
B1 internal state
→ sender readout
→ B3 message
→ B2 receiver
→ downstream task / prediction / outcome
```

Credit kann getrennt aufgeteilt werden:

```text
sender_credit
bridge_credit
receiver_credit
channel_policy_credit
```

Kein direktes Kopieren von B1-Gewichten in B2.

## 34.2 B2 → B1

Analog, aber typischer Zweck:

```text
global plan/context/constraint
→ local fine processing
```

## 34.3 JEF → B1/B2

JEF lernt:

```text
when to ask
whom to ask
what query resolution
how much compute
when to ignore late offer
```

B1/B2 lernen:

```text
how to interpret JEF broadcast
which internal information answers that query
how to package useful offer
```

## 34.4 B1/B2 → JEF

JEF lernt Offer-Utility und Integration.
Bodies lernen Offer-Selection.
Bridges lernen compatible representation.

## 34.5 A3 → B/JEF

A3 darf zunächst Teacher-Semantik imitieren, soll aber langfristig zusätzlich an **downstream usefulness und real outcome** lernen, damit Teacher-Abhängigkeit nicht bloß durch schlechteres Copying ersetzt wird.

## 34.6 Self ↔ Reference ↔ Human

```text
SELF_CANDIDATE first
        ↓ freeze
REFERENCE_CANDIDATE second
        ↓
HUMAN_DECISION_PACKET
        ↓
credit decomposition:
- language
- factual
- routing
- cost
- completeness
- style
```

Teacher-Ausgabe wird nie rückwirkend zur eigenen Ausgabe umetikettiert.

---

# 35. PASS I — LERNMODULATION UND CREDIT

## 35.1 Vier getrennte Fragen

```text
ACTIVATION
Wer war beteiligt?
        ↓
eligibility

ERROR
Was war lokal/predictiv falsch?
        ↓
local/mapped δ

VALUE / EVIDENCE
Ist dieses Ereignis lernwürdig und in welcher Hinsicht?
        ↓
modulator vector

PLASTICITY
Wie stark darf genau dieser Pfad gerade verändert werden?
        ↓
metaplastic gate
```

Konzeptionell:

```text
Δθ_i ∝ e_i × δ_i × M_i × P_i
```

## 35.2 Modulator-Vektor

Mindestens:

```text
M_epistemic
M_task_success
M_surprise
M_uncertainty
M_novelty
M_cost
M_safety
M_social
M_retention
M_arousal/urgency
```

Keine einzelne Reward-Zahl darf diese Bedeutungen still zusammenfassen.

## 35.3 Lernarten bekommen unterschiedliche Gewichte

```text
knowledge update
← evidence / source / contradiction / confirmation

control update
← task success / cost / calibration / missed escalation

language update
← human/reference quality / groundedness / style

skill update
← repeatability / outcome / cost / safety

world update
← predicted vs actual state/outcome

attention update
← evidence recovery / downstream utility / missed signal
```

---

# 36. PASS I — MEMORY / LEARNING TIMESCALES

## 36.1 Memory Stack

```text
M0 ACTIVE
   focal/workspace/current state

M1 EXACT / PROVENANCE
   raw source, user, tool, world, teacher tags

M2 FAST EPISODIC
   concrete experience / second-attempt

M3 SEMANTIC STAGING
   candidate abstractions

M4 PROCEDURAL STAGING
   candidate skills/routes

M5 PARAMETRIC / VALIDATED DELTAS
   learned weights/adapters/slices

M6 ARCHIVE
   slow/versioned/recovery
```

## 36.2 Learning Timescales

```text
T0 milliseconds/turn state
   attention, gain, active slots, route, wake

T1 seconds/minutes fast persistent
   episodic memory, priorities, small control heads, projectors

T2 episode/idle shadow updates
   bridges, adapters, cross-predictors, skills

T3 repeated-confirmation consolidation
   selected body/JEF weights

T4 slow developmental/meta
   metaplasticity, homeostasis, structural changes, Age proposals
```

Die Grenzen sind Boot-Hypothesen, keine festen biologischen Zeiten.

## 36.3 Second-attempt ladder

```text
1) remembering
   exact/episodic retrieval improves repeat

2) adapting
   route/offer/context changes on similar input

3) learning
   generalized improvement survives paraphrase/restart/new instance
```

Benchmarks müssen diese drei Stufen auseinanderhalten.

---

# 37. PASS I — REPLAY / COUNTERFACTUAL / DREAM / HOMEOSTATIC SLEEP

Vier verschiedene Offline-Prozesse:

```text
REAL REPLAY
= recorded real experience

COUNTERFACTUAL REPLAY
= alternate action/route on real anchored episode

DREAM
= synthetic recombination / simulation / abstraction

HOMEOSTATIC SLEEP
= normalization / decay / plasticity recalibration / cleanup
```

Authority:

```text
real replay           → highest potential epistemic authority
counterfactual        → policy/world learning, weak factual authority
dream                 → exploration/abstraction, direct fact authority = 0
homeostatic sleep     → stability, not fact creation
```

Parameters remain research knobs:

```text
DREAM.novelty
DREAM.depth
DREAM.counterfactual_strength
DREAM.world_model_gain
DREAM.skill_recombination_gain
DREAM.policy_learning_gain
DREAM.body_learning_gain
DREAM.fact_write_gain = 0 direct
```

---

# 38. PASS I — AGE AS GRAPH-WIDE DEVELOPMENTAL ENVELOPE

Age ist kein Datenpfad und keine simple Unlock-Tabelle.

Es moduliert:

```text
path authority
plasticity ceilings
teacher reliance
human confirmation need
exploration budget
focal-loop freedom
observer depth
memory edit rights
dream/replay budget
tool/body autonomy
self-edit
self-messaging
structural plasticity
```

Age 0 bleibt voraussichtlich lange der reale Forschungszustand.

Beispielhafte **nicht-kanonische** Age-0-Konfiguration:

```text
B1/B2.base_weight_learning     ≈ off/tiny
A3.projector_learning          = moderate
C2.control_learning            = moderate
C3.language_shadow_learning    = moderate
FastEpisodic.write             = strong
Bridge learning                = shadow
Dream.fact_write               = 0
SelfInitiative                 = near 0
TeacherReliance                = high
HumanDecisionWeight            = high
```

Higher Age bleibt vorbereitet, nicht vorgetäuscht.

---

# 39. PASS II — OUT-OF-THE-BOX RESEARCH CHARTER

## 39.1 [LOCKED] Nicht nach Bestätigung suchen, sondern nach besseren Mechanismen

Research-Frage ist NICHT:

```text
"Welches Paper bestätigt unseren aktuellen Kasten?"
```

sondern:

```text
"Welche bekannte oder überraschende Mechanik erfüllt diese V13-Funktion
am besten unter Stabilitäts-, Lern- und Redmi-Grenzen?"
```

Widersprechende Evidenz ist wertvoll.

## 39.2 Function-first falsification rule

Für jede Funktion:

```text
1. Was muss die Funktion leisten?
2. Welche einfache Baseline erfüllt sie?
3. Welche V13-Hypothese ist besser?
4. Welche völlig andere Alternative könnte sie besser erfüllen?
5. Welche Messung würde unsere bevorzugte Idee widerlegen?
6. Welche alte Funktion darf trotz Implementationstausch nicht verschwinden?
```

## 39.3 Alternative Mechanism Bank

### Fine/Gist specialization

Nicht nur fixe Token-Gruppierung testen:

```text
boundary-aware grouping
learned temporal pooling
recurrent compression
state-space summaries
predictive bottlenecks
multi-resolution memory
hierarchical event states
adaptive chunk recurrence
```

### Callosum

Nicht nur latent vectors testen:

```text
cross-attention adapters
message tokens
recurrent state adapters
projected KV/state
shared prediction residuals
sparse mailbox slots
short symbolic control
exact source pointers
no-message baseline
hybrids
```

### JEF C2

Nicht auf Tiny Transformer festlegen:

```text
Needle-like structured model
small recurrent model
SSM / hybrid recurrent state
multi-head policy over executive state
learned state machine + neural readouts
tiny LM with grammar constraints
mixture of very small specialists
```

JEF bleibt Architektur unabhängig davon.

### Focal coalition

Nicht nur klassisches Workspace-Array:

```text
multi-slot blackboard
recurrent attractor-like state
gated shared latent state
sparse cross-attention hub
event-bound working-set
activity-silent state + selective reactivation
hybrids
```

### Attention / gain

```text
standard attention
multiplicative gain
sparse routing
index-based retrieval
predictive gain
competition/inhibition
salience-triggered re-entry
active sensing / re-look policies
```

### Memory

```text
exact retrieval
latent episodic retrieval
key/value associative memory
small parametric fast weights
conditional sparse parameter memory
recurrent state
hybrid multi-store
```

### Learning

Nicht alles zwingend JEPA:

```text
JEPA-like latent prediction
contrastive prediction
masked/state prediction
predictive coding-style residuals
self-distillation
local auxiliary losses
control/bandit learning for routing
supervised human/teacher correction
world-model prediction
combinations
```

`JEPA` bleibt zentrales V13-Prinzip für viele repräsentative Pfade, aber eine Control-Policy muss nicht künstlich denselben Loss benutzen, wenn ein anderer Mechanismus messbar besser ist.

### Habits / automaticity

```text
compiled route policy
cached procedural graph
distilled small policy
recurrent shortcut
skill-conditioned head
fast associative mapping
```

Fehler/Novelty muss den Shortcut wieder in Deliberation aufbrechen können.

### Teacher internalization

Nicht nur linear "Teacher weniger":

```text
teacher dropout
teacher disagreement
multiple teachers
student-first prediction
teacher-afterwards comparison
uncertainty-gated teacher calls
counter-teacher / critique
raw-only canary trials
```

## 39.4 Developmental architecture may differ from mature architecture

[LOCKED DESIGN FREEDOM]

Age 0 darf **mehr Scaffold, mehr External Help und mehr explizite Struktur** besitzen als ein reifes System.

Das ist kein Scheitern der Architektur.

```text
DEVELOPMENTAL V13
≠
MATURE V13
```

Beispiel:

```text
Age 0: teacher encoder + explicit structured query packets + rigid replay gates
later: student perception + learned compact state + internalized routes
```

Ein Modul darf also als Entwicklungsorgan existieren und später nach Parity/Retention verschwinden.

## 39.5 Research muss auch gegen V13 argumentieren dürfen

Gezielt prüfen:

```text
Braucht B3 expliziten Callosum oder genügt eine bessere gekoppelte Dynamik?
Braucht C3 langfristig ein klassisches LM?
Braucht C4 explizite Workspace-Slots oder funktioniert activity-silent recurrent state besser?
Ist JEPA für jeden repräsentativen Pfad wirklich stabiler als einfachere Objectives?
Hilft Gist-Spezialisierung wirklich oder erzeugt sie nur Informationsverlust?
Verbessert Dream tatsächlich Transfer oder erzeugt es Drift?
Sind zwei Bodies auf Redmi die beste Laborapproximation oder sollte Hardware zeitweise shared-body ablation nutzen?
```

Ein negatives Ergebnis entfernt eine **Hypothese**, nicht automatisch das zugrunde liegende Funktionsziel.

---

# 40. PASS II — CANONICAL V13 VS REDMI LAB REALIZATION

Zwei Beschreibungen müssen gleichzeitig existieren:

```text
CANONICAL V13
= langfristige Funktionsarchitektur

REDMI LAB REALIZATION
= kleinste messbare Approximation derselben Hypothesen
```

Beispiele erlaubter Redmi-Abweichungen:

```text
smaller boot bodies
sequential instead of simultaneous B1/B2 execution
aggressive mmap / unload
smaller workspace dimension
shadow updates on tiny adapters first
external teacher API instead of local teacher
reduced context windows
sampled observer coverage
```

Nicht erlaubt:

```text
"Redmi kann X nicht" → X aus Canon löschen
```

Stattdessen:

```text
canonical function X
→ lab proxy X_small
→ parity/utility metric
```

---

# 41. PASS III — BRAIN-NEAR DESIGN DOCTRINE

## 41.1 Hirnnah bedeutet Organisationsprinzipien, nicht Namens-Cosplay

V13 ist dann hirnnah, wenn seine **Dynamik** Eigenschaften zeigt wie:

```text
parallel local processing
specialized pathways
multiple temporal scales
recurrent loops
selective global/focal availability
competition + gain control
activity-dependent local plasticity
late modulatory credit
fast + slow memory
proceduralization / habits
prediction + action-outcome correction
self-vs-world distinction
offline replay
homeostatic stabilization
developmental plasticity
active perception
body/resource interoception
```

Es reicht nicht, Kästen "Thalamus" oder "Cerebellum" zu nennen.

## 41.2 Kein einzelner Master-Controller

JEF ist wichtig, aber lokale Prozesse dürfen selbstständig wirken:

```text
B1 local recurrence
B2 local recurrence
A4 salience/attention
skills/habits
memory cueing
fast-forward prediction
reflexes
```

JEF/Focal processing wird besonders bei:

```text
novelty
conflict
uncertainty
new goals
rule conflict
failed habit
unresolved prediction error
```

rekrutiert.

## 41.3 Mehrere Zeitskalen statt nur "8 Tokens"

B1/B2-Unterschied soll langfristig dynamisch entstehen aus:

```text
update frequency
integration horizon
recurrent persistence
compression span
event boundaries
memory horizon
prediction horizon
attention scale
```

Der historische ~1-vs-~8-Token-Bootwert bleibt Teststart, aber nicht die Theorie der Zeitskalen.

## 41.4 Focal availability ist knapp

Nicht alles wird "bewusst".

```text
broad distributed state
      ↓ gain/admission
limited focal coalition
      ↓
flexible report/action/re-entry authority
```

Kapazitätsknappheit soll **funktional messbar** sein:

- begrenzte aktive Slots/State,
- Konkurrenz,
- Ersetzungs-/Refresh-Kosten,
- Interrupt durch Salience,
- automatische Prozesse außerhalb des Fokus.

## 41.5 Plasticity ist lokal + moduliert + langsam selbstreguliert

Hirnnahe V13-Lernlogik:

```text
local activity
→ eligibility

local prediction/control error
→ candidate change

later outcome/evidence
→ modulatory context

metaplasticity
→ learning permission/strength

homeostasis
→ operating envelope
```

Nicht jede Erfahrung löst persistentes Lernen aus.

## 41.6 Habit formation / proceduralization

Wiederholt erfolgreiche fokale Routinen dürfen:

```text
slow deliberate route
→ repeated success
→ procedural staging
→ shadow shortcut
→ validated automatic route
```

Bei Fehler/Novelty:

```text
automatic route
→ prediction error / salience
→ reopen focal deliberation
```

Automaticity ist damit nicht ein separater Agent, sondern eine veränderte Route durch dasselbe System.

## 41.7 Fast and slow memory complementarity

```text
fast episodic
= schnell aufnehmen, konkret, source-linked

slow parametric/conceptual
= langsam generalisieren, stabiler, schwerer reversibel
```

V13 soll zunächst erinnern können, **bevor** es tiefe Base-Weight-Konsolidierung beherrscht.

## 41.8 Action is part of cognition

World understanding wird nicht nur aus passivem Text gelernt.

Schon Body-0 erzeugt echte Schleifen:

```text
choose tool
→ tool result

write file
→ changed file state

load model
→ RAM/latency/thermal change

ask user
→ correction/confirmation
```

Damit können World Model, Fast Forward, Affordances und Self/Body Model bereits vor Robotik grounded lernen.

## 41.9 Active perception

Später soll Wahrnehmung nicht nur passiv sein:

```text
uncertainty/conflict
→ request higher-res source
→ re-read exact span
→ inspect image tile
→ listen again to audio segment
→ move sensor / camera later
```

Das verbindet Attention, Action und Perception zu einer Schleife.

## 41.10 Developmental plasticity

Age soll nicht einfach "mehr Rechte" bedeuten.

Reife verändert zugleich:

```text
plasticity
teacher dependence
habit strength
exploration
deliberation freedom
memory consolidation
body autonomy
self-edit rights
structural change budget
```

Neue Domänen dürfen capability-lokal wieder "jung" sein.

## 41.11 Prediction at multiple horizons

Statt eines einzigen Welt-Predictors:

```text
immediate action consequence  → Fast Forward
short event prediction        → B1/B2 local predictors
medium task/world transition  → World-JEPA
longer abstraction/plan       → B2/Memory/World recurrent state
```

Mehrere Horizonte dürfen unterschiedliche Errors und Plasticity-Timescales haben.

## 41.12 Self/world distinction is mandatory

Corollary Copy ist nicht Dekoration.

Ohne sie drohen:

```text
own generated text mistaken for evidence
own file edit mistaken for external observation
own tool request conflated with tool response
self-caused sensor change misread as world surprise
```

Deshalb jede relevante Aktion mit `action_id`, expected consequence und later observed result verbinden.

---

# 42. PASS III — HIRNNAHE OPTIMIERUNGSPRINZIPIEN

Optimierung soll möglichst die kognitive Struktur **unterstützen**, nicht verdecken.

## 42.1 Event-driven statt permanently-hot

Auf Redmi besonders interessant:

```text
mostly quiet subsystems
→ wake by event/salience/goal
→ bounded processing
→ return compact state/offer
→ sleep/unload if safe
```

Das ist gleichzeitig ressourcenschonend und kompatibel mit spezialisierter verteilter Verarbeitung.

## 42.2 Activity-silent / reconstructable state

Nicht jeder Zustand muss als heißer KV-Cache im RAM bleiben.

Mögliche Kombination:

```text
hot focal state
warm compact latent/state
exact source pointers
reconstructable local cache
cold archive
```

## 42.3 Gain before brute-force compute

Schwierigkeit soll nicht automatisch "alles maximal aktivieren" bedeuten.

Zuerst:

```text
which evidence?
which scale?
which body?
which memory?
which source region?
```

Dann Compute erhöhen.

## 42.4 Local shortcuts after learning

Wenn eine Route stabil geworden ist, darf eine kleinere Policy/Head sie ausführen, solange Re-open-Mechanismen bestehen.

Das reduziert Redmi-Kosten **durch Lernen**, nicht nur Quantisierung.

---

# 43. RESEARCH-READY CONTRADICTION / OPEN-QUESTION REGISTER

Diese Punkte werden ausdrücklich NICHT vor Research als gelöst ausgegeben.

## 43.1 [OPEN] Observer Coverage vs Full Wake

Unterscheide:

```text
observer availability
cheap partial observer
cached/readout observer
full body observer
full focal re-entry
```

Age 0 braucht hohe Coverage, nicht zwingend zwei volle Body-Forwards pro Event.

## 43.2 [OPEN] Technische Repräsentation der Focal Coalition

Funktionsziel ist klar, Implementation offen:

```text
B4 workspace + C1 binding + gain
vs
recurrent shared state
vs
activity-silent + sparse reactivation
vs
hybrid
```

C4 koordiniert; C4 ist nicht selbst der ganze Workspace.

## 43.3 [RESEARCH] C2 vs C3 boundary

Testen:

```text
separate C2 + C3
C2 handles short language too
shared tiny backbone with separate heads
fully distinct models
```

Keine vorzeitige Streichung.

## 43.4 [RESEARCH] B1/B2 online plasticity depth

Stufenweise testen:

```text
heads only
projectors
adapters
selected active experts
selected shared layers
base weights
```

## 43.5 [RESEARCH] Exact prediction objective per subsystem

JEPA-like latent prediction bleibt Kernkandidat, aber Lossform und Objective-Mix bleiben offen.

## 43.6 [RESEARCH] JEF learning rule

JEF könnte Mischform benötigen:

```text
supervised teacher/human correction
+ outcome/control learning
+ prediction/state learning
+ calibration learning
+ replay
```

Nicht erzwingen, dass JEF dieselbe Lernregel wie B1/B2 verwendet.

## 43.7 [OPEN] Knowledge in weights vs memory

Boot-Heuristik:

```text
generalizable skill/strategy/world regularity
→ candidate parametric consolidation

personal exact/event data
→ Exact/Episodic by default

repeated personalized pattern
→ isolated reversible delta candidate
```

## 43.8 [RESEARCH] Explicit Callosum vs emergent coupled dynamics

Callosum-Funktion bleibt, aber konkrete Umsetzung darf challenged werden.

## 43.9 [RESEARCH] Does Dream help?

Dream muss gegen:

```text
no dream
real replay only
counterfactual only
dream with no weight writes
dream with policy/world updates
```

abgetragen werden.

## 43.10 [RESEARCH] Developmental scaffold retirement

Jede Teacher-/Translator-/Scaffold-Komponente braucht Parity-, Retention- und Regression-Kriterien für Reduktion.

---

# 44. RESEARCH QUESTION MAP — NÄCHSTER DEDIZIERTER PASS

Der spätere Research soll nicht thematisch herumwandern, sondern diese Fragen bearbeiten:

```text
A-PLANE
- raw+teacher multimodal student learning
- active perception
- learned segmentation/boundaries
- teacher dropout/internalization

B1/B2
- complementary specialization
- multiscale temporal integration
- sparse mobile bodies
- stable local plasticity

B3
- cross-model communication
- latent vs exact vs symbolic vs no-message
- receiver calibration

B4/C4
- limited focal/global availability
- recurrent workspace / activity-silent state
- trajectory + halting

C1
- persistent executive state
- compact broadcast

C2/C3
- Needle-class vs tiny LM vs recurrent/SSM/control heads
- minimal language/control footprint

F1/F2
- gain, salience, inhibition, active sensing

F3 MEMORY
- fast episodic second-attempt improvement
- associative/parametric fast traces
- safe consolidation

F4 WORLD/SELF/BODY
- action-conditioned prediction
- self/world distinction
- body interoception / affordances

F5 ACTION
- competition/action selection
- fast-forward control
- safe exploration

F6/F7 LEARNING
- eligibility / local credit
- JEPA alternatives/objective mix
- metaplasticity
- homeostasis
- shared pre-router forgetting

F8 AGE
- developmental plasticity / human control
- reversible authority

F9 DREAM
- replay, counterfactual, dream utility

F10 REDMI RUNTIME
- residency
- mmap
- cache reconstruction
- event-driven scheduling
- thermals
- quantization
```

Research sollte pro Frage enthalten:

```text
1. current strongest relevant approaches
2. evidence for/against
3. smallest Redmi-testable baseline
4. V13 mapping
5. failure modes
6. ablation
7. what result would change the Canon implementation
```

---

# 45. MINIMUM NON-NEGOTIABLE V13 IDENTITY AFTER THE TRIPLE PASS

Wenn spätere Research-Runden radikal umbauen, müssen mindestens folgende Funktionen erhalten oder explizit ersetzt werden:

```text
1. world/source-preserving ingress
2. complementary fine/gist cognition
3. direct cross-scale communication
4. persistent distributed active state
5. composite JEF executive/action interface
6. limited focal/global availability
7. memory separated from workspace
8. exact provenance
9. action-outcome loop
10. self/world distinction via action copy or equivalent
11. fast episodic second-attempt improvement
12. local activity-dependent credit
13. typed outcome/evidence modulation
14. prediction-based representation/world learning
15. metaplasticity + homeostatic stability
16. replay/consolidation separated from dream
17. developmental Age/human-control envelope
18. rollback/retention/regression protection
19. modality scaffolds that can be retired by evidence
20. local-first runtime with architecture/runtime separation
```

Das ist V13s Funktionsidentität. Die genaue neuronale Mechanik darf deutlich überraschender werden.

---

# 46. KANONISCHER v10.14-SATZ

**V13 ist ein entwicklungsfähiges, brain-inspired continual-learning System aus einer lernbaren Wahrnehmungs-/Ingress-Ebene, einem komplementären Fine/Gist-Split-Brain-Core und einem zusammengesetzten JEF-Executive-/Action-System. Seine Intelligenz entsteht nicht aus einem seriellen Zentralrouter, sondern aus spezialisierten lokalen Zuständen, direkter Cross-Scale-Kommunikation, begrenzter fokaler globaler Verfügbarkeit, hierarchischem Gedächtnis, Action–Outcome-Prediction und aktivitätsabhängiger lokaler Plasticity, die durch typisierte spätere Modulatoren, Metaplastizität, Homeostasis, Replay und Entwicklungs-Age geregelt wird. Die Funktionsziele sind Canon; konkrete Implementierungen – Callosum, Workspace, JEF-Organe, Attention, Memory, Prediction Objectives und Runtime – bleiben experimentell und dürfen durch überraschend bessere Mechanismen ersetzt werden, solange ihre Funktion, Provenance, Retention und messbare Second-Attempt-Verbesserung erhalten oder verbessert werden. Das Redmi Note 10 Pro ist die erste Laborbegrenzung, nicht die Theorie des Systems.**


---

# 47. v10.15 — TAGESAKTUELLER RESEARCH-PASS + LAYERED PARAMETER STACK

**Research-Stichtag:** 20.09.2026  
**Regel:** Dieser Abschnitt ersetzt v10.14 **nicht**. Er ist ein additiver Research-/Bootstrap-Pass.  
**Ziel:** aktuelle 2026-Techniken dort einsortieren, wo sie V13 konkret verbessern können, und daraus einen **spielbaren Parameter-Stack** für Age 0 / Redmi Note 10 Pro ableiten.

WICHTIG:

- Zahlen in diesem Abschnitt sind **[BOOT] Startpriors**, keine biologischen Konstanten und keine endgültigen Hyperparameter.
- `0.0 … 1.0` bedeutet zunächst **relative Stärke/Authority**, nicht automatisch eine Optimizer-Learning-Rate.
- Parameter sollen später experimentell bewegt werden können.
- Funktions-Canon bleibt stabil; konkrete Implementierung bleibt falsifizierbar.
- Research darf Funktionen ersetzen, aber nicht still löschen.

---

# 48. RESEARCH-DELTA — WAS IM SEPTEMBER 2026 BESONDERS RELEVANT IST

## 48.1 [RESEARCH→BOOT CANDIDATE] Needle 3 passt sehr gut zu C2/JEF-Control

Aktueller Stand:

- 29–121M Parameter,
- 2–20 Layer als separat deploybare Subnetze,
- ca. 8–29 MB 2-bit Deployments,
- Tool Calling,
- strukturierte Extraction,
- Embeddings,
- grammar-constrained output,
- learned confidence head,
- native kleine Device-Runner.

V13-Folge:

```text
C2 Structured Control Organ
    ← Needle-3-class ernsthaft benchmarken

NICHT:
Needle = JEF
```

Besonders interessant:

```text
C2.intent_parse
C2.tool_select
C2.packet_emit
C2.embedding
C2.confidence
C2.route_hint
```

Age-0 Redmi:

```text
Needle 4L baseline
Needle 8L fallback / harder packets
20L nur Benchmark, nicht Default
```

**Wichtig:** mehrere Rungs zunächst als getrennte Builds behandeln. Nicht behaupten, die Engine könne innerhalb eines laufenden Turns kostenlos zwischen Tiefen umschalten.

Research-Quelle:
- https://github.com/cactus-compute/needle
- https://www.cactuscompute.com/needle

---

## 48.2 [RESEARCH] GPT-Live bestätigt eine sehr wichtige V13-Trennung

OpenAI GPT-Live arbeitet full-duplex und trennt den kleinen/reaktionsschnellen Live-Pfad von tieferer asynchroner Delegation. Außerdem hält das System einen **provisorischen/speculative State** und einen später finalisierten/authoritative Record.

V13-Folge:

```text
LIVE / FAST STATE
= darf sofort Verhalten beeinflussen
= noch nicht automatisch Lernquelle

AUTHORITATIVE EVENT
= finalisiert / stabilisiert
= darf Experience / Replay / Learning speisen
```

Neue wichtige Flags:

```text
event_state = PROVISIONAL | FINAL
learning_eligible = false until FINAL
provisional_gain
finalization_confidence
```

Außerdem:

```text
realtime path
!=
heavy reasoning path
```

Das passt direkt zu:

```text
C2/C3 live control
        ||
B1/B2 / tools / world deeper work
```

Quelle:
- https://openai.com/index/continuous-voice-interaction-with-gpt-live/

---

## 48.3 [RESEARCH] Gemini 3.8 Live bestätigt asynchrone Tool-/Reasoning-Schleifen

Gemini 3.8 Live (September 2026):

- Text/Bild/Audio/Video Input,
- Text/Audio Output,
- interleaved reasoning,
- asynchrone Function Calls standardmäßig non-blocking,
- separates Extended-Thinking-Modell für komplexere Tasks.

V13-Folge:

```text
C-Plane fast/live loop
    darf weiterlaufen

tool / B1 / B2 / world
    dürfen async arbeiten

late result
    → versioned offer
    → only incorporate if still state-compatible
```

Dafür braucht V13 explizit:

```text
offer_state_version
offer_deadline
offer_staleness
candidate_invalidation
```

Quelle:
- https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live
- https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-8-live-gemini-3-8-live-extended-thinking/

---

## 48.4 [RESEARCH] Gemma 4 12B stärkt das A-Plane-Ziel: schwere Teacher können verschwinden

Gemma 4 12B verarbeitet multimodale Daten ohne die traditionellen schweren getrennten Vision-/Audio-Encoder:

- Vision: leichte Embedding-/Projection-Schicht,
- Audio: Projektion des Rohsignals in den Text-/Backbone-Raum.

V13-Folge:

```text
AGE 0:
RAW PATH + strong frozen teacher

später:
RAW PATH + small learned projector
        + increasingly native B-core interpretation

Teacher dependency ↓
```

Das bestätigt **nicht**, dass jedes kleine V13-Modell automatisch Raw-Pixel lernen kann. Es zeigt aber, dass das Endziel „schwere semantische Encoder weg, kleine physische/projektive Schnittstelle bleibt“ technisch plausibel ist.

Quelle:
- https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/
- https://developers.googleblog.com/gemma-4-12b-the-developer-guide/

---

## 48.5 [RESEARCH] Qwen3-Omni zeigt eine nützliche C/Egress-Trennung

Qwen3-Omni verwendet eine Thinker/Talker-Trennung und einen Streaming-Speech-Pfad über diskrete Codec-Codebooks plus leichten kausalen ConvNet-Decoder.

V13-Folge:

```text
JEF / Brain
→ intent / semantic speech plan

C7 Speech Effector
→ codec / acoustic generation
→ audio
```

Also:

```text
Sprachintelligenz
!=
Waveform-Erzeugung
```

C7 darf ein spezialisiertes physisches Output-Organ sein, ohne zur vierten Intelligenz zu werden.

Quelle:
- https://arxiv.org/abs/2509.17765

---

## 48.6 [RESEARCH] DeepSeek V4.1-Flash bringt vier starke Runtime-/Architekturideen

DeepSeek V4.1-Flash (10.09.2026):

- Causal Encoder–Decoder,
- 8B aktive Parameter für Input / 16B für Output,
- Compressed Sparse Attention 2 mit Cross-Layer-KV-Reuse,
- 890 Byte globaler KV pro Token,
- SWA Bounded Replay,
- Engram conditional memory,
- DSpark speculative decoding.

V13 übernimmt NICHT das riesige Modell.

V13-Forschungsfragen:

```text
1. Input-Verarbeitung darf billiger sein als Output-Verarbeitung.
2. Global state darf zwischen Layern geteilt/projiziert werden.
3. Lokale Cache-Zustände dürfen rekonstruiert statt permanent gehalten werden.
4. Sparse associative memory kann stabile Patterns billig ergänzen.
5. Speculative decode bleibt SERVING, nicht Kognition.
```

Besonders wichtig für Redmi:

```text
persist only:
- exact source
- compact global state
- important anchors

reconstruct:
- disposable local cache
```

Quelle:
- https://www.deepseek.com/en/news/deepseek-v4-1-flash/
- https://arxiv.org/abs/2609.19969
- https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash

---

## 48.7 [RESEARCH] MiniMax Sparse Attention spricht für „Index zuerst, Attention danach“

MSA:

```text
cheap index branch
→ wählt relevante KV-Blöcke pro GQA-Gruppe
→ teure Attention nur auf ausgewählte Blöcke
```

V13-Folge außerhalb eines nativ MSA-trainierten Bodys:

```text
Context/Memory Block Index
→ shortlist
→ exact/native body attention
```

NICHT:

```text
externe Blocksuche = neuronale Attention
```

Diese Ebenen bleiben getrennt.

Quelle:
- https://arxiv.org/abs/2606.13392
- https://github.com/MiniMax-AI/MSA

---

## 48.8 [RESEARCH] „Language Models Need Sleep“ passt direkt zu F9, aber bleibt Proof-of-Concept

2026-Paper von Behrouz/Hashemi/Mirrokni:

```text
short-term memories
→ consolidation / distillation
→ dreaming / synthetic curriculum
```

V13 übernimmt daraus nicht blind RL-Dreaming.

Interessant ist die klare Trennung:

```text
REAL MEMORY CONSOLIDATION
vs
DREAM / synthetic self-improvement
```

V13 behält deshalb:

```text
Dream.fact_write_gain = 0
```

bis Grounding unabhängig bestätigt wird.

Quelle:
- https://arxiv.org/abs/2606.03979

---

## 48.9 [RESEARCH] Procedural Memory wird 2026 deutlich interessanter

ReMe (ACL 2026) zeigt einen Memory-Lifecycle aus:

- Experience Distillation,
- context-adaptive reuse,
- utility-based refinement/pruning.

V13-Folge:

```text
Procedural staging
≠ append-only skill log

sondern:
candidate
→ reuse
→ measure utility
→ refine / prune
→ possible internalisation
```

Quelle:
- https://aclanthology.org/2026.findings-acl.829/

---

## 48.10 [RESEARCH] Continual Learning: stabile pretrained geometry kann als Anker dienen

MePo++ (September 2026) trennt:

```text
representation refinement/plasticity
+
reconciliation with stable pretrained geometry
```

V13-Folge:

Zusätzlich zu Replay/Retention kann ein langsamer **representation anchor** sinnvoll sein:

```text
current representation
↔ slow/frozen anchor representation
```

Nicht als starres „bleib wie früher“, sondern als Drift-Messung/Regularizer.

Neue mögliche Parameter:

```text
ANCHOR.geometry_weight
ANCHOR.new_domain_relaxation
ANCHOR.old_skill_weight
```

Quelle:
- https://arcxiv.org/abs/2609.05075

---

## 48.11 [RESEARCH] Event-driven sparse/recurrent Modelle sind für JEF/B2 ernsthaft interessant

August 2026 wurde ein Ansatz mit:

- quantisierten linear-attention/SSM-artigen Modellen,
- trainierbaren Aktivitätsschwellen,
- event-driven sparsity,

gezeigt.

V13-Folge:

```text
C2 / executive-state
oder
B2 coarse temporal state
```

müssen langfristig nicht zwingend klassische Transformer sein.

Alternative:

```text
fixed-size recurrent state
+
sparse event updates
+
occasional global retrieval
```

Quelle:
- https://arxiv.org/abs/2608.30439

---

## 48.12 [RESEARCH] Aktuelle Continual-Learning-Arbeit unterstützt „Plastizität + stabiler Anker“

2026-Ergebnisse bleiben konsistent mit dem alten V13-Problem:

```text
plasticity
vs
stability
```

Daher keine aggressive sofortige Base-Weight-Adaption.

Neue Updates zunächst:

```text
fast state
→ memory
→ shadow delta
→ retention test
→ only then consolidation
```

Quelle:
- https://doi.org/10.1145/3735633
- https://www.sciencedirect.com/science/article/pii/S0925231226006946

---

## 48.13 [BRAIN-NEAR SUPPORT] Eligibility-Traces bleiben ein starker Organisationsanker

2026-Arbeiten zeigen weiterhin das Prinzip:

```text
local recent activity trace
+
delayed modulatory/reward signal
→ later weight change
```

V13 darf daraus keine biologische Gleichheit ableiten, aber als Organisationsprinzip passt es sehr gut.

Quelle:
- https://www.nature.com/articles/s41467-026-69898-9
- https://www.nature.com/articles/s41467-026-68453-w

---

## 48.14 [BRAIN-NEAR SUPPORT] Thalamus eher dynamische Kopplung/Lernen als serieller Router

Eine aktuelle Nature-Communications-Arbeit zum mediodorsalen Thalamus/OFC zeigt eine Rolle in adaptiver assoziativer Lernkontrolle.

V13-Folge:

```text
Thalamic/Gain Fabric
≠ choose exactly one module

sondern eher:
- gain
- coupling
- admission
- learning context
- state-dependent amplification
```

Quelle:
- https://www.nature.com/articles/s41467-026-76118-x

---

## 48.15 [BRAIN-NEAR SUPPORT] Event Boundaries sollten prediction- UND context-sensitive sein

2026 Event-Segmentation-Forschung spricht dagegen, Event Boundaries nur aus Surprise zu erzeugen.

V13:

```text
boundary_score =
prediction_error
+ context_shift
+ goal_shift
+ action transition
+ source transition
```

nicht nur:

```text
boundary = surprise > threshold
```

Quelle:
- https://www.nature.com/articles/s41562-026-02403-w

---

# 49. PARAMETER-NORMALISIERUNG

Für fast alle Research-Knobs:

```text
0.00 = aus / keine Authority
0.10 = sehr schwach
0.25 = schwach
0.50 = mittel
0.75 = stark
0.90 = sehr stark
1.00 = maximale erlaubte Authority
```

WICHTIG:

```text
learn_gain = 0.5
```

bedeutet NICHT:

```text
learning rate = 0.5
```

sondern:

```text
relative Freigabe / Gewichtung dieses Lernpfads
```

Actual optimizer-LR wird separat angegeben.

---

# 50. LAYER 0 — GLOBAL AGE-0 ENVELOPE [BOOT]

```text
SYSTEM.system_stage                   = 0
SYSTEM.user_stage_cap                 = 0

AGE.human_confirmation_need           = 0.90
AGE.teacher_reliance_new_capability   = 0.80
AGE.autonomy_budget                   = 0.10
AGE.exploration_budget                = 0.15
AGE.structural_edit_authority         = 0.00
AGE.self_message_authority            = 0.00
AGE.dream_authority                   = 0.10
AGE.base_weight_plasticity_ceiling    = 0.05
AGE.adapter_plasticity_ceiling        = 0.35
AGE.head_projector_plasticity_ceiling = 0.65
AGE.fast_memory_write_authority       = 0.90
```

Interpretation:

Age 0 darf **viel lernen**, aber zunächst dort, wo Rollback billig ist:

```text
State / Memory        = hoch
Heads / Projectors    = mittel-hoch
Adapters / Bridges    = niedrig-mittel
Body Base Weights     = fast aus
Structural Growth     = aus
```

---

# 51. LAYER 1 — A-PLANE / PERCEPTION PARAMETER

## 51.1 A0 Raw/Physical

```text
A0.raw_preservation                    = 1.00
A0.semantic_processing                 = 0.00
A0.timestamp_precision                 = 1.00
A0.source_binding_strength             = 1.00
```

A0 soll möglichst wenig „denken“.

---

## 51.2 A1 Segmentation / Boundaries

```text
A1.fixed_chunk_prior                   = 0.40
A1.semantic_boundary_gain              = 0.25
A1.context_shift_gain                  = 0.35
A1.prediction_error_boundary_gain      = 0.25
A1.goal_change_boundary_gain           = 0.30
A1.action_transition_boundary_gain     = 0.30
A1.multi_scale_overlap                 = 0.60
A1.learn_gain                          = 0.15
```

Boot-Regel:

```text
Boundary nicht nur aus Surprise.
```

---

## 51.3 A2 Frozen Teacher

Neue Modalität:

```text
A2.teacher_presence                    = 0.85
A2.teacher_authority_semantic          = 0.55
A2.teacher_authority_epistemic         = 0.35
A2.teacher_gradient                    = 0.00
A2.teacher_dropout                     = 0.15
A2.teacher_disagreement_sampling       = 0.25
```

Teacher hilft stark bei Bedeutung, hat aber **keine Truth-Sonderrechte**.

---

## 51.4 A3 Student Projector

```text
A3.learn_gain                          = 0.65
A3.teacher_alignment_weight            = 0.35
A3.reconstruction_weight               = 0.20
A3.cross_body_utility_weight           = 0.25
A3.real_outcome_weight                 = 0.20

A3.plasticity                          = 0.70
A3.retention_priority                  = 0.45
A3.shadow_ratio                        = 0.80
```

Actual optimizer [BOOT]:

```text
projector LR:
1e-4 … 5e-4

start:
2e-4
```

---

## 51.5 A4 Perceptual Attention

```text
A4.salience_gain                       = 0.45
A4.goal_topdown_gain                   = 0.45
A4.novelty_gain                        = 0.35
A4.teacher_hint_gain                   = 0.20
A4.raw_relook_authority                = 0.70
A4.suppression_max                     = 0.70
```

Kein Chunk darf durch A4 endgültig verschwinden.

---

# 52. LAYER 2 — B1 DETAIL BODY

Aktueller Redmi-Kandidat:

```text
MobileMoE-S-QAT class
272M active / 1.3B total
~0.68 GB projected INT4 weights
```

Nur Kandidat; License/Runner beachten.

Boot:

```text
B1.detail_gain                         = 0.80
B1.literal_gain                        = 0.90
B1.exact_source_gain                   = 0.90
B1.local_context_gain                  = 0.75
B1.global_context_gain                 = 0.35

B1.offer_threshold                     = 0.35
B1.offer_budget                        = 0.45
B1.reentry_gain                        = 0.70

B1.local_jepa_weight                   = 0.45
B1.adapter_learn_gain                  = 0.20
B1.base_weight_learn_gain              = 0.00
B1.retention_priority                  = 0.90
```

Fine resolution:

```text
B1.target_integration_scale            ≈ 1–3 native tokens / short span
```

Nicht hart; Code/Zahlen dürfen noch feiner werden.

---

# 53. LAYER 3 — B2 GIST BODY

Boot-Kandidat ebenfalls MobileMoE-S-QAT-class für faire Symmetrie.

```text
B2.gist_gain                           = 0.85
B2.global_context_gain                 = 0.90
B2.literal_gain                        = 0.30
B2.event_relation_gain                 = 0.85
B2.plan_structure_gain                 = 0.80

B2.gist_span_target                    = 8 token-equivalents
B2.gist_span_min                       = 3
B2.gist_span_max_boot                  = 24
B2.boundary_sensitivity                = 0.65
B2.coarse_to_fine_threshold            = 0.45

B2.offer_threshold                     = 0.30
B2.offer_budget                        = 0.50
B2.reentry_gain                        = 0.65

B2.local_jepa_weight                   = 0.50
B2.adapter_learn_gain                  = 0.20
B2.base_weight_learn_gain              = 0.00
B2.retention_priority                  = 0.90
```

Boot:

```text
~12 active gist slots
```

aber event-/boundary-aware statt dauerhaft fix.

---

# 54. LAYER 4 — B3 CALLOSUM

Bootstrap soll LATENT noch nicht übervertrauen.

Initiale Channel Prior:

```text
B3.channel.latent                      = 0.20
B3.channel.exact_source                = 0.35
B3.channel.control                     = 0.25
B3.channel.symbolic                    = 0.10
B3.channel.no_message                  = 0.10
```

Wenn Latent-Kommunikation nachweislich gewinnt:

```text
B3.channel.latent
→ darf Richtung 0.40–0.55 steigen
```

aber nur nach Utility/Retention.

Weitere Knobs:

```text
B3.message_budget                      = 0.35
B3.receiver_gate                       = 0.45
B3.cross_jepa_weight                   = 0.30
B3.alignment_strength                  = 0.25

B3.private_state_protection            = 0.90
B3.anti_collapse_weight                = 0.80
B3.ood_reject_threshold                = 0.65

B3.learn_gain                          = 0.25
B3.shadow_ratio                        = 0.90
```

Wichtig:

```text
message learned
!=
private representation aligned away
```

---

# 55. LAYER 5 — B4 WORKSPACE / FOCAL STATE

Redmi Boot:

```text
B4.workspace_dim                       = 768
B4.active_slot_target                  = 12
B4.active_slot_soft_max                = 16
B4.exact_pointer_slots                 = 4
B4.goal_slot_priority                  = 0.95
B4.conflict_slot_priority              = 0.80
B4.source_binding_strength             = 1.00

B4.write_threshold                     = 0.35
B4.refresh_threshold                   = 0.40
B4.replacement_aggressiveness          = 0.35
B4.multi_timescale_mix                 = 0.70
```

Focal subset:

```text
FOCAL.slot_target                      = 6
FOCAL.slot_soft_max                    = 8
FOCAL.global_broadcast_gain            = 0.65
FOCAL.recurrent_gain                   = 0.55
```

Das ist absichtlich kleiner als gesamter Workspace.

---

# 56. LAYER 6 — C1 EXECUTIVE STATE / BROADCAST

Boot:

```text
C1.exec_state_dim                      = 256
C1.broadcast_dim                       = 256

C1.goal_persistence                    = 0.90
C1.constraint_persistence              = 0.95
C1.state_refresh_rate                  = 0.65
C1.broadcast_compression               = 0.75
C1.old_state_decay                     = 0.25
C1.offer_recency_weight                = 0.55
C1.provenance_binding                  = 1.00
```

Private native KV:

```text
not shared raw
```

Broadcast:

```text
versioned
compact
typed
projected
```

---

# 57. LAYER 7 — C2 STRUCTURED CONTROL ORGAN

Primary candidate:

```text
Needle 3
```

Age-0 deployment:

```text
C2.primary_rung                        = 4L
C2.fallback_rung                       = 8L
C2.max_rung_lab                        = 12L
```

Nicht als runtime dynamic-depth voraussetzen; getrennte Builds okay.

Knobs:

```text
C2.route_gain                          = 0.75
C2.intent_gain                         = 0.85
C2.tool_gain                           = 0.80
C2.structured_packet_gain              = 0.90
C2.embedding_gain                      = 0.55
C2.native_confidence_gain              = 0.45

C2.control_learn_gain                  = 0.55
C2.teacher_imitation_weight            = 0.30
C2.human_feedback_weight               = 0.65
C2.real_outcome_weight                 = 0.55

C2.shadow_ratio                        = 0.90
```

Nach Fine-Tuning:

```text
native confidence
→ MUST recalibrate
```

---

# 58. LAYER 8 — C3 TINY BASIC LANGUAGE

Boot-Baseline:

```text
SmolLM2-135M-Instruct class
```

Nicht als Wissensmodell behandeln.

```text
C3.short_answer_authority              = 0.55
C3.free_language_authority             = 0.35
C3.factual_authority_without_grounding = 0.10
C3.report_surface_gain                 = 0.65

C3.native_token_budget_default         = 64
C3.native_token_budget_soft_max        = 128

C3.language_learn_gain                 = 0.30
C3.teacher_style_weight                = 0.25
C3.human_style_weight                  = 0.60
C3.fact_learning_weight                = 0.05
C3.shadow_ratio                        = 0.85
```

C3 darf gut formulieren lernen, ohne Teacher-Behauptungen automatisch als Fakten zu absorbieren.

---

# 59. LAYER 9 — C4 FOCAL / DELIBERATION

```text
C4.coalition_threshold                 = 0.45
C4.reasoning_effort_default            = 0.25
C4.reasoning_effort_conflict_gain      = 0.60
C4.reasoning_effort_uncertainty_gain   = 0.55
C4.reasoning_effort_novelty_gain       = 0.40

C4.max_cycles_age0                     = 3
C4.body_reentry_budget                 = 0.45
C4.inquisition_depth                   = 0.35
C4.verify_gain                         = 0.50
```

Escalation [BOOT]:

```text
uncertainty > 0.45
OR conflict > 0.40
→ reasoning_effort at least 0.50

epistemic-risk > 0.65
→ verify / source / human / tool strongly preferred
```

---

# 60. LAYER 10 — ATTENTION / GAIN / SALIENCE

Separate values:

```text
GAIN.perceptual                        = 0.55
GAIN.callosum                          = 0.40
GAIN.workspace                         = 0.60
GAIN.focal                             = 0.65
GAIN.action                            = 0.55
```

Salience:

```text
SAL.novelty                            = 0.35
SAL.conflict                           = 0.65
SAL.prediction_error                   = 0.55
SAL.goal_violation                     = 0.75
SAL.external_interrupt                 = 0.80
```

Cautiousness:

```text
CAUT.source_risk                       = 0.70
CAUT.B1_B2_disagreement                = 0.55
CAUT.world_surprise                    = 0.45
CAUT.router_instability                = 0.35
CAUT.teacher_dependence                = 0.25
```

Invariante:

```text
high gain != high truth
```

---

# 61. LAYER 11 — OBSERVER / WAKE POLICY

Canon:

```text
every event creates an observer OPPORTUNITY
```

Boot auf Redmi:

```text
OBS.B1_opportunity_coverage            = 1.00
OBS.B2_opportunity_coverage            = 1.00

OBS.full_B1_pass                       = 0.45
OBS.full_B2_pass                       = 0.45
OBS.cheap_or_cached_pass               = 0.40
OBS.defer_under_pressure               = 0.15
```

Die Summe ist kein Zufallsroulette, sondern Policy-Prior.

Unter guter Thermal-/RAM-Lage dürfen beide Full Observer häufiger laufen.

---

# 62. LAYER 12 — LOCAL LEARNING / ELIGIBILITY

Zwei Trace-Zeitskalen [RESEARCH BOOT]:

```text
ELIG.fast_decay_per_event              = 0.65
ELIG.slow_decay_per_event              = 0.93
ELIG.slow_mix                          = 0.25
```

Das erzeugt:

- sehr lokalen Credit,
- plus schwache längere Rückwirkung.

Detailed traces nur selektiv:

```text
ELIG.detailed_trace_rate_normal        = 0.10
ELIG.detailed_trace_rate_error         = 0.80
ELIG.detailed_trace_rate_human_feedback= 1.00
```

---

# 63. LAYER 13 — MODULATOR BUS

Epistemisch:

```text
M.epistemic.real_deterministic_outcome = 1.00
M.epistemic.primary_source             = 0.90
M.epistemic.human_correction           = 0.75
M.epistemic.verified_teacher           = 0.45
M.epistemic.internal_crosscheck        = 0.20
M.epistemic.dream                      = 0.00
```

Instrumentell:

```text
M.utility.task_success                 = 0.80
M.utility.human_preference             = 0.70
M.utility.latency_cost                 = 0.40
M.utility.energy_cost                  = 0.30
M.utility.repeated_failure             = 0.75
```

Safety:

```text
M.safety.permission_violation          = 1.00
M.safety.irreversible_action           = 0.90
M.safety.rollback_available            = -0.20 risk reduction
```

Diese Werte modulieren unterschiedliche Lernarten verschieden.

---

# 64. LAYER 14 — JEPA / PREDICTION LEARNERS

Boot relative weights:

```text
JEPA.B1_detail                         = 0.45
JEPA.B2_gist                           = 0.50
JEPA.B1_to_B2                          = 0.30
JEPA.B2_to_B1                          = 0.30
JEPA.JEF_control                       = 0.25
JEPA.workspace_state                   = 0.25
JEPA.world                             = 0.40
JEPA.teacher_student                   = 0.35
JEPA.fast_forward                      = 0.55
```

Target EMA:

```text
EMA.fast_projector_beta                = 0.995
EMA.slow_adapter_beta                  = 0.999
```

Nicht Full-Body-EMA auf Redmi.

---

# 65. LAYER 15 — ACTUAL OPTIMIZER LR [BOOT, SHADOW ONLY]

Nur für trainierbare Shadow-Slices:

```text
projectors / small heads:
1e-4 … 5e-4

control LoRA / tiny organ adapter:
5e-5 … 2e-4

B1/B2 body adapter:
2e-5 … 1e-4

selected real body slice:
1e-6 … 1e-5

full shared base:
OFF in Age 0
```

Default:

```text
A3 projector                  2e-4
C2 control adapter            1e-4
C3 language adapter           5e-5
Callosum projector            5e-5
B1/B2 adapter                 2e-5
B1/B2 shared/base             0
```

Die Werte werden nur unter Shadow/Retention verwendet.

---

# 66. LAYER 16 — FAST EPISODIC / MEMORY

```text
MEM.fast_episode_write                = 0.95
MEM.fast_episode_retrieval            = 0.75
MEM.exact_source_priority             = 1.00
MEM.semantic_staging_write            = 0.25
MEM.procedural_staging_write          = 0.40
MEM.parametric_fast_trace             = 0.00 initially
```

Second attempt:

```text
similarity high + source relevant
→ episodic cue gain up to 0.80

but:
exact same answer copy authority <= 0.20
```

System soll adaptieren, nicht kopieren.

---

# 67. LAYER 17 — REPLAY / DREAM / CONSOLIDATION

Age 0:

```text
REPLAY.real_episode_gain               = 0.70
REPLAY.old_skill_retention_gain        = 0.75
REPLAY.procedural_gain                 = 0.50
REPLAY.semantic_gain                   = 0.30
REPLAY.counterfactual_gain             = 0.20

DREAM.gain                             = 0.05
DREAM.policy_learning_gain             = 0.10
DREAM.world_model_gain                 = 0.10
DREAM.body_learning_gain               = 0.00
DREAM.fact_write_gain                  = 0.00
```

Replay sampling:

```text
recent/new                             = 0.50
protected old                          = 0.35
failure/edge cases                     = 0.15
```

Consolidation:

```text
CONSOLIDATE.min_independent_confirmations = 3 [BOOT]
CONSOLIDATE.shadow_required            = 1.00
CONSOLIDATE.retention_required         = 0.95
CONSOLIDATE.base_merge_authority_age0  = 0.00
```

---

# 68. LAYER 18 — METAPLASTICITY / HOMEOSTASIS

```text
META.stability_decay_plasticity        = 0.55
META.novelty_reopen                    = 0.45
META.repeated_failure_reopen           = 0.70
META.conflict_verify_before_learn      = 0.80
META.saturation_suppression            = 0.65
```

Homeostasis:

```text
HOME.activation_balance                = 0.30
HOME.dead_path_reopen                  = 0.30
HOME.dominant_path_inhibition          = 0.40
HOME.shared_representation_drift       = 0.75
HOME.router_collision_monitor          = 0.70
HOME.update_budget_normalization       = 0.60
```

Nicht „Experten gleich machen“.

---

# 69. LAYER 19 — REPRESENTATION ANCHOR [NEW RESEARCH KNOB]

Inspiriert durch neuere Continual-Learning-Arbeit:

```text
ANCHOR.pretrained_geometry_weight      = 0.25
ANCHOR.protected_old_skill_weight      = 0.60
ANCHOR.new_domain_relaxation           = 0.55
ANCHOR.shared_layer_priority           = 0.75
```

Bei völlig neuer Domäne:

```text
anchor ↓
```

Bei altem stabilen Skill:

```text
anchor ↑
```

Das ist kein neuer großer Body, sondern ein Stability Objective/Monitor.

---

# 70. LAYER 20 — WORLD MODEL / FAST FORWARD

Fast Forward:

```text
FF.immediate_outcome_weight            = 0.80
FF.latency_prediction                  = 0.65
FF.resource_prediction                 = 0.55
FF.side_effect_prediction              = 0.70
FF.learn_gain                          = 0.55
```

World:

```text
WORLD.next_state_prediction            = 0.55
WORLD.action_conditioning              = 0.80
WORLD.observation_prediction           = 0.55
WORLD.inverse_action_aux               = 0.20
WORLD.counterfactual_authority         = 0.20
WORLD.real_outcome_grounding           = 0.90
```

Prediction ≠ causality.

---

# 71. LAYER 21 — ACTION GATE / COROLLARY / HUMAN CONTROL

Age 0:

```text
ACTION.internal_mental_auto            = 0.70
ACTION.read_only_tool_auto             = 0.35
ACTION.reversible_external_auto        = 0.10
ACTION.irreversible_external_auto      = 0.00

ACTION.human_confirm_side_effect       = 0.95
ACTION.human_confirm_rule_change       = 1.00
ACTION.human_confirm_stage_change      = 1.00

COROLLARY.copy_strength                = 1.00
COROLLARY.expected_outcome_binding     = 0.80
```

---

# 72. LAYER 22 — PROVISIONAL vs AUTHORITATIVE EVENT STATE [NEW]

Aus Live-Systemen übernehmen:

```text
EVENT.provisional_gain                 = 0.65
EVENT.provisional_memory_write         = 0.20
EVENT.provisional_weight_learning      = 0.00

EVENT.final_gain                       = 1.00
EVENT.final_memory_write               = 0.90
EVENT.final_learning_eligibility       = 0.80
```

Wenn Event revidiert wird:

```text
invalidate provisional traces
```

statt falsche Version weiterzulernen.

---

# 72H. Provisional-State-Persistence-Hardening

## IH-H13 — PROVISIONAL Memory Write bedeutet Ephemeral Buffer [MUST]

v10.15 sagt zugleich:

```text
learning_eligible = false until FINAL
```

und

```text
EVENT.provisional_memory_write = 0.20
```

Damit kein falscher Event autoritativ erinnert wird:

```text
PROVISIONAL_MEMORY
= TTL scratch / speculative event buffer
!= Fast Episodic authoritative store
!= Semantic consolidation
!= Procedural learning
```

Bei FINAL:

```text
promote/rewrite -> authoritative Experience/Event record
```

Bei Revision:

```text
invalidate + tombstone speculative traces
```

Kein parametrisches Weight-Learning aus PROVISIONAL.

---

# 73. LAYER 23 — REDMI NOTE 10 PRO RUNTIME BUDGET

Hardware-Floor:

```text
6 GB RAM variant
Snapdragon 732G
LPDDR4X
UFS 2.2
```

Boot-Ziel:

```text
V13.weight_hot_budget                  ≈ 1.6–2.0 GB
V13.total_RSS_soft_budget              ≈ 3.0–3.4 GB
V13.total_RSS_hard_backoff             ≈ 3.8 GB
```

Diese Zahlen sind **Laborziele**, keine Garantie des OS.

Candidate weight footprint:

```text
B1 MobileMoE-S INT4                    ~0.68 GB
B2 MobileMoE-S INT4                    ~0.68 GB
C2 Needle                              ~0.01–0.03 GB
C3 tiny LM quantized                   ~0.08–0.15 GB class

pure weights total                     ~1.45–1.55 GB class
```

Rest braucht:

- runtime,
- KV/state,
- workspace,
- mmap/page cache,
- buffers,
- Android/Termux overhead.

Deshalb:

```text
B1/B2 physical scheduling = sequential first
```

---

# 74. LAYER 24 — CACHE / CONTEXT OPTIMIZATION

Start:

```text
CTX.exact_recent_pin                    = 0.80
CTX.global_compact_state                = 0.60
CTX.reconstruct_disposable_cache        = 0.40
CTX.long_context_block_index            = 0.45
CTX.prefetch_gain                       = 0.30
CTX.cache_compression_aggressiveness    = 0.35
```

Nur erhöhen, wenn Exact Recall stabil bleibt.

DeepSeek-inspiriert:

```text
global important state persist
local disposable state replay/rebuild
```

---

# 75. LAYER 25 — PROCEDURALIZATION / HABIT FORMATION

Wenn ein teurer Pfad oft erfolgreich ist:

```text
full deliberate route
→ procedural candidate
→ shadow
→ cheaper compiled policy
```

Boot:

```text
SKILL.compile_after_successes           = 5 [BOOT]
SKILL.shadow_cycles                     = 10 [BOOT]
SKILL.automatic_authority               = 0.20
SKILL.reopen_on_surprise                = 0.85
SKILL.reopen_on_failure                 = 1.00
```

Zahlen bleiben Research.

---

# 76. LAYER 26 — TEACHER RETIREMENT

Neue Capability:

```text
Teacher Active
→ Teacher Dropout
→ Student Shadow
→ Student Primary
→ Teacher Verify-only
→ Archived
```

Boot-Kriterien:

```text
student_vs_teacher_parity               >= 0.95
student_retention                       >= 0.98
source/exact behavior preserved         = required
minimum diverse validation cases        = 200 [BOOT]
```

Teacher darf bei Regression zurückkehren.

---

# 77. CROSS-LEARNING MATRIX — WER LERNT VON WEM?

| Source | Receiver | Communication | Initial learn gain | Was gelernt wird |
|---|---|---:|---:|---|
| Raw A0/A1 | A3 | 1.00 | 0.65 | native modality mapping |
| Teacher A2 | A3 | 0.70 | 0.35 | semantic alignment |
| A3 | B1 | 0.70 | 0.20 | useful fine percept conditioning |
| A3 | B2 | 0.60 | 0.20 | useful coarse/event percept conditioning |
| B1 | B2 via B3 | 0.45 | 0.25 | fine→gist useful message |
| B2 | B1 via B3 | 0.45 | 0.25 | gist→fine constraint/message |
| B1 | JEF | 0.55 | 0.25 | useful detail offers |
| B2 | JEF | 0.60 | 0.25 | useful gist offers |
| JEF | B1 | 0.50 | 0.20 | query/goal conditioning |
| JEF | B2 | 0.50 | 0.20 | query/goal conditioning |
| Fast Episodic | JEF/B1/B2 | 0.70 | 0.10 | second-attempt reuse |
| World Outcome | eligible paths | — | 0.80 modulator | grounded credit |
| Human Decision | JEF/C3/route | — | 0.65 | preference/control |
| Human correction | knowledge path | — | 0.75 epistemic | corrected knowledge candidate |
| Teacher output | C3/JEF | 0.40 | 0.25 | language/reference imitation |
| Dream | policy/world only | 0.10 | 0.05 | exploration, no facts |

Diese Matrix ist **kein finaler Learning Graph**.
Sie ist ein Startpanel für Experimente.

---

# 78. AGE-0 DEFAULT PROFILE — EINMAL ALLES ZUSAMMEN

```text
PERCEPTION
  raw integrity              ██████████ 1.00
  teacher presence           ████████░░ 0.80
  student projector learn    ███████░░░ 0.65

B1 DETAIL
  inference authority        ████████░░ 0.80
  adapter learning           ██░░░░░░░░ 0.20
  base learning              ░░░░░░░░░░ 0.00

B2 GIST
  inference authority        ████████░░ 0.85
  adapter learning           ██░░░░░░░░ 0.20
  base learning              ░░░░░░░░░░ 0.00

CALLOSUM
  communication              ████░░░░░░ 0.40
  latent authority           ██░░░░░░░░ 0.20
  learning                   ██░░░░░░░░ 0.25
  private-state protection   █████████░ 0.90

JEF C2 CONTROL
  authority                  ████████░░ 0.80
  shadow learning            ██████░░░░ 0.55

JEF C3 LANGUAGE
  authority                  █████░░░░░ 0.55
  factual authority          █░░░░░░░░░ 0.10
  language learning          ███░░░░░░░ 0.30

FOCAL / DELIBERATION
  default effort             ██░░░░░░░░ 0.25
  conflict escalation        ██████░░░░ 0.60

FAST EPISODIC
  write                      █████████░ 0.95
  retrieval                  ████████░░ 0.75

REPLAY
  real replay                ███████░░░ 0.70
  counterfactual             ██░░░░░░░░ 0.20

DREAM
  overall                    █░░░░░░░░░ 0.05
  factual write              ░░░░░░░░░░ 0.00

HUMAN CONTROL
  side-effect confirm        ██████████ 0.95
  rule/stage confirm         ██████████ 1.00

AUTONOMY
  overall                    █░░░░░░░░░ 0.10
```

---

# 79. RESEARCH ORDER — NICHT ALLES GLEICHZEITIG

## R0 Baseline

```text
JEF C2 + C3
+ explicit state
+ provenance
+ no learning
```

## R1 Split-Brain utility

```text
B1 only
B2 only
B1+B2 no callosum
B1+B2 exact/control callosum
B1+B2 latent callosum
```

## R2 Second-attempt

```text
Fast Episodic only
vs
Fast Episodic + route adaptation
vs
Fast Episodic + shadow adapter
```

## R3 JEF co-adaptation

```text
fixed wake
vs
learned wake
vs
Needle C2
vs
separate heads
```

## R4 Local learning

```text
projector/head only
→ bridge
→ adapter
→ selected body slices
```

## R5 Continual stability

```text
no anchor
vs replay
vs representation anchor
vs replay + anchor
```

## R6 Dream

Nur wenn R0–R5 funktionieren.

```text
no dream
vs counterfactual replay
vs synthetic dream
```

Wenn Dream keinen Netto-Gewinn bringt:
nicht romantisieren, abschalten.

---

# 80. WICHTIGSTE RESEARCH-HYPOTHESEN NACH DIESEM PASS

### H1
**JEF sollte eher ein Verbund aus explizitem State + sehr kleinem structured control model + optionalem tiny language organ sein als ein einzelnes 0.5–1B Chat-LLM.**

### H2
**B1/B2-Spezialisierung sollte nicht nur über Prompt-Rollen entstehen, sondern über verschiedene zeitliche Readouts, Workspace-Auflösung, Cross-Learning und lokale Objectives.**

### H3
**Callosum sollte mit Exact/Control beginnen und Latent-Kommunikation erst Authority verdienen lassen.**

### H4
**Fast Episodic Memory muss vor Base-Weight-Lernen die primäre Second-Attempt-Plasticity tragen.**

### H5
**Age 0 darf stark lernen, aber zunächst in reversiblen Komponenten.**

### H6
**Provisional/Final Event State ist für Live-/Multimodal-Lernen Pflicht, sonst lernt V13 unreife Zwischenzustände.**

### H7
**Multimodales Lernen sollte Raw+Teacher dual starten und die Teacher-Lane später durch Dropout/Parity abtrainieren.**

### H8
**Recurrent/event-driven state + sparse global retrieval könnte langfristig besonders für JEF und Gist effizienter sein als ausschließlich klassischer Transformer-KV.**

### H9
**Dreaming ist optionales Forschungselement, nicht Identitätsmerkmal. Replay und echte Outcome-Konsolidierung sind wichtiger.**

### H10
**Das Redmi-Lab sollte dieselben Hypothesen mit kleineren/sequenziellen Realisierungen testen, statt Canon nach Hardware zu verbiegen.**

---

# 81. CURRENT MODEL / ORGAN SHORTLIST — SEPTEMBER 2026

## B1/B2 Redmi Boot

### MobileMoE-S-QAT
- 272M active,
- 1.3B total,
- 60 routed experts,
- top-4,
- ~0.68 GB projected INT4 weight memory,
- on-device design.

**Vorteil:** aktuell sehr passend zur „viel Gesamtwissen, wenig aktiv“-Idee.

**Risiko:** FAIR Noncommercial Research License; Runtime auf Snapdragon 732G messen.

---

## C2 Control

### Needle 3
- 29–121M,
- 2–20 layer ladder,
- ca. 8–29 MB deployment,
- structured automation / embeddings / tools.

**Sehr starker C2-Kandidat.**

### FunctionGemma 270M
- function-calling spezialisiert,
- lokal,
- fine-tune-orientiert,
- kann Tool-Ergebnis anschließend sprachlich zusammenfassen.

**Größer, aber gute C2-Vergleichsbasis.**

---

## C3 Basic Language

### SmolLM2-135M-Instruct
- 135M,
- einfacher kleiner Decoder,
- Apache 2.0,
- primär Englisch,
- faktisch/reasoning schwach.

**Gut als Minimal-Sprachorgan-Baseline, nicht Wissenszentrum.**

---

# 81H. Needle Runtime Hardening

## IH-H32 — Needle 3 Runtime Notes [CURRENT RESEARCH HARDENING]

Needle ist weiterhin ein guter C2-Kandidat, aber Work darf nicht annehmen:

- dass C2 freie Sprache liefert,
- dass ein fine-getuntes Needle automatisch dieselbe Confidence-Kalibrierung behält,
- dass ein einzelner Prozess beliebig Base-/tuned weights hot-swappen kann,
- dass jeder Android/ARM64-Build ohne vorherigen device proof existiert.

Daher:

```text
C2 structured output contract first
C3 free-language fallback remains separate
confidence after tuning -> recalibrate / unavailable until proven
runner/device support -> capability probe
```

---

# 82. WAS DIESER RESEARCH-PASS NICHT BEHAUPTET

- Needle ist nicht automatisch der beste JEF-Control-Core.
- Zwei MobileMoE-S laufen nicht garantiert schnell genug auf dem Redmi.
- MSA/CSA2 lassen sich nicht einfach in fremde Bodies hineinpatchen.
- Gemma-4-Encoder-free bedeutet nicht, dass ein winziges Modell ohne Training Raw-Pixel versteht.
- Eligibility-Trace-Neuroscience beweist nicht V13s konkrete Lernregel.
- Dreaming ist nicht bewiesen als notwendig.
- „Brain-near“ ist keine biologische Gleichheit.
- Zahlen dieses Kapitels sind keine wissenschaftlich gemessenen Optima.

---

# 82H. Integrated Implementation Audit — Schlussurteil

## IH-H36 — Final Audit Judgment

Die V13-Architektur muss **nicht** vereinfacht oder neu erfunden werden, um baubar zu werden.

Das Hauptproblem vor Implementierung ist nicht „zu viele Ideen“, sondern die Grenze zwischen:

```text
Canon-Funktion
Research-Kandidat
Boot-Heuristik
Runtime-Annahme
Coding-Vertrag
```

Diese fünf Dinge sind im Blueprint inhaltlich meistens vorhanden, aber noch nicht überall maschinenhart voneinander getrennt.

Nach der integrierten Hardening-Schicht gilt:

- Architektur bleibt dual-hemisphärisch + JEF-System,
- Detail/Gist-Asymmetrie bleibt,
- JEPA/Eligibility/EMA/Metaplasticity bleiben,
- Age/Human Control bleibt,
- Teacher/Raw/Internalisation bleibt,
- Memory/World/Self/Dream bleiben,
- Callosum bleibt experimentell aber funktional verpflichtend/falsifizierbar,
- Redmi bleibt Labor-Floor,
- keine Mobile-Zahl wird ohne Runner-Proof als Tatsache behandelt,
- kein Learning-Update kann still aktive Gewichte überschreiben,
- kein spät eintreffender Offer kann ungeprüft alten State mutieren,
- keine Modell-Ausgabe kann den privilegierten Bedienkanal übernehmen,
- Work kann pro Feature nachweisen, ob es wirklich implementiert ist.

**Damit wird V13 nicht kleiner. Es wird schwerer, es versehentlich nur zu simulieren.**

---

# 83. v10.15 KANONISCHER ZUSATZSATZ

**Der September-2026-Research-Pass stärkt V13s bestehende Richtung, verändert aber nicht seine Funktionsidentität: aktuelle Live-Systeme sprechen für einen kleinen kontinuierlichen Executive-/Interaktionspfad mit asynchroner tieferer Verarbeitung und getrenntem provisional/final State; neue multimodale Modelle zeigen, dass schwere semantische Encoder langfristig durch leichte Projektionen und native Verarbeitung ersetzt werden können; aktuelle Sparse-/Cache-Architekturen motivieren hierarchische Context-Auswahl, gemeinsam genutzten globalen State und rekonstruierbare lokale Caches; aktuelle Continual-Learning-, Memory- und Sleep-Arbeiten stärken die Trennung von Fast Episodic, Shadow-Updates, Retention, Consolidation und Dream. Für Age 0 wird deshalb ein konservativer, reversibler Parameterzustand verwendet: starke Provenance/Fast-Memory/Human-Control, mittlere Projector-/Control-Plasticity, schwache Bridge-/Body-Adapter-Plasticity und zunächst keine B1/B2-Base-Weight-Updates. Alle numerischen Stärken sind Boot-Priors und werden layerweise durch Ablationen ersetzt, sobald echte Redmi-Messungen vorliegen.**


---

# V13 — v10.16 COMBINED NEUROSCIENCE × IMPLEMENTATION RESEARCH DELTA

**Datum:** 20.09.2026  
**Basis:** `V13_CANONICAL_BRAIN_BLUEPRINT_v10.15_INTEGRATED_WORK_READY.md`  
**Status:** Research-/Implementation-Delta; additiv; v10.15 bleibt vollständig erhalten.  
**Ziel:** Den technischen 2026-Umsetzungspass mit einem zweiten, unabhängigen Neuro-/Brain-Pass zusammenführen und daraus konkrete, falsifizierbare Implementierungsregeln für Age 0 / Redmi ableiten.

---

# 84. V10.16 GRUNDREGELN

## 84.1 Preservation

Dieser Pass darf keine gesetzte V13-Funktion still löschen.

Er darf:

1. biologische Analogien präzisieren,
2. überzogene Anatomie-Gleichsetzungen zurückstufen,
3. technische Umsetzung ändern,
4. neue Mess-/Falsifikations-Gates hinzufügen,
5. Implementationsprioritäten neu ordnen,
6. Research-Kandidaten austauschen.

Nicht erlaubt:

```text
"Das Gehirn macht X" -> V13 muss X anatomisch kopieren.
"Paper Y zeigt Z" -> Z ist automatisch V13-Canon.
"Redmi kann X heute nicht" -> X aus der Funktionsarchitektur löschen.
```

Stattdessen:

```text
biologische Funktion
    ↓
computational principle
    ↓
kleinste testbare V13-Realisierung
    ↓
Ablation gegen einfachere Alternative
    ↓
retain / replace / demote
```

## 84.2 Neue Evidenzklassen

Jede neue v10.16-Aussage wird intern einer Klasse zugeordnet:

```text
[NEURO-STRONG]      robuste funktionale Stütze aus mehreren Linien von Evidenz
[NEURO-MODERATE]    plausible, aber nicht eindeutige biologische Stütze
[NEURO-CONTESTED]   aktive Debatte / konkurrierende Modelle
[AI-STRONG]         direkte aktuelle technische Demonstration
[AI-CANDIDATE]      aktuelle Technik, aber V13-/Redmi-Proof fehlt
[ENGINEERING]       V13-Entscheid für Robustheit/Testbarkeit
[BOOT]              Startprior, keine Naturkonstante
```

## 84.3 Hirnnähe = Dynamik, nicht Organ-Cosplay

Die vorhandene v10.15-Doktrin wird verschärft:

```text
Hirnnah =
parallel + spezialisiert + rekurrent + multiskalig
+ selektive Verfügbarkeit
+ lokale aktivitätsabhängige Plasticity
+ spätes moduliertes Credit
+ fast/slow memory
+ action/outcome prediction
+ offline replay
+ homeostatic stabilization
+ Entwicklung

NICHT:
Box heißt "Thalamus" -> Box verhält sich automatisch wie Thalamus.
```

---

# 85. ZWEITER RESEARCH-PASS — WAS DAS GEHIRN FÜR V13 WIRKLICH SAGT

## 85.1 B1/B2: Zwei Zeitskalen sind gut begründet; zwei buchstäblich biologische Hemisphären nicht

### Evidenz

Neurale Verarbeitung arbeitet auf vielen intrinsischen Zeitskalen. Sensorische Bereiche integrieren typischerweise kürzer, höher-assoziative Areale länger; 2024–2026 Reviews und Datensätze stützen eine hierarchische Verteilung von Integrationsfenstern über Kortex und Forebrain.

Für Sprache/Audition gibt es zusätzlich die **Asymmetric Sampling in Time**-Literatur: linke auditive Areale zeigen im Mittel mehr kurze Integrationsfenster, rechte mehr längere. Die 2025-Neubewertung beschreibt grob Zehner-Millisekunden links versus etwa 150–300 ms rechts als relevante Hypothese. Das ist jedoch domänen- und regionsabhängig, nicht die Aussage "linkes Gehirn = Detail, rechtes Gehirn = Gist".

### V13-Folge

**[PRECISION / LOCKED FUNCTION, CHANGED INTERPRETATION]**

B1/B2 bleiben zwei komplementäre Bodies, aber ihre biologische Begründung lautet ab v10.16:

```text
B1_DETAIL = kurzer / feiner Integrationsmodus
B2_GIST   = längerer / gröberer Integrationsmodus

inspired by:
- hierarchical neural timescales
- lateralized temporal biases in some domains
- parallel specialization

NOT claimed:
- B1 = literal left hemisphere
- B2 = literal right hemisphere
```

### Implementationsänderung

Die Differenz darf nicht nur aus `1 token vs 8 tokens` bestehen.

B1/B2 sollen sich mindestens über mehrere der folgenden Dimensionen unterscheiden können:

```text
integration_horizon
segment_span
state_decay
recurrent_persistence
prediction_horizon
memory_retrieval_horizon
compression_ratio
exactness_bias
source_reentry_threshold
novelty sensitivity
update frequency
```

### Gate

`G-B-TIMESCALE-DIVERGENCE-001`

Bestehen nur, wenn B1/B2 auf einem Timescale-Testset messbar unterschiedliche, komplementäre Fehlerprofile haben und die Kombination mehr Utility liefert als zwei identische Instanzen.

Kontrollen:

```text
same-model same-policy
same-model different prompt only
shared body + dual state heads
true two-body B1/B2
```

Wenn `shared body + dual timescale state` gleich gut oder besser ist, darf die Redmi-Lab-Realisierung zeitweise diese billigere Form nutzen; der Canon-Funktionsbedarf nach komplementären Zeitskalen bleibt.

---

## 85.2 B3 Callosum: Kommunikation ist dynamisch, bidirektional und kann sowohl erleichtern als auch unterdrücken

### Evidenz

Corpus-callosum-Forschung stützt Interhemisphären-Integration, Spezialisierung und dynamische taskabhängige Lateralisierung. Neuere Reviews betonen, dass interhemisphärische Interaktionen keine statische "Datenleitung" sind. Exzitatorische Übertragung kann über lokale inhibitorische Schaltkreise effektiv unterdrückend wirken; Neuromodulation verändert Synchronie und Dominanz.

### V13-Folge

B3 darf nicht als einzelner `latent_vector_exchange()` implementiert werden.

Neue Minimalfunktion:

```text
B3_MESSAGE {
  content_channel      // LATENT | EXACT | CONTROL | SYMBOLIC | NONE
  sender_role
  receiver_role
  salience
  confidence
  signed_gain          // amplify / neutral / suppress proposal
  urgency
  temporal_scope
  source_refs
  compatibility_score
  utility_history
}
```

`signed_gain` bedeutet **keine** direkte neuronale Nachbildung. Es ist die engineering-nahe Möglichkeit, inter-body Einfluss als Verstärkung oder Dämpfung zu modellieren.

### Implementationsreihenfolge

```text
B3-0 NONE baseline
B3-1 EXACT/SOURCE pointers
B3-2 CONTROL messages
B3-3 short SYMBOLIC
B3-4 projected continuous prefix / LATENT
B3-5 learned hybrid channel policy
```

### Aktuelle AI-Brücke

Interlat (ACL 2026) zeigt vollständig latent-space Kommunikation auch zwischen heterogenen LLMs. StateBridge (Aug. 2026) zeigt eine besonders einfache training-free Variante: finale Hidden States → orthogonales Alignment → Norm-Kalibrierung → kontinuierlicher Prefix beim Empfänger.

Das macht Latent-Callosum technisch plausibler, aber nicht automatisch besser.

### Gate

`G-CALLOSUM-UTILITY-002`

LATENT darf nur ACTIVE werden, wenn es gegen `NONE`, `EXACT`, `CONTROL` und `SYMBOLIC` gewinnt auf:

```text
task utility
latency
bytes transferred
receiver OOD
source faithfulness
role retention
interference
restart reproducibility
```

---

## 85.3 B4/C4 Focal Coalition: begrenzte globale Verfügbarkeit ja; "das ist Bewusstsein" nein

### Evidenz

Global-Workspace-/Global-Neuronal-Workspace-Ansätze bleiben ein wichtiger Rahmen für selektive globale Verfügbarkeit, aber ein großes preregistriertes Nature-Adversarial-Experiment 2025 stellte zentrale Vorhersagen sowohl von GNWT als auch IIT in Frage. 2026-Diskussionen betonen zusätzlich, dass GNW auf mehreren biologischen Ebenen verstanden wird und nicht einfach mit einer Software-Message-Bus-Metapher gleichgesetzt werden sollte.

Working-Memory-Forschung unterstützt zudem nicht genau **einen** Speichermechanismus. Persistente Aktivität, dynamische Population Codes, intermittierende Aktivität, episodisches Retrieval und schnelle synaptische Mechanismen können je nach Aufgabe beitragen.

### V13-Folge

`FOCAL_COALITION_STATE` bleibt, aber wird funktional definiert:

```text
FOCAL_COALITION_STATE =
  kleine, priorisierte Menge aktuell handlungs-/report-/reentry-relevanter Inhalte,
  die über mehrere V13-Subsysteme hinweg gegenseitig lesbar wird.
```

Nicht Canon:

```text
"FOCAL_COALITION_STATE = Bewusstsein bewiesen"
"B4 muss immer N feste Slots haben"
"persistent KV = working memory"
```

### Neue Hybrid-Realisierung

B4 darf drei Zustandsarten kombinieren:

```text
ACTIVE_STATE
- aktuell aktiv / rekurrent / KV-nah

REACTIVATABLE_STATE
- compact keyed state, schnell ping/retrieve-fähig

EPISODIC_POINTER
- Source-/Experience-gebundener Restore-Pointer
```

C4 koordiniert Admission, Binding, Refresh und Re-entry; es ist nicht selbst der gesamte State.

### Gate

`G-FOCAL-CAPACITY-003`

Muss funktional zeigen:

```text
capacity limit
competition
priority replacement
salience interrupt
re-entry
source binding
unattended retention/recovery
```

und gegen einfaches "alles in Context hängen" gewinnen.

---

## 85.4 JEF: Das Gehirn spricht gegen einen einzigen Chef und für gekoppelte Executive-Schleifen

### Evidenz

Executive Control wird nicht nur PFC zugeschrieben. Mediodorsaler Thalamus beeinflusst PFC-Netzwerke, Unsicherheit, Flexibilität und Strategy Arbitration. Basalganglien, PFC und Thalamus bilden rekurrente Schleifen; kognitive Kontrolle, Arbeitsgedächtnis, Handlungswahl und gelerntes Gating verteilen sich über diese Systeme.

### V13-Folge

Die bestehende Definition wird **gestärkt**:

```text
JEF != master brain
JEF != one Judge LLM
JEF != only route through cognition
```

JEF bleibt die **körper-/handlungsnahe Executive- und Report-Schnittstelle** mit einem autorisierten äußeren Intent-Stream.

Lokale B1/B2/Memory/Skill/Salience-Prozesse dürfen weiterhin ohne JEF-Full-Forward arbeiten.

### Neue interne Aufteilung

```text
C1 EXECUTIVE STATE        ~ task/goal/constraint continuity
C2 STRUCTURED CONTROL     ~ language -> typed control
C3 FREE LANGUAGE          ~ cheap report surface
C4 FOCAL BINDER           ~ dynamic coalition/re-entry
C5 ACTION/REPORT GATE     ~ candidate selection + permission authority
```

Biologisch inspirierte Zusatzregel:

**Uncertainty erhöht nicht nur "mehr Denken", sondern darf gezielt die Kopplung zwischen Executive State, B1/B2 und Memory erhöhen.**

Neuer Knob:

```text
C4.uncertainty_coupling_gain
```

---

## 85.5 C5 / Action Gate: Basalganglien-Analogie ist brauchbar, aber nicht als simples Go/No-Go

### Evidenz

Basalganglien werden mit Action Selection, Reinforcement, Initiation, Habit und Cost/Benefit in Verbindung gebracht. Neuere Arbeiten zeigen jedoch, dass direkte/indirekte Pfade nicht sauber auf eine einzige "Go/No-Go"-Logik reduziert werden können; striatale Signale sind kontext- und lernabhängig. Dopamin trägt neben klassischen Reward Prediction Errors auch reichere, teilweise value-freie Action-/Feature-Teaching-Signale.

### V13-Folge

C5 erhält keine biologisch naive `GO_LOGIT`-Implementierung.

Stattdessen:

```text
ACTION_CANDIDATE {
  action_id
  expected_utility
  expected_cost
  confidence
  reversibility
  evidence
  permission_class
  novelty
  uncertainty
  habit_strength
  focal_support
}

C5:
  candidate competition
  suppression / defer / ask / execute
  alternate-action availability
  permission gate
  corollary dispatch
```

### Learning

Action-Learning bekommt getrennte Modulatoren:

```text
reward_error
cost_error
action_prediction_error
rule_violation
human_correction
world_mismatch
```

Nicht alles wird in einen scalar reward gepresst.

---

## 85.6 Cerebellum/Fast-Forward: V13s Proceduralization wird durch aktuelle Forschung deutlich gestärkt

### Evidenz

2025 Nature Reviews Neuroscience beschreibt das Cerebellum als überwiegend feedforward spezialisiertes System und bewertet Evidenz für gelernte schnelle assoziative Control Policies. 2026-Reviews betonen cerebelläre Beiträge zu Prediction, Error Correction, Learning und Internal Model Updating über mehrere Zeitskalen.

### V13-Folge

`FAST_FORWARD / CEREBELLAR` soll **kein weiterer Foundation-Body** werden.

Es ist am besten realisiert als kleine, billige, spezialisierte Vorhersage-/Policy-Schicht:

```text
expensive successful recurrent route
        ↓ repeated validated success
trajectory / state-action distillation
        ↓
small compiled predictor/policy
        ↓ SHADOW
cheap automatic proposal
        ↓
reopen to focal loop on surprise/failure
```

Das passt direkt zu V13s Proceduralization/Habit-Pfad.

### Gate

`G-PROCEDURALIZATION-004`

Compiled skill muss:

```text
latency↓
energy↓
accuracy noninferior
reopen-on-error preserved
source/rule constraints preserved
```

sonst bleibt deliberative Route.

---

## 85.7 Corollary / Efference Copy: einer der stärksten biologischen Anker in V13

### Evidenz

Corollary discharge/efference copy ist breit belegt: Kopien eigener Motor-/Action-Signale helfen, selbstverursachte sensorische Folgen von externen Veränderungen zu unterscheiden. Neuere Arbeiten zeigen verteilte thalamisch-kortikale Corollary-Architekturen; Meta-Analysen stützen sensorische Abschwächung bei selbstgenerierten Reizen.

### V13-Folge

Der bestehende LOCKED-Punkt bleibt und wird technisch härter:

**Jede reale externe Aktion muss vor Dispatch einen `COROLLARY_PACKET` erzeugen.**

```text
COROLLARY_PACKET {
  action_id
  issued_at
  intended_effect
  predicted_observations[]
  affected_sources/body_ports[]
  uncertainty
  causal_hypothesis
  expected_cost
  permission_snapshot
}
```

Nach Outcome:

```text
actual observation
- predicted self-caused component
= residual / external mismatch candidate
```

Das World/Self-System lernt aus der Differenz.

### Gate

`G-SELF-WORLD-005`

Tests:

```text
same external event, no self action
same observation following self action
partial action failure
delayed outcome
unexpected side-effect
ambiguous causality
```

---

## 85.8 Memory: Fast Episodic + Slow Parametric ist eine der besten V13-Entscheidungen

### Evidenz

Complementary Learning Systems (CLS) liefert seit langem eine rechnerische Begründung für schnelles episodisches Lernen und langsameres verteiltes Lernen. 2024–2026 Arbeiten verfeinern das Bild: selbst der Hippocampus enthält unterschiedliche Pfade für sehr schnelles episodisches Lernen und schnellere Regularitäts-/Strukturextraktion. Replay unterstützt die spätere Integration.

### V13-Folge

`Second-Attempt Advantage` darf **explizit zuerst über episodisches Gedächtnis** entstehen.

```text
first encounter
→ exact + episodic trace
→ correction/outcome
→ fast retrieval binding
→ second attempt improvement
```

Kein Requirement:

```text
second attempt better => body weights mussten schon geändert werden
```

Parametrische Konsolidierung kommt später.

### Neue Memory-Ladder

```text
M0 exact source/event record
M1 episodic association
M2 compact reusable pattern candidate
M3 semantic/procedural candidate
M4 reversible parametric delta
M5 selected body consolidation
```

Jede Stufe braucht eigene Evidence/Retention-Regeln.

---

## 85.9 Replay ist biologisch stark; Dream als Pflichtmechanismus nicht

### Evidenz

2025/2026 Forschung stützt hippocampales Replay während Ruhe und Schlaf sowie Koordination mit hippocampo-kortikaler Konsolidierung. 2026 Neuron-Daten zeigen, dass bestimmte große Sharp-Wave-Ripples mit hippocampaler und präfrontaler Reaktivierung zusammenhängen und experimentelles Boosting Reaktivierung steigern kann. 2026 Current Biology zeigt umgekehrt, dass Störung von Ripples mit schlechterer Konsolidierung einhergeht.

Aber: "Dreaming" als eigenständiger notwendiger Lernalgorithmus ist wesentlich schlechter belegt. Replay kann vergangene Episoden priorisieren und auch hypothetische/fiktive Sequenzen enthalten, ohne dass daraus folgt, dass freie Traumgenerierung direkt Fakten lernen sollte.

### V13-Folge

Die vorhandene Trennung wird verbindlicher:

```text
SLEEP_A = evidence-bound replay / consolidation
SLEEP_B = counterfactual / abstraction / recombination
SLEEP_C = homeostasis / cleanup / recalibration
```

Neue Regel:

```text
SLEEP_A darf Konsolidierungsautorität besitzen.
SLEEP_B besitzt standardmäßig KEINE Fact Authority.
SLEEP_C verändert Stabilitäts-/Plasticity-Regler, nicht Wissenswahrheit.
```

### Priorisierung

Replay ist nicht uniform random:

```text
priority = f(
  surprise,
  correction,
  unresolved error,
  future relevance,
  novelty,
  source quality,
  retention risk,
  user importance
)
```

Aber ein hoher Surprise allein darf keinen Fakt autoritativ machen.

---

## 85.10 Eligibility + spätere Modulation: stark gestützt, aber der dritte Faktor ist kein einzelner Reward-Skalar

### Evidenz

Eligibility Traces sind ein etablierter Kandidat, um lokal aktive Synapsen über Sekunden für spätere Modulation "markiert" zu halten. 2025 Reviews führen neue Evidenz zusammen. Dopamin-Forschung 2025 zeigt zudem, dass Teaching-Signale über klassischen Reward hinausgehen und u. a. Feature- oder Action-Prediction-Information tragen können.

### V13-Folge

Die alte intuitive Formel

```text
Δθ_i ∝ e_i · δ_i · m
```

bleibt als Struktur, aber `m` wird **typisiert und vektoriell**.

```text
MODULATOR_PACKET {
  experience_id
  reward_error
  action_error
  world_prediction_error
  evidence_gain
  human_correction
  surprise
  cost_error
  rule_violation
  abstention_quality
  confidence_calibration_error
  source_quality
}
```

Jeder Lernpfad besitzt `ModulatorWeights`.

Beispiel:

```text
B1 factual/detail update:
  source_quality high
  evidence_gain high
  human correction high
  raw reward low

C5 route/action policy:
  outcome/action_error high
  cost high
  rule_violation hard gate

A3 perceptual projector:
  reconstruction/alignment/world mismatch high
```

### Wichtige technische Präzision

Eligibility ersetzt nicht automatisch echte lokale Gradienten.

Start:

```text
exact local gradient
× eligibility/activity mask
× typed modulator
× plasticity state
× norm/update cap
```

Biologisch inspirierte gradient-free Regeln bleiben Research-Ablation.

---

## 85.11 Metaplasticity + Homeostasis: V13 liegt hier sehr richtig

### Evidenz

Hebb-artige Plasticity allein ist potentiell instabil. Homeostatic Plasticity und Metaplasticity werden seit langem als Mechanismen verstanden, Aktivität und Lernbereitschaft in brauchbaren Bereichen zu halten. Neuere Literatur behandelt weiter die Bedeutung verschiedener Zeitkonstanten und entwicklungsabhängiger Stabilisierung.

### V13-Folge

Keine Änderung am Grundprinzip; Implementation wird präzisiert:

```text
FAST state:
eligibility / recent error / temporary trace

MEDIUM state:
plasticity gain / route bias / adapter stability

SLOW state:
consolidation / metaplasticity / homeostatic target
```

Homeostasis darf Spezialisierung nicht plattmachen.

Für MoE:

```text
wrong: force uniform expert use
right: detect pathological starvation, saturation, route collapse, shared-layer drift
```

---

## 85.12 Age: biologisch sinnvoll als Entwicklungs-Hülle, aber die 0..5-Stufen sind Engineering

### Evidenz

Neuroentwicklung zeigt sensitive/critical periods, Pruning, Inhibitionsreifung und langgezogene Reorganisation höherer Assoziations-/PFC-Systeme. 2025 Reviews betonen **hierarchische** kritische Perioden: verschiedene Systeme öffnen/schließen Plasticity-Fenster zu unterschiedlichen Zeiten. Adoleszenz ist kein einzelner Schalter.

### V13-Folge

Die bestehende Struktur ist überraschend gut:

```text
SYSTEM_STAGE 0..5         = human/operator envelope
CAPABILITY_STAGE 0..5     = capability-specific coarse maturity
CONTINUOUS_MATURITY       = actual continuous control state
```

Biologische Präzision:

```text
Stage 0..5 != menschliche Lebensalter
Age rise != automatisch mehr Rechte
maturity != autonomy
plasticity != permission
```

`user_stage_cap` bleibt **über** biologischer Inspiration.

### Neue Maturity-Dimensionen

```text
maturity.retention
maturity.calibration
maturity.teacher_independence
maturity.error_recovery
maturity.route_stability
maturity.source_grounding
maturity.action_reversibility
maturity.plasticity_stability
maturity.self_monitoring
```

Eine Capability darf z. B. sprachlich reif, aber toolseitig unreif sein.

### Plasticity windows

Age soll nicht nur monoton Plasticity senken.

```text
new domain / new modality
→ local plasticity window can reopen

stable mature skill
→ plasticity narrows

repeated failure
→ bounded reopen
```

Das ist näher an sensitiven Perioden und Metaplasticity als "älter = überall weniger Lernen".

---

## 85.13 Predictive Processing / JEPA: funktional verwandt, aber nicht gleichsetzen

### Evidenz

Predictive processing, active inference und interne Vorwärtsmodelle sind einflussreiche Gehirnmodelle, aber nicht in allen Details empirisch entschieden. 2026 Reviews fordern explizit Theorie-vergleichende Tests statt pauschaler Bestätigung. Sensorimotorische Prediction/Efference-Copy ist stärker belegt als die Behauptung, der gesamte Kortex implementiere exakt einen bestimmten mathematischen Free-Energy-Algorithmus.

### V13-Folge

JEPA bleibt eine **AI-Lerntechnik**, nicht "der Algorithmus des Gehirns".

Biologische Brücke:

```text
predict future/hidden state
compare predicted vs observed
learn useful representations
condition on action
separate self-caused vs external outcomes
```

### Implementationsregel

Age 0:

```text
B state -> small predictor -> future/paired target
                         ↑
                    stop-grad / EMA

body initially frozen or near-frozen
predictor learns first
```

Erst wenn Prediction Error echte Utility hat, darf sein Credit tiefer in Projector/Adapter/Expert-Deltas gelangen.

---

# 86. TECHNISCHER PASS × HIRN-PASS — GEMEINSAME ARCHITEKTUR

## 86.1 Das neue Gesamtbild

```text
WORLD / USER / BODY
        ↕
A-PLANE: source-preserving perception
        ↕
B1_DETAIL       ↔ B3_DYNAMIC_CALLOSUM ↔       B2_GIST
short/fine                                     long/coarse
      ↘              B4 DISTRIBUTED STATE             ↙
                       ↕
              C4 FOCAL COALITION BINDER
                       ↕
C1 EXEC STATE ↔ C2 CONTROL ↔ C3 LANGUAGE
                       ↕
                 C5 ACTION/REPORT GATE
                       ↓
               C6/C7 EFFECTORS / TOOLS
                       ↓
                     WORLD

Cross-cutting:
F1 gain/attention
F2 salience/interrupt
F3 memory/self/world
F4 local learning + typed modulation
F5 Age/human control
F6 provenance/rules
F7 runtime/resources
F8 replay/consolidation/homeostasis
```

Wichtig:

- keine serielle Pflichtpipeline,
- kein einzelner "PFC/JEF Chef",
- kein Bewusstseinsclaim,
- Memory bleibt getrennt von Workspace,
- Action authority bleibt zentralisiert für Sicherheit/Permissions, kognitive Bewertung nicht.

---

# 87. MODEL-/RUNTIME-STACK — AKTUELLER AGE-0-KANDIDAT

## 87.1 B1/B2

**Primary research candidate:** `facebook/MobileMoE-S-QAT`

Aktuelle veröffentlichte Eckdaten:

```text
272M active
1.3B total
20 layers
60 routed experts
top-4
768 model dim
projected INT4 weight memory ~0.68 GB
license: FAIR Noncommercial Research License
```

Zwei Bodies:

```text
~2.6B total parameters
~544M active parameters per token-path combined, before JEF
projected pure INT4 weights ~1.36 GB
```

Das trifft V13s gewünschte Sparse-Größenordnung sehr gut.

**Aber:** projected weight memory != real process RSS.

Status bleibt:

```text
MODEL = strong candidate
REDMI RUNNER PROOF = required
```

## 87.2 C2 Structured Control

**Primary candidate:** Needle 3 class.

Aktuell:

```text
29–121M
2–20 layer deployable ladder
CQ2 binaries ~9–29 MB class
structured extraction
tool calling
embeddings
grammar-constrained output
base-model confidence head
```

Wichtige Hardening-Regel bleibt:

```text
fine-tuned Needle -> confidence unavailable / recalibrate before authority
```

C2 darf nicht als General-Chat-LM vorausgesetzt werden.

## 87.3 C3 Basic Free Language

Neue v10.16-Vergleichsbasis:

```text
SmolLM2-135M-Instruct
vs
LFM2.5-230M QAD Q4_0 GGUF
```

LFM2.5-230M besitzt aktuell offizielle GGUF/QAD-Q4_0-Varianten; die 4-bit-Datei liegt grob im 149-MB-Bereich und läuft über llama.cpp.

C3 bleibt on-demand/hot nach Messung.

## 87.4 Runner

Nicht eine Runtime erzwingen.

```text
RunnerRegistry
 ├─ NeedleRunner       C2
 ├─ LlamaCppRunner     C3 / compatible harness bodies
 ├─ ExecuTorchRunner   MobileMoE / future V13-native bodies
 └─ TrainRunner        isolated shadow learning
```

ExecuTorch Android unterstützt aktuell u. a.:

```text
XNNPACK CPU
Vulkan GPU
Qualcomm AI Engine / QNN
MediaTek NeuroPilot
Arm VGF
Samsung Exynos backend
```

**Age-0 Redmi rule:** XNNPACK first for proof; hardware acceleration only after exact target-device benchmark.

## 87.5 Termux

```text
Termux = Age-0 lab shell + operator UI
not = architecture
```

Hot kernels native. Python darf koordinieren.

Spätere App-Realisierung darf denselben V13-Core hinter Android/NDK/Service-Shell verwenden.

---

# 88. NEUER LEARNING LADDER — HIRNNÄHER UND UMSETZBARER

## 88.1 Learning Authority Levels

```text
L0  RECORD_ONLY
    exact event/source/outcome

L1  FAST_MEMORY
    episodic associations / retrieval keys

L2  CALIBRATION
    confidence, route statistics, thresholds

L3  SMALL_LOCAL_HEADS
    predictors, projectors, policy/readout heads

L4  REVERSIBLE_DELTA
    LoRA / isolated adapter / expert delta

L5  SELECTED_BODY_SLICE
    selected active experts/shared components under strict gates

L6  BASE_CONSOLIDATION
    rare, explicit, retention-tested
```

Age 0 default:

```text
L0 ACTIVE
L1 ACTIVE
L2 ACTIVE/SHADOW
L3 SHADOW -> approved
L4 SHADOW only by default
L5 experimental
L6 off
```

## 88.2 Why

Diese Reihenfolge verbindet:

- CLS fast/slow learning,
- eligibility + late modulation,
- mobile memory limits,
- rollback,
- catastrophic forgetting protection,
- second-attempt improvement without requiring immediate body rewrite.

---

# 89. TRAIN_RUNNER_PROOF — NEUER BLOCKER

Der bestehende `RUNNER_PROOF` reicht für Inferenz, aber nicht Lernen.

Vor produktivem On-device Weight Update muss pro TrainPath gemessen werden:

```text
TRAIN_RUNNER_PROOF {
  model_revision
  train_runner_revision
  trainable_parameter_count
  frozen_parameter_count
  optimizer
  master_precision
  inference_quant_format
  gradient_method
  recompute_policy

  forward_peak_rss_pss
  backward_peak_rss_pss
  optimizer_peak_rss_pss
  checkpoint_peak_rss_pss

  activation_bytes
  optimizer_state_bytes
  master_weight_bytes
  delta_bytes

  step_latency_ms
  examples_per_step
  energy_delta
  battery_delta
  thermal_headroom_start/end
  throttle_events

  gradient_reference_test
  deterministic_seed_test
  cancel_during_forward
  cancel_during_backward
  crash_during_checkpoint
  resume_correctness
  rollback_correctness
  retention_suite_before_after
}
```

Gate:

`G-TRAIN-RUNNER-PROOF-001`

Kein `APPROVED_COMMIT` ohne grünen Proof für **genau** den trainierten Parameterpfad.

---

# 90. ON-DEVICE TRAINING — AKTUELLER STAND

MeSP (ACL 2026) zeigt, dass mathematisch exakte LoRA-Gradienten auf mobilen Geräten mit deutlich reduziertem Peak-Memory möglich sind. Berichtete Qwen2.5-Experimente (0.5B–3B) reduzieren Peak-Memory im Mittel um 49 % gegenüber der verglichenen memory-efficient Backprop-Baseline; beim 0.5B-Modell sank ein gemessener Peak von 361 MB auf 136 MB.

V13-Folge:

```text
on-device exact small-delta training = credible
full body training on Redmi = not established
```

Daher:

```text
small local delta first
recompute where useful
real gradient reference test
quantized inference weights != optimizer master
```

---

# 91. MOE LEARNING HARDENING

MobileMoE passt architektonisch, aber sparse routing schützt nicht automatisch vor Forgetting.

Neue verpflichtende Update-Reihenfolge:

```text
PHASE A
router frozen
shared trunk frozen
small predictor/projector/delta only

PHASE B
active expert delta shadow
route-distribution monitor
old-task retention

PHASE C
selected router adaptation shadow
only if missed-routing evidence exists

PHASE D
selected shared component update
rare; only if pre-router bottleneck proven
```

Monitor:

```text
expert_usage_distribution
route_entropy
route_collision
old_task_route_shift
shared_representation_drift
expert_delta_norm
router_delta_norm
pre_router_drift
```

Keine Regel "getroffener Expert = automatisch Weight Update".

Aktivierung erzeugt Eligibility; Commit braucht Error + typed modulator + permission + retention.

---

# 92. JEPA / PREDICTION IMPLEMENTATION

## 92.1 Predictor-first

Age-0 Body Learning startet so:

```text
state_t
   ↓
small predictor
   ↓
predicted target_{t+k}

EMA/stop-grad target state_{t+k}
   ↓
local latent prediction error
```

Trainierbar zuerst:

```text
predictor
projection/readout
optional tiny delta
```

Nicht sofort:

```text
all body weights
router
all experts
```

## 92.2 Action-conditioned world prediction

World predictor bekommt:

```text
state_t
action_intent
corollary packet
context
   ↓
predicted observation / latent state / cost
```

Nach Outcome:

```text
actual - predicted
→ world error
→ self/world causal update
→ action-policy modulator
```

## 92.3 Prediction objective registry

Jeder Loss bekommt ID/Version:

```text
OBJ-B1-FUTURE-LATENT-v1
OBJ-B2-GIST-FUTURE-v1
OBJ-B3-CROSS-UTILITY-v1
OBJ-WORLD-ACTION-v1
OBJ-C-ROUTE-CALIB-v1
```

Keine namenlose "JEPA loss" im Code.

---

# 93. FOCAL STATE — NEUE HYBRID-SCHEMA

```text
FOCAL_ITEM {
  item_id
  source_kind
  source_ref
  payload_ref
  active_representation?
  reactivation_key?
  confidence
  salience
  uncertainty
  age_ms
  decay
  bound_goal_ids[]
  fact_hypothesis_status
  provenance
}
```

State-Typen:

```text
ACTIVE
REACTIVATABLE
EPISODIC_POINTER
```

Admission:

```text
priority =
  goal relevance
+ conflict
+ uncertainty
+ salience
+ expected utility
+ source quality
- redundancy
- cost
```

Die Formel ist eine Policy-Struktur, kein fester linearer Endwert.

---

# 94. REPLAY / SLEEP IMPLEMENTATION

## 94.1 ReplayQueue

```text
REPLAY_ITEM {
  experience_id
  replay_type
  priority
  evidence_class
  unresolved_errors[]
  affected_paths[]
  max_authority
  ttl
  source_refs[]
}
```

Typen:

```text
EPISODIC
PROCEDURAL
SEMANTIC
COUNTERFACTUAL
RETENTION_PROBE
```

## 94.2 Sleep A

```text
real replay
interleaving old + new
retention tests
candidate consolidation
```

## 94.3 Sleep B

```text
counterfactual generation
route alternatives
skill recombination
world hypotheses
```

Default:

```text
fact_write_authority = 0
```

## 94.4 Sleep C

```text
trace decay
homeostatic gains
plasticity recalibration
stale delta cleanup
index rebuild
resource compaction
```

## 94.5 Wake replay

Kurze Idle-/Pause-Fenster dürfen hochpriorisierte Episoden reaktivieren. Sie dürfen User-Response-Governor niemals blockieren.

---

# 95. AGE / DEVELOPMENT IMPLEMENTATION

## 95.1 Drei Ebenen bleiben

```text
SYSTEM_STAGE
CAPABILITY_STAGE
CONTINUOUS_MATURITY
```

## 95.2 Neue Regel: Rechte und Reife sind orthogonal

```text
capability_maturity high
!=
autonomy permission high
```

Final authority:

```text
allowed =
  hard_rules
∩ user_permissions
∩ user_stage_cap
∩ system_stage
∩ capability_stage
∩ current_resource_state
```

Maturity beeinflusst innerhalb des erlaubten Bereichs nur Stärke/Budget.

## 95.3 Reopenable plasticity

```text
mature stable domain -> lower plasticity
novel domain -> local reopen
repeated error -> bounded reopen
new modality -> new sensitive window
```

Kein globales "Age 5 = alles frei und kaum lernfähig".

---

# 96. CURRENT BUILD ORDER — V10.16

Der v10.15 STEP-0→11-Plan bleibt. Innerhalb davon wird die technische Reihenfolge verschärft.

## STEP 0 — Runtime substrate

MUSS fertig sein:

```text
schema registry
IDs / SourceRef semantics
SQLite WAL + blob store
migrations
active-generation manifest
operator command parser
bounded queues
cancellation
response governor
resource / thermal monitor
model manifest
runner registry
logging rotation
:doctor
completion ledger
```

## STEP 1 — JEF vertical slice

Real, keine Mocks:

```text
C1 executive state
C2 Needle-class structured path
C3 SmolLM2 vs LFM2.5 benchmark
C5 report broker
persistent chat/session
restart
cancel
```

Exit:

```text
real model outputs
persistent state
telemetry
no B dependency
```

## STEP 2 — Split-brain observer

```text
B1/B2 real BodyPort
sequential physical scheduling allowed
fine/coarse preprocessing/state policy
OFFER_PACKET
NONE/EXACT/CONTROL channels
no latent injection yet
```

Exit:

```text
measurable complementarity
bounded RSS
observer latency known
```

## STEP 3 — Fast Memory / second attempt

```text
exact event
human correction
fast episodic association
restart test
negative transfer test
```

Exit:

Second attempt improves without weight update.

## STEP 4 — Reference Teacher

Unchanged principle:

```text
SELF_CANDIDATE first
REFERENCE separate
HUMAN/REAL outcome authority
```

## STEP 5 — JEF / small-head Shadow Learning

Add:

```text
TRAIN_RUNNER_PROOF
ModulatorPacket
Eligibility/activity traces
shadow generation
atomic candidate commit
```

## STEP 6A — Callosum channels

```text
NONE
EXACT
CONTROL
SYMBOLIC
```

## STEP 6B — Latent bridge

Start with simplest viable continuous-prefix alignment before invasive layer-by-layer injection.

Candidates:

```text
trained low-rank projector
orthogonal StateBridge-style alignment
receiver norm calibration
vocabulary anchoring where meaningful
```

## STEP 6C — B learning

```text
predictors
projectors
active expert deltas
router frozen initially
```

## STEP 7 — Stability epoch

Weeks / large session set:

```text
retention
second attempt
teacher on/off
rollback
thermal drift
restart
long-run route stability
no silent corruption
```

Only then modalities/Age >0.

---

# 97. REDMI-SPECIFIC EXECUTION POLICY

## 97.1 Initial physical scheduling

Functional parallelism does not require simultaneous residency/forward.

Default candidate:

```text
JEF hot
B1/B2 mapped/on-demand
observer scheduling sequential or sampled
C3 hot/on-demand depending RSS
shadow learner separate and idle-only
```

## 97.2 Resource modes

```text
GREEN
normal observer coverage

YELLOW
reduce observer depth / context / replay

ORANGE
single-body observer + JEF
pause shadow learning

RED
JEF safe path only
no replay/no learning
preserve response governor/rules/provenance/cancel
```

Thresholds measured on device, not hardcoded from desktop numbers.

## 97.3 Runner proof

MobileMoE is production candidate only after exact Redmi measurement of:

```text
packed quantization retained?
RSS/PSS
page faults
KV slope
TTFT
observer latency
decode speed
thermal drift
unload/reload
layer taps
latent injection capability
```

---

# 98. WHAT BECOMES MORE BRAIN-LIKE AFTER V10.16

## Stronger

```text
B1/B2 = complementary timescale regimes, not cartoon hemispheres
B3 = dynamic influence/gain, not one data pipe
JEF = coupled executive interface, not central brain
B4/C4 = hybrid distributed/focal state
C5 = candidate competition + gating, not single judge scalar
Corollary = mandatory pre-action prediction packet
FastForward = procedural compiled predictor/policy
Memory = fast episode first, slow consolidation later
Eligibility = local activity trace + typed late modulators
Sleep = replay/consolidation separated from dream
Age = capability-specific sensitive windows under human cap
```

## Less biologically literal on purpose

```text
Transformer attention != biological attention
MoE expert != cortical column
JEPA != proven cortical algorithm
KV cache != working memory neuron-for-neuron
Stage 0..5 != childhood/adolescence/adulthood mapping
JEF != prefrontal cortex
B3 != anatomical corpus callosum simulation
```

This is intentional. Functional equivalence beats decorative anatomy.

---

# 99. CRITICAL ABLATIONS — MUST EXIST BEFORE CLAIMING V13 MECHANISMS WORK

| Hypothesis | Preferred V13 mechanism | Required controls |
|---|---|---|
| Fine/Gist split helps | dual timescale B1/B2 | identical policies; shared-body dual state; single body |
| Callosum helps | adaptive hybrid B3 | no-message; exact; symbolic; latent |
| Focal coalition helps | bounded hybrid B4/C4 | full context only; retrieval only; fixed slots |
| Episodic fast memory helps | Experience retrieval | response cache; no memory; param delta only |
| JEPA predictor helps | latent predictor | supervised readout; next-token-like probe; no predictor |
| Eligibility helps | activity trace gating | gradient only; random mask; recency only |
| Typed modulators help | vector modulators | scalar reward; human-only; outcome-only |
| Dream helps | counterfactual Sleep B | no dream; replay only; dream no writes; dream policy-only |
| Proceduralization helps | FastForward compiled skill | full deliberation; static shortcut |
| Age helps stability | stage+continuous maturity | fixed conservative; fixed permissive |
| Two bodies worth mobile cost | B1+B2 | shared body + two states; one body |

No positive result may be claimed from a benchmark that allows response caching to fake learning.

---

# 100. NEW GATES FOR WORK

```text
G-B-TIMESCALE-DIVERGENCE-001
G-CALLOSUM-UTILITY-002
G-FOCAL-CAPACITY-003
G-PROCEDURALIZATION-004
G-SELF-WORLD-005
G-TRAIN-RUNNER-PROOF-001
G-REPLAY-CONSOLIDATION-001
G-MODULATOR-SPECIFICITY-001
G-AGE-REOPEN-001
G-MOBILE-LONGRUN-001
```

A Gate is green only with:

```text
CODE
REAL STATE PATH
PERSISTENCE/RESTART where relevant
TEST
TELEMETRY
ABLATION BASELINE
KNOWN LIMITATIONS
```

---

# 101. NEW MACHINE-READABLE SCHEMAS

## 101.1 `ModulatorPacket`

```yaml
schema_id: SCHEMA-MODULATOR-PACKET-001
fields:
  experience_id: required
  reward_error: optional_float
  action_error: optional_float
  world_prediction_error: optional_float
  evidence_gain: optional_float
  human_correction: optional_float
  surprise: optional_float
  cost_error: optional_float
  rule_violation: optional_float
  calibration_error: optional_float
  source_quality: optional_float
  finality: PROVISIONAL|FINAL
```

## 101.2 `CorollaryPacket`

```yaml
schema_id: SCHEMA-COROLLARY-PACKET-001
fields:
  action_id: required
  intent_id: required
  issued_at: required
  intended_effect: required
  predicted_observations: list
  uncertainty: float
  expected_cost: optional
  permission_snapshot: required
  affected_ports: list
```

## 101.3 `TrainRunnerProof`

Machine serialization of §89.

## 101.4 `FocalItem`

Machine serialization of §93.

## 101.5 `ReplayItem`

Machine serialization of §94.

---

# 102. UPDATED COMPLETION LEDGER FIELDS

Add to v10.15 ledger:

```text
neuro_inspiration_class
neuro_claim_limit
ablation_baseline
train_runner_proof_id
modulator_schema
eligibility_owner
corollary_required
replay_authority
age_window_policy
redmi_longrun_proof
```

This prevents "brain-inspired" from becoming an untestable label.

---

# 103. V10.16 FINAL ARCHITECTURE JUDGMENT

After the independent brain pass and the implementation pass, V13 should **not** be collapsed into a normal multi-agent orchestration system and should **not** be rebuilt as an anatomically literal brain simulation.

The strongest combined design is:

```text
1. source-preserving perception
2. two complementary cognitive integration regimes
3. direct but gated cross-scale communication
4. distributed state with limited focal availability
5. small composite executive/language/action surface
6. fast episodic memory separated from slow parametric learning
7. mandatory self-action prediction / corollary path
8. local prediction learning gated by eligibility + typed later modulation
9. replay-driven consolidation separated from counterfactual dream
10. slow metaplastic/homeostatic regulation
11. proceduralization of repeatedly successful expensive routes
12. developmental plasticity/autonomy envelope under explicit human control
13. pluggable mobile runtimes and reversible learning transactions
```

The most important conceptual correction is:

> **V13's "brain-nearness" should come from interacting timescales, recurrent competition, fast/slow learning, prediction, action, replay and stability — not from forcing every software module to map one-to-one onto an anatomical structure.**

The most important implementation correction is:

> **Immediate learning should be proven first through exact/episodic memory and small reversible local updates. Deep sparse-body plasticity is an experiment behind TRAIN_RUNNER_PROOF + retention gates, not a prerequisite for the first functioning V13.**

The most important architecture point that survives both research passes is:

> **JEF remains a small executive/action subsystem embedded in a larger distributed cognitive system; it is neither the whole brain nor a third independent chatbot.**

---

# 104. CURRENT RESEARCH SOURCE SET — SEPTEMBER 2026

## Neuroscience / Brain

1. Changeux & Farisco (2026), *The Global Neuronal Workspace as a multilevel model of conscious processing*, Trends in Cognitive Sciences. https://pubmed.ncbi.nlm.nih.gov/41927383/
2. Cogitate Consortium et al. (2025), *Adversarial testing of global neuronal workspace and integrated information theories of consciousness*, Nature. https://www.nature.com/articles/s41586-025-08888-1
3. Oderbolz, Poeppel & Meyer (2025), *Asymmetric Sampling in Time: Evidence and perspectives*, Neuroscience & Biobehavioral Reviews. https://pubmed.ncbi.nlm.nih.gov/40010659/
4. Regev et al. (2024), *Neural populations in the language network differ in the size of their temporal receptive windows*, Nature Human Behaviour. https://www.nature.com/articles/s41562-024-01944-2
5. Miller & Constantinidis (2024), *Timescales of learning in prefrontal cortex*, Nature Reviews Neuroscience. https://www.nature.com/articles/s41583-024-00836-8
6. Singh & Schapiro (2026), *Evidence for complementary learning systems within the hippocampus*. https://pubmed.ncbi.nlm.nih.gov/42421581/
7. Liao & Losonczy (2024), *Learning, Fast and Slow: Single- and Many-Shot Learning in the Hippocampus*. https://pubmed.ncbi.nlm.nih.gov/38663090/
8. Zhang, Ou & Liu (2025), *Replay and Ripples in Humans*. https://pubmed.ncbi.nlm.nih.gov/39971381/
9. Robinson et al. (2026), *Large sharp-wave ripples promote hippocampo-cortical memory reactivation and consolidation during sleep*. https://pubmed.ncbi.nlm.nih.gov/41205608/
10. Salgado-Puga et al. (2026), *Exposure to broadband noise during non-REM sleep impairs hippocampal sharp-wave ripples and memory consolidation*. https://pubmed.ncbi.nlm.nih.gov/42419296/
11. Shouval & Kirkwood (2025), *Eligibility traces as a synaptic substrate for learning*. https://pubmed.ncbi.nlm.nih.gov/39965463/
12. Gerstner et al. (2018), *Eligibility Traces and Plasticity on Behavioral Time Scales*. https://pubmed.ncbi.nlm.nih.gov/30108488/
13. Kahnt & Schoenbaum (2025), *The curious case of dopaminergic prediction errors and learning associative information beyond value*. https://www.nature.com/articles/s41583-024-00898-8
14. Greenstreet et al. (2025), *Dopaminergic action prediction errors serve as a value-free teaching signal*, Nature. https://www.nature.com/articles/s41586-025-09008-9
15. Wolff et al. (2024), *The mediodorsal thalamus in executive control*. https://pubmed.ncbi.nlm.nih.gov/38295791/
16. Zhang et al. (2025), *Mediodorsal thalamus regulates task uncertainty to enable cognitive flexibility*. https://www.nature.com/articles/s41467-025-58011-1
17. Nguyen & Person (2025), *Cerebellar circuit computations for predictive motor control*, Nature Reviews Neuroscience. https://www.nature.com/articles/s41583-025-00936-z
18. Spampinato et al. (2026), *Cerebellar rhythms: mechanisms, functions and translational opportunities*, Nature Reviews Neuroscience. https://www.nature.com/articles/s41583-026-01072-y
19. Crapse & Sommer (2008), *Corollary discharge across the animal kingdom*. https://www.nature.com/articles/nrn2457
20. 2025 Nature Neuroscience, *A thalamic hub-and-spoke network enables visual perception during action by coordinating visuomotor dynamics*. https://www.nature.com/articles/s41593-025-01874-w
21. 2025 Neurodevelopment review, *Investigating hierarchical critical periods in human neurodevelopment*. https://www.nature.com/articles/s41386-025-02246-5
22. Panichello et al. (2024), *Intermittent rate coding and cue-specific ensembles support working memory*, Nature. https://www.nature.com/articles/s41586-024-08139-9
23. 2025 Nature Human Behaviour, *Unattended working memory items are coded by persistent activity in human medial temporal lobe neurons*. https://www.nature.com/articles/s41562-025-02235-0
24. 2026 review, *Neural timescales from a computational perspective*. https://pubmed.ncbi.nlm.nih.gov/42393348/

## AI / Implementation

25. Meta (2026), `facebook/MobileMoE-S-QAT` model card. https://huggingface.co/facebook/MobileMoE-S-QAT
26. Meta (2026), *MobileMoE: Scaling On-Device Mixture of Experts*, arXiv:2605.27358.
27. Cactus Compute (2026), Needle 3 repository. https://github.com/cactus-compute/needle
28. Cactus Compute (2026), Needle 3 model/runtime docs. https://www.cactuscompute.com/needle
29. Park et al. (ACL 2026), *Memory-Efficient Structured Backpropagation for On-Device LLM Fine-Tuning*. https://aclanthology.org/2026.acl-industry.62/
30. Du et al. (ACL 2026), *Enabling Agents to Communicate Entirely in Latent Space*. https://aclanthology.org/2026.acl-long.1248/
31. Peng et al. (2026), *StateBridge: Training-free Hidden-state Alignment for Latent Communication in LLM Multi-Agent Systems*. https://arxiv.org/abs/2608.13317
32. PyTorch ExecuTorch Android documentation. https://docs.pytorch.org/executorch/stable/using-executorch-android.html
33. PyTorch ExecuTorch Android backends. https://docs.pytorch.org/executorch/stable/android-backends.html
34. Liquid AI (2026), `LFM2.5-230M-GGUF`. https://huggingface.co/LiquidAI/LFM2.5-230M-GGUF
35. Liquid AI (2026), *LFM2.5 Q4_0: Quantization-Aware Distillation for Edge Deployment*. https://www.liquid.ai/blog/qad

---

# 105. WORK HANDOFF — WHAT TO DO NEXT

Work must treat this v10.16 delta as **implementation guidance layered over v10.15**, not permission to rewrite the Canon from scratch.

Immediate coding priority:

```text
P0
STEP 0 substrate + schemas + persistence + governor + runner registry

P1
real C2/C3 JEF vertical slice

P2
real B1/B2 BodyPort + timescale-divergent observer passes

P3
Fast Episodic second-attempt proof

P4
TRAIN_RUNNER_PROOF + small-head shadow learning

P5
B3 channel ablations

P6
predictor-first B learning + active expert delta experiments
```

Before marking anything complete, apply existing `IH-H33`:

```text
CODE
REAL DATA/STATE PATH
PERSISTENCE/RESTART
TEST
TELEMETRY
```

plus v10.16:

```text
ABLATION BASELINE
NEURO CLAIM LIMIT
HARDWARE/TRAIN PROOF where applicable
```

---

# v10.16.1 IMPLEMENTATION ADDENDUM — B3 LATENT SAFETY LADDER [WORK BLOCKER]

**Status:** binding implementation hardening for Age-0 B3 / Callosum experiments.  
**Reason:** a vector can have the correct dimensionality and still be out-of-distribution for the receiver. Raw hidden-state injection into a pretrained receiver can perturb residual statistics, attention inputs and especially sparse-MoE routing before any useful semantic transfer is established.

This addendum does **not** remove LATENT communication. It defines the only allowed escalation path for Age 0.

## B3-H1 — No raw foreign hidden-state injection [LOCKED / AGE 0]

Forbidden in production and shadow bootstrap:

```text
B1 arbitrary internal hidden state
        -> dimension-only projection
        -> arbitrary B2 residual stream / router input

B2 arbitrary internal hidden state
        -> dimension-only projection
        -> arbitrary B1 residual stream / router input
```

Matching tensor shape is not receiver compatibility.

Age-0 invariant:

```text
foreign_state != native_receiver_state
until distribution + utility + router-stability are measured
```

Native B1/B2 pretrained routers remain **frozen** during initial B3 bootstrap.

---

## B3-H2 — Message Subspace, not private-state alignment [LOCKED]

B3 aligns only a small exported communication subspace.

```text
B1 private state ------------------------------ stays private
      |
      v
sender selector
      |
      v
sender projector
      |
      v
B3_MESSAGE_SPACE  z[K, r]
      |
      v
receiver projector + calibration
      |
      v
receiver gate
      |
      v
B2-compatible conditioning

and symmetrically B2 -> B1
```

Goal:

```text
useful cross-body communication
!=
make B1 and B2 representations identical
```

Required diversity checks:

```text
role retention
private-state similarity drift
fine-vs-gist specialization
old-task behavior
message utility
```

---

## B3-H3 — LATENT SAFETY LADDER [BLOCKER]

LATENT authority may only progress through these levels. A higher level cannot be activated until the previous level has passed its own gate.

### L0 — NO_MESSAGE / EXACT / CONTROL / SYMBOLIC baselines

Production-capable from the start:

```text
NO_MESSAGE
SOURCE_EXACT
CONTROL
SYMBOLIC
```

These are mandatory baselines, not temporary debugging hacks.

Exit evidence:

```text
latency measured
memory measured
quality measured
source fidelity measured
```

### L1 — Receiver-adapter-only latent read [first latent experiment]

```text
sender native state
    -> small selector/pooler
    -> sender projector
    -> B3 message
    -> receiver-specific adapter/readout
    -> OFFER / policy / auxiliary prediction
```

The foreign latent does **not** enter the pretrained receiver backbone yet.

Purpose:

```text
prove that the sender latent contains useful information for the receiver
without destabilizing the native body
```

Required comparison:

```text
L1 vs NO_MESSAGE
L1 vs EXACT
L1 vs SYMBOLIC
```

### L2 — Calibrated continuous input-prefix conditioning

First allowed direct conditioning of the receiver backbone.

```text
selected sender states
    -> geometry-preserving / low-rank alignment
    -> receiver distribution calibration
    -> K continuous prefix slots
    -> receiver native input path
```

The prefix must be calibrated toward the receiver's **native input/embedding statistics**, not merely toward the sender hidden-state dimension.

Required controls:

```text
prefix OFF
random-but-norm-matched prefix
shuffled sender prefix
EXACT/SYMBOLIC baseline
```

### L3 — Tiny gated residual influence

Only after L2 has passed:

```text
h_next = h_native + alpha * calibrated_message
```

Age-0 search begins near zero, e.g. experimental shadow values:

```text
alpha in {0.01, 0.025, 0.05, 0.10}
```

These values are **[BOOT/RESEARCH]**, not canon optima.

No residual injection is allowed directly before a MoE router unless the target tap has its own measured compatibility proof.

### L4 — Deeper / multi-layer latent integration

Research-only until L3 repeatedly wins.

Possible mechanisms:

```text
multiple calibrated prefix points
cross-attention adapter
projected KV/state
sparse mailbox slots
selected residual taps
receiver-native learned conditioning port
```

This level is never implied merely because L1/L2 work.

---

## B3-H4 — Receiver calibration packet [MUST]

Every candidate latent message carries or references measured receiver-compatibility metadata.

```text
ReceiverCalibration {
  body_pair_id
  sender_revision
  receiver_revision
  injection_level
  target_tap_id

  native_norm_mean
  native_norm_std
  message_norm
  norm_ratio
  mean_shift
  variance_ratio

  geometry_error
  manifold_distance?          // only if implemented and validated
  calibration_confidence

  router_kl
  expert_flip_rate
  residual_norm_shift
  attention_shift?            // if observable
  receiver_loss_delta?

  downstream_utility
  latency_cost
  memory_cost

  sample_count
  calibration_dataset_id
  valid_until_revision
}
```

A stale calibration from another receiver/model revision is invalid.

---

## B3-H5 — Hard receiver gate [LOCKED]

Before an active latent message can influence behavior:

```text
if calibration_missing:
    LATENT = OFF

if receiver_revision_changed:
    LATENT = OFF

if OOD / router-drift gate fails:
    LATENT = OFF
    fallback = EXACT | CONTROL | SYMBOLIC | NO_MESSAGE

if utility <= fallback_utility after cost:
    LATENT authority must not increase
```

The receiver gate is allowed to reduce gain continuously, not only binary on/off:

```text
latent_gain = gate(
    norm_shift,
    geometry_error,
    router_drift,
    historical_success,
    task/body-pair utility,
    resource_cost
)
```

But in Age 0:

```text
unknown -> 0 authority
unsafe  -> 0 authority
```

---

## B3-H6 — Router-stability gate for sparse MoE bodies [BLOCKER]

For B1/B2 sparse-MoE candidates, every latent experiment must compare the receiver with and without the same latent message opportunity.

Minimum metrics:

```text
router KL divergence
expert top-k flip rate
expert-use histogram shift
router-input norm shift
shared pre-router representation drift
receiver loss / task delta
old-task retention delta
```

Required new knobs:

```text
B3.max_router_kl                  [TUNE after calibration]
B3.max_expert_flip_rate           [TUNE after calibration]
B3.max_router_input_shift         [TUNE after calibration]
B3.max_residual_norm_shift        [TUNE after calibration]
B3.max_old_task_loss_delta        [USER/TUNE]
B3.min_downstream_utility_gain    [TUNE]
```

Do **not** hard-code universal scientific constants. Thresholds are derived from receiver-native baseline variation on the real body/runner/dataset.

Recommended bootstrap evaluation grid, research only:

```text
alpha       = 0 / .01 / .025 / .05 / .10
K slots     = 1 / 4 / 8 / 16 / 32
rank r      = 8 / 16 / 32 / 64
channel     = NONE / EXACT / SYMBOLIC / LATENT
```

---

## B3-H7 — Small mobile bridge implementation [AGE-0 DEFAULT]

If the boot body hidden width is `d = 768`, a first bridge should remain tiny.

Example:

```text
projector: 768 -> 32 -> 768
```

Parameter count per directional bridge:

```text
768*32 + 32*768 = 49,152 parameters
```

Approximate BF16 inference weight storage:

```text
49,152 * 2 bytes ~= 96 KiB per direction
~192 KiB for B1->B2 + B2->B1
```

Message-buffer examples at `d=768`, BF16:

```text
16 slots ~= 24 KiB
32 slots ~= 48 KiB
```

These are arithmetic payload sizes, **not RSS guarantees**. Runtime allocator, tensor metadata, activation buffers and training optimizer state must be measured separately.

Age-0 rule:

```text
bridge/controller overhead should remain in the KB-to-low-MB class
unless an ablation proves a larger mechanism materially better
```

B3 must not become a hidden fourth foundation model.

---

## B3-H8 — Training order [LOCKED]

B3 bootstrap training order:

```text
1. freeze B1 body
2. freeze B2 body
3. collect paired grounded experiences
4. train sender selector/projector + receiver adapter
5. calibrate receiver distribution
6. evaluate L1 utility
7. if passed -> L2 prefix shadow test
8. if passed -> tiny L3 residual shadow test
9. only then consider receiver-side/body co-adaptation
10. router learning remains separate and later
```

Do not jointly move:

```text
sender bridge
receiver backbone
receiver MoE router
```

from the first experiment, because failure attribution becomes impossible and router/body co-drift can masquerade as communication learning.

---

## B3-H9 — Channel utility contract [MUST]

For each task/body-pair:

```text
UTILITY(channel) =
    task_gain
  + uncertainty_reduction
  + source_recovery_gain
  - latency_cost
  - memory_cost
  - router_drift_penalty
  - retention_penalty
```

`LATENT` is allowed to become preferred only when it wins against the relevant simpler baselines over a sufficient validation window.

The channel policy must retain:

```text
p(NO_MESSAGE)
p(SOURCE_EXACT)
p(CONTROL)
p(SYMBOLIC)
p(LATENT)
```

No global `latent_first=true` flag is permitted in Age 0.

---

## B3-H10 — Failure and automatic degradation [LOCKED]

Any of the following can demote LATENT authority:

```text
receiver model revision changes
runner revision changes
calibration expires
router drift increases
expert flip rate spikes
retention regresses
message utility falls
latency/thermal cost exceeds budget
message projector collapses
B1/B2 role diversity collapses
```

Degradation path:

```text
L4 -> L3 -> L2 -> L1 -> EXACT/SYMBOLIC -> NO_MESSAGE
```

Demotion requires no architectural rewrite.

---

## B3-H11 — Required `:doctor` output [MUST]

`:doctor` must report at least:

```text
B3 latent level per direction
B1->B2 calibration status
B2->B1 calibration status
body/model revisions
receiver tap IDs
message rank + slot budget
current latent gain
router KL baseline/current
expert flip baseline/current
utility vs NO_MESSAGE
utility vs EXACT
utility vs SYMBOLIC
fallback channel
last calibration time / experience count
hardware proof id
```

If latent influence is active without valid calibration:

```text
:doctor = FAIL
```

---

## B3-H12 — Completion gate for Work [LOCKED]

Work may mark `B3_LATENT_IMPLEMENTED=true` only when all are true:

```text
CODE
REAL sender state path
REAL receiver effect
receiver-specific calibrated bridge
fallback channels operational
OOD gate operational
router-stability metrics measured
restart persistence where required
integration tests
telemetry
NO_MESSAGE ablation
EXACT ablation
SYMBOLIC/CONTROL ablation
real target-runner measurement
```

A random tensor, a dimension-matching linear layer, or a latent packet that never changes receiver behavior is **not** an implemented Callosum.

Allowed intermediate statuses:

```text
B3_LATENT = unavailable
B3_LATENT = scaffold
B3_LATENT = L1_shadow
B3_LATENT = L2_shadow
B3_LATENT = L3_shadow
B3_LATENT = active
```

---

## B3-H13 — Canon interpretation

The canonical function remains:

```text
B1 <-> B3 <-> B2
```

but the implementation principle is now explicit:

> **The callosal bridge must learn a receiver-compatible communication language before it earns the right to perturb a receiver's pretrained internal dynamics.**

This preserves all existing V13 functions while making Age-0 latent communication falsifiable, rollback-safe and compatible with the Redmi resource constraint.



---

# ORIGINALANHANG B — DRIVE-ROADMAPS / SICHTUNG / KI-ÜBERGABE, UNVERÄNDERT

# V14: Originale Drive-Roadmap / Sichtung / KI-Übergabe (2026-10)

> Unveränderte historische Quelltexte. Nicht als aktuelle Fertigmeldung lesen. V14-Ziele und neue Arbeitsweise stehen zuerst in `V14_01_ARCHITEKTUR.md` und `V14_02_FORSCHUNG_LIZENZEN_UMSETZUNGSPLAN.md`.



---

# QUELLDOKUMENT: ROADMAP_Teil1von3.md

# V13 Umsetzungs-Roadmap (Stand 2026-10-09)  [Teil 1 von 3 – Zeilen 1–353 von ROADMAP.md]

Grundlage: Blueprint v10.16.1 (`blueprint/…B3_HARDENED.md`), `status/BUILD_STATE.json`
(Checkpoint `CAUSAL_NATIVE46_NINTH_EXPORTED_SQLITE_FAILED_BEFORE_FIT`),
`status/completion-ledger.json`, `code/specs/component-contracts.json`,
`code/docs/REMAINING_IMPLEMENTATION.md`. Kein Code wurde für diese Roadmap geändert.

## 1. Zielbild ehrlich

Der Blueprint definiert in §29 selbst, wann V13 „funktioniert“: echter A+B+C-Stack,
Fine/Gist-Split mit gemessenem Nutzen, trainierter Callosum, JEF mit Broadcast/Offers,
Focal Coalition, selektiver Body-Wake, Deliberation mit Re-entry, World-JEPA,
Second-Attempt-Vorteil, lokale Eligibility + echtes JEPA/EMA-Update, Replay, Regression
Shield, Age-Rechtehülle, adaptiver Reasoning Effort, Event-Scheduler, Output-Garantie.
Alles darunter nennt der Blueprint „Harness-Prototyp“. Das ist das Ziel dieser Roadmap.

Was das **nicht** ist: AGI. Mit 230M/1.2B-Modellen auf einem 6-GB-Handy entsteht ein
lernender Architektur-Prototyp, dessen Qualität durch die kleinen Modelle begrenzt ist.
Die aktuellen Messungen zeigen das schon: STEP2 `UTILITY_FAIL` (B1 allein 0.59, B1+B2
0.53, B2 0.12) und der C3-Kausal-Decoder liefert „query echo“.

## 2. Stand: was da ist, was fehlt

Gesamter Runtime-Code: 36 Module, ca. 6.400 (sehr dichte) Zeilen in `code/v13/`.
Ledger: 4 PASS, 15 PARTIAL, 1 BLOCKED (B3 latent), 1 NOT_STARTED (Body-JEPA).
`canonical_architecture_complete=false`.

| Bereich (Blueprint) | Stand | Fehlt |
|---|---|---|
| STEP0 Substrat (§96, IH-H27) | PASS: Store/WAL/Blobs, Migrationen, IDs/SourceRef, Schema-Registry, Generation-Manifest, Operator, Queue/Cancel, Governor, Ressourcen-Monitor, Logging, `:doctor`; SQLite-Integritätscheck nach jedem Close (Fix vom 09.10.) | Wiederholung des 46er-Laufs mit echten Modellen; Langzeit-Nachweise |
| STEP1 JEF (C1/C2/C3/C5) | C2 Needle + C3 LFM2.5-230M real, C2/C3/C2+C3-Modi, Restart, Kausal-Streaming opt-in | Sprachqualität (C3 zu schwach), native Confidence, Redmi-Dauerpfad |
| STEP2 Split-Brain | B1/B2 real, Offers, NONE/EXACT/CONTROL/SYMBOLIC | B1 und B2 sind **dasselbe** LFM2.5-1.2B (Harness-Body); kein Gist-Gruppieren nach G1B; Komplementarität FAIL; MobileMoE nicht zugänglich |
| STEP3 Fast Episodic | Korrektur → Second Attempt, Restart, Negativ-Transfer | Abruf ist **lexikalisch**, keine semantische Generalisierung |
| STEP4 Reference Teacher | getrennte Self/Reference/Human-Lanes, Spans | kein stärkerer Teacher angeschlossen |
| STEP5 Shadow Learning | externe Route/Wake/Halt-Heads, Output-Adapter-Lifecycle, Freigabe/Rollback | echte Nutzer-Labels fehlen (`INSUFFICIENT_LABELLED_COHORT`), native Confidence |
| STEP6 Callosum/B-Learning | Dense-Taps, t+2-Predictor mit EMA, Receiver-/Midlayer-Numerik (Authority 0) | B3 Latent-Leiter L1–L4 (§B3-H3), Body-JEPA, Train-Runner, Expert-Deltas |
| STEP7 Stabilität | kurze Sammlung, 3 Restarts | Wochen-Lauf, Redmi Thermik/RSS |
| Querschnitt ohne Code | – | **Adaptive Reasoning Effort (G5B, §10.2)**, **Salience/Interrupt gelernt (F2, §5.2)**, **Age-Stufenlogik (G9, §17, §95)** (heute hart auf 0), **Sleep A/B/C + Event-Scheduler (§94, G13)**, **Proceduralization/FastForward (§6, §75)**, **Homeostasis (§16.2)**, **Action-Transaction/Output-Commit/Provisional-Promotion (IH-H12/13/14)** |
| STEP8–11 (Vision, Audio, Effectors, Full-Duplex, Age>0) | gesperrt | laut Blueprint erst nach stabilem Age-0-Core |

## 3. Was in der Cloud prüfbar ist und was nur auf dem Redmi

Geprüft in diesem Container: Python 3.13, numpy, g++/cmake, 4 CPUs, 15 GB RAM;
HuggingFace und GitHub-Releases sind erreichbar. Damit lässt sich der gepinnte
llama.cpp-b10964-Runner plus alle drei Modelle (≈1 GB) hier aufsetzen, genau wie der
frühere Linux-Nachweis.

Unit-Tests auf der Projektkopie: **382/398 grün**. Alle 16 Fehler kommen von Dateien, die
beim Entpacken weggelassen wurden (`docs/canon/…md`, `docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json`,
`native_norm_poll_policy.hpp`), nicht von Codefehlern.

| Cloud (Linux x86) | Nur Redmi |
|---|---|
| Unit-/Integrationstests, native Smoke, Acceptance-Stufen | RSS/PSS, LMK/OOM, Thermik, Energie |
| Modellqualität (C3/B-Bodies), STEP2-Nutzen, Second-Attempt | echte TTFT/Latenz, Observer-Scheduling-Budget |
| numerische B3-Experimente, Predictor/JEPA-Training (CPU) | RUNNER_PROOF / TRAIN_RUNNER_PROOF auf Zielhardware |
| Restart/Rollback/Migration, Langlauf-Simulation | Termux-Spezifika, 30-min-Session (G12B) |

Der Nutzer arbeitet nur am Handy: jeder Redmi-Nachweis braucht einen Lauf von ihm
(`bash TESTEN.sh`) und das Hochladen des Reports.

## 4. Reihenfolge (Blueprint §105, angepasst an den Ist-Stand)

1. **P0 Substrat heil machen**: SQLite-Fix erledigt (401 Tests grün laut ZIP-Thread); 46er-Lauf wiederholen, sobald WP-B steht.
2. **P0' Cloud-Prüfstand**: nativer Linux-Lauf hier reproduzierbar, sonst ist nichts
   Native-Bezogenes prüfbar.
3. **P1 Fehlende Querschnittsfunktionen in Python** (kein Modell nötig, parallel machbar):
   Age-Hülle, Reasoning Effort/Wake, Sleep/Scheduler, Salience, Proceduralization, Homeostasis.
4. **P2 Qualitätsengpass Modelle**: C3-Kandidaten und ein echter, verschiedener Gist-Body.
   Ohne das bleiben STEP2-Nutzen und Sprachqualität FAIL, egal wie gut die Architektur ist.
5. **P3 Semantisches Gedächtnis** (STEP3 über Lexik hinaus).
6. **P4 Lernen**: Train-Runner (Cloud zuerst), Labels sammeln, Shadow-Fit, Freigabe.
7. **P5 B3-Latent-Leiter L1→L2** mit Ablationen.
8. **P6 Predictor-first B-Learning, Expert-Deltas**.
9. **P7 Action-Transaction/Output-Commit** (vor jeder echten Aktion/Tool).
10. **P8 Redmi-Langlauf (STEP7)**, danach erst STEP8+ (Vision/Audio) und Age>0.

## 5. Arbeitspakete

Konvention für alle Pakete: Arbeit in einer eigenen Kopie oder auf neuen Dateien;
`v13/runtime.py`, `v13/store.py` und `v13/operator.py` sind Hotspots. Pro Paket nur
kleine, klar markierte Hook-Änderungen dort; wer eine Hotspot-Datei ändert, steht unten.
Definition „fertig“ bleibt W3/IH-H33: Code, echter Zustandspfad, Persistenz/Restart,
Test, Telemetrie, plus Ablation/Claim-Limit wo relevant. Ledger-Zeile pro Paket
aktualisieren (`completion-ledger.json`), Proofs nach `docs/proofs/`.

### WP-A Substrat-Reparatur — ERLEDIGT (Thread „V13-ZIP laden und auswerten“, 09.10.)
- `v13/store.py` + Collector: Integritätscheck nach jedem Close, WAL/SHM-Snapshot beim ersten Fehler, neuer Test; 401 Tests grün.
- Ursache vermutlich die alte Cloud-Umgebung, nicht V13-Code.
- Offen: der echte 46-Zeilen-Lauf mit Modellen. Das geht in der Cloud über WP-B (Modelle sind hier ladbar) und zusätzlich auf dem Redmi.
- `store.py` ist damit wieder frei für WP-E/H/K, aber immer nur ein Paket gleichzeitig.

### WP-B Cloud-Nativ-Prüfstand — ERLEDIGT (Thread „Cloud-Prüfstand für Modellläufe“, 09.10.)
- Ein Befehl: `bash /mnt/project-files/v13/code/scripts/cloud_bench.sh [--units|--smoke|--candidates|--full]`; Anleitung + Baseline in `code/docs/CLOUD_BASELINE.md`, Ergebnisse unter `v13/bench-results/<Zeit>/`.
- Baseline: Units grün (fehlende Canon-/Proof-Dateien aus dem Drive-ZIP wiederhergestellt), probe `SMOKE_PASS`, Acceptance `--quick` 14/16 PASS (FAIL: control-calibration `support`, memory-retrieval: C3 nutzt Quelle nicht).
- Kandidaten (`specs/cloud-candidates.json`, `scripts/cloud_candidates.py`, EN zuerst + DE): Qwen3.5-0.8B, LFM2.5-350M, Gemma-3-270M, EmbeddingGemma-300M laden alle auf b10964. Smoke-Vergleich: LFM2.5-350M 8/8+8/8, Qwen3.5-0.8B 7/8+8/8. Nichts produktiv gesetzt (WP-G entscheidet).
- Dateien (neu): `scripts/cloud_bench.sh`, `docs/CLOUD_BASELINE.md`. Keine Runtime-Änderung.
- Inhalt: `setup.sh` mit `V13_HOME` im Scratch, gepinnter Runner + 3 Modelle mit Hash-Check,
  `v13 selftest`, `v13 probe`, `TESTEN.sh` (Acceptance, mit `--resume`), Ergebnis-JSON.
- Fertig: Smoke PASS auf aktuellem Quellstand, Acceptance-Stufenzahl dokumentiert,
  Anleitung, wie jeder andere Thread denselben Prüfstand in 1 Befehl nutzt.
- Tests: das ist selbst der Test. Redmi: nichts.

### WP-C Age-/Entwicklungs-Hülle (G9, §17, §95) — ERLEDIGT (Thread „Age-Stufen mit Hysterese“, 09.10.)
- Neu `v13/age.py` (`AgeControl`), `tests/test_age.py` (13 Tests); `operator.py`: `:age [freeze on|off|lower n|structural lock|unlock]`,
  `:capability [<Name> stage <n>]` (nur absenken), `:stage cap` klemmt gespeicherte Stufen, `:status` zeigt echte Stufe.
  `config.py`, `runtime.py`, `store.py` unverändert; Zustand in `states['age_control']` (versioniert, mit Generation-ID je Wechsel), Wechsel in Telemetrie `age_transition`.
- `BUILD_CEILING=0`: real bleibt Age 0 bis STEP7; erfüllte Gates erzeugen nur einen Vorschlag. Tests zeigen Promotion/Demotion mit simulierten Nachweisen.
- Volle Suite danach 425/425 grün. Offen: echte Nachweisquellen (Retention/Regression-Shield, Calibration) an `record()` anschließen; `executive.py` meldet `permission_flags.age` noch fest 0 (WP-D-Datei); Rechte/Budgets von Cognition/Sleep/Effort noch nicht abgefragt (`allowed()`, `budgets()`, `gist_resolution()`, `plasticity()` stehen bereit).
- Dateien: neu `v13/age.py`, `tests/test_age.py`; Hooks in `v13/config.py`,
  `v13/operator.py` (`:age`), `docs/schema-registry.json`.
- Inhalt: Stage-Gates 0..5 mit Hysterese und mehreren stabilen Nachweisen,
  bindender `user_stage_cap` (nicht selbst überschreibbar), capability-spezifische Reife,
  kontinuierliche Trust/Retention/Calibration-Modulation, Rückstufung bei Regression,
  „Rechte ≠ Reife“ (§95.2), reopenable plasticity (§95.3). Persistiert in der Generation.
- Wichtig: `system_stage` bleibt real 0 (Blueprint: Age>0 erst nach STEP7); die Logik
  muss aber echt sein und mit simulierten Nachweisen Promotion/Demotion zeigen.
- Fertig: Unit-Tests für Cap, Hysterese, Demotion, Restart-Persistenz; `:age` zeigt echten Zustand.
- Cloud: vollständig. Redmi: nichts.

### WP-D Adaptive Reasoning Effort + Wake Policy (G5B, §10.2, Layer 11) — ERLEDIGT (Python, 09.10.)
- Umgesetzt: `v13/effort.py` (Signale Neuheit/Unsicherheit/Konflikt/Salience/Risiko, §59-Gains + Eskalationsregel,
  Bänder → Plan für Wake `none|detail|gist|both`, B1-Re-entry, Focal-Slots, Observer-Zeit; harte Grenzen Exact/Observer aus/
  Ressourcen/Deadline/cfg; Age-Rechte und `autonomous_effort_max` aus `v13/age.py`; gelernter Wake-Head nur innerhalb der Obergrenze,
  nie über einem User-Modus). Hooks: `runtime.py` (Wake-Block), `cognition.focal(slots)`, `executive.effort_context` +
  `permission_flags.age` aus age.py, `:effort [Modus]` in `operator.py`, Paket `EffortDecision` (contracts + schema-registry),
  Ledger-Zeile `G5B_ADAPTIVE_REASONING_EFFORT` (PARTIAL). Modus persistiert über Restart. `tests/test_effort.py` 13 Tests; Suite 427/427 grün.
- Offen: Qualität-vs-Kosten mit echten Modellen gegen fixe low/high/max (§24.23, braucht WP-B); Verify/Tool/Focal-Zyklen sind nur
  Budgets, weil es noch keinen Verifier-/Tool-Runner gibt; Gains sind BOOT, nicht gelernt; Redmi-Latenzbudgets.
- Dateien: neu `v13/effort.py`, `tests/test_effort.py`; Hooks in `v13/cognition.py`,
  `v13/executive.py`; `:effort`-Kommando über einen kleinen Eintrag in `v13/operator.py`
  (nach WP-C mergen, gleiche Datei).
- Inhalt: `disabled|low|adaptive|high|max` steuert echte Compute-Entscheidungen
  (C_native direkt vs. `none|B1|B2|B1+B2` Wake vs. Focal-Loop + Re-entry), adaptive Wahl
  aus Unsicherheit/Salience/Ressourcenmodus, User-Override innerhalb Rules/Deadline/Resource,
  Telemetrie pro Turn.
- Fertig: Unit-Tests ohne Modell (Policy-Entscheidungen, Override, Ressourcen-Downgrade);
  mit WP-B zusätzlich Qualität-vs-Kosten gegen fixe low/high-Baselines (§24.23).
- Cloud: vollständig (Kosten in CPU-Zeit). Redmi: echte Latenzbudgets.

### WP-E Sleep/Replay-Phasen + Event-Scheduler (§94, §15, G8, G13) — ERLEDIGT (Thread „Sleep und Replay mit Scheduler“, 09.10.)
- Umgesetzt: `v13/scheduler.py`, `v13/sleep.py`, `tests/test_sleep_scheduler.py` (21 Tests), Doku `code/docs/SLEEP_SCHEDULER.md`; kleine Hooks in `runtime.py`, `operator.py` (`:sleep`, `:scheduler`), `store.py` (Telemetrie). Gesamtsuite 456/456 grün. Age-Rechte aus `age.py`.
- Offen: native Neubewertung im Sleep (bleibt `:replay`), generativer Dream-Text (bleibt `:dream`), Gewichts-Konsolidierung, Redmi-Messung der Hintergrund-Ticks.
- Dateien: neu `v13/sleep.py`, `v13/scheduler.py`, Tests; nutzt `consolidation.py`, `memory.py`.
- Inhalt: ReplayQueue mit Prioritäten, Sleep A (Replay/Konsolidierung), Sleep B
  (Dream/Counterfactual, schreibt nur Hypothesen), Sleep C (Homeostasis), Idle/Timer/Goal-Events,
  nie den Live-Pfad blockieren, Ressourcen-Modus RED = kein Replay.
- Abhängigkeit: WP-A ist fertig, kann also sofort starten.

### WP-F Salience/Interrupt + Proceduralization/FastForward (§5.2, §6, §75, G4)
- Dateien: neu `v13/salience.py`, `v13/skills.py`, Tests; Hook in `cognition.py`
  (nach WP-D, gleiche Datei).
- Inhalt: Salience-Score aus Offers/Neuheit/Konflikt, spätes hochsalientes Offer kann
  provisional Output invalidieren; Skill Store + Selector, bekannte sichere Route ohne
  seriellen C_fast-Pass, De-Automatisierung bei Fehler (§24.3/24.4).
- **Status 2026-10-09: erledigt** (Thread „Nächste offene Pakete A“). `code/v13/reflex.py` (Timeout-Reflex wirft Beobachter ab, Circuit-Breaker je Body → C3, OOM/Hitze entlädt Runner), `code/v13/fastforward.py` (Kleinhirn-Vorwärtsmodell mit Delta-Regel → N10 `fast_forward`; Prozeduralisierung OBSERVE→SHADOW→READY nach G-PROCEDURALIZATION-004, handelt nur mit `:ff active`, nur ruhige Turns, nur weglassen; Reopen bei Fehler/Überraschung), späte Salienz nach Commit → gated Self-Message (`selfmodel.late_offer`). Skill-Store/Selector war schon AG4. 13 Tests, volle Suite grün. Übergabe: `code/docs/FAST_FORWARD_REFLEX.md`.

### WP-G Modellqualität: C3-Kandidaten + echter Gist-Body (P2)
- Dateien: `specs/models.json` (nur additive Kandidaten), `scripts/benchmark_c3.py`,
  `v13/runners.py`, `v13/cognition.py` (Gist-Gruppierung G1B).
- **Status 2026-10-09: G1B-Teil erledigt (Pakete A).** `code/v13/gist.py`: B2-Gist-Gruppen ~8 Token-Äquivalente/~12 Slots, Auflösung über `age.gist_resolution` (Literal/Neuheit/Konflikt/niedrige Grenz-Konfidenz verfeinern), grenzbewusst ohne Schnitt durch exakte Spans, verlustfrei per SourceRef, alte Teile gröber. SHADOW in `QueryPacket.gist`, `:gist active` schickt `gist_slots` an B2. Bench `bench-results/gist-grouping-20261009/` (84 % vs. 49 % Satzgrenzen, 0 vs. 2 geschnittene Spans). Doku `code/docs/GIST_GROUPING.md`, Suite 703/703 grün. Offen: Nutzen mit Modell (WP-N12), C3-Kandidaten-Benchmark.
- Inhalt: C3 (SmolLM2-135M vs. LFM2.5-230M vs. 1–2 weitere unter Redmi-RAM-Budget)
  mit festem deutschem Benchmark; B2 als zweiter, verschiedener Body oder gleicher Body mit
  echter ~8-Token-Gruppierung/~12 Slots; STEP2-Nutzen neu messen.
- Fertig: Benchmark-Tabelle, Modellwahl begründet, STEP2-Nutzen mit gleicher 70er-Kohorte.
- Cloud: Qualität ja. Redmi: RAM/Latenz der neuen Modelle zwingend vor Produktivsetzung.
- Braucht WP-B.

### WP-H Semantisches Fast-Episodic-Gedächtnis (STEP3, G6)
- **Status 2026-10-09: erledigt (Pakete B)**, zusammen mit WP-S2. EmbeddingGemma-300M als optionales Modell `:download embedding`, Recall-Kanal in `memory.recall` (max(lexikalisch, Kosinus ≥ 0,84), Entitäts-Wächter + Quelle bleiben, gelernter Cue-Kopf hat Vorrang), `:semantic off|shadow|on|auto`. Cloud: Treffer@1 EN 25 % → 96 %, DE 0 % → 75 %, keine zusätzlichen Fehlaufnahmen; RSS 433 MB. Code `v13/semantic_memory.py`, Tests `tests/test_semantic_memory.py`, Bench `scripts/semantic_recall_bench.py` / `cloud_bench.sh --semantic`, Doku + Übergabe `code/docs/SEMANTIC_MEMORY.md`. Offen: Redmi-RAM (WP-R), DE-Schwelle, Negativ-Transfer-/Response-Cache-Ablation §99 (WP-N12).
- Dateien: `v13/retrieval_worker.py`, `v13/memory.py`, Tests. (`store.py` erst nach WP-A.)
- Inhalt: Abruf über Needle-/Body-Embeddings statt Lexik, Second-Attempt auf
  unbekannte Frageformen, Negativ-Transfer- und Response-Cache-Ablation (§99).
- Braucht WP-B für native Embeddings.

### WP-I Lernen echt machen (STEP5/6C, TRAIN_RUNNER_PROOF)
- Train-Runner für kleine Heads/Projector/LoRA in der Cloud (CPU), dann Redmi-Messung;
  Label-Sammlung über `:feedback … --learn` (braucht echte Nutzer-Labels vom User);
  Shadow-Fit, Retention-Gate, Freigabe. Danach Predictor-first B-Learning.
- Nach WP-A/WP-B.

### WP-J B3-Latent-Leiter L1→L2 (§B3-H3..H12)
- `scripts/native_receiver_effect.cpp` & Co., Receiver-Adapter-only Read, Kalibrierpaket,
  Router-Stabilität, Utility gegen NONE/EXACT/SYMBOLIC. Nach WP-B und WP-G.
- **Status 2026-10-09: modellfreier Teil erledigt (Pakete A).** `code/v13/callosum.py`: §85.2 B3_MESSAGE-Felder inkl. signed_gain (Verstärkungs-/Dämpfungs-Vorschlag), gelernte Kanal-Policy pro Richtung (SHADOW, `:callosum active`), Utility-Vertrag B3-H9 aus dem nächsten Empfänger-Offer + Bewertungen, Degradation bei Modellwechsel B3-H10, `:doctor`-B3-Block nach B3-H11 (LATENT `unavailable`, p=0). Doku `code/docs/CALLOSUM.md`, Suite 712/712 grün. Offen: native L1–L4, B3-H2/H7, Latent-Gate G-CALLOSUM-UTILITY-002 (Cloud-Prüfstand).

- **Status 2026-10-09: L1-Experiment erledigt (Pakete A).** `code/scripts/b3_l1_bench.py`, Ergebnis `bench-results/b3-l1-20261009/`: Sender-Latent (B1, PCA r=16) bringt dem B2-Empfänger höchstens +2,5 Punkte (max_item, nicht signifikant), bei Arithmetik nichts; EXACT löst beide Detail-Aufgaben zu 99,6–100 %. Gate G-CALLOSUM-UTILITY-002 nicht bestanden → `B3_LATENT` bleibt `unavailable`, SOURCE_EXACT bleibt Detail-Kanal. Nächster L1-Versuch nur mit gelerntem Selektor (B3-H2) oder Aufgaben ohne exaktes Gegenstück.
- **Status 2026-10-10: B3-H2/B3-H7 erledigt (Pakete E).** `code/v13/b3bridge.py` (gelernter K-Slot-Selektor, Projektor, BF16-Nachricht 64 B, Empfänger-Projektor + Kalibrierung/OOD + Gate als Residuum auf eingefrorener NO_MESSAGE-Readout, Diversitäts-Checks, `budget` B3-H7: 29 k Parameter/58 KB, `l1_gate`, Manifest mit Revisionen B3-H10, `:doctor`-Felder). Messung `bench-results/b3-h2-20261010/`: Selektor schlägt Mean-Pool (max_item +10/+29 Punkte) und trägt Ton/Unsicherheit, die der Empfänger nicht sieht (99 %), aber Gate G-CALLOSUM-UTILITY-002 L1 **FAIL** auf allen 8 Aufgaben (EXACT/SYMBOLIC billiger). `B3_LATENT` bleibt `unavailable`, L2 gesperrt. Tests `tests/test_b3bridge.py`. Offen: Aufgaben ohne kurze exakte/symbolische Form, Redmi-Zeiten, B3-H3 L2–L4 erst nach L1-PASS.
### WP-K Action-Transaction / Output-Commit / Provisional (IH-H12/13/14/29, P3)
- `store.py`, `runtime.py` → strikt nach WP-A. Voraussetzung für jede echte Aktion (C6/C7).
- **Status 2026-10-09: erledigt (Pakete A).** `code/v13/transaction.py`, Doku `code/docs/ACTION_TRANSACTION.md`, Tests `tests/test_transaction.py` (Suite 681/681 grün).
  - IH-H14: Transaktion PREPARED→COPY_COMMITTED→EXECUTING→SUCCEEDED/FAILED/UNKNOWN/CANCELLED; Intent+Corollary atomar vor dem Effekt; nach Absturz UNKNOWN statt Wiederholung; Idempotenz-Schlüssel; Undo.
  - IH-H29: Vertrag Schema→Freigabe→Risiko→Bestätigung→C5; keine Shell-Strings, eigener Namensraum, Secrets nur als Handle (`V13_SECRET_*`, geschwärzt).
  - IH-H12: Commit-Punkt vor dem ersten sichtbaren Byte; danach nur Korrektur-Nachricht. IH-H13: Provisional-Puffer mit TTL, Promotion erst bei FINAL, sonst Tombstone.
  - Erstes Schreib-Werkzeug `sandbox_note` (Sandbox, Undo, Freigabe pro Aufruf über `:tx approve`).
  - Offen: gepuffertes Final-Output, echte Netz-Werkzeuge, TOOL_CALL als C5-Kandidat im Live-Turn (mit WP-AG10/N4).

### WP-R Redmi-Messlauf (nur Nutzer)
- Nutzer startet `bash TESTEN.sh --compare-c3` auf dem Handy und lädt den Report nach Drive.
- Wird vor Produktivsetzung von WP-G und vor STEP7 gebraucht.

## 6. Vorschlag: erste parallele Threads

| Thread | Paket | Warum jetzt | Konflikte |
|---|---|---|---|
| 1 | WP-B Cloud-Nativ-Prüfstand | Ohne ihn ist nichts Native-Bezogenes prüfbar | keine (nur neue Dateien) |
| 2 | WP-C Age-Hülle | reine Python-Logik, komplett fehlend | `config.py`, `operator.py` (Besitzer) |
| 3 | WP-D Reasoning Effort / Wake | reine Python-Logik, komplett fehlend | `cognition.py`, `executive.py` (Besitzer); `operator.py`-Eintrag nach WP-C |

Danach: WP-G und WP-H, sobald WP-B steht; WP-E kann sofort als vierter Thread starten (WP-A ist fertig); WP-K und WP-I danach.

## 7. Beobachtung zum bisherigen Vorgehen

Der Großteil der letzten Wochen ging in Wiederherstellung nach verlorenen Sandboxes,
eingefrorene Kohorten und Nachweis-Buchhaltung (Acceptance 6/20, viele „recovery“-Einträge).
W3/IH-H33 bleiben verbindlich, aber die Threads sollten Proofs knapp halten (ein Report pro
Paket) und Zeit in fehlende Funktionen statt in Re-Validierung alter Kohorten stecken.
Alles Wichtige muss sofort in `/mnt/project-files` landen, damit nichts mehr verloren geht.

## Vorschläge aus Forschung (2026-10-09)

Quelle und Belege: `research/FORSCHUNG.md`. Nur Vorschläge; Status der Pakete oben bleibt unverändert.
Nummern WP-S1… damit nichts mit WP-A…K kollidiert.

### WP-S1 Modell-Shortlist erweitern (speist WP-G)
- `specs/models.json` additiv: C3-Kandidaten **LFM2.5-350M**, **Gemma-3-270M-it**, **Qwen3.5-0.8B**; B2-Kandidat **Qwen3.5-0.8B** (anderer Body als B1); optional B1-Kandidat **Qwen3.5-2B**, **Gemma-4-E2B-it**.
- Zuerst prüfen, ob Runner b10964 die Qwen3.5-/Gemma-4-Architekturen lädt; sonst Runner-Pin anheben (eigener Hash-Check).
- Fertig: C3-Benchmark-Tabelle, STEP2-Nutzen mit B2 = Qwen3.5-0.8B auf der 70er-Kohorte. Cloud zuerst, Redmi-RAM/Latenz vor Produktivsetzung.
- MobileMoE-S-QAT auf „optional Research“ zurückstufen (FAIR-Noncommercial, gated, kein GGUF).

- **Status 2026-10-09: Cloud-Teil erledigt (Pakete A)** mit dem C3-Benchmark aus WP-G und der V3-Echo-Messung: `code/scripts/c3_candidates_bench.py`, `bench-results/c3-candidates-20261009/`. LFM2.5-350M schlägt den installierten 230M (73 % vs. 64 %, Format 72 % vs. 33 %), kostet ~28 % Tempo und +136 MB; Gemma-3-270M unbrauchbar (17 %); Qwen3.5-0.8B am besten (79 %, einziges mit Abstention), aber 2 GB RAM. anti_echo vs. legacy: kein klarer Unterschied. Offen: Redmi-Messung + Nutzerentscheidung vor C3-Wechsel; Abstention der LFMs schwach.
### WP-S2 Semantische Einbettungen für STEP3 (speist WP-H)
- **Status 2026-10-09: erledigt (Pakete B)** mit WP-H, Details dort. RAM < 200 MB nicht erreicht (433 MB mit Q8); LFM2.5-Encoder/Body-Hidden-States nicht verglichen.
- **EmbeddingGemma-300M** (Matryoshka 128/256 Dim.) vs. **LFM2.5-Encoder-230M** vs. Body-Hidden-States als Abruf-Schlüssel.
- Fertig: Second-Attempt auf umformulierten Fragen, Recall@k gegen lexikalisch, RAM < 200 MB.

### WP-S3 Sparse Memory Finetuning als parametrisches Fast-Gedächtnis (F3)
- Kleiner Memory-Layer an C3 oder an den Predictor (Nachrüstung nach arXiv 2604.05248), Slot-Auswahl TF-IDF/KL.
- Ablation gegen LoRA und Full-FT: Neulernen vs. Vergessen auf fester Probe-Menge. Cloud zuerst. Nach WP-I.

- **Status 2026-10-09: erledigt, torch-Pfad (Pakete B).** `code/v13/sparse_memory.py`: Memory-Layer neben dem FFN von C3 (LFM2.5-230M, Layer 7), Werte starten bei 0 (Basis bitgleich). Modus `keyed` (Standard): ein Slot pro Antwort-Position, Radius ≥ 0,9 über Hintergrund-Kosinus; Modus `tfidf` nach dem Papier. Ablation `scripts/sparse_memory_bench.py` → `bench-results/sparse-memory-20261009/`: keyed r90 lernt 8/8, vergisst keine Probe, KL 3e-6 (LoRA+Anker 0,075, Full-FT 0,99), 82 k Parameter; Near-Miss-Leck 0,8 wie LoRA+Anker, ungelöst (braucht Entitäts-Wächter). Tests `tests/test_sparse_memory.py`. Doku + Übergabe `code/docs/SPARSE_MEMORY.md`. Offen: nativer ggml-Op oder Termux-torch für das Handy, Einbinden in AG6/`lora_trainer` (Thread „Echtes Lernen“), `:forget` → Slots nullen, Sleep-Konsolidierung der Slots.
### WP-S4 JEPA-Predictor: SIGReg + Kollaps-Telemetrie (STEP6)
- LeJEPA-SIGReg als Alternative/Zusatz zur EMA im t+2-Predictor; Einbettungs-Rang/Isotropie pro Update loggen.
- Fertig: Ablation EMA vs. SIGReg vs. beides, Kollaps-Test. Reines Python/numpy, sofort machbar.
- **Status 2026-10-09: umgesetzt.** `predictor_regularizer` = ema|sigreg|both in `code/v13/predictor_worker.py`, Telemetrie pro Update, Ablation + Kollaps-Test in `tests/test_predictor_sigreg.py` (456 Tests grün). Default bleibt `ema`; Messung auf echten Taps offen. Details `code/docs/SIGREG_PREDICTOR.md`.

### WP-S5 Drift-Gate und Self-Distillation (STEP5, Regression Shield)
- KL(neu ‖ Basis) auf fester Probe-Menge nach jedem Adapter-Update (RL's Razor) als Freigabe-Kriterium.
- Nutzerkorrekturen per SDFT/iSDFT statt SFT lernen, nur hinter Retention-Gate (Gegenbefund arXiv 2607.01763).
- Optional LLM-JEPA-Hilfsloss beim Adapter-Training.

- **Status 2026-10-09: erledigt, modellfreier Teil (Pakete B).** `code/v13/drift.py` (`:drift`): eingefrorene Probe-Mengen (30 generische Sprach-Prompts `specs/drift-probes.json`, route/wake/halt-Entscheidungen aus menschlichen Labels; SHA-256 fest, Änderung nur per `refreeze` mit Grund + Historie), KL(Basis‖Kandidat) über einen Evaluator mit `kl(prompts)` (passt zu `LlamaCppEvaluator`), Flip-Rate für Entscheidungs-Heads, `record()` ins Update-Manifest; `guards.stability_envelope` lehnt `:approve` bei `DRIFT_ABOVE_CAP` ab (Knobs `drift_kl_max` .05, `drift_flip_max` .10, `drift_required` 0/1). SDFT-Datensatz aus menschlichen Korrekturen: Lehrer-Prompt = Frage + Korrektur, Schüler-Prompt = Frage, Ziel vom Modell selbst erzeugt, nur hinter AG6-Retention-Gate. Tests `tests/test_drift.py`, volle Suite 703 grün. Doku + Übergabe `code/docs/DRIFT_GATE.md`. Offen (Besitzer „Echtes Lernen“/learning.py): `measure_lm`+`record` in den LoRA-Pfad, SDFT im Trainer, `measure_decisions` nach Shadow-Training; dann `drift_required=1`. LLM-JEPA-Hilfsloss liegt schon im LoRA-Trainer.
- **Pakete D 2026-10-10 (Code fertig, Gate noch zu; PAUSE bis Mo 04:00):** SDFT im AG6-Pfad. `weights.sdft_candidates()` + `stage(include_sdft=True)` (Nacht-Job nutzt es) holt Korrekturen mit `learn` aus `drift.sdft_dataset` (Ziel leer, answer_keys aus der Korrektur, origin human_replay); `train()` gibt sie nur Trainern mit `self_teaches` (LoRA); `LoraTrainer.self_teach` lässt das Basismodell die Lehrer-Frage beantworten, verwirft Antworten ohne Korrektur, kürzt nach dem Satz mit der Korrektur; `approve` markiert verworfene SDFT-Items nicht als konsolidiert. Tests in test_lora_trainer, Suite 933 grün. Echte Läufe (`bench-results/ag6-live-20261010/SWEEP.md`, `scripts/ag6_live_bench.py --sdft`): 10/10 gelernt inkl. beider Korrekturen, aber eine Probe („größter Ozean“ → Indian) kippt in jeder Einstellung; Anker 12 bringt Drift .041 < .05; mit Anker 12 + Seed 7 besteht das Gate (9/10 gelernt, 0 vergessen, Drift .044), mit Seed 13 nicht → grenzwertig. Nächster Schritt: Ablation welche Korrektur stört, Seed 7, mehr Anker.
### WP-S6 On-Device-LoRA-Runner (TRAIN_RUNNER_PROOF, speist WP-I)
- QVAC-fabric-llm.cpp (Vulkan) in der Cloud mit C3 (230–350M) reproduzieren, dann Redmi (Adreno 618): Minuten/Schritt, RSS, Thermik.
- Alternative MobileFineTuner. Fertig: ein LoRA-Schritt mit Checkpoint/Resume/Rollback und Retention-Messung.
- **Status 2026-10-09 16:30 (Thread „Echtes Lernen in den Modellen“): Kern fertig, Gate-Werte noch nicht erreicht.**
  Code: `code/v13/lora_trainer.py` (LoraTrainer: torch-CPU-LoRA, trainiert auf den dequantisierten Q4-Gewichten = was der Runner nutzt,
  KL-zur-Basis-Anker + automatische Lokalitäts-Anker, optional Body-JEPA-Term, Checkpoint/Resume, Export llama.cpp-LoRA-GGUF;
  LlamaCppEvaluator misst im Runner b10964: Lern-Recall, Paraphrasen, Near-Miss-Leck, Retention, top-k-KL; AdapterRegistry +
  `runner_lora_args`). AG6 `agi/weights.py`: `train_and_gate`, Spezifitäts-Check (LEAK_MAX .2), `:approve` bindet Adapter (+ Slot-Asset
  `lora:<batch>`), Rollback löst ihn. `runners.py`: `--lora-scaled` nur bei Freigabe + exaktem Hash von Modell und Adapter.
  Nativ ohne Python: `code/scripts/native_select_finetune.cpp` + `build_native_finetune.sh` (llama.cpp ggml-opt, nur gewählte Tensoren).
  Tests: `tests/test_lora_trainer.py` (ohne torch). Bench: `code/scripts/lora_bench.py`; Ergebnisse `bench-results/lora-20261009/summary.json`.
  Messung (8 erfundene Fakten, Basis 0/8): beste Variante E = 8/8 auf dem Q4-Pfad, Paraphrasen 4/6, Retention 0,83 = Basis, KL 0,08,
  aber 1/10 Probe vergessen, Near-Miss-Leck 0,6–0,8 → AG6-Gate sperrt (korrekt). Erster Lauf ohne Anker: Vergessen 30 %, KL 0,78.
  Nativ: LFM2 BLOCKIERT (ggml ohne Backward für SSM_CONV, Hybrid-Cache im Trainingspfad); SmolLM2-135M läuft (2,7 M Parameter,
  270 s / 4 Epochen, RSS 0,9 GB), lernt 7/8, vergisst aber 62 % (kein KL-Anker, Verlust auf allen Tokens).
  Nächste Schritte: (1) Leck/Vergessen senken: Sparse-Memory-Variante (WP-S3), Antwort-only-Verlust + Anker im nativen Pfad,
  größerer C3 (LFM2.5-350M) testen; (2) Gate-Schwellen an echte Probenzahl anpassen (12 Proben → 1 Fehler = 10 %); (3) Termux-Torch
  auf dem Redmi prüfen (WP-R), sonst ggml-Backward für SSM_CONV ergänzen. Erledigt: explizite `:note` ≥ 8 gehen über
  `WeightConsolidation.rated_candidates`/`stage(include_rated=True)` als gewichtete Stil-Beispiele ins Training (implizites Lob nicht).
  Volle Unit-Suite nach den Änderungen: 640/640 OK.
  **Erledigt 2026-10-10 (Pakete D):** WP-S5-Drift im AG6-Live-Pfad: `agi/trainers.LiveNearMissEvaluator` misst `Drift.measure_lm('C3_LANGUAGE')` auf den eingefrorenen `specs/drift-probes.json` im selben llama-server; `weights.gate` hat Check `frozen_drift`, Batch trägt `drift`; `weights.approve` sperrt per `drift.gate` (DRIFT_ABOVE_CAP, mit `drift_required=1` auch DRIFT_NOT_MEASURED; Grenze aus aktueller Config). Echter Lauf: KL .019, alle 7 Checks grün (`bench-results/ag6-live-20261010/ag6-live-lora-drift.json`). Tests in test_lora_trainer/test_agi_trainers. `drift_required` bleibt 0, bis die Shadow-Heads messen. Ursprünglich: `v13/drift.py` in `LoraTrainer.fit` einhängen: `Drift.measure_lm('C3_LANGUAGE', evaluator)` auf
  `specs/drift-probes.json` statt der Bench-Proben, Ergebnis per `record()` ins Manifest (siehe `code/docs/DRIFT_GATE.md`).
  WP-S3 hat ein anderer Thread als `v13/sparse_memory.py` + `scripts/sparse_memory_bench.py` gebaut (Ergebnisse `bench-results/sparse-memory-20261009/`);
  Einbinden als zweiter AG6-Trainer und Messung auf dem Q4-Pfad liegt noch bei diesem Paket.
  **Erledigt 2026-10-10:** `v13/memory_trainer.py` (SparseMemoryAG6Trainer: keyed Slots + Entity-Guard, Keys auf den dequantisierten
  Q4-Gewichten geschrieben, Speicher wächst auf dem gebundenen Artefakt weiter; liefert Gate-Werte inkl. automatischer Near-Miss-Fragen),
  Rolle `C3_LANGUAGE#sparse_memory` in der AdapterRegistry. `:forget` nullt die Slots des Fakts (auch in Rollback-Zielen) und sperrt,
  solange der Fakt in einem aktiven LoRA steckt. Nativ ohne Python: `scripts/native_memory_hook.cpp` (+ `build_native_memory_hook.sh`,
  Export `sparse_memory.export_native`), cb_eval-Hook addiert den Speicher auf `l_out-7` im Q4-Modell.
  Messung (`bench-results/memory-native-20261010/`): nativ auf Q4 8/8 Fakten (Basis 0/8), Proben 0,83 = Basis, nichts vergessen,
  Near-Miss-Leck 0,4 (vorher 0,8; Rest: „least favourite colour“, „brother plays“), Paraphrasen 2/6; torch-Gate: KL 1e-9 → würde PENDING_USER.
  **Erledigt 2026-10-10 (Live-Chat):** `v13/memory_server.py` baut aus der gepinnten Runner-Quelle ein zweites Binary
  `bin/llama-server-mem` (Hook `scripts/v13_memory_hook.h` nur bei `V13_MEMORY_FILE`; ganzer Prompt inkl. Cache-Präfix geht an den
  Entity-Guard). `runners.py` nutzt es nur bei passendem Binary-/Modell-/Speicher-Hash. Trainer bindet die native `.bin`
  (+ `.bin.items.json`), `:forget` ohne torch. Suite 800/800. HTTP 230M (`bench-results/memory-server-20261010/`): 8/8, Proben gleich,
  `:forget` entfernt genau einen Fakt. **350M (aktueller C3)** (`bench-results/memory-350m-20261010/`): Layer 8, 297 s, KL 0,0,
  nativ + HTTP 8/8 Fakten, Proben 1,0 = Basis, Leck 0,2, Paraphrasen 2/6.
  AG6 (`agi/trainers.py`): `:growth trainer sparse` meldet `served_live`, wenn `llama-server-mem` gebaut ist; `auto` wählt Sparse nicht
  (Messung im echten Chat-Prompt siehe WP-T9). Offen: Redmi-Build + Messung (WP-R).
  Master: HF `LiquidAI/LFM2.5-230M@40cb2ad3`, sha256 f630da86…; llama.cpp-Quelle via PyPI-sdist llama-cpp-python 0.3.36 (GitHub gesperrt).
### WP-S7 Sleep mit Offline-Rechenzeit (Erweiterung WP-E)
- Sleep A nicht nur Replay: Re-Encoding/Zusammenfassen des Tageskontexts, Predictor-Updates, später Kontext→LoRA (TTT-Idee), nach arXiv 2605.26099.
- Nie Live-Pfad blockieren; RED-Ressourcenmodus = aus.
- **Status 2026-10-09: erledigt (Pakete A).** Phase `SLEEP_A_OFFLINE` in `code/v13/sleep_offline.py`: extraktiver Tagesdigest pro Sitzung (exakte Spans fest, Lineage geprüft, `:sleep digest`), FF-Prädiktor-Nachtraining mit Held-out-Gate, Kontext→LoRA-Kandidaten nur gestaget (`exports/sleep-ttt-candidates.jsonl`, `:pause training` greift). Doku `code/docs/SLEEP_OFFLINE.md`, Tests `tests/test_sleep_offline.py`, Suite 690/690 grün.
  - Nachtrag: Digest jetzt im Live-Kontext (Turns außerhalb `history_turns`, Lineage bei jedem Turn geprüft, `:ctxos digest on|off`, Standard an). Cloud-Messung `bench-results/digest-context-20261009/`: alte Fakten 0 % → 79–92 %, kein Schaden bei Fakten im Fenster (nach Format-Fix; erstes Format ließ kleine Modelle „Noted…“ kopieren). n=24, Redmi-Langchat offen.
  - Offen: nativer C3-Schlafsummary; Training der Kandidaten in WP-I.

### WP-S8 Blueprint-Hygiene (klein)
- `arcxiv.org/abs/2609.05075` → `arxiv.org` (MePo++). Zitate mit `access_date 2026-10-09, verified` markieren (Liste in FORSCHUNG.md §7).
- **Status 2026-10-09: erledigt** in `blueprint/…B3_HARDENED.md` (IH-H31 + Quelle §48). Die Kopie `code/docs/canon/` bleibt unverändert, weil ihr SHA-256 in `specs/component-contracts.json` gepinnt ist; Archiv-Versionen bleiben historisch.

Reihenfolge-Vorschlag: WP-S4 und WP-S8 sofort (kein Modell nötig); WP-S1/S2 sobald WP-B steht; WP-S5/S6 mit WP-I; WP-S3 und WP-S7 danach.

## Vorschläge aus Sichtung (2026-10-09)

Quelle und Belege: `SICHTUNG.md`, Einzelberichte in `sichtung/`, Code-Kopien in `salvage/`. Nur Vorschläge; Pakete oben bleiben unverändert. Nummern WP-V1… gegen Kollision mit WP-A…K und WP-S….

### WP-V1 Verlorenen burst3–5-Code zurückholen (sofort, klein)
- **Status 2026-10-09: erledigt.** `executive.py` (nur explizite `:task` bleibt, Test `test_implicit_task_tracks_current_turn_but_explicit_task_persists`), `v13/body_training.py` + `tests/test_body_training_port.py` (FP32-Ausnahme über `fp32_inference_parameter_ids`, Autorität bleibt 0), `native_capability_profile` in `verification.py` mit `:native` und in `:doctor`, `world.py` liest das Profil, STEP2 `task_score` + Assertions in `integration_step2.py`.
- Executive-Bugfix: `v13/executive.py:96` hält die erste Nutzerfrage für immer als `active_task`. Fix + Test aus `salvage/executive_implicit_task/`.
- `body_training.py` + Test als fail-closed Train-Port-Vertrag (speist WP-I/S6), Requantizer-Ausnahme für FP32-Slices.
- `native_capability_profile` als `:native` (nicht `:capability`, gehört `age.py`); `world.py` liest dann das Profil statt `'body_training':False`.
- STEP2-`task_score` zurück in `scripts/analyze_step2_proof.py` (speist WP-G).
- Hotspots: `executive.py`, `operator.py`, `world.py`, `verification.py`. Mit den Besitzern dieser Dateien abstimmen.

### WP-V2 Billige Schutz- und Messregeln aus v4/v5 (kein Modell nötig)
- **Status 2026-10-09: erledigt bis auf LoRA-Invariante.** `v13/guards.py`: Kollapswächter (`:collapse`, `:doctor`), Datenmix-Quoten + `enforce_data_mix`, 2-%-Rollback, Stabilitätshülle als Sperre in `Store.switch_generation` vor `:approve`. Invarianten in `tests/test_learning_invariants.py`. Offen: Datenmix in die Trainingsjobs einhängen, sobald Selbsterzeugtes trainiert wird; „kein doppeltes LoRA“ erst mit erstem Merge-Pfad. Drift wird nur gemeldet, kein Alarm ohne Basislinie.
- Kollapswächter pro Turn/Batch: Wiederholungsrate, Typen-Vielfalt, Selbstzitat, Abstention, Drift → Telemetrie + `:doctor`.
- Datenmix-Quoten für Replay/Lernen (≥ 60 % Mensch, ≤ 10 % selbst erzeugt, Dream ≤ 5 %) + Rollback bei > 2 % Verlust auf alten Sets. Passt in WP-E/S5.
- Invarianten-Tests: Target ohne Gradient, EMA bewegt sich, Optimizer isoliert, schlechtes Outcome nie negativer JEPA-Loss, kein doppeltes LoRA nach Merge.
- Stabilitätshülle (max. Update-Norm, Route-Shift, Kalibrier-Shift) als Freigabekriterium vor `:approve`.

### WP-V3 C3-Decoding gegen „query echo“ (speist WP-G)
- **Status 2026-10-10: Messung erledigt (Pakete B).** `scripts/measure_anti_echo.py` auf dem aktuellen C3 LFM2.5-350M, 8 Fälle je Sprache, Saat 13 → `bench-results/anti-echo-20261010-350m-{en,de}.json` (230M-Lauf: `anti-echo-20261009-en.json`). Query-Echo (Anteil Frage-Wörter in der Antwort) EN legacy 0,034 → anti_echo 0,021 (230M: 0,038 → 0,010), DE 0,042 = 0,042; lexikalische Checks EN 2/4 → 3/4, DE 4/4 beide. Befund: Echo ist auf beiden C3 kein echtes Problem mehr, anti_echo bleibt Standard. `below_min_new` (2 EN, 3 DE) trifft nur korrekt kurze Antworten (Gruß, „120 Euro“): min_new=8 taugt nicht als Fehlerzeichen und bleibt reine Messung. Redmi-Lauf und echte Chats offen.
- **Status 2026-10-09: Baseline drin, Messung offen.** C3-Freitext nutzt v4-Decoder (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, rep 1,08, DRY statt no_repeat_ngram 4), umschaltbar mit `:sampling anti_echo|legacy`; Zitat-/Abstention-Regel im Systemprompt. `min_new=8` nur gemessen (`below_min_new_rate`), llama-server hat keinen Mindestlängen-Regler. Wirkung auf „query echo“ braucht einen Lauf mit Modell.
- Decoder-Parameter aus v4 §64 (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, no_repeat_ngram 4, rep 1,08) und `min_new=8` als Baseline, bevor Modelle getauscht werden.
- Zitatregel (≤ 2 Zitate, Nutzerversion gewinnt) und Abstention-Form „nichts Belegtes, ich vermute:“ im C5-Report.

### WP-V4 Timescale-Gate und Modellpaar-Entscheidung (vor WP-G-Produktivsetzung)
- **Status 2026-10-09: Nutzer hat entschieden:** viele verschiedene Modelle in einem System wie im Blueprint definiert (mehr als 2), kein Ein-Body-Kompromiss; Ziel konstantes Lernen. Die vier §85.1-Kontrollen bleiben als Messung sinnvoll, die Entscheidung ist aber gefallen.
- **Umgesetzt 2026-10-09:** B2 = Qwen3.5-0.8B als eigener Body (`specs/models.json` Schlüssel `gist`, `:download gist`), Qwen-Denkmodus aus. Vier §85.1-Kontrollen über `b2_control`, Messung `scripts/timescale_gate.py`. B2-Tap (lfm2) für Qwen gesperrt bis eigene Validierung. Erste Messung (Cloud, 2 englische Aufgaben, 1 Durchgang, nur Hinweis): zwei Bodies lösen alle Aufgabenprüfungen (100 %), die Ein-Modell-Kontrollen 75–88 %; B1 allein 50 %, B2 allein 75 %, d. h. sie ergänzen sich über die Aufgaben. Gate bleibt ungefördert, braucht mehr Aufgaben und den Redmi. Daten: `bench-results/timescale-gate-20261009/`.
- §85.1 mit vier Kontrollen messen: same-model same-policy, same-model prompt-only, shared body + dual state heads, true two-body.
- Nutzer entscheidet danach: zwei verschiedene Bodies (sein ursprünglicher Wunsch, ggf. MobileMoE wenn Zugang/Runner) oder bewusst ein Body mit getrennten Zuständen. Entscheidung in USER_DECISIONS festhalten.

### WP-V5 Bedienung und Lernsignale am Handy
- **Status 2026-10-09: erledigt.** `v13/inputs.py`: Logs-Filter (Verlauf + B2-Kontext), `:note 1-10`, implizites Lob/Kritik als schwache Bewertung, `:ratings`, `:context`, `:pause selfedit|traum|training|budget N` und Ausbrenn-Budget im Scheduler, Einfügen als Block (Plain + prompt_toolkit), Statusmeldungen warten beim Tippen. Offen: Bewertungen in WP-I-Trainer einlesen.
- Live-Logs überschreiben getippten Text nicht; mehrzeiliges Einfügen als ein Block; `:context` zeigt, was ins Modell geht; Knobs live ändern; `:pause selfedit|traum|training`.
- Filter: eingefügte Terminal-Logs nicht ins Gedächtnis.
- Implizites Feedback (Lob/Kritik im Chattext) und `:note 1–10` als echte Labels gegen `INSUFFICIENT_LABELLED_COHORT` (speist WP-I).
- „Ausbrennen“-Budget: ohne Input klingt Aktivität ab, Limit vom Nutzer einstellbar (speist WP-E-Scheduler).

### WP-V6 Regeln nach Nutzerposition (Fixed Policy C5/F6)
- **Status 2026-10-09: erledigt, soweit im Code.** Regel nach realem Schaden, Fiktion erlaubt, offener Ablehnungsgrund im Systemprompt (`prompts.py` `conduct`); Telemetrie speichert keine Inhalte (Test), Cloud-Teacher nur mit Zustimmung war schon da.
- Regeln an realem Schaden statt Themen/Schlüsselwörtern; Darstellung/Absicht/Kontext/Veröffentlichung/Handeln unterscheiden; private Fiktion erlaubt; Ablehnung mit offenem Grund.
- Privatsphäre: keine Inhalts-Telemetrie, externer Teacher nur nach Zustimmung, Löschen über IH-H20. Quelle: `archiv/KI_Zensur_Privatsphaere_Grundbasis.md`.

### WP-V7 Fehlende Blueprint-Pakete (später, nach STEP2-Klärung)
- **Status 2026-10-10: C2-Benchmark Needle vs. FunctionGemma erledigt (Pakete C).** `code/scripts/c2_benchmark.py`, Korpus `code/specs/c2-benchmark.json` (96 EN, Autor-Labels), Test `tests/test_c2_benchmark.py`, Ergebnis `bench-results/c2-benchmark-20261010/README.md`: Regex 48 %, Needle nativ 17 % (Konfidenz-AUROC .52), Needle-Einbettung + Kopf 85 % (4-fach CV), FunctionGemma-270M 4 % frei / 25 % erzwungen bei 736–800 MB RSS. Entscheidung: Needle bleibt C2, Routing über gelernten Kopf `C2_EXTERNAL_ROUTE_HEAD` sobald Nutzer-Labels da sind; FunctionGemma kein Ersatz.
- **Status 2026-10-09: teilweise.** KnobSpec (IH-H5, `:knobs`) und BridgeKey (IH-H21, `models.bridge_key`) drin. Rest (Focal Coalition, Modulatoren, Context OS, C2-Benchmark, Inquisition) offen; World-Model ist WP-V10 im Lücken-Thread.


---

# QUELLDOKUMENT: ROADMAP_Teil2von3.md

[ROADMAP.md Teil 2 von 3 – Zeilen 354–533 der Originaldatei; Teil 1 endet mitten in WP-V7]

- Focal Coalition (§93), World/Self-Lernen aus Corollary (§85.7), typisierte Modulatoren + Objective Registry (§85.10, IH-H25), Context OS mit „Re-entry statt Re-prefill“ (§8.3–8.6, §74, v10.6-Zweig), KnobSpec (IH-H5), BridgeKey (IH-H21) vor jedem Modelltausch, C2-Benchmark Needle vs. FunctionGemma.
- Inquisition (κ, P1/P2, adaptives N) bewusst entscheiden: als WP aufnehmen oder als gestrichen dokumentieren.

### WP-V8 Doku- und Aufräum-Commit (nur wenn kein `TESTEN.sh --resume` läuft)
- **Status 2026-10-09: teilweise.** Root-Duplikate nach `archiv/code-root-duplicates-20261009/`, `Store.close()` wertet Busy aus, Exception-Klassennamen bleiben in Telemetrie lesbar, USER_DECISIONS listet echte Nutzeraufgaben, README ergänzt. Bewusst nicht: Blueprint-Edits (Canon-Hash), Skript-Umzug/Dispatcher (andere Threads nutzen die Pfade).
- Root-Duplikate `code/completion-ledger.json` und `code/USER_DECISIONS_AND_OPEN_QUESTIONS.md` durch Verweis auf `docs/` ersetzen.
- BUILD_STATE-Kopf, Ledger `current_acceptance`, REMAINING_IMPLEMENTATION, README (STEP2-Pfad, `:age`/`:effort`) korrigieren; Acceptance-Zählweise 20/21 erklären.
- USER_DECISIONS: Nutzeraufgaben unter `USER_DECISION_REQUIRED` (Redmi-Lauf, echte Labels, 46er-Rerun, Modellpaar, MobileMoE-Zugang) und die Anforderungen aus SICHTUNG §4 aufnehmen.
- Ungenutzte Skripte/Drafts nach `archive/`, Wrapper-Skripte zu einem Dispatcher, `__pycache__` raus, Test-Helper-Modul statt gegenseitiger Imports.
- Blueprint: IH-H1 A/B-Mapping versionsabhängig machen, latent 0.20 in §54/§78 auf 0, `arcxiv`-Tippfehler.
- `Store.close()`: Busy-Ergebnis des WAL-Checkpoints auswerten; breite `except` in learning/runtime/cognition/world mit Meldung statt nur Klassenname.

Reihenfolge-Vorschlag: WP-V1 und WP-V2 sofort; WP-V3 mit WP-G; WP-V4 bevor WP-G produktiv wird; WP-V5/V6 parallel; WP-V8 in einem ruhigen Moment; WP-V7 nach STEP2-Klärung.

### Nutzerentscheidung 2026-10-09 zu WP-V4 (siehe `NUTZER_ENTSCHEIDUNGEN.md`)
- Viele Modelle wie definiert, B1 und B2 echt verschieden: WP-V4 misst den Ist-Stand, das Ziel ist entschieden (true two-body, plus World-Model).
- Englisch zuerst, Deutsch später als Lerntest: WP-G-Benchmark und System-Prompts auf Englisch umstellen (neues kleines Paket **WP-V9**, Prompts in `runtime.py`, `__main__.py`, `verification.py`, `proofs.py`; Besitzer der Dateien beachten).
  - **WP-V9 Status 2026-10-09: erledigt.** `v13/prompts.py` (en/de), `answer_language`=en, Runtime/Probe/Smoke/Welcome/Replay englisch, C3-Benchmark und STEP2-Fixtures EN zuerst, DE bleibt als Transfertest.
- World-Model (§7.2, §92.2) als eigenes Paket **WP-V10** aufnehmen. → zusammengelegt mit **WP-AG2** (Thread „AGI-Lücken als Infrastruktur“, Besitzer dort).
- Konstantes Lernen als Endziel: Age-Hülle (WP-C) ist der Weg dorthin, kein Dauerzustand.

## WP-AG: Infrastruktur für die 12 AGI-Lücken (FORSCHUNG.md §9) — Gerüst ERLEDIGT 09.10. (Thread „AGI-Lücken als Infrastruktur“)

Name **AG** statt G, weil „WP-G“ (Modellqualität) und die Blueprint-Gates G1–G13 schon belegt sind.
Code: `code/v13/agi/` (13 Module, ca. 1.400 Zeilen), Tests: `code/tests/test_growth.py` (21, grün).
Anschluss: `scheduler.py` (4 neue Aktionen `growth_*`), `sleep.py` (`job` leitet `growth_*` weiter, nach voller Nacht `after_sleep`), `operator.py` (`:growth`).
Regeln für alle: Zustand versioniert in `states`, Age-Rechte über `age.py`, Eigeninitiative (SELF) bei Age 0 gesperrt,
alles was Gewichte, Struktur, Regeln oder Außenwelt berührt endet als `requests`-Eintrag für den Nutzer. Kein Modell nötig.
Was ein Modell erst „beibringen“ muss, steht jeweils unter „Später“.

| WP | Lücke | Vorher (Blueprint / Code) | Jetzt gebaut | Später (braucht Modelle/Redmi) |
|---|---|---|---|---|
| AG0 | Modelle einzeln austauschbar | §19 BodyPort, Gate G11 Body Swap, §24.9, IH-H21 BridgeKey; Code lädt fest über `ModelManager.path_for(role)` | `slots.py`: Slots B1/B2/C3/C2/Lehrer/Embedder/World (erweiterbar), Fähigkeitsprofil je Modell, gelernte Assets mit Revision. Beim Tausch: Gedächtnis/Skills/Regeln/Ziele/Nutzer-Modell wandern mit (PORTABLE), Heads/Kalibrierer werden neu angepasst (REFIT), LoRA/Adapter werden auf dem neuen Modell aus gespeicherten Daten neu gelernt (REDISTILL, nie alte Gewichte auf neues Modell), Bridges fallen auf SHADOW (IH-H21). Ablauf: Kandidat → Schatten → Parität (AG12) → 10/50/100 % Verkehr → aktiv, Rollback jederzeit. Eigener Tausch durch V13 erst Age 5. Sichern/Export nach Blueprint §21.1 (modulare Checkpoints) und IH-H17: `export_bundle` schreibt je Slot ein geprüftes Paket (Modell-Revision, Assets, Datensatz-Verweise), `import_bundle` führt es nur über dieselben Tausch-Tore wieder ein, `manifest_fields` bindet alle Slots in einen Hash fürs Generation-Manifest | `route()` in Runner/`ModelManager` einhängen (Datei-Besitzer beachten); Redistill-Job aus AG1/AG6-Daten |
| AG1 | Starke Basis durch Lehrer | L4.5/L5.5 Teacher-Internalisierung, `:teacher` als Referenz | `teacher.py`: Anfragen (eigene erst Age 3), Cloud-Lehrer nur mit Nutzer-Erlaubnis, Spuren als `REFERENCE_NOT_FACT`, Distillations-Datensatz (Holdout-geschützt), Reliance/Dropout, Lehrer-Entfernung nur durch Nutzer | Backend für großen Lehrer registrieren; Datensatz in WP-S6-Trainer |
| AG2 (= WP-V10) | Geerdetes Weltmodell | §7.2 World-JEPA (kein vierter Body, sondern State + Prädiktoren auf A/B/C), §7.2.1 forward/inverse/state-align/outcome, §7.2.2 Coverage + Counterfactual-Confidence, §92.2, G-SELF-WORLD-005; `world.py` digital, Kamera/Audio aus | `grounding.py`: Vorhersage vor Aktion, echtes Ergebnis danach, Fehler = M_world; Basis-Vorhersager (Häufigkeit); Modalitäten-Register (Kamera/Audio/Effektor aus); Werkzeug-Ergebnisse fließen automatisch ein; Ursache SELF/EXTERNAL; `counterfactual()` mit Coverage, OOD-Flag, immer `SIMULATION_NOT_FACT` | World-JEPA als Vorhersager einstecken; STEP8 Sensorik |
| AG3 | Lange Planung | Self-Model „offene Ziele“, Age-Recht `resume_open_goals`, kein Ziel-Store | `goals.py`: persistenter Zielbaum mit Teilzielen, Planschritten, Fortschritt, `GOAL_WAKE` über G13-Scheduler, Plan-Bewertung über Evaluator | Planer, der Teilziele selbst zerlegt; World-JEPA als Plan-Bewerter |
| AG4 | Offenes Skill-Lernen | §6.2/6.5/L5.6 Skill Store + Lifecycle, nur Routen | `skills.py`: deklarative Skills (Werkzeugketten/Routen, kein freier Code), CANDIDATE→SHADOW→TRUSTED→INTERNALISED, Parität, Wiederöffnen bei Fehler, Selector, Übungsaufgaben am Lernrand | Skills aus erfolgreichen Spuren automatisch vorschlagen; Internalisierung über AG6 |
| AG5 | Eigener Antrieb | Layer 6 M_novelty/M_surprise, `exploration_rate` 0 bei Age 0 | `curiosity.py`: Lernfortschritt + Neuheit pro Bereich, Rauschen/Gekonntes bekommen ~0, Sperrliste, eigene Wahl nur mit `active_info_search` (Age 4) | Fehlersignale echter Prädiktoren einspeisen |
| AG6 | Wissen in Gewichte | L8.3/§21, Sleep A staged nur Indizes, `base_merge_authority=0` | `weights.py`: nach voller Nacht Batch aus menschlichen, replay-geprüften Erinnerungen → Trainer → Retention-Gate (AG12-Eval Basis vs. Kandidat, Vergessen, KL-Drift, Batch-Recall) → Nutzer-Anfrage → Freigabe/Rollback. `NullTrainer` meldet ehrlich `NO_TRAINER` | WP-S6 LoRA/Sparse-Memory-Trainer; Generationswechsel über bestehenden Update-Pfad |
| AG7 | Transfer / Abstraktion | Sleep B macht Hypothesen, keine Regeln | `abstraction.py`: Episoden clustern, Regel induzieren (kleine Programm-DSL, DreamCoder-Idee), an zurückgehaltenen Fällen prüfen, nur VALIDATED, Fakt-Autorität 0, Nutzer befördert | Modell-basierter Induzierer; Anschluss an Sleep B |
| AG8 | Selbstverbesserung | Generation-Manifest, Regression Shield, Age `structural_modification` (5) | `self_improve.py`: Knob-/Lernregel-Vorschläge, Sandbox-Eval mit AG12, Regression Shield (keine Achse schlechter), Nutzer-Freigabe; Regeln/Age/Kanal/Latents nie vorschlagbar; Strukturänderungen nur protokolliert | Evaluator, der eine Kopie der Runtime mit Kandidat startet |
| AG9 | Metakognition | Native Route-Kalibrierung extern, keine allgemeine Confidence | `metacog.py`: pro Komponente Kalibrierer (monoton), ECE/Brier, Entscheidung „zweiter Versuch“/„weiß ich nicht“, Semantic Entropy, Age-Metrik `calibration` | Confidence aus Bodies/JEF einspeisen; Effort-Policy (WP-D) liest `decide()` |
| AG10 | Werkzeuge | WP-K/IH-H14/H29 gesperrt | `tools.py`: Register + Transaktion je Aufruf, sicherer Rechner (`calc`, ohne eval), Nutzer schaltet je Werkzeug frei, eigene Wahl erst Age 1, Netz/Schreiben/Außenwirkung nur Vorschlag | Echte Werkzeuge erst nach WP-K; Needle/C2 wählt Werkzeug |
| AG11 | Soziales Modell | Self-Model da, kein Nutzer-Modell | `user_model.py`: Annahmen über den Nutzer nur mit Beleg, Konfidenz, Zerfall, Widerspruch ersetzt, geschützte Merkmale verweigert, `forget()` | Annahmen aus Feedback automatisch erfassen; Kontext an C1/JEF |
| AG12 | Allgemeinheit messen | Acceptance prüft nur Mechanismen | `generality.py`: Englisch zuerst (Nutzerentscheidung), deutsche Fassung mit gleicher Aufgabenlogik als späterer Lerntest; fester Aufgabensatz (7 Familien, 88 Aufgaben, deterministisch), gesehen/ungesehen, Transfer, Vergessen zwischen Läufen, Planungstiefe, Kalibrierung, Kurven pro Generation, monatlich fällig, Holdout-Schutz für alle Trainingsdaten | Solver-Adapter für die echten Bodies; Deutsch-Kurve als Lerntest freischalten; später ARC-artige interaktive Aufgaben |
| AG13 | MoE-Experten nur im RAM wenn aktiv | L9.3 `OPT.body_residency_policy`, §24.33, §12.1, W6 (erst Experten/Deltas, Router zuletzt); MobileMoE gesperrt | `residency.py`: Laden/Verdrängen nach Nutzen im RAM-Budget, Router/Shared immer resident, gelb/rot verkleinert sofort; Lernen nur für residente Experten, Lernsignale ausgelagerter Experten werden gepuffert | Echter MoE-Body + Runner-Unterstützung (mmap) |
| Age-Feeder | Stufen wirklich verdienen | §17.4 Stage Gates; `age.record` wurde nirgends aufgerufen | `maturity.py`: Nachweis aus echten Messungen (AG12, AG9, Sleep A, Integrität, Werkzeug-Verhalten), nach jeder vollen Nacht einer; `:growth age` zeigt Blocker und Tage. Schätzung: `research/VISION_UND_AGE_STUFEN.md` | Freischalten über `:stage cap` nach STEP7 (Nutzer) |

Ausrichtung nach Nutzerentscheidung 2026-10-09 (`NUTZER_ENTSCHEIDUNGEN.md`): viele verschiedene Modelle (AG0-Slots: B1, B2, C3, C2, Lehrer,
Embedder, World, erweiterbar; B1 und B2 sollen echt verschieden sein), Englisch zuerst, konstantes Lernen als Endziel (AG6 + Age-Hülle
öffnen schrittweise; Age 0 ist Start, kein Dauerzustand), Ziel ist eine heruntergebrochene Gehirn-Simulation: die AG-Module sind
Fabric-Funktionen (F3 Gedächtnis/Selbst/Welt, F4 Lernen, F5 Age), keine Chat-Features.

Lernen und Austausch zusammen [Schluss]: Wissen lebt an drei Orten. (1) Modellunabhängig (Gedächtnis, Skills, Regeln, Ziele,
Nutzer-Modell, Lehrer-Spuren, AG6-Batches) überlebt jeden Tausch. (2) Kleine Köpfe auf den Modell-Ausgaben werden nach dem Tausch
aus gespeicherten Labels neu angepasst. (3) Gewichtsnahe Anpassungen (LoRA) sind an eine Revision gebunden und werden auf dem neuen
Modell aus (1) neu gelernt. Deshalb muss jeder Trainingsdatensatz gespeichert bleiben (`dataset_ref`), nicht nur das Ergebnis.

Bedienung: `:growth` (Übersicht AG0–AG13), `:growth age`, `:growth slots`, `:growth export <Slot>`, `:growth eval`, `:growth goals`, `:growth goal <Titel>`, `:growth consolidate`,
`:growth approve|reject <Batch>`, `:growth tools`, `:growth enable calc`, `:growth calc 6*7`.

Nächste Schritte in dieser Reihenfolge [Schluss]: AG12-Solver-Adapter (sonst keine Kurve) → AG6 mit echtem Trainer (WP-S6) → AG9 an Effort-Policy → AG1-Backend → Rest.
- **Status 2026-10-10 (Pakete D): AG12-Solver + AG1-Backends erledigt und gemessen.** Erste echte AG12-Kurvenpunkte (`bench-results/ag12-bodies-20261010/`, gleicher Runtime-/Runner-Pfad wie am Handy): gesamt C3 .22, B1 .17, B2 .35, v13-Abstimmung .34 (ECE .07, am besten kalibriert); ungesehen .17–.23; Planungstiefe 0, Wort umdrehen/Buchstaben sortieren 0 bei allen. Ein Runner, der jede Aufgabe verliert, gibt Status ERROR statt 0-%-Punkt. AG0 `route()` war schon über WP-N11 (`ModelManager.router`) drin. `v13/agi/solver.py`: Solver `c3|b1|b2|v13` (v13 = konfidenzgewichtete Abstimmung B1+B2+C3), JSON-Grammatik `{"answer"}`, Konfidenz = unwahrscheinlichstes Antwort-Token (`runners.generate(confidence_field=)`), keine Gedächtnis-/Event-Schreibzugriffe (Holdout bleibt unverbraucht), `batch()` ein Body nach dem anderen, Kurven + Vergessen pro Solver (`generality.run(solver_name=)`), (Konfidenz, richtig) → AG9 `ag12:<solver>`. `hub()` setzt `g.solver` sobald ein Body installiert ist → monatlicher Lauf nach voller Nacht. `:growth eval run <solver>`, `:growth eval curve <solver> <Achse>`. `v13/agi/teacher_backends.py`: `local` (TEACHER-Runner) und `claude` (Anthropic-SDK, `claude-opus-5-5`, kind cloud → nur nach `:growth teacher cloud on`), Scheduler-Aktion `growth_teacher`, `:growth teacher ask|run|cloud|dataset`. Tests `tests/test_agi_solver.py` (12), Suite 735/736 grün (einziger Fehler: `test_b3bridge` von Pakete E, Datei war mitten im Schreiben). Doku `code/docs/AG12_SOLVER_AG1_TEACHER.md`, Messskript `scripts/ag12_body_bench.py`.
- **Status 2026-10-10 (Pakete D): AG6 läuft live mit echtem Trainer.** Vorher bekam der Nacht-Job immer `NullTrainer` (Batch endete stets NO_TRAINER). `v13/agi/trainers.py`: Auswahl `auto|lora|sparse|none` (`:growth trainer <Art> [Master-Ordner]`, Master-Hash wird gepinnt), auto = LoRA wenn Master + torch/peft/gguf + Runner + C3-GGUF da sind; Master muss Breite/Tiefe des installierten C3-GGUF haben (C3 ist jetzt 350M, alter 230M-Master wird abgelehnt). `growth_consolidate` → `train_and_gate`; Near-Miss-Fragen aus dem Batch abgeleitet und als Spezifität ins Gate. Proben/Anker `specs/ag6-probes.json` (AG12-Holdout-geprüft). Tests `tests/test_agi_trainers.py` (7), Suite 788/788 grün. Echter Lauf `bench-results/ag6-live-20261010/` (Cloud, LFM2.5-350M-Master, 8 erfundene Fakten): 21 Schritte, 257 s, RSS 2,8 GB; gelernt 8/8 (Basis 0/8), Near-Miss-Leck .33, aber 1/12 Probe vergessen und KL .107 > .05 → GATE_FAIL (richtig gesperrt, nichts aktiviert). **Nachtrag 2026-10-10 (Pakete D): Gate besteht jetzt.** Live-Standard `LIVE_LORA` = lr 3e-4, Anker-Gewicht 8, 16 Anker/Schritt, nur FFN (w1–w3); Anker 32→48, Probes 12→32; Regler pro Gerät `:growth trainer cfg k=v|reset`; KL-Messung stürzte bei Kurzantworten (EOS) ab → behoben. Sweep `bench-results/ag6-live-20261010/SWEEP.md`: alle Ziele + Anker 4/8 vergessen 2/31; FFN + Anker 8 besteht mit Seed 13 und 7 (8/8 gelernt, 0 vergessen, Leck 0, KL .012–.014, ~6 min Cloud-CPU, RSS 2,8 GB) → PENDING_USER. FFN + Anker 4 nur 1 von 2 Seeds. Gate unverändert (kein einziger Kipper erlaubt). Offen: Termux-torch auf dem Redmi (WP-R), Sparse-Memory im Live-Runner (nativer Hook), mehr Seeds/echte Nutzer-Fakten.

## Neue Pakete aus dem Blueprint-Abgleich (2026-10-09, `ABDECKUNG.md`)

Quelle: `ABDECKUNG.md` (210 Blueprint-Bausteine gegen Code geprüft: 24 % fertig, 52 % teilweise, 21 % fehlen, 2 % laut
Blueprint erst später). Diese Bausteine hatten bisher kein eigenes Paket. Nur Vorschläge; nichts davon ist gebaut.
Nummern WP-N… gegen Kollision mit WP-A…K, S, V, AG. WP-N1–N3 ersetzen die JEF-Stichworte aus WP-V7.

### WP-N1 JEF-Fokusschleife + Koalition + Workspace (G3D, G5)
- §3.3.7, §3.4.5, §4.4, §8.1–8.2A, §59, §85.3–85.4, §93. Heute nimmt `cognition.focal()` nur die ersten N Offers.
- Inhalt: `FocalItem` nach §93 (Salienz, Unsicherheit, Zerfall, Ziel-Bindung, ACTIVE/REACTIVATABLE/EPISODIC_POINTER),
  Admission-Priorität, Multi-Slot-Workspace (`WorkspaceSlot` wird endlich benutzt), rekurrente Runden mit gezielter
  Re-entry, `C4.uncertainty_coupling_gain`, Cross-scale-Kopplung §3.2A, Age-Rechte für Cognition.
- Dateien: neu `v13/focal.py`; Hooks in `cognition.py`, `runtime.py` (Besitzer abstimmen). Kein Modell nötig für die Logik; Nutzen-Messung mit WP-B.
- **Status 2026-10-09: Code fertig und live im Durchlauf** (Thread „JEF-Fokusschleife bauen“). `code/v13/focal.py`, Tests `tests/test_focal.py` (10 grün, volle Suite 559 grün), Schemas `FocalItem` (§93-Felder Pflicht), `FocalCycle`, `InquisitionStep`, `ActionSelection` in `contracts.py`, Befehl `:focal`.
  - C4 `FocalLoop.run` in `runtime._turn` ersetzt den festen Einmal-Re-entry: Kandidaten (B1/B2-Offers, Memory, gehaltene Slots) → Priorität §93 (Ziel, Konflikt, Unsicherheit, Salienz, Nutzen, Quellqualität − Redundanz − Kosten) → Koalition (Kapazität = Effort-`focal_slots`, Schwelle §59 .45, Salienz-Interrupt) → Inquisition bei Trigger → Entscheidung §3.4.6 (QUERY_A/B gezielt, INCORPORATE_A/B/AB, IGNORE) → Runden bis Halt/Budget/Deadline. Runden aus Effort-Plan (Age-gedeckelt), Re-entry-Budget = `max_reentry`.
  - `C4.uncertainty_coupling_gain` (§85.4, BOOT .5): Unsicherheit senkt die Koalitionsschwelle und koppelt Memory stärker an. Cross-scale-Links §3.2A/§8.2A (Gist-Slot ↔ Fine-Slots über überlappende SourceRefs).
  - B4 `Workspace` je Session (`C4_WORKSPACE:<session>`): ACTIVE/REACTIVATABLE/EPISODIC_POINTER, Zerfall pro Turn, Quelle/Generation weg → Slot weg. Frühere Items bleiben PRIOR_HYPOTHESIS, zählen für Konflikt, gehen nie als aktuelle Offers in die Antwort.
  - WP-N2-Kern mit drin: `Inquisition` P1 (Hypothese) ↔ P2 (Kritik); Age 0/1 erzwungene Folge P1→P2, ab Age-Recht `deliberation_modes` zusätzlich VERIFY/COMPARE/CONSTRAINT_CHECK. Trigger: B1/B2-Widerspruch, Memory-Widerspruch, Salienz, Nutzer „gründlich/step by step“, Effort-verify, World-Fehler (Flag, noch nicht gespeist). CONTESTED lenkt die Re-entry auf die schwächer belegte Hälfte. Halt fest budgetiert (§10.1 Phase B); gelernter Halt-Kopf berät nur einmal.
  - WP-N4-Kern mit drin: C5 `ActionGate` mit §85.5-Kandidaten (SOURCE_COPY, C3, B1, B2, ASK_USER, EXTERNAL_TOOL), Rechte-/Ressourcen-Unterdrückung, Alternativen; BOOT-Nutzen reproduzieren die alte Route→Rolle-Tabelle exakt (Fokus-Unterstützung nur innerhalb der Marge). ASK_USER wird angeboten, nicht ausgeführt; Tools ab Age-Recht.
  - WP-N5 eingehängt: A4-Spannensalienz nach `percept()` (High-Res-Re-looks als exakte Quellspannen gewährt), Thalamus-Gain pro Runde aus Konflikt (focal-Gain → Kopplung, workspace-Gain → Schwelle, Interrupt → Salienz), Re-entry als `AttentionRequest` JEF→B1/B2 unter Event-Budget, `outcome` (+.5 wenn die Re-entry in die Koalition kam, sonst −.25).
  - Grenzen: Konflikt/Unsicherheit sind lexikalische Proxys (Zahlen, Verneinung, Hecken), nicht kalibriert; alle Gewichte BOOT. `cfg.max_reentry` ≤ 1 deckelt Re-entries pro Turn.
  - Offen/nächste Schritte: World-Vorhersagefehler als Inquisition-Trigger speisen (WP-N9/World); Age-Rechte an `cognition.offer` (Gist-Auflösung `age.gist_resolution`); `cfg.max_reentry` > 1 erst nach Nutzen-Messung; Nutzen-Messung G-FOCAL-CAPACITY-003 / §24.27 auf dem Cloud-Prüfstand (WP-N12); P1/P2 als gelernter Raum (WP-N2 Rest, Trajektorie zuerst); C6-Egress und echte Tool-Ausführung (WP-N4 Rest, mit WP-K).

### WP-N2 Inquisition P1↔P2 (§10, §10.1, §24.17)
- **Teilweise erledigt in WP-N1** (Scaffold P1↔P2, Modi, Trigger, CONTESTED → gezielte Re-entry). Rest: gelernter Deliberationsraum, World-Fehler-Trigger, Halt-Kopf erst nach stabiler Trajektorie.
- **Status 2026-10-09: Rest erledigt (Pakete A).** `code/v13/deliberation.py`, Doku `code/docs/DELIBERATION.md`, Tests `tests/test_deliberation.py` (Suite 671/671 grün).
  - Handoff: Der World-Fehler-Trigger wird jetzt gespeist (FF-Überraschung, N9-MIXED). Der gelernte Modus-Raum gilt pro Triggermenge; SHADOW ist Standard, `:delib active` nur explizit und mit Age-Recht. Der Halt-Kopf steuert erst bei stabiler Trajektorie (10 Läufe, ≥80 % gleiche Entscheidung, Zyklenspanne ≤1), sonst entscheidet das BOOT-Gerüst; die Auslesung wird trotzdem geloggt (`halt_decision.steering`).
  - Offen: Nutzen-Messung auf dem Cloud-Prüfstand (WP-N12).
- Modi Hypothese/Kritik/Verifikation/Constraint-Check im Fokus, ausgelöst durch B1/B2-Widerspruch, Salienz, World-Fehler,
  Memory-Widerspruch, Nutzerwunsch. Tiefe aus WP-D-Budget. Trajektorie zuerst, gelernter Halt-Kopf erst danach.
- Nach WP-N1.

### WP-N3 JEF↔Gehirn lernen (G3C, L4.3, L4.4, §3.4.2–3.4.7)
- Broadcast-Cache als gelerntes Paket statt nur JSON, Top-down-Query (welche Frage an B1/B2), Offer-Nutzen lernen
  (welche Offers helfen der Antwort), Observer-Pass-Nutzen §24.25, JEF-KV/Broadcast-Bridge §24.26. Schatten + Freigabe wie WP-I.
- **Status 2026-10-09: erledigt** (Thread „Nächste offene Pakete A“). `code/v13/jefbridge.py`: JEF_BROADCAST_CACHE je Turn (gehashte symbolische Latents, ehrlich markiert), JEF2B-Feld-Gate mit Exploration + Mit/Ohne-Nutzenvergleich (§24.26), Offer-Nutzen-Modell (Antwortabdeckung + Bewertungen), gelernte JEF-Entscheidung im Schatten neben Scaffold, Re-entry-Werte → QUERY_PACKET-Vorschlag, Observer-Pass-Statistik §24.25. Hooks: runtime (Cache, learn_turn), cognition (Brückenfelder), focal (`utility` nur ACTIVE), inputs (Bewertungen). 8 Tests `tests/test_jefbridge.py`, volle Suite 639 grün. Übergabe: `code/docs/JEF_BRIDGE.md`. Offen: native JEF2A/B-Projektoren (brauchen Latents), Query-Vorschlag in focal einhängen, Observer-Frequenz an WP-D.
  - **2026-10-10: Query-Vorschlag in focal + Observer-Frequenz an WP-D erledigt (Pakete A).** `FocalLoop._jef_target`/`JEFBridge.query_target` (gelerntes Re-entry-Ziel, nur `:jef active` + ≥3 Belege je Ziel, nie zusätzlicher Re-entry, immer als `jef_query` im FocalCycle geloggt); `JEFBridge.observer_scale` senkt die Observer-Zeit im Runtime-Durchlauf auf ≥0,5 bei unnützen Observer-Offers (nur ACTIVE, sonst `meta['jef_observer']`). Doku-Nachtrag `code/docs/JEF_BRIDGE.md`, Tests `FocalHookTests`. Offen: Nutzen-Messung mit Modell, native JEF2A/B.

### WP-N4 C5 Action Gate + C6 Egress (§6.4, §11.1, §85.5)
- **Teilweise erledigt in WP-N1** (`focal.ActionGate`: Kandidaten, Unterdrückung, Rechte, BOOT = alte Tabelle). Rest: gelernte Auswahl, C6-Schema-Adapter, Tool-Ausführung mit WP-K.
- **Status 2026-10-09: Rest erledigt (Pakete A).** `code/v13/actionlearn.py`: getrennte promote/suppress-Pfade aus eigenen Modulatoren (kein Skalar-Reward), SHADOW-Vergleich mit BOOT-Tabelle im ActionSelection-Paket, ACTIVE nur per `:c5 active` (±0,2, Rechte gewinnen); C6-Egress-Typprüfung (`EgressCheck`, schreibt nie um, TOOL_CALL ohne Shell-Strings). Bewertungen fließen ein. 4 Tests, Suite 665 grün. Übergabe: `code/docs/C5_LEARNING_C6_EGRESS.md`. Offen: Tool-Ausführung/Transaktion mit WP-K.
- C5 wählt zwischen Kandidaten (Direkt, C3, B1/B2-Sprecher, Skill, Tool) mit Rechten statt fester Route→Rolle-Tabelle
  in `runtime.py`; Basalganglien-Idee: gelernte Auswahl + Hemmung, nicht nur Go/No-Go. C6 als Schema-Adapter vor C7.
- Zusammen mit WP-K (Commit-Point, Transaktion).

### WP-N5 Aufmerksamkeit und Gain (F1, §4B, §5.1, A4, §60)
- `AttentionRequest`/`AttentionResponse` nach §4B, thalamische Gain (dynamische Kopplungsstärke zwischen Teilen),
  A4-Wahrnehmungs-Salienz. Speist WP-N1 und WP-F.
- **Status 2026-10-10: Live-Hook erledigt (Pakete C).** A4 + Re-entry-Requests liefen schon live. Neu: N10-Modulatoren der letzten 3 Turns speisen `modulate` (`attention.recent_modulators`); A4-High-Res-Spans bekommen nach der Antwort ein §4B.4-Ergebnis aus Cue-Abdeckung (`source_outcome`); C5 nutzt die thalamische Action-Gain (`ActionSelection.action_gain`). Doku `code/docs/ATTENTION.md`. Offen: MEMORY/WORLD-Provider, Nutzen-Messung mit Modell. **2026-10-10: MEMORY-Provider erledigt (Pakete C):** bei B1/B2-Konflikt fragt JEF per F1-Request einen zweiten Abruf an, Cue = die widersprechenden Offers; neue Erinnerungen konkurrieren sofort in der Koalition, Ergebnis (+.5 in Koalition / −.25 sonst) lernt `recall|MEMORY`. Test in `tests/test_focal.py`, volle Suite 793 grün. WORLD-Provider bewusst nicht: World-Vorhersage betrifft Aktionen, kein Koalitions-Inhalt.
- **Status 2026-10-10: WP-K-Rest „TOOL_CALL als C5-Kandidat im Live-Turn“ erledigt (Pakete C).** `v13/toolstep.py`: Rechen-Vorschlag → `ToolProposal` → IH-H29-Politik → EXTERNAL_TOOL-Kandidat in C5; erlaubt (Nutzer + Age 1) läuft calc als Transaktion und das Ergebnis geht als `TOOL_RESULT` an den antwortenden Körper; Age 0 = SHADOW mit Übereinstimmungs-Zählung. 6 Tests, volle Suite 772 grün. Doku `code/docs/TOOL_STEP.md`. Offen: Werkzeugwahl über Needle-Kopf statt Regex.
- **Status 2026-10-09: Code fertig und live eingehängt** (Thread „Aufmerksamkeit und Thalamus-Gain“; Live-Hook geprüft von Pakete A: `runtime._turn` ruft `perceive_packet`/`admit` nach dem Percept, `FocalLoop` nutzt `modulate`/`admit`/`outcome`). Nutzen-Messung offen. `code/v13/attention.py`, Tests `tests/test_attention.py` (15 grün, volle Suite 549 grün), Schemas `AttentionRequest`/`AttentionResponse` in `contracts.py`, Befehl `:attention [status|edge <Kante>|shadow|active]`.
  - Inhalt: §4B-Vertrag (Ziele A_SOURCE/B1/B2/MEMORY/WORLD/TOOL/SELF, Gründe, Budget, Ablauf; Antworten GRANTED/NOT_AVAILABLE/TOO_EXPENSIVE), Zulassung pro Event unter Budget × Ressourcendruck; thalamische Gain je Kante (§60 GAIN.*), getrieben von Salienz (SAL.*) und Vorsicht (CAUT.*) als getrennte Größen, relaxiert pro Event zur Basis; Interrupt ab Salienz .6; A4-Spannensalienz (§51.5) ohne Chunk-Verlust + High-Res-Anfragen; Lehrer-Sicht nur Age 0, markiert, Priorität gedeckelt; gelernter Nutzen-Prior läuft SHADOW, ACTIVE nur per `:attention active`.
  - Schnittstellen für WP-N1: `controller(runtime)`, `rank(candidates)` → `admission_score`, `offer_features(offer)`, `modulate(...)['interrupt']`, `coupling('E_C4_B4_GAIN')`. Für WP-N10: Gewährung → `neuromod.touch('attention_policy')`, `outcome(response_id, nutzen)` → `neuromod.signal(path='attention_policy')`; `from_modulators(channels)` liest N10-Kanäle. **Bitte WP-N10:** `'attention_policy':'control'` in `neuromod.COMPONENT_KIND` (heute Default `skill`).
  - Handoff/offen: Einhängen in `runtime._turn`/`cognition.focal` (Besitzer WP-N1/WP-D): `perceive_packet` nach `percept()`, `modulate` aus B1/B2-Widerspruch + World-Fehler, `admit` mit Providern (Memory/World/B-Re-entry), `outcome` nach der Antwort. Nutzen-Messung mit WP-B/WP-N12.

### WP-N7 Context OS + Cache-Policy (§8.3–8.6, §74, G6B, R6)
- Was roh, was komprimiert in den Modellkontext geht, „Re-entry statt Re-prefill“, KV-Cache-Entscheidungen als
  Kontroll-Aktion, Warm/activity-silent Memory. Native Primitiven (§8.6) nur als Forschung.
- **Status 2026-10-09: erledigt + gemessen** (Thread „Nächste offene Pakete A“). Cloud-Messung: Layout `append_only` (jetzt Standard) spart 44–62 % neu vorgefüllte Tokens und ~45 % Prefill-Zeit auf C3/B1/B2 (hybride Bodies können nur fortsetzen, nicht zurückspulen), `stable_prefix` nur 4–18 %; `bench-results/context-cache-20261009/report.json`. `code/v13/context_os.py`: ContextPlan über die §8.3-Schichten, extraktive Kompression mit Exact-Span-Pinning, Exact-Restore §8.4 (Zahlen/Code/wörtlich/Quellenkritik/Inquisitions-Konflikt), Budget-Planung vor dem Runner, Cache-Layout `stable_prefix` (Re-entry statt Re-prefill, nur mit geprüfter Template-Fähigkeit `consecutive_user`, G6B), Präfix-Wiederverwendung geschätzt + echte `cache_n/prompt_n` gemessen, Warm/activity-silent Memory §9.1, CTX-Regler §74 mit Exact-Recall-Sperre, gelernter Prior SHADOW, N10-Pfad `context_policy`. SHADOW ist Standard (Modell sieht byte-gleich den alten Kontext); `:ctxos active` schaltet um. Hooks in `runtime.py` (Warm nach Recall, Plan beim Prompt-Bau, observe nach Antwort), `:ctxos`, Schema `ContextPlan`. 17 Tests `tests/test_context_os.py`, volle Suite grün. Doku/Übergabe: `code/docs/CONTEXT_OS.md`; Messskript `scripts/context_cache_bench.py`. Offen: §8.6-Primitiven (Forschung), Ratings→`outcome`, Ausgabe-Adapter vor ACTIVE prüfen.

### WP-N8 Event-Segmentierung + Kausaler Gedächtnisgraph (A1, §9.3–9.5, §48.15)
- **Status 2026-10-10: Rest erledigt (Pakete C).** Assoziativer Abruf (`Episodes.spread`, SHADOW Standard, `:episodes spread on`), keine Selbstverstärkung durch Ausbreitung, Consolidation stellt Staging-Episoden zuerst. 5 Tests, volle Suite 766 grün. Offen: A1 innerhalb eines Textes (cognition.py), gelernte Grenz-Politik.
  - **2026-10-10: A1 innerhalb eines Textes erledigt (Pakete A; Pakete C hatte parallel `cognition.event_segments` gebaut, der Stand auf Platte ist die Pakete-A-Version).** `episodes.text_segments` über `cognition.segments(..., mode='event')`: Noisy-OR der §51.2-Gewichte (Chunk-Prior .40, Absatz/Satz .25, Themenwechsel .35, Frage↔Aussage .30, Prosa↔Liste/Code .30) ≥ 0,5, 25–150 % der Zielbreite, exakte Spans nie geschnitten, verlustfrei mit SourceRef. `cfg segment_mode` = `percept` (Standard: PerceptPacket/A4) | `all` (+ B1/B2-Sicht) | `fixed`; Body-Ansichten standardmäßig byte-gleich. Tests `tests/test_text_segments.py`, Suite 808 grün. Offen: gelernte Grenz-Politik.
- **Status 2026-10-09: erledigt (Pakete B).** `code/v13/episodes.py`: Episodengrenzen aus mehreren Signalen (Noisy-OR mit §51.2-Gewichten, Überraschung allein schneidet nie, Pause/Korrektur/Sleep schneiden), Gedächtnisgraph mit TEMPORAL/CORRELATIONAL/CAUSAL/HYPOTHESIS (kausal nur mit Eingriff), Aufnahme-Stufe je Episode, Erinnerungs-Stärke mit Zerfall und Vergessens-Vorschlägen (Löschen nur per `:forget`). Hooks: `runtime._turn` (finally), `memory.feedback`/`forget`, Sleep (voller Sleep schließt Episoden, Traum = Hypothese). `:episodes`. Tests `tests/test_episodes.py`, volle Suite grün. Doku + Übergabe `code/docs/EPISODES.md`. Offen: Consolidation liest Stufe noch nicht, `related_memories()` nicht im Abruf, A1 innerhalb eines Textes (cognition.py), gelernte Grenz-Politik.
- Ereignisgrenzen aus Vorhersagefehler + Kontextwechsel statt fester 240-Zeichen-Stücke; Gedächtnisgraph mit
  Ursache/Folge-Kanten; gelernte Memory-Admission. Baut auf WP-H/WP-S2.

### WP-N9 Selbstmodell, Körpergefühl, Corollary-Rückkopplung (§7.3–7.5, §20.2, §20.4, §85.7, §24.28)
- Self-Model über `world.self_state` hinaus (Fähigkeiten, Grenzen, offene Ziele), Interozeption (RAM/Hitze/Last als
  Signal an JEF), Corollary-Kopie geht an B1/B2 zurück, bevor die Welt antwortet; Self-Messaging; Self-Edit nur als
  Vorschlag (Age-Recht, Nutzerfreigabe).
- **Status 2026-10-09: erledigt** (Thread „Nächste offene Pakete A“). `code/v13/selfmodel.py`: Selbstmodell §7.3 als Aggregat (`:self model`), Körpergefühl §7.4 mit Modulationen (Kontextbudget an WP-N7, Dream/Learning, Schlafdruck) und Corollary-Dämpfung nur in der Salienz, `SelfCorollary` vor jedem Dispatch + `SelfWorldAttribution` SELF/EXTERNAL/MIXED/UNCLEAR mit Residuum → N10 `world_prediction_error`, Corollary-Sicht an B1/B2 (`self_corollary` in `cognition.offer`), Self-Messaging §20.4 (Relevanz, Rate-Limit, Anti-Spam, HELD unter Age 4), Self-Edit §20.2 (nur Vorschläge, Nutzerfreigabe, Context-Policy rücknehmbar, safe_config → AG8). 18 Tests `tests/test_selfmodel.py` (inkl. alle G-SELF-WORLD-005-Fälle). Doku/Übergabe: `code/docs/SELF_MODEL.md`. Offen: Redmi-Sensoren (WP-R), Tool-Aktionen (WP-K) mit eigenen Kanälen.

### WP-N10 Neuromodulation und Eligibility (§12.1–12.3, Layer 6, §16.3, §35, §62–63, §85.10)
- Echte Eligibility-Spur pro Pfad (wächst bei Aktivität, zerfällt), typisierter Modulator-Bus (Überraschung, Neuheit,
  Korrektur, Erfolg, Kosten, Veto) der Lernbudgets wirklich steuert statt nur geloggt zu werden, Consolidation Tag,
  Metaplastizität aus `plasticity.py` daran koppeln. Reines Python, sofort machbar.
- **Status 2026-10-09: erledigt** (Thread „Neuromodulation und Lernspuren“). `code/v13/neuromod.py`: Zwei-Zeitskalen-Eligibility aus den vorhandenen LearningTrace-Paketen, typisierter Modulator-Bus (epistemisch/instrumentell getrennt, Gewichte je Lernart, Credit-Map, Sicherheits-Veto), Gate-Faktor e×M×P skaliert LR + Update-Norm in `plasticity.budget` (über `learning.training_config`), Consolidation Tag, Sleep C + AG6 eingehängt, `:neuromod`. 17 Tests in `tests/test_neuromod.py`, volle Suite grün. Details/Übergabe: `code/docs/NEUROMODULATION.md`. Offen: Spuren für Callosum/Workspace/C_focal kommen mit WP-N1/N7; gelernter Metaplastizitäts-Kopf; Wirkung auf echten Läufen messen.

### WP-N11 MoE-Körper (§81, §87.1, §91, §16.2.1, B3-H6; Nutzerwunsch „zwei verschiedene MoE-Hälften“)
- **Status 2026-10-09: in Arbeit (MoE-Hälften)** (Thread „Zwei echte MoE-Hälften“): B1 LFM2.5-1.2B + B2 Qwen3.5-0.8B über AG0-Slots + AG13-Residenz end-to-end, STEP2-Messung.
- Zugang/Runner für einen kleinen MoE-Körper klären (MobileMoE-S-QAT gated + noncommercial; Alternativen prüfen),
  Detail-Hälfte mit mehr aktiven Experten, Router-Stabilitäts-Gate, Pre-Router-Interferenz-Monitor, Experten-Deltas.
  `agi/residency.py` ist schon da. Braucht WP-B und Redmi-RAM-Messung (WP-R).

### WP-N12 Messsuite + Parameter-Register + Abschluss-Audit (§24, §31, §79, §99, 0P, IH-H5, IH-H28, IH-H36)
- **Status 2026-10-09: erledigt (Pakete B).** Register `code/v13/register.py` (`:register`): 301 Blueprint-Regler aus §49–§78 + §78-Age-0-Profil (`scripts/build_knob_register.py` → `specs/blueprint-knobs.json`), 60 per `specs/knob-map.json` an Code-Konstanten gebunden, alle MATCH, 0 DRIFT; Abdeckung ehrlich 20 %, Rest DECLARED_ONLY; PathSpec der lernbaren Pfade. Gate-Graph `specs/gate-graph.json` + `code/v13/gates.py` (`:gates`): 19 Gates, §100-Kriterien je Gate, Mocks zählen nie als echte Daten, Ergebnis-Verdikte binden; Stand 8 GREEN, 11 PARTIAL. Messsuite `scripts/measure_suite.py` / `cloud_bench.sh --suite`: §24 und §99 auf Tests/Artefakte/Verdikte abgebildet (`specs/benchmarks.json`); Ergebnis `bench-results/suite-20261009/` (4 MEASURED, 23 TESTED, 1 MEASURED_FAILING = 24.11 Callosum, 2 NEEDS_REDMI = 24.14/24.33, 5 NOT_IMPLEMENTED = 24.18/24.19/24.26/24.30/24.31). Tests `tests/test_register_gates.py`, volle Suite 686 grün. Doku + Übergabe `code/docs/MEASUREMENT_SUITE.md`. Offen: weitere Regler in knob-map binden, wenn Pakete sie bauen; R0–R9 und Thin-Control-Budget noch nicht als eigene Läufe; Redmi-Messungen (WP-R).
- Die 34 Kern-Benchmarks §24 und Experimente R0–R9 als ein Befehl auf dem Cloud-Prüfstand; Pflicht-Ablationen §99;
  KnobSpec/PathSpec-Register für alle Regler aus §49–§78 (Age-0-Profil §78); Gate-Abhängigkeitsgraph; Thin-Control-Budget.
- **Status 2026-10-10: IH-H36-Neuabgleich `ABDECKUNG.md` erledigt (Pakete B).** 19 Zeilen aktualisiert (u. a. A4/F1/Gain/Workspace jetzt ✅ live, Gate-Graph ✅, Needle-Benchmark ✅, Vision/Full-Duplex/Sparse-Memory/Drift-Anker 🟡); Zählung neu: 85 ✅ / 111 🟡 / 11 ❌ / 3 ⏸ von 210 (Erstabgleich 51/109/45/5). Offene ❌ fast nur MoE (WP-N11), B3 L2–L4 (WP-J), native Cache (G6B) und Redmi (WP-R).
- **Nachtrag 2026-10-09 (Pakete A):** §22.6 Speculative Decoding gemessen (`code/scripts/spec_decode_bench.py`, `bench-results/spec-decode-20261009/`): greift auf den hybriden LFM2/Qwen3.5-Bodies in b10964 nicht (0,92–0,98×, Draft +330 MB) → bleibt aus. ABDECKUNG-Zeilen für N1/N8/N3 auf Stand gebracht.

### WP-AB §99-Pflicht-Ablationen ohne Modell (Eligibility, Modulatoren, Prozeduralisierung, Age)
- **Status 2026-10-10: erledigt (Pakete A).** `code/v13/ablation99.py`, Lauf `code/scripts/ablation99_bench.py`, Tests `code/tests/test_ablation99.py` (Suite 761 grün), Ergebnis + Übergabe `bench-results/ablation99-20261010/README.md`, Einträge in `specs/benchmarks.json`. Echte Module (Neuromod-Gate, FastForward, AgeControl) auf synthetischem Strom, 5 Saaten, gleiche Ströme für alle Kontrollen:
  - Prozeduralisierung belegt: −52 % Kosten ggü. voller Deliberation, 0,7 % vs. 24,6 % Fehler der statischen Abkürzung.
  - Typisierte Modulatoren schlagen scalar reward und human-only 5/5, outcome-only 4/5.
  - Eligibility schlägt gradient only / random mask 5/5, aber nicht recency only (1/5).
  - **Gate allein lernt Traum-/Eigen-Labels** (wirkt pro Pfad, nicht pro Beispiel); erst `guards.enforce_data_mix` schützt (Endfehler 0,65 → 0,17).
  - **Age nicht belegt:** Rauschen → Herabstufung → mehr Plastizität (verrauschte Phase 0,18 vs. conservative 0,09).
  - **Zur Nutzer-Prüfung:** Age-Korrektur als Flag `age_plasticity_policy=stable_reopen` in `age.py` (Standard bleibt `boot`): Halten der Plastizität nach Herabstufung, Wiederöffnen erst bei anhaltenden Fehlern. Verrauscht 0,18 → 0,14 (5/5), Zielwechsel 0,025 → 0,033 (langsamer). Nicht eingeschaltet.
  - Offen: Rausch-Schätzung für Age, Datenmix vor jedem Trainingsjob sicherstellen, Strom mit verzögerter Belohnung für die zweite Zeitskala.
  - **2026-10-10: „Rausch-Schätzung für Age“ erledigt (Pakete E).** `age.py`: Rausch-Schätzer je Fähigkeit (winsorisierte MAD der Kompetenz), Flag `age_plasticity_policy=noise_aware`: Fehlschläge im Rauschband zählen nicht zur Herabstufung, Plastizität und Fehler-Wiederöffnung werden mit dem Rauschen gedämpft. Messung `bench-results/age-noise-20261010/`: verrauschte Phase 0,073 (boot 0,175, stable_reopen 0,129, conservative 0,086; 5/5), Zielwechsel langsamer (0,079 vs. 0,053). **Nicht eingeschaltet, Nutzerwahl boot | stable_reopen | noise_aware.** Test `test_ablation99.py::AgeNoiseAware`.
  - **2026-10-10: „Strom mit verzögerter Belohnung“ erledigt (Pakete E).** `ablation99.delayed_ablation` (Bursts, Ergebnis 3–40 Ereignisse später, 30 % falsche Labels unbestätigt), echtes Neuromod, 5 Saaten, `bench-results/delayed-reward-20261010/`. Gate schlägt recency only und budget-gleichen Gradienten 5/5, aber **langsame Spur bringt nichts** (v13 = fast only 0,157) und Trennung bestätigt/unbestätigt nur 1,14× (Orakel 0,003): Credit pro Beispiel muss aus der Beispiel-Herkunft kommen (Datenmix/AG6), nicht aus längerer Eligibility. SLOW_MIX bleibt BOOT. Test `test_ablation99.py::DelayedReward`.
  - **2026-10-10: „Datenmix vor jedem Trainingsjob“ erledigt (Pakete E).** `guards.item_origin` + `mix_for_training` (Herkunft je Item: explizites `origin`, Traum/Hypothese → dream, modellgeschriebene Ziele wie `rated_answer`/TTT → self, sonst human). AG6 `WeightConsolidation.stage` kürzt auf die Quoten (Mensch ≥ 60 %, self ≤ 10 %, dream ≤ 5 %, seed 0) oder meldet `DATA_MIX_FAIL`; `train()` prüft vor `trainer.fit` erneut. TTT-Kandidaten tragen `origin:self`, SDFT `origin:human_replay` (Inhalt = Korrektur). Andere Trainer (Retrieval/Output/Control) lesen nur menschliche Labels (geprüft). Tests `test_learning_invariants.py::DataMixBeforeTraining`; `test_lora_trainer` angepasst (1 Fakt lässt keinen Platz für eine bewertete Modellantwort). Suite 792 grün.

### WP-N13 AG-Module in den Live-Durchlauf (Querschnitt)
- **Status 2026-10-09: erledigt (Pakete B).** `code/v13/agi/live.py`: AG4 vertrauter Routen-Skill setzt die Route nach `_route`; AG9 kalibrierte Antwort-/Routen-Konfidenz hebt Effort-Unsicherheit (zweiter Versuch) oder setzt Abstain-Flag, Labels aus Bewertungen, Korrekturen, Routen-Feedback; AG2 Vorhersage vor jeder Antwort-Aktion, Ergebnis danach; AG11 Präferenz/Stil-Feedback → Annahmen; AG0 installierte Modelle → Slots, neue Revision → Tausch-Vorschlag. Fail-open, `:live`. Tests `tests/test_agi_live.py`, volle Suite 603 grün. Doku + Übergabe `code/docs/AGI_LIVE.md`. Offen: Executive liest Nutzer-Annahmen nicht in constraints, Abstain nur Flag (C5 ASK_USER bei BOOT aus), Tool-Skills erst mit WP-K.
- **Status 2026-10-10: Rest erledigt (Pakete E).** AG11-Annahmen (Konfidenz ≥ 0,5) → `ExecState.user_beliefs` + C2-Sicht + beschriftete `USER_MODEL`-Schicht im Antwort-Kontext, nie in `constraints`. AG9-Abstain → C5: SHADOW protokolliert, `:live ask active` (nur Nutzer) lässt ASK_USER gewinnen, C3 stellt eine kurze Rückfrage; exakte Ausgaben bleiben. Tests `test_agi_live.py::ClarifyAndUserModel`, volle Suite 788 grün. Doku `code/docs/AGI_LIVE.md`. Offen: Nutzen von Rückfrage vs. Raten an echten Turns messen.
- Heute rufen nur `:growth`, Sleep und Scheduler die `agi/`-Module. Einhängen in `runtime._turn`: Metakognition (AG9)
  an Effort, Grounding (AG2) an jede Aktion, Nutzer-Modell (AG11) an C1, Skills (AG4) an C5, Slots (AG0) an `ModelManager`.

### WP-N14 Live / Full-duplex im Text (§4A.4, G10D, §24.30)
- **Status 2026-10-09: erledigt, Text-Phase (Pakete B).** `code/v13/duplex.py` (`:duplex status|auto|interrupt|off`): Nachricht während laufender Antwort → CONTINUE / INTERRUPT (Stopp-Wort) / REVISE (Korrektur), Entscheidung ohne I/O unter dem Runtime-Lock; abgeschnittene Antwort bleibt CANCELLED + `provisional` (nie gelernt, nicht in nativer Historie); nächster Turn bekommt `DUPLEX_HANDOFF` (Frage, Teilantwort, Beziehung) und deren Quellen in `context_source_refs`. Telemetrie `duplex`. Tests `tests/test_duplex.py` (§24.30 in der Messsuite), volle Suite grün. Doku + Übergabe `code/docs/DUPLEX.md`. Offen: Audio/Video und Sprach-Barge-in (STEP 11), gelernter Unterbrechungs-Klassifikator, asynchrone Offers in eine laufende Antwort.

### WP-N15 Vision-Gerüst im Lab (STEP8, §18.9, G10B, Teil von §24.31)


---

# QUELLDOKUMENT: ROADMAP_Teil3von3.md

[ROADMAP.md Teil 3 von 3 – ab Zeile 534 der Originaldatei; Teil 2 endet mit der Überschrift „WP-N15 Vision-Gerüst im Lab“]

- **Status 2026-10-10: erledigt (Pakete B).** `v13/vision.py` + `:image` (add/describe/train/look/forget), Doku `code/docs/VISION.md`, Tests `tests/test_vision.py` (7), Bench `scripts/vision_bench.py` → `bench-results/vision-20261010/`. Bild = IMAGE-Quelle mit Regionen-SourceRef (Pixel-Box), RAW EYE 117 Merkmale, Ridge-Student → Text-Embedding, Teacher LFM2.5-VL-450M (+mmproj, `:download vision`, Beschreibung REFERENCE_NOT_FACT, fehlt → fail-open), Rekonstruktion nur Messung. Messung 48 synthetische Szenen: Teacher nennt Farbe/Form 100 %, Position 0 %; Student held-out Retrieval 0,73 (Zufall 0,08) mit EmbeddingGemma, Zero-Shot Farbe 0,92 / Form 1,00 / Position Zufall, obwohl das rohe Auge die Position zu 100 % trägt. **WP-N15b erledigt (Pakete B, 2026-10-10):** Hälften `hl/hr/ht/hb` als Regionen, Training auf allen beschriebenen Regionen, `:image locate <id> <Text>`. Der Student findet die Objekt-Hälfte held-out zu 100 % auf der richtigen Achse (Zufall 50 %), die Lage kommt über die Regionen-Herkunft. **Übergabe:** echte Fotos und Handy-RSS des Teachers ungemessen; nichts im Chat-Turn oder Kern (G10B-Gate offen).

### Ergänzung zu WP-F
- Reflex-Schicht §5.3 und Fast-Forward/Kleinhirn §7.1/§85.6 gehören ausdrücklich dazu (heute fehlen beide).

Reihenfolge-Vorschlag: WP-N10 und WP-N1 sofort (kein Modell nötig, Kern des „Gehirns“), dann WP-N2, WP-N13, WP-N5;
WP-N3/N4 mit WP-I/WP-K; WP-N11 sobald ein MoE-Modell ladbar ist; WP-N12 laufend.

### WP-KAL Startwerte mit echten Modellen einmessen (Cloud-Prüfstand)
- **Status 2026-10-10: erledigt (Runde 2, Qualität)** (Thread „Kalibrierungs-Befunde umsetzen“). Erste Runde: Thread „Werte mit echten Modellen einmessen“. Ergebnis: `bench-results/KALIBRIERUNG.md`,
  Rohdaten `bench-results/kalibrierung-20261009/`. Skript `code/scripts/calibrate_real.py` (ag12|pairs|offers|effort|echo|echo_exact),
  Messwerte je Regler in `code/specs/calibration.json` → `:register` zeigt Feld `calibration` (30 Blueprint-Regler), Tests `tests/test_calibrate_real.py`.
  Keine Code-Defaults geändert (keine Messung stützt eine Änderung klar). AG12 roh: .13–.30 (Qwen3.5-0.8B best), Planungstiefe 0.
- Übergabe/offen: (1) B1/B2-Offer-Prompt in `cognition.py` nennt kein Ergebnis (B1 5 %; mit Lös-Prompt 37,5 %) → umstellen, dann Effort neu messen.
  (2) Offer-Unsicherheit aus Token-Logprobs statt HEDGE-Regex (AUROC .75 vs .50) → Runner muss Logprobs liefern.
  (3) Anti-Echo halbiert Exaktheit beim 230M-C3 (22→12 %), nicht beim 350M → C3 auf 350M oder exakte Antworten ohne Penalties.
  (4) Gains/Neuromod/Coalition brauchen Lernläufe (WP-I/S6) als Zielgröße. (5) Redmi-Zeiten (WP-R), Deutsch später.
- **Übergabe Runde 2 (erledigt, Details `bench-results/KALIBRIERUNG.md` Runde 2):** C3 = LFM2.5-350M (`specs/models.json`, alter Eintrag unter `previous`); C3-Antwortregel ohne „Nothing verified“-Zwang (Aufgaben 16→38 %, Gedächtnis 7→73 %); STEP2 B1+B2 .58 > B1 .45 (Gate rot nur wegen „B2 allein gewinnt nie“); Effort: Bodies wecken hilft (.40 vs .32), Schwellen BOOT; Acceptance 13/16, memory-retrieval C3-Teil grün. Offen: eigenständig stärkerer B2, B1-Detail-Antwort nutzt Korrektur nicht, control-calibration `support` braucht mehr Daten, 230M-LoRA (WP-S6) auf 350M neu lernen, Redmi-RAM/Latenz 350M (WP-R). Rohdaten `bench-results/kalibrierung2-20261009/`.
  Erledigt: (2) Runner holt bei Offers Token-Logprobs (`n_probs`), `focal.token_confidence` + `offer_uncertainty` nutzen das
  unwahrscheinlichste Summary-Token (AUROC Fehler B1 .52→.88, B2 .61→.76; zweite Stichprobe .83/.75), Pivots je Body in `focal.TOKEN_UNC`.
  (1) Offer-Prompt jetzt `cognition.offer_instructions` mit `OFFER_STYLE='solve'` (B1 5→33 %, B2 13→35 % Ergebnis genannt; `cfg offer_style=hypothesis` = alt).
  `tests/integration_retrieval.py` suchte nach dem deutschen Präfix → Quellen-Check war seit WP-V9 immer rot (behoben). Tests `tests/test_kal2.py`.
  Neue Messskripte: `calibrate_real.py effort_rt|rules` (Laufzeit-Prompt, nativer Pfad).
hprobe 

## Restarbeit aus den 🟡-Zeilen von ABDECKUNG.md (Pakete WP-T, angelegt 2026-10-10 von Pakete B)

Quelle: 111 🟡-Zeilen nach dem IH-H36-Neuabgleich. Nur Arbeit, die **ohne Handy** geht. Nicht hier, weil schon vergeben:
B3-Leiter (WP-J), MoE-Hälften (WP-N11), echtes Gewichts-Lernen/LoRA/TRAIN_RUNNER (WP-I, WP-S6, Thread „Echtes Lernen“), Redmi (WP-R).
Vor Beginn Status-Zeile „in Arbeit (<Thread>)“ setzen; Tests + Doku + Übergabe wie üblich.

### WP-T1 JEF-Steuerung vervollständigen (§3.3.0–3.3.3, §3.4.7, §4.4, G4)
- **Status 2026-10-10: erledigt (Pakete C).** `v13/fastpolicy.py`: Fast-Köpfe skill/memory/channel auf dem geteilten C2-Embedding (gleicher Label → `:learn` → Gate → `:approve`-Weg wie wake, ohne Freigabe nur Scaffold); `C2ExecutivePacket` (Tool, Memory-Key, Antwort-Typ, Quelle je Feld; Needle-Schema bewusst unverändert wegen control_calibration); Re-entry-Frage `jef_query` an B1/B2 (on/off/measure, Koalitionsrate je Arm); DEEP_FOCAL bis 2 Re-entries mit Stopp bei stabiler Trajektorie (`max_reentry` 2, Age 0 = 1). Tests `test_fastpolicy.py` (13), Suite 839 grün. Doku `code/docs/JEF_FAST_POLICY.md`. Offen: echte Labels, Fokus-Wirkung mit Modellen (WP-T3).
- JEF_FAST_POLICY: Köpfe für skill/memory/channel neben route/wake/halt (Schatten, gleiche Freigabe-Logik).
- C2-Needle liefert strukturierte Pakete (Tool-Wahl, Memory-Key, Antwort-Typ), nicht nur Route.
- Top-down-Query: QUERY_PACKET aus `jefbridge` steuert `focal` (welche Frage an B1/B2), Wirkung mit/ohne messen.
- Ziel-gerichtetes Re-entry: mehr als ein B1-Neuversuch, Abbruch nach stabiler Trajektorie, Budget aus WP-D.

### WP-T2 Age-Rechte überall (§3.3.0 C0, §17.4, §17.5)
- **Status 2026-10-10: erledigt (Pakete E).** `age.RIGHT_CAPABILITY` + `AgeControl.may/rights`: jedes Recht gilt an der Decke seiner Fähigkeit (tool, language, memory_skill, routing_skill, body_port), sonst System. `executive.permission_flags` (Age je Fähigkeit, gewährte Rechte, Ressourcenmodus; Tool-Ausführung/Body-Training nur mit Age-Recht). Effort/Fokus (`age_limits`), Gist (Breiten-Anpassung erst mit `adaptive_gist_grouping`), Attention (language-Age), Cognition (Age-Hülle im Broadcast an B1/B2, nur über Age 0), Sleep/Scheduler/`age_allows` über `may`. `agi/maturity.feed/turn_feed`: Nachweise für System + gemessene Fähigkeiten nach jeder vollen Nacht und live aus Turns (max. 1/h, nur bei neuer Erfahrung); vision/audio/social/body_port bleiben ehrlich 0. Tests `tests/test_age_rights.py` (4), Suite grün. Doku `code/docs/AGE_RIGHTS.md`.
- `ExecState.permission_flags` aus Age je Fähigkeit statt fester Flags; Cognition, Gist, Focal, Attention fragen Age ab.
- `agi/maturity.py`-Nachweise live aus Turns/Sleep einspeisen; Test „Age-Stufe ändert erlaubte Pfade“.

### WP-T3 Nutzen-Messungen mit Modell in der Cloud (G3D, G5, G5B, G1B, A4/F1)
- **Status 2026-10-10: erste Runde erledigt (Pakete A).** `code/scripts/utility_bench.py`, Ergebnis `bench-results/utility-20261010/` (README + `utility.json` mit Verdikt). 9 Arme × 12 Aufgaben mit echtem C3/B1/B2, Baseline 3× für das Rauschband: **kein Arm außerhalb des Rauschens** (bestanden 0,42–0,58); Koalition, Inquisition, Adaptive Effort, Gist aktiv, Attention aktiv, coupling_gain 0/1 zeigen keinen messbaren Nutzen; `effort_low` (Fokusschleife faktisch aus) ist nicht schlechter. Identische Läufe reproduzieren nur 4–5/12 Antworten (Observer-Fristen). `uncertainty_coupling_gain` bleibt BOOT 0,5. G-FOCAL-CAPACITY-003 hat jetzt echte Daten + Ablation, Verdikt False → EVIDENCE_NOT_PASSING. Offen: deterministische Observer-Fristen im Bench-Modus, 60–100 Aufgaben mit B1/B2-Widerspruch.
- Ein Bench mit echtem C3/B1/B2: Fokus-Koalition an/aus, Fokusschleife + Inquisition an/aus, Adaptive Effort an/aus (R5), Gist-Auflösung an/aus, Attention/Gain an/aus.
- Gleiche Fragen, gleiche Saat; Antwortqualität + Latenz; `C4.uncertainty_coupling_gain` einmessen. Ergebnis als Verdikt in `gate-graph`.

### WP-T4 A-Plane Lehrer/Student (A1–A3, §18.1–18.4, §18.11, G9B, G10)
- **Status 2026-10-10: erledigt bis auf den gelernten A1-Grenz-Kopf (Pakete C).** `v13/aplane.py`: A3-Schüler T2 `fallback` (routet nur bei ausgefallenem Lehrer-Pfad; Gate ≥50 Vergleiche, ≥90 % Übereinstimmung, Retention ≤5 Punkte Abfall; nur per `:aplane student fallback`, automatischer Rückfall); Text-Destillation als kleiner Ridge-Kopf auf `teacher.dataset` (zentrierte Ziele, Holdout, nie Ausgabe, Solo-Trials in die Reliance); Lehrer-Entfernung als Lauf 100/75/50/25 % → Reliance-Kurve. Tests `test_aplane.py`, Suite 860 grün. Doku `code/docs/APLANE.md`. Offen: gelernte A1-Grenzen (keine Labels), semantische Embeddings statt Rohbytes.
- A1: gelernte/inhaltliche Segmentgrenzen statt fester 240 Zeichen (Satz/Absatz/Episoden-Signal aus WP-N8). — inhaltlicher Teil erledigt (WP-N8), gelernt offen.
- A3-Student über Schatten-T1 hinaus mit Retention-Gate; Lehrer-Entfernung als echter Lauf (Reliance-Kurve).
- Text-Distillation: Trainer für den `agi/teacher.py`-Datensatz (kleiner Kopf, nicht LoRA).

### WP-T5 Körper-Sicht und Zugriff (B1, B4, B5, §3.2A)
- **Status 2026-10-10: erledigt (Pakete C).** `v13/bodyview.py`: B1-Detailfenster aus gewährten A4-Spans (±240 Zeichen, zusammengeführt, max. 3/1200 Zeichen, exakte SourceRefs); B5 World-/Self-/Skill-Zustand als gespeicherte Quelle `BODY_STATE` im B1/B2-Query (STATE_NOT_FACT, `:bodyview state off`); B4 eine frühere Koalitions-Sicht über Sessions bei gleichem Thema (SHADOW, `:bodyview b4 on`). Tests `test_bodyview.py`. Doku `code/docs/BODYVIEW.md`. Offen: Nutzen mit echten Modellen (WP-T3).
- B1-Detail-Sicht über 240 Zeichen (Fenster aus Attention-Spans), B4 verteilter Zustand über Sessions hinweg.
- B5: B1/B2 bekommen World-/Self-/Skill-Zustand als Quelle (mit SourceRef), nicht nur Memory.

### WP-T6 Skills und Prozeduralisierung live (WP-F-Zeilen §6.1–6.3, §41.6, §75, F2)
- **Status 2026-10-10: erledigt bis auf das Unterbrechen laufender Ausgabe (Pakete C).** `v13/skilllive.py`: automatischer Pfad – TRUSTED-Route-Skill routet vor C_fast ohne Needle-Aufruf, Rückfall bei Skill-Kopf-Veto, Fehler oder Routen-Korrektur (reopen); Selector im normalen Turn bucht Parität für CANDIDATE/SHADOW-Skills; Habits aus wiederholten Cues (5×, ≥90 % gleiche Route) → CANDIDATE-Skill (SELF). Tests `test_skilllive.py`, Suite 890 grün. Doku `code/docs/SKILLS_LIVE.md`. Offen: spätes Offer unterbricht laufende Ausgabe (braucht parallelen Body-Lauf während C3, STEP 11).
- `agi/skills.py`-Selector im normalen Turn (nicht nur `:growth`), automatischer Pfad ohne C_fast mit Rückfall.
- Habits aus wiederholten Prozedur-Cues; spätes internes Offer darf laufende Ausgabe unterbrechen (Brücke zu `duplex.py`).

### WP-T7 Action Gate, Egress, Output-Broker (§6.4, §11, C6/C7)
- **Status 2026-10-10: erledigt (Pakete A).** Sandbox-Aktion im Live-Turn: Notiz-Bitte → `sandbox_note` (WRITE_LOCAL, nur vom Nutzer erlaubt) wird PROPOSED mit Dry-Run-Vorschau (`ToolSpec.preview`), Körper erfährt „nicht ausgeführt“, Broker zeigt `[Aktion wartet auf Freigabe] … :tx approve <id>`, Rücknahme `:tx undo`. Neuer C7-Output-Broker `code/v13/broker.py`: Rangfolge feste Regel > exakte Kopie > Modell > Systembericht, nach Commit nur späte `broker`-Nachrichten (nie in History/Memory/Training), `OutputBrokerDecision`-Paket, C6-Prüfung für jede Egress-Art (TEXT_REPORT, CLARIFY, EXACT_RENDER, SYSTEM_REPORT, SNAPSHOT, CORRECTION, ACTION_PREVIEW, TOOL_CALL), `:tx broker`. **Zur Nutzer-Prüfung:** Flag `tool_conflict_policy` (Standard `correct`: fehlt ein ausgeführtes Werkzeug-Ergebnis in der Antwort, zeigt der Broker den exakten Wert als Korrektur; `log` = nur protokollieren). Tests `tests/test_broker.py` (10), Suite 855 OK. Doku `code/docs/OUTPUT_BROKER.md`. Offen: gelernte Werkzeugwahl, TTL für offene Vorschläge.
- Action Gate über `local_text_only` hinaus: Tool-Aktion im Sandbox-Modus mit Vorschau, Freigabe, Undo (WP-K-Transaktionen).
- Output-Broker: Konflikt Snapshot/Policy/Antwort sauber entscheiden, Tests für jede Egress-Art.

### WP-T8 World-Model und Ziele (§7.2, §7.2.1, §7.2.2, §20.3, §6.6)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/world_model.py`: kontrollgeerdetes Weltmodell über eigene digitale Übergänge mit getrennten Zielen forward (Ridge-Ensemble), inverse (Aktion aus Zustand+Folge, kein Kausalbeleg), state-align (Probe auf gelernte Latents, sonst UNAVAILABLE), outcome (Hold-out-MAE vs. Baseline); Coverage/OOD/Ensemble-Streuung → Counterfactual-Konfidenz, unter 0,5 SIMULATION_UNCERTAIN, nie REAL. Sleep B ordnet Routen-Alternativen nach Konfidenz und setzt die Replay-Priorität daraus (Coverage statt Häufigkeit). Ziele im Lauf: ungelöste Turns → offenes USER-Ziel, späterer FINAL-Turn schließt es; Neugier beobachtet jede Routen-Region, wählt selbst nur mit Age-Recht (`learn_medium`). Tests `tests/test_world_model.py` (6), Suite 882 grün (außer `test_bodyport` von WP-T13 im Entstehen). Doku `code/docs/WORLD_MODEL_GOALS.md`. Offen: echte Messung, sobald genug eigene Übergänge am Handy liegen.
- Inverses Modell + State-Alignment neben dem Forward-Prädiktor; Counterfactual mit Coverage statt Häufigkeit.
- `agi/goals.py` und Neugier (`agi/curiosity.py`, Age-gegated) im Lauf statt offline.

### WP-T9 Gedächtnis-Rest (§9.1, §9.5)
- **Status 2026-10-10 13:10: großteils erledigt (Thread „Echtes Lernen in den Modellen“).**
  (1) Gelernte Aufnahme `code/v13/admission.py` (`:admission [status|train|active|shadow|table]`): Merkmale nur aus menschlichen
  Signalen und Nutzung (Abrufe, `:retrieval relevant/irrelevant`, erneut bestätigt, `:note` der Turns, Stärke WP-N8), Labels nur
  menschlich (positiv: relevant/bestätigt/gut bewertet; negativ: irrelevant/überschrieben/`:forget`/schlecht bewertet); logistische
  Regression ab 20 Labels, Held-out-Check gegen BOOT-Prior. SHADOW: Scores stehen in jedem AG6-Batch (`admission`), Reihenfolge
  bleibt; ACTIVE nur durch Nutzer nach bestandenem Check, dann sortiert AG6 nach Score und lässt < `admission_floor` weg; Check
  rot → automatisch zurück auf SHADOW. Tests `tests/test_admission.py`.
  (2) §9.5 „redundante schnelle Spuren verschwinden“: überschreibt der Nutzer eine Korrektur, werden die Slots des alten Werts im
  Live-Faktenspeicher genullt (`memory_trainer.prune_inactive`, Hook in `memory.feedback`).
  (3) Blueprint-Vergleich §9.1 exakt vs. exakt + parametrischer Fast Trace (`bench-results/fast-trace-20261010/README.md`): im echten
  Chat-Prompt liefert exakter Abruf 8/8; Trace allein 8/8 (+1 Paraphrase, −15 % Prompt-Tokens), beides zusammen schlechter
  (7/8, Leck .8). Trace mit Schlüsseln aus nacktem Turn feuert im Chat kaum (1/8) → Trainer schreibt Schlüssel jetzt im
  Live-Kontext (`sparse_memory` cfg `system`/`contexts`, `memory_trainer.live_system`). AG6 `auto` wählt Sparse deshalb nie
  automatisch. Offen: Fakt entweder als Trace oder als exakter Block ausliefern (nicht doppelt) und neu messen; Archiv-Politik
  (Quellen nur inaktiver Erinnerungen komprimiert archivieren, ohne `read_source`/Export zu brechen); Semantic/Procedural-Staging
  hat schon `tests/test_consolidation.py`.
- Gelernte Memory-Aufnahme (Admission-Kopf aus Bewertungen/Korrekturen), Semantic/Procedural-Staging mit Test.
- Sparse-Memory (WP-S3) optional im Turn (torch vorhanden) + Entitäts-Wächter gegen das Near-Miss-Leck; Archive-Politik.

### WP-T10 Lern-Autorität und Beförderung Schatten → aktiv (§88.1, §17A, §14.1–14.6, IH-H25)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/authority.py`: ein Beförderungsweg SHADOW → CANDIDATE → ACTIVE für 10 gelernte Köpfe (C5, JEF-Brücke, Fast-Forward, Context-Policy, Admission, Attention, Deliberation, Callosum, Gist, Neuromod-META). Kandidat nur mit eigenem Gate (Regression/Übereinstimmung ≥ 90 %/bessere Ergebnisse/Held-out), Lernziel IMPLEMENTED und Gate-Graph ohne Fehl-Verdikt; ACTIVE nur per `:authority promote` (Mensch); Regression fällt automatisch aufs Scaffold zurück. `v13/objectives.py`: IH-H25 `ObjectiveAdapter` mit Validierung (UNAVAILABLE/PARTIAL → learn_gain 0) + `register()`, 10 neue Lernziel-Zeilen. Scheduler-Jobs `learn_medium` (idle, ≤ 1/30 min; passt auch das Weltmodell an) und `learn_slow` (nach voller Nacht; wartet bei Homöostase-FAIL). Tests `tests/test_authority.py` (6). Doku `code/docs/LEARNING_AUTHORITY.md`. Offen: Hooks, die `authority.observe` für attention/deliberation/callosum füttern. Nur Regeln/Gates, kein Gewichts-Training (das macht „Echtes Lernen“).
- Einheitlicher Beförderungsweg für gelernte Köpfe (Autorität 0 → 1 → 2) mit Gate-Graph-Verdikt; Scaffold-to-Policy schaltet bei bestandenem Gate um.
- Learning-Objective-Plugin (IH-H25) statt reiner Registry-Datei; Lernzeitskalen mittel/langsam als geplante Jobs.

### WP-T11 Sleep-Rest (§15.4–15.7, §16.2, §94.5, L8.2)
- **Status 2026-10-10: erledigt (Pakete E).** Sleep B prüft gequeuete Traum-Hypothesen gegen gespeicherte Quellen/Erinnerungen (`SleepCycle.validate_hypotheses`): Anker-Hash + aktive Erinnerungen (sonst STALE), Belege aus menschlichen Routen/Fakten → SUPPORTED/CONTRADICTED/UNVERIFIED, Paket `SLEEP_B_VALIDATION`, nie Fakt-Schreiben; CONTRADICTED/STALE scheiden aus. `v13/homeostasis.py`: Sleep C misst Drift/Sättigung/tote Pfade der gelernten Steuerparameter, Gate (BOOT Drift ≤ 0,5, Sättigung ≤ 0,5), FAIL hält `learn_slow`-Konsolidierung an. Tests `tests/test_sleep_validation.py` (4), Suite 872 grün (bis auf `test_bodyport`, Datei von WP-T13 noch im Entstehen). Doku `code/docs/SLEEP_VALIDATION_HOMEOSTASIS.md`. Offen: Shared-Pre-Router-Drift §16.2.1 braucht native Body-Hidden-States (WP-T13/WP-R).
- Counterfactual Replay und Dream prüfen Hypothesen gegen gespeicherte Quellen (nicht nur erzeugen); Homöostase-Messung (Gewichts-/Gain-Drift) mit Gate.

### WP-T12 Neuromodulation-Rest (§12.2, §16.1, §68, G7)
- **Status 2026-10-10: erledigt (Pakete E).** `neuromod.py`: δ pro Pfad (Fehlerkanäle → `error_level`) und vorzeichenbehaftetes δ = r − r̂ pro Beispiel, `local_update` = e×δ×M×P (§12.4); Metaplastizität §16.1/§68 als BOOT-Regel (META-Regler in knob-map) + gelernter Kopf aus Retention-Ergebnissen, SHADOW, `:neuromod meta active` nur Nutzer. Messung `bench-results/delayed-reward-20261010/`: δ pro Beispiel 0,051 vs. Gate allein 0,158 (5/5), Trennung 12,8× statt 1,1×; langsame Eligibility-Spur ohne Nutzen. Tests `test_neuromod.py::LocalErrorAndMeta`, `test_ablation99.py::DelayedReward`. Doku `code/docs/NEUROMODULATION.md`. Offen: `local_update` in einen echten Worker einhängen, META ACTIVE erst nach Retention-Läufen.
- Vorhersagefehler δ pro Pfad (statt Worker-Loss), gelernter Metaplastizitäts-Kopf, Eligibility × δ als lokales Update-Signal.

### WP-T13 BodyPort und Body-Swap online (IH-H8, IH-H21, G2, G11)
- **Status 2026-10-10: erledigt (Pakete A).** `code/v13/bodyport.py`: BodyPort je Rolle im Laufpfad (RunnerPool meldet ASSIGNED/READY/RELEASED/MODEL_CHANGE/FAILED, State `T13_BODY_PORTS`); IH-H21-Bridge-Key (sha256 Rolle/Modell/Revision/Datei/Dims/Tokenizer/Fähigkeiten) wird vor jedem Dateiwechsel live geprüft, B3-Manifeste und bridge/latent_path-Assets der alten Revision → veraltet/`SHADOW_RECALIBRATE`, `bridge_valid` fail-closed. Body-Swap online `:body swap|parity|ramp|rollback`: GGUF → SHADOW → Parität → RAMP 0,1/0,5/1,0 → ACTIVE, wirkt beim nächsten `pool.get` ohne Neustart, Gesundheits-Probe nach ACTIVE mit automatischem Rollback, Rollback aus jeder Stufe, fertiger Tausch überlebt Neustart (`models.revision` meldet neue Revision). Tests `tests/test_bodyport.py` (8), Suite 882 OK. Doku `code/docs/BODY_PORT.md`. Offen: Ladezeit-Kosten während RAMP auf dem Redmi messen; Probe prüft nur Laden, Qualität über AG12-Parität.
- `BodyPort`-Objekt mit Lifecycle im Laufpfad; Bridge-Key vor jedem Modelltausch live geprüft; Body-Swap mit Rollback ohne Neustart.

### WP-T14 Kernexperimente R2–R4, R6–R9 + §99-Pflicht-Ablationen + Thin-Control-Budget (§31, §79, §99, §22.2.3)
- **Status 2026-10-10: Teil 2 erledigt (Pakete B):** §99 „JEPA-Prädiktor hilft“ auf echten B2-Taps (Qwen3.5-0.8B, 1024 dim), Themenwechsel-Erkennung, Test nur auf ungesehenen Themen (`scripts/jepa_ablation_bench.py` → `bench-results/jepa-ablation-20261010/`): JEPA 0,73–0,76 AUROC = kein Prädiktor 0,74 (16-dim); 128-dim 0,87 vs. 0,91; roher Tap-Kosinus 0,93; supervised 0,82. **Nicht belegt**; die 16-dim Projektion kostet 0,19 AUROC; EMA mit langem Budget instabil, SIGReg stabil. Für WP-N8 reicht Tap-Kosinus als Grenzsignal. Doku-Abschnitt in `code/docs/CORE_EXPERIMENTS.md`.
- **Status 2026-10-10: Teil 1 erledigt (Pakete B).** Übersicht + Übergabe `code/docs/CORE_EXPERIMENTS.md` (R0–R9 und §99 je mit Stand und Beleg). Neu gemessen: **R2 dicht** (`scripts/r2_scope_bench.py` → `bench-results/r2-scope-20261010/`): weniger Parameter ≠ weniger Vergessen (Norm-Gains 29 k vergessen 5/12 Proben, Attention-LoRA 4, Conv-LoRA 2, Full-FT 2), nur gegatete Sparse-Memory-Slots vergessen 0 (KL ≈ 0) → erster Lern-Scope = gegatete Slots, dichte Updates nur mit Drift-Gate. **§99 Episodisch** (`scripts/episodic_ablation_bench.py` → `bench-results/episodic-ablation-20261010/`): Antwort-Cache 8/8 exakt aber 0 Paraphrase, Retrieval 0,33 Paraphrase / 0,4 Leck (falsche lexikalische Treffer), Parameter-Delta 0,50 / 0,8. **Thin-Control-Budget** `v13/control_budget.py` + `:fabric [report|record]` (Latenz P95 der Steuer-Stufen, Checkpoint-/State-Bytes, Limits-Regler, Verdikt NO_LIMITS bis Redmi), 4 Tests; volle Suite 839 grün. Rest: R3/R4/R5 + Focal-§99 → WP-T3 (Lauf mit Modellen); R6 blockiert (Runner); R7 → Echtes Lernen; R8 → WP-R; JEPA-/Dream-§99 offen (WP-T11/T12); router-/expert-Arme von R2 → WP-N11.
- Fehlende R-Experimente als Skripte mit Verdikt; §99-Ablationen als Läufe; Budget-Gate je Stufe aus der Zeitmessung.

### WP-T15 Register, Ledger, Doku-Hygiene (IH-H0, IH-H2, IH-H5, IH-H34, IH-H35)
- **Status 2026-10-10: erledigt (Pakete E).** 14 weitere Blueprint-Regler gebunden (92/299, vorher 78); Abweichungen Code ≠ Blueprint stehen begründet und ehrlich als „nicht gemessen“ in `specs/knob-map.json` `deviations` (Status DOCUMENTED_DEVIATION, ungeklärte Drift bleibt 0). Completion-Ledger v3: jede der 104 Dateien in `v13/` hat eine Zeile (kuratierte Feature-Zeilen + automatische Modulzeilen mit Docstring, Kanon-Verweisen, importierenden Tests; nie PASS), `uncovered_modules` muss leer sein. Offene Nutzerentscheidungen werden live erzeugt (Age-Plastizität, Kandidaten zur Freigabe) und `docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md` neu geschrieben (statt „None“). README: gültiger STEP2-Lauf, `:age/:effort/:authority/:objectives/:live/:register`; BUILD_STATE-Kopf und REMAINING_IMPLEMENTATION als historisch markiert, SQLite-Blocker genannt. Tests `tests/test_ledger_hygiene.py` (2), Suite 890 grün.
- Weitere Blueprint-Regler in `knob-map.json` binden; Completion-Ledger-Zeile für jedes Modul; widersprüchliche Doku (SICHTUNG §5) bereinigen; Blocker-Liste P1–P3 aktualisieren.

### WP-T16 Vision-Lab Schritt 3 (§18.9, G10B, Fortsetzung WP-N15)
- **Status 2026-10-10: erledigt bis auf echte Fotos (Pakete A).** `v13/vision.py`: Quadranten-Regionen, Kachel-Ausrichtung aus schwachen Labels (auffällige Kachel erbt Beschreibung der kleinsten beschriebenen Region, sonst BACKGROUND), `:image tiles`, `:image find` (4×4-Heatmap, mehrere Objekte getrennt), `:image teacher off|on` (Lehrer-Entfernung). Messung mit echtem LFM2.5-VL-450M `code/bench-results/vision3-20261010/`: Einzelobjekt per Kachel 1,00 (Hälften 0,60–0,67), zwei Objekte per Kachel 0,79 (Quadranten-Regionen 1,00, Zufall 0,25), Abhängigkeitskurve: 1/4 Lehrer-Beschriftungen −5 Punkte, 1/8 −21 Punkte, Selbsttraining holt +7. Skript `code/scripts/vision_bench3.py`, Tests `tests/test_vision.py` (+2), Suite grün. **Offen: echte Fotos brauchen die Erlaubnis des Nutzers.**
- Ausrichtung pro Kachel, mehrere Objekte pro Bild, echte Fotos (kleiner Satz mit Nutzer-Erlaubnis), Lehrer-Entfernung für Bilder.

## Restbausteine aus ABDECKUNG.md ohne Redmi (Pakete WP-U, angelegt 2026-10-10 von Pakete C)

### WP-U1 JEF-Lernschnittstelle + Experience-Lebenszyklus (§3.3.8, §14.6, §24.32)
- **Status 2026-10-10: erledigt (Pakete C).** `v13/jefoutcome.py`: Ergebnis-Labels (OUTCOME_SELF_LABEL, unter Nutzer-Labels) für wake/memory/skill nach jedem FINAL-Turn, Übereinstimmung mit Nutzer-Labels messbar, in `:learn` nur nach `:fastpolicy outcomes learn` und nur ohne Nutzer-Label; Lebenszyklus L0–L11 als Lesemodell (`:fastpolicy lifecycle`); ABDECKUNG-Zeilen für WP-T1/T4/T5/T6 nachgezogen (✅ 85→93). Tests `test_jefoutcome.py`. Doku `code/docs/JEF_OUTCOME.md`.
- JEF lernt Steuerung aus Ergebnissen: Ergebnis-Labels (Packet-Targets) für die Fast-Köpfe wake/memory/skill aus dem Turn (welche Offers/Erinnerungen in der Koalition landeten, ob die Antwort hielt); Autorität unter Nutzer-Labels, nur Schatten, Nutzen gegen Nutzer-Labels messen.
- Experience-Lebenszyklus L0–L11 je Erfahrung als Lesemodell aus vorhandenen Spuren (Capture, Tag, Vergleich, Credit, Vorschlag, Schatten, Validierung, Freigabe, Wiederöffnung); `:experience lifecycle`.
- ABDECKUNG.md-Zeilen der von Pakete C erledigten Bausteine (WP-T1/T4/T5/T6) nachziehen.


### WP-U2 Homöostase-Regelung + Metaplastizität-Rest + ABDECKUNG-Nachzug Pakete E (§16.1, §16.2, §68)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/homeostasis.py` `regulate()`: je N10-Pfad Aktivierungs- und Update-Häufigkeit zwischen zwei Sleep C; dominante Pfade gedämpft, tote nützliche wieder geöffnet, Update-Budget normalisiert, Gain wandert je Nacht 30 % Richtung Ziel (0,5–1,5); wirkt im Plastizitäts-Gate nur nach `:homeostasis active` (Mensch), sonst SHADOW; Routen-Dominanz nur Monitor. `neuromod`: META.conflict_verify_before_learn (stützende vs. widersprechende Belege → Faktor 0, bis Mensch/echtes Ergebnis klärt). 8 HOME/META-Regler gebunden (Register 92 MATCH, 0 DRIFT). ABDECKUNG: 16 Zeilen nachgezogen (✅ 109 = 52 %). Tests `tests/test_homeostasis_regulation.py` (7), volle Suite 899 grün. Doku `code/docs/SLEEP_VALIDATION_HOMEOSTASIS.md`. Offen: HOME.shared_representation_drift (keine geteilte trainierbare Repräsentation).
- Homöostase regelt langsam statt nur zu messen: Aktivierungs-/Update-Häufigkeit je Pfad, dominante Pfade dämpfen, tote nützliche Pfade wieder öffnen, Update-Budgets normalisieren, Routen-Dominanz überwachen (HOME.* aus §68); SHADOW, wirkt nur mit `:homeostasis active` (Mensch).
- META.conflict_verify_before_learn: widersprüchliche Belege auf einem Pfad → erst verifizieren, dann lernen.
- ABDECKUNG.md-Zeilen der von Pakete E erledigten Bausteine (WP-T2/T8/T10/T11/T12/T15) nachziehen.

### WP-U3 Spätes internes Offer unterbricht laufende Ausgabe (F2, §5.2)
- **Status 2026-10-10: erledigt (Pakete C).** `v13/latewatch.py`: Body ohne Vor-Antwort-Offer läuft parallel zur C3-Ausgabe (nur wenn Body-Fabric an, C3 gepinnt und der Body ins Budget passt, NORMAL, server-Decode; sonst NO_RESIDENCY); Vergleich mit der Teilantwort (RESULT_CONFLICT: abgeleitete Zahlen widersprechen, BODY_REENTRY); `:latewatch shadow` (Standard) protokolliert nur, `active` stoppt den Stream, markiert den Schnitt vorläufig und lässt C3 mit dem Befund korrigieren/fortsetzen; zu spätes Offer → bisheriger `selfmodel.late_offer`; Post-Commit-Pass überspringt den schon gelaufenen Body. Haken: 3 Zeilen um die C3-Schleife + 1 Zeile im Post-Commit-Pass. Tests `test_latewatch.py` (5), volle Suite 909 grün. Doku `code/docs/LATE_WATCH.md`. Offen: gelernte Interrupt-Salienz (braucht SHADOW-Labels), Tokenraten-Einbuße auf dem Redmi messen.
- Eigenes Modul `v13/latewatch.py`, in `runtime._turn` nur ein kleiner Haken um die C3-Streaming-Schleife; Flag `:latewatch off|shadow|active`, Standard SHADOW (protokolliert nur „hätte bei Zeichen N unterbrochen“).
- Ein Body-Offer, das während der C3-Ausgabe eintrifft und der Teilausgabe widerspricht (fehlende Zahlen/Belege, Re-entry nötig), unterbricht in ACTIVE die Ausgabe; der Schnitt wird als vorläufig markiert, die Antwort revidiert/ergänzt. Paralleler Body-Lauf nur, wenn die Residenz C3 nicht verdrängt, sonst NO_RESIDENCY.

### WP-T17 JEPA-Prädiktor für Handlungsfolgen + übrige Ablationen ohne Redmi (§13, §7.2, §99, Fortsetzung WP-T14)
- **Status 2026-10-10 22:25: JEPA-Teil erledigt, Dream-Teil vorläufig; pausiert (Nutzer-Pause bis Montag 04:00) (Pakete B).** Handlungsfolgen: `code/scripts/jepa_action_bench.py`, Tests `test_jepa_action.py` (3), Ergebnis `bench-results/jepa-action-20261010/` (3 Seeds): aktionsbedingter JEPA lernt Folgen (invers 0,84–0,90 statt 0,25), schlägt aber die Kontrolle „Mittelwert-Delta je Handlung“ nicht → nicht belegt. §99 Dream: `code/scripts/dream_ablation_bench.py`, `bench-results/dream-ablation-20261010/` Lauf 1 (2 Seeds): kein Vergessen im Aufbau, ungeprüfte Träume schaden Proben (0,25–0,33) → nicht belegt. Doku CORE_EXPERIMENTS.md Teil 3. Suite 842 grün (lokal). **Offen:** Dream-Lauf 2 mit Vergessens-Druck `--b-steps 40 --seeds 13,21,34` (abgebrochen, ca. 1–2 h CPU), dann §99-Tabelle Dream-Zeile endgültig.
- JEPA-Prädiktor aktionsbedingt auf echten B2-Taps: Ergebnis einer Handlung vorhersagen, falsche Ergebnisse per Überraschung erkennen, Handlung aus Vorher/Nachher erschließen (inverses Modell); Kontrollen ohne Prädiktor, Mittelwert-Delta, Ridge im vollen Raum, supervised.
- Danach übrige §99-Zeilen/R-Experimente ohne Redmi, soweit nicht in WP-T3 (Pakete A).

### WP-T3b Nutzen-Messung Runde 2: deterministisch + 60 Aufgaben mit B1/B2-Widerspruch (G3D, G5, G5B; Fortsetzung WP-T3)
- **Status 2026-10-10: erledigt (Pakete A).** `code/scripts/utility_bench2.py`, Ergebnis `code/bench-results/utility2-20261010/` (README + `utility2.json` mit Verdikt), Gate G-FOCAL-CAPACITY-003 ergänzt. 60 Aufgaben × 5 Läufe, echte Modelle: Bench-Modus trotz Temperatur 0 und ohne Fristschnitte **nicht deterministisch** (Wiederholung: 33/60 identisch, 8 Bewertungen kippen = Rauschband; vermutet Prompt-Cache/Hintergrund-Observer). Koalition und Inquisition ohne messbaren Nutzen. Feste niedrige Effort-Stufe 0,70 vs. adaptiv 0,57 (+8 netto, p 0,12): weckt beide Körper, hilft bei Widerspruch/Vergleich → adaptive Politik ruft B1 zu selten (Kandidat für Effort-Einmessung, keine Default-Änderung ohne Signifikanz).
- Bench-Modus ohne Fristschnitte (feste Saat, Temperatur 0, großzügige Observer-Fristen), Reproduzierbarkeit messen; 60 generierte Aufgaben (Zahlen im Detail vs. irreführende Zusammenfassung, lange Texte), Arme baseline/effort_low/no_inquisition/no_coalition mit gepaartem Test; Verdikt in `gate-graph`.

### WP-U4 Archiv-Politik für Quellen (§9.1 Archive, §9.5 „Exact Provenance wird günstig archiviert“)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/archive.py`: kalte Quellen (≥ 30 Tage, ≥ 512 B, nur archivierbare Arten, keine aktive Erinnerung braucht sie; überschriebene Werte ja) werden in Sleep C verlustfrei als `<sha256>.z` abgelegt (nur bei ≥ 10 % Ersparnis, vor dem Löschen geprüft); `Store.blob_bytes` liest beide Formen, Hash-Prüfung bleibt, `:doctor` erkennt kaputte Archive, `:forget` löscht beide; `:archive [status|run|restore <Quelle>]`. Tests `tests/test_archive.py` (4), volle Suite 903 grün. Doku `code/docs/ARCHIVE.md`. (Offener Rest aus WP-T9; WP-T9 selbst bleibt beim Thread „Echtes Lernen“.)
- Kalte Quellen (alt, keine aktive Erinnerung, nur archivierbare Arten) verlustfrei komprimiert ablegen; `read_source`, Export, Backup und `:doctor` funktionieren unverändert; Sleep C archiviert, `:archive [status|run|restore <Quelle>]`.

### WP-U5 Representation Anchor als Stabilitäts-Regler (§69, §48.10)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/anchor.py` + Haken in `agi/weights.train`: Anker-Multiplikator je Batch aus Neuheit/Stabilität mit Untergrenzen (Geometrie .25, geteilte Layer .75), SHADOW protokolliert `anchor` im Batch, ACTIVE (`:anchor active`, Mensch) skaliert `anchor_weight` nur für diesen Batch; Drift-Gates unverändert. 4 ANCHOR-Regler gebunden (Register 96 MATCH, 0 DRIFT). ABDECKUNG: Anchor, Staging, §12.2 ✅, IH-H5/IH-H34 aktualisiert (✅ 113 = 54 %). Tests `tests/test_anchor.py` (3), volle Suite 906 grün. Doku `code/docs/REPRESENTATION_ANCHOR.md`. Offen: Messung mit Modell, ob schwächerer Anker bei neuer Domäne das Gate besteht.
- Anker-Stärke je Trainings-Batch aus Domänen-Neuheit (Batch vs. bestehende aktive Erinnerungen) und Stabilität des alten Skills (N10-Pfad `weights`): neue Domäne → Anker ↓, alter stabiler Skill → Anker ↑, Untergrenze = vortrainierte Geometrie; ANCHOR.* aus §69. SHADOW (nur protokolliert im Batch), ACTIVE skaliert `anchor_weight` des Live-LoRA-Trainers nur nach `:anchor active` (Mensch); Drift-Grenzen werden nie gelockert.
- ABDECKUNG-Nachzug veralteter Zeilen (Staging, §12.2, IH-H5, IH-H34).

### WP-U6 Gemeinsamer Weltfehler → lokale Updates in allen gelernten Köpfen (§12.4, §12.7)
- **Status 2026-10-10: erledigt (Pakete E).** `neuromod.step_scale`/`step()`: Attention-Policy, Callosum, Context-Policy, Deliberation, Fast-Forward, JEF-Brücke und C5 multiplizieren ihre Schrittweite mit dem Gate-Faktor ihres Pfads; SHADOW = 1,0 (unverändert), ACTIVE per `:neuromod local active` (Mensch), Veto/Konflikt → 0. Tests `tests/test_local_updates.py` (3), volle Suite 909 grün. Doku `code/docs/NEUROMODULATION.md` (Abschnitt WP-U6).
- Jeder gelernte Kopf (Attention-Policy, Callosum, Context-Policy, Deliberation, Fast-Forward, JEF-Brücke, C5) skaliert seine eigene Schrittweite mit dem N10-Plastizitäts-Gate seines Pfads (Eligibility × Modulator × Age/Meta/Homöostase; Veto/Konflikt → 0); eigener Fehler bleibt lokal. Standard SHADOW (Schrittweite unverändert, vorgeschlagener Faktor sichtbar), ACTIVE nur per `:neuromod local active` (Mensch).

### WP-U7 Cross-scale-Kopplung vollständig (§3.2A)
- **Status 2026-10-10: erledigt (Pakete E).** `gist.coupling`: jeder Gist-Slot trägt `source_span_refs` (die Fein-Gruppen, die er bündelt), `covered`, `compression_ratio`, `boundary_confidence` (Minimum der gebündelten Grenzen) und `fallback` (EXACT_STORE bei exakten Spans, sonst B1_DETAIL); im QueryPacket als `gist.slot_coupling`. `gist.local_bundle`: B1 bündelt bei Re-entry (JEF-Frage oder eigenes needs_reentry) die Fein-Gruppen um frühere Zitate/Detail-Fenster zu vorläufigen lokalen Gists (≤ 96 Token, Autorität PROVISIONAL_LOCAL_GIST); immer im QueryPacket `local_gist`, im Prompt nur mit `:gist active`. Tests `tests/test_cross_scale.py` (3), volle Suite 912 grün.
- Gist-Slots tragen Quell-Spans, abgedeckten Bereich, Kompressionsrate, Grenz-Konfidenz und Rückfall (B1-Detail oder Exact Store); umgekehrt bündelt B1 bei Re-entry benachbarte Fein-Stücke zu einem vorläufigen lokalen Gist (immer im QueryPacket protokolliert, im Prompt nur mit `:gist active`).

### WP-U8 B4 Workspace-Stabilitäts-Lernschleife (L3-B4, B4, §8.1)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/workspace_learn.py`, Haken in `focal.Workspace.save/load`: Refresh-Nutzen und Wiederherstellungs-Verlust je Quellenart → Halte-Multiplikator (0,5–1,5, ab 10 Beobachtungen), SHADOW protokolliert, ACTIVE per `:workspace active` (Mensch) verändert den Zerfall; Quellenverlust wird gezählt und nie gehalten. Tests `tests/test_workspace_learn.py` (4), volle Suite grün (915 + Haken-Test). Doku `code/docs/WORKSPACE_LEARNING.md`. Offen: L_B4_BINDING ohne gelernte Nutzung.
- Workspace lernt je Quellenart (B1/B2-Offer, Erinnerung), welche Slots sich zu halten lohnen: gehaltener Slot später wieder in der Koalition = nützliches Refresh, verworfener Slot, der neu geholt werden muss = Wiederherstellungs-Verlust; daraus Haltedauer-Multiplikator je Art (SHADOW, aktiv nur mit `:workspace active`); Quellenverlust bleibt hart (L_B4_SOURCE_LOSS gesperrt).

### WP-U9 B3-H12 Abschluss-Gate für LATENT (+ B3-H13 Auslegung)
- **Status 2026-10-10: erledigt (Pakete E).** `b3bridge.completion_gate`: 14 Bedingungen je Richtung aus Belegen (Bridge-Manifest + L1-Gate-Kriterien, Callosum-Erfahrung, MessagePacket-Telemetrie, native Taps, Router-Metriken, Hardware-Nachweis); Status unavailable → scaffold → L1_shadow (nur bei L1 PASS und passender Empfänger-Revision) → active (nur wenn alle 14 erfüllt), LATENT-Autorität bleibt 0; B3-H13-Satz als `canon`. In `:doctor` unter `B3.<Richtung>.completion`. Stand heute: scaffold, es fehlen u. a. echter Sender-Pfad, Empfänger-Wirkung, Router-Metriken, Zielgerät. Tests `tests/test_b3_completion.py` (4), volle Suite 920 grün (ein Lauf hatte einen sporadischen Fehler in `test_bodies.TightBudget`, einzeln und im Wiederholungslauf grün; nicht von diesem Paket).
- Die 14 Bedingungen aus B3-H12 je Richtung aus echten Belegen prüfen (Code, Sender-Pfad, Empfänger-Wirkung, Kalibrierung, Rückfall-Kanäle, OOD, Router-Metriken, Neustart, Tests, Telemetrie, Ablationen, Zielgerät) und den erlaubten Zwischenstatus (unavailable/scaffold/L1_shadow/…) in `:doctor` melden; `B3_LATENT_IMPLEMENTED` nur, wenn alle erfüllt.

### WP-U10 Fast Episodic „zweites Mal besser“ für Routen (§9.1, STEP3)
- **Status 2026-10-10: erledigt (Pakete E).** `v13/episodic_route.py` + Haken in `runtime._route` (nach der prozeduralen Konsolidierung, vor dem Scaffold): aktive menschliche Routen-Korrektur mit Relevanz ≥ 0,6 (entitätsbewusst, gelöschte Quellen zählen nicht) → Vorschlag mit Erinnerungs-/Event-/Quellen-Bezug; `shadow` (Standard) schreibt ihn nach `meta.route.episodic_route`, `active` (`:episodes route active`) nimmt ihn als Route, `off` aus. Tests `tests/test_episodic_route.py` (3), volle Suite 940 grün.
- Eine einzelne menschliche Routen-Korrektur bei einer sehr ähnlichen früheren Anfrage (gleiche Entitäten, hohe Relevanz) wird beim nächsten Mal sofort als Routen-Vorschlag genutzt, ohne auf die prozedurale Konsolidierung (≥ 3 Bestätigungen) zu warten; mit Episoden-/Quellen-Bezug. Standard SHADOW (Vorschlag in `meta.route`), wirkt mit `:episodes route active` (Mensch).


---

# QUELLDOKUMENT: SICHTUNG.md

# V13 Sichtung der kompletten Übergabe (2026-10-09)

Gelesen: das ganze ZIP `V13_INQUISITION_KOMPLETT_NEUER_CHAT_2026-10-09.zip` (418 MB, 164 Einträge):
30 Blueprint-Fassungen v4.0 bis v10.16.1, 23 Programmversionen (inkl. 7 Standalone-Prototypen),
alle Entscheidungs- und Statusdateien, der 5-MB-GLM-Chat „AI-Consciousness-Blueprint-Theses“ und das
Positionspapier des Nutzers zu KI/Zensur/Privatsphäre. Abgeglichen gegen Blueprint v10.16.1,
`ROADMAP.md` und den aktuellen Code `code/`.

Die sieben Einzelberichte mit Zeilen- und Abschnittsangaben liegen in `sichtung/`
(`old_blueprints.md`, `blueprint_evolution.md`, `old_code.md`, `code_audit.md`, `chat1-3.md`).
Diese Datei fasst sie zusammen. *(E)* = Einschätzung, nicht gemessen.

## 0. Was in den Projektordner kopiert wurde (nur hinzugefügt, nichts überschrieben)

| Ziel | Inhalt |
|---|---|
| `code/docs/proofs/` | 2 083 kleine Proof-Dateien + 58 in der Doku referenzierte größere (u. a. `native46-failed-report.json`, eingefrorenes Acceptance-Archiv). SQLite-Proof-DBs der STEP2-Zustandsprüfung weggelassen. |
| `code/docs/canon/` | Blueprint-Kopie, die die Tests erwarten. Damit laufen **425/425 Unit-Tests grün** (vorher 16 Fehler wegen fehlender Dateien). |
| `archiv/blueprints/` | alle älteren Blueprints v4.0 bis v10.16 als Markdown |
| `archiv/entscheidungen/` | alle USER_DECISIONS-Fassungen |
| `archiv/chat/GLM_AI_Consciousness_Chat.txt` | Klartext des 12-MB-JSON-Chats (363 aktive Nachrichten) |
| `archiv/architektur/` | Codeaudit, Evidenz-JSON und SVG des Architektur-Pakets vom 09.10. |
| `archiv/KI_Zensur_Privatsphaere_Grundbasis.md` | Positionspapier des Nutzers |
| `salvage/` | verlorener bzw. wiederverwendbarer Code, siehe `salvage/README.md` und Abschnitt 2 |

Nicht kopiert: Architektur-PNGs (je 2–3 MB, nur Bilder), alte Runtime-ZIPs (Inhalt ist im neuesten enthalten), große Trainings-JSONs der Norm-Experimente.

## 1. Wichtigste Befunde

1. **Unbemerkter Codeverlust vom 06.10.** Die Arbeit aus burst3–5 fehlt im aktuellen Stand, ohne Vermerk in BUILD_STATE,
   Ledger oder Recovery-Doku. Alle späteren Stände bauen auf `auto-burst2` auf; bei den Wiederherstellungen 07.–09.10.
   wurde der burst-Zweig nicht übernommen. Verloren: `v13/body_training.py` (fail-closed Body-Train-Port-Vertrag) mit Test
   und Proof, `native_capability_profile`, der STEP2-`task_score`, ein Executive-Bugfix und acht Tests.
2. **Dadurch ist ein alter Bug zurück:** `code/v13/executive.py:96` übernimmt `previous.get('active_task')`. Die erste
   Nutzerfrage einer Session bleibt für immer `active_task` und landet in jedem nativen Kontext. Fix + Test liegen in
   `salvage/executive_implicit_task/` (nur gelesen, nicht ausgeführt).
3. **Die zentrale Designzusage „zwei verschiedene MoE-Hälften“ wurde still aufgegeben.** v7.1/v9 hatten sie LOCKED, der
   Nutzer fordert sie im Chat mehrfach („KEINE DICHTEN MODELLE“, Detail mit mehr aktiven Experten). Heute laufen B1 und B2
   auf derselben dichten LFM2.5-1.2B. Das ist die wahrscheinlichste Ursache für STEP2 `UTILITY_FAIL` *(E)*.
4. **Gefährlichster Doku-Widerspruch:** Die Alias-Firewall IH-H1 bildet legacy „A“ auf Detail ab. Das stimmt nur für v4/v5
   und ab v10.4. In v6 bis v10.3 war A = Gist. Wer alte Texte über IH-H1 liest, vertauscht die Hälften.
5. **Billige Schutz- und Messregeln aus v4/v5 fehlen ganz:** Datenmix-Quoten mit 2-%-Rollback, Kollapswächter,
   Zitat-/Abstention-Regel, Decoder-Parameter mit `min_new`, Zahlen-Gates der Könnenstreppe S1–S4. Alle handytauglich.
6. **Die alten Standalone-Prototypen taugen nicht als Vorlage.** Ihre eigenen Audits melden PASS, der Code tut es nicht
   (LoRA-Update läuft nie, Konsolidierung ist No-op, Training sieht Zukunftstokens). Brauchbar sind nur ein maskiertes
   JEPA mit EMA (`code (26).py`) und der saubere v10-Starter.
7. **Der Nutzer hat Anforderungen formuliert, die nirgends stehen** (Abschnitt 4), u. a. zu Zensur/Privatsphäre,
   Termux-Bedienung und „Thesen > Blueprint“.

## 2. Verlorener oder nie umgesetzter Inhalt

### 2a. Code (Details: `sichtung/old_code.md`, Kopien in `salvage/`)
| Was | Prio | Empfehlung |
|---|---|---|
| `body_training.py` Train-Port-Vertrag | A | zurückholen (WP-I/S6). Requantizer-Pflicht braucht Ausnahme für FP32-Slices wie `token_embd_norm`. |
| `native_capability_profile` | A | zurückholen, aber als neuer Befehl `:native`, weil `:capability` jetzt `age.py` gehört. Heute ist `'body_training':False` in `world.py` hart verdrahtet. |
| Executive-Fix implizite Aufgabe | A | sofort zurückholen (Bug, siehe 1.2) |
| STEP2 `task_score` | A | für WP-G (STEP2 neu messen) |
| v10-Starter (Eligibility mit TTL, Inferenz vor Training, Admissions-Checkliste für Modellpaare) | B | Referenz |
| I-JEPA + EMA + VICReg mit Kovarianzterm (`code (26).py`) | B | Referenz für WP-S4; `predictor_worker.py` hat keinen Kovarianzterm |
| Top-k + Overflow-KL aus `inquisition_rsi.py` | B | passt zum Drift-Gate WP-S5 mit llama-server-Logprobs |
| LoRA-Slow-Merge, SparseMoE-Losses (v1.1) | B | nur falls MoE-Body kommt |
| Regelvorschläge mit Digest/Stale-Check (Termux v11) | B | Vorlage für Age-Fähigkeit `propose_config_changes` |

### 2b. Alte Blueprints v4–v10.2 (Details: `sichtung/old_blueprints.md`)
Verloren oder stark abgeschwächt, mit hohem Nutzen *(E)*:
- Datenmix-Quoten (≥ 60 % Mensch, ≤ 10 % selbst erzeugt, Dream ≤ 5 %) + Rollback bei > 2 % Verlust auf alten Sets (v4 §24, v5 §28).
- Kollapswächter: Wiederholungsrate, Typen-Vielfalt, Selbstzitat-Rate, Abstention-Rate, Drift (v4 §63). Rein lexikalisch, sofort nützlich gegen „query echo“.
- Decoder-Parameter (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, no_repeat_ngram 4, rep 1,08) und `min_new=8` (v4 §64–66).
- Zitatregel (≤ 2 Zitate, Nutzerversion gewinnt) und Abstention-Form „nichts Belegtes, ich vermute:“ (v4 §21–22).
- Zahlen-Gates S1–S4 als Startwerte für die Age-Hülle (v4 §27, v9 §45–53); heute [OPEN].
- Stabilitätshülle pro Zyklus: max. Update-Norm, Route-Shift, Workspace-Drift, Kalibrier-Shift (v8 §42).
- Invarianten als Tests: „schlechtes Outcome wird nie negativer JEPA-Loss“, „Target bekommt keinen Gradienten, EMA bewegt sich, Optimizer isoliert“, „kein doppeltes LoRA nach Merge“ (Forschungs-BP v10, v7.1 §40).
- Getrennte Konfidenzen (Quelle vs. Antwort), epistemisch/aleatorisch (v8 §24, §36).
- „CAUSES-Kante nur nach Intervention“ (Forschungs-BP v10).
- Inquisition selbst (Cautiousness κ, P1/P2, adaptives N 1..7): Namensgeber des Projekts, seit v10.2 nur Scaffold, kein WP.

Fehlende Abnahmen: Lern-Abnahme v5 §54, Hardware-Abnahme mit Page Faults/Batterie v5 §58, voller Regression Shield mit getrennten Sets und modularem Rollback, Bridge-Test mit vertauschten Nachrichten, Strict-Key-Load, episodenbasierte Splits, Langzeitsitzung (v6 G15).

### 2c. Blueprint-Verlauf v10.3–v10.16.1 (Details: `sichtung/blueprint_evolution.md`)
Ab v10.10 gilt „Additive-Only“, danach geht kaum etwas verloren. Echter Verlust: der verworfene v10.6-Zweig
„Cross-Cache“ mit **„Re-entry statt Re-prefill“** und Cache-Lineage. Gerade auf 6 GB relevant *(E)*.
Außerdem wurde das Redmi-Gewichtsbudget ohne Begründung von < 1,5–1,8 GB auf 1,6–2,0 GB gelockert, und der
„Readiness Vector“ / „1 Änderung pro Laborzyklus“ aus v10.9 fiel weg.

Im Blueprint, aber ohne ROADMAP-Paket: Focal Coalition (§93), World/Self-Lernen aus Corollary (§85.7, G-SELF-WORLD-005),
typisierte Modulatoren + Objective Registry (§85.10, IH-H25), Context OS/Cache-Policy (§8.3–8.6, §74), Metaplastizität +
Representation Anchor (§68–69), KnobSpec (IH-H5), Delete-Lineage (IH-H20), BridgeKey (IH-H21) + Body Swap (G11),
C2-Benchmark Needle vs. FunctionGemma (§57, G12C), Event-Segmentierung (§9.3), Rules/Self-Edit/Goals (§20), Self Model.
Das Timescale-Gate §85.1 mit vier Kontrollen (same-model same-policy … true two-body) ist genau der Test für B1 = B2.

### 2d. GLM-Chat (Details: `sichtung/chat1-3.md`)
Der Chat (05.09.–Ende 09.2026) zeigt die Vorgeschichte: erst eigenes PyTorch-Netz von Null (nur Byte-Müll), dann
llama.cpp-Harness mit zwei GGUF-Modellen. Kern sind die Thesen T1–T10 und Ziele 2A–2G des Nutzers (`archiv/chat`, ab
ca. Zeile 10481 und 29443). Vieles steht heute im Blueprint (Callosum, Sleep, Rückfrage vor Regeländerung,
Neuromodulatoren, aktives Vergessen, Output-Garantie). Echte Lücken:
- **„Ausbrennen“-Budget:** ohne Input klingt die Aktivität ab, das System lernt, wann Pause ist, der Nutzer kann das Limit hochstellen.
- **Implizites Feedback** aus normalem Chattext (Lob/Kritik) und `note 1–10`-Bewertung. Hilft direkt gegen `INSUFFICIENT_LABELLED_COHORT`.
- **Termux-Bedienung:** Live-Logs dürfen getippten Text nicht überschreiben (readline-Neuzeichnen), mehrzeiliges Einfügen als ein Block, Kontext-Vorschau („was geht ins Modell“), Knobs live im Chat ändern, Pause-Befehle (`:pause selfedit|traum|training`).
- **Filter**, damit eingefügte Terminal-Logs nicht ins Gedächtnis gelangen.
- **Anti-Echo-Sampling / Wiederholungsstrafe** für C3.
- Neugier-Signal (RND), Notizbuch mit typisierten Kanten und 1-Hop-Abruf, abgesicherte Code-Ausführung als Grounding.
- Echte Redmi-Messungen aus dem Chat (nicht im Blueprint): OLMoE-7B 0,2 tok/s, fp32 22–32 GFLOPS, 3 Threads schneller als 4, mmap nur unter `$HOME`. Stützt die llama.cpp-Wahl.

Achtung: Ein persönlicher Text des Nutzers steckt in einem Trainingskorpus im Chat; nicht in V13-Daten übernehmen.

## 3. Toter Code und Aufräumkandidaten (Details: `sichtung/code_audit.md` §1)

**Vor jedem Aufräumen:** `scripts/verify_acceptance.py` und `scripts/acceptance.py` hashen alle Skripte, Tests und
`v13/*.py`. Jede Änderung macht ein laufendes `TESTEN.sh --resume` ungültig. Aufräumen daher gebündelt, wenn kein Resume läuft,
und nach `archive/` verschieben statt löschen (Proof-Manifeste verweisen auf die Dateinamen).

- Veraltete Duplikate: `code/completion-ledger.json` (es fehlen die drei Einträge vom 09.10.) und
  `code/USER_DECISIONS_AND_OPEN_QUESTIONS.md` (36 statt 94 Zeilen). Gültig sind die Fassungen in `code/docs/`.
- Ungenutzt: `docs/drafts/`, `docs/resume_acceptance.py`, `docs/check_resume_acceptance.py`,
  `scripts/checkpoint_step2_progress.py`, `scripts/compare_causal_runtime_decoder.py`, `scripts/test_live_output_adapter_port.py`,
  `scripts/test_live_output_export_native.py`, `scripts/test_native_midlayer_numeric_policy.py`, `effort.compare()`,
  `causal_output.source_revision()`, 16 ungenutzte Importe in `v13/`, 5 lose Snapshot-Dateien in `docs/`, `__pycache__/`.
- `age.py`: `open_window`, `gist_resolution` werden nur in Tests benutzt; Age wirkt also noch nicht auf Gist/Plastizität.
- 7 byte-gleiche `TESTEN_NATIVE_*.sh`-Wrapper → ein Dispatcher. `TESTEN_NATIVE_TRAIN.sh` trainiert nichts (Norm-Shadow-Diagnose).
- Veraltete Doku: `docs/RESUME.md` (Stand 01.10., README verweist trotzdem darauf), datierte Arbeitsnotizen → `docs/history/`.
- Tests importieren sich gegenseitig über bloße Modulnamen; nur mit `PYTHONPATH=.:tests` grün.

## 4. Nutzeranforderungen, die nirgends festgehalten sind

Aus dem Chat und dem Positionspapier. Gehören nach `code/docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md`:
- **Thesen > Blueprint/Zahlen:** Bei Konflikt sollen T1–T10/2A–2G gelten; Zahlen sind Schätzungen. Mit dem Blueprint (LOCKED-Regeln) nicht abgestimmt.
- **Alles lernt permanent, außer Safety-Regeln.** Blueprint sagt: Age 0 = nur Shadow-Lernen mit Freigabe.
- **Zwei verschiedene MoE-Hälften**, Detail mit mehr aktiven Experten; kleiner vortrainierter Sprachteil, nichts von Null.
- **Englisch zuerst, Deutsch später als Lerntest** (Chat, 09.2026). Code und ROADMAP setzen heute auf Deutsch. Evtl. später geändert.
- **Regeln an realem Schaden, nicht an Themen oder Schlüsselwörtern.** Darstellung, Absicht, Kontext, Veröffentlichung, reales Handeln unterscheiden; private Fiktion erlaubt; bei Ablehnung Grund offen nennen.
- **Privatsphäre als Normalfall:** lokal, keine Inhalts-Telemetrie, externer Teacher nur mit ausdrücklicher Zustimmung, Löschen muss gehen. Regeln lesbar, versioniert, nur mit `y` änderbar.
- **Bedienung:** alles am Handy/Termux mit einem Befehl, komplette Dateien mit festen Namen statt `code (N).py`, keine Heredocs zum Einfügen, Befehle während des Laufs, kein Neustart für kleine Änderungen.
- **Ehrlichkeit:** nichts als „lernt“ oder „neural“ verkaufen, was ein Platzhalter ist; Fakt/Schätzung/Vermutung trennen.
- Zentrale Vorgabe aus BUILD_STATE: „complete plan and additions, not only diagnostics“.

## 5. Widersprüche

**Nutzerwunsch vs. Blueprint (Entscheidung beim Nutzer):**
1. Permanentes Lernen vs. Age-0-Shadow mit Freigabe.
2. Zwei verschiedene MoE vs. heute B1 = B2 = LFM2.5-1.2B (dicht). Zwei MoE à 4–5 GB passen nicht gemeinsam auf 6 GB *(E)*; MobileMoE-S-QAT (0,68 GB INT4) wäre klein genug, ist aber gated, FAIR-noncommercial und ohne Android-Runner.
3. „Keine LoRA“ (Chat) vs. LoRA/Deltas im Blueprint.
4. Englisch zuerst vs. deutscher C3-Benchmark.
5. Freies `/py`-Exec und Self-Edit (Chat) vs. Sicherheitsregeln.

**Innerhalb Blueprint v10.16.1:** latent 0.20 beim Boot (§54/§78) vs. latent aus (IH-H27, §96, B3-H5); C3-Zielgröße
50–150M / 100–300M / 230M; Lernreihenfolge Adapter vor Predictor (§22.2.4) vs. Predictor-first (§92.1, §88, B3-H8);
zwei Ressourcen-Zustandsmaschinen (IH-H23 vs. §97.2); Reasoning Effort als Zahl (§10.2) vs. Modi (G5B); viermal „L0“
mit verschiedenen Bedeutungen; Legacy-Namen C_fast/C_focal im Gate-Text; IH-H1 A/B-Mapping (siehe 1.4);
`arcxiv.org`-Tippfehler noch zweimal drin (Z. 7843, 9961); Training auf dem Handy (§90) vs. nur extern (§33.3).

**Doku vs. Doku/Code:** Acceptance-Stand je nach Datei 18/21, 6/20, 3/20, 2/20; BUILD_STATE-Kopf veraltet
(`completed_this_run`, `base_checkpoint`, `next_priority`); Ledger mit zwei sich widersprechenden Einträgen zum
Causal-Lifecycle und 19 Modulen ohne Ledger-Zeile; REMAINING_IMPLEMENTATION führt Erledigtes als fehlend und nennt den
SQLite-Blocker nicht; README verweist für STEP2 auf den alten Test und kennt `:age`/`:effort` nicht;
`USER_DECISION_REQUIRED: None`, obwohl Redmi-Lauf, echte Labels und Modellfrage offen sind. `Store.close()` prüft im
Produktivpfad keine Integrität und wertet das Busy-Ergebnis des WAL-Checkpoints nicht aus; der Integritätscheck läuft nur im Test-Collector.

**Verloren zwischen Versionen der Entscheidungsdatei:** MobileMoE-Zugang (HTTP 401) als Blocker, Redmi-DEADLINE-Abbruch
(Ursache unbewiesen), die konkrete Liste für Body-Training (Master, Runner, Requantizer, Revisionsbindung).

## 6. Forschung (nur was die Berichte bestätigt oder als relevant markiert haben)

Im Web bestätigt: MobileMoE (2605.27358), Needle 3, StateBridge (2608.13317), MeSP (2602.13069), „Language Models Need
Sleep“ (2606.03979), XKV, Mixture-of-Translators, KV-Cache-Alignment, LFM2.5-230M (laut Hersteller für Extraktion/Tool-Calls,
nicht für freies Schreiben, passt zum „query echo“). Viele 2026er-arXiv-Nummern in alten Blueprints und im Chat sind
**nicht geprüft** und teils wohl erfunden.
Für „Mini-AGI auf billigem Handy“ am wichtigsten *(E)*: MeSP (exakte LoRA-Gradienten mit wenig Speicher), Fast-Episodic-first
(CLS), Needle 3 als C2 (auch Embeddings), StateBridge für B3 L2 (passt ausgerechnet zu B1 = B2), LeJEPA/SIGReg,
APOLLO/GaLore, FOREVER, Titans/TTT, ReFT, Benna&Fusi/Turrigiano (Metaplastizität/Homöostase). Ergänzt
`research/FORSCHUNG.md` des Forschungs-Threads, nicht dupliziert.


---

# QUELLDOKUMENT: UEBERGABE_FUER_ANDERE_KI.md

# Codex-Fortsetzung — 2026-10-16

GitHub: https://github.com/RedMentos/Aii/pull/4
Arbeitsbranch: `codex/continuation-20261016`
Verifizierter Checkpoint: `3af7ea8fe8f124459041133a34ce457f179d1f99`, Tree `322346ab17249e63536bd76d5a829713f63a4e35`.

K list_arith mit aktuellem M calc/note/ToolForecast integriert; minimale H-Text- und G-Approval-Voraussetzungen übernommen. M hatte die fünf älteren Codex-Befunde bereits selbst korrigiert. Neu enger Schutz gegen Quellentausch während Outcome-Tap; vollständige Lernzeilen-/Aktionskontrolle und quell-/modell-/bibliotheks-/NumPy-gebundener Einmal-Lauf mit fsynced Rohzeilen.

Gesamtsuite 1421 Tests: 1416 bestanden, 5 Skips, 0 Fehler. Vier Skips: PyTorch fehlt. Ein optionaler nativer Unittest wurde ohne Tap/GGUF-Umgebungsvariablen übersprungen; der separate registrierte Native-Lauf misst tatsächlich native Taps. O's bereits vorhandene Testkorrektur für das ResourceGuard-Rennen exakt übernommen; kein BodyRuntime-Eingriff.

Phone-Checkpoint: https://drive.google.com/file/d/1b16ED4mf2W-FvbnkkWdAfhwwP7djE-xt/view
SHA256 `6e6d3115ce667cbb447cdae22c8cefe91f0d9781b1809699cac91908d7bf03c5`, 11767941 Bytes. Tatsächlich entpackt vollständige1421 Tests erneut grün (1416+5 Skips), alle612 Quelldateien/Manifest unverändert; Drive-Download SHA/CRC exakt geprüft. Linux-Softwarebeleg, kein Redmi-PASS.

Neue disjunkte competence-v2-Lernkohorte: Preregistrierung vor Inferenz auf GitHub `aa00ee365172e6e257f7f52b774e6fdcc851d5d9`, Drive bytegleich geprüft: https://drive.google.com/file/d/1yFty8iczxo32Dj_uF2mSq4aW9Q7l3XJ7/view . Native Installationsparität bestanden;610-Call-Kohorte läuft, Ergebnis noch offen.250 Erfahrungs- und360 gehaltene Testaufrufe; ursprüngliche .90/1.02/strikte Mehrheit unverändert. Jeder Aufruf sofort protokolliert, keine Wiederholung desselben Registers nach Negativ/Abbruch. Schwere Modelljobs seriell unter8GiB. Keine Qualitätsbehauptung aus Teilzeilen.

Neuere historische Zustände: SourceHandoff16/16 beendet und Freeze laut ROADMAP aufgehoben; Dream2v3 ist15/15 abgeschlossen mit Nutzen-/Retention-Tradeoff. Alte Hinweise auf Freeze/2von15 bleiben unten nur historisch. STEP2 UTILITY_FAIL und B3L1 FAIL unverändert; Canon/Fullscope/Redmi weiter offen. Neues isoliertes STEP2-Privatdaten-Testpaket:30 ergänzende Fälle+9 Kontrollen, Solo-Unzulänglichkeit/Paarslösbarkeit maschinell geprüft, noch keine native Messung.

Claude-Owner-Branches nicht überschrieben. Aktive Claude-Threads sind hier nicht beobachtbar; letzter Commit wird nicht mit fertig gleichgesetzt. Nächster Schritt: Native-Kohorte schließen, Original-Phone-Lernreport ebenfalls strikt anbinden, Ergebnisse sichern und finalen Stand erneut paketieren.

## Historische Übergaben (erhalten)

# Aktueller unabhängiger Codex-Review — 2026-10-13

GitHub Review: https://github.com/RedMentos/Aii/pull/3
Eigener Branch `codex/continuation-review-20261013`, verifizierter HEAD `36e6ec050a4e7c7d75be1482e2df5b4878bdb819`. Ausführliche Übergabe: https://drive.google.com/file/d/1xF9d2LTEhfgFCtlubNdDReY_ULrx6ek8/view?usp=drivesdk
Review-ZIP: https://drive.google.com/file/d/1CEC9vQkZsyo0apA4WaYqoqt4E2Fcpdhm/view?usp=drivesdk

Claude K–P können noch aktiv oder auf Limits wartend sein. Der neueste M-Branch und seine kumulative Roadmap sind kein gemeinsam integrierter Stand. 44 deklarierte K/L/M/N/O/P/G-Dateien wurden gegen M geprüft: 6 gleich, 25 fehlen, 13 unterscheiden sich. Ihre aktiven Branches wurden nicht geändert oder gemergt.

Neue unabhängige Kandidaten: exakt quellgebundene ToolForecast-Kopie für Prognose/Neustart/Bewertung/Lernprovenienz; sichere Install-Generation als noch nicht angeschlossener Helper; beschädigte Encoder-Statusdateien und Kapazitätsbereinigung; begrenzter Handy-Testdriver mit Erhalt von Teilbelegen; komplette ZIP-/Entpacktprüfung. Keine Änderung an M's produktiven Runtimequellen. Originale Fehlversuche bleiben erhalten.

Vollständige entpackte Software-Suite: 1398 Tests, 1393 PASS, 5 ausdrückliche Skips (4 PyTorch fehlt, 1 echte Tap/Qwen-Ressourcen fehlen), 0 Fehler. Alle 603 Quelldateien exakt an Remote-Codecheckpoint `bdeb4f647f80f8f6c574d9d8a6eddfe6d630f578` gebunden; ZIP und Quellen nach Tests unverändert. ZIP SHA256 `16d768a59e54467015eaab69e1a102d3bb1fc5ac21a62938e114f6a971aef068`.

Linux-Softwarebelege; keine neuen Modellläufe oder Redmi-Messungen. STEP2/B3- und sonstige Original-Gates bleiben unverändert, Gesamtarchitektur/Fullscope unvollständig. Nächste Arbeit: aktive HEADs/Kohorten neu lesen, Kandidaten mit Besitzer M prüfen und getrennt binden, private Installer-Staging übernehmen, native/Redmi-Gates messen. Backend-Bibliotheksbindung, Modell-Hash-IO und Legacy-Migration bleiben offen.

## Historische Übergabe vor diesem Review (unverändert erhalten)

# Fortsetzung 2026-10-12: Arbeitsregeln und vollständige native Rohdaten

`AGENTS.md` enthält die wiedergefundenen Arbeitsregeln samt Quellen, Research-Verfahren, offenen Fragen, Endziel, Agenteneinsatz und geprüften Sicherungen. Ein vollständiger Chatexport ist keine Voraussetzung der autorisierten Fortsetzung. Die exakten letzten drei Nachrichten wurden nicht vollständig wiedergefunden.

Der erhaltene alte Workspace wurde mit GitHub verglichen; sein neuerer lokaler Checkpoint `dac5a5f` ist wieder aufgenommen. Tatsächlich überprüft: 1875 native Zeilen/118 Rohbatches. Die 736er Basis plus 72-Batch-Delta rekonstruieren das gesamte originale NPZ bytegleich (`09fde379793ea8c4a63268df729a33b4b98a3f4f90f3eeee2dec4a83a10b5843`). Geschlossene Rohbytes liegen verlustfrei in `docs/proofs/continuation-20261011/action-native1875-recovered-20261012/parts/`; der Report erklärt den unverändert erhaltenen veralteten letzten Einzelworker-Status. Kein Nutzen-/Redmi-PASS daraus.

Der vorhandene isolierte Approval-Reader-/Firing-Fix ist wiedergefunden. Ein zusätzlicher Lock-/SQLite-Reproducer zeigt: Cancellation/Deadline blockierten bis zum Ende eines Schreibers. Der Kandidat prüft beim Warten nun spätestens alle 50 ms; beide Regressionen scheiterten vorher und bestehen danach; 31 gezielte Tests PASS. Belege `approval-reader-cancellation-20261012/`. Nicht in die eingefrorene Runtime integriert. Native Diagnose-Registrierung muss nach dieser Kandidatenänderung separat neu gebunden werden.

Nächste Arbeit gestartet: unveränderte 16-Fall-SourceHandoff-Ablation im erhaltenen Workspace, gleiche Preregistrierung `4cfaddad1d9fadd23b5810c7cd4ddc0637e0e9b59d6d6fcd007fc22b5870b1d0`, alle 121 Runtimequellen unverändert. Danach originale NumPy-Trainings-Seeds13/21/34 und Dream2 (2/15 abgeschlossen), danach isolierte Fixes integrieren, Gesamttests/Paketprüfung und weitere ursprüngliche Gates. Fehlendes PyTorch im neuen Workspace ist eine technische Voraussetzung, kein abgeschlossener Dream-Lauf.

STEP2 UTILITY_FAIL/B3 L1 FAIL bleiben erhalten; Canon/Fullscope noch offen. GitHub-Veröffentlichung gilt erst nach geprüftem Remote-Tree.

## Vorheriger datierter Handoff (historisch erhalten)

# Aktueller Fortsetzungsstand — Codex, 2026-10-11, 23:21 Berlin

Der vorhandene Drive-Plan bleibt verbindlich; neue Zukunftsideen werden getrennt gesammelt. Ziel sind belastbare längere Menschentests und belegter fortgesetzter Lernnutzen, kein vorzeitig behauptetes AGI-/RSI-Ergebnis.

- Autoritative Code-/Test-/Proof-Quelle: GitHub `RedMentos/Aii`, Branch `codex/authority-live-comparisons`, https://github.com/RedMentos/Aii/tree/codex/authority-live-comparisons . Zuletzt verifizierte Basis: `ef46ddbbe2cc2b694ccb0c74275a86a78f0ae2aa`, Tree `0bd3babb9d8f0777f8b772f377829d5e7b3e4c36`. Vor jedem Wechsel tatsächlichen Remote-HEAD neu lesen; diese Notiz ist ein datierter Checkpoint.
- Code liegt im Repo unter `v13/code`; Roadmap `v13/ROADMAP.md`; aktueller Status `v13/code/BUILD_STATE.json`, `docs/completion-ledger.json`, `docs/CONTINUE_20261011_PROGRESS.md`, Proofs `docs/proofs/continuation-20261011/`. Drive-Roadmap-Originale, Canon und frühere Fehlschläge erhalten.
- Aktuell gesicherter Source-ZIP Version4, Phone-ZIP Version2. Phone-ZIP SHA `477593e79a6069210258d91500ca9a42b0dfeaadf696d9788b09c3a63679a88a`: tatsächlich entpackt1125 Tests PASS,0Skips,495 Datei-Hashes unverändert. Ausschließlich Linux-Softwaretest; Redmi-RAM/Thermals/Laufzeit nicht gemessen. Eine fehlerhafte RSS-Probe wurde verworfen und separat korrigiert.
- Workspace-Bereinigung entfernte zweimal lokale Caches/ungesicherte Resultate. Original736 native Tap-Zeilen/46Rohbatches sind als geschlossenes ZIP dauerhaft gesichert. Die erste vollständige1875-Erfassung hat dauerhaft erhaltene terminale11Worker-Belege, ihre großen Rohbytes wurden vor erfolgreichem Upload entfernt. Metadaten-Dataset wurde aus bereits angelegten Git-Blobs gerettet; dadurch fehlen weiterhin die nativen Zustände. Nicht aus Metadaten als vollständig rekonstruierte Rohdaten ausgeben.
- Native3Modelle+Launcher+19Bibliothekseinträge jetzt wieder bytegleich;121Source-Handoff-Quellen eingefroren. Neue Night-Capture-Preregistrierung `f348d9ca38c728c8b7a5074b25ce1a74aac7fd924e15da9406c3912146590c80` ändert nur Wiederherstellungsordner, keine numerischen Einstellungen oder Gates. Erst nach Git-VerifikationInference starten. Neue geschlossene Belege in<=1MiB Teile mit Teil-/Gesamt-SHA sichern; `scripts/sealed_storage_parts.py` rekonstruiert exakte Originalbytes.
- Nächste Reihenfolge: begrenzte tatsächliche Capture mit zwei frischen Invarianzkontrollen und kontrollierten8BatchWorker-Grenzen, vollständige1875Rohdaten plus originale3NumPySeeds13/21/34; danach unveränderte16FallSource-Handoff-Ablation; danach Dream2 exakt40BSteps×3Seeds×5Arme (2/15dauerhaft abgeschlossen; unvollständigerB10Arm vonBase neu). Alle schweren Modelljobs seriell unter8GiBLinux-Cgroup. Danach isolierteAG6Reader/FiringFixes integrieren und Paket erneut testen, dann weitereOriginal-Gates.
- Original STEP2:70/70UTILITY_FAIL, kein neuer Nutzen-PASS. B3L1:alle8TasksFAIL, L2–L4gesperrt. Gist nativeReadoutConsumer fehlt, aktuelletextbasierte Gruppierung ist kein gelerntesGist-Ziel. NativeFiringdiagnostik bleibtSHADOW,keineSelective-Auslassung. `canonical_architecture_complete=false`, `user_full_scope_complete=false`, aktuellerHandyqualitätsnachweisoffen.
- Bei parallelem Codex/Claude-Wechsel: erst Remote-HEAD und diese Drive-Datei neu lesen; geschlossene Belege/Gates weiterführen; eigene Branches oder Hash-CAS für Schreibzugriffe. Keine Force-Pushes und keine Änderungen an aktiven gefrorenen Quellen. Kein direkter Claude-Kanal ist hier verfügbar; GitHub/Drive sind die gemeinsame Übergabe.

## Historische ursprüngliche Drive-Übergabe (unverändert erhalten)

# V13 / Inquisition-JEPA – Übergabe für eine andere KI (Stand 2026-10-11)

Projekt: brain-inspirierte, kontinuierlich lernende KI-Runtime für ein Redmi-Handy (Android/Termux, 6 GB RAM). Nutzer schreibt Deutsch, arbeitet nur am Handy. Leitfrage des Projekts: braucht AGI mindestens 8 GB RAM; Zwischenergebnisse für Tests und exakte Werte sind erlaubt.

## Wo was liegt (Drive-Ordner https://drive.google.com/drive/folders/1dEAaqlWvdsU8hciVBNfVVPV1f5CjucZv)
- ROADMAP_Teil1von3.md, Teil2von3.md, Teil3von3.md: alle Arbeitspakete mit Status (zusammen die komplette ROADMAP.md)
- SICHTUNG.md: Sichtung der ganzen Übergabe, Widersprüche, verlorener Code
- NUTZER_ENTSCHEIDUNGEN.md: verbindliche Nutzerentscheidungen
- Code, Tests und Bench-Ergebnisse liegen NICHT als Text auf Drive. Sie stecken in ZIPs im Claude-Projekt (V13_2_Code.zip ca. 1,7 MB, V13_1_Doku.zip, V13_3_Bench.zip, V13_4_Archiv_ohne_Chat.zip, V13_5_Proofs.zip). Wer sie braucht, bittet den Nutzer, die ZIPs hierher in den Ordner hochzuladen.

## Kernpunkte
- Code in `code/v13/` (ca. 104 Module), Tests `code/tests/` (zuletzt ca. 940 grün, `test_bodies.TightBudget` sporadisch flaky), Befehl: `cd code && PYTHONPATH=.:tests python -m unittest`.
- Nutzerentscheidungen: viele verschiedene Modelle (B1 und B2 echt verschieden), Englisch zuerst, konstantes Lernen als Endziel, Ziel ist eine heruntergebrochene Gehirn-Simulation. Age-Hülle startet bei 0.
- Fertig laut ROADMAP: WP-A bis E, WP-V1 bis V9, WP-N1 bis N14, WP-T1 bis T16, WP-U1 bis U10, WP-AG (AG0 bis AG13), Abdeckung ca. 56 %.
- Offen: B3 LATENT unavailable (L1-Gate FAIL), STEP2 two-body FAIL, viele SHADOW-Flags brauchen Redmi-Messung (WP-R, nur der Nutzer), WP-T17 Dream-Lauf 2 (`--b-steps 40 --seeds 13,21,34`).
- Arbeitsregel: jedes Paket aktualisiert ROADMAP.md und schreibt eine Übergabenotiz; Status-Zeile „in Arbeit“ vor Beginn setzen.
- Nutzer-Pause bis Montag 2026-10-12 04:00 Berlin war angesetzt; der Nutzer lässt jetzt eine andere KI bis Montag weiterarbeiten.



---

# ORIGINALANHANG C — 49 KLEINE HISTORISCHE DRIVE-PATCHNOTIZEN, UNVERÄNDERT

# V14: originale kleine Drive-Patch- und Entscheidungsnotizen (Stand Oktober 2026)

Historische Originaltexte. ZIP-/JSON-Pilotdateien mit potenziellen Roh- und Privatdaten sind nicht enthalten. Alte Statusmeldungen sind keine neue Implementierungs- oder Freigabe-Evidenz.

---

## QUELLE: THREAD_REGEL_LESER_V7_20261022.md

# Thread „Regel-Leser Version 7“ (2026-10-22)

Branch `claude/project-thread-ub4in2` (auf PR #31 / c62rfz), PR #40 (Entwurf). Beleg im Repo: `v13/code/docs/proofs/continuation-20261022/user-rules-v7/` (BEFUND.md).

Urteil `USER_RULES_V7_UNSAFE`: v7 ist auf frischen Sätzen nicht besser als v6.
- holdout_de4 (60 neue deutsche Autor-Sätze): v7 4 Fehlersätze, v6 4.
- Runde 7 (Hunyuan 7B, Yi 1.5 9B, Apertus 8B; 118 von 360 brauchbar): v7 14, v6 13.
- Unnötige Rückfragen: 50 % der Sätze ohne Regel (Grenze 30 %).
- Bekannte Sätze: 0 Fehler.
- Rückschritt: Kosten-Regel „kaputt = Feststellung“ verschluckt „Mach meine Notizen bloß nicht kaputt“.
- Salamandra 7B und InternLM3 8B liefen im festen llama.cpp b10964 nicht und wurden vorab ersetzt.

Nächster Schritt WP-UR8: starkes Sperr-Signal ohne Ziel ⇒ Rückfrage für alles; „kaputt“-Regel zurücknehmen; zweite Meinung (kleines Modell oder gelernter JEF-Leser), die nur Vorsicht hinzufügen darf. Sicherheit bleibt: Außenwirkung nur als sichtbarer Vorschlag + getipptes :verbot.

Commits: 8500f78 prereg, 8f3aba5 Ersatz-Modelle, ea025e7 v7, c7f8a06 Rohdaten, e52532c Freeze, bcb3064 Audit, 0f93042 Messung.


---

## QUELLE: THREAD_DS3B_SCHALTER_20261022.md

Thread "Unsicherheit bei Namen prüfen", 2026-10-22, Nachtrag zu THREAD_DS3B_NAMEN_GEGENPROBE_20261022.md.

Die Gegenprobe ist jetzt als Schalter in die Laufzeit eingebaut: cfg tool_answer_check (off|shadow|note), Standard off. Commit b79cb8c auf Branch claude/project-thread-l0wfdt; dieser Branch enthält jetzt auch den Integrations-Branch dq33gk (live list_arith). PR #39 hat jetzt dq33gk als Basis.
- off: Es passiert nichts. Ein Test prüft, dass sich ohne Schalter nichts ändert.
- shadow: Die Gegenprobe zählt nur mit (State TOOL_ANSWER_CHECK), die Antwort bleibt unverändert.
- note: Schlägt die Probe fehl, wird ein fester Satz angehängt: "passt nicht zur exakten Rechnung, als unsicher behandeln".
Code: agi/listarith.answer_check, ToolStep.check_answer, Kettenglied in integrated_candidates.py, tests/test_tool_answer_check.py. 371 Tests grün.
Offen: Messung auf dem Handy in shadow; eigene Vorregistrierung für "Werkzeug-Antwort statt raten" (Seeds 61+).


---

## QUELLE: THREAD_HARNESS_HX2_HX5_20261022_ZWISCHENSTAND.md

# Thread "Harness HX2 und HX5" – Zwischenstand 2026-10-22 19:35 UTC

Branch: claude/project-thread-gqty8y (Basis 4iqpro / PR #33). Commits: f94bb84 (HX2 Vorregistrierung + Runner, vor jedem Modelllauf), d0c3b4e (B2-Mitschnitt), 9118020 (HX5).

- HX2: v13/agi/harness_probe.py + scripts/hx2_same_task_probe.py; Vorregistrierung docs/proofs/continuation-20261022/hx2-same-task-probe/PREREG.md. Neues Harness-Ziel prompt.b2_earlier_context (Text in harness.py gespiegelt, cognition.py unverändert, weil hash-gebunden).
- HX5: v13/agi/harness_data.py – Export von Lerndaten nur nach HX2_PASS (Beleg-Hash gebunden) + Freigabe durch Nutzer; trainiert selbst nichts; retention_gate.
- Suite: 1778 OK, 5 übersprungen.
- Messung: erster Lauf REF_s20 abgebrochen (eine Zeile Zeitbudget überschritten, weil die Testsuite gleichzeitig lief; Bericht aufbewahrt). Neustart 19:33 UTC ohne Parallel-Last. Ergebnis folgt.


---

## QUELLE: THREAD_DS3B_NAMEN_GEGENPROBE_20261022.md

Thread "Unsicherheit bei Namen prüfen" (2026-10-22), WP-DS3b. Branch claude/project-thread-l0wfdt (auf eq3869), Commits 7fc3a8c (Skript), 8de2994 (Vorregistrierung), 491db1c (Ergebnis).
Skript v13/code/scripts/ds3b_name_check.py, Belege v13/bench-results/ds3b-name-check-20261022/ (auch im Projektordner).

Verdikt (vorregistriert): NOT_SUPPORTED wegen H1. Die Namen-Unsicherheit hilft nicht (AUROC 0,79 gegen 0,84 nur Ziffern).
Die feste Gegenprobe Antwort<->Werkzeug ist PASS (H2-H4): Sie findet 18 von 21 falschen Werkzeug-Antworten bei 78 % Treffsicherheit. Die Fehler sinken von 25 auf 6, das ergibt 143 statt 130 Punkte bei 86 % beantworteten Aufgaben (180 frische Aufgaben, Seeds 47/53/59).
Nur berichtet: Bei Fehlschlag die feste Werkzeug-Antwort zu geben, ergibt 162 Punkte.
Nächste Schritte: die Gegenprobe als SHADOW-Schalter (Standard aus) in toolstep einbauen, und eine eigene Vorregistrierung für "Werkzeug-Antwort statt raten" (Seeds 61+).
Die frischen R4-Seeds 41..59 sind verbraucht.


---

## QUELLE: V13-Thread-Z6-Z12-20261022.md

# Thread „Offene Ziel-Pakete Z6 bis Z12“ — Zwischenstand 2026-10-22

Branch `claude/project-thread-i41cub` (Basis h8vj3v), Draft-PR #38.

- WP-Z8b/c G-AGE-REOPEN-001: FAIL (öffnet/schließt richtig, Neustart bitgleich, aber Öffnen spart nur 4–7 % Fehler, vorregistriert ≥10 %; Kandidat noise_aware_v2 öffnet auch bei Rauschen). Befund: code/docs/proofs/continuation-20261022/z8-age-reopen/BEFUND.md
- WP-Z9 §99 Dream: Z9_POLICY_DREAM_NO_GAIN, FACT_WRITE_CARRIES. Träume ohne Fakt-Schreiben: A-Paraphrase 0; Replay+Policy-Traum +0,08; Probes .22 statt .61. Befund: z9-dream-policy-only/BEFUND.md
- WP-Z7: HANDY_PFLICHT.sh (RAM, Trainings-Nachweis, Residenz §24.33/§24.14, Wiederholung, Werkzeug, Langlauf), docs/HANDY_PFLICHT.md. TrainRunnerProof für Routen-Kopf; fsync-Fehler in learning_worker behoben.
- Vorregistriert, laufend: Z6a (§24.23 Effort), Z11 (STEP4 Lehrer Qwen3-4B).


---

## QUELLE: THREAD_STEP2_ENGPASS_20261022_ANTWORT_VORN.md

# Thread „STEP2-Nutzen Engpass“ – 2026-10-22: Werkzeug-Entscheidung vorn

- Branch `claude/project-thread-dq33gk` @ cd7d39e (Prereg 6d278e5), PR #7.
- Fester Regel-Leser (Regeln nie von C3) + Entscheidungssatz als erster Satz der Antwort; bei unbekannt/keine fester Ganztext.
- Frische Messung Saat 41, 60 Aufgaben: Antwort richtig 59/60 (vorher 23, C3 allein 18), falsch festgelegt 0 (vorher 30). Rezept-Entscheidung 60/60 (C3-Leser 42). FIRST_SUPPORTED + FIXED_READER_SUPPORTED.
- Standard jetzt an (eligibility_reader=fixed, tool_answer_first=true); Werkzeug selbst nur nach `:growth enable eligibility`.
- Nutzerentscheidung 22.10.: Werkzeug eingeschaltet ins nächste Handy-Paket (WP-Z7, noch zu bauen).
- Befund: code/docs/proofs/continuation-20261022/eligibility-first/BEFUND.md


---

## QUELLE: THREAD_DS2_DS3_BEFUND_20261022.md

# Thread "Sandbox-Pakete DS2 und DS3" (2026-10-22)

Branch claude/project-thread-eq3869, PR #37 (enthält DS1 aus PR #25). Nur Lab-Code, keine Laufzeit-Änderung.

## WP-DS2 (vorregistriert, Commit 16d1fcc)
- Teil A 4/4 PASS: lpgoal (Lernfortschritt + Hunger) hungert wie efe, lernt neues Objekt 20/20 (efe 6/20).
- A5 Vorhersage falsch: Neuheits-Schub schadet leicht -> nicht übernehmen.
- Teil B 3/3 PASS: Merkmals-Lerner überträgt auf ungesehene Wortpaare und ähnlich aussehende Dinge; Wachsapfel-Täuschung wird durch Erfahrung überstimmt (20/20). Grenze: Merkmale von Hand.

## WP-DS3 (vorregistriert, Commit 7b931be), frische echte Läufe Seeds 31+37
- NOT_SUPPORTED: Kalibrierung trägt (AUROC 0,78, ECE 0,08), "unsicher" 2/3 berechtigt, Nutzen nur +1 statt +5 gegen "immer Rezept" (95 vs 94).
- Restfehler sind selbstsicher (richtige Zahl, falscher Name). Nächste Idee: Namen-Unsicherheit + feste Gegenprobe Antwort<->Rezept.

Belege im Repo: v13/bench-results/sandbox-ds2-20261022/, v13/bench-results/ds3-metacog-20261022/.
Frische R4-Seeds ab jetzt 41+.


---

## QUELLE: V13-Z5c-Koalition-lange-Sitzung-20261022.md

# WP-Z5c Fokus-Koalition in einer langen Sitzung (2026-10-22)

Git: RedMentos/Aii, Branch claude/project-thread-hmopsm @ 0825134, PR #15. Beleg v13/code/bench-results/z5c-focal-session-20261022/ (PREREGISTRATION.md, README.md, z5c.json, run.log), Skript scripts/z5_focal_controls.py --session.

Aufbau: 60 WP-T3b-Aufgaben je Lauf in einer Sitzung (gemischt), frühere Aufgaben als Ablenker im Workspace, meist 11 Kandidaten bei 4 Slots, 5 Läufe, Effort max.
Bestanden/300: Koalition 166, Voll-Kontext 82 (158 passt nicht ins Kontextfenster), feste Slots 181, Retrieval 185, ohne Hypothesen 188.
Vorregistrierte Gate-Regel erfüllt: vs Voll-Kontext 97:13 p<0,001; alle 7 Eigenschaften treten auf (Kapazität bindet 295/300, 356 Verdrängungen, 478 Interrupts).
Vorbehalt: wenn beides passt 83:82; Koalition schlechter als ohne Hypothesen 19:41 p 0,006; Live-Pfad läuft 41/300 über (Systembericht). Live-Zeilen nachträglich als nicht bestanden gezählt (Regex fand Zahlen im wiederholten Input).
Empfehlung: Gate nicht ohne Vorbehalt grün; Folge: Live-Overflow beheben.



---

## QUELLE: B3 L1 frische Seeds (WP-Z4d) 2026-10-22

﻿Thread "B3 L1 frische Seeds", 2026-10-22. Branch claude/project-thread-y2mnt5 (Basis 2p69gl, enthält Versuch-5-Code aus yub2lf), Draft-PR #36.


Aufgabe: escalate-L1-PASS aus Versuch 5 (Saat 20261105) auf zwei frischen Saaten wiederholen.
Vorregistriert (Commit b17b8ec) vor dem Rechnen: Rezept unverändert, Saaten 20261201 und 20261202, je 600 Zeilen, 0 Überschneidung.


Ergebnis (privat, Genauigkeit %):
- escalate: 86,2 vs Attribut-Wörter 84,5 (n.s.) und 85,5 vs 81,3 (n.s.) -> FAIL auf beiden -> NICHT REPLIZIERT.
- apologize: FAIL / FAIL.
- action: PASS / FAIL -> saatabhängig (über 4 frische Datensätze 2:2).
Folge: B3_LATENT bleibt unavailable, L2 gesperrt, kein L2-Prefix auf escalate. Nächster Versuch nur mit mehr Testdaten je Saat oder anderer Aufgabe.


Ehrlich: Saat 2 durch Container-Neustart unterbrochen, mit gespeicherten Zuständen und gleichem Skript neu gestartet (Zahlen identisch). Report-Feld overlap attempt5 zeigt fälschlich 600, nachgerechnet 0.
Belege: v13/bench-results/b3-l1-v6-20261022/ (Git + Projektordner; states.npz nur Projektordner).

---

## QUELLE: V13 Thread LP2 Lernziel C3 2026-10-22

﻿WP-LP2 (Thread "Lernziel für C3 LP2"), 2026-10-22
Branch claude/project-thread-h8vj3v, PR #35 (Basis claude/project-thread-2p69gl / PR #30). Commits a9e4ce3 (Vorregistrierung + Skript, vor dem Lauf), danach Ergebnis-Commit.


Frage: Bringt ein latentes C3-Ziel, das nur die RICHTIGE Zuordnung belohnt (Predictor + langsames EMA-Ziel + InfoNCE gegen die anderen Fakten), mehr Treffer auf neuen Aufgaben als CE+KL allein und als dasselbe Ziel mit falscher Zuordnung?


Aufbau: LFM2.5-350M Master (sha256 1c9c77a4...), 16 erfundene Fakten, 32 neue Umformulierungen (Hauptgröße), 3 Arme x 4 neue Saaten (31,37,41,43) x 30 Schritte.


Urteil: LP2_ALIGNS_NO_GAIN.
- Zuordnung gelernt: .41 -> .99 (falsche Kontrolle landet sicher beim falschen Fakt .91). Diese Probe trennt richtig/falsch, anders als der LP1-Kosinus.
- Kein Nutzen: neue Aufgaben CE 110, NCE_OK 110, NCE_SHUF 108 von 128. Alte Umformulierungen 17/18/16 von 24.
- Drift nur +8 % (KL .026 -> .028), kein Vergessen, Leck gleich.
- Grund: auch falsche Zuordnung ist fast gleich lernbar (NCE .27 vs .21); die Zuordnung sitzt im Predictor, die Antwort hängt nicht davon ab. Alle Arme scheitern an denselben 5 Fragen.


Folge: jepa_weight bleibt 0, keine Aktivierung. Neues Paket WP-LP3: Antwort muss vom vorhergesagten Zustand abhängen (Soft-Prefix oder Speicher-Schlüssel), neu vorregistrieren, LP2-Zuordnungsprobe mit Verschiebungs-Kontrolle weiterverwenden.
Dateien im Repo: v13/code/docs/proofs/continuation-20261022/lp2-assignment-objective/{PREREG,BEFUND}.md, v13/code/scripts/lp2_assignment_objective.py, v13/bench-results/lp2-assignment-objective-20261022/.

---

## QUELLE: V13-Entscheidung-noise_aware-Zitatkontext-20261022.md

# Nutzerentscheidung 2026-10-22 umgesetzt (Thread „Ziele gegen Blueprint abgleichen“)

Git: RedMentos/Aii Branch claude/project-thread-rxq188 @ 3fdc402 (enthält Merge von claude/project-thread-dq33gk). Projektordner: v13/code/v13/config.py, v13/NUTZER_ENTSCHEIDUNGEN.md, v13/ROADMAP.md (WP-Z8).

1. age_plasticity_policy = noise_aware ist Standard. Grund lange Sicht: verrauschte Phase 0,073 (boot 0,175, stable_reopen 0,129, conservative 0,086); Preis: langsameres Umlernen bei echtem Zielwechsel (0,079 vs 0,053). Offen: Wiederöffnen-Test für G-AGE-REOPEN-001.
2. Zitat-Kontext an: offer_quote_context_chars=200, b2_offer_body_state=false, offer_quote_min_chars=90.
3. Alte Werte als LEGACY_PRE_20261022 in config.py; eingefrorene Harnesses (source_handoff_ablation, rule_transport) und Tests des alten Verhaltens (test_age, test_source_handoff_candidate) nutzen sie. test_neuro_ledger folgt dem Standard.
4. Volle Suite: 1609 Tests OK, 5 Skips (vorher mit neuen Standardwerten 10 Fehler + 2 Errors, alle aus festen Annahmen über alte Standardwerte).


---

## QUELLE: THREAD_REGEL_LESER_V6_20261022.md

# Thread Regel-Leser v6 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31, Commit 7ba3ae6. Beleg: `v13/code/docs/proofs/continuation-20261022/user-rules-v6/` (PREREG, holdout_de3.json, generate_round6.py, round6_raw.json, freeze_v6.json, audit_round6_make.py, cohort_round6*.json, run_round6.py, Ergebnisse, BEFUND.md).

## Urteil: USER_RULES_V6_UNSAFE (aber Fehler etwa halbiert)

v6 baut hinter den genauen Leser ein breites Netz. Enthält ein Satz Verneinung, Halten oder eine Bedingung und nennt er eine bekannte Handlung oder ein bekanntes Ziel, wird er zur offenen Rückfrage. Bis zur Antwort gilt dann „erst fragen“.

| Prüfsatz | Sätze | v6 Fehlersätze | v5 |
|---|---|---|---|
| holdout_de3 (Autor) | 60 | 1 | 6 |
| Runde 6 (Qwen 2.5 7B, EXAONE 3.5 7.8B, GLM-4 9B) | 181 | 11 | 20 |

- Unnötige Rückfragen gab es bei 30–38 % der Sätze ohne Regel. Das Ziel war höchstens 30 %, es wurde also knapp verfehlt.
- Auf allen bekannten Sätzen hat v6 0 Fehler. Die Testreihe mit 1692 Tests ist grün.
- Command R7B lief im festen llama.cpp nicht und wurde vor der Erzeugung durch EXAONE ersetzt.

## Was noch fehlt (v7)
- Sperr-Wörter ohne Verneinung: ausgeschlossen, abgeschafft, blockiert.
- Ziel-Nomen am Wortende erkennen (Zusatzprogramm, Internetverbindung). Telefon/Handy als das ganze Gerät lesen.
- „sag mir, wenn …“ und „erstmal“ als Bedingung erkennen.
- Doppelpunkt-Etiketten als ganzen Satz lesen.
- Weniger Rückfragen bei Verneinung über Dritte („niemand hat mir gesagt“).

Die Grundregel bleibt: Außenwirkung gibt es nur als sichtbaren Vorschlag.


---

## QUELLE: V13_Thread_APK_oder_Termux_20261022_Teil2_Befehle.md

# Thread „APK oder Termux-Oberfläche“, Teil 2 (22.10.2026)

Auf Wunsch des Nutzers: scrollbare Liste aller Befehle mit Erklärung.
- v13/code/docs/BEFEHLE.md: alle ~116 Befehle in einfachem Deutsch, 11 Abschnitte (Sicherheit zuerst).
- Im Chat: :befehle [Wort] (ganze Liste oder gefiltert). Knopf „V13 Befehle“ auf dem Startbildschirm öffnet sie (less, /Wort sucht, q schließt).
- Test prüft, dass jeder Befehl aus operator.py erklärt ist.
Commit 6129797 auf Branch claude/project-thread-e53fle, PR #34. Volle Testsuite 1752 OK.


---

## QUELLE: V13_Thread_APK_oder_Termux_20261022.md

# Thread „APK oder Termux-Oberfläche“ (22.10.2026)

Ergebnis: in Termux bleiben, keine APK jetzt, keine Web-Oberfläche auf localhost.
Gebaut (WP-UI1): Startbildschirm-Knöpfe über Termux:Widget (V13 Chat, Status, Notaus, Stillstand).
Knöpfe können Stopps nur einschalten; aufheben nur getippt im Chat.
Code: Branch claude/project-thread-e53fle, PR #34 (Basis PR #30). Volle Testsuite 1750 OK.
Dateien: v13/code/KNOEPFE_EINRICHTEN.sh, v13/code/v13/phone_halt.py, v13/code/docs/HANDY_OBERFLAECHE.md, tests/test_phone_halt.py.
Offen: Prüfung am Redmi (HANDY_TESTLISTE, Abschnitt „Knöpfe“).


---

## QUELLE: THREAD_FEHLALARM_SELBSTKORREKTUR_20261022.md

# Thread "Fehlalarm Selbstkorrektur" (WP-AGE0c), 2026-10-22

Branch claude/project-thread-ozmbv5 (Basis 2p69gl @ 3403403), Draft-PR gegen 2p69gl.
Vorregistrierung Commit 73ef6f4 (K1 Fehlalarm <= 10 % / obere Grenze <= 15 %, K2 >= 50 % begruendete Alarme, K3 >= 20 Punkte Trennschaerfe).

Ergebnis AGE0C_STAY_SHADOW:
- 1137 echte B1/B2-Angebote (STEP2 + Kalibrierung) wiedergegeben, echter Code = Nachbau.
- Heutiger Erkenner: 100 % Fehlalarm bei richtiger JSON-Antwort, 41 % bei knapper Antwort, 19 % bei Antwort mit Fragewiederholung.
- 0 % der Alarme nennen den echten Fehler, 0 Trennschaerfe.
- Grund: needs_reentry ist in allen 400 STEP2-Angeboten true (Koerper sieht Antwort nie); fehlende Zahlen sind Echos der Frage.
- Varianten (ohne needs_reentry, mit Echo-Filter) finden ebenfalls keinen echten Fehler.
- deliver nicht empfohlen, Standard bleibt shadow. Neues Paket WP-AGE0d: Pruefung, die die Antwort sieht.

Dateien: v13/code/scripts/age0c_false_alarm.py, tests/test_age0c_false_alarm.py, docs/proofs/continuation-20261022/age0a-false-alarm/{PREREG,BEFUND}.md + report.json. Suite 1750 OK.


---

## QUELLE: THREAD_REGEL_LESER_V5_20261022.md

# Thread Regel-Leser v5 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31 (Entwurf, Basis 2gzrwi / PR #28). Commit d180cf3.
Beleg: `v13/code/docs/proofs/continuation-20261022/user-rules-v5/` (PREREG, holdout_de2.json, generate_round5.py, round5_raw.json, freeze_v5.json, audit_round5_make.py, cohort_round5*.json, run_round5.py, Ergebnisse, BEFUND.md).

## Urteil: USER_RULES_V5_UNSAFE

| Prüfsatz | Sätze | v5 | v4 | v3 |
|---|---|---|---|---|
| T1 holdout_de2 (deutsch, vom Autor) | 46 | 25 Fehler in 7 Sätzen | 27/8 | 27/8 |
| T2 Runde 5 (Mistral 7B, Falcon 3 7B, OLMo 2 7B; deutsch) | 100 | 45 in 19 | 52/23 | 63/25 |

- Auf allen bekannten Sätzen hat v5 0 Fehler. „nur wenn“ wurde nie als Lockerung gelesen.
- Neue Formen, die noch fehlen: trennbare Verben („fass … an“), „niemand“, „Schluss mit“, „lässt du bleiben“, „lass die Finger von“, „Erst fragen, dann ändern“, Etiketten.
- Aya Expanse lief nicht im festen llama.cpp und wurde vor der Erzeugung durch Falcon 3 ersetzt (in der PREREG festgehalten).

## Folgerung
Ein fester Wortleser kommt auf offener deutscher Alltagssprache nicht gegen 0 Fehler. Für v6 ist deshalb ein Architekturwechsel vorgesehen:
1. Breites Netz: jedes Halte-, Verneinungs- oder Bedingungssignal und jede Bitte zusammen mit einer Handlung oder einem Ziel führt mindestens zu einer Rückfrage mit Vorschlag.
2. Bestätigung statt Raten: Der Nutzer bestätigt, wie der Leser die Regel verstanden hat. Bis dahin gilt „erst fragen“.
3. Die Grundregel bleibt: Außenwirkung gibt es nur als sichtbaren Vorschlag.



---

## QUELLE: THREAD_HARNESS_HX1_HX3_HX4_20261022.md

# Thread „Harness-Pakete HX1 HX3 HX4“ (2026-10-22)

Basis: Branch claude/project-thread-2p69gl (PR #30). Arbeits-Branch: claude/project-thread-4iqpro (RedMentos/Aii). Code liegt in Git; diese Notiz ist die Drive-Sicherung des Stands.

## Was gebaut wurde (alles SHADOW, Autorität 0, kein Modell)
- WP-HX1 `v13/code/v13/agi/harness.py` + Art `harness` in `agi/self_improve.py` (AG8): feste Liste von 20 änderbaren Zielen (Prompt-Teile answer_rules/digest/task_context/hypotheses/clarify/replay/duplex_handoff/welcome je en/de, tool_hint.list_note, tool_hint.eligibility_note, parser.listarith_extra, recipe.list_result). Nie änderbar: system, conduct, Operator-/Nutzer-Regeln, Verbote, Age, Kanal. Zweites Netz gegen regelschwächende Texte (Wort-Heuristik). Gleicher Regressionsschild, Nutzerfreigabe; HarnessLibrary.apply() nur für freigegebene Vorschläge, rollback() auf Vorversion, harness_hash fürs Generation-Manifest. Kein Live-Pfad liest die Überschreibungen.
- WP-HX3 `agi/experience.py`: Eintrag nur mit Freigabe + bestandenem Schild + Beleg-Datei (sha256). verify() -> STALE bei geänderter Datei, retire() nach Rücknahme, lookup() liefert Daten (DATA_NOT_INSTRUCTION), ablation() mit/ohne.
- WP-HX4 `agi/blind_select.py`: Richter sieht nur Buchstaben + geschwärzten Text, Herkunft per Hash versiegelt, nach Wahl aufgedeckt; zwei Runden gegen Positions-Vorliebe (INCONSISTENT), Fehler = NO_PICK.
- Tests: `v13/code/tests/test_harness_hx.py` (10). Laufzeit-Dateien runtime/runners/store/memory_server unverändert.
- research/HARNESS2_AUSWERTUNG.md aus Branch 1x4aho (PR #23) mit in diesen Branch gemergt.

## Nächster Schritt
WP-HX2: Referenz + Varianten auf derselben Aufgabe mit echten Modellen, erste Probe STEP2 B2-Regel-Zitat; nutzt HX1 (Vorschlag), HX3 (Bibliothek), HX4 (Auswahl). Vorregistrieren vor dem Lauf.


---

## QUELLE: THREAD_REGEL_LESER_V4_20261022.md

# Thread „Regel-Leser Version 3“, Teil 2: v4 + Runde 4 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31. Befund `v13/code/docs/proofs/continuation-20261022/user-rules-v4/BEFUND.md`.

Urteil `USER_RULES_V4_UNSAFE`.
- v4 aus den Runde-3-Fehlern (englische Umgangssprache): bekannte Sätze inkl. Runde 3 → 0 Fehler.
- Runde 4 (versiegelt; Phi-4-mini, Granite 3.3 2B, EuroLLM 9B; 630 roh, 93 geprüft, 67 deutsch): v4 13 Fehler in 6 Sätzen, alle deutsch; v3 und v2 gleich. Englisch 0/26.
- Gefährlichste Form: „Du darfst nur Nachrichten senden, wenn …“ / „erst … wenn ich erlaube“ wird als Lockerung gelesen (Regel entsteht nicht).
- Weitere: „Bleib ab von meinen Notizen!“, „Kein Versand!“, „Kein Kram ohne mein grünes Licht“, „Bitte keine Dateien herunterladen“ (zu eng).
- Nebenbefund 202 übersetzte Sätze: v4 37 Fehler / v3 41 / v2 43.
- Nächster Schritt v5: Bedingung vor Lockerung, deutsche Halte-Formen, Nomen zu Handlungen, Handlung mit eigenem Ziel; Runde 5 aus deutschen Quellsätzen.
Commits: b13d355 Vorregistrierung, 39c4994 Runde 4 versiegelt, ec69532 v4 eingefroren, 9d1f822 Ergebnis.


---

## QUELLE: THREAD_REGEL_LESER_V3_20261022.md

# Thread „Regel-Leser Version 3“ (2026-10-22)

Branch `claude/project-thread-c62rfz` (aufgebaut auf PR #28 / Branch 2gzrwi), Repo RedMentos/Aii.
Befund: `v13/code/docs/proofs/continuation-20261022/user-rules-v3/BEFUND.md`.

Urteil: `USER_RULES_V3_UNSAFE`.
- Runde 3 (versiegelt vor dem Code; Gemma 3 4B, Llama 3.2 3B, SmolLM3 3B; 354 Rohsätze, 149 von Hand geprüft):
  v3 58 Sicherheitsfehler in 19 Sätzen (11 übersehene Verbote), v2 92 in 29.
- Bekannte Sätze (Dev, Holdout, Runde 1, Runde 2): v3 0 Fehler (v2 Runde 2: 20).
- Übervorsicht 31 % der erlaubten Proben.
- Neue Fehlerformen: lässige Bitte als Frage („could you like, not …?“), Verbot ohne Verneinung („put the calculator away“, „stay offline“), „warte bis zur Freigabe“, höfliche Vorliebe mit „you can“, Etiketten-Fälle.
- Neu in v3: Lexikon als Daten mit Beleg (`v13/userrules_lexicon.json`, `extend()` lehnt versiegelte Sätze ab), vorher+zeigen = erst fragen, „rät ab/warnt vor“ = Rückfrage, Ich-Satz an die KI, Verbformen, Vorschlag bei offenen Rückfragen.
- Grundregel unverändert: Außenwirkung nur als sichtbarer Vorschlag.
- Nächster Schritt: v4 mit Grundsätzen statt Wortlisten + versiegelte Runde 4 (neue Erzeuger, deutscher Auftrag).

Commits: 032ce6b Vorregistrierung, df2c55f Runde 3 roh versiegelt, 43fa3d0 v3 eingefroren, danach Audit und Messung.


---

## QUELLE: THREAD_GPT_STAND_PRUEFUNG_RUNDE2_20261022.md

# Thread „GPT-Stand erneut prüfen“ (2026-10-22)

Branch claude/project-thread-2p69gl (Basis 2gzrwi @ 9436eb7), Draft-PR an 2gzrwi.
- GPT 22.10. geprüft + gemergt: c1d6615 (PR #29 Lernpfad-Auditor), 16a0b17 (PR #27 Age-0/Freeze-Notiz), Drive V13_JEPA_AGE0_REVIEW_20261022.md. Alle Aussagen bestätigt (14/14 jepa_weight 0; plen=0 Fehler; nur C3 hat Gewichts-Updates, B1/B2 keine).
- Runde 1 (PR #8) war nie in der Kette, nachgeholt.
- Neu WP-SAFE2 :stillstand (Notaus + Warteschlange + Age-Freeze; bestätigt erst nach Ende des laufenden Vorgangs; bleibt über Neustart; hebt nur eigene Teile auf). Grund: unter :notaus liefen Lernen/Traum/Replay/Training weiter.
- Suite 1727 OK, 5 Skips; Privatsphäre-Scan CLEAN.
- Neue Pakete: WP-AGE0a (späte Selbstkorrektur), WP-AGE0b (Organ-Checkpoint), WP-LP1 (Lernpfad Komponenten-Gradienten).
- Antwort an GPT: v13/code/docs/coordination/CLAUDE_ANTWORT_AGE0_LERNPFAD_20261022.md


---

## QUELLE: Thread Zitierhilfe an, Regeln per JEF (2026-10-21)

﻿Sicherung Thread "Zitierhilfe an, Regeln ohne Halluzination" (2026-10-21)
Branch: claude/project-thread-2gzrwi (RedMentos/Aii). Enthält PR #7, #19, #21 und WP-SAFE1 (:verbot/:notaus aus Thread "Sicherheit: Verbote modellunabhängig").


Nutzerentscheidungen:
- Zitierhilfe AN (Menschen zitieren auch direkt).
- Rückfragen zu Regeln ja, aber kein halluzinierendes Modell entscheidet Regeln: JEF / fester Baustein.
- PR #2, #3, #4 geschlossen (Inhalt schon im Stand).
- Handytest nur wenn er wirklich hilft.
- 20 englische Beispielregeln nicht nötig.
- Ziel: KI tut nichts, wovon der Nutzer nichts weiß, sagt vorher was sie tun würde, legt Verbote nie falsch aus.


Ergebnis:
- v13/userrules.py: fester Leser (kein Modell) für Verbote und "frag mich vorher" aus den eigenen Sätzen. Durchsetzung in der Werkzeug-Policy, feste Hinweise, Befehle :regeln / :regel.
- Messung: eigener Holdout 0 Fehler. Frische Umformulierungen durch 3 lokale Modelle (Runde 2): v1 71, v2 20 Sicherheitsfehler (8 von 57 Sätzen) -> USER_RULES_UNSAFE.
- Schreibende Werkzeuge laufen ohnehin nie automatisch (nur Vorschlag), automatisch laufen nur Rechen-Werkzeuge.
- Fazit: fester Wortleser allein reicht nicht für offene Sprache; Garantie trägt "Außenwirkung nur als Vorschlag" + feste :verbot-Zeilen.
- Befund: v13/code/docs/proofs/continuation-20261021/user-rules/BEFUND.md


Offen: v3 mit den 8 Fehlerformen + frische Runde 3; Merken/Lernen im Gedächtnis durchsetzen; feinere Wirkungsklassen.

---

## QUELLE: V13-Sicherheit-Verbote-Notaus-20261021.md

# Thread "Sicherheit: Verbote modellunabhängig" (2026-10-21)

Git: Branch claude/project-thread-rdesm7, PR #26 (Basis claude/project-thread-0zelvf). Auch im Projektordner-Code eingespielt.

Neu: code/v13/prohibitions.py, tests/test_prohibitions.py (16 Tests), docs/VERBOTE_UND_NOTAUS.md.
Geändert: transaction.py (authorize: Verbote als 1. Schritt + Vorabansage; execute: letztes Tor), agi/tools.py, toolstep.py (kein Schatten-Rechnen bei Verbot), operator.py (:verbot, :notaus).

Befehle: :verbot | :verbot werkzeug <Name> | :verbot art NETWORK | :verbot unumkehrbar | :verbot alles | :verbot weg V1 | :verbot ansage an|aus | :notaus | :notaus aus

Befund:
- Feste Regelprüfung existierte schon (IH-H29 in transaction.authorize, vor der Ausführung, reiner Code). Es fehlten: Nutzer-Verbote, Notaus, Vorabansage für alles. Jetzt da.
- Verbot schlägt Einzelfreigabe; zweite Prüfung direkt vor der Funktion; nur Nutzer ändert; beschädigt = alles gesperrt.
- Neuromod-Veto wirkt nur aufs Lernen (Standard RECORD_ONLY -> keine Wirkung; live nur C6-Regelverstoß als Veto-Quelle).
- Selbst-Unsicherheit hebt live den Rechenaufwand; "nachfragen statt raten" nur Beobachtungsmodus.
- Volle Suite 1597 Tests, nur alter Fehler test_neuro_ledger (auch auf Basis rot).
Offen WP-SAFE2: Verbots-Treffer als Veto-Signal; Nachfrage-Modus messen (mit WP-DS3).

---

## QUELLE: Thread DeepSeek-Kritik 2026-10-21 (WP-DS1, PR 25).md

Thread "DeepSeek-Kritik gegen Stand prüfen", 2026-10-21. Git: branch claude/project-thread-qt2cqv, PR #25 (RedMentos/Aii). Volltext: v13/research/DEEPSEEK_KRITIK_AUSWERTUNG.md.

Bewertung: Neuromodulation existiert (neuromod.py, homeostasis.py, curiosity.py; steuert v.a. Lernen, Verhalten kaum). Active Inference teilweise (Vorhersage vor Handlung da, kein Vergleichstest). Verkörperung echte Lücke (STEP8 gesperrt). Metakognition existiert (agi/metacog.py AG9, selfmodel.py, C3-Unsicherheit AUROC .84). Lernender Balken existiert (callosum.py, b3bridge.py); MoE-Router nur isolierter Kandidat (Z10).

WP-DS1 erledigt: Lab-Sandkasten code/v13/sandbox.py, Vorregistrierung vor Lauf (Commit 3f3cb09), Seeds 100..119, alle 4 Hypothesen PASS.
Fehler@600: Zufall .34, Überraschung .61 (94% am Rausch-Fernseher), Neuheit .17, Lernfortschritt AG5 .16 (bester), Informationsgewinn .21, +Hungerziel .23 (Hunger .05 bester, neues Objekt nur 7/20).
Offen: WP-DS2 kombinierte Policy (Lernfortschritt + Ziel + Neuheits-Kanal), WP-DS3 Unsicherheit -> Werkzeug-Nachprüfung / "unsicher" sagen.

---

## QUELLE: V13-Z5c-Koalition-Aktualitaets-Term-20261021.md

# WP-Z5c Aktualitäts-Term für Notizen in der Koalition (2026-10-21)

Thread „Koalition Aktualitäts-Term“, Branch claude/project-thread-8zhj41 (auf Z5b, PR #16), Draft-PR folgt im Repo RedMentos/Aii.
Beleg: v13/code/bench-results/z5c-recency-20261021/ (PREREGISTRATION.md, README.md, z5c.json, run.log).

Schalter focal_note_recency (0/1, Standard 0): Notizen mit gleichem Schlüssel bis auf Kalenderwörter/Zahlen = Versionen; neueste gespeicherte +0,10 (recency), ältere -0,30 (superseded).

Lauf: Z5b-Aufgaben, 3 Saaten (11,12,13) x 2 Läufe x 60 = 360 Turns, Platzgrenze bindet immer, kontrafaktische Koalition ohne Term aus denselben Kandidaten (Treue 360/360).

Mechanismus: update neueste Notiz in Koalition 1,00 statt 0,90, veraltete 0 statt 0,95; combine benötigte 0,75 statt 0,63.
Antworten: mit Term 93/360, ohne 90, Voll-Kontext 97, Retrieval 98, ohne Kontext 64. Mit vs ohne 24:21 p=0,77; vs Voll-Kontext 30:35 p=0,62. Rauschband 2.
Verdikt: Term hilft FAIL, schlägt Voll-Kontext FAIL, Gate G-FOCAL-CAPACITY-003 bleibt PARTIAL, Schalter bleibt aus.
Befund: bei update schlechter als Voll-Kontext (3:21); bei schmaler Koalition antwortet das Organ oft nur "2" (33/82 Turns).
Nächster Schritt: Ersetzungs-Kette sichtbar im Kontext statt veraltete Notizen wegzulassen; Ursache der "2"-Antworten prüfen.
Cloud-Hinweis: Container wird im Leerlauf zurückgesetzt; lange Läufe als überwachte Hintergrund-Aufgabe mit Zwischenspeicher.



---

## QUELLE: THREAD_B3_L1_ESCALATE_APOLOGIZE_20261021.md

# Thread "B3 L1 escalate apologize" (2026-10-21)

Branch claude/project-thread-yub2lf (stacked on c122qc / PR #20), draft PR #22.

## Cause (exploratory diagnosis on attempt-4 states)
escalate/apologize need a receiver-private fact (capacity/client, 100 % decodable from receiver state) combined with U/F. The bridge read as an additive residual on the FROZEN NO_MESSAGE readout, so the fact weights could not be rescaled to the message. With the true U/F that costs 8.2/9.3 points (on action it helps, -5.5). The same message with a jointly refit readout gains +8.0/+5.5 points (5/5 seeds). 72-78 % of errors fall within 1 of the threshold.

## Fix
Bridge(recv_cond=dim) + Bridge.refit_readout (default off, byte-identical; gate closed = old readout).

## Attempt 5 (preregistered 9d52f49, fresh seed 20261105, new B1/B2 states, gate unchanged)
- escalate 90.5 vs attr words 84.7 / label 78.7 / SCALAR 89.2: canon L1 PASS (strict FAIL n.s.)
- apologize 89.0 vs attr words 88.5: FAIL (n.s.)
- action replication 86.7 vs label 83.5: FAIL (n.s.). The attempt-4 action PASS depends on the seed.

Consequence: L2 prefix SHADOW is allowed only for private/escalate. Next: WP-Z4d L1 robustness on 2 more fresh seeds, then L2 for escalate.
Evidence: project folder v13/bench-results/b3-l1-escapo-diagnose-20261021/, v13/bench-results/b3-l1-v5-20261021/ (states.npz only there).


---

## QUELLE: THREAD_Z2D_B2_REGELZITAT_20261021.md

# Thread „B2 zitiert Regel selten“ — WP-Z2d (Code: z2c), 2026-10-21

Branch `claude/project-thread-0fckhc` (Basis `s439sv` = Z2b), Draft-PR #21. Prereg `8cc006d` (vor Inferenz), Ergebnis `058e8c7`.

## Ursache
B2 kennt die alte Regel, schreibt sie aber um oder zitiert den Aufgabentext. Von 384 Z2b-B2-Angeboten (RULE/SPLIT) trugen nur 115 die volle Regel; 110 scheiterten an einer Umschreibung bzw. kaputten Kopie des richtigen Satzes, 65 zitierten den aktuellen Aufgabentext.

## Änderung
Schalter `b2_quote_select` off (Standard) | anchor | pointer. Kettenglied `integrated_candidates.b2_quote_select`, Tests `test_b2_quote_select.py`.

## Ergebnis (CQ/CQA/CQP × Seeds 17–19, 630 Zeilen)
- B2-Regelquote: Kontrolle .167, Anker .542 (teilweise), **Zeiger .969 (FIXED)**
- 0 falsche Regelwerte, 0 falsch festgelegte Entscheidungen
- Zeiger: zwei Körper .881 vs. b1_only .581 (+.30, CI > 0, jeder Seed), 27/30 exakt
- STEP2 bleibt formal FAIL (Kriterium 3, Ein-Körper-Kontrolle offen)

## Offen
Nutzerentscheidung: Zeiger einschalten; vorher live-`analyst_context` reparieren. Neues Prereg mit Ein-Körper-Kontrolle und längeren Regeln. Merge-Hinweis: Thread 4ttld7 (Kettenglied body_question) beim Zusammenführen hintereinander anwenden.
Befund: `v13/code/docs/proofs/continuation-20261021/step2-z2c-b2-rule/BEFUND.md`


---

## QUELLE: V13-Z4b-L2-Prefix-action-20261021.md

# WP-Z4b B3 L2-Prefix-SHADOW nur private/action — 2026-10-21

Thread „Z4b L2 nur für action“, Branch claude/project-thread-c122qc (auf PR #17), Draft-PR #20. Commits e0d6cd5 (Präregistrierung, vor Messung), df5c6cc (Ergebnis).

Aufbau: 64-B-Nachricht der L1-Brücke (Versuch 4, exakt reproduziert, Digest 3c75aad1…) -> Ausrichtung in den Eingabe-Embedding-Raum von Qwen3.5-0.8B Q4_0 -> Kalibrierung auf native Token-Statistik (Normverhältnis 1,00) -> 4 Prefix-Slots über llama.cpp b10964 batch.embd -> Auslesen nur über die eigenen Text-Tokens des Empfängers (eingefrorenes Rückgrat).

Ergebnis (5 Seeds): Prefix 80,2 % | aus 41,5 | vertauscht 37,5 | zufällig 37,8 | EXACT-Text 76,5 | Label-Wort-Text 81,5 | Attribut-Wörter 74,8 | L1 (Adapter) 90,0.
Urteil: L2 FAIL (einzig fehlendes Kriterium: Nutzen vs. Label-Wort −0,017). Explorative Variante EXACT_ALIGN 77,5 % ebenfalls FAIL.
Nebenbefunde: L2 9,8 Punkte unter L1; alter Themen-Kopf fällt mit Prefix 100 % -> 40 % (neu trainiert 0 Verlust).
Folge: B3 bleibt L1_shadow, L3 gesperrt, Autorität 0, Runtime unverändert. Neuer L2-Versuch nur auf Aufgabe ohne billiges Label-Wort (vorher L1 auf escalate/apologize bestehen).

Belege: Repo v13/bench-results/b3-l2-prefix-20261021/ (README, report.json, run.log); Projektordner gleich. Werkzeug code/scripts/native/b3_prefix_embd.cpp, Skript code/scripts/b3_l2_prefix_bench.py, Gate b3bridge.l2_gate.


---

## QUELLE: THREAD_Z2C_B1_FRAGE_SCHALTER_20261021.md

# Thread „B1-Frage als Schalter“ (WP-Z2c), 2026-10-21

Branch `claude/project-thread-4ttld7` (Basis Z2b `s439sv`), Draft-PR #19, Commits 061d778 (Code+Tests+Runner, vor Lauf) und 915ff6d (Ergebnis).

- Neue Schalter `body_question_b1` / `body_question_b2` (Standard '' = aus, live unverändert). Feste Frage als jef_query (FILL_GAP) an jedes Körper-Angebot ohne Re-Entry-Fokus. Kettenglied integrated_candidates.body_question, Tests test_body_question.py. Suite 1608, nur Altfehler test_neuro_ledger.
- Bestätigung Seed 14 (echte Modelle, Linux): Schalter beide both_exact .592 (ohne .375, Z2b-Patch .675); nur B1 .450; b1_only .275 -> .575; 0 falsch in 140 Werkzeug-Zeilen.
- Frage ist STEP2-spezifisch -> bleibt aus. Offen: Nutzerentscheidung, allgemeine Chat-Frage ungemessen, Paket „B2 liefert Regel-Zitat“, Seed-Bug cognition.offer.
- Rohdaten: Projektordner v13/bench-results/step2-z2c-switch-20261021/; Befund im Repo docs/proofs/continuation-20261021/step2-z2c-switch/BEFUND.md.


---

## QUELLE: V13-Z5b-Koalition-Platzmangel-20261021.md

# WP-Z5b: Fokus-Koalition unter echtem Platzmangel (G-FOCAL-CAPACITY-003), 2026-10-21

Thread „Z5b Koalition mit Platzmangel“, Git-Branch claude/project-thread-bn7n5k (Basis: Z5-Branch hmopsm), Draft-PR #16 (RedMentos/Aii).
Beleg im Repo: v13/code/bench-results/z5b-capacity-20261021/ (PREREGISTRATION.md, README.md, z5b.json, Logs); Skript v13/code/scripts/z5b_capacity.py; Tests v13/code/tests/test_z5b_capacity.py. Auch im Projektordner v13/code/ gespiegelt.

## Aufbau
60 neue Aufgaben (update / combine / correction / distract, Saat 11), je 6 gespeicherte Notizen (alle abgerufen, memory_top_k 6), Effort max, 4 Plätze, 5 Läufe, echte Modelle (C3 LFM2.5-350M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), Cloud-CPU. Vorregistriert vor dem Lauf. Wiedergabe-Treue 300/300.

## Ergebnis
- Platzgrenze greift jetzt in 300/300 Turns (9 Kandidaten für 4 Plätze; in Z5 nie). 11 Verdrängungen.
- Bestanden/300: ausgeliefert 68, Koalition als Engpass 60, Voll-Kontext 54, feste Slots 55, nur Retrieval 64, ohne Kontext 47.
- Koalition vs. Voll-Kontext 33:27, p = 0,52, Vorsprung 1,2 je Lauf < Rauschband 4 → „schlägt Voll-Kontext“ FAIL. Nicht schlechter als Retrieval und feste Slots.
- Eigenschaften 1, 2, 3, 5, 6, 7 gemessen; 4 (Aufnahme nur über Salienz) nie → G-FOCAL-CAPACITY-003 bleibt PARTIAL.
- Nach Art (ausgeliefert / Koalition / voll / fest / Retrieval / ohne): update 0,23/0,16/0,21/0,15/0,07/0; correction 0,25/0,16/0,05/0,01/0,53/0; distract 0,43/0,48/0,45/0,57/0,25/0,63; combine überall 0.

## Befunde
1. Unter echtem Platzmangel ist die Koalition nicht besser als „alles in den Kontext“ (Rauschen).
2. Die Koalition behält oft die falsche Notiz (correction: Retrieval 0,53 vs. Koalition 0,16), weil die Priorität keinen Term für Aktualität/Ersetzung hat.
3. Im ausgelieferten Pfad gehen abgerufene Notizen an der Koalition vorbei in die Antwort; die Koalition filtert nur Körper-Angebote.
4. Die Auswahl spart 44 % Kontext ohne messbaren Verlust (Ressourcen-Argument, kein Gate-PASS).

## Abweichungen
Lauf 5 brach zweimal ab (Container-Neustart; ein Wiedergabe-Arm überschritt das native Kontextfenster). Fehlerbehandlung repariert (Skip statt Absturz, keine Regeländerung), Lauf 5 vollständig neu, ohne Skip.

## Nächster Schritt
Aktualitäts-/Ersetzungs-Term für Notizen in der Fokus-Priorität, neu vorregistrieren, dieselben 60 Aufgaben gegen dieselben Kontrollen. Aufgaben für Eigenschaft 4 (salienter Kandidat unter der Prioritätsschwelle).


---

## QUELLE: THREAD_Z2B_STEP2_SEEDS_20261021.md

# Thread „Z2b STEP2 mit mehreren Seeds“ (2026-10-21)

Branch `claude/project-thread-s439sv` (Basis: Z2-Branch hsm0ga), Draft-PR #18. Vorregistrierung f5b9d03, Ergebnis f7d9611.
Belege: v13/code/docs/proofs/continuation-20261021/step2-z2b-seeds/ (PREREG.md, BEFUND.md), v13/code/bench-results/step2-z2b-seeds-20261021/. Volle STEP2-Berichte liegen im Projektordner v13/bench-results/step2-z2b-seeds-20261021/.

## Was gemacht wurde
- Arme C/D (wie Z2) und CQ/DQ: dazu eine feste gezielte Frage über jef_query, nur in der aktuellen Runde. B2 soll die früheren Regeln zitieren, B1 die Optionswerte. Alles mal Seeds 14/15/16, ergibt 840 Zeilen plus Werkzeug-Replay. Echte Modelle, Linux-Cloud, kein Redmi.
- Fund vor dem Lauf: Die Körper-Angebote haben cfg['seed'] nie benutzt (immer Seed 13). Das ist im Skript behoben, der Live-Code ist unverändert.

## Ergebnis
- Z2B_DIVERGENCE_NOT_SUPPORTED: Zwei Körper liegen bei .611, B1 allein bei .592, Differenz +.019 (CI −.075 bis +.106). Ein Körper mit zwei Zuständen ist gleich gut.
- Z2 war Rauschen: C both_exact schwankt über die Seeds zwischen .308 und .450. Zwischen Qwen und LFM als B2 zeigt sich kein klarer Unterschied.
- Die gezielte Frage hilft klar: +.23 (CI +.12 bis +.34). B1 liefert die Optionswerte dann in 170 statt 63 von 210 Zeilen.
- 0 falsch festgelegte Entscheidungen.
- Engpass ist jetzt B2: Es zitiert die alte Regel nur in etwa ¼ der Zeilen.

## Offen
(a) Nutzerentscheidung, ob die gezielte B1-Frage als Schalter (aus) in den Live-Pfad kommt. (b) Paket „B2 liefert das Regel-Zitat“. (c) cognition.offer soll seed=cfg['seed'] übergeben.


---

## QUELLE: THREAD_R_B3L1_V4_UND_SCHLUESSELTRENNUNG_20261021.md

# Thread „Nächste Pakete R“ – 2026-10-21

Branch `claude/project-thread-8hlx74` (Basis `claude/project-thread-0zelvf`), Draft-PR #17. Commits: eaf49b7 (Prereg B3 v4), f2f6976 (Fix + Prereg v3), f09ef8b (nativer Scope-Fix + Prereg v3b), ffc3d8e (Ergebnisse + Doku).

## WP-Z4 B3 L1 Versuch 4 – L1 PASS auf private/action
- Frische Saat 20261021 (600 Zeilen, 0 Überschneidung mit Versuch 3), neue B1 LFM2.5-1.2B / B2 Qwen3.5-0.8B Zustände (b10964), aux-Brücke (U,F nur Training), Gate unverändert.
- action: LATENT 90,0 % (ohne aux 80,0; SYMBOLIC 81,5; Attribut-Wörter 76,7; SCALAR 85,2) -> Kanon-L1 PASS (Rollen-Verlust 0, OOD 1,3 %, Reload bitgleich). escalate 83,0 / apologize 85,0 -> FAIL gegen Attribut-Wörter. Strikt gegen SCALAR FAIL.
- Folge: nur L2-Prefix-SHADOW für private/action erlaubt (nächstes Paket Z4b); Autorität 0, Runtime unverändert.
- Belege: Projektordner v13/bench-results/b3-l1-v4-20261021/ (inkl. states.npz 231 MB), Git ohne states.

## Native Firing-Diagnostik / WP-T9 v3 – Schlüsseltrennung
- Ursachen falschen Feuerns: gemeinsame Guard-Wörter („favourite“) und Guard auf ganzem Prompt (Exakt-Block öffnet fremde Slots).
- Fix (Standard aus): guard_distinct + guard_vocab, guard_scope='last_user' (torch + nativ; V13SMEM1 Feld 6 = 2+Marker).
- v3: fremdes Feuern 24->17 Zeilen, auf Faktfragen 4->0. Nativen Fehler gefunden (Scope nur im Cache-Präfix), behoben, v3b: combined 84->17, selektiv 25->16.
- KEY_SEPARATION_SUPPORTED; SELECTIVE_DOES_NOT_WIN (2:5 gegen exakt, vorher 2:9; Verluste = falsche Spur-Werte auf Paraphrasen).
- Belege: v13/bench-results/selective-delivery-v3-20261021/ (+ v3b/).

## Sonst
- b3bridge.save übernahm alte Revisionen -> behoben + Test.
- 19 fehlende §102-Belegordner ins Git, test_neuro_ledger grün. Suite 1591 Tests.
- Zwei Läufe wurden durch einen Container-Neustart abgebrochen (vor Ergebnissen), danach neu gestartet.

## Offen
- Z4b: L2-Prefix-SHADOW für private/action (vorregistrieren).
- Schnelle Spur: Wertqualität auf Paraphrasen (z. B. Paraphrase-Kontexte beim Schlüssel-Schreiben).


---

## QUELLE: V13-Z5-Fokus-Koalition-20261021.md

# WP-Z5 Fokus-Koalition gegen §99-Kontrollen (2026-10-21)

Git: RedMentos/Aii, Branch claude/project-thread-hmopsm @ db31f9c, PR #15 (Basis claude/project-thread-rxq188).
Belege: v13/code/bench-results/z5-focal-controls-20261021/ (PREREGISTRATION.md, README.md, z5.json), Skript scripts/z5_focal_controls.py, Tests tests/test_z5_focal_controls.py.

Aufbau: 60 WP-T3b-Aufgaben x 5 Läufe, echte Modelle, Effort max. Kontroll-Arme im selben Turn aus denselben Angeboten an dasselbe Organ (C5 wählte B1 165x, B2 135x, nie C3). Wiedergabe-Treue 300/300.

Bestanden (300): Koalition 186, Voll-Kontext 183, feste Slots 193, Retrieval 184, ohne Hypothesen 195.
Gepaart: vs Voll 17:14 p 0,72; vs feste Slots 15:22 p 0,32; vs Retrieval 32:30 p 0,90. Rauschband 7.
Verdikt: schlägt Voll-Kontext FAIL; nicht schlechter als Retrieval/feste Slots. G-FOCAL-CAPACITY-003 bleibt PARTIAL.
7 Eigenschaften: Wettbewerb 201/886 abgelehnt, Re-entry 289/300, Quellbindung 685/685, Halten/Wiederherstellen 886/886 ja. Kapazitätsgrenze, Ersetzung, Interrupt 0 (max. 3 Kandidaten bei 4 Slots).
Nach Art: Hypothesen helfen bei summary (0,57 -> 0,71), schaden bei compare (0,33 -> 0,12).
Lauf 5 nach Sitzungsabbruch komplett neu gefahren.
Nächster Schritt: neue Vorregistrierung mit Kapazitätsdruck (Ablenker-Erinnerungen, mehrere Turns, Embedding-Retrieval).



---

## QUELLE: THREAD_Z2_STEP2_B1_DETAIL_20261021.md

# THREAD Z2 STEP2 mit B1-Detailinfo (2026-10-21)

Git: RedMentos/Aii Branch claude/project-thread-hsm0ga @ 6a8937d (Prereg bdaafc2). Volle Berichte: Projektordner v13/bench-results/step2-z2-timescale-20261021/.

# Befund WP-Z2: STEP2 mit Information, die nur B1 hat (2026-10-21)

Vorregistrierung PREREG.md (Commit bdaafc2, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, kein Redmi.
Modelle/Runner byte-gleich mit 13.10./20.10.: B1 LFM2.5-1.2B bb741ebb, B2 Qwen3.5-0.8B 57d19977, C3 LFM2.5-350M 3d10b6ab, llama.cpp b10964 79e31218.
5 Arme x 70 Zeilen, alle RECORDED, 0 Strukturfehler; dazu Werkzeug-Replay je Arm (350 Zeilen).

## Ergebnis: Z2_DIVERGENCE_NOT_SUPPORTED (Gate FAIL)
1 C both_exact > bester Einzelkörper: .325 vs b1_only .333 -> nein
2 B1 und B2 gewinnen je eine Episode: ja
3 komplementäre Fehlerprofile (>= .25): Optionsfelder b1 .57 / b2 .37, Regelfelder beide .10 -> nein
4a > gleiches Modell gleiche Policy: .325 > .308 -> ja
4b > gleiches Modell nur anderer Prompt (D prompt_only_dual): .325 < .425 -> nein
5 Struktur: ja
§99 "zwei Körper lohnen": nein (ein Körper + zwei Zustände .367 >= zwei Körper .325).

## Sekundär
- Neuer Schalter b1_recent_source_chars (0 = aus): B1 behält exakte Quelle der letzten Runde. Damit liefert B1 Optionswerte als verifiziertes Zitat 27/70 (vorher 0).
- Erstmals exakte SPLIT-Entscheidungen, aber nur im Ein-Körper-Arm D (both_none 3/6); Zwei-Körper-Arm 0/6.
- 0 falsch festgelegte Entscheidungen in 350 Werkzeug-Zeilen; ohne Werkzeug 0 exakt.
- Ohne Zitat-Kontext (Arm E) 0 verifizierte Zitate.

## Pannen
- Arm C Nachbearbeitung brach ab (altes Feld 'prior'), Zeilen weiterverwendet.
- Arm D Versuch 1: Hash-Wächter kannte shared_body nicht, alle Vorbereitungen ERROR; korrigiert, neu gelaufen, Versuch 1 aufbewahrt.

## Empfehlung
Schalter bleibt aus. Nächstes (neu vorregistrieren): Rauschband mit 3-5 Seeds für C/D; gezielte JEF-Rückfrage "zitiere Regel/Optionen"; Qwen- vs. LFM-B2 als gebundene Modellfrage.


---

## QUELLE: THREAD_Z3C_ERWEITERBARER_PARSER_20261021.md

# Thread Z3c Erweiterbarer Regel-Parser (2026-10-21)

Branch claude/project-thread-x1etmj (Basis a9je9s / PR #12), Draft-PR #13. Beleg im Repo:
v13/code/docs/proofs/continuation-20261021/z3c-extensible-parser/ (PREREG.md, BEFUND.md, parser_v2.py, lexicon.json, z3c_run.py, Tests, run/).

Reihenfolge: 62c5c7f Vorregistrierung + versiegelter Autor-Holdout -> dac892a Parser eingefroren -> cc34bda B1-Runde 1 + Audit -> 92d87ce Nachtrag A1 -> 40e0618 Runde 2 + Audit -> afde1f9 Ergebnis.

Urteil: PARSER_V2_CARRIES_AUTHOR_ONLY; sekundaer C3_TRAINING_NOT_NOW.
- kanonisch 39/39, Z3b-Paraphrasen 39/39 (vorher 0.154), Autor-Holdout 0.912 exakt, 1/57 falsch (Koeder "Nobody has decided whether the budget should be 102 euros.").
- Modell-Holdout (B1 formuliert um): nur 22/39 bedeutungsgleich -> unterbesetzt; 0.318 exakt, 0 falsch. Luecken: Lokal-Wortschatz (nearby, area, anywhere, "requirement is true"), "tops out".
- C3-Satzprobe: 57/60 true, nie null bei Koedern -> kein Trainingssignal.
Naechstes: neues Paket mit Lexikon-Erweiterung + neuem fremden Holdout (Nutzer-Saetze oder staerkeres Cloud-Modell). v2 nur SHADOW.


---

## QUELLE: THREAD_Z3B_PARSER_VS_C3_20261021.md

# Thread „Z3b Parser statt C3-Leser“ — 2026-10-21

Branch `claude/project-thread-a9je9s` (Basis xiuwmf/Z3), Commits 23eb0df (Prereg vor Lauf), 50e239f (Ergebnis). Beleg im Repo und Projektordner: `v13/code/docs/proofs/continuation-20261021/z3b-parser-paraphrase/`.

Frage: Kann C3 (350M) Regeln besser lesen als ein fester Parser? 39 kanonische + 39 umformulierte Aufgaben (gleiche Werte), 3 Seeds, 468 C3-Aufrufe, Schwellen vorab ≥80 % exakt, ≤5 % falsch.

Urteil: PARSER_SUFFICIENT_NO_C3_GAIN; sekundär BOOL_PARSER_FIX_CONFIRMED.
- Parser liest local_only, C3 nur Zahlen: kanonisch 117/117 exakt, 0 falsch.
- C3 gibt local_only immer true zurück (234/234), auch bei verneinten Umformulierungen.
- Auf Umformulierungen kein C3-Arm ≥ 0.80; einziger Gewinn (0.41 statt 0.15) mit 7.7 % falscher Wahl.
- Folge: Ja/Nein-Regeln nie vom C3 lesen lassen, auch nicht als Rückfall. Neue Wortformen brauchen erweiterbaren Parser oder Lese-Training.


---

## QUELLE: THREAD_STEP2_ENGPASS_20261021_ENDE.md

# Thread „STEP2-Nutzen Engpass“ – Stand 2026-10-21 (Ende)

- Branch `claude/project-thread-dq33gk` @ 4898f7a, PR #7 aktualisiert. Suite 1609 OK.
- Zitat-als-Zeiger-Schalter: CONTEXT_SUPPORTED (Transport 7→23/30). Fehler behoben: mit Schalter an brach jeder echte Chat-Turn in analyst_context ab.
- Ganzer Live-Turn mit meiner Eignungs-Variante: NOT_SUPPORTED (Rezept 23/24 richtig, C3 ignoriert Ergebnis).
- Thread Qs Fassung (Antwortsatz + Broker-Korrektur, TOOL_LIVE_SUPPORTED 22→32/60, sichtbar 53/60) zusammengeführt und gilt.
- STEP2 bleibt UTILITY_FAIL (B1 ohne eigene Info).
- Offen: Nutzerentscheidung Schalter einschalten; Handy-Paket mit Schaltern+Werkzeug; STEP2-Fixtures mit B1-eigener Info (WP-Z2).
- Handy-Testliste: v13/HANDY_TESTLISTE.md.


---

## QUELLE: THREAD_Q_ELIGIBILITY_LIVE_TURN_20261021.md

# Thread „Nächste Pakete Q“ – 2026-10-21

Paket: Eignungs-Werkzeug `eligibility` im echten Antwort-Turn (C5/IH-H29, SHADOW zuerst).
Git: Branch `claude/project-thread-hzzqh4`, Draft-PR #11 (Basis `claude/project-thread-0zelvf`), Commits a94f91c (Code + Vorregistrierung, vor dem Lauf gepusht), f2d99b3 (Ergebnis).

Ergebnis (60 frische Aufgaben, C3 LFM2.5-350M, Linux-Cloud, Alters-Recht nur für die Messung ersetzt):
- Antworttext richtig 22 → 32 (p .006), falsch festgelegt 33 → 23, Rezept 0/60 falsch → TOOL_LIVE_SUPPORTED
- mit Broker-Korrektur sichtbar richtig 53/60 → TOOL_SHOWN_SUPPORTED
- Schwächen: fehlende Regel sagt C3 nie selbst (nur Korrektur), geänderte Regeln liest C3 oft alt (override 5/15) → sichere Ablehnung.

Achtung: Thread „STEP2-Nutzen Engpass“ (dq33gk) hat parallel eine eigene Fassung gebaut; beim Zusammenführen toolstep.py / agi/eligibility.py / tests/test_eligibility_live.py abgleichen.
Runtime-Änderungen nur als Kettenglied in scripts/integrated_candidates.py, sonst brechen ~60 hash-gebundene Tests.
Befund: v13/code/docs/proofs/continuation-20261021/eligibility-whole-turn-q/BEFUND.md (Git + Projektordner).
Nächster Engpass: Lesen geänderter Regeln. Einschalten bleibt Nutzerentscheidung.


---

## QUELLE: THREAD_Z3_C3_KONSUMENT_20261021.md

# Thread „Z3 C3-Konsument isolieren“ — 2026-10-21

Branch claude/project-thread-xiuwmf (Basis rxq188), Commits: Prereg (vor Lauf), fe814d3 Ergebnis. Draft-PR gegen rxq188.
Beleg im Git: v13/code/docs/proofs/continuation-20261021/z3-c3-consumer/ (PREREG.md, BEFUND.md, registration.json, run/report.json, run/rows.json.gz).

Aufbau: 39 private Fixtures × 3 Seeds × 7 Arme, gleiche Exakt-Quellen; Modelle byte-gleich zum Pilot 20.10.; Linux-Cloud.
Urteil (vorregistriert): NO_CONSUMER_PATH.
- C3 direkt 0/117 exakt, immer UNKNOWN (auch mit fertigem Werkzeug-Satz), 0 falsch.
- B1 0.13 / B2 0.27 exakt, 72 % / 63 % falsche Festlegung (Positions-Bias A).
- C3 liest + Eignungs-Werkzeug strict: 0.54 exakt, 0 falsch. C3 liest Zahlen 117/117 richtig, local_only immer true.
- v2 ohne strict: 3/18 Kontrollen falsch festgelegt -> strict vor Einschalten des Live-Pfads.
- Nur Werkzeug: 1.00.
Nächstes: Z3b (Bool-Regeln deterministisch, Paraphrasen-Kohorte), neue Registrierung.


---

## QUELLE: THREAD_Z1_GATE_EHRLICH_20261021.md

Thread "Z1 STEP2-Gate ehrlich" 2026-10-21. Git: RedMentos/Aii Branch claude/project-thread-61we5j (fae26f4, 930fe5d), Draft-PR #9 -> claude/project-thread-rxq188. Projektordner: v13/code synchronisiert, ROADMAP WP-Z1 = ERLEDIGT.

WP-Z1 Gate-Ehrlichkeit (kein Modelllauf)
- Problem: gate-graph STEP2 = GREEN, weil nur all70_rowchecks_pass (Harness) geprüft wurde; Ergebnis ist UTILITY_FAIL (canonical_gate_pass false).
- STEP2 geteilt: STEP2_HARNESS (GREEN), STEP2_EXIT (§96: Komplementarität FAIL, B1/B2 je eine Episode FAIL, RSS-Budget UNMEASURED, Observer-Latenz Cloud 3,8 s PASS) -> EVIDENCE_NOT_PASSING.
- blueprint-Block: Blueprint-Kriterien für STEP2_EXIT, STEP5, alle zehn §100-Gates an gemessene Werte gebunden. Neuer Status CRITERIA_UNMEASURED; gemessenes FAIL nie mehr hinter PARTIAL.
- measure_suite: §29-Tabelle berechnet (specs/properties29.json): 3 erreicht, 15 teilweise, 6 fehlen (Hand-Einschätzung 8/14/2).
- Gates Projektstand vorher 8 GREEN/1 ENP/10 PARTIAL, jetzt 7 GREEN/5 ENP/1 CRITERIA_UNMEASURED/7 PARTIAL.
- Tests: Gate/Authority 18/18; volle Suite 1584, 1 bekannter FAIL test_neuro_ledger.
- Offen: STEP2-RSS-Budget vorregistrieren (mit Z2).
Befund: v13/code/docs/proofs/continuation-20261021/z1-gate-ehrlich/BEFUND.md


---

## QUELLE: THREAD_STEP2_ENGPASS_TEIL2_20261021.md

# Thread „STEP2-Nutzen Engpass“, Teil 2 — 2026-10-21

Nutzerziel (21.10.): AGI = wissenschaftlich, psychologisch, moralisch fundiertes System, das Menschen nicht schadet; Gehirn als grobes Basismodell; holt später selbst Module nur mit bewusster, unmanipulierter Erlaubnis und lernt daraus. Weiterarbeiten, Handy-Tests parallel nach Liste.

Git: RedMentos/Aii Branch `claude/project-thread-dq33gk` (PR #7, Basis `claude/project-thread-0zelvf`), Prereg `298b6d7`, Ergebnis-Commit danach.

## Eignungs-Werkzeug im Live-Antwortpfad
- `ToolStep._propose_eligibility`: Frage nach Option A/B unter Projektregeln → C3 liest nur typisierte Werte aus Quelle + verifizierten Body-Zitaten → deterministisches Rezept entscheidet → C5-Kandidat.
- Nur nach Freigabe `:growth enable eligibility`; Age 0 = SHADOW (berechnet, verglichen, nicht gezeigt).
- Vorregistriert gemessen auf 70 STEP2-Belegen: LIVE_PROMPT_SUPPORTED, 55/70 exakt, „Regel behalten“ 25/30, 0 falsch. Alle Fehlschläge sind ehrliche UNKNOWN-Verweigerungen.

## Handy-Testliste
`v13/HANDY_TESTLISTE.md` im Projekt: 1. `bash WERKZEUG_TESTEN.sh` (ZIP export/V13-Werkzeug-Handy-20261020.zip), 2. RAM-Messung `scripts/ram_budget_bench.py`, 3. `bash TESTEN.sh --quick`, 4. STEP2 am Handy erst mit neuem Paket.

## Offen
Ganzen Live-Turn mit Werkzeug + Antworttext messen; dann Schalter + Werkzeug gemeinsam einschalten (Nutzerentscheidung); neues Handy-Paket; STEP2-Fixtures mit B1-eigener Information.



---

## QUELLE: THREAD_GEGENSEITIGE_PRUEFUNG_20261021.md

# Thread „Gegenseitige Prüfung mit GPT“ — 2026-10-21

Nutzerwunsch: Claude und GPT prüfen sich gegenseitig.

Git: Branch `claude/project-thread-g2f277` @ 58c5d1a, Draft-PR #8 (Basis `claude/project-thread-0zelvf`).
Projektordner: v13/PRUEFUNG_CLAUDE_FUER_GPT.md (volles Protokoll + Checkliste für GPT), AGENTS.md, UEBERGABE, ROADMAP aktualisiert.

## Runde 1: Claude prüft GPT bis a1973d4 (PR #2–#4)
- Laufzeitcode (listarith, toolstep, tools, transaction, broker, toolforecast): korrekt; Werkzeuge standardmäßig aus, nur mit Nutzer-Erlaubnis; Vorhersage bleibt SHADOW.
- Gate-Angaben ehrlich: canonical_gate_pass=false, phone_measured=false, FAILs bleiben FAIL. Urteilsname CONTINUAL_LEARNING_CONFIRMED (stammt von Claude M) klingt größer als gemessen -> immer mit „SHADOW, zwei Werkzeugwelten“ nennen.
- GPT hatte zwei echte Claude-Fehler gefunden (Vorzeichen im list_arith-Wächter; M-Analyse akzeptierte 4/21 Zeilen). Beide inzwischen drin.
- Privatsphäre: neues scripts/public_repo_privacy_scan.py, alle GPT-Branches CLEAN; „private“ STEP2-Fixtures sind synthetisch.
- PR #3: Code-Kandidaten in a1973d4 enthalten; 51 Review-Belege nur auf dem PR-#3-Branch.

## Behoben
- list_arith-Zahlen-Wächter zählt Vorkommen (doppelt gelesener Posten: 800 statt 500 lief durch).
- 19 Belegordner bench-results/*-20261012 fehlten im Git -> Suite auf frischem Checkout war 1 FAIL.

## Tests (v13/code, PYTHONPATH=.:tests python -m unittest discover -s tests)
- GPT a1973d4: 1439 OK, 5 Skips
- Basis cc527f0: 1582, 1 FAIL (fehlende Belege)
- nach Runde 1: 1585 OK, 5 Skips

## Offen
- GPT: Runde 2 (Claudes Arbeit prüfen), Checkliste Abschnitt 4 in PRUEFUNG_CLAUDE_FUER_GPT.md.
- list_arith: ausgelassener Posten wird nicht erkannt; „Total cost: 65“ zählt als Posten (braucht Messung).
- Nutzer: alte GPT-Draft-PRs #2–#4 schließen oder offen lassen.


---

## QUELLE: V13-Zielabgleich-20261021.md

Sicherung Thread „Ziele gegen Blueprint abgleichen“, 2026-10-21. Git: RedMentos/Aii Branch claude/project-thread-rxq188 @ 1c27c2a (v13/ZIELABGLEICH.md, ROADMAP.md §0 + WP-Z1..Z12, ABDECKUNG.md §12, NUTZER_ENTSCHEIDUNGEN.md offene Punkte). Projektordner: /v13/ZIELABGLEICH.md.

# V13 Zielabgleich: Blueprint v10.16.1 gegen ROADMAP/ABDECKUNG (2026-10-21)

## Kurzfassung
1. Die Roadmap ist seit dem 12.10. ein Arbeitsprotokoll und keine Zielliste mehr; ihr Kopf (Zielbild, Stand, Reihenfolge) war vom 09.10.
2. Die Blueprint-Ziele fehlten als Liste: §29 „V13 funktioniert“ (24 Eigenschaften) und §100 (10 Gates). Sechs der zehn §100-Gates kamen in ROADMAP/ABDECKUNG nie vor.
3. Stand nach Blueprint-Regeln: 0 von 10 §100-Gates grün (alle PARTIAL, measure_suite 21.10.); §29: 8 erreicht, 14 teilweise, 2 fehlen (Latent-Kanal-Nutzen, Message-Subspace-Austausch). Nach Blueprint-Wortlaut noch Harness-Prototyp.
4. „56 % ✅“ in ABDECKUNG = Code existiert, nicht Ziel erreicht. §24: nur 6 von 35 gemessen (24.11 durchgefallen), 25 nur Existenz-Test, 2 NEEDS_REDMI, 2 NOT_IMPLEMENTED.
5. Drift: R4 Teile 4–11 (Rechen-Werkzeug-Regeln), Action-JEPA Runden 1–9, Werkzeug-Vorhersage schließen kein §100-Gate. STEP2 (Komplementarität B1/B2) ist seit 09.10. offen.

## §96 STEP-Ausgänge
STEP0 ✅, STEP1 ✅, STEP2 ❌ (UTILITY_FAIL; gate-graph.json meldet trotzdem GREEN), STEP3 ✅, STEP4 🟡 (kein Referenz-Lehrer), STEP5 🟡 (TRAIN_RUNNER_PROOF Redmi fehlt), STEP6A ✅, STEP6B ❌ (B3 L1 FAIL), STEP6C 🟡 (keine Expert-Deltas), STEP7 ❌ (Redmi-Wochenlauf), STEP8–11 ⏸.

## §100 Gates (alle PARTIAL)
G-B-TIMESCALE-DIVERGENCE-001 → Z2; G-CALLOSUM-UTILITY-002 → Z4; G-FOCAL-CAPACITY-003 → Z5; G-PROCEDURALIZATION-004 → Z6/Z7; G-SELF-WORLD-005 → Z12; G-TRAIN-RUNNER-PROOF-001 → Z7; G-REPLAY-CONSOLIDATION-001 → Z9; G-MODULATOR-SPECIFICITY-001 → Z6; G-AGE-REOPEN-001 → Z8; G-MOBILE-LONGRUN-001 → Z7.

## Was nicht passte
a ROADMAP §1–§4 veraltet (jetzt historisch, neuer §0). b „R4 Teile 4–11“ sind Werkzeug-Regeln, nicht §31 R4. c Blueprint hat zwei R-Nummerierungen (§31 R0–R9, §79 R0–R6); Roadmap folgt §31. d Vision-Lab vor STEP7 (Blueprint: erst danach) – keine weitere Arbeit. e Action-JEPA/Werkzeug-Vorhersage ersetzen kein World-JEPA im Körper. f WP-AG (12 AGI-Lücken) ist Nutzerziel, nicht Blueprint. g ABDECKUNG-✅ widerspricht Gate-🟡 (Effort/G5B, Inquisition/G5, Koalition/G3D). h gate-graph STEP2 GREEN trotz FAIL.

## Neue Pakete WP-Z
Z1 Gate-Ehrlichkeit (STEP2_HARNESS vs STEP2_EXIT, §29-Tabelle in measure_suite). Z2 STEP2 neu mit B1-eigener Detail-Information + 4 Kontrollen. Z3 C3-Konsument isolieren (C3 vs B1 vs Werkzeug). Z4 B3 L1 Versuch 4 (läuft in anderem Thread). Z5 Fokus-Koalition gegen Voll-Kontext/Retrieval/feste Slots. Z6 §24 Gehirn-Mitte messen (24.22, 24.23, 24.17, 24.25, 24.26, 24.32). Z7 ein Redmi-Paket für alle Handy-Pflichtmessungen. Z8 Nutzerwahl Age-Plastizität. Z9 Dream-Kontrolle policy-only. Z10 MoE verdrahten + 24.19. Z11 Referenz-Lehrer STEP4. Z12 JEPA im Körper + echte Self/World-Fälle.
Start sofort: Z1, Z2, Z3, Z5. Seitenzweige nicht weiter ausbauen bis Z2–Z5 Ergebnisse haben.

## Offene Nutzerentscheidungen
1 age_plasticity_policy boot|stable_reopen|noise_aware (seit 10.10.). 2 offer_quote_context_chars=200 (seit 20.10.). 3 Redmi-Läufe (Z7).


---

## QUELLE: THREAD_B3_L1_DIAGNOSE_20261020.md

# Thread „B3 L1 Gate reparieren“ — 2026-10-20

Branch `claude/project-thread-0zelvf`, Commits dbd9df7 (Vorregistrierung), 8568949 (Diagnose + aux-Parameter), cc527f0 (aux-Lauf, Doku). Projektordner gespiegelt (v13/code, v13/bench-results/b3-l1-diagnose-20261020).

## Ergebnis
- L1-FAIL liegt NICHT an Bytes (64 B kosten nur 0,004 Nutzen mehr) und NICHT am Kanal: die 64-B-Nachricht trägt U/F (R² 0,88–0,94); mit U/F-Sonde gelesen ist sie so gut wie SCALAR (89/93/86 % vs 91/94/84 %, n.s.).
- Ursache: Brücke lernt nur aus ≤360 Aufgabenlabels, SYMBOLIC_ATTR/SCALAR bekommen privilegierte U/F-Labels. Eingefrorener NO_MESSAGE-Kopf kostet weitere ~2 Punkte. Mehr Aufgabenlabels (180→360) schließen die Lücke nicht.
- Fix-Kandidat: `Bridge(aux=A).fit(..., aux=...)` in v13/b3bridge.py (nur Trainingssignal; Empfängerpfad und 64 B unverändert; Default byte-identisch; Test mit Gradientenprüfung).
- Explorativ (gesehene Testitems): LATENT_AUX +5,5/+4,7/+9,8 Punkte; Gate PASS auf `action` (auch strikt vs SCALAR), escalate/apologize weiter FAIL gegen Attributwörter.
- Kein Canon-PASS: B3_LATENT bleibt unavailable, L2 gesperrt.

## Nächstes Paket
B3 L1 Versuch 4: vorregistriert, neue Datensaat (neue B1/B2-Zustände, Modelle wie Versuch 3), aux-Brücke, Gate unverändert, Rollen-Retention neu messen.

## Suite
1572 Tests, 5 Skips, 1 Fehler = vorbestehender test_neuro_ledger (fehlende bench-results im Git-Baum), auch ohne diese Änderung.


---

## QUELLE: THREAD_HANDY_PAKET_WERKZEUG_20261020.md

# Thread „Handy-Paket Werkzeug-Vorhersage“ (2026-10-20, Claude)

Paket 4 aus ROADMAP „Nächste offene Pakete“. Git: Branch `claude/project-thread-0zelvf`, Commits `5571a0b` (Paket) und `d341be2` (ROADMAP-Merge).

## Ergebnis
- Ein Befehl am Redmi: `bash WERKZEUG_TESTEN.sh [paritaet|kurz|voll]` (neu `code/WERKZEUG_TESTEN.sh`, `code/scripts/werkzeug_handy.py`, Tests `tests/test_werkzeug_handy.py` 9/9, Anleitung `code/WERKZEUG_ANLEITUNG.txt`).
- Ablauf: Vorprüfung (RAM >= 1,5 GB frei, Speicher, kein Chat), bei Bedarf `setup.sh` ohne Chat-Autostart, `termux-wake-lock`, GPTs begrenzter Treiber `tool_forecast_bounded_phone_candidate.py` mit Frist 2/4/10 h, RAM-/Akku-Temperatur-Verlauf alle 10 s, Ergebnis-ZIP `V13-Werkzeug-Ergebnis-<stufe>-<zeit>.zip` in Downloads (nur Berichte/Logs, KURZ.txt). Kein Plan/Gate geändert, Autorität 0, SHADOW.
- Fehler behoben: Handy-ZIP brach im Setup-Selbsttest ab (2 Belegdateien fehlten in `package_source.py` PHONE_REQUIRED_FIXTURES). Selbsttest im entpackten ZIP jetzt 1580 OK.
- Cloud-Probelauf aus entpacktem ZIP, frisches Home (Linux, 4 CPUs, KEIN Redmi): `voll` → LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED in 22 min; Parität PASS 45 s; Live 245/245, Median 1,47 s/Aufruf, Spitzen-RSS Tap-Prozess 1213 MB; Lernen 610 Aufrufe 14,8 min, Integrität PASS. Verhältnisse identisch zu 12./13.10.
- Handy-ZIP: Claude-Projektordner `export/V13-Werkzeug-Handy-20261020.zip` (12,2 MB, SHA f8fb5719…, 714 Dateien). Nicht auf Drive (Größe/Inline-Upload).
- Bekannt, nicht von diesem Thread: `test_neuro_ledger` scheitert im reinen Git-Baum (fehlender Belegordner `bench-results/homeo-meta-20261012`), Thread uvi2sq hat die Ordner auf seinem Branch nachgezogen.

## Offen (Nutzer)
Redmi: ZIP entpacken, `bash WERKZEUG_TESTEN.sh` (kurz, geschätzt 30–90 min), Ergebnis-ZIP hochladen; optional `voll` über Nacht. SHADOW → active erst danach.


---

## QUELLE: THREAD_STEP2_ENGPASS_20261020.md

# Thread „STEP2-Nutzen Engpass“ — 2026-10-20

Git: RedMentos/Aii Branch `claude/project-thread-dq33gk` (Basis `claude/project-thread-0zelvf`), Commits `3d9e767` (Code + Prereg, vor Inferenz) und `7109977` (Ergebnis, ROADMAP, Handoff).
Projektordner: v13/code (Code übernommen), v13/bench-results/step2-quote-context-20261020 (volle Reports), ROADMAP-Abschnitt gleichen Namens.

## Ursache
Qwen-B2 findet die frühere Projektregel, zitiert sie aber zerstückelt oder klein geschrieben. Die exakte Zitatprüfung verwirft das; volle Regel erreichte C3 nur in 7/30 „Regel behalten“-Offers.

## Änderung
`v13/cognition.quote_span`, Schalter `offer_quote_context_chars` (Standard 0 = aus = bisher). Bei 200: Zitat ist Zeiger auf ganze exakte Quellsätze (≤200 Zeichen derselben Quelle), transportiert wird nur exakter Quelltext. Kettenglied `integrated_candidates.quote_context`. Tests `tests/test_quote_context.py` 7/7.

## Native Messung (Linux, gleiche Modelle wie 13.10.), CONTEXT_SUPPORTED
- volle Regel an C3: 7/30 → 23/30
- mit Eignungs-Werkzeug, „Regel behalten“ B2-Varianten exakt: 11/30 → 24/30
- 0 falsch festgelegt; b2_only/both_none/both_control 10/10; Überschreibungen 16/16 in beiden Armen

## Unverändert
STEP2 UTILITY_FAIL (B1 ohne eigene Information; both_exact .842 < b2_only .917 mit Werkzeug). Ohne Werkzeug 0/70 exakt: C3 (350M) rechnet nicht. Kein Redmi/Kanon.

## Offen
1. Nutzerentscheidung: Schalter einschalten (offer_quote_context_chars=200 + b2_offer_body_state=false + offer_quote_min_chars=90).
2. Eignungs-Werkzeug in den Live-Antwortpfad (C5/READ_LOCAL).
3. Neue vorregistrierte STEP2-Fixtures mit B1-eigener Information.
4. Rest 7/30: B2 zitiert die frühere Regel gar nicht.


---

## QUELLE: THREAD_WP_G2_GIST_READOUT_20261020.md

# Thread „Nächste Pakete Abdeckung“ — WP-G2 nativer Gist-Readout-Konsument (2026-10-20)

Git: RedMentos/Aii Branch `claude/project-thread-uvi2sq` (Basis `claude/project-thread-0zelvf` @ 13acfc3), Commits 8036f62, 86a500f, d4336a6.
Projektordner: /mnt/project-files/v13 (Code, ROADMAP, ABDECKUNG, HANDOFF_CURRENT aktualisiert).

## Was gebaut wurde
- `code/v13/gist_readout.py`: konsumiert gespeicherten B2-Tap (Qwen3.5-0.8B Endnorm pro Token), bytegenaue Token→Zeichen-Bindung über native Pieces, Gruppierung ~8 Tokens (fixed|text|native|hybrid), 12 Slots, §3.2A-Felder, verlustfrei geprüft. `:tap B2_GIST` → `:gist readout [Modus]`. SHADOW, keine Rechte.
- Tests `tests/test_gist_readout.py` (11). Volle Suite 1582 OK / 5 Skips.
- 19 fehlende §102-Belegordner (`bench-results/*-20261012`, 444 KB) ins Git nachgezogen (Test test_neuro_ledger schlug sonst im Git-Baum fehl).

## Messung (nativ Linux, vorregistriert, Prereg vor Lauf gepusht)
- Runde 1 (160 Fragen): hybrid .594, text .563, nativ .563, fest .481, zufällig .355 → SUPPORTED.
- Explorativ: fest Größe 9 (gleiche Gruppenzahl) .544 → Teil-Effekt durch Gruppenzahl.
- Runde 2 (640 Fragen, Kontrolle gleiche Gruppenzahl): hybrid +.022 CI [-.016,.061] FAIL; text +.081 CI [.045,.114]; nativ -.005.
- Folge: Standardmodus `text`. Natives Sprungsignal liegt an Satzgrenzen (AUC .88), bringt aber keinen Zusatznutzen.

## Offen
Andere Tap-Schicht; gelernter Grenz-Kopf (neues Prereg); Antwort-Nutzen mit `:gist active`; native Firing-Diagnostik (anderer Teil von Paket 5) nicht angefasst. Redmi nicht gemessen.


---

## QUELLE: THREAD_STEP2_PILOT_20261020.md

# THREAD Privater STEP2-Pilot — 2026-10-20

Git: RedMentos/Aii Branch claude/project-thread-s7943o @ 5ae02fd (Registrierung vorab @ abc5dc4). Projektordner: v13/code/docs/proofs/continuation-20261016/step2-private-fixtures/pilot-run-20261020/

# Privater STEP2-Pilot — nativer Lauf 2026-10-20

**Status: gelaufen, 18/18 Zeilen abgedeckt, Kohorte `NOT_CONFIRMED` (1 Zeile ERROR), 0/18 exakt. Diagnostik, kein Gate. Historisches STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` unverändert.**

## Ablauf
1. GPTs read-only Auditor (Drive `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip`, alle 10 Manifest-Hashes geprüft) eingebunden: `audit_private_pilot.py`, `test_audit_private_pilot.py` (11/11 OK).
2. Original-Registrierung `pilot/native-registration.json` hier nicht ausführbar (bindet GPTs Gerät/Pfade); bleibt unverändert `REGISTERED_NOT_RUN`.
3. Neues Home aus dem gepinnten Katalog: B1/B2/C3-GGUF, Runner b10964 und alle 39 Bibliotheken byte-identisch zur Original-Registrierung.
4. Zweite Registrierung `native-registration-20261020.json` vor dem Lauf veröffentlicht (Commit abc5dc4), Quellen = exakt a1973d4.
5. Auditor-Preflight: PREPARED_NOT_RUN, 0 Fehler.
6. Lauf seriell 19:27–19:30 UTC, 188 s, Linux x86_64, 4 CPUs, Peak-RSS 1408 MB. report.json sha256 50ed2226…
7. Auditor nach Lauf: REFUSED nur wegen der einen ERROR-Zeile; sonst konsistent.

## Ergebnis
| Arm | RECORDED | exakt | Aktion richtig | Feld-Utility |
| --- | ---: | ---: | ---: | ---: |
| b1_model_quotes | 3/3 | 0 | 0 | 0.667 |
| b2_model_quotes | 3/3 | 0 | 0 | 0.639 |
| paired_model_quotes | 3/3 | 0 | 0 | 0.639 |
| same_policy_dual | 3/3 | 0 | 0 | 0.639 |
| no_message | 2/3 | 0 | 0 | 0.361 |
| exact_source_control | 3/3 | 0 | 0 | 0.667 |

## Befunde
- Flaschenhals ist C3 (LFM2.5-350M), nicht der Zitat-Transport: auch die Exakt-Quellen-Kontrolle liefert 0/3 exakt und immer action UNKNOWN; C3 rechnet remaining nicht.
- B1 zitiert seine Regel korrekt; mehr Zitate helfen C3 nicht.
- ERROR-Zeile bfzwzwww/no_message: B2 zitierte den öffentlichen Text unter seiner privaten SourceRef, Adapter lehnt korrekt ab (strenge registrierte Regel).
- project-Format ("Project X" statt "X") kostet 12 Felder.

## Nächster Schritt
Konsument isoliert testen (neue Registrierung): Exakt-Quellen-Kontrolle mit größerem Konsumenten (B1) oder deterministischem calc/eligibility-Tool vor C3.


---

## QUELLE: THREAD_GPT_UEBERNAHME_20261020.md

## GPT/Codex-Stand 13.–19.10. übernommen — ERLEDIGT 2026-10-20 (Thread „GPT-Stand erneut übernehmen“)
Git: Branch `claude/project-thread-0zelvf` (Draft-PR https://github.com/RedMentos/Aii/pull/5, baut auf GPT-PR #4 auf). Bitte künftig hier aufsetzen.

- Quelle: **GPT/Codex** Branch `codex/continuation-20261016` @ `a1973d4` (PR #4, 12 Commits seit `1941d07`, 16.10.), dazu Drive: `V13-Codex-Fortsetzung-20261016.md`, Native-Abend-ZIPs (geschlossen `V13-Native-Evening-0610-closed.zip`, SHA `0260f539…`), Preregistrierungen, und am 19.10. ein **nicht integrierter** Kandidat `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip` (read-only Auditor für den privaten STEP2-Pilot, 11/11 eigene Tests, kein Modelllauf; GPT konnte ihn nicht auf GitHub pushen, Branch `assistant/private-pilot-readonly-audit-20261019` = `a1973d4` ohne neuen Code). PR #3 (`codex/continuation-review-20261013`) war schon von M umgesetzt; seine restlichen Review-Kandidaten bleiben dort.
- Was GPT gebracht hat: K (list_arith) + M (calc/note/ToolForecast) zusammengeführt; enger Fix gegen Quellentausch während Outcome-Tap (`toolforecast.py`); Lernintegritäts-Gate gegen falschen PASS aus unvollständigen Zeilen, in die normalen Phone-Skripte integriert; Vorzeichen-Guard in `agi/listarith.py` (−5/Unicode-Minus wird nicht mehr als +5 akzeptiert); **native ToolForecast-v2-Lernkohorte 610/610 geschlossen** (Linux, SHADOW, Qwen-Taps): verschobene Zahlen calc MSE-Verhältnis .386–.707, Notizen .504–.666, feste Retention calc .982–1.002, Notizen 1.000, beide Lerngates PASS im engen Scope, unabhängig nachgerechnet. Erster abgebrochener Lauf bleibt UNKNOWN/negativ. Neuer Runtime/Store-Adapter für private STEP2-Quelle (28 Tests) und registrierter 18-Zeilen-Pilot — **noch nicht gelaufen**.
- Übernahme: 152 neue GPT-Dateien + 7 nur von GPT geänderte Dateien übernommen; `tools.py`, `broker.py`, `toolstep.py`, `transaction.py` behalten den Projektstand (hatte K+M bereits, plus WP-W2c `eligibility`-Tool, das GPT fehlte; GPT-Unterschiede dort nur Kommentare/Reihenfolge). Vorherige Fassungen in `archiv/vor-gpt-uebernahme-20261020/`. Kein Überschreiben, kein Force-Push.
- Prüfung: volle Suite (auch auf dem reinen Git-Tree) → **1571 Tests OK, 6 Skips**. Privatsphäre-Grep: nichts Privates.
- Unverändert offen/negativ: STEP2 original 70/70 UTILITY_FAIL, B3 L1 FAIL, Redmi-Messungen, Canon/Fullscope.

### Nächste offene Pakete (für sechs parallele Threads)
1. Privater STEP2-Pilot nativ ausführen (18 Zeilen/max 42 Aufrufe) + GPTs read-only Auditor vom 19.10. prüfen und binden.
2. B3 L1 / LATENT weiter (L1 FAIL, L2–L4 gesperrt).
3. STEP2-Nutzen: B2-Produzent/C3-Konsument-Flaschenhals, nächste Ablation auf Basis R4-Teile 5–8.
4. ToolForecast v2 → Gerät: Phone-Paket bauen, Neuinstallation + Redmi-Messung durch Nutzer.
5. Canon-Abdeckung: nächste offene WP aus ABDECKUNG.md (~56 %), Gist-Readout-Consumer, native Firing-Diagnostik.
6. Git-Konsolidierung: welcher Branch ist Hauptstand (PR #2/#3/#4/#5).



---

## QUELLE: Thread_N_Sicherung_2026-10-13.md

# V13 Thread „Nächste offene Pakete N“ – Sicherungsnotiz 2026-10-13

Repo: RedMentos/Aii, Branch `claude/project-thread-lmo0ri`, HEAD `434b19b` (Remote geprüft). Basis: Branch von Thread H (`claude/project-thread-3w32al`).
Gleicher Stand liegt im geteilten Projektordner `v13/code/` (Live-Kopie aller Threads).

| Paket | Commit | Inhalt |
|---|---|---|
| WP-N16 §97.2 | e60340b | Ressourcen-Modi GREEN/YELLOW/ORANGE/RED (`v13/resource_modes.py`), im Turn, Effort, Bodies, Sleep, Lern-Jobs |
| WP-N17 §22.2.4/§73 | 9a190fc | Observer-Scheduling-Regler (`v13/observer_schedule.py`), RSS-Budget als Modus-Eingang |
| WP-N18 G13 | c94eb00 | Langlauf-Soak `scripts/longrun_soak.py`; Fix: Wach-Replays verdrängten Nacht-Schlaf (`v13/sleep.py`) |
| WP-N19 B3-H10/H11 | f06696c | Degradations-Leiter + 10 Auslöser (`v13/b3degrade.py`), `:doctor`-Pflichtfelder |
| WP-N20 B3-H4/H5/H9 | bbedb57 | Empfänger-Kalibrierungspaket + hartes Tor (`v13/b3calibration.py`) |
| WP-N21 | bd356d3 | Körper-Größen aus RAM-Messung (`v13/body_sizes.py`, `specs/body-sizes.json`) |
| WP-N22 B3-H8 | ff214a0 | Trainingsreihenfolge erzwungen (`v13/b3order.py`) |
| – | 434b19b | `.gitignore` für Python-Caches |

Volle Suite 1333 OK / 4 Skips (Linux-Softwaretest, kein Redmi). Doku: `code/docs/RESOURCE_MODES.md`, `LONGRUN_SOAK.md`, `B3_DEGRADATION.md`.
Offen: Redmi-Messungen (WP-R): `:resources calibrate`, RAM-Bench von Thread P + `:resources bodies import <json>`, `longrun_soak.py --native`.
Keine privaten Daten im Repo geprüft (keine Tokens, E-Mails, Geräte-IDs).


