# V14 / INQUISITION-JEPA — Neuer vollständiger Systemplan

**Fassung:** 14.0-DRAFT, 19. November 2026
**Auftrag:** V13 vollständig und ohne stillen Funktionsverlust neu organisieren, durch spätere Entscheidungen, Research und legale Wiederverwendung verbessern und danach als echtes System implementieren.
**Geltungsbereich:** Gesamtes Projekt von A0 über B1/B2/B3, C/JEF, Memory, World, Self, JEPA, Sleep, Tools bis zur späteren kontrollierten Selbstoptimierung.
**Status:** Architektur- und Entwicklungsentwurf, ausdrücklich KEIN Nachweis, dass diese Funktionen bereits auf Android laufen.

Dieser Plan steht allein. Historische Originaltexte sind unter Teil III als Quellen vollständig enthalten, damit seltene Canon-Verträge und ältere Patches nicht beim Umschreiben verschwinden. V14 darf eine Implementierung ersetzen, nicht still eine gewünschte Funktion beseitigen. Ein Status wie LAB, SHADOW oder UNAVAILABLE bedeutet unfertig, nicht aus dem Endziel gestrichen.

# TEIL I — Architektur V14

## 1. Verbindliches Ziel, Konflikte und Entwicklungsstil

V14 soll ein lokal nutzbares, über viele Zeitskalen lernendes, heterogenes System mit mehreren spezialisierten neuronalen Organen werden. Es ist weder ein Prompt um ein einzelnes LLM noch bloß eine feste Regelmaschine. Lokale Wahrnehmung, Verarbeitung, vorsichtige Aktionen, Vorhersage, Fehlervergleich, Gedächtnis und Gewichtsänderung bilden einen wiederkehrenden Kreislauf. Das System lernt durch unterschiedliche Mechanismen: Fast Episodic, World/Self, Router, Prädiktoren, echte JEPA-Updates, spätere Body-Plastizität, Distillation, Replay und eigene Optimierung. Kein einzelnes Lernverfahren ist das ganze System.

Neue explizite Nutzerentscheidungen haben Vorrang gegenüber alten widersprechenden Zahlen oder einem veralteten Test-Setup. Der Funktionsumfang des V13-Canon ist ein Mindestumfang; seine etwaigen alten Modellnamen, Aufteilungen, Zahlen oder Testziele sind austauschbare Mittel. Zwei langfristig **verschiedene** sparse MoE-Körper, ein sehr kleiner Steuer-/Sprachteil, modellübergreifende eigene Repräsentationen, selbständiges Lernen und später kontrollierte Selbstprogrammierung gehören ausdrücklich zu den Zielen.

**Build-first und reuse-first:** Erst vorhandene Codebausteine inventarisieren, einen echten vertikalen Vollsystem-Pfad zusammenschalten und parallel unerledigte Organe ausbauen. Ein isolierter Endlosloop mit Test-Fixture-Fixes ist kein Fortschritt an V14 als Gesamtsystem. Bestehende OSS-Implementierungen unter nutzbaren Lizenzen haben Vorrang vor eigenem Duplikatcode; fehlende Integrationsadapter können selbst entwickelt werden. Tests dienen der funktionierenden Entwicklung. Sicherheits-, Rechts-, Lizenz- und Einwilligungsgrenzen bleiben immer aktiv und dürfen nicht durch neue Versionsnamen ausgehebelt werden.

**Ehrliche Statuswerte:** REQUIREMENT, CODE_PRESENT, CONNECTED, SHADOW, EXPERIMENTAL, UNAVAILABLE, LINUX_NATIVE, ANDROID_NATIVE, WEIGHTS_UPDATED, HELDOUT_UTILITY_PASS, REGRESSION_FAIL, APPROVED. „Fertig“ verlangt echten Consumer, Datenpfad, Persistenz wo nötig, Tests, Telemetrie, Rückfall und messbare Funktion; keine Fake-Latent-, Fake-Optimizer- oder UI-Schalter-Scheinfertigstellung.

## 2. Das vollständig integrierte Organmodell

~~~text
INPUTS / RAW OBSERVATIONS / USER / DIGITAL ACTION EVENTS
   |
 A0 source -> A1 events -> A2 frozen optional teacher
   |                 -> A3 student projector
   |                 -> A4 salience / re-look / prediction
   v
 A5 PerceptPacket + provenance
   |                 |                      |
 B1_DETAIL      B2_GIST             MEMORY / WORLD / SELF
 short-fine      long-coarse          fast + slow + prediction
   |                 |                      |
   +------ B3 callosum / Enlightened Space --+
                   |
           B4 WORKSPACE + C4 FOCAL
                   |
             C1 JEF / C2 CONTROL
                   |
             INQUISITION / checks
                   |
           C5 ACTION / C6 EGRESS
             |                  |
           TOOLS             C3 LANGUAGE
             |                  |
             +------- C7 OUTPUT ------->
                        |
               observed real outcome
                        |
          error + eligibility + modulation
                        |
       memory / JEPA / distillation / replay
                        |
        retention + self-optimisation trials
                        |
          back into all involved organs
~~~

Das ist keine starre lineare Pipeline. A, B, C, Memory, World und Self können über einen typisierten gemeinsamen Raum mehrfach miteinander kommunizieren und eigene Unsicherheiten/Teilziele melden. Es gibt keine einzelne allwissende Master-Instanz. Der gleiche Ort kann logisch parallel, auf einem kleinen Handy physisch sequenziell arbeiten. Jede Kommunikation hat eine SourceRef, Rolle, Zeit, Modellrevision, Quelle, Unsicherheit, Lebensdauer, zulässigen Empfänger und beobachtbaren Effekt.

### 2.1 A-Plane — Wahrnehmung, Ereignisse und Aufmerksamkeit

A0 nimmt Text, Dateien, lokale Tool-Resultate, die eigene Runtime und später Audio, Video, Bilder und Sensoren mit Einwilligung und Dateiquellen auf. A1 segmentiert nach echten Ereignissen, Satz-, Thema- und Zeitgrenzen mit verlustloser Rekonstruktion und überprüften Offsets. A2 ist ein optionaler eingefrorener Lehrer, nie grundsätzlich erforderlich oder wahrheitsautoritär. A3 ist ein kleiner trainierbarer Projektor/Student, dessen echter Nutzen und EMA-/Teacher-Bezug getestet wird. A4 verteilt Aufmerksamkeit anhand Salience, neuem Ziel, Unsicherheit, erwartetem Outcome und Ressourcen, nicht nur anhand Worttreffer. A5 veröffentlicht die zeitlich und inhaltlich gebundenen PerceptPackets. Wahrnehmung, Deutung, Vermutung und späteres tatsächliches Outcome sind getrennt.

Multimodale Eingaben verwenden den gleichen Ereignisvertrag, aber verschiedene Adapter. Audio/Visions-Modelle werden zuerst als Lab-Funktionen integriert und im realen Store nachgewiesen; keine stillen Netzaufrufe.

### 2.2 B1 und B2 — zwei echte verschiedene Körper

B1_DETAIL: kurze, detaillierte, fokale Verarbeitung, exakte Evidenz, konkrete Zwischenzustände und lokale Korrekturen. B2_GIST: längere Integrationsfenster, Generalisierung, globale Muster und gröbere zeitliche Modelle. Beide müssen eigenständige relevante Beiträge leisten. Ein identisches dichtes Modell mit zwei Rollennamen ist nur ein transparentes Age-0-Provisorium, kein erfülltes Split-Brain-Endziel.

Langfristig werden **zwei verschiedene sparse MoEs** mit eigenen Experten, Routing-/Shared-Pfaden, unabhängiger Lernkapazität, numerischen Gewichten und Gegenkopplung verwendet. B1 darf mehr aktive Detail-Experten, B2 eher komprimierende Gist-Experten nutzen. Auf 6-GB-Geräten sind Lazy Load, serialisierte Expert-Aktivierung und kleine Head-/Delta-Scopes möglich; das bedeutet keine Ausrede, die konzeptuell eigenständigen Hälften zu streichen. Gezählt werden aktive Parameter, KV/rekurrenter Zustand, PSS/RSS, TTFT, thermischer Verbrauch und tatsächliche Komplementarität.

### 2.3 B3, B4 und Enlightened Space — gemeinsames Denken ohne Text-Attrappe

B3 Callosum umfasst SOURCE_EXACT, CONTROL, SYMBOLIC, NO_MESSAGE und später echten trainierten LATENT-Transport. Realer Latent-Transport benötigt aus tatsächlichen Modellaktivierungen exportierte Sender-Repräsentationen, kleinen trainierten Projektor, Receiver-kompatible Einbindung und messbare Wirkung am Receiver; keine zufälligen Vektoren, nicht nur ineinander verschachtelter JSON-Text. B3 hat OOD-Gates, Replay, Ablationen, Modell-/Generation-Pinning und automatische Rückfallkanäle. Geringe Latent-Injection-Autorität im Labor ist nicht dasselbe wie die dauerhafte Absage an diese Funktion.

B4 Workspace stellt fokal ausgewählte globale Information bereit, nicht ein drittes Chatmodell. Enlightened Space ist der systemweite, typisierte Bus zwischen A, B, JEF/C, Memory, World, Self, Inquisition, Action, Outcome und Learning. Er bietet Multi-Timescale- und konkurrierende Hypothesen-Kanäle. Sender und Empfänger haben Rechte; ein global verfügbares Faktum ist noch kein wahrer externer Fakt.

### 2.4 C-Plane, JEF und Inquisition

C1/JEF koordiniert Budget, Fragen, Ziele und fokale Konkurrenz. C2 ist der kleine strukturierende neuronale Steuerteil, kann echte Vorhersagen und Routing-Lernen nutzen, besitzt aber **keine** exklusive Autorität über Sicherheit oder Quellenvertrauen. C3 ist ein kleines nativ ausführbares Sprachmodell, das die Ergebnisse verständlich und schnell ausgibt; Englisch als robuste frühe Baseline, Deutsch als separater späterer Transfer-/Lerntest. C4 Focal/Attention bestimmt selektive Re-entry-, Re-look- und Koalitionszyklen. Inquisition P1/P2 prüft Gegenargumente, Fehlerwahrscheinlichkeiten, Quellen und Definitionen; „Konsens“ ohne Kritik ist kein selbständiges Prüfen.

C5 wählt Antwort, Toolvorschlag, Speicher-/Lernhandlung oder Nichtaktion; C6 prüft Daten, Handlung, Consent, Provenance, Grenzen und Ausgabe; C7 liefert einen sichtbaren, abbrechbaren und wiederaufnehmbaren Bericht. Leichte Antworten bleiben schnell, komplexe können B-Organe / World / Inquisition nutzen. Die Rechenzeit und der native Prefill dürfen **nicht** durch den Age-Stand künstlich limitiert werden.

### 2.5 Memory, World, Self und Motivation

Fast Episodic speichert exakte Ereignisse, Korrekturen und source-linked Second-Attempt-Wissen. Semantic Memory ist ein später lernender Weltgraph mit Such-/Ähnlichkeitsrepräsentation, Beziehungen, zeitlicher Gültigkeit, Negativwissen und Widerruf. Relevante Erinnerungen werden von echten Consume-Pfaden gelesen; reine SQLite-Persistenz ist kein Lernen.

World Model sagt digitale und externe Zustände, Entwicklungen, Ereigniszeiten, Aktionsfolgen und Gegenbeispiele voraus. Self Model ist ein kleines eigenes trainierbares NN für Fähigkeiten, Fehler, Ungewissheit, Hardware- und Aufgabenbezug — getrennt vom Weltgraphen. Beide sind nicht allwissend. Anmutungen von Emotion/Neugier/Stress sind funktionale interne Modulatoren, keine behauptete menschliche Subjektivität.

Ziele haben Owner, Evidence, Permission, Expected Outcome, Timeout, Stop Condition, Widerruf und Scope. Nutzerziele haben nicht dieselbe Autorität wie selbst generierte Neugier. Unerledigte Ziele dürfen als Aufgaben weiterbestehen, aber nicht zwanghaft, endlos, unautorisiert oder ressourcenblind verfolgt werden.

### 2.6 Aufmerksamkeits-, Fehlervorhersage- und Omission-Lernen

Das Licht→Futter-Beispiel ist eine Intuition für ein lernendes **Zeit-/Erwartungsmodell**, nicht wortwörtliche Beschreibung aller Dopaminneuronen. Ein korrekt beobachteter Cue bleibt korrekt, auch wenn ein Folgeereignis nicht eintrifft. Daher werden getrennt gespeichert: Beobachtung des Cues; konditionale Outcome-Vorhersage; Zeitpunkt-/Hazard-Verteilung; Unsicherheit; tatsächliches Outcome; Nachweis, dass das Ausbleiben wirklich beobachtbar war; Lernfehler und Ergebnis.

~~~yaml
ExpectationRecord:
  condition_source: observed_source_ref
  predicted_outcome: typed_hypothesis
  earliest: observed_or_learned_time
  deadline: finite_time
  probability: calibrated
  status: PENDING | OBSERVED | OMITTED | DELAYED | DIFFERENT | CENSORED | CANCELLED
  owner: WORLD | SELF | ACTION | B1 | B2
  evidence: source_refs
  error: only_when_observable
  updates: bounded_eligibility_with_permissions
~~~

Bei Cue kann Aufmerksamkeit steigen und eine **offene Vorhersage** gespeichert werden. Bei pünktlicher Erfüllung wird kalibriert; bei belegtem Ausbleiben entsteht zum erwarteten Zeitpunkt ein negativer Vorhersagefehler; bei Verspätung ändert sich die Zeitverteilung; bei Beobachtungsdefizit bleibt UNCERTAIN/CENSORED und wird nichts als fehlender Reward „bewiesen“. Phasisches Reward-Prediction-Error-Verhalten in klassischer Biologie ist **kein** wörtlich unbegrenztes Neuronenfeuern. V14 vergleicht TD(λ), temporale Hazard-Modelle und JEPA-Zustandsvorhersage. Sicherheit: endliche Traces und aktive Stop-/Widerrufsbedingungen; kein Recht aus bloßem Überraschungssignal.

### 2.7 Alle Lernformen getrennt, aber kooperierend

1. Exaktes Episodic und Replay als schnelle Verhaltensanpassung ohne Weight-Update.
2. Router, C2, JEF, Wake/Confidence/Output-, Memory- und Tool-Köpfe mit echten kleinen Gewichten.
3. A3/percept Student und repräsentationsbasierte Verdichtung.
4. B1- und B2-JEPA, EMA-Targets und lokale trainierbare Adapter/Experten.
5. B3 trainierter Projektor/Readout mit echtem Receiver-Utility.
6. World- und Action-JEPA mit Zustands- und Folgeprädiktion.
7. Local Error × Eligibility × Modulation, typisierte Outcome-Feedbacks und Retention.
8. LoRA/Delta/selected Expert/Projector-Lernen mit numerisch vorhandenen Mastergewichten; ein GGUF ist nicht automatisch differenzierbar trainierbar.
9. C3-Ausgabe- und Skill-/Sprach-Updates.
10. Dream/Sleep/Rehearsal, getrennt von realen Quellen und Bewertungen.
11. Teacher- und Self-Distillation, selektiv und quellengebunden.
12. Meta-Learning über Folgen einer Update-Richtung und später kontrollierte organübergreifende Weight-Änderung.
13. Algorithmische Selbstoptimierung, Werkzeuge und langfristige Selbstprogrammierung.

JEPA ist ein Prediction-Loss mit Stop-Gradient/EMA als Zielstabilisierung. Echte trainierte Parameter brauchen eine brauchbare Optimierung, etwa Backpropagation für kleine LoRA-/Head-/Projektor-Slices; eine lokale Hebb-/Eligibility-Interpretation darf den Gradient ohne Nachweis nicht ersetzen.

### 2.8 NEU: selektive Mini-Distillation zur JEPA- und Gewicht-Update-Steuerung

**Status: Forschungs-Hypothese, nicht im Paper bereits bewiesenes JEPA-Modul.** On-policy Self-Distillation soll dort unterstützen, wo der Student das aktuelle Problem selbst erlebt, und ein konditionierter Lehrer eine relevante Abweichung kennt. Speculative Self-Distillation kann Teacher-Abfragen selektiv an großen lokalen Divergenzen ansetzen. Eine dritte kleine Vorhersageeinheit soll zusätzlich die **Folgen eines beabsichtigten Updates** einschätzen.

- Live Student: aktuelle Sprach-/Welt-/Body-Vorhersage ohne privilegierten Ausgang.
- Teacher: eingefrorene oder langsame Kopie, derselbe Body mit menschlich/World-verifiziertem Kontext, oder ein separat rechtlich freigegebenes Modell.
- JEPA Predictor: latente zukünftige Repräsentation; das Grundlernziel bleibt.
- Mini Distillation Head: Soft-Targets/Teacher-Student-Divergenz, nur bei relevanten und rechtlich sauberen Fällen.
- Meta Update Predictor: schätzt erwartete neue Utility, Alt-Fähigkeitsverlust, Unsicherheit, Kosten und geeignete trainierbare Parametergruppen.
- Evaluator / Inquisition: prüft Gradienten, Source, Heldout, OOD und Rollback unabhängig.

~~~text
L = a * L_JEPA(student_predictor, stop_gradient(EMA_target))
  + b * L_selective_distillation(student, privileged_teacher)
  + c * L_observed_outcome_and_omission
  + d * L_retention_anchor
  + e * L_collapse_and_OOD
~~~

Koeffizienten werden nicht automatisch als optimal behauptet. Der Meta-Head **schlägt** vor, wo und wie ein echter Gradient trainierbare Parameter ändern könnte, autorisiert nicht den Trainingsmodus. Ein Kandidat wird isoliert trainiert und auf neuem/nichtleakendem Holdout, Langzeit-Retention, negative controls, Lernbudget und Reversibilität verglichen.

Zwingende Ablation: (a) JEPA allein; (b) Distillation allein; (c) JEPA+Distillation; (d) JEPA+Distillation+Meta-Head; jeweils gleiche Daten, Commit-Revisionsbindung und Budget. Falls d keine Vorteile bringt, kann die Methode verworfen werden, **ohne** JEPA oder andere Lernpfade zu löschen. Bei späterer echter Cross-Organ-Lernsteuerung werden Parameter-/Rechte-Grenzen, Eligibility, Quellen und unabhängige Safety-Pfade zusätzlich erzwungen.

### 2.9 Sleep, Dream, Wiederholung und Konsolidierung

Sleep hat unterscheidbare Phasen: überprüfte Rehearsal-Samples, episodische Konsolidierung, semantische Graph-Zusammenführung, Slow Target/EMA, vorsichtige Offline-/Counterfactual-Dream-Experimente, Retentionsprüfung und Cleanup. Die Startquelle und der Traum bleiben unterscheidbar. Mehrfaches Auftreten eines Verhaltens kann als Konsolidationsindikator dienen, aber nicht als unabhängiger Beweis für Wahrheit. Erlernte Modelle bekommen kein Autoritätsrecht durch automatisch erzeugte Daten. Kein Nutzerturn nötig für ausdrücklich autorisierten, ressourcenbegrenzten lokalen Idle-Lernpfad.

### 2.10 Age, Rechte und kontrollierte Selbstprogrammierung

Drei **unabhängige** Dimensionen: (1) official_age — tatsächlich belegte Reife, anfangs 0; (2) lab_age — frei einstellbare experimentelle Test-/Entwicklungs-/Tool-/Lernfunktionen bis X10, ohne official_age zu ändern; (3) runtime_resources — physische Speicher-, Rechen-, Thermik-, Token- und Antwortzeitgrenzen, niemals aus „Age“ abgeleitet. Lernstufen RECORD_ONLY, SHADOW_UPDATE, APPROVED_COMMIT und Self-Edit-Proposal/Test/Approved-Deploy bleiben technisch getrennt.

Langfristige Vision: Das System schreibt unter realer Fehler- und Nutzenkontrolle Teile seines eigenen Programms um, später ganze Organe und irgendwann potentiell jede ursprünglich fremd geschriebene Zeile. Es geht nicht nur um kleine Konfigurations-/Promptänderungen. Ein selbstproduzierter Codevorschlag besitzt jedoch **kein** Recht, Sicherheits- und Einwilligungsmechanismen eigenständig außer Kraft zu setzen.

Self-Edit-Zyklus: Problembeobachtung → Literatur/OSS+Lizenzsuche → unterscheidbare Hypothesen → isoliertes Source-/Weight-Diff → menschlich verständliche Erklärung jedes Tests und seiner Grenzen → automatischer Sandbox-/Adversarial-/Regressionstest → Kosten/Nutzen-/Retention-Vergleich → berechtigte Freigabe → atomischer Rollout und beweisbarer Rollback. Keine automatische Selbsterteilung von Root-/Netz-/Trainer-/Release-Rechten.

### 2.11 Android/Termux und schnelle tatsächliche Benutzbarkeit

Baseline: Redmi Note 10 Pro, Android 13, aarch64, 6-GB-Klasse. Übergangsmodelle B1/B2 LFM2.5-1.2B Q4, C3 LFM2.5-230M Q4 und kleines C2 — nicht als endgültige zwei sparse MoE ausgeben. Langfristiger Modell- und Hardwareaustausch über stabile BodyPort-/Runner-Schemas und überprüfte Generationen.

Terminal: ein verständlicher Setup-/Startbefehl, Echtzeitstatus, Autostart/Update mit zutreffendem UI, Cancel/Pause/Resume, private persistente History und Graph, Toolgenehmigungen, Test-Age und offizieller Age separat, komplette Logs ohne öffentliche Geheimnisse. Browserbuttons müssen ohne Reload tatsächlich funktionieren. Offline-Fallback und Rollback während Update-Ausfall.

Leichte „Hi“/offensichtliche Fragen werden durch Fastpath / C3 / kleine Heads beantwortet, ohne schwere B1-/B2-Modelle unnötig abzuarbeiten. Relevantere Anfragen aktivieren die tatsächlich nötigen Organe und können asynchron weitere Evidenz liefern. Messen: prompt→TTFT, C3 native input/output tokens, B1/B2-Angebote, Timeout/PSS/RSS, Prewarm, Cache-/rekurrenter Zustand, Stack-Latenz, Wärmelast und Crash-Wiederaufnahme. Kein Linux-Test ersetzt reale Redmi-Messung. Keine falschen Garantien aus GGUF-Dateigröße.

### 2.12 Sicherheits- und Ethikvertrag

Security und Privatsphäre sind funktionale **Systemanforderungen**, nicht spätere Zusatz-Patches. Lokale Daten bleiben lokal; externe Teacher, synchronisierte Daten, persönliche Gerätemessungen und private Chats erfordern informierte Nutzerfreigabe. Öffentliche GitHub-Repos bekommen nur öffentliche Source-/Testtexte, keine Tokens/Transkripte/Geräte-IDs. Sorgfältig unterscheiden: private Gedanken/Fiktion, Texte, Toolvorschläge, externe Aktionen, tatsächlich zu erwartenden Schaden. Bei Ablehnungen nachvollziehbarer Grund. Kein versteckter Autonomie-/Gewichts-/Code-/Rechteaufstieg.

Für jede Aktion gibt es Owner, ein prüfbares Source-/Berechtigungs-/Zeit-Scope, Stop/Cancel, Report, Undo/Fail-Closed. Quelle, Fakt, Modell-Hypothese, Beobachtung, selbst generierte Erinnerung und Interpretation sind eigene Vertrauensstufen. Keine Selbsttrainings-Feedbackschleife darf Sicherheitsautorität erzeugen. Datensätze, Modelle, Tools und kopierter Code sind lizenz- und datenschutzrechtlich separat zu prüfen.

### 2.13 Bewiesener Stand statt kosmetischer Erfolgszähler

Ein Feature ist nur implementiert, wenn CODE, REAL_PATH, CONSUMER, PERSISTENCE/RESTART, TEST, TELEMETRY vorliegen. Lernende Parameter brauchen echte Gradienten/Optimizer/Master-Gewichte oder alternative mathematisch getestete Lernmethode, Diff/Checkpoint, unabhängige Retention- und Nutzenprüfung und Rollback. Für mobile Funktionen zählt zusätzlich real gemessene Android-Inferenz/Trainingsfähigkeit.

Wichtige negative Fakten dürfen nicht still verschwinden: B3 L1 hat nicht den nötigen latenten Receiver-Nutzen bewiesen; ursprüngliche STEP2-Komplementarität war nicht ausreichend; auf Redmi wurden B1-/C3-Timeoute beobachtet. Neue CI-Greens sind nur CI-Status, kein Ersatz für live funktionierende Antworten. Alte FAILs bleiben offen bis zur konkreten erfolgreichen Wiederholung.

### 2.14 Vollständigkeitskonzept

**Das ursprüngliche Canon bleibt verbindlicher unterer Funktionskatalog**, mit allen IH-H, H-, G-, F-, STEP-, A/B/C- und Forschungs-/Ablationsvorgaben. Keine seltene Detailfunktion wird allein wegen der neuen Gliederung gestrichen. Im vollständig angehängten Alttext sind Original-Spezifikation, Nummern und Kontext reproduzierbar. V14s Fortschritts-Ledger muss jeden alten Abschnitt und jedes spätere WP einer neuen Komponente, einem Consumer, einem Szenario und einer Status-Evidenz zuweisen. Alte unklare A/B-Bezeichnungen werden historisch interpretiert, nicht falsch umgekehrt.

Zusätzlich ausdrücklich erfasst: alte Datenmix- und Kollapswächter, veraltete Decoder-Startwerte nur als Versuch, Repair von Body-Training-Port / native Capabilities, Lost burst3–5, zwei verschiedene MoE-Hälften, Englisch→Deutsch-Lerntest, geclearte Long-Context/SourceRefs, Meta CLM, Typ-/Zeit-/Rights-Trennung, Device-Speed, numerische JEPA-Veränderung, Eignungs-Ablationen, Vision/Audio/TTS, echte autonomere Tool- und Self-Edit-Ziele.

---

# TEIL II — Research, Codeübernahme, Lizenzen, Arbeitsablauf

## 15. Wissenschaftliche Grundlage des neuen Vorschlags

**Self-Distillation Enables Continual Learning**, Shenfeld, Damani, Hübotter, Agrawal, publiziert ICML 2026; arXiv 2601.19897 vom Januar 2026. Konditioniertes Selbst-Lehrmodell gibt dem aktuellen Student auf dessen eigener Trajektorie Targets. Weniger katastrophisches Vergessen als in den verglichenen SFT-Baselines; keine Aussage, alle kleinen Mobile-Modelle könnten damit beliebig lernen. Primär: https://proceedings.mlr.press/v306/shenfeld26a.html .

**Speculative Self-Distillation enables Efficient Knowledge Internalization**, Talaei et al., erstmals 9. November 2026, arXiv 2611.12016. Schüler schreibt standardmäßig selbst; Lehrer greift selektiv bei erheblicher Abweichung ein. Das ist besonders nah an der Idee „Mini-Distillation an relevanten Stellen statt pauschalem Lehrer“. Autorenimplementierung benutzt GPU/vLLM-Konfiguration; ein Android-Gewinn ist offen. Primär: https://arxiv.org/abs/2611.12016 ; https://ssd-distill.github.io/ .

**iSDFT**, arXiv 2609.24646, kontrolliert den Informationsabstand bei Self-Distillation; **Learning without Overwriting**, arXiv 2610.05200, beschreibt theoretische Zusammenhänge von On-Policy-Signalen, Sparsity und Forgetting. Diese Richtungen ergänzen, nicht ersetzen, das ganze V14-Lernsystem.

**Reward prediction / Omission:** Schultz-/Hollerman-Dopaminbefunde zeigen frühe Reward-Reaktion, später Reaktion auf den konditionierenden Cue und ein negatives Signal **am erwarteten Zeitpunkt** ausgelassener Belohnung. Die von dir beschriebene Idee wird als eigenständiger zeitlicher Erwartungs-/Outcome-/Fehlerkreis abstrahiert, nicht als wörtlich dauerfeuerndes Neuron. Primär u. a. https://journals.physiology.org/doi/full/10.1152/jn.1998.80.1.1 .

**Neuer und unbewiesener Vorschlag:** ein Meta-Head könnte durch Self-Distillation und JEPA aus beobachteten Updatefolgen abschätzen, welche Update-Richtungen wahrscheinlich nützen. Das wird gerade *nicht* als etablierter Paper-Befund ausgegeben, sondern als testbares zusätzliches Organ.

Der Nutzerlink https://youtu.be/XgVm8Nxz68Q bleibt als konkrete Recherche-Referenz enthalten. Titel/Video-Transkript ließen sich nicht unabhängig verifizieren; ihm wird keine erfundene spezifische Aussage zugeschrieben.

## 16. OSS-Entscheidungsmatrix / Lizenzstatus (geprüft am 19.11.2026)

| Projekt | Lizenz aus Repository | Rolle in V14 | Entscheidung |
| --- | --- | --- | --- |
| https://github.com/ggml-org/llama.cpp | MIT | GGUF/nativer Inferenz-/Stream-/Cache-Runner | Vorhandene Integration verbessern und benchmarken statt eigenes LLM-Backend schreiben |
| https://github.com/Cactus-Compute/cactus | Apache-2.0 | kleiner mobiler KI-/Controller-Backend-Kandidat | Native C2/Tool/Audio-Profil und ABI gegen existierenden Needle-Runtime-Stand testen |
| https://github.com/pytorch/executorch | BSD | mobile kleine Projector-/NN-Export-Inferenz | Nur nach Export- und tatsächlichem Android-ABI-Test; kein automatisch trainierbares GGUF |
| https://github.com/online-ml/river | BSD-3-Clause | online Lernen/Drift/Evaluationsalgorithmen | Kandidat für leichte Heads; Termux-Build und C-Abhängigkeiten prüfen |
| https://github.com/ContinualAI/avalanche | MIT | continual-learning Ablations-/Forgetting-Bench | Offline-Lab; PyTorch-Schwere nicht aufs Handy übertragen |
| https://github.com/facebookresearch/vjepa2 | MIT für Repository-Quellcode | JEPA/EMA/Prediction-Architektur | Referenz, nicht direkt mobiles Video-Modell; Drittdateien/Gewichte separat |
| https://github.com/ShayanTalaei/SpeculativeSelfDistillation | Apache-2.0 | neues SSD/Teacher-Interventionsprinzip | Backend/paired-vLLM nicht unverändert auf 6-GB-Handy kopieren |
| https://github.com/idanshen/Self-Distillation | KEINE LICENSE im Repository-Root gefunden | SDFT-Wissenschaft, Experimentablauf | Kein Kopieren des Codes ohne Rechteklärung; saubere eigene Reimplementierung möglich |
| https://github.com/tinygrad/tinygrad | MIT | einfacher kleiner trainierbarer Tensor-Engine-Kandidat | Erst tatsächlichen ARM/Termux-Backend- und Gradienten-Lauf prüfen |
| Projektbestand https://github.com/RedMentos/Aii | vorhandene Eigentums-/Dritt-Herkünfte prüfen | Organe, Runtime, Memory, JEPA, Sleep, Tools | Zuerst Konsumenten integrieren, keinen dritten Dummy-Runtime bauen |

**Lizenzverfahren:** für jedes tatsächlich importierte Fremdteil exakten Upstream-Commit, Quelle/Autor, SPDX, LICENSE und NOTICE, veränderte Dateien, Patent-/Transitiv- und Distributionseinschränkungen, Modellkarten/Weight-Rechte, Datensatzrechte, Updatepfad dokumentieren. MIT/BSD/Apache erleichtern Nutzung, aber machen Lizenzen **nicht egal**. GPL und nichtkommerzielle/unklare Gewichte erfordern gesonderte Entscheidung oder anderen Code. Der reine Paper-Gedanke kann ohne Quellcode-Kopie eigenständig umgesetzt werden; Urheberrechte an konkreten Implementierungen gelten weiter.

## 17. Was übernehmen, inspirieren oder neu bauen?

- **Übernehmen nach Lizenz-/ABI-Test:** bewährte native LLM-Inferenz, kleine Online-Lern-/Optimizer-Bausteine, Graph-/SQLite-/Transaktions-/Streaming-/Profiling-Techniken und seriöse Regressionswerkzeuge. Zuerst vorhandene V13-Module wiederverwenden.
- **Nur Ideen/Benchmarks:** GPU-schwere Distillation-Trainingsframeworks, große Video-JEPA-Backbones, unklare Model-Werk-Lizenzen, nicht kommerziell verfügbare oder gated MoE-Weights. Kein unbelegter Android-Anspruch.
- **V14-spezifische Integration:** systemweiter aktiver Organ-Bus, eindeutige Source-/Time-Contracts, echte unterschiedliche B1/B2, konsistenter World/Self-Speicher, trainierbarer B3-Receiver, verlustarme Omission-/Delayed-Outcome-Schicht, JEPA↔Distillation-Meta-Gating, Tool-Lifecycle, Self-Edit-Review, rights-/age-aware Console und full-run Redmi-Bench.
- **No-Copy:** V13-private Telemetrie, Work-Cloud-Zugänge und persönliche Chats niemals in öffentliches Repo. Die 418-MB-Drive-Historie bleibt private Quelle; projektbezogene schriftliche Drive-Roadmaps können nach Geheimnisprüfung eingebunden werden.

## 18. Arbeitsreihenfolge als zusammenhängende Entwicklung (keine künstlichen Stop-Gates)

**Phase A — Gesamtbild funktionsfähig verbinden:** ein reales V14-Entry und bestehender source-bound Store, A0–A5/B1/B2/B3/C1–C7, World/Self/Memory/Enlightened in einer einzigen ausführbaren Turn- und Outcome-Schleife; für untrainierte Teile sichtbarer Lab-/Fallback-Status statt getarnter Fake-Latents. Benutzerantwort und Termux-Bedienung sind zuerst tatsächlich nutzbar. Parallel führen A-, B-, C-, Memory- und Android-Teams ihre eigenen organübergreifenden Integrationstests durch.

**Phase B — Lernkreisläufe aktiv:** echte Event→Outcome- und Pending-/Omission-Records, trainierbare kleine Router/World-/A3-/C2-/Head-Pfade, B1/B2-JEPA mit echter Gradienten-/Master-/EMA-Schicht, persistente Checkpoints und Holdout. Parallel wird B3 mit tatsächlichen Hidden-State-/Receiver-Tests statt nur textuellen MessagePackets ergänzt.

**Phase C — zwei echte MoE-Körper und selektive Distillation:** verfügbare passende Sparse-Modelle recherchieren, rechtlich und speichertechnisch prüfen, in BodyPorts integrieren. Lehr-/Distillationsfälle einzeln mit Realgrößen/Latency/Retentionsvergleichen messen. Meta-Update-Head nicht für alle Gewichte auf einmal freischalten. Native Training auf ARM nach echtem Nachweis, sonst offline/training-runner mit lokal aktiver, rücksetzbarer Wirkung.

**Phase D — Rückkopplung und fortlaufende Selbstoptimierung:** Sleep/Replay/Consolidation, selbstinitiiert erlaubte lokale Forschungsarbeit, Vorschläge anderer Algorithmen, eigene Code-Diffs, verständliche unabhängige Tests, menschliche Genehmigungen, Rollbacks. Über viele Generationen dürfen alle alten Organe neu geschrieben werden; übergeordnete Safety/Permissions/Privacy-Verträge bleiben durchsetzend.

**Parallelität:** Architect/Integrator, A/Perception, B/MoE, B3/Latent, C/JEF, Memory/JEPA/Distillation, Android/QA, Security/Legal, Research/Open-Source, Boss/Independent Review. Jeder hat getrennte Dateibereiche und ein messbares **funktionales** Slice. Kein gegenseitiges Überschreiben, kein Force-Push. Nach max. zwei gleichartigen erfolglosen Debug-Runden Ursachenforschung durch Upstream-/Code-Reuse und Wechsel auf ein anderes großes offenes Systemziel statt weitere Nischen-Fixtures. Integrieren in funktionalen Batches, dann Nachprüfen/Verbessern.

**Monat-/Wochentakt ist kein Fertigkriterium.** Fortschritt wird durch reale vollständige Pfade und Nutzwert bewertet: „Hi“ in vertretbarer Echtzeit, B1/B2 unabhängige Angebote, C3 Native Tokens, echtes Erinnern beim zweiten Versuch, JEPA Gradient/Checkpoint, B3 Receiver-Effekt, Tool-Vorschlag/Freigabe/Ergebnis, Reboot/Update und experimentelles Meta-Lernen.

## 19. Messverträge und klares Reporting

Ein Agentenbericht muss sagen: (1) welcher echte End-to-End-Consumer neu läuft; (2) Code- und Model-/Lizenzrevision; (3) welchen V14-/Canon-Abschnitt das abdeckt; (4) echte Linux-/Redmi-/Trainings-/Holdout-Beweise; (5) welche Funktion noch fehlt; (6) den nächstgrößeren Integrationsschritt. PR-Zahlen, Commits und CI-Screenshots ohne Funktionspfad sind Sekundärdaten. Ehrliche negative Kontrollen sind wertvoll; sie dürfen aber die Implementierung aller anderen Organe nicht anhalten.

Testarme: JEPA vs SDFT vs SSD vs JEPA+SSD+Meta; zwei MoE statt identischem Dense; Memory Consumer vs ohne; mit/ohne Pending-/Omission-Time; latent/exact/no-message; English→German; Reset/Crash/Revocation; explizit erlaubte vs verbotene Tools; offene Welt vs verifizierte Quellen; dauerhafte Retention und Rückfall.

## 20. Fortbestehende Pflichten aus V13

Die vollständigen alten Canon-/Roadmap- und Drive-Sichtungstexte werden unten **verbatim** archiviert. Keine einzelnen IH-H-, B3-H-, G-, F-, A/B/C-, WP-, STEP-, State-/Contract-/Ablationspflichten werden aus der V14-Soll-Liste entfernt. Historische widersprüchliche Modi und neuere Nutzerentscheidungen sind über die Provenienz auditierbar, nicht still umgedeutet. Für eine vollständig neue operative Fassung werden die obigen Abschnitte benutzt; für seltene Einzelverträge gilt der jeweilige unverändert beigefügte Nachweis bis ein ausdrücklich dokumentierter kompatibler Ersatz vorliegt.

---

# TEIL III — vollständige historische Quelltexte

Die folgenden Teile werden aus der bestehenden öffentlichen V13-Repo-Quellrevision und den drei projektbezogenen Drive-Roadmaps mit Revisions-/Dateiherkunft unverändert angefügt. Ein Originalnachtrag bleibt sichtbar, auch wenn sein technischer Vorschlag inzwischen veraltet ist. Roh-Chats und das private 418-MB-ZIP werden aus Datenschutzgründen nicht öffentlich reproduziert.
