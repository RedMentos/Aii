# V13 Redmi: Browser-Steuerung, Logs und Delta-Updates

Stand 2026-11-11. Der neue Browser-Code ist bisher in GitHub Actions unter Linux getestet, NICHT auf dem Redmi abgenommen. Der frühere HEALTH-Handshake war dagegen ein realer Termux-Nachweis.

## Einmaliger Aktualisierungsbefehl

```sh
curl -fsSL https://raw.githubusercontent.com/RedMentos/Aii/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_one_command.sh -o "$HOME/v13-start.sh" && bash "$HOME/v13-start.sh"
```

Der Installer aktualisiert den privaten Bridge-/Dashboard-Code im separaten Verzeichnis ~/.v13-agent-source, überprüft das Relay RedMentos/Aiiii (PRIVATE) und öffnet die lokale Browseroberfläche. Die eigentliche V13-Installation ~/V13-Phone und die Modelle/Chats unter ~/v13 bleiben bestehen.

## Touch-Oberfläche

Aktionen: V13 Chat starten, Nachricht senden, abbrechen/beenden, Gehirnstatus, Modelle, Ressourcen, JEPA/World, Memory, Lernkandidaten, JEF, weitere Organproben, Diagnose-ZIP, Update prüfen/holen/zurücksetzen. Regler: CPU-Threads, Antwort-Tokens, Deadline, Temperatur, Modell-RAM-Budget. Der Befehls-Katalog wird aus der tatsächlich installierten Operator-Hilfe gelesen (statisches AST-Lesen, nicht ausgeführt); Kommandos mit Parametern benötigen diese Angaben.

Der Browser bedient V13 über eine lokal gestartete, aufgezeichnete chat --plain-Sitzung. Ausgabe einschließlich User-Eingabe und Fehlermeldungen wird in ~/.v13-private/console-logs/ privat (0600) gehalten: maximal acht Dateien, jeweils ca. 4 MiB. Andere Termux-Sitzungen und verlorener alter Scrollback bleiben unerreichbar. Ein Klick auf Diagnose-ZIP erstellt ein lokales Artefakt in Android Downloads; diese ZIP kann Chattexte enthalten und wird NICHT automatisch verschickt.

## Private KI-Diagnose

Der autorisierte owner-read Issue-Befehl DIAGNOSTICS liest eine begrenzte, quellengebundene technische Zusammenfassung. Mit dem Button Fern-Fehlercodes EIN kann der Besitzer zusätzlich ausschließlich erkannte Fehlerklassen/Exit-Codes freigeben. Mit dem gesonderten Button V13-Konsolenauszug TEILEN kann er auch die letzten maximal 6000 Zeichen der verwalteten V13-Konsole zur privaten GitHub-Issue-Antwort freigeben. Benutzer-Eingabezeilen und erkennbare Tokens werden maskiert, aber andere Ausgaben können weiterhin private Informationen enthalten. GitHub speichert diese privaten Antworten; der Modus ist standardmäßig AUS und kann lokal widerrufen werden. Andere Termux-Shells werden dadurch nicht ausgelesen.

## Delta-Updater

Das GUI und der CLI-Befehl v13-update verwenden Git fetch plus fast-forward nur auf dem bereits ausgecheckten vertrauenswürdigen Branch und nur bei sauberem Checkout. Abgleich des vorherigen Commits, Syntaxprüfung, Git-Rollback-Referenz. Kein Setup-Neustart, Modell-Neudownload, Chats/Modelle-Überschreiben. Automatische Updates sind per GUI optional und standardmäßig AUS; sie prüfen alle 15 Minuten, sofern die Oberfläche läuft, und benötigen grüne genau-commitbezogene GitHub-Workflows. Updates an laufendem V13 werden verweigert. Vorhandene Python-Modelle müssen anschließend kontrolliert neugestartet werden.

## Grenzen

Kein beliebiger Remote-Shell-Zugriff, keine Android-Prozessliste anderer Apps, kein automatisches Teilen alter Konsolenlogs, keine Live-Gewichtsänderung, kein Root, kein System-Startup-Service. Die neue UI muss auf dem echten Redmi getestet werden; Linux CI allein genügt nicht.