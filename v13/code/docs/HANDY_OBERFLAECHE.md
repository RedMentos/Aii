# Handy-Oberfläche: APK oder Termux? (WP-UI1, 2026-10-22)

Frage des Nutzers: Wäre eine eigene App (APK) sinnvoller, oder geht Oberfläche und alles in Termux, auch wegen Leistung?

## Empfehlung

**In Termux bleiben, keine APK jetzt.** Die Bedienung wird mit Knöpfen auf dem Startbildschirm (Termux:Widget)
handlicher gemacht. Eine APK lohnt sich erst, wenn V13 an andere Leute verteilt werden soll oder Android-Funktionen
gebraucht werden, die Termux nicht bietet.

## Begründung

| Punkt | Termux (jetzt) | Eigene APK |
|---|---|---|
| Rechenleistung | Die schwere Arbeit machen die nativen llama.cpp-Programme, die auf dem Handy selbst übersetzt werden (ARM-Befehle, gleiche Bibliothek). Python koordiniert nur. | Gleicher nativer Code. **Kein Tempo-Gewinn**, die Modelle rechnen gleich schnell. |
| Speicher (RAM) | Gemessen: C3+B1+B2 brauchen ~2,0 GB (mit Umpacken) bzw. ~1,0 GB ohne (WP-RAM). Termux selbst kostet wenig. | Eine App-Oberfläche (WebView/Java) kostet eher **mehr** Speicher, der den Modellen fehlt. |
| Android beendet Hintergrund | Termux hat eine Daueranzeige (Vordergrund-Dienst) und `termux-wake-lock`. Auf Xiaomi/HyperOS zusätzlich: Akku-Optimierung für Termux aus, „Autostart“ an. Android 12+ kann Unterprozesse beenden („phantom process killer“). | **Gleiches Problem.** Eine APK braucht denselben Vordergrund-Dienst und dieselben Xiaomi-Ausnahmen. Nur der Unterprozess-Killer trifft eine App mit eigenen Threads etwas weniger. |
| Bedienung | Vollbild-Chat im Terminal (gibt es schon), dazu ab jetzt vier Knöpfe auf dem Startbildschirm. | Schönere Knöpfe/Fenster möglich. |
| Aufwand | Klein: die Knöpfe sind ein Einrichtungs-Skript. | Groß: Python + llama.cpp mit dem Android-NDK bauen, App signieren, ohne PC am Handy praktisch nicht machbar. |
| Updates | ZIP entpacken / Git, wie bisher. Jede Änderung ist sofort drin. | Jede Änderung = neue APK bauen, signieren, installieren. |
| Sicherheit | Befehle (auch Aufheben von Notaus/Stillstand) nur über die Tastatur im Chat. Unverändert. | Neue Wege hinein (App-Knöpfe, Intents) müssten alle neu abgesichert werden. |

Warum keine Web-Oberfläche auf `localhost`: Jede andere App auf dem Handy kann `localhost` erreichen. Die
Operator-Befehle sind bewusst nur über die Tastatur erlaubt (`operator_command_origin: TTY only`). Eine Web-Seite
bräuchte ein eigenes Schlüssel-System und wäre ein zusätzliches Einfallstor. Erst sinnvoll, wenn es echten Bedarf
gibt; dann mit Einmal-Schlüssel und nur Lesen (Status), nie Aufheben von Stopps.

## Der kleine Schritt: Knöpfe auf dem Startbildschirm

Einmal in Termux im Programmordner:

    bash KNOEPFE_EINRICHTEN.sh

Dazu die App **Termux:Widget** aus derselben Quelle wie Termux (z. B. F-Droid) installieren und das Widget auf den
Startbildschirm ziehen. Für eine kurze Meldung beim Drücken zusätzlich **Termux:API** + `pkg install termux-api`.

| Knopf | Was er macht |
|---|---|
| V13 Chat | Hält das Handy wach (`termux-wake-lock`), startet `v13 chat`, gibt den Wach-Halter beim Beenden frei. |
| V13 Status | Zeigt, ob V13 läuft und ob ein Stopp-Knopf noch auf den Chat wartet. |
| V13 Befehle | Öffnet die Liste aller Befehle mit Erklärung (`docs/BEFEHLE.md`) zum Scrollen; `/Wort` sucht, `q` schließt. Im Chat dasselbe mit `:befehle [Wort]`. |
| V13 Notaus | Wie `:notaus`: kein Werkzeug, keine Freigabe mehr, laufende Antwort wird abgebrochen. Ohne Fenster. |
| V13 Stillstand | Wie `:stillstand`: hält alles an (Werkzeuge, Aufgaben, Lernen, Hintergrund, Alterung). Ohne Fenster. |

Entfernen: `bash KNOEPFE_EINRICHTEN.sh weg`.

### Wie die Stopp-Knöpfe wirken (Sicherheit)

- Ein zweiter Prozess kann den Speicher nicht öffnen, solange der Chat läuft (Sperre in `store.py`). Deshalb legt der
  Knopf nur eine leere Datei `~/v13/control/NOTAUS` bzw. `STILLSTAND` ab. Der laufende Chat prüft alle 0,5 s
  (`v13/phone_halt.py`) und ruft **dieselben Funktionen** auf wie die getippten Befehle.
- **Nur Einschalten.** Kein Knopf und keine Datei kann einen Stopp aufheben. Aufheben geht nur im Chat:
  `:notaus aus`, `:stillstand aus`. Unbekannte Dateinamen werden ignoriert, der Inhalt wird nie gelesen.
- Läuft der Chat gerade nicht, wird der Stopp **beim nächsten Start vor der ersten Eingabe** angewendet.
- Jede erledigte Datei wird in `<Name>.erledigt-<Zeit>` umbenannt, damit sie nach dem Aufheben nicht wieder greift.
- Jeder Knopfdruck steht im Protokoll (`phone_halt_button`).
- Grenze: Der Knopf wirkt nur auf den Chat (`v13 chat`). Einzelaufrufe wie `v13 ask` oder Messläufe sehen ihn nicht;
  die beendet man wie bisher mit Strg+C.

## Was am Handy zu prüfen ist (Nutzer)

1. `bash KNOEPFE_EINRICHTEN.sh`, Widget auf den Startbildschirm, alle vier Knöpfe erscheinen.
2. „V13 Chat“ drücken, Chat startet.
3. Zum Startbildschirm, „V13 Stillstand“ drücken, zurück in Termux: im Chat steht „Knopf ‚Stillstand‘ gedrückt …
   STILLSTAND AN“. Mit `:stillstand aus` aufheben.
4. Chat mit `:shutdown` beenden, „V13 Notaus“ drücken, Chat neu starten: Notaus ist sofort an. `:notaus aus`.
5. Xiaomi: Einstellungen → Apps → Termux → Akku-Sparmodus „Keine Einschränkungen“, Autostart an.

## Später (nur bei Bedarf)

- Eine Android-Daueranzeige mit Knöpfen (`termux-notification --button1 …`) statt Widget.
- APK erst, wenn V13 verteilt werden soll; dann als Hülle um dieselbe Laufzeit, Stopps weiter nur einschaltbar
  von außen.
