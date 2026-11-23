# INQUISITION-JEPA / V13 — EINZIGE UEBERGABE AN NEUEN CHAT
Stand der vorhandenen Belege: 2026-10-09, Checkpoint 06:19 UTC. Dieses ZIP ist ein Transportpaket aus frueheren Projektdateien, KEIN Nachweis einer fertigen Implementierung.

## Was du im NEUEN Chat zuerst tun sollst
1. `00_START_HIER/NEUER_CHAT_PROMPT.txt` lesen und die Anweisungen ernst nehmen.
2. `01_BLUEPRINTS/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` ist der kanonische Architektur-/Designstand, ABER aktueller Runtime-Code und `03_WORK_STATUS/BUILD_STATE.json` sind fuer implementierten Zustand massgeblich.
3. `04_PROGRAMM_VERSIONEN/V13-Redmi-Start-20261009-0819.zip` ist das letzte gespeicherte komplette Laufzeit-Quellpaket (3644 ZIP-Eintraege unter `V13-Phone/`). Darin: START_HIER.txt, README.md, Skripte, Tests, Docs/Proofs. Bei Bedarf dieses ZIP entpacken.
4. `03_WORK_STATUS/completion-ledger.json`, `03_WORK_STATUS/USER_DECISIONS_AND_OPEN_QUESTIONS.md` und darin bzw. im neuesten Quellpaket `docs/REMAINING_IMPLEMENTATION.md` konsultieren. Fakten und Belege pruefen statt abgeschlossene Implementierung zu behaupten.
5. `05_WORK_SICHERUNGEN_METADATA/` enthaelt die Original-Restore-Readmes / Manifestinformationen beider alten Work-Huellen. Der gesamte darin verpackte Code ist entweder in `04_PROGRAMM_VERSIONEN/` oder als Delta in `06_AELTERE_QUELL_DIFERENZEN/` erhalten.

## Projektziel
Inquisition-JEPA/V13 ist eine brain-inspirierte kontinuierlich lernende Android-/Termux-Laufzeit mit A-Plane Ingress, Split-Brain B1_DETAIL/B2_GIST, C-Plane JEF/Executive, lokalem Lernen/JEPA-Ziel, EMA, wiederverwendbaren KV-Caches, Sleep/Dream, Routing, Calibration/OOD/Abstinenz und persistenter Chat-UI. KEIN normales Multi-Agent-System, KEINE reine konzeptionelle Blaupause. Vollstaendige Implementierung mit Tests/Proofs ist gefordert. Nicht neuarchitektieren oder Features streichen.

## Wichtiger ehrlicher Zustand (aus BUILD_STATE.json)
- `state: WORK_IN_PROGRESS`; `canonical_architecture_complete: false`; `user_full_scope_complete: false`.
- Gates: `B3_latent: OFF`; `body_JEPA: UNAVAILABLE`; `higher_age: OFF`.
- Letzter gespeicherter Checkpoint: `CAUSAL_NATIVE46_NINTH_EXPORTED_SQLITE_FAILED_BEFORE_FIT`.
- Aktueller offene Blocker: Die 46er native Causal/SQLite-Sammlung scheiterte nach 9 exportierten Zeilen mit fehlerhafter SQLite-DB, VOR Fit und Utility-Validierung. Nur 2-row-Test war positiv, NICHT gleich Qualitätsgewinn.
- Im `BUILD_STATE.json` notiert: 385 aktuelle Regressionstests, 0 Fehler, aber `native_model_calls: false`; kein Ersatz fuer reale Phone-/native-Tests.
- Keine bewiesene komplette native JEPA-Lernimplementierung behaupten. STEP2 Utility, native Body/Sparse/B3, Retention, echte Redmi-Telemetrie sind noch zu pruefen.

## Historische Pakete und Groesse
Die Originalbibliothek enthielt identische ZIP-Dubletten sowie Work-Huellen, die dieselbe grosse Runtime nochmals verschachtelten. Um unter typischen Uploadlimits zu bleiben, hat dieses EINE ZIP alle unterschiedlichen Projektdaten ohne redundante Verpackungsbytes. Das fruehere 149-MB-Runtime-Paket war bzgl. Dateipfaden komplett in der neuesten Runtime enthalten; seine 28 abweichenden Dateiinhalte sind einzeln in `06_AELTERE_QUELL_DIFERENZEN/` abgelegt. Das History-Delta ist fuer Quellinhalt verlustfrei, aber rekonstruiert NICHT die exakten historischen ZIP-Komprimierungsmetadaten / binaeren Archivbytes. Siehe `ARCHIV_ALIASE_UND_VOLLSTAENDIGKEIT.json`.

## Empfehlung
Als Start in neuem Chat DIESES EINE ZIP anhaengen und die Erstnachricht aus `00_START_HIER/NEUER_CHAT_PROMPT.txt` verwenden. Fuer Entwicklung die aktuelle Codebasis entpacken, SHA/manifeste pruefen, STEP0/1/2 und vorhandene Tests korrekt weiterfuehren. Nicht nur Bugs/Diagnostik; die gesamte offene Funktionsabdeckung bearbeiten.
