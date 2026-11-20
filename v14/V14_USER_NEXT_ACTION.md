# V14 — letzte verifizierte Entwicklung / nächstes sinnvolles Nutzer-Update

**Stand:** 21. November 2026. **Zuständig:** V14 Boss & Integration.  
**Zweck:** Bei der nächsten V14-Frage diese Datei, Board, aktuellen GitHub-HEAD und offene PRs abgleichen. Kein automatischer Push ans Handy.

## Letzter gesicherter Gesamtstand

- Release-Arbeitsbranch gpt6/v13-private-remote-bridge-20261111: letzter verifizierter HEAD 14d7386484dfce6728aa404d89eae98403b4dba0. Dieser Stand ist keine neue Redmi-Installationsbestätigung.
- V14-Kandidat PR #2130, Branch boss/v14-temporal-outcome-semantics-20261120. Code-/Test-Checkpoint a24bc46700cc59bd6059c383ba8efb5f5fafa2fe; aktueller Branch-HEAD nach Live-Coverage- und Real-Store-Test-Update wird beim Readback verifiziert. Base 14d7386484dfce6728aa404d89eae98403b4dba0. PR bleibt DRAFT / NOT MERGED / NOT RELEASED.
- Neue Kandidatenfunktion: t8_store_authority.py bindet vom vorhandenen world_model.transitions() zugelassene T8-Zeilen zusätzlich an Event-Quelle, CorollaryCopy, genau ein passendes ActionOutcome und Store.read_source()-Hashprüfung. Ein getypter VerifiedT8Transition ersetzt das frei gesetzte trusted=True im Temporal-Bridge-API. Der Python-Issuer ist eine In-Process-Vertragsgrenze, kein Schutz vor beliebigem Code im selben Prozess.
- Temporal-Outcome- und Scalar-Readout-Dateien serialisieren Schreibtransaktionen pro Datei über fcntl.flock, laden den neuesten Stand innerhalb des Locks neu, schreiben atomar und synchronisieren Datei + Verzeichnis. Das behebt den von QA reproduzierten Lost-Update-Fehler bei mehreren veralteten Instanzen.
- Lokale Tests auf LOCAL_LINUX / CPython 3.13.5: python -m pytest -q v14/learning — 29 passed; py_compile — 5 Dateien PASS. Vier fork-Deprecation-Warnungen aus Multiprozess-Regressionen.
- Tests sind isoliert/synthetisch: FakeStore und gepatchtes world_model.transitions(). Der neue echte SQLite-Store-/ActionSelection-/CorollaryCopy-/ActionOutcome-Integrationstest wurde hinzugefügt, aber noch nicht durch GitHub-CI ausgeführt. Keine Runtime-Verkabelung und kein Redmi-Test. GitHub-CI für den neuen Kandidatenstand hat bisher keinen Run geliefert.
- TemporalReadout bleibt standardmäßig learning_enabled=False; numerische Deltas wurden nur in isolierten Tests mit beiden expliziten Gates geprüft. Das ist ein kleiner Scalar-Readout, keine JEPA-Repräsentation und keine B1/B2-Modellgewichtsänderung.

## Whole-Canon / Capability ledger

Die vollständige additive Statusmatrix steht in V14_CANON_COVERAGE_INDEX.md unter “Boss live evidence overlay — 2026-11-21”. Sie hält A0–A5, B1/B2/B3, C/JEF/C3, World/Self/Memory, JEPA, Sleep/Dream/Replay, Tools, Android Background/UI, VOICE_AUDIO, Self-Optimization, Age/X10, Remote Maintenance und Model Registry getrennt. Kein Track ist als ACCEPTED markiert.

## Weitere geprüfte PR-Blocker

- PR #2131 (Core exact arithmetic, HEAD 3e7876400fbbf68be8ac252b40ebe0a92019bbf8): Arithmetic-spezifischer Workflow PASS, aber safe-additive policy FAIL und staged context/integrated regression FAIL. Builtin arithmetic wird fälschlich als APPROVED_FIXED_RULE markiert, exact_policy_matched für nicht-menschliche Regeln gesetzt, und World validiert manipulierte Outcomes nicht durch Source-Recompute. Review-Kommentar auf #2131. Kein Merge.
- PR #2129 (FastForward latency gate): integrierte Regression laut QA-Run rot; synthetischer predicted_fast_s-Wert beweist keinen gemessenen Fastpath-Nutzen. Review-Kommentar. Kein Merge.
- PR #2124/#2126/#2127 (RAW EAR → A5 → A4): Producer/Receiver-Schema uneinheitlich; A4 muss aktuelle Consent-Receipt prüfen. #2127 ändert eingefrorene Runtime-Datei und hat einen reproduzierten rms=None TypeError. Review-Kommentare. Kein Merge.
- PR #2119/#2108 (Android companion/capability): nur Receipt-Verifier bzw. Simulation; keine OS-authentifizierte lokale Zustimmung, kein nativer Executor, keine Android-Verifikation; Basen teils veraltet. Kein Merge.
- PR #2106/#2110/#2113/#2114: parallele Temporal-Ledger-Varianten. #2114 wurde als durch #2130 superseded geschlossen; andere Varianten bleiben Referenz/offen, bis gemeinsame Konsolidierung geprüft ist. #2106 editiert eingefrorenes runtime.py und sein Getter ist kein tatsächlicher Consumer.
- PR #2070/#2082: OnlineWorld-Atomic-Cursor-Stack ist auf altem Base und hat SourceHandoff-/Integrated-Regression-Blocker. Nicht blind cherry-picken.

## Geräte- und Nutzerstatus

- Private Owner-Relay-Abfragen #342 und #343 erhielten keine Geräteantwort; #342 wurde nach Ablauf geschlossen, #343 war bei Readback offen ohne Kommentar. Status: NO_LIVE_RECEIPT / REDMI_UNVERIFIED.
- Auto-Updater, installierte Phone-SHA, C3-Korrektheit, B1/B2-Lieferung und Android-native Lernwirkung sind für den aktuellen Release-HEAD nicht verifiziert.
- Keine Modelle, Gewichte, Berechtigungen, Age-Stufe, Datenbank oder Telefonkonfiguration wurden geändert.
- Nutzeraktion: keine nötig, um die Repositoryarbeit fortzusetzen. Kein Termux-Befehl und kein Modell-Download auf Verdacht.

## Nächster ausführbarer Schritt

1. Exakte CI für PR #2130 aktivieren/abholen; der neue Real-Store-Test muss auf dem exakten Branch-HEAD laufen.
2. Echten SQLite-Store-Integrationstest mit ActionSelection, CorollaryCopy, ActionOutcome und Source-Blob bauen.
3. Den Adapter als hash-gebundenen Kandidaten in den eingefrorenen Runtime-Consumer-Pfad überführen, ohne runtime.py oder fremde Source-Handoff-Dateien direkt zu überschreiben.
4. Core repariert #2131 arithmetic contracts und #2129 source pins; Research/Perception richtet A5 producer/receiver/consent aus.
5. Parallel den echten P0-Redmi-Pfad fortsetzen: korrekte C3-Antwort + source-bound B1/B2-Beiträge + World/Memory/JEPA-Rückkopplung. Ein Temporal-Kandidat ersetzt diese Arbeit nicht.
