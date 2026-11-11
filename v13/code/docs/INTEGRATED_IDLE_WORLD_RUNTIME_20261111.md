# Budgetiertes World-JEPA-Lernen im vorhandenen Idle-Worker

Aufbau auf C3-Commit `4df40e5598db5b9d5e75ee2f1f04117388a2a18d`, mit unverändertem SourceHandoff-Freeze. Der einzige gemeinsame Stager verwendet `scripts/integrated_idle_world_candidate_20261111.py`, SHA `38c6879b74bcd3158e6e95b48f08b98015662010f55423c54a5db09d879a49f9`. Er ergänzt denselben Runtime-/SQLite-/Archiv-/Organ-Kandidaten. Keine produktive eingefrorene Python-Datei wird editiert.

## Tatsächlicher Datenpfad

Der bestehende G13-/Sleep-Worker führt `learn_world_jepa_idle` aus. Die Funktion startet keinen zweiten Worker und gibt sich nicht als menschlicher Bedienbefehl aus. Eine neue private SQLite-Policy ist standardmäßig OFF. Erst eine ausdrückliche lokale Operatorwahl aktiviert sie; der Trainingsmodus muss zusätzlich SHADOW_UPDATE oder APPROVED_COMMIT erlauben. Das ist keine Modellaktivierung und kein neues Age-Recht.

Die Jobberechtigung `IDLE_SCHEDULER` verlangt den tatsächlichen DISPATCHED-Eintrag der richtigen Aktion, die laufende Sleep-Arbeit, denselben ausführenden Thread und eine gespeicherte Reservierung. Die Berechtigung erlaubt innerhalb dieses Jobs genau einen numerischen Lernaufruf mit einem Schritt. Bool-Werte, größere Schritt-/Zeilenbudgets, ein zweiter Aufruf und ein paralleler fremder Thread werden zurückgewiesen. Save und Restore haben eigene Operationsprüfungen. Direkte IDLE-Aufrufe außerhalb dieses Besitzes erhalten keine Berechtigung.

Automatische SYSTEM-Ereignisse entstehen nach der gespeicherten Freigabe und Mindestleerlaufzeit; SELF-Initiative wird dadurch nicht freigeschaltet. Mindestleerlauf wird beim tatsächlichen Start erneut geprüft. USER-step ist eine ausdrückliche lokale Testanforderung über denselben Scheduler und umgeht die Mindestleerlaufzeit, nicht die übrigen Grenzen. Globale Pause, Trainingspause, Cancel/Stop, Nutzereingaben/Warteschlange, Ressourcen und das bestehende kleine SHADOW-Lernrecht werden vor dem Lernen erneut geprüft.

Default: ein Schritt, höchstens 64 neue Trainingszeilen, mindestens 300 Sekunden Abstand/Leerlauf und acht reservierte Versuche pro UTC-Tag. Konfiguration bleibt auf 1–32 Tagesversuche, 16–128 Zeilen und 30–86400 Sekunden Abstand begrenzt. Reservierung und Abstand werden **vor** Datenzugriff/Fit gespeichert. Fehlende oder veränderte Quellen verbrauchen den Versuch; wiederholte Fehlversuche können keinen automatischen heißen Loop bilden. Uhr-Rücksprung setzt das Budget nicht zurück. Diese Quota gilt für diese World-JEPA-Route, nicht pauschal für alle bestehenden Lerner.

Der Job nutzt die bereits geprüfte echte Runtime-Update- und private Checkpoint-Route. Nach einem Update werden Gewichte, EMA, Optimizer, Inversmodell, RNG und Quelllineage gemeinsam gespeichert. Beim nächsten Runtime-Start stellt der Job einen vorhandenen gültigen privaten Checkpoint vor dem weiteren Schritt wieder her. Ein Save-Fehler kann vor oder nach Manifestveröffentlichung auftreten: Er meldet deshalb `persisted=null` und sperrt weitere Idle-Updates dauerhaft bis zur ausdrücklichen gültigen Wiederherstellung. Er behauptet weder einen sicheren Save noch eine sichere Nichtveröffentlichung. Wiederherstellung erstattet kein Tagesbudget.

## Bedienung in der Reviewkopie

```text
:learning shadow
:learning idle status
:learning idle cfg daily_steps=8 max_rows=64 interval_s=300 min_idle_s=300
:learning idle on
:learning idle step
:learning idle off
:learning idle recover
```

`recover` ist für einen unklaren privaten Checkpointstand bestimmt und verlangt eine tatsächlich gültige bestehende Generation. Ohne gültigen Checkpoint bleibt die Sperre bestehen; keine automatische Neuinitialisierung oder Löschung.

## Bestätigter alter Fehler

Die vorherige C3-Stage erlaubte `authority.job(..., 'learn_medium')` in RECORD_ONLY einen tatsächlichen numerischen Ridge-Fit und persistierte `T8_WORLD_MODEL`. Das neue Paket prüft beide alten Lernaktionen vor Review und Mutation über dieselben Modus-/Pause-/Queue-/Ressourcengrenzen. Der ursprüngliche numerische Fehler bleibt als ausführbarer Test auf dem exakt gepinnten Vorgänger erhalten; auf der neuen Stage muss RECORD_ONLY ohne Review und ohne Zustandsänderung abbrechen. Ein ausdrücklich erlaubter alter Medium-Job darf weiterhin den tatsächlichen Ridge-Fit ausführen.

## Prüfung und Evidenz

Geschlossen: **76 gezielte PASS / 12 Untertests PASS, 2 äußere Tests PASS** einschließlich des gepinnten alten Record-only-Gegenbeispiels; **562 gemeinsame PASS / 3 CUDA SKIP / 70 Untertests PASS** in einer Stage, äußerer Test PASS. Die sechs bisherigen Staging-/Runtime-Dateien bestehen zusätzlich mit **13 äußeren PASS**. Ergebnisse und SHA-Bindungen liegen unter `proofs/idle-world-runtime-20261111/`. Remote-CI ist vor dem neuen Push noch nicht nachgewiesen. Die gezielten Fälle enthalten echte synthetische Runtime-Turns, den tatsächlichen Scheduler, NumPy-Updates, private Speicherung und Wiederöffnung. Mehrere unabhängige Negativfälle verwenden Kopien einer einmal über echte Runtime-Turns erzeugten und geschlossenen synthetischen SQLite-Quelle; sie ersetzen keine Quellenprüfung durch Mock-Zeilen.

Frühe Versuche bleiben erhalten: ein veralteter Helper-Pin, ein 300-Sekunden-Timeout des ersten wiederholt aufgebauten Testbestands und danach 5 FAIL/71 PASS. Letztere betrafen zwei Queue-Mock-Aufräumfehler, zwei alte Unit-Tests mit implizit als grün vorausgesetzten Repository-Gates und die alte positive RECORD_ONLY-Jobfixture. Queue-Mocks werden vor `Runtime.close` entfernt; die beiden abstrakten Promotionsfälle liefern nun ausdrücklich synthetische grüne Gate-Fixtures, während ihre negativen Gatekontrollen erhalten bleiben. Der Scheduler-Positivfall verlangt jetzt ausdrücklich SHADOW. Keine produktive Gate-Evidenz wurde geändert. Im ersten gemeinsamen Lauf bestanden bereits 562 Fälle/70 Untertests, aber ein weiterer Queue-Mock verursachte einen Teardown-ERROR; sein enger Mock-Kontext ist repariert und der vollständige gemeinsame Wiederholungslauf jetzt sauber. Beide Originalprotokolle bleiben erhalten.

```bash
cd v13/code
python -m pytest -q -s tests/test_idle_world_stage_20261111.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

## Noch offen

Das ist synthetische Softwareevidenz, kein eigenständiger Qualitäts-, Retention-, Native- oder Redmi-Nachweis. Der bestehende World-Guard hält während des einen begrenzten Fits Runtime-/SQLite-Sperren; harte Vordergrundunterbrechung und Handy-Latenz sind nicht bewiesen. Historische Quellprüfung kann bis zu 2048 vorhandene Lineage-Zeilen lesen; das neue Zeilenlimit ist das Trainingsfenster und keine Zusage über sämtliche Prüflast. Erreicht eine langfristige Lineage die vorhandene Kapazität beziehungsweise verlässt eine benötigte Quelle das prüfbare Fenster, muss der Pfad blockieren; effiziente Langzeitkonsolidierung bleibt offen.

Unverändert sind die Fit-Aufrufgrenzen: bei Ein-Schritt-Aufrufen führt der vorhandene Bootstrap-Nebenpfad mit `steps//2` keine zusätzlichen Ensemble-Schritte aus. Nutzen und bessere Schrittplanung brauchen eigene Vergleiche; keine Qualitätsbehauptung aus veränderten Gewichten ableiten.

Kein Datasetdownload, kein Datasettraining und keine Bildschirm-/Audio-/Android-Befugnis wird hier aktiviert. Der nächste konkrete Consumer nimmt bereits lokal vorbereitete Datasetzeilen mit eigener Herkunft, Cursor und Speicherquota auf; ein eigener Trainingsvertrag bleibt erforderlich. Komprimierte quasi unbegrenzte Erinnerung, unabhängige Retention und tatsächliche organübergreifende Selbstoptimierung bleiben verbindlicher offener Blueprint-Umfang. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE und beide false-Gesamtflags bleiben bestehen.
