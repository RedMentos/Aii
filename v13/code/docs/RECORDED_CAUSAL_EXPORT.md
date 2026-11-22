# Vorhandene kausale Beobachtung exportieren

Der bestehende Runtime-Modus `same_causal_zero` beziehungsweise `same_causal` speichert die echte, geprüfte Prefill-Beobachtung in seinem Diagnoseverzeichnis. `scripts/export_recorded_live_output_dataset.py export` verwendet diese bereits abgeschlossene Beobachtung. Es führt keinen weiteren Prefill, keine Generierung und kein Training aus.

Im Chat zunächst eine ausdrücklich selbst verfasste Referenz angeben:

```
:feedback output Hallo --learn
```

Chat beenden. Mit `python scripts/export_live_output_dataset.py labels --installed-home "$HOME/v13"` die aktuelle originale Decision-ID und Label-Source-ID finden. Die Lernberechtigung bleibt ausdrücklich erforderlich; Modellantworten werden nicht zu Labels.

Wenn noch kein passender echter Tokenizer-Beleg existiert:

```
python scripts/export_recorded_live_output_dataset.py tokenize --installed-home "$HOME/v13" --decision DECISION_ID --label-source SOURCE_ID --learn --out "$HOME/v13/exports/label-receipt" --seconds 30 --rss-limit-mb 768
```

Dies lädt den gebundenen nativen Tokenizer und tokenisiert ausschließlich die exakte Referenz mit `add_special=false`. Es gibt keinen Antwort-Prefill und keine Generierung. Deadline, RSS-Grenze, Coordinator-Ausschluss und Prozess-Reaping werden geprüft. Ein Beleg darf nur für identischen Text, Modell, Serverrevision, Worker-ABI und Tokenisierungsparameter wiederverwendet werden.

```
python scripts/export_recorded_live_output_dataset.py export --installed-home "$HOME/v13" --decision DECISION_ID --label-source SOURCE_ID --learn --tokenizer-receipt "$HOME/v13/exports/label-receipt/receipt.json" --out "$HOME/v13/exports/recorded-label" --seconds 90
```

Der Export prüft aktuelle Quellen und Berechtigungen, die Original-Context-Pakete, die im Store gespeicherte Beobachtungshash, vollständige rohe Token-Ereignisse, das native Resume-Kommando, Modell-/Bibliotheks-/Worker-Bindung und das geprüfte abgeschlossene Reaping. Alle portablen Trainingsdaten durchlaufen den unveränderten Trainer-Parser. Erst danach entsteht der ausdrücklich gebundene Export-Decision-Beleg. Der bestehende `assemble`-Befehl kann die erzeugten `fragment.json`-Dateien zusammenführen; Training und einzelne Freigabe bleiben getrennte bestehende Schritte.

Die Diagnoseaufbewahrung hält höchstens acht abgeschlossene Runtime-Verzeichnisse. Rechtzeitig exportieren. Fehlt ein Originalverzeichnis oder seine Store-Hashbindung, lehnt der neue Pfad ab; der ursprüngliche explizite Capture-Pfad bleibt verfügbar. Unvollständige, widerrufene oder überschriebene Quellen dürfen nicht nachgebildet werden.

Softwarefixtures und die separat preregistrierten zwei Testreferenzen sind keine echten Nutzer-Lerndaten und kein Nachweis einer lernfähigen Gesamtarchitektur. Der Export selbst vergibt keine Freigabe und ändert keine Modellgewichte.

Der mitgelieferte echte Zwei-Zeilen-Diagnosetest ist nach Einrichtung des nativen kausalen Runners ausführbar. Chat vorher beenden und ein neues Ausgabeverzeichnis wählen:

```
python tests/integration_recorded_live_output_export.py --home "$HOME/v13" --out "$HOME/v13/exports/recorded-export-diagnostic"
```

Er verwendet die vorab festgelegten Begrüßungs-/Dankesreferenzen, zwei echte Runtime-Aufrufe und echte Label-Tokenisierung. Er testet die Offline-Übernahme der bereits erzeugten Beobachtungen. Die zwei Zeilen reichen ausdrücklich nicht für Training; erwartet wird `INSUFFICIENT_LABELLED_COHORT` ohne Optimizerschritte oder Freigabe. Gesamtbudget: 420 Sekunden.

Der bestehende Linux-Nachweis wurde mit dem eingefrorenen Collector unter `docs/proofs/recorded-live-output-export-20261009/native_lifecycle.py` erhoben. Die mitgelieferte Datei unter `tests/` hat denselben Algorithmus; ausschließlich die Ermittlung des Repository-Verzeichnisses wurde an ihren Speicherort angepasst. Die AST-Prüfung ist in `shipped-collector-equivalence.json` dokumentiert. Der native Nachweis wurde durch diese Verpackungsänderung nicht erneut ausgeführt; er ist kein Redmi-Test.
