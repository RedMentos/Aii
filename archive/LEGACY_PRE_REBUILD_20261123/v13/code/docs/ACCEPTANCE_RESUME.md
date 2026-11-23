# Gesamtprüfung fortsetzen

Eine neue Prüfung startet wie bisher mit `bash TESTEN.sh`. Sie prüft echte
Modelle und speichert nach jeder abgeschlossenen Stufe Bericht, Log und
gegebenenfalls native Feature-Dateien. Die vollständige Stufenliste bleibt
fest; fehlgeschlagene Stufen bleiben im Ergebnis enthalten.

Nach einem Abbruch denselben Ergebnisordner angeben:

```bash
bash TESTEN.sh --resume "$HOME/v13/exports/acceptance-ZEITSTEMPEL"
```

Wurden `--quick`, `--compare-c3` oder `--archive-dir` beim ersten Start
verwendet, müssen dieselben Optionen wieder angegeben werden. Mit `--resume`
wird das Setup nicht erneut ausgeführt. Der Collector prüft stattdessen
Quellen, Testprogramme, Einstellungen, Gerät, tatsächliche Modelle und Runner.
Bei Änderungen bricht er mit einer konkreten Fehlermeldung ab. Alte Berichte
ohne Fortsetzungsbindung bleiben historische Nachweise und werden nicht
nachträglich zu einem neuen Lauf zusammengefügt.

Abgeschlossene Stufen werden unverändert übernommen. Eine unterbrochene
Stufe startet neu; ihre bisherigen Dateien und ihr ursprünglicher Status
bleiben unter `interrupted-attempts` erhalten. Zwei Collector-Prozesse dürfen
denselben Lauf nicht gleichzeitig ausführen.

Ein bestandener Gesamtcollector bewertet die ausgeführten Pfade. Er erklärt
die noch offenen Anforderungen der unveränderten SSOT nicht für erledigt.

Für begrenzte Arbeitsabschnitte kann `--stage-limit 3` nach insgesamt drei
Stufen stoppen. Die vollständige Stufenliste bleibt gespeichert und der
Status lautet `DIAGNOSTIC_INCOMPLETE`. Beim Fortsetzen kann die Grenze
erhöht oder weggelassen werden. Ein Teilabschnitt ist kein Gesamt-PASS.
