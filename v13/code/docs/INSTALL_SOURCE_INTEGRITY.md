# V13 Phone: Quellcode-Prüfung vor der Einrichtung (Run194)

Das aus dem offiziellen V13-Phone-Quell-ZIP entpackte `setup.sh` prüft **vor** Python-Paketinstallation, V13-Bootstrap und Modellprobe die Datei `WORKSPACE_FILES.json`.

Die Prüfung startet mit `python -I -S` und benötigt nur die Python-Standardbibliothek. Sie prüft alle registrierten Dateien anhand SHA-256, Pflichtdateien, Dateinamen, fehlende und zusätzliche Dateien, symbolische Links und unerwartete Modell-/Privatdateien. Nur Python-`__pycache__/*.pyc` aus späteren Starts werden als zusätzliche Dateien toleriert.

Bei einer Abweichung bricht die Einrichtung mit `V13_SOURCE_PREFLIGHT_FAIL` ab. **Die Prüfliste nicht manuell verändern und den Fehler nicht umgehen.** Stattdessen das Original-ZIP erneut von einer vertrauenswürdigen Quelle beziehen und neu entpacken. Ein Git-Checkout ohne generiertes `WORKSPACE_FILES.json` ist kein fertiges Phone-Installationspaket; erst mit `python3 scripts/package_source.py --out /pfad/zur/phone.zip --phone-install` paketieren und das Ergebnis entpacken.

**Grenze:** Die Prüfliste liegt im selben ZIP. Sie erkennt Beschädigung und nachträgliche Änderungen, ist aber **keine kryptografische Signatur des Herausgebers**. Ein Angreifer könnte ein ganzes ZIP samt Prüfliste neu bauen. Für Herkunftsschutz braucht man zusätzlich einen über einen unabhängigen, vertrauenswürdigen Kanal erhaltenen ZIP-Hash oder eine verifizierte Signatur. Auch nach bestandener Prüfung sind keine Modelle, kein Redmi, kein Body-JEPA, keine B3-Freigabe und kein STEP2-Nutzen nachgewiesen.

Der vollständige V13-Blueprint, alle bestehenden Alters-, Lern-, Freigabe- und Sicherheitsregeln sowie die negativen Gates bleiben unverändert.
