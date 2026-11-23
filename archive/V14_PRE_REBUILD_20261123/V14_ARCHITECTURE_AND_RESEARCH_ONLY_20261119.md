# V14 / INQUISITION-JEPA — Neuer vollständiger Systemplan

**Fassung:** 14.1-LIVE, 20. November 2026 (vollständige Erstrevision 14.0 vom 19.11. historisch gesichert)
**Auftrag:** V13 vollständig und ohne stillen Funktionsverlust neu organisieren, durch spätere Entscheidungen, Research und legale Wiederverwendung verbessern und danach als echtes System implementieren.
**Geltungsbereich:** Gesamtes Projekt von A0 über B1/B2/B3, C/JEF, Memory, World, Self, JEPA, Sleep, Tools bis zur späteren kontrollierten Selbstoptimierung.
**Status:** Architektur- und Entwicklungsentwurf, ausdrücklich KEIN Nachweis, dass diese Funktionen bereits auf Android laufen.

Dieser Plan steht allein. Historische Originaltexte sind unter Teil III als Quellen vollständig enthalten, damit seltene Canon-Verträge und ältere Patches nicht beim Umschreiben verschwinden. V14 darf eine Implementierung ersetzen, nicht still eine gewünschte Funktion beseitigen. Ein Status wie LAB, SHADOW oder UNAVAILABLE bedeutet unfertig, nicht aus dem Endziel gestrichen.

# TEIL I — Architektur V14

## 1. Verbindliches Ziel, Konflikte und Entwicklungsstil

V14 ist die vollständig erhaltene und weiterentwickelte **V13/Inquisition-JEPA-Gesamtarchitektur**. Der gesamte ursprüngliche Funktionskatalog, seine individuellen IH-H-, F-, H-, G-, A/B/C-, B1–B6-, STEP-, WP- und Trainings-/Sicherheitsverträge sowie alle zusätzlichen dokumentierten Nutzerentscheidungen bleiben Anforderungen. Weder die neue Gliederung noch der Austausch einer Implementierung dürfen sie lautlos entfernen. **Das Systemziel ist ein Gehirn-ähnlich verteiltes, kontinuierlich lernendes, handlungsfähiges Gesamtnetz**, kein einzelnes LLM mit angehängten Dummy-„Agenten“.

**Nutzerkorrektur 20.11.2026 – verteilte Integration:** Mit der Formulierung, das „Bewusstsein lebt überall“, ist die angestrebte systemweit verteilte Verarbeitung und Integration gemeint: viele voneinander abhängige, wiederkehrende neuronale Zustände und Teilaktivitäten, aus denen ein kohärentes Handeln entsteht. Die Architektur darf **weder JEF noch C3 noch B4** zum einzigen Ort von Denken, Selbstbild oder einer angeblichen Bewusstseinsinstanz machen. Sie behauptet nicht, damit menschliches subjektives Bewusstsein wissenschaftlich nachgewiesen zu haben.

**Topologie ist ein Graph, keine Taktstraße.** Ereignisse können mehrere Organe gleichzeitig aktivieren; Rückkopplung, Konkurrenz, Umleitung, direkte Kollaboration, ereignisbasierte Reentry-Schleifen, dynamische Zuteilung von Aufmerksamkeit und Lernen sind normale Vorgänge. Der kürzeste verlässliche Pfad darf benutzt werden. Eine ARM-Runtime darf GPU/RAM-bedingt Ausführung serialisieren, ohne die *logische* Anatomie linear auf A→B→C festzunageln. Es gibt keinen generellen Zwang, erst isolierte Organe ihre Text-„Meldungen“ abgeben zu lassen.

**Latenter Austausch ist die präferierte Endform** der neuronalen Kommunikation. Mit „Enlightened Space“ ist eine echte lernbare, temporale und modellübergreifende **latente Kopplung** gemeint: aktivierungsbasierte Repräsentationen, Projektions-/Kompatibilitätslernen, direkte Receiver-Einwirkung und verteilte Integration. Ein getypter Text-/JSON-/SQLite-Bus kann den Betrieb und die Nachvollziehbarkeit unterstützen, ist aber *nicht selbst* der gewünschte Latent Space. Hypothesen, Assoziationen und Ungewissheiten müssen möglichst ohne erzwungene Sprachübersetzung verfügbar sein. Vorhandene Text-Fallbacks bleiben ehrliche Zwischenlösungen.

**Allgemeines Ziel: lernfähige Organe, keine dauerhaft stillgelegten neuronalen Kerne.** Alle dazu vorgesehenen Modelle und Unterteile sollen auf eigenen Zeitskalen weiterlernen und sich verändern können. EMA-/Slow-Targets, reversible Stabilisierungsphasen, Momentaufnahmen für Regression und vorläufige technische Hilfsmodelle sind mögliche *Methoden*, keine endgültig unbeweglichen Teacher-Organe. Teacher/Student sind kontextabhängige Funktionen, die auch wechseln oder entfallen dürfen. Die spätere Selbstoptimierung schließt Algorithmen, Verbindungen, Parameter und kontrollierte Umgestaltung des eigenen Codes ein.

**Build-first, reuse-first, audit-first:** Vor neuen Duplikatimplementierungen vorhandenen V13-Code, offene PRs, gepflegte OSS-/Paper-Quellen und Lizenzstatus untersuchen. Einen echten verbundenen End-to-End-Betrieb herstellen und gleichzeitig die großen fehlenden Organe in parallelen Sparten fertigstellen. Nicht wochenlang nur Mikro-Fixtures oder künstliche Erfolgszahlen pflegen. Keine Architektur wegen eines kurzfristigen Mobil- oder Testproblems verkleinern. User-Rechte, Einwilligung, Privatsphäre, Gefahrengrenzen und reproduzierbare Rollbacks bleiben bindend.

**Lebende Source of Truth:** Der vorliegende **V14-Master wird selbst aktiv fortgeschrieben**. `v14/V14_LIVE_WORKPLAN.md` hält operative Prioritäten und `v14/V14_RESEARCH_LEDGER.md` aktuelle Forschung fest. Vor jeder materiellen Canon-Änderung eine **separate unveränderliche Sicherung** und einen überprüfbaren Commit herstellen. Der komplette unveränderte V13-Text im Teil III wird nicht durch eine neue Zusammenfassung ersetzt. Neue belastbare Forschung darf das Design auch tiefgreifend verändern, jedoch nur unter dokumentiertem Funktions-Migrationsvergleich; nicht still etwas streichen.

Statuswörter sind explizit: REQUIREMENT, CODE_PRESENT, CONNECTED, SHADOW, EXPERIMENTAL, UNAVAILABLE, LINUX_NATIVE, ANDROID_NATIVE, WEIGHTS_UPDATED, HELDOUT_UTILITY_PASS, REGRESSION_FAIL, APPROVED. Kein Plan-, Mock-, Test- oder Demo-Erfolg wird als echte Trainierbarkeit, Handy-Funktion oder Gesamtfertigstellung ausgegeben.

## 2. Das vollständig integrierte Organmodell

Die folgende Karte zeigt **gleichzeitig gekoppelte Fähigkeitsbereiche** und beispielhafte Verbindungen. Pfeile sind bidirektionale, zeitlich variierende Signal- und Lernmöglichkeiten, **keine** verpflichtende Ausführungsreihenfolge:

~~~text
             ┌──────────── PERCEPTION / A0...A5 ────────────┐
             ⇅                 ⇅           ⇅                ⇅
       B1 DETAIL ⇄⇄ LATENT COUPLING / B3 ⇄⇄ B2 GIST     ACTIVE ATTENTION
             ⇅            ⇅     ⇅          ⇅                ⇅
          B4 / DISTRIBUTED WORKSPACE / COALITIONS / FOCAL REENTRY
             ⇅            ⇅     ⇅          ⇅                ⇅
       WORLD MODEL ⇄ SELF MODEL ⇄ MEMORY ⇄ GOALS / INQUISITION
             ⇅                 ⇅             ⇅
         C1/JEF ⇄ C2 CONTROL ⇄ C3 LANGUAGE ⇄ C4/C5/C6/C7
             ⇅                                      ⇅
       LEARNING / PLASTICITY / JEPA / REPLAY ⇄ TOOLS / OUTCOMES
             ⇅                                      ⇅
                 HUMAN / LOCAL RUNTIME / OBSERVED WORLD
~~~

Die Topologie darf umgeordnet, unterbrochen, verteilt, mehrfach durchlaufen, parallel oder durch einen Fastpath abgekürzt werden. Sensor-, Lern-, World-/Self-, Gedächtnis-, Sprach-, Steuerungs- und Handlungssignale können auf verschiedenen Zeitskalen gegenseitig Zustände beeinflussen. Ein Organ muss nicht erst seine private Textantwort „melden“, bevor der Rest weiterdenken kann.

**Zwei komplementäre Schnittstellen:** (a) das neuronale verteilte **Latent Space / Enlightened Space** für schnelle, reichhaltige wechselwirkende Zustände; (b) eine explizite **Evidenz-/Berechtigungs-/Ereignis-/Transaktionsschicht**, damit tatsächliche externe Aktionen, Provenance, Grenzen und Tests auditierbar bleiben. Die zweite ersetzt die erste nicht. Die latente Repräsentation eines Modells ist nicht automatisch kompatibel mit der eines anderen: dafür sind trainierbare Alignment-/Router-/Receiver-Pfade und messbare Ablationen nötig.

Die gesamte äußere Schleife darf Wahrnehmung → Vorhersage → Handlung → Outcome → Lernen enthalten, kann aber auch beim fehlenden Ereignis, internem Konflikt, eigenem Informationsbedarf oder einer Erinnerung starten. Diese Darstellung ist ein Forschungsziel, kein Nachweis eines bereits existierenden Android-Systems.

### 2.1 A-Plane — Wahrnehmung, Ereignisse und Aufmerksamkeit

A0 nimmt mit Berechtigungsprüfung Text, digitale Ereignisse, Dateiquellen und später Audio, Bilder, Video und Sensoren auf. A1 bildet Ereignisse, zeitliche Grenzen, Thema/Objekte und verlustlos rückverfolgbare Segmente; A5 ist der quellgebundene wahrnehmungsseitige Datenvertrag. A4 ist **aktive Aufmerksamkeit**: Erwartung, Neugier, Fehlerpotenzial, Re-look, Interrupt, Kontext und Ressourcenkosten beeinflussen, *wo* Wahrnehmung weitergeht und welche Hypothese getestet wird.

A2/A3 sind **entwicklungsabhängige** Semantik-/Übersetzungs-/Projektorpfade. Vorübergehend stabilisierte externe Lehrsignale dürfen fehlende Fähigkeit am Anfang überbrücken, sind aber kein dauerhaft unveränderlicher zentraler Lehrer. A3 wird trainierbar gedacht und kann Lehrerrollen internalisieren, selbsttätig nachkalibrieren, aus Erfahrungen und anderen Organen lernen; erfolgreiche Kompetenzübertragung soll technische Gerüste reduzieren oder entfallen lassen. Quelle und Interpretation bleiben getrennt. Reelle visuelle/auditive Funktion und spätere emotional angemessene Sprachausgabe benötigen native Validierung statt Platzhaltern.

### 2.2 B1 und B2 — zwei echte verschiedene Körper

B1_DETAIL arbeitet schwerpunktmäßig kurz/fokal, mit feinen Ereignisauflösungen, genauen Belegen und lokalen Korrekturen; B2_GIST integriert längere Horizonte, Muster und Generalisierung mit gröberer zeitlicher Hierarchie. **Beide sind eigene, möglichst verschieden optimierte lernfähige Gehirnhälften**, keine zwei Personas desselben unveränderten Dense-Modells. Langfristig sind zwei **unterschiedliche sparse MoEs** mit eigenen Experten/Router-/Shared-Pfaden, Temporalität und Plastizität vorgesehen.

Ihre Verarbeitung darf sich mehrfach gegenseitig beeinflussen: B1 kann Hypothesen aus B2 an konkreter Evidenz testen, B2 kann aus B1-Zuständen abstrahieren; beide können eigenständig mit A, C, Memory, World, Self und B3 verbunden sein. Fokale und globale Aufmerksamkeit dürfen sich während einer einzelnen Anfrage ändern. Die alten V13-B1–B6-, Residency-/Hafen-/Parity-, Bridge-, Train-/Swap-/Handover-Verträge sind vollständig weiter in Teil III verbindlich; hier wird nichts davon gestrichen.

Ein kleiner ARM-Prototyp darf Expert- oder Body-Ausführung aufgrund von RAM thermisch seriell laden. Das ersetzt nicht die im Ziel geforderte **logische Parallelität und wirkliche gegenseitige Kopplung**. Nachweise: Aktivierungen/KV oder rekurrente States, aktive Parameter, RSS/PSS, echte Beiträge beider Modelle, Detail/Gist-Ablationsdifferenz, Herkunft und Revisions-Pinning, Lernen und Retention.

### 2.3 B3, B4 und Enlightened Space — gemeinsames Denken ohne Text-Attrappe

**B3/Enlightened ist ein möglichst direkter neuronaler Latent-Austausch zwischen allen dafür geeigneten Organen**, nicht bloß ein zentraler Chatraum. Ziel ist eine gemeinsame anschlussfähige latente Repräsentation bzw. dynamisch miteinander abgestimmte Latent-Räume, in denen Aktivierungen über erlernte Projektionen, rekurrente Verbindungen, selektive Schreibtore und Receiver-Kopplungen wirksam werden. „Gemeinsam“ meint neurale Kompatibilität/Interaktion, nicht dass alle Modelle nur einen einzelnen zentralen Memory-Slot oder Textbroker nutzen müssen. Die Räumlichkeit ist konzeptionell, kein erzwungenes einzelnes Tensorformat.

B3 bildet interhemisphärische und organübergreifende Verbindungen; B4 ist verteilter Zustand, begrenzter focal access, Arbeitsgedächtnis/Koalitionsbildung und Re-entry-Gateway. JEF und C sind Teilnehmer, keine exklusiven Empfänger oder Freigabestellen für normales internes Denken. Wichtige Verbindungen können bei Quelle, Überraschung, Ziel, Nutzen oder Verfügbarkeit direkt/indirekt arbeiten. Selbst-/Weltbild und Memory sind nicht nur Passivdatenbanken, sondern können latent und durch Ereignisse weitere Kognition anstoßen.

Technisch getrennte Schichten: (1) **model-native Aktivationsextraktion** mit verifizierter Herkunft; (2) trainierbarer **Alignment-/Projection-/Cross-Architecture-Kanal**; (3) zeitlich/räumlich passendes **Receiver-Read/Inject/Gain**; (4) Rekurrenz und unterschiedliche Zeitskalen; (5) flexible Routing-/Attention-/Feedback-Kontrolle; (6) extern überprüfbare Provenance-, Consent-, OOD-, Budget- und Rollback-Contracts. Gerade diese Zweischichtigkeit verhindert, dass ein JSON-Paket als fertiger Latent Space durchgeht. Zwischenstufen SOURCE_EXACT/SYMBOLIC/CONTROL/NO_MESSAGE dürfen bleiben, sind ausdrücklich Fallbacks, kein Endzustand.

Für **einen bewiesenen** echten Latent-Pfad braucht es Sender-Aktivierung und stabile Zuordnung, trainierbaren Projektor (oder belastbar abgeleitete gemeinsame Repräsentation), konsumierenden Receiver, sinnvolle Taskwirkung, Ablation gegen SOURCE_EXACT und NO_MESSAGE, OOD-/Retentions-/Kostenmessung und Rückfall. Alte B3-L1-/STEP2-Negativbefunde bleiben offene Gates. Ein erlaubter systemweiter latenter Zustand ist niemals automatisch die Wahrheit oder externe Handlungsautorität.

### 2.4 C-Plane, JEF und Inquisition

**C ist ein spezialisiertes, lernfähiges Steuer-/Sprach-/Aktionsnetz – nicht die einzige bewusste Instanz.** C1/JEF kann Ziele, Aufmerksamkeit und knappe Ressourcen koordinieren; C2 ist ein kleiner strukturierender neuronaler Controller; C3 erzeugt schnelle, verständliche natürliche Sprache. C4 koppelt fokale Koalitionen, Re-look, Interrupts und Reentry; C5/C6/C7 betreffen Vorschläge, überprüfte Ausführung und Berichte. Nicht jeder Gedanke muss durch JEF „genehmigt“ werden. Die Handlungs-/Sicherheitsgrenzen müssen aber für externe Effekte strikt geprüft werden.

Inquisition P1/P2 und erweiterte Prüferstrukturen erzeugen echte Gegenhypothesen, Unsicherheitsbewertung, Definitionsvergleich, False-Positive-Schutz und Belegkonflikte; sie sind nicht nur höflich formulierte Kritik oder eine sequenzielle Antwortschleife. Bestehende P1/P2-Logik aus historischen Versionen wird im Canon erhalten, kompatibel gemappt und nicht ohne explizites Migrationsdokument entfernt. C und andere Organe können ihre eigenen Fehler vorhersagen, Fähigkeiten einschätzen und langsam lernen. Kleine Reaktionen nutzen einen Fastpath; komplexere Fragen erhalten opportunistisch zusätzliche verteilte Verarbeitung. Age ist **Rechte-/Lern-/Entwicklungsstufe**, nicht künstliches Token- oder Rechenzeitbudget.

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

**V14-Aktives-Lernen-System (Erweiterung, keine Reduktion auf den vorigen Reward-Record):** Lernen kann auch durch fehlendes Wissen, neue Ziele, eigene Fragen, neue Aufmerksamkeit, Selbstbeobachtung, konkurrierende Wahrnehmungsinterpretationen, Hypothesen-Konflikte, eine erwartete aber nicht eintretende Beobachtung oder die Unfähigkeit, relevante Latents sinnvoll zu koppeln gestartet werden. Das System soll nach Möglichkeit **selbst den nächsten informativen Beobachtungs-/Probe-Schritt wählen** und die Auswirkungen auf seinen Zustand, seine Weltannahmen und seine späteren Handlungen berücksichtigen.

Mehrere zusammenarbeitende, aber getrennt messbare Lernkreise: (i) sehr schnelle latente/rekurrente Aktivitäts- und Kontexterfahrung; (ii) episodisches Feedback/Second Attempt; (iii) lokale Eligibility-Traces × fehlermoduliertes Lernen auf ausgewählten kleineren Gewichtsgruppen; (iv) aktive Welt-/Zeit-/Hazard-/Omission-Vorhersage; (v) selbsterklärende Hypothesen- und Counterfactual-Prüfung; (vi) B1/B2-JEPA mit trainierbarer EMA-/Predictor-Kopplung; (vii) Cross-Organ-Alignment, Lang-/Kurzzeit-Synapsen, routenspezifische Plastizität und Konsolidierung; (viii) eigene Sprach-/Skill-/Tool-/Self-Modell-Verbesserung; (ix) langsames Meta-Lernen aus tatsächlich beobachteten Folgen früherer Updates; (x) später kontrollierte Algorithmus-/Code-/Gewichts-Selbständerung. Aktive Wissensgewinnung ist von externen Aktionen und Nutzer-Consent zu unterscheiden.

Lernen **während des Betriebs** darf auf einer explizit erlaubten, sicheren, reversiblen Skala erfolgen; Idle-/Dream-Phasen können intensivere Änderungen probieren. Keine blanket Annahme „während Inferenz gar keine Gewichtsänderung“ für das Endziel. Umgekehrt gilt: ein kurzfristiges verändertes Hidden State ist *kein* Beweis für dauerhaft geänderte Modellgewichte. Immer numerische Parameteränderung, Attribution, Replay-/Retention-/Forgetfulness- und Rollbackmessung dokumentieren. Keine unbeobachtete Auslassung automatisch zum negativen Lernsignal umetikettieren.

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

**Learning-Policy:** Kein einzelnes Verfahren ist exklusiver Besitzer des Systems. JEPA, Hebb/Eligibility, Transformer-Gradienten/Adapter, neuromodulierte Konsolidierung, Distillation und Self-/World-Lernen sollen *kooperativ und differenziert* arbeiten. Alltagsaktivität, Explorationsereignisse, normale Gespräche, Sleep und Prüf-/Reset-Phasen haben unterschiedliche Rechte, Zeitkonstanten und Updateziele. EMA bedeutet laufende langsame Anpassung, nicht einen permanent unlernbaren neuronalen Body. Teacherrollen dürfen sich ändern oder verschwinden, sobald die Fähigkeiten internalisiert sind.

### 2.8 NEU: selektive Mini-Distillation zur JEPA- und Gewicht-Update-Steuerung

**Status: Forschungs-Hypothese, nicht im Paper bereits bewiesenes JEPA-Modul.** On-policy Self-Distillation soll dort unterstützen, wo der Student das aktuelle Problem selbst erlebt, und ein konditionierter Lehrer eine relevante Abweichung kennt. Speculative Self-Distillation kann Teacher-Abfragen selektiv an großen lokalen Divergenzen ansetzen. Eine dritte kleine Vorhersageeinheit soll zusätzlich die **Folgen eines beabsichtigten Updates** einschätzen.

- Live Student: aktuelle Sprach-/Welt-/Body-Vorhersage ohne privilegierten Ausgang.
- Teacher: zeitweilig stabilisierte oder langsam mitlernende Kopie, derselbe Body mit menschlich/World-verifiziertem Kontext oder ein separat rechtlich freigegebenes Modell; die Teacher-/Student-Rollen können dynamisch wechseln oder wegfallen.
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

**Keine Teacher-Dogmatik:** Distillation ist eine mögliche lokale Lernhilfe, nicht das Zentrum von V14. Neu entstehende Fähigkeiten sollen auch ohne externe Lehrinstanz über Beobachtung, Selbst-/Weltmodell, verteilte Plastizität, JEPA und tatsächliche Outcomes wachsen können. In Forschungsabläufen kann eine Snapshot-Referenz kurzfristig stabil sein, während die zugrunde liegenden aktiven Organe und langsamen Zielrepräsentationen fortlaufend lernfähig bleiben. Ob und wann das hilft, entscheiden Ablationen, nicht der Architekturtext.

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

**Verbindliche aktuelle Betriebsweise:** Nicht nur neue Entwürfe schreiben: den **vorliegenden V14-Master selbst** weiterentwickeln und nach jeder substanziellen Änderung `V14_LIVE_WORKPLAN.md` und `V14_RESEARCH_LEDGER.md` nachziehen. Die komplette V13-Pflichtliste bleibt indiziert und wird im Code gegen tatsächlich verbundene Consumers geprüft. Jeder stündliche oder manuell gestartete Forschungsagent führt zusätzlich den laufenden Research-Zyklus aus, statt allein bestehende Patches zu testen. Änderungen aus neuem Paper dürfen grundlegende Designmethoden ersetzen, sofern dieselben Funktionsziele/möglichen älteren Nutzerentscheidungen weitergeführt, Lizenz/Safety respektiert und Verifikation/Backup durchgeführt werden.

## 19. Messverträge und klares Reporting

Ein Agentenbericht muss sagen: (1) welcher echte End-to-End-Consumer neu läuft; (2) Code- und Model-/Lizenzrevision; (3) welchen V14-/Canon-Abschnitt das abdeckt; (4) echte Linux-/Redmi-/Trainings-/Holdout-Beweise; (5) welche Funktion noch fehlt; (6) den nächstgrößeren Integrationsschritt. PR-Zahlen, Commits und CI-Screenshots ohne Funktionspfad sind Sekundärdaten. Ehrliche negative Kontrollen sind wertvoll; sie dürfen aber die Implementierung aller anderen Organe nicht anhalten.

Testarme: JEPA vs SDFT vs SSD vs JEPA+SSD+Meta; zwei MoE statt identischem Dense; Memory Consumer vs ohne; mit/ohne Pending-/Omission-Time; latent/exact/no-message; English→German; Reset/Crash/Revocation; explizit erlaubte vs verbotene Tools; offene Welt vs verifizierte Quellen; dauerhafte Retention und Rückfall.

## 20. Fortbestehende Pflichten aus V13

Die vollständigen alten Canon-/Roadmap- und Drive-Sichtungstexte werden unten **verbatim** archiviert. Keine einzelnen IH-H-, B3-H-, G-, F-, A/B/C-, WP-, STEP-, State-/Contract-/Ablationspflichten werden aus der V14-Soll-Liste entfernt. Historische widersprüchliche Modi und neuere Nutzerentscheidungen sind über die Provenienz auditierbar, nicht still umgedeutet. Für eine vollständig neue operative Fassung werden die obigen Abschnitte benutzt; für seltene Einzelverträge gilt der jeweilige unverändert beigefügte Nachweis bis ein ausdrücklich dokumentierter kompatibler Ersatz vorliegt.

---

---

## 21. Verbindliche laufende Forschungsarbeit — keine einmalige Literaturbeilage

**V14-Forschung ist eine Daueraufgabe und Teil der normalen Arbeitsaufträge aller Agenten.** Bei jedem geplanten Research-Lauf – und zusätzlich bei einem in der Entwicklung aufgetauchten ungelösten Problem – gezielt aktuelle Primärliteratur, relevante verwandte frühere Forschung, Referenzimplementierungen, GitHub-/HF-Versionen, offene Lizenzfragen und Gegenbeispiele recherchieren. Auch ohne eine neue Nutzerfrage neue Relevanz entdecken und dokumentieren. Das geschieht über tatsächlich eingerichtete Agenten-Läufe, nicht durch die bloße Existenz dieses Textes.

**Research-Loop:** `scan new / related -> dedupe & resolve title/aliases -> read primary methodology + limitations -> classify evidence -> map to V13 obligations and V14 organs -> propose concrete architectural/application change -> design falsifiable baseline, negative controls, resource/license checks -> prototype when authorized -> measure -> update research ledger and live plan -> adapt active V14 only with evidence & backup`.

Das Research Ledger `v14/V14_RESEARCH_LEDGER.md` speichert für jeden Eintrag: Originaltitel/Identifier/Aliasse; Datum des tatsächlichen Nachschlagens und Paper-Erscheinungsdatum; belastbare URL/Originalquelle; Befund, Grenzen, Gegenargument und offene Reproduzierbarkeit; relevante V14-/V13-Funktionen; konkreter Vorschlag samt Alternativen; Testdaten/Ablation/erwartete Beobachtung; vorhandener Code/Modell-Lizenz/ARM-Status; aktueller Status; Wiedervorlage; PR/Commit/Device-Evidenz. Fehlende Daten bleiben explizit **UNVERIFIED**, nicht erdacht. Vermeide „habe ich schon gelesen“, wenn nur ein Titel entdeckt wurde.

**Spätere Fragen sollen wiederauffindbar sein:** Nennt der Nutzer etwa ein Paper mit unklarem/anders geschriebenem Namen, erst Ledger und Originaltitelvarianten prüfen; dann sagen, welche konkrete Methode bekannt ist, welche V14-Ideen dazu notiert wurden, was wirklich experimentell bewiesen ist und woran wir bereits arbeiten. Keine Behauptung einer vorherigen Lektüre ohne datierten Eintrag.

**Aktive Adaption:** Erkennt ein Agent nach echter Prüfung eine Methode, die exakt das gesuchte Verfahren oder eine fehlende Voraussetzung liefert, darf er selbstständig einen tiefgreifenden Architektur- oder Codevorschlag samt Source-, Lizenz-, Budget- und Regressionsanalyse vorbringen und in einem isolierten Branch umsetzen. Nicht bei jedem neuen Preprint das Zielsystem umwerfen: fairer Vergleich, Missbrauchs-/Sicherheitsgrenzen, echte Messung und explizite Migration vor Übernahme. Auch bewährte ältere Bausteine dürfen ersetzt werden, ihre *Funktion* und alten Nutzerentscheidungen aber nicht still verloren gehen.

## 22. Operativer Live-Plan und unabhängige Sicherung

**Aktive Dokumente:** der vorliegende **V14-Master** ist der fortlaufend bearbeitete Hauptkanon; `v14/V14_ARCHITECTURE_AND_RESEARCH_ONLY_20261119.md` ist seine konsistente Lesefassung; `v14/V14_LIVE_WORKPLAN.md` hält Workstreams und offene Vollsystem-Lücken; `v14/V14_RESEARCH_LEDGER.md` hält laufende Forschung; `v14/V14_CANON_COVERAGE_INDEX.md` indiziert historisch benannte Canon-Verträge.

**Vor jeder materiellen Änderung:** aktiven Git-HEAD prüfen, unveränderlichen vorherigen Masterstand unter `v14/backups/` sichern, Quellen/Änderungsgrund und betroffene Canon-Funktionen erfassen; danach nur Teil I/II gezielt ändern, gesamte Teile-III-Quellhistorie **bytegleich** behalten, Lesefassung synchronisieren, Coverage-Index gegen vorherigen Stand vergleichen, tests/review durchführen, git commit/remote readback kontrollieren. Keine ältere Sicherung nachträglich „aktualisieren“. Weil auch Git seine Historie bewahrt, haben Snapshot+Commit eine zweite voneinander unterscheidbare Wiederherstellungsmöglichkeit.

Bei mehreren parallelen Agenten ist ein Integrator für Master-Schreibzugriffe verantwortlich. Research- und Feature-Agenten erfassen eigene Evidenz und Änderungsvorschläge zunächst konfliktfrei; der Integrator übernimmt überprüfte Ergebnisse in einem geordneten Batch. Kein blindes Auto-Merge von konkurrierenden Manuskripten und kein Force-Push.

## 23. Vollständigkeits- und Forschungszustand, 20.11.2026

**Nicht gleichsetzen:** `ARCHITECTURE_SPECIFIED` ≠ `CODE_PRESENT` ≠ `CONSUMER_CONNECTED` ≠ `TESTED_LINUX` ≠ `REDMI_NATIVE` ≠ `NUMERIC_LEARNING` ≠ `HELDOUT_UTILITY` ≠ `COMPLETE`. Der erhaltene V13-Canon ist ein **verbindlicher Funktionskatalog**, kein Nachweis seiner Implementierung. Research-Ledger-Einträge sind Ideen mit Evidenzstufen, nicht automatisch implementierte Updates. Echte Ergebnisbelege sind im Live-Plan rückverlinkt.

*Die vollständigen historischen Anhänge und alle älteren Quellpflichten stehen in [V14 MASTER](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md). Diese lesbare Kurzdatei ist keine Kürzung des verbindlichen Canon.*
