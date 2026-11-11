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

## Mobile UI 2: vier statt einer langen Scrollseite (2026-11-12)

Die Oberfläche ist jetzt mobile-first in **vier logisch getrennte Tabs** umgebaut: **Chat**, **Gehirn**, **Regler**, **Wartung**. **Keine Befehle entfernt.** Der Gehirn-Tab gruppiert alle bisherigen spezifischen Operator-Kommandos plus die im installierten V13-HELP entdeckten Befehle. Anklicken übernimmt den Befehl in den Chat-Eingabebereich; Ausführen bleibt eine bewusste Aktion. Die kurze direkte Probe- und Modellbedienung bleibt erhalten.

Im **Chat-Tab** stehen Start/Abbruch/Status, der live aktualisierte V13-Terminalverlauf, **„Gesamten Chat kopieren“** und **„Verlauf als TXT“** unmittelbar über dem Eingabefeld. Beim Kopieren werden alle aktuell noch gespeicherten verwalteten V13-Sitzungen (max. 32 lokale Protokolle mit Größenbegrenzung) zusammengeführt; die Ausgabe bleibt auf dem Smartphone, kein GitHub-Upload. Ein Browser, der Clipboard-Zugriff blockiert, kann das TXT direkt herunterladen. Andere Termux-Sitzungen und vor Aktivierung nicht protokollierte Texte sind nicht enthalten.

Alle Formulare verwenden **AJAX**, sodass ein Klick nicht mehr an eine andere Stelle springt. Der laufende Status sowie die Konsolenausgabe werden alle 1,5 Sekunden über die lokale URL aktualisiert. Das Backend gibt für fehlende Voraussetzungen eine verständliche Fehlermeldung; es erscheint kein endloses „wird geprüft“ ohne Rückmeldung.

Im **Wartungs-Tab** sind **V13-Code aktualisieren** und **Steuerzentrale aktualisieren** explizit getrennt. Der Code-Updater führt ein verifiziertes Git-fast-forward im vorhandenen `~/V13-Phone` aus. Die dort installierte `~/v13/bin/v13`-Launcherdatei referenziert diesen Code per `PYTHONPATH`; nach Update muss V13 neu gestartet werden, damit die neue Version aktiv ist. Der Browser-Updater aktualisiert `~/.v13-agent-source`, validiert geänderte Python-Dateien und die notwendige HTML-Datei und startet den lokalen HTTP-Server auf **demselben Port mit demselben lokalen Seiten-Token** neu. Vor beiden Updates muss eine über die Oberfläche gestartete V13-Sitzung beendet sein. Für Git-Fetch gilt 90 Sekunden Timeout; die Seite zeigt Dauer und Resultat an. Fehler werden sichtbar statt still im Hintergrund zu verschwinden.

**Einmalige Migration aus der alten Oberfläche:** Den untenstehenden bereits existierenden Termux-Installer noch einmal ausführen, damit das neue HTML-Template mit installiert und das lokale Browserfenster neu geöffnet wird. Ab dann ist die Schaltfläche „Steuerzentrale aktualisieren“ direkt in der GUI verfügbar.

```sh
curl -fsSL https://raw.githubusercontent.com/RedMentos/Aii/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_one_command.sh -o "$HOME/v13-start.sh" && bash "$HOME/v13-start.sh"
```

**Nachweisgrenze:** Python-/HTTP-/JS-Tests in GitHub Actions validieren die neue Oberfläche synthetisch. Ein erneuter realer Redmi-Test des neuen vierteiligen Layouts und seines selbständigen Neustarts bleibt erforderlich, bevor behauptet wird, dass es auf diesem Gerät bereits funktioniert.
