# V13 Code- und Doku-Audit (nur lesend)

Stand: 2026-10-09, 12:30–12:48 UTC. Grundlage ist `/mnt/project-files/v13/code` plus eine Kopie für vulture/pyflakes/unittest.
Andere Threads ändern parallel Dateien. Während des Audits kamen `v13/sleep.py`, `v13/scheduler.py`, `scripts/cloud_bench.sh`, `scripts/cloud_candidates.py` und zwei Tests hinzu. Einzelne Punkte können deshalb schon erledigt sein.
Unit-Suite in der Kopie (`PYTHONPATH=.:tests`, entspricht `v13 selftest`): **425/425 OK** (81 s). Ohne `tests` im Pfad scheitern 6 Module am Import, weil sich Tests gegenseitig über den bloßen Namen importieren.

Konfidenz: **H** = per grep/Lauf belegt, **M** = wahrscheinlich, **N** = Vermutung.

---

## 1. Toter Code und Aufräumkandidaten

**Vorab wichtig:** `scripts/verify_acceptance.py:24-29` (`harness_hashes`) hasht alle `.py/.sh/.cpp/.json` unter `scripts/`, `tests/`, `specs/` und `*.sh`. `scripts/acceptance.py:26,102` hasht `v13/*.py`.
**Jedes Löschen oder Aufräumen macht ein laufendes `TESTEN.sh --resume` der Working-Source ungültig.** Den eingefrorenen Acceptance-Stand betrifft das nicht, er liegt als eigenes Archiv vor. Aufräumen deshalb nur gebündelt in einem eigenen Commit, wenn kein Resume aktiv ist.
Viele Skripte sind zudem namentlich in Proof-Manifesten gebunden, zum Beispiel `docs/proofs/acceptance-*-verified-index-20261009.json`. Die Proofs bleiben historisch gültig, aber die Dateien sollten archiviert und nicht spurlos gelöscht werden.

### 1a. Duplikate der Statusdateien (H)
| Datei | root `code/` | `code/docs/` | `status/` | Befund |
|---|---|---|---|---|
| BUILD_STATE.json | md5 11ae… | 11ae… | 11ae… | identisch (3 Kopien) |
| completion-ledger.json | **8d50…** | b176… | b176… | **root ist veraltet**: Einträge `causal_lifecycle_recovery_resume_oct9`, `recorded_causal_export_oct9` und `current_regressions_resume_oct9` fehlen dort (diff ab Zeile 1791) |
| USER_DECISIONS_AND_OPEN_QUESTIONS.md | **36 Zeilen** | 94 Zeilen | = docs | **root ist veraltet**: Zeile 10 sagt noch „STEP2 semantic utility needs validated scoring“, docs Zeile 10 dagegen „has a fixed structured scorer“ |

Kanonisch ist laut `scripts/checkpoint_work_phase.py:68,79-85`: BUILD_STATE wird nach root und docs geschrieben, Ledger und Decisions nur nach `docs/`.
Vorschlag:
- root `completion-ledger.json` und root `USER_DECISIONS_AND_OPEN_QUESTIONS.md` löschen oder durch einen Verweis ersetzen.
- Bei `status/` festlegen, ob es ein Spiegel ist; wenn ja, automatisch kopieren.

### 1b. Ungenutzte Module, Funktionen und Skripte
| Kandidat | Befund | Konf. |
|---|---|---|
| `docs/drafts/control_calibration_worker.py` + `docs/drafts/README.md` | Laut README selbst „historical draft, not imported“. Weicht von `v13/control_calibration_worker.py` ab (ältere Validierung). Keine Referenz. | H |
| `docs/resume_acceptance.py`, `docs/check_resume_acceptance.py` | Altes Resume-Tool für den 21-Stufen-Plan. Wird nur gegenseitig referenziert, von keinem `.sh`, Skript oder Test. Ersetzt durch `scripts/acceptance.py --resume` + `acceptance_checkpoint.py`. Python-Code gehört ohnehin nicht nach `docs/`. | M-H |
| `scripts/checkpoint_step2_progress.py` | Keine Referenz. Setzt einen externen „upload helper“ der alten ChatGPT-Work-Umgebung voraus. | H |
| `scripts/compare_causal_runtime_decoder.py` | Keine Referenz außer Proofs. Einmaliger Decoder-Abgleich (erledigt laut USER_DECISIONS:79). | M |
| `scripts/test_live_output_adapter_port.py` | Keine Referenz außer Proofs. 4-Token-Client, durch `test_native_prefill_stream.py` und STARTEN_CAUSAL abgelöst. | M |
| `scripts/test_live_output_export_native.py` | Keine Referenz außer Proofs. Einmaliger TEST_OPERATOR-Lebenszyklus. | M |
| `scripts/test_native_midlayer_numeric_policy.py` | Keine Referenz. Guard-Skript ohne Aufrufer. | M |
| `v13/effort.py:147 compare()` | Nirgends aufgerufen. Gedacht für §24.23, aber ohne Runner. Mutabler Default-Parameter. | H |
| `v13/causal_output.py:20 source_revision()` | Nirgends aufgerufen. | H |
| `v13/age.py:15 STAGES`, `age.py:139 open_window`, `:168 gist_resolution` | Nur in `tests/test_age.py` genutzt. Age wirkt also noch nicht auf Gist-Auflösung oder Plastizität in cognition/learning. | H |
| `v13/utility.py` | Kein v13-Import, nur `tests/test_step2_utility.py` + `tests/integration_step2_utility.py` (über TESTEN_STEP2.sh). **Nicht tot**, gehört aber eher zu `tests/`/`scripts/`. | H |
| pyflakes | 16 ungenutzte Importe in `v13/` (z. B. `verification.py:1,3,6`, `__main__.py:3,8`, `learning_worker.py:5,10`, `retrieval_worker.py:11`). Die fünf `numpy`-Importe in `learning.py:470…758` sind wohl bewusste Verfügbarkeitsprüfungen. Dazu 37 in `tests/` und `scripts/`. | H |
| Lose Dateien in `docs/` | `checkpoint-test-status.txt` („52/52 UNIT PASS“), `step12-unit-tests.txt`, `native-probe-linux.json`, `real-integration.json`, `retrieval-native-doctor-20261001.json`: nirgends referenziert, veraltete Momentaufnahmen. Gehören nach `docs/proofs/` oder weg. `logging-policy.json` und `schema-registry.json` werden genutzt (verification.py). | H |
| `__pycache__/` in `v13/`, `scripts/`, `tests/` | Liegen im Projektordner. `package_source.py` schließt sie aus, aber `.gitignore` oder Aufräumen fehlt. | H |
| `start/NEUER_CHAT_PROMPT.txt` | **0 Bytes**, obwohl `start/README_ZUERST.md:4` sagt: „zuerst lesen“. | H |

### 1c. TESTEN_*.sh
- 7 der 8 `TESTEN_NATIVE_*.sh` und `TESTEN_LONG.sh` sind byte-gleiche Wrapper, die sich nur im Skriptnamen unterscheiden.
  - Ein Dispatcher wie `TESTEN.sh native <port|session|stream|train|receiver|midlayer>` würde 7 Dateien ersetzen. (M)
  - Alle sind noch in `INSTALL_ZIP.md:21-27` dokumentiert. Nicht ersatzlos löschen.
- Inhaltlich überholt (M):
  - `TESTEN_NATIVE_PORT.sh` (Observer-Paritätstest, abgeschlossen)
  - `TESTEN_NATIVE_SESSION.sh` (4-Token-Pause/Resume, abgelöst durch STREAM)
  - Beide sind reine Diagnose. Sinnvoll wäre, sie nach `scripts/diagnostics/` zu verschieben.
- `TESTEN_NATIVE_TRAIN.sh` ruft `test_native_norm_shadow.py` auf. Der Name verspricht Training; es ist eine Norm-Shadow-Diagnose mit Ergebnis EVALUATED_FAIL. Irreführend. (M)

### 1d. Veraltete Doku (beschreibt nicht mehr gültige Zustände)
- `docs/RESUME.md`: 149 Zeilen gestapelter Wiederaufnahmepunkte vom 23.09. bis 01.10. Die neueste Überschrift (Zeile 1) ist vom **01.10.** („119 units PASS“).
  - README:77 verweist trotzdem darauf als Fortsetzungsdoku. Tatsächlich aktuell ist `docs/CONTINUE.md`, das `checkpoint_work_phase.py:92` automatisch erzeugt. (H)
- `docs/ACTIVE_WORK_20260929.md`, `docs/RECOVERY_20261007.md`, `docs/AUDIT_RULES_LATENCY_COUPLING_20261007.md`, `docs/NATIVE_*_2026100x.md`: datierte Arbeitsnotizen. Gehören nach `docs/history/`. (M)
- `START_HIER.txt:10-12`: Zielordner `v13-app-20260929` und ZIP-Name `V13-Redmi-Start.zip`. Harmlos, aber datiert. (N)

---

## 2. Widersprüche

### 2a. Dokument gegen Dokument
1. **Acceptance-Stand: 18/21, 6/20, 3/20 oder 2/20?**
   - `docs/BUILD_STATE.json:184` `tests.acceptance_current` = „18/21 PASS …“ (Stand 06.10.).
   - `docs/CONTINUE.md:80-99` = 6/20 `DIAGNOSTIC_INCOMPLETE`.
   - `docs/USER_DECISIONS…:62` „overall2/20“, `:64` „3/20“, `:73` „remains3/20“, `:75` „4/20“, `:77` „6/20“: ein chronologisches Log, aber Zeile 73 im Block „Causal-live labelled export“ wirkt wie der aktuelle Stand.
   - Erklärung (H): `scripts/acceptance.py:42-53` hat 20 Stufen, mit `--compare-c3` 21. Die 18/21 sind ein alter Working-Source-Lauf, die 6/20 der eingefrorene Neustart. Das steht nirgends klar.
   - `docs/CONTINUE.md:96` nennt `frozen_app_directory …acceptance-20261009-2of20`, und `:93/:96` zeigen auf nicht mehr existierende `/workspace/scratch/...`-Pfade.
2. **`docs/completion-ledger.json:1736` `current_acceptance`** = 16 Stufen, „119/119 units“ (01.10.). Trägt trotzdem den Namen „current“. (H)
3. **Ledger widerspricht sich selbst:**
   - `:1787 causal_learned_output_lifecycle_oct9` = `IN_PROGRESS_CODE_COMPILES, new_lifecycle_guards_complete:false`.
   - `:1793 causal_lifecycle_recovery_resume_oct9` = `RECOVERED_FINAL_SOFTWARE_PASS, lifecycle_tests 9`.
   - Der alte Eintrag wurde nicht geschlossen. (H)
4. **BUILD_STATE-Kopfdaten sind veraltet** (H):
   - `completed_this_run` (Zeile 3) beschreibt einen Lauf aus der auto-burst-Zeit („Expanded regression suite to 42/42 PASS“).
   - `base_checkpoint` = `V13-Redmi-Start-auto-burst2.zip` (Zeile 252). Tatsächlich ist es ZIP 60.
   - `tests.unit_download` = „65/65“ (Zeile 159).
   - `next_priority[1]` = „STEP2 validated semantic complementary-utility scoring“ (Zeile 150 ff.). Das ist erledigt: Der Scorer ist fixiert, 70/70 strukturell, `UTILITY_FAIL`.
5. **Testanzahl:**
   - BUILD_STATE `current_working_source_regressions` = 385.
   - `diagnose/unit-tests-after-guard` = 401.
   - ROADMAP:106 = 425, ROADMAP:124 = 427.
   - Mein Lauf: 425.
   - `status/` ist seit dem 06:19-Checkpoint nicht nachgezogen.
6. **REMAINING_IMPLEMENTATION.md** (H):
   - Titel „Verbindlicher Restumfang — 2026-09-29“, danach Abschnitte bis 09.10. angehängt.
   - In der Spalte „Tatsächlich noch fehlend“ stehen erledigte Punkte („…jetzt implementiert“: Zeilen 8, 11, 13, 16, 17).
   - Zeile 54 („Restart isolation and a separate corrected attempt are required“) ist durch Zeile 62 (70/70 komplett) überholt.
   - Zeile 64 („sein neuer Client-Nachweis ist noch offen“) ist überholt durch `CONTINUE.md:54` `LIVE_OUTPUT_CLIENT_ZERO_PASS`.
   - **Der aktuelle Blocker (SQLite-Fehler nach 9/46) fehlt in dieser Datei vollständig.**
7. **USER_DECISIONS: Abschnittsköpfe gegen Inhalt.** `USER_DECISION_REQUIRED: None` (Zeile 5), obwohl mehrere Punkte nur der Nutzer erledigen kann: echte Labels, Redmi-Lauf. Siehe Abschnitt 3. Der SQLite-Blocker steht nur in der Prosa (Zeile 94), nicht unter `HARD_BLOCKER`.
8. **ROADMAP intern:**
   - Zeile 38 „Querschnitt ohne Code: Adaptive Reasoning Effort, Age-Stufenlogik (heute hart auf 0), Sleep/Event-Scheduler“.
   - Dagegen: WP-C und WP-D sind „ERLEDIGT“ (Zeilen 101, 118), `v13/effort.py` ist in `runtime.py:266-273` verdrahtet, und `sleep.py`/`scheduler.py` entstehen gerade.
   - Zeile 24 „36 Module“ ist nicht mehr aktuell.
9. **`start/README_ZUERST.md:43`** „385 Regressionstests“ und `:42` „Blocker SQLite“. Der neue Befund `diagnose/SQLITE_NATIVE46_BEFUND.md` (Ursache vermutlich Umgebung, nicht V13-Code) ist weder in BUILD_STATE noch im Ledger nachgetragen.

### 2b. Dokument gegen Code
1. **README:44** empfiehlt für STEP2 `tests/integration_step2.py` (alte Ablation mit „Zahlenvorkommen“). Der aktuelle, vorregistrierte Pfad ist `TESTEN_STEP2.sh` → `tests/integration_step2_utility.py`. Im README fehlt er. (H)
2. **README erwähnt `:age`, `:effort`, `:stage cap`, `:capability` nicht.** In `v13/operator.py:28,35,123-124` existieren sie. (H)
3. **README:78** behauptet, `WORKSPACE_FILES.json` liege bei. Es entsteht nur beim Packen (`scripts/package_source.py:42`) und fehlt im Arbeitsbaum. (H, harmlos)
4. **ROADMAP:88 (WP-A)** „`v13/store.py` + Collector: Integritätscheck nach jedem Close“. Das stimmt nur für den Collector:
   - `store.audit_closed()` (store.py:~199) wird ausschließlich von `tests/integration_causal_output_lifecycle.py:136` und `tests/test_sqlite_close_audit.py` aufgerufen.
   - `Store.close()` (store.py:564-570) prüft keine Integrität und wertet das Busy-Flag von `wal_checkpoint(TRUNCATE)` nicht aus.
   - Für den Produktivpfad ist die Aussage deshalb zu stark. (H)
5. **Ledger-Zeilen decken den Code nicht ab.** `docs/completion-ledger.json` `rows[*].implementation_files` nennen 19 Module nirgends:
   - age, effort, causal_output, causal_prepare, consolidation, executive, output_adapter_worker, output_policy, plasticity, pressure, retrieval_worker, history, backup, bootstrap, utility, ui und weitere.
   - Die README beschreibt für viele davon fertige Features: C1 Executive, C5/F6 Fixed Policy, Konsolidierung, F7, C3-Output-Adapter, Retrieval-Head.
   - Die ROADMAP-Zählung „4 PASS / 15 PARTIAL“ bezieht sich deshalb nur auf 21 ältere Zeilen. Laut ROADMAP:124 ist inzwischen eine G5B-Zeile dazugekommen. (H)
6. **31 von 168 in Doku/BUILD_STATE/Ledger referenzierten `docs/proofs/...`-Pfade fehlen** (geprüft gegen /mnt, 12:40). Beispiele:
   - `causal-output-lifecycle-20261009/native46-failed-report.json` (gehört direkt zum aktuellen Blocker)
   - `…/source-phase3-final.zip`
   - `acceptance-frozen-source-20261009.tar.gz` (CONTINUE:97 nennt es als eingefrorene Quelle!)
   - `step2-final-native-evening-20261008.json` (CONTINUE:27, nur .log/.checkpoint vorhanden)
   - `memory-retrieval-*-20261001.json` (4×) und `control-calibration-native-*-20261001.json` (3×)
   - Zusätzlich verweist `docs/proofs/sqlite-native46-diagnosis-20261009/report.json` auf `checkpoint65-first8.sqlite3` im selben Ordner; dort fehlt die Datei.
   - Die ZIPs wurden vermutlich fürs Kompaktpaket entfernt. Dann sollte die Doku das sagen, statt die Pfade als vorhanden darzustellen. (H)
7. `INSTALL_ZIP.md:24` `--max-tokens 64` passt (`test_native_prefill_stream.py:89`). Kanon-SHA in `specs/component-contracts.json` = Datei in `docs/canon` = `blueprint/` (3423906b…). Alle Code-Pfade in specs und Ledger existieren. (H, ok)

---

## 3. Offene Nutzerentscheidungen und Fragen über die Historie

Quellen:
- `x/01_BLUEPRINTS/USER_DECISIONS*` (burst2, run3, auto-burst5, 20261006-burst3…5, 20261009-0819)
- BUILD_STATE-Varianten
- `user_addition_*` in BUILD_STATE

### Beantwortet bzw. erledigt
| Frage/Blocker (zuerst gesehen) | Ergebnis |
|---|---|
| C3 SmolLM2 gegen LFM2.5 (run3: „candidate GGUF + paired scoring required“) | Gepaarter nativer 4+4-Vergleich ist komplett, ohne Promotion. Offen bleiben breitere deutsche Qualität und Phone-Latenz. |
| STEP2 „validated scoring set“ (run3, auto-burst5) | Scorer vorregistriert, 70/70 strukturell, **UTILITY_FAIL** (B1 0,59 > Kombination 0,525). Als Mess-Frage beantwortet, als Architekturfrage offen. |
| Expanded STEP3 real-weight family braucht Model-Caches (run3) | Linux-Lauf erledigt (FAMILY_CHECKS_PASS). |
| Nutzerwunsch 07.10.: Modell-Workspace und Android-Klicks | Beantwortet (BUILD_STATE `user_addition_20261007`): Termux-Privatordner ohne APK, App-übergreifende Klicks nur über einen Accessibility-Begleiter. **Nicht umgesetzt**, „zukünftiger C6/C7-Pfad“. |
| Nutzerwunsch 07.10.: Sicherheit | Teilweise: Fixed Policy C5/F6 und sichere Unicode-Anzeige sind umgesetzt. Ein neuronaler Semantik-Prüfer fehlt (`whole_answer_neural_semantic_regulator:false`). |
| „TinyAGI / mini AGI“-Hinweis des Nutzers | Recherche `docs/research/TINYAGI_REFERENCES_20261009.md` (drei Projekte unterschieden, keine Übernahme). Die ROADMAP („Vorschläge aus Forschung“, WP-S1…S8) greift Forschungsrichtungen auf. |

### Weiterhin offen (Nutzer muss handeln oder entscheiden)
1. **Aktueller Redmi-Lauf** (`TESTEN.sh --compare-c3`, `TESTEN_LONG.sh`): Thermik, Energie, RSS/KV. Seit burst2 offen. Nur der Nutzer kann ihn ausführen.
2. **Echte Nutzer-Labels für den Output-Lernpfad.** Alle bisherigen Labels sind „authored TEST_OPERATOR“, der Trainer meldet `INSUFFICIENT_LABELLED_COHORT`. Das ist faktisch eine Nutzeraufgabe (≥32 Kontexte, ≥12 Route-Beispiele usw.), steht aber nicht unter `USER_DECISION_REQUIRED`.
3. **Echte Freigaben** (`:approve`) bleiben bewusst manuell. Es gibt keinen dokumentierten Plan, wann der Nutzer welche Kandidaten prüft.
4. **SQLite-46er-Lauf:** Muss er wiederholt werden, in der Cloud (WP-B) oder auf dem Redmi? Wenn der Befund „Umgebung“ akzeptiert wird, braucht es eine Freigabe für einen neuen, quellgebundenen 46er-Lauf. Laut `start/README_RESTORE_FIRST.md:13` war „nicht still neu laufen lassen“ die Regel.
5. **STEP2 UTILITY_FAIL:** Architekturentscheidung offen. B1/B2 sind dasselbe LFM2.5-1.2B (ROADMAP:32), also stellt sich die Frage nach einem anderen Gist-Body oder Modell (WP-G/WP-S1). Die SSOT sagt „keine Redesigns“, der Nutzer müsste das abwägen.

### Zwischen Versionen verloren gegangen
- **MobileMoE-S-QAT-Zugang (HTTP 401)**:
  - War `HARD_BLOCKER` in USER_DECISIONS-auto-burst5. In späteren USER_DECISIONS fehlt er.
  - Er lebt nur noch in `REMAINING_IMPLEMENTATION.md:33` und `docs/research/mobilemoe-access-20260929.json`.
  - Offen ist, ob der Nutzer einen Zugang beantragt oder einen Ersatz will (ROADMAP: „MobileMoE nicht zugänglich“).
- **Alter Redmi-`DEADLINE` (Chat-Abbrüche auf dem Telefon)**:
  - War in burst2 und run3 explizit als Rerun-Blocker geführt.
  - Seit den Oct-06-Versionen steht er nicht mehr in USER_DECISIONS, nur noch in BUILD_STATE `tests.target_phone` und README:71-72.
  - Ursache und Fix sind unbewiesen.
- **„Native Body train-port contract / TrainRunnerProof“** (burst5-HARD_BLOCKER):
  - Der Code existiert weiterhin (`contracts.py`, `learning.py`, `scripts/audit_native_ports.py`).
  - In den heutigen USER_DECISIONS ist er auf „capabilities not present“ verkürzt. Was konkret fehlt, steht nicht mehr da: Master, Runner, Requantizer, Revisionsbindung.
- **Nutzer-Notiz in BUILD_STATE.note:** „User explicitly requires complete plan and additions … not only diagnostics.“ Das steht in keiner USER_DECISIONS-Datei. Es ist die zentrale Nutzervorgabe und sollte dort oben stehen.
- **Ältere Prototyp-Linien** (`inquisition_rsi_prototype.zip`, `V13_Hemisphere_Brain_Prototype.zip`, `V13_TRUE_ARCHITECTURE_v2.zip`, `V13_Combined_v3_FINAL.zip`, `V13_Termux_v11.zip`): Ob dort Funktionen stecken, die in V13-Phone fehlen, **wurde nicht geprüft**. Das wäre ein eigener Abgleich (N).

---

## 4. Code-Smells mit Relevanz für Korrektheit (Top 15)

Vorweg: Es gibt keine nackten `except:` und keine `assert` im Produktcode. Transaktionen laufen über `Store.tx()` mit RLock und `BEGIN IMMEDIATE`. Die Fehlerbehandlung ist insgesamt bewusst gebaut. Die folgenden Punkte sind deshalb echte, aber begrenzte Risiken.

1. **`Store.close()` ignoriert das Busy-Ergebnis von `wal_checkpoint(TRUNCATE)`** (store.py:569). Der Kommentar weiß das, ausgewertet wird es nicht. Es gibt auch keinen Integritätscheck beim Schließen im Produktivpfad. Relevant für den 46er-SQLite-Befund. (H)
2. **Breites `except Exception` → nur Klassenname als Fallback-Grund** in `learning.py:70, 231, 330, 458`, z. B. `reason=type(exc).__name__`. Ein Programmierfehler (KeyError, TypeError) im Retrieval-, Calibration- oder Output-Pfad wird zu einem stillen „Fallback“ ohne Meldung und Traceback. Das maskiert Bugs als „nicht unterstützt“. (H)
3. **`runtime.py:213`**: Jeder Fehler im C2-Kontrollpfad wird zu `info['control_unavailable']`, und die Route bleibt still bei `simple`. Gleiches Muster bei `runtime.py:283` (offer_rejected) und `:291` (reentry_failed). Nur gekürzte Strings, kein Zähler, kein `:doctor`-Signal. (H)
4. **`cognition.py:27, 95` und `world.py:49, 75`**: Bei Student-, Predictor- oder World-Fehlern wird nur `type(exc).__name__` geloggt. Die Ursache ist hinterher nicht rekonstruierbar. (H)
5. **`learning.py:25-27`**: Ein `except Exception: pass` in einem Exception-Handler verschluckt sogar das Logging der verzögerten F7-Beobachtung. Laut Kommentar repariert der Restart das, aber es gibt keinen Test, der genau diesen Pfad abdeckt. (M)
6. **Extrem dichte Zeilen**:
   - 1 470 von 6 861 Zeilen in `v13/` sind länger als 120 Zeichen; Rekord `verification.py:100` mit 1 302 Zeichen.
   - Weitere Stellen mit mehr als 600 Zeichen: `proofs.py:62`, `output_adapter_worker.py:154`, `executive.py:99`, `pressure.py:64`.
   - `learning.py` enthält 368 Semikolons.
   - Folgen: Review und Diffs sind fehleranfällig, Tracebacks zeigen auf Zeilen mit 10+ Anweisungen, Merge-Konflikte unter parallelen Threads sind wahrscheinlich. (H)
7. **Acceptance-Resume bindet Hashes über alle Skripte und Tests** (verify_acceptance.py:24-29). Jeder Parallel-Commit (auch Kosmetik) bricht ein laufendes Resume. Das ist korrekt fail-closed, aber unter mehreren gleichzeitigen Threads praktisch nicht nutzbar, solange es keinen eingefrorenen Arbeitsbaum je Lauf gibt. (H)
8. **Tests importieren sich gegenseitig über den bloßen Modulnamen**, z. B. `test_live_output_export` → `test_live_output_training` → `test_output_adapter`. Das funktioniert nur mit `tests/` in `sys.path`; `python -m unittest discover -s tests` scheitert (6 ImportErrors). Gemeinsame Fixtures gehören in ein Helper-Modul. (H)
9. **Daemon-Threads ohne Join** (`pressure.py:57`, `runners.py:91, 118, 159, 201`, `runtime.py:43`). Daemon-Watcher können beim Interpreter-Ende mitten in einer Store-Operation sterben. Bei Store über RLock nur dann kritisch, wenn ein Watcher selbst schreibt. Nicht verifiziert. (N)
10. **`pressure.py:48`**: Unerwartete Observer-Fehler zählen nur `failures+=1`. Fällt der Watcher dauerhaft aus, fehlt der Ressourcen-Abbruch (Thermal/Memory). Ob `failures` irgendwo zu einem Fail-Closed führt, ist nicht erkennbar. (M)
11. **`effort.compare()`** hat einen mutablen Default-Parameter (effort.py:147). Er wird nicht mutiert, ist aber auch ungenutzt (siehe 1b). (H, gering)
12. **Doppelte Rolle von `store.audit_closed()`**: Es öffnet `mode=ro` auf einer WAL-DB. Bei vorhandener `-shm` kann ein Read-only-Öffnen je nach SQLite-Version die Sidecars anfassen. Für eine Beweisprobe wäre `immutable=1` auf einer Kopie sauberer, wie es `docs/proofs/sqlite-native46-diagnosis-20261009/audit_immutable.py` bereits tut. (M)
13. **Hart kodierte BOOT-Schwellen verstreut** (z. B. `runtime.py:209` `calibrated_confidence<.6`, Gains in effort.py, Ratios in age.py). Ein Teil liegt in `config.py`, ein Teil in Literalen. Dadurch ist schwer belegbar, dass „keine Gates retuned“ wurden. (M)
14. **`causal_output.py` und `runners.py` haben kaum Fehlerkontext**: `runners.py:64` verschluckt `OSError/RuntimeError/HTTPException/JSONDecodeError` beim Health-Poll (gewollt). Bei Startfehlern sieht der Nutzer deshalb nur einen Timeout statt der Ursache. (M)
15. **Teile der Ledger- und BUILD_STATE-Pflege sind Handarbeit** (siehe Abschnitt 2). `checkpoint_work_phase.py` erzeugt nur CONTINUE.md und BUILD_STATE-Kopien. Ledger-Zeilen, USER_DECISIONS und REMAINING werden von Hand angehängt, daher die Drift. Kein Code-Bug, aber die Hauptursache der Widersprüche. (H)

---

## Empfohlene Reihenfolge (klein und risikoarm)

1. **Statusdateien:**
   - root-Ledger und root-USER_DECISIONS entfernen oder als Verweis anlegen.
   - `status/` als automatischen Spiegel festlegen.
   - BUILD_STATE-Kopf (`completed_this_run`, `base_checkpoint`, `next_priority`, `tests.acceptance_current`) und Ledger `current_acceptance` korrigieren.
   - SQLite-Befund und die 425 Tests nachtragen.
2. **USER_DECISIONS** neu gliedern:
   - Nutzeraufgaben unter `USER_DECISION_REQUIRED`: Redmi-Lauf, echte Labels, 46er-Rerun-Freigabe, STEP2-Modellfrage, MobileMoE-Zugang.
   - Das Datums-Log in einen eigenen Abschnitt „Verlauf“.
3. **REMAINING_IMPLEMENTATION**: Tabelle bereinigen (Erledigtes raus aus „fehlend“), aktuellen Blocker aufnehmen.
4. **README**: STEP2-Abschnitt auf `TESTEN_STEP2.sh` umstellen, `:age`/`:effort` ergänzen, `RESUME.md` als historisch kennzeichnen.
5. **Aufräum-Commit**, wenn kein Resume läuft: drafts/, docs/*resume_acceptance*.py, lose docs/*.txt/*.json, 5 unreferenzierte Skripte → `archive/`; ungenutzte Importe; `__pycache__`.
6. `Store.close()`: Busy-Ergebnis des Checkpoints auswerten und loggen. Breite `except` in learning.py/runtime.py so ändern, dass Meldung und Traceback in die Telemetrie gehen und nicht nur der Klassenname.
