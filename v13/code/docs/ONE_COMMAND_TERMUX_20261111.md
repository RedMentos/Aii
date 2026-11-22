# V13: ein Termux-Befehl fuer private KI-Diagnosen

Status: Installer und privat abfragbarer READ-ONLY-Agent implementiert. Der native Redmi-Test ist noch ausstehend; Patch-Apply bleibt AUS.

## EINMAL in Termux einfuegen

Bei einer bereits laufenden KI zuerst **V13 beenden**. Der Installer beendet
keine aktive V13-Sitzung. Eine inaktive alte Browseroberflaeche wird vor dem
Quellupdate beendet und danach neu geoeffnet; benutze anschliessend diese neue
Browserseite. So werden alte Server und neue HTML-Dateien nicht vermischt.

    pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/RedMentos/Aii/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_one_command.sh -o "$HOME/v13-start.sh" && bash "$HOME/v13-start.sh"

Script-Quelle zum Pruefen: https://github.com/RedMentos/Aii/blob/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_one_command.sh

## Automatisch erledigt

1. Installiert Git, Python, curl und die GitHub CLI (gh).
2. Laedt per sparse Git checkout nur die benoetigten Dateien nach ~/.v13-agent-source; veraendert nicht die bestehende V13-Installation.
3. Startet bei Bedarf den einmaligen GitHub-Browser-/Device-Code-Login fuer RedMentos. **Dieser braucht echte Zustimmung im Browser** und kann nicht im Chat erledigt werden. GitHub CLI OAuth mit repo-Scope kann auch Zugriff auf weitere Repositories haben; wer das vermeiden moechte, muss einen fine-grained Token fuer nur RedMentos/Aiiii separat konfigurieren.
4. Prueft, dass das private Repo RedMentos/Aiiii erreichbar und wirklich PRIVATE ist.
5. Erstellt lokal ~/.v13-private/remote.json (chmod 600), ein Geraetegeheimnis (verlaesst Termux nicht), State/Staging-Ordner und startet den Agenten.
6. Prueft den GitHub-Relay-Zugriff und startet die private Poll-Schleife. **Keine Portfreigabe, keine freie Shell, remote_apply_enabled=false**.

## ChatGPT / Agenten

Die verbundene GitHub-App kann eine Issue in https://github.com/RedMentos/Aiiii erzeugen:

Titel: V13READ:<32-stellige kleingeschriebene hex-ID>

Body (JSON, ohne Geheimnisse): {"schema":"v13.private-relay.owner-read/1","id":"<dieselbe 32-hex-ID>","command":"HEALTH","expires_at":<aktuelle Unix-Sekunden plus max. 600>}

Alternativ command: LEARNING_STATUS.

Wenn der autorisierte GitHub-Account RedMentos diese private Issue erstellt, der Agent im Termux laeuft und das Token gueltig ist, prueft das Geraet die Repo-Privatsphaere, GitHub-Issue-Autor, Zeitfenster und das exakte Schema und schreibt eine redigierte Antwort als privaten Issue-Kommentar. Es wird kein Agent-HMAC-Schluessel an ChatGPT weitergegeben. Diese vereinfachte Authentifizierung gilt ausschliesslich fuer zwei read-only Commands und verlässt sich auf die private Repo-Zugangsverwaltung und GitHub-Account-Sicherheit. Fuer Patches bleibt die staerkere separate HMAC-/Ed25519-Pipeline notwendig.

Der HEALTH-Status umfasst aktuelle Systemdaten und nachweislich frische lokale Runtime-Statusfelder, falls vorhanden. Bis V13 ein autorisiertes lokales live-status.json erzeugt, meldet LEARNING_STATUS ehrlich UNINSTRUMENTED; nicht jedes Modell hat damit schon eine Live-Schnittstelle.

## Fehler, Stop und Neustart

Log ansehen: tail -n 20 "$HOME/.v13-private/bridge.log"

Lokales Stop:
    PYTHONPATH="$HOME/.v13-agent-source/v13/code" python -m v13.owner_read_bridge stop --config "$HOME/.v13-private/remote.json"

Erneuter Start: denselben Ein-Zeilen-Befehl nochmals ausfuehren. Ein ausdruecklicher
lokaler Stop bleibt erhalten und wird nicht als erfolgreicher Start gemeldet.
Nur wenn du diesen Stop bewusst aufheben moechtest, zuerst lokal ausfuehren:

    (cd "$HOME" && PYTHONPATH="$HOME/.v13-agent-source/v13/code" python -m v13.owner_read_bridge resume --config "$HOME/.v13-private/remote.json")

Danach den Ein-Zeilen-Befehl erneut ausfuehren. Bestehende Quellkopien werden nur
auf demselben Branch aus dem erwarteten Repository vorwaerts aktualisiert;
lokale Aenderungen und abweichende Commits werden nicht zurueckgesetzt.
Android kann Termux-Hintergrundprozesse unterbrechen; eine systemweite
Boot-/Foreground-Service-Lebensdauer ist nicht implementiert.

`v13-update` aktualisiert die separate V13-Quellkopie in `~/V13-Phone`.
Die Browseroberflaeche in `~/.v13-agent-source` wird ueber **Steuerzentrale
aktualisieren** oder den Ein-Zeilen-Befehl aktualisiert. Ein gruener GitHub-Test
beweist noch keine Verbindung zum Handy oder erfolgreiche B1/B2-Modelltests.

Noch NICHT fertig: Live-Patches ohne getrennt eingerichteten Entwickler-Schluessel, automatischer Neustart der laufenden V13-Gewichte/Prozesse, Modell-Rollback, nativer Redmi-Langzeitnachweis. Keine Passwoerter, Tokens oder privaten Diagnose-Logs in oeffentliche Issues oder Chats kopieren.
