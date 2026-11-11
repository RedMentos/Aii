# Integrierter ContextOS-Quellenabruf und ausführbare Testkopie — 2026-11-11

Status: **SHADOW / REVIEW ONLY**, auf PR #1716, Ausgangspunkt `ebf32205d91d0b1f2cdb097b193d72a0cd023f76`. Keine Änderung der eingefrorenen Runtime-Quellen, keine Produktivpromotion. Der vorhandene Blueprint für geschichteten Langzeitkontext bleibt maßgeblich; diese Arbeit schließt eine konkrete fehlende Verbraucherschnittstelle.

## Tatsächlich verbundener Pfad

`scripts/stage_integrated_candidate.py` erzeugt eine separate Kopie aus dem hashgebundenen `integrated_context_recall_candidate_20261111.py`. Dieser baut auf der bisherigen gemeinsamen Feedback-/Archiv-/C3-/Body-/World-Kette auf. Die erzeugte Runtime kann nach ausdrücklicher Aktivierung ältere Quellen aus demselben Chat als begrenzte, überprüfte Ausschnitte in die normalen C3-Nachrichten übernehmen:

`Runtime-Turn → ContextOS ACTIVE + recall on → begrenzte Quellensuche → verifizierter Streaming-Span → SOURCE_LINKS → ContextPlan/C3 → Antwort-Quellenlineage → späterer World-Lernpfad`.

Der Schalter ist standardmäßig aus und pro Chat gespeichert. Er erweitert weder Trainings- noch Werkzeug-/Bildschirmrechte. Befehle in der Testkopie: `:ctxos active`, `:ctxos recall on`, `:ctxos recall status`, `:ctxos recall off`. Pausen, Abbruch und Ressourcenstatus verhindern den Abruf. Eine alte Nutzeraussage erhält ausdrücklich die Kennzeichnung `PAST_USER_STATEMENT_NOT_VERIFIED_FACT`.

Die Suche betrachtet höchstens 128 ältere Nutzernachrichten mit je 4096 Präfixzeichen und vier einfachen ASCII-Suchbegriffen. Ereignishüllen und Nachrichtenmetadaten gelangen nur als jeweils höchstens 16-KiB-Zeichenpräfix plus Überlaufzeichen nach Python; übergroße Hüllen werden verworfen. Bereits aktive Historie wird ausgeschlossen. Höchstens zwei Ausschnitte mit je 256 Zeichen gelangen in eine insgesamt höchstens 1400 Zeichen große serialisierte Schicht einschließlich Quittungen und Kopf. Sie muss zusätzlich in das verbleibende vorhandene ContextOS-Zeichenbudget passen; das normale Tokenfenster wird nicht erhöht. Quellen sind auf 512 KiB beschränkt und werden vor Ausgabe vollständig auf Hash, UTF-8, Größe und Quellenrechte geprüft. Die Suche ist kein universeller semantischer Gedächtnisabruf.

0,25 Sekunden sind ein **kooperatives** Lesezeitbudget. Mutex-Warten wird zeitlich begrenzt, SQLite-Busy-Warten auf das Restbudget beziehungsweise maximal 50 ms gekürzt und anschließend zurückgesetzt. Der Leser prüft Abbruch/Frist während des Streamings und verwirft Teilergebnisse. Ein bereits laufender Betriebssystem-I/O-Aufruf lässt sich dadurch nicht hart unterbrechen. Verschachtelte begrenzte Lesetransaktionen werden abgelehnt, ohne die äußere Transaktion zu beschädigen.

Die Runtime prüft Ereignis-/Chat-/Quellenbindung vor dem Speichern der Kontextnachrichten und nochmals vor dem Modellaufruf. Die wiederhergestellten Quellen werden in ContextPlan und Antwortmetadaten weitergegeben. Ein Test lernt anschließend ausdrücklich nur aus der neuesten T8-Zeile und widerruft danach die ältere erinnerte Quelle: Der World-Pfad verweigert weitere Nutzung. Zwischen letzter Prüfung und Verbraucherbeginn bleibt eine Zeitlücke; nach begonnener Inferenz können bereits gelesene Informationen nicht zurückgerufen werden. Kein sofortiges Entlernen oder vollständiges Löschen aller Ableitungen behauptet.

## Entdeckter Archivfehler und Reparatur

Der erste echte Abruflauf scheiterte unter anderem daran, dass die normale Runtime beim Anlegen einer weiteren Historienreferenz den schon komprimierten Nutzertext erneut als Klartextblob schrieb. Der neue, nur in der Testkopie angeschlossene Text-Publisher verifiziert einen vorhandenen gemeinsamen `.z`-Blob vollständig gegen die erwarteten Bytes und verwendet ihn für kalte Textreferenzen weiter. Beschädigte, abgeschnittene, ausgetauschte oder um Zusatzdaten erweiterte Archive werden abgelehnt. Bilder, heiße `HUMAN_DECISION`-Quellen und unbekannte Quellentypen behalten den bisherigen Klartextpfad. Texte über der bisherigen 64-MiB-Lesergrenze nutzen ebenfalls den bisherigen Pfad.

Das beseitigt die erneute Klartextblob-Erzeugung für diesen geprüften Fall. **`messages.text` bleibt zusätzlich unkomprimiert in SQLite.** Effizient quasi unbegrenzter lokaler Kontext, Gesamtquoten, adaptive Verdichtung und Idle-Konsolidierung sind damit noch nicht fertig.

## Reproduzieren

```bash
python v13/code/scripts/stage_integrated_candidate.py --output /tmp/v13-review-new
cd v13/code
python -m pytest -q -s tests/test_stage_integrated_candidate.py tests/test_integrated_stage_real_smoke.py tests/test_pinned_stage_runtime_e2e_20261111.py tests/test_context_source_recall_stage_20261111.py tests/test_runtime_jepa_utility_integration_20261111.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

Das Ausgabeziel muss neu sein. Der Stager prüft den Builder vor dessen Import, lehnt Quellbaum-/Symlink-/Pfadüberlappungen ab, kopiert keine Datenbanken, Modellgewichte oder Logs und veröffentlicht unter Linux ohne Überschreiben eines konkurrierenden Ziels. Android-Kompatibilität dieser Veröffentlichungsoperation ist nicht nachgewiesen. `INTEGRATION_STAGE.json` enthält die SHA-256 aller anfangs erzeugten Dateien; es ist weder eine Signatur noch Schutz vor späteren lokalen Änderungen. Nachträglich kopierte Tests stehen nicht im ursprünglichen Dateimanifest.

Lokale aktuelle Reviewkopie: `/workspace/shared/v13-integrated-context-review-20261111-v2`, 325 Dateihashes geprüft. Builder-SHA-256: `168d6003db2c871599e70922619cfc416882b137ce05704b5c7b4d35037f6c0f`. Keine echten Nutzerdaten oder aktiven Modellgewichte darin.

## Geschlossene lokale Evidenz

Python 3.12; NumPy 2.2.6; CPU-Torch 2.5.1; Transformers 4.44.2; PEFT 0.13.2. Tatsächliche synthetische SQLite-Runtime-Turns und kleine numerische beziehungsweise Tiny-Torch-Updates, keine nativen Modellantworten und keine Redmi-Messung.

- Aktueller gemeinsamer Staging-Regressionslauf: **374 PASS / 3 CUDA SKIP / 35 Untertests PASS**, ein äußerer Test PASS. Zuvor 371 PASS auf dem früheren Stand mit zwölf Kontextfällen; beide Rohlogs bleiben erhalten.
- Aktueller gezielter Lauf der fünf oben genannten Dateien: **12 äußere Tests PASS**, darin **15 Kontextfälle PASS**, zwei bestehende echte Runtime-Lifecycle-Fälle und der übernommene JEPA-Readback-Fall. Die äußeren Zahlen nicht mit inneren Tests zu einem neuen Gesamtergebnis addieren.
- Kontextfälle: tatsächlicher C3-Nachrichtenverbrauch nach Verdrängung aus `history_turns=1`, Neustart, Chatgrenze, kein Budgetplatz, Pause/Ressourcen, Widerruf vor Modellaufruf, geänderte Ereignis-Chatbindung, Abbruch ohne Teilausgabe, Fristablauf, Mutex/SQLite-Blockade, unbeschädigte äußere Transaktion, Archiv-Wiederverwendung/-Korruption übergroße Ereignishüllen/Metadaten und spätere World-Lineage.
- #1737s übernommener JEPA-Test misst endliche datendisjunkte Holdout-Werte und prüft Readback/Neustart/weiteren Schritt. Er verlangt **keine Verbesserung**, nutzt synthetische Ereignisse und vergleicht ein während des Lernens mitbewegtes Ziel. Die beobachteten Deltas sind kein vorab registrierter Nutzenbeweis.

Unveränderte Rohlogs und Hashes: `proofs/staged-context-20261111/`. Der neue Workflow `.github/workflows/v13-integrated-context-stage-20261111.yml` prüft dieselbe erzeugte Kopie unter Python 3.11, einmal nur NumPy und einmal mit CPU-Torch. Ein remote bestandenes Ergebnis wird erst nach tatsächlichem CI-Abschluss ergänzt.

## Fortsetzen

1. Exakte CI dieses Kandidaten prüfen und Fehler reparieren; Gesamt-RED aus den Originalbranch-Reviews erhalten (`INTEGRATED_STAGE_CROSS_REVIEW_20261111.md`).
2. World-JEPA-Persistenz um den gebundenen Optimizerzustand und einen tatsächlich fortgesetzten Vergleich ergänzen; Holdout-Ziele/Retention getrennt fixieren. Der bisherige Neustart lädt Modell/EMA, erzeugt aber einen neuen Optimizer.
3. Body-JEPA in die reguläre Trainer-/Organ-Auswahl integrieren, danach Replay/Sleep und tatsächlichen langsamen Idle-Import unter Quoten fortsetzen. Vorhandener Datensatzkatalog bleibt 47 Ansichten/35 Repositories, 18 PROBE/29 HOLD, ohne automatischen Download oder Training.
4. Die neue verbindliche Selbstoptimierungsanforderung bleibt zusätzlicher offener Umfang: `../../USER_ADDENDUM_2026-11-11_SELF_OPTIMIZATION.md` und `CROSS_ORGAN_WEIGHT_EDIT_CONTRACT_20261111.md`. Organübergreifende tatsächliche Parameter-Deltas und später kontrolliertes strukturelles Self-Edit werden nicht als Promptoptimierung umdefiniert oder als fertig behauptet.

SourceHandoff-Freeze, Age, STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `canonical_architecture_complete=false` und `user_full_scope_complete=false` bleiben bestehen. Drive-Backup weiterhin technisch durch Quota-403 blockiert; Git-Sicherung und deren überprüfter Remote-Stand sind getrennt zu dokumentieren.
