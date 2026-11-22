# Tatsächliche längere Messung auf dem Handy

Nach `STARTEN.sh` und `TESTEN.sh` im entpackten Quellordner:

```bash
bash TESTEN_LONG.sh --batches 4 --cycles-per-batch 12 --duration-seconds 3600 --termux-battery
```

Das führt den **bereits vorhandenen** nativen Sustained-Pfad aus: vier getrennte
Messblöcke mit je zwölf echten Modellantworten und drei Runtime-Neustarts. Es
ändert weder Modelle noch Lernrechte. Das Stundenbudget ist eine Obergrenze;
erfolgreiche Blöcke können früher fertig sein. Der aktuelle Sustained-Pfad nutzt
`route=simple`, `history_turns=0`, `RECORD_ONLY`, deaktivierte Teacher und Observer.
Die übrigen Pfade werden durch `TESTEN.sh` geprüft. Ein Linuxlauf wird ausdrücklich
als `NON_PHONE_BOUNDED_COLLECTION_PASS` gekennzeichnet.

Alle zwei Sekunden werden echte `/proc`-, Batterie- und Thermal-Sysfs-Werte
gesichert. `--termux-battery` ruft ausschließlich das **bereits installierte**
`termux-battery-status` auf. Fehlender oder verweigerter Sensorzugriff bleibt
sichtbar `null`/`UNAVAILABLE`. Es wird keine Zusatz-App installiert. Die originale
Termux-JSON wird aufbewahrt; ihre Stromwerte werden ohne belegte Einheit nicht
in eine Energieangabe umgerechnet.

`summary.json`, fortlaufende `samples-NNN.jsonl` und unveränderliche
`batch-NNN-attempt-NNN.json`/`.log` liegen im ausgegebenen Ergebnisordner.
Die Zusammenfassung bindet alle Runtime-Quellen, diesen Collector, den Canon und
tatsächlich installierte Modell-/Runnerdateien über SHA-256. Sensorreihen werden
nach jedem Messpunkt geflusht und synchronisiert. Das Indexdokument wird atomar
ersetzt. Abbruch mit Strg+C hält Teilmessungen und fehlgeschlagene Versuche fest.

Wiederaufnahme desselben Laufes mit **denselben Argumenten**, wobei `--out`
durch `--resume` ersetzt wird:

```bash
bash TESTEN_LONG.sh --resume "$HOME/v13/exports/phone-epoch-DEIN-ZEITSTEMPEL" \
  --batches 4 --cycles-per-batch 12 --duration-seconds 3600 --termux-battery
```

Bereits bestandene Blöcke werden übersprungen; unterbrochene Blöcke werden als
neuer Versuch ausgeführt. Quellen, Modelle, Einstellungen und abgeschlossene
Proof-/Sensor-Dateien müssen unverändert sein. Ein hart beendeter vorheriger
Collector bleibt als `INTERRUPTED_BY_RESTART` sichtbar. Das Zeit- und Samplebudget
gilt je Aufruf; ältere Zeitabschnitte werden nicht als lückenlose Messung ausgegeben.
Fertige Läufe werden nicht fortgeschrieben. Für ein neues Ergebnis neuen Aufruf
ohne `--resume` starten.

Eine zusätzliche Kopie während der Messung und die Zuordnung zu einem bestehenden
Quell-ZIP sind optional:

```bash
bash TESTEN_LONG.sh --out "$HOME/v13/exports/meine-messung" \
  --archive-dir "$HOME/v13-proof-kopie/meine-messung" \
  --source-zip "$HOME/storage/downloads/V13-Redmi-Start.zip" \
  --batches 4 --cycles-per-batch 12 --duration-seconds 3600 --termux-battery
```

`archive-dir` muss bei einem neuen Lauf leer sein. Vorhandene Quell-ZIPs werden
kopiert und gehasht; der Collector packt keine Chat-/Benutzerdaten in ein Quell-ZIP.
Ein neues reproduzierbares Quellpaket erzeugt das bestehende Paketwerkzeug:

```bash
python scripts/package_source.py --out "$HOME/V13-Phone-Source.zip"
```

Der kleine Sensor- und Speicher-Test ohne Modellstart:

```bash
bash TESTEN_LONG.sh --sensors-only --duration-seconds 10 --sample-seconds 1
```

Dieser Test liefert `COLLECTION_COMPLETE`, **keinen** nativen oder Handy-Proof.
Für alle Aufrufe gelten Bounds: 4–128 Zyklen je Block, 1–32 Blöcke,
1–86400 Sekunden, 0,25–60 Sekunden Sampleabstand, maximal 100000 Samples
(`--max-samples`, Standard 20000).

## Aussagegrenzen

- Energie wird nur aus gültigen aufeinanderfolgenden **entladenden** Sysfs-Samples
  derselben einzelnen Batterie integriert. Lücken, Laden, unbekannte Werte und
  Suspend werden nicht überbrückt. Die Angabe betrifft das ganze Gerät, keine
  isolierte App-Energie; Messabdeckung in Sekunden und Intervallen ist separat.
- RSS wird je PID **und Prozessstartzeit** verfolgt. Endpunktänderungen sind
  beschreibend, kein Leak-Nachweis. Die Summe der Prozess-RSS kann gemeinsam
  gemappte Seiten mehrfach zählen.
- Der bestehende Runner exportiert keine nativen KV-Bytegrößen. Daher bleibt
  `native_kv_growth_measured=false` und `kv_cache_bytes=null`; RSS ersetzt das
  nicht. Auch ein erfolgreicher Lauf schließt diesen Canon-Punkt nicht.
- Wochenlange Retention, STEP-7-Stabilitätsepoche und vollständige Canon-Umsetzung
  bleiben ausdrücklich unbewiesen. `hardware_epoch_complete` wird nicht durch
  diesen Collector gesetzt. Die `missing_proofs` im Ergebnis nennen offene Gates.

Die Rohdateien enthalten Messdaten und die tatsächlichen Sustained-Testantworten.
Ein Archiv sichert lokal eine zweite Kopie; für Verlust des gesamten Telefons
oder Workspace muss diese Kopie zusätzlich außerhalb davon aufbewahrt werden.
