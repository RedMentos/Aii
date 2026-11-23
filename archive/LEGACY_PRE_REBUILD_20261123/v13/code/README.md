# V13 – vorhandener Age-0-Teststand

Single Source of Truth: `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`.
Chat, Routing und Ausgabe sind weiterhin ein Zwischenstand. Der frühere echte
Redmi-`SMOKE_PASS` bleibt erhalten; neue Linux-Proofs sind getrennt gekennzeichnet.

## Auf dem Handy starten

Das ZIP entpacken und in Termux in den entpackten Ordner `V13-Phone` wechseln:

```bash
bash STARTEN.sh
```

Das bestehende Setup installiert Abhängigkeiten, prüft/lädt die festgelegten
Modelle und startet nach den Tests den Chat. Bereits vollständige Downloads
werden anhand ihrer Hashes wiederverwendet. Standard-Datenordner ist `~/v13`;
vorhandene Chats, Korrekturen und Modelle bleiben dort. Den Quellcodeordner
nicht in den Datenordner hinein entpacken. Ein vollständiger erster Download
benötigt Internet; danach laufen die Modelle lokal.

Später starten: `v13 chat`. Im Chat zeigen `:doctor`, `:resources` und `:ledger`
den tatsächlichen Zustand; `:cancel` erhält bereits ausgegebenen Text.

## Neue Nachweise ausführen

```bash
v13 selftest
v13 probe
v13 probe step12
```

Im Chat funktionieren `:probe` und `:probe step12` ebenfalls. Der STEP12-Test
nutzt einen getrennten Test-Speicher und dieselben installierten Modelle. Er
prüft C2/C3 ohne B-Abhängigkeit, C1-Neustart, B1/B2 und Paketverweise. Ergebnisse
stehen unter `~/v13/exports/`; vorherige Proof-Dateien werden archiviert.
`VERTICAL_CHECKS_PASS` bestätigt die beschriebenen Prüfungen, keine fertige
Gesamtarchitektur und keinen bewiesenen Qualitätsgewinn durch B1/B2.

Die gültige STEP2-Messung (fester 70-Zeilen-Satz, aufgabengebundene Nutzenbewertung) startet
`bash TESTEN_STEP2.sh` (ruft `tests/integration_step2_utility.py`). Stand: 70/70 Zeilen strukturell PASS,
Nutzen UTILITY_FAIL (siehe `docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md`). Die ältere Kanal-/Rollen-Ablation
(nur diagnostisch) läuft weiterhin so:

```bash
python tests/integration_step2.py --installed-home "$HOME/v13" --out "$HOME/v13/exports/step2-ablations.json"
```

Das dauert mehrere Minuten. Nach jedem Fall wird der Zwischenbericht gespeichert.
Mit `--cycles 2` lässt sich die Messung wiederholen. Zahlenvorkommen in den
Antworten sind ausdrücklich nur ein diagnostischer Messwert, keine automatische
Bewertung von Richtigkeit oder Komplementarität. Laufende Probe abbrechen:
im Chat `:cancel`, im Terminal Strg+C.

Die neuen Prüfungen ändern weder Gewichte noch Freigaben. B3-Latents bleiben OFF.
Parameter sind dokumentierte Boot-Schätzungen; aus einzelnen Antworten wurden
keine neuen Prompts oder Default-Budgets abgeleitet.

Der Second-Attempt-Test prüft Korrektur, Umformulierung, Teilübertragung, Neustart,
zwei negative Übertragungsfälle und einen Lauf ohne Gedächtnisabruf:

```bash
python tests/integration_second_attempt.py --installed-home "$HOME/v13" --out "$HOME/v13/exports/second-attempt.json"
```

Auch dieser Test verwendet einen getrennten Speicher und speichert jeden
abgeschlossenen Fall. Frühere Ergebnisdateien bleiben unter `proof-history/`.
`FAMILY_CHECKS_PASS` ist der Nachweis für diese begrenzte Testfamilie.

Bei einem Chat-`DEADLINE` enthält `:export chat json` jetzt zusätzlich die
Turn-Phasen, den Abbruchabschnitt und native Lade-/Template-/Prefill-/Stream-Zeiten.
Damit lässt sich eine langsame Phase vom bloßen Gesamtzeitlimit unterscheiden.
Die alten Redmi-Screens zeigen echte Abbrüche; ihre genaue Ursache und eine
Behebung auf dem aktuellen Redmi-Build sind noch nicht nachgewiesen.

## Arbeitsstand wieder aufnehmen

`BUILD_STATE.json` nennt bestandene Prüfungen und nächste offene Aufgaben.
`docs/RESUME.md` beschreibt die Fortsetzung; `docs/proofs/` enthält die echten
Berichte. Das ZIP enthält außerdem `WORKSPACE_FILES.json` mit SHA-256 für alle
gesicherten Dateien. Heruntergeladene Modelle und native Binärdateien sind
reproduzierbare Caches und nicht Teil des Source-ZIPs.

## B2-Kontext aus mehreren Ereignissen (2026-09-23)

B2 kann jetzt passende frühere Quellen aus bis zu vier gespeicherten Angeboten
in den nächsten Modelllauf einbeziehen. Der zusätzliche Kontext ist begrenzt,
quellengebunden und übersteht einen Neustart. B1 behält sein kurzes Fenster.
`:budget` zeigt die Boot-Werte; `:budget b2_state_slots 4` setzt die Slot-Anzahl. Zum Vergleich deaktiviert `:budget b2_state_slots 0`
den zusätzlichen B2-Kontext. Das ist keine Änderung der Modellgewichte.

`v13 probe body-state` beziehungsweise `:probe body-state` führt sechs echte
Modellprüfungen in einem getrennten Testspeicher aus und speichert nach jedem
Fall `~/v13/exports/body-state-proof.json`. Der neue Linux-Nachweis ist enthalten;
ein aktueller Redmi-Nachweis und allgemeine semantische Komplementarität sind offen.

Die vollständigen Entpack-/Startbefehle stehen in START_HIER.txt.

## Experience, Teacher und Lernen (2026-09-29)

Der bestehende Chat ist um tatsächliche Auswahl-, Replay- und Exportpfade
ergänzt. Beispiel nach einer eigenen Modellantwort:

```text
:teacher use B1_DETAIL
:teacher on
:teacher compare
:experience
:choose teacher 0:80 --kind fact
:replay 1
:export dataset
```

Vor `:choose` den Referenztext prüfen und passende Zeichengrenzen wählen;
`0:80` ist nur ein Beispiel. Ohne Bereich wird die ganze Referenz gewählt.
`:choose self` wählt die eigene Antwort. Die gewählte Aussage erhält ihre
Autorität durch deine Auswahl; eine Teacher-Antwort wird nie automatisch Fakt.
Der wiederverwendete B1-Checkpoint ist eine separate eingefrorene Referenz und
kein behauptetes stärkeres Modell. Ein anderes GGUF lässt sich weiterhin mit
`:import model TEACHER /vollstaendiger/pfad.gguf` importieren.

`:export dataset` erzeugt JSONL plus SHA256-Manifest für den aktuellen Chat;
`:export dataset all` exportiert alle Chats. Self, Reference und HumanDecision
bleiben getrennte Felder mit Quellen, Status und Lernberechtigung. Export allein
startet keinen Optimizer. Replay benutzt echte Modelle und gespeicherte
Korrekturen; seine Entwürfe bleiben außerhalb von Fakten und Nutzerchat.

Der vorhandene kleine Routing-Lerner verändert nach ausdrücklich erlaubten
Labels tatsächliche Gewichte. Ablauf:

```text
:feedback route detail --learn
:learning shadow
:learn
:requests
:learning commit
:approve <konkrete-Update-ID>
:rollback <dieselbe-Update-ID>
```

Feedback immer nach der passenden eigenen Antwort geben. Training benötigt
mindestens vier unterschiedliche markierte Fragen; eine Freigabe verlangt
mindestens zwölf Beispiele, alle vier Routen und bestandene Held-out-/Retention-
Prüfungen. `:requests` zeigt den tatsächlichen Kandidatenstatus. Trainiert wird
der externe Routing-Head auf echten eingefrorenen Needle-Embeddings; die
LLM-Body-Gewichte werden dabei nicht verändert. Reines Speichern von Korrekturen
mit `:feedback fact ...` wirkt dagegen direkt über quellengebundenen Abruf.

`:self` zeigt den strukturierten Gerätezustand und echte Fähigkeiten;
`:world` zeigt beobachtete eigene Textaktionen, zeitliche Vorhersagen und Fehler.
Die Zeitprognose basiert auf vergleichbaren früheren Aktionen. Bei zu wenigen
Messungen oder fehlender Abdeckung bleibt sie unbekannt. Das ist eine
statistische Baseline, kein semantisches World-JEPA. Die abgeleiteten Zustände
werden bei Neustart aus gespeicherten Aktionen repariert.

## Gemeinsamer ausführbarer Testlauf

Den laufenden Chat zuerst mit `:shutdown` beenden. Im Programmordner:

```bash
bash TESTEN.sh
```

Setup und Downloads werden geprüft; danach laufen JEF-Modi, Teacher/Auswahl/
Replay, echter Lern-Commit mit Neustart/Rollback, STEP1/2, B2-Kontext,
Second-Attempt, Abbruch/Neustart und zwölf wiederholte native Antworten.
Lernfreigaben gelten ausschließlich im separaten Testspeicher. Der Test
verändert keine trainierten Gewichte in deinem Chat-Speicher.

`bash TESTEN.sh --quick` verkürzt die Stabilitätsserie und überspringt die längeren STEP1/2-, Body-State-, Second-Attempt- und Abbruchtests. Die implementierten Lernpfade werden weiterhin geprüft. Mit
`bash TESTEN.sh --compare-c3` kommt der gepinnte SmolLM2-Vergleich hinzu
(zusätzlich rund 92 MB Download). Berichte und Protokolle liegen je Lauf in
`~/v13/exports/acceptance-<Zeit>/`; jeder Abschnitt wird sofort gespeichert.
Ein Abbruch erhält fertige Teilberichte. `IMPLEMENTED_PATHS_PASS` bedeutet,
dass diese Tests bestanden sind, nicht dass sämtliche Canon-Funktionen
implementiert oder auf dem Redmi langfristig nachgewiesen sind.

Einzeln: `:probe jef-modes`, `:probe sustained` oder im Terminal
`v13 probe sustained --cycles 12` (4 bis 128 Durchläufe).
Fehlende Temperatur-/Energie-/Speichersensorwerte bleiben unbekannt.

`specs/component-contracts.json` erfasst A0–A5, B1–B5, C0–C7 und F1–F11;
`specs/learning-objectives.json` trennt implementierte und fehlende Lernziele.
Im Chat abrufbar mit `:components` und `:objectives`. Nicht implementierte
JEPA-/Projektor-/Body-Lernziele besitzen weiterhin Lernfreigabe null.

## Ergänzte reale Lern- und Beobachtungstests

`bash TESTEN.sh` prüft zusätzlich die getrennten Wake-/Halt-Heads, native
read-only LFM2-Taps und beide lokalen Dense-State-Predictors. Auch `--quick`
führt diese neuen Pfade aus und verkürzt nur die vorhandene Stabilitätsserie.
Die Tests arbeiten in isolierten Test-Brains mit expliziten Fixture-Freigaben.
Ihre Freigaben verändern den eigenen Brain nicht. Teilberichte bleiben bei
Abbruch unter `~/v13/exports/acceptance-...` erhalten.

`:tap B1_DETAIL` beziehungsweise `:tap B2_GIST` beobachtet die letzte Eingabe
(maximal 64 native Tokens). `:feedback prediction observe --learn` erlaubt
beobachtete Zustände dieser Quelle als Target. Nach mindestens zwölf kurzen,
verschiedenen Quellen: `:learning shadow` und `:learn b1_predictor` oder
`:learn b2_predictor`. Ein geeigneter Kandidat benötigt weiterhin eine
individuelle `:approve <Update-ID>`-Freigabe im Commit-Modus. Der aktive
Predictor liefert bei weiteren expliziten Taps eine 16-dimensionale lokale
Vorhersage; die tatsächlichen Features und Hypothesen werden quellengebunden
gespeichert. Dies aktiviert weder Body-Training noch B3-Receiver-Injection.

## A3 Text-Projector

`:feedback alignment observe --learn` erlaubt ein quellengebundenes Raw/Encoder-Paar. Nach mindestens 32 unterschiedlichen kurzen Quellen kann `:learn a3_student` im Shadow-Modus den Text-Projector trainieren. Quellen über 4096 UTF-8 Bytes werden ausdrücklich abgelehnt; keine stille Kürzung. Native Encoder-Targets sind eingefrorene Referenzen, keine Fakten.

Der Kandidat benötigt Verbesserungen gegenüber beiden Mean-Baselines, getrennte Alignment-/Reconstruction-Ablationen, Nicht-Kollaps und Retention. Nach individueller Freigabe enthält das PerceptPacket das tatsächliche 16-dimensionale Student-Ergebnis. Ein vorhandener Routing-Head wertet seine Encoder-Feature-Projektion im JEF-Shadow gegen den eingefrorenen Encoder aus; Routing-Rechte bleiben null. `TESTEN.sh` enthält jetzt auch diesen Lebenszyklus. Kein Teacher-Removal oder native Receiver-Injection wird dadurch freigegeben.

## World-Predictor für tatsächliche eigene Textaktionen

Nach einer abgeschlossenen Antwort erlaubt `:feedback world observe --learn` das genaue Eingabe-/Aktions-/Output-Paar als Lernbeobachtung. Ab zwölf unterschiedlichen Quellen und mindestens zwei tatsächlich gemessenen Aktionsrollen: `:learning shadow`, dann `:learn world_predictor`. Der getrennte externe Projector/Predictor lernt eine 16-dimensionale Zukunftsvorhersage aus eingefrorenen Encoder-Features und der tatsächlichen Aktionsrolle. Kopie, Action-off, Action-shuffle und Target-shuffle dienen als getrennte Baselines. Ein geeigneter Kandidat benötigt Nicht-Kollaps, Retention gegenüber den unveränderten alten Zielkoordinaten und individuelle Freigabe.

Ein aktiver Kandidat ergänzt vor der bestehenden Textaktion die Prognose; danach wird der Fehler gegenüber dem wirklich fest gespeicherten eigenen Output gemessen. Die Antwort erhält dadurch keine Wahrheitsbestätigung und kein automatisches Faktenlernen. Modellgewichte bleiben eingefroren. Modell-, Konfigurations- oder Regeländerungen führen zur Baseline, bis der Kandidat erneut validiert wird. `TESTEN.sh` prüft den Lebenszyklus mit echten Copy-/Modellaktionen, Neustart, bestehendem Antwortpfad und Rollback in einem separaten Speicher.

Jede Prognose benötigt außerdem gemessene Unterstützung für genau diese Aktionsrolle und diesen Eingabebereich. Trainingsquellen bestimmen den Cosine-Support, mit mindestens drei unterschiedlichen Quellen pro Rolle; Testquellen ändern diese Grenze nicht. Untrainierte Rollen und außerhalb liegende Eingaben erhalten die bestehende Baseline. Der gespeicherte Residual-Spread beschreibt Fehler des Fits, keine kalibrierte Wahrscheinlichkeit. Alte Kandidaten ohne Support-Artefakte benötigen erneute Validierung.

## C2: Kalibrierung des ersten nativen Routing-Vorschlags

Mit `:feedback route simple|detail|gist|both --learn` wird die gewünschte Route für die letzte genaue Eingabe festgehalten. Ab 32 unterschiedlichen freigegebenen Quellen: `:learning shadow`, dann `:learn control_calibration`. Der bestehende native Needle-Runner liefert die tatsächlichen Vorschläge und seine rohe Confidence. Das Lernziel ist die Übereinstimmung des **ersten** gültigen Vorschlags mit dem Operator-Label. Sechs externe Gewichte und eine separat angepasste Temperatur werden gelernt; native Gewichte bleiben eingefroren.

Trainings-, Kalibrierungs- und Testquellen bleiben getrennt. Ein Kandidat benötigt Brier-/NLL-Verbesserung, ECE höchstens 0,2, Retention, Gradient-, Wiederholungs- und Reload-Prüfungen. `:requests` zeigt den konkreten Kandidaten; im Commit-Modus aktiviert `:approve <Update-ID>` nur dieses Artefakt. Nach Neustart verwendet der bestehende Routing-Pfad die genehmigte Kalibrierung. Unter 0,6 oder außerhalb der gemessenen Route-/Confidence-Unterstützung gilt das BOOT-Routing. Ein bereits genehmigter externer Routing-Head behält seinen Vorrang.

Die Wahrscheinlichkeit betrifft das explizite Routing-Label, keine sachliche Wahrheit der Antwort. Diese begrenzte Unterstützung beweist keine allgemeine OOD-Erkennung. `TESTEN.sh` prüft echte native Beobachtungen, echte finale Modellausgabe, Abstention, zweiten Kandidaten, Neustart und Rollback in einem separaten Test-Speicher.

Abgeschlossene Gesamttests lassen sich nach einem Neustart oder nach Verschieben der Berichte prüfen: `python scripts/verify_acceptance.py <Berichtsordner>/acceptance.json --compare-c3`. Für einen ohne Vergleich gestarteten Lauf entfällt `--compare-c3`; bei einem bewusst gestarteten Kurzlauf kommt `--quick` hinzu. Der Prüfer verlangt alle jeweiligen Stufen, passende aktuelle Code-Hashes, unveränderte Proof-Dateien und tatsächliche PASS-Status. Er verwendet die Dateien im Berichtsordner, auch wenn der ursprüngliche absolute Workspace-Pfad verschwunden ist. Ein laufender oder unvollständiger Test erhält keinen PASS.

## Gelerntes Gedächtnis-Retrieval

`:memory` zeigt die gespeicherten Korrekturen mit ihren IDs. Für die letzte Frage kennzeichnet `:feedback retrieval <Memory-ID> relevant|irrelevant --learn` die Relevanz einer vorhandenen Korrektur. Das speichert ein quellengebundenes menschliches Relevanzlabel; es erzeugt keine neue Tatsache. Ohne `--learn` wird der Eintrag nur aufgezeichnet und eine frühere Lernfreigabe desselben Frage-/Quellenpaares aufgehoben.

Ab 48 unterschiedlichen freigegebenen Paaren: `:learning shadow`, dann `:learn memory_retrieval`. Jede der getrennten Trainings-, Kalibrierungs- und Testgruppen benötigt mindestens zwei unterschiedliche Erinnerungsquellen und je vier positive und negative Paare. Die tatsächlich verwendeten Needle-Features bleiben eingefroren. Der kleine externe Relevanz-Head muss die lexikalische Suche schlagen, falsche Treffer begrenzen und semantische Ablation, Kalibrierung, Retention, Gradientenprüfung und Reload bestehen. Erst `:learning commit` und `:approve <Update-ID>` aktivieren diesen einzelnen Head.

Die Laufzeit verbindet zugelassene Treffer mit der aktuellen Frage und ihrer unveränderten menschlichen Wertquelle im bestehenden Antwortpfad. Andere ausdrücklich benannte Projekte und fremde Chat-Sessions bleiben ausgeschlossen. Unsichere oder nicht unterstützte Paare verwenden die bisherige Suche. `retrieval_seconds` begrenzt das gesamte semantische Suchbudget innerhalb der Antwortfrist; `retrieval_candidates` begrenzt die Zahl semantisch geprüfter Erinnerungen. `TESTEN.sh` misst echtes Finden, Ablehnen, C3-/B1-Ausgaben, neue Quellen mit alten Retentionfällen, Neustart und Rollback. Der Nachweis umfasst wiederkehrende Frageformen an getrennten Erinnerungsquellen; allgemeine Übertragung und der aktuelle Redmi-Test bleiben eigenständige Nachweise.

## Langsame F7-Lernbudgetsteuerung

`:plasticity` zeigt die getrennten Messzustände; `:plasticity route` zeigt einen einzelnen Pfad. Nach einem abgeschlossenen, artefaktgebundenen Shadow-Job werden Retention, Freigabefähigkeit und gemessene Schrittgrenzen ausgewertet. Eine langsame EMA reduziert Lernrate und Normbudget innerhalb des bereits konfigurierten Basisbudgets. Wiederholte sichere Updates reifen langsamer; ein erhaltender, aber noch unbrauchbarer Fit öffnet das Budget langsam wieder. Ein Retentionfehler dämpft den betroffenen Pfad. Bestehende Test-/Commit-Grenzen bleiben gleich.

Der nächste ausdrücklich gestartete Shadow-Job erhält die abgeleiteten Werte; `PlasticityBudget` und Worker-Metriken halten die wirkliche Lernrate und Normgrenze fest. Die Operator-Konfiguration bleibt erhalten. F7 beobachtet keine native Shared-Attention-/Router-Verschiebung, wenn dieser Port fehlt; diese Werte bleiben unbekannt. Eine Stabilitätsmarkierung erlaubt keine automatische Konsolidierung oder Freigabe. Ein Neustart zählt fertige Prüfungen genau einmal und repariert eine unterbrochene Diagnoseveröffentlichung, ohne einen fertigen Kandidaten zu verwerfen. Das ist ein gemessener Feedback-Regler; ein trainierter neuraler Meta-Controller bleibt ein eigener offener Objective.

C2 verwendet jetzt höchstens `calibration_sources` freigegebene Quellen (BOOT256, einstellbar32–512). Frühere Testbeobachtungen und ihre Route-/Confidence-Unterstützung bleiben im Artefakt. Ein neuer Datensatz muss sowohl aktuelle Fälle als auch alte unveränderte Fälle je Route erhalten. Ältere Köpfe ohne gespeicherte Retentionfälle bleiben für Inferenz lesbar; ein Ersatztraining erfordert eine ausdrückliche Neuvalidierung der fehlenden Daten.

Für fortlaufende Quellsicherungen kann `TESTEN.sh --compare-c3 --archive-dir <neuer-Ordner>` die Berichte und tatsächlichen Feature-Dateien nach jeder Stufe spiegeln. Der Ordner muss neu sein; frühere Proofs werden erhalten. Ein Spiegel mit Status RUNNING ist kein abgeschlossener Proof.

## Quellengebundene Konsolidierung

Nach mindestens drei unabhängig formulierten, ausdrücklich mit `--learn` bestätigten Erfahrungen kann `:consolidate semantic` gleichlautende Human-Werte als einen mehrteiligen Quellenindex zusammenführen. `:consolidate procedural` sammelt mehrfach bestätigte Routen für genau die vom Operator verwendeten Fragen. `:requests` zeigt den einzelnen Vorschlag; `:learning commit` und `:approve <Request-ID>` aktivieren ihn. `:consolidate status` zeigt den aktuellen Bestand, `:consolidate rollback <Request-ID oder Index-ID>` deaktiviert den Index und erhält die ursprünglichen Erinnerungen.

Jede Nutzung prüft alle Eingabe-, Entscheidungs- und Wertquellen sowie die aktuelle Korrektur/Lernfreigabe erneut. Eine widersprechende Korrektur, ein Vergessen oder eine beschädigte Quelle macht den Index unbrauchbar. Gedächtnis und Replay tragen die gesamte Provenance; bestätigte exakte Verfahren gelten ausschließlich für ihre ursprünglichen Frage-Cues. Das implementiert bestätigte Verdichtung und Wiederverwendung, keine neuen semantischen Schlussfolgerungen oder Konsolidierung in native Gewichte.

## Nativer C3-Output-Adapter

Nach einer echten C3-Antwort gibt `:feedback output <gewünschte Referenz> --learn` einen expliziten Zieltext für ihren genauen Antwortkontext frei. Ab32 verschiedenen Kontexten mit2–16 unterschiedlichen ersten nativen Zieltokens: `:learning shadow`, `:learn output_adapter`. Training, Kalibrierung und Test benötigen jeweils mindestens acht Quellen sowie zwei Beispiele je Zieltokentyp. Das Lernziel betrifft den ersten nativen Token der Referenz.

Der Job misst den wirklichen1024-dimensionalen C3-Zustand und alle65.536 nativen Token-Wahrscheinlichkeiten. Nur kleine externe Wortschatz-Delta-Zeilen werden gelernt. Freigabe verlangt NLL-/Brier-Gewinn, mindestens80Prozent konservative erste-Token-Treffer, Kalibrierung, Unterstützung und alte unveränderte Retentionfälle. Die ursprünglichen Modellgewichte bleiben eingefroren. `:learning commit` und `:approve <Update-ID>` aktivieren genau diesen einzelnen Bestandteil; Neustart und `:rollback <Update-ID>` verwenden die bestehenden Generation-Manifeste.

Der normale C3-Pfad erzeugt den ersten Token mit dem genehmigten Delta und setzt anschließend mit dem nativen Decoder ohne Delta fort. Unsichere/nicht unterstützte Zustände verwenden die bestehende Ausgabe. Unterstützung im Feature-Raum beweist keine semantische OOD-Erkennung. Der begrenzte Vergleichs-Test ist kein Nachweis allgemeiner Sprach-/Rechenqualität. `output_adapter_seconds` begrenzt die zusätzliche Messung innerhalb der Antwortfrist; `output_adapter_max_bias` ist eine ausgewiesene BOOT-Grenze.

## Arbeitszustand und sichere Wiederaufnahme

`:executive` zeigt den quellengebundenen C1-Stand; `:task set <Aufgabe>` bzw. `:task clear` ändern die explizite Aufgabe. `:force-report` liefert sofort bereits gespeicherten Antworttext oder den klar gekennzeichneten Quellenbericht und beendet laufende Deliberation. Das ist keine erfundene Modellantwort.

Angenommene Anfragen liegen jetzt atomar in SQLite. Noch nicht begonnene Anfragen und `:pause` bleiben über Neustarts erhalten; `:resume` setzt die Warteschlange fort. Die bestehende Wartefrist gilt auch nach einem Neustart. Begonnene, unterbrochene Antworten werden erhalten und nicht automatisch doppelt erzeugt. Alte V1-Datenbanken und Backups werden geprüft und transaktional auf Schema2 migriert.

Ausgabe-Feedback nennt jetzt seine `source=src_…`-ID. `:forget-source <Source-ID> --confirm` löscht diese HUMAN_OUTPUT_REFERENCE und sperrt davon abhängige Kandidaten. Aktive gelernte Komponenten müssen zuvor ausdrücklich zurückgerollt werden. `record` widerruft zukünftiges Lernen, löscht die Referenz jedoch nicht. Der Chatverlauf und separate Backups bleiben bestehen. Ungültige oder nicht belegbare alte Antworten werden nicht erneut als native Modellkontexte/Lernquellen importiert.

Während Laden, Prefill und Ausgabe beobachtet der bestehende Ressourcenregler kontinuierlich die tatsächlich verfügbaren Prozess-/Sysfs-Werte. Kritische Werte lösen den vorhandenen Abbruchpfad aus; native Teilantworten bleiben erhalten. PID-Namespace und Prozessstartzeit werden geprüft, damit keine fremden Prozesse als Modell-RAM gezählt werden. Fehlende Sensoren oder KV-Zähler bleiben unbekannt.

## C3 mit einem einzigen kausalen Prefill testen

`bash STARTEN_CAUSAL.sh` richtet die vorhandenen Modelle ein, bereitet den geprüften kausalen Decoder vor und öffnet denselben persistenten Chat mit diesem ausdrücklich gewählten Modus. Frische Installationen verwenden über `bash STARTEN.sh` weiterhin den bisherigen Server-Decoder; ein zuvor gewählter Modus bleibt gespeichert. Details und Rückkehr zum Server-Modus stehen in [CAUSAL_CHAT.md](docs/CAUSAL_CHAT.md).

`bash TESTEN_NATIVE_STREAM.sh --prompt 'Berechne die Hälfte von 120 Euro.'` bleibt als separater Decoder-Test verfügbar. Der kausale Chat verwendet einen Prefill mit anschließender nativer Fortsetzung, bis zum Modell-Endtoken oder 64/128 Tokens. Alte Adapter passen nicht zu dieser neuen Feature-ABI. Solange kein passender Head ausdrücklich freigegeben ist, verwendet der kausale Modus die echte native Ausgabe ohne gelerntes Delta.

Für den neuen kausalen Lernpfad werden die mit `:feedback output … --learn` ausdrücklich freigegebenen Referenzen samt originalem Kontext exportiert. Nach dem Beenden des Chats zeigt `python3 scripts/export_live_output_dataset.py labels` gültige Packet-/Quellen-IDs. Die Befehle für tatsächliche Aufnahme, Zusammenstellung und Shadow-Training stehen in [LIVE_OUTPUT_DATA_EXPORT.md](docs/LIVE_OUTPUT_DATA_EXPORT.md) und [LIVE_OUTPUT_TRAINING.md](docs/LIVE_OUTPUT_TRAINING.md). Aufnahme benötigt den zuvor vorbereiteten Streaming-Build. Alte Adapter werden wegen ihrer anderen Feature-ABI nicht übernommen. Zu wenige Referenzen liefern `INSUFFICIENT_LABELLED_COHORT`; dabei findet kein Training statt. Der bisherige native Exporttest verwendet ausdrücklich verfasste Testreferenzen und belegt keine Verbesserung durch Nutzerfeedback.

Der gespeicherte Entwicklungsstand und die konkreten nächsten Schritte stehen in [CONTINUE.md](docs/CONTINUE.md). Die vollständige Source-ZIP enthält zusätzlich die rohen Proofs und den eingefrorenen Acceptance-Quellstand.

## Nutzerentscheidungen und Schutzregeln (WP-V, 2026-10-09)

- **Eigener B2-Body:** B1 = LFM2.5-1.2B, B2 = Qwen3.5-0.8B (`:download gist`, ca. 563 MB). Messkontrollen nach §85.1 über `b2_control` in `config/settings.json`, Messung mit `python3 scripts/timescale_gate.py --installed-home ~/v13 --out-dir <Ordner>`.
- **Englisch zuerst:** Modell-Prompts in `v13/prompts.py`, `answer_language` = `en` (Standard) oder `de` (Deutsch als späterer Lerntest).
- **Gegen Nachplappern:** `:sampling anti_echo|legacy`, Kollapswächter `:collapse [all]` (auch in `:doctor`), Messung `scripts/measure_anti_echo.py`.
- **Freigabe:** `:approve` prüft zusätzlich die Stabilitätshülle (Update-Norm, Datenmix ≥ 60 % Mensch / ≤ 10 % selbst erzeugt, 2-%-Rückgang auf alten Sets).
- **Bedienung:** `:note 1-10 [Text]` bewertet die letzte Antwort (Lob/Kritik im Chat zählt schwach mit), `:ratings`, `:context` zeigt den letzten Modellkontext, `:pause selfedit|traum|training|budget N` und `:resume <Klasse>` halten Hintergrundarbeit an; eingefügte Terminal-Logs bleiben aus dem späteren Kontext; mehrzeiliges Einfügen bleibt ein Block.
- **Weitere:** `:native` (Fähigkeitsprofil inkl. Body-Train-Port-Vertrag), `:knobs` (Regler mit Typ nach IH-H5). STEP2-Ablationen bewerten jetzt aufgabengebunden (`task_score`).

## Age, Lern-Autorität, Weltmodell und Schlaf (Pakete E, 2026-10-10)

- `:age` zeigt System- und Fähigkeitsstufen; Rechte gelten je Fähigkeit (`docs/AGE_RIGHTS.md`). `:effort` steuert den Denkaufwand.
- `:authority [status|review|promote <Kopf>|demote <Kopf>]` — gelernte Köpfe Schatten → Kandidat → aktiv, aktiv nur mit deiner Freigabe (`docs/LEARNING_AUTHORITY.md`). `:objectives` zeigt die Lernziele (IH-H25).
- `:live [status|ask shadow|ask active]` (Rückfragen bei Unsicherheit), `:neuromod meta shadow|active` (gelernte Metaplastizität).
- Schlaf prüft Traum-Hypothesen gegen gespeicherte Quellen und misst Homöostase mit Gate (`docs/SLEEP_VALIDATION_HOMEOSTASIS.md`); Weltmodell und offene Ziele: `docs/WORLD_MODEL_GOALS.md`.
- `:register [summary|drift|declared|<Präfix>]` — Blueprint-Regler; begründete Abweichungen stehen in `specs/knob-map.json` unter `deviations`.
- Aktueller Gesamtstand und offene Pakete: `ROADMAP.md` und `ABDECKUNG.md` im Projektordner (nicht die älteren Kopf-Felder in `BUILD_STATE.json`).
