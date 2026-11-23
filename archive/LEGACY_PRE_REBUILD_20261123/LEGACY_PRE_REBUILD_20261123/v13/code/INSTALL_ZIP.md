# Handy-Paket

`V13-Redmi-Install.zip` enthält den ausführbaren Code, alle Testprogramme,
die unveränderten Pläne und Anleitungen. Die umfangreichen historischen
Rohdaten und Proof-Sammlungen liegen im vollständigen Source-Checkpoint
`V13-Redmi-Start.zip`.

In Termux die ZIP entpacken, in `V13-Phone` wechseln und starten:

```bash
bash STARTEN.sh
```

Das bestehende Setup installiert die Abhängigkeiten, lädt und prüft die
fest gepinnten Modelle und baut den passenden nativen Runner. Danach startet
der Chat. Der erste Aufbau braucht Internet und freien Speicher.

Nach Schließen des Chats können die vorhandenen Pfade einzeln geprüft werden:

```bash
bash TESTEN_STEP2.sh
bash TESTEN_NATIVE_PORT.sh
bash TESTEN_NATIVE_SESSION.sh
bash TESTEN_NATIVE_STREAM.sh --prompt 'Berechne die Hälfte von 120 Euro.' --max-tokens 64
bash TESTEN_NATIVE_TRAIN.sh
bash TESTEN_NATIVE_RECEIVER.sh
bash TESTEN_NATIVE_MIDLAYER.sh
```

Die nativen Zusatztests sind experimentelle Diagnosepfade. Insbesondere
ein numerisch reproduzierbares Gewichtsupdate ist noch kein nachgewiesener
Lernerfolg. Die vollständige Architektur bleibt ein Entwicklungsstand;
`BUILD_STATE.json` und die unveränderte SSOT beschreiben die Grenzen.
