# F1/F5 → episodische Assoziation → Sleep-A → zweiter Turn (Kandidat)

Stand: 2026-11-08. Grundlage: Review-Kette PR #1608, Commit `15c7a4f5f1961280e2cb0f78746ead3adfc2c39f`. Die Korrektur-/Episoden-Hooks werden nur in einer quellgebundenen Testkopie gesetzt; die Originale `runtime.py`, `memory.py` und `episodes.py` bleiben unverändert. Der getrennte Bewertungs-/Ledger-Kandidat ändert `inputs.py` auf diesem isolierten Zweig. Nutzerkorrekturen, Gedächtnisabruf und Replay bleiben im bestehenden Store; der Assoziationskandidat fügt nur eine abgeschattete, quellgebundene Beziehung hinzu.

## Verbundener Datenpfad

1. Die vorhandene `Memory.feedback`-Funktion erzeugt eine F5-Menschenentscheidung, einen F1-MemoryRecord und eine Replay-Zeile. In einer quellhashgebundenen Runtime-Kopie ergänzt der Kandidat einen Kontextzusammenhang zu den Erinnerungen, die der betroffene abgeschlossene Turn tatsächlich abgerufen hatte. Aktive Quellen und F1/F5-Kette werden geprüft. Ein Zusammenhang ist **korrelational**, kein kausaler Beweis und keine Behauptung, dass die Antwort fachlich korrekt war.
2. Sleep A führt den vorhandenen echten Recall-/Quellen-Retentionstest aus. Erst ein passender `F9_SLEEP_A`-Replay-Beleg mit bestandenem Recall für die Korrektur macht den Zusammenhang für die Vorschau sichtbar. Ohne Replay bleibt er aus.
3. Beim nächsten `Runtime._turn` ruft der vorhandene F1-Pfad direkt passende Erinnerungen ab. Der neue episodische Consumer prüft die gespeicherte Verbindung, beide aktuellen F1/F5-Quellen und den Replay-Beleg und nennt höchstens zwei zusätzliche Memory-IDs als `correction_association_shadow` in der Turn-Metadatei. Er fügt keinen Text zum Prompt und ändert weder Antwort, Route noch Gewichte.

Default ist **off**. In der Testkopie kann der Operator `:episodes correction-association shadow` ausdrücklich wählen; einen Active-Modus gibt es nicht. `:episodes correction-association rollback <Memory-ID>` entfernt nur die zugehörige Kandidatenverbindung; Originalkorrektur und Replay bleiben erhalten. Speicherung enthält IDs und SourceRefs, keine neue Textkopie.

## Nachweis und Grenzen

`PYTHONPATH=.:tests python -m unittest test_correction_association_shadow_slice -v` materialisiert den Kandidaten nach SHA-256-Prüfung von `memory.py`, `episodes.py`, `runtime.py`, `sleep.py` und `store.py` in einer isolierten Kopie. Vier Tests verwenden echte Runtime-/SQLite-/Memory-/Replay-Pfade mit einem synthetischen Fake-C3:

- Im zweiten Turn ist die zuerst abgerufene Erinnerung direkt verfügbar; die Korrektur ist es bei dieser Frage nicht. Die Shadow-Verbindung findet ihre ID erst nach erfolgreichem Sleep-A-Replay. Off-Modus und Replay-Ablation liefern keinen Kandidaten; Ausgabe und Age-0-`RECORD_ONLY` bleiben gleich.
- Der Kandidat überlebt Runtime-Neustart. Der gezielte Rollback entfernt die Verbindung, nicht das weiterhin abrufbare F1-Memory.
- Vergessen der Korrektur oder Entzug ihrer F5-Menschenentscheidung entzieht auch dem alten Replay-Beleg die Nutzbarkeit.
- Eine Änderung der gepinnten Sleep-Quelle wird bei Materialisierung abgelehnt; keine Originalquelle wird überschrieben.

Zusätzlich bestanden 92 bestehende Episoden-, Memory-, Retrieval- und Sleep-Tests auf einer separat materialisierten Kandidatenkopie mit unverändertem Canon. Das sind Softwaretests ohne native Modellgewichte.

Dies ist ein enger, synthetischer Software-Nachweis für verbundenen Datenfluss und Retention auf Abrufebene, **kein** Nachweis, dass die vorgeschlagene Assoziation sachlich relevant ist, eine Benutzerantwort verbessert, ein JEPA/Sprachmodell trainiert oder auf dem Redmi funktioniert. Die Rohbedingungen werden bei der Vorschau erneut geprüft, aber es gibt keinen atomaren Schutz gegen einen späteren Widerruf; deshalb hat der Pfad keine Ausgabe- oder Lernfreigabe. Weitere Schritte: unabhängiger Review, frische semantische Relevanz-/Negativkontrollen und bei nachgewiesenem Nutzen eine atomare Quellenprüfung vor einem erlaubten Consumer.
