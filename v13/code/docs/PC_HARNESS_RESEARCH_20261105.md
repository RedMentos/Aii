# PC-Harness: Recherche und Arbeitsgrenzen, 2026-11-05

## Nutzerziel

Das vollständige V13-Blueprint und seine Ergänzungen bleiben das Ziel. Zusätzlich
soll V13 später nach bewusster Erlaubnis einen PC über Terminal und/oder eine
grafische Oberfläche bedienen können. Redmi/Termux bleibt Zielgerät; ein
zusätzlicher PC ist eine weitere Umgebung, kein Ersatz für den Handy-Nachweis.
Frühere wirklich nutzbare Zwischenschritte sollen nicht bis zum Ende aller
Forschung warten. Keiner der folgenden Bausteine ist durch diese Recherche
bereits aktiviert oder als auf dem Redmi getestet nachgewiesen.

## Recherche: offizielle Quellen, gelesen am 2026-11-05

| Baustein | Beobachtung und Grenze | Quelle / Lizenz |
|---|---|---|
| Linux-Desktop | XDG RemoteDesktop erlaubt Auswahl von Tastatur, Maus und Touch sowie Kombination mit ScreenCast. Sitzungs-Persistenz ist standardmäßig aus. Ein passendes Desktop-Backend ist erforderlich; Termux-Unterstützung ist damit nicht belegt. | https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html ; Interface-Datei LGPL-2.1-or-later: https://github.com/flatpak/xdg-desktop-portal/blob/main/data/org.freedesktop.portal.RemoteDesktop.xml |
| Browser auf dem PC | Playwright unterstützt echte Browser auf Linux, Windows und macOS; die offiziellen Host-Voraussetzungen nennen Termux nicht. Das Android-API ist experimentell und benötigt gesonderte Geräteanbindung. | https://playwright.dev/python/docs/intro ; https://playwright.dev/docs/api/class-android ; Apache-2.0 laut https://github.com/microsoft/playwright-python/blob/main/pyproject.toml |
| Verbindung Handy–PC | OpenSSH ist als Termux-Paket vorhanden. `StrictHostKeyChecking=yes` verweigert neue bzw. geänderte Hostschlüssel, bis die Identität bewusst geprüft wurde. Eine Verbindung allein ist keine Autorisierung für einen Befehl. | https://github.com/termux/termux-packages/blob/master/packages/openssh/build.sh ; https://man.openbsd.org/ssh_config.5 ; OpenSSH-Lizenz laut Paket BSD |
| Werkzeugerweiterungen | MCP kann spätere Werkzeuganbindung unterstützen; fremde Werkzeug-Metadaten müssen durch lokale Rechte und tatsächliche Adaptergrenzen abgesichert werden. Kein Muss für den ersten Textchat. | MIT: https://github.com/modelcontextprotocol/python-sdk ; https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/ |
| Isolation | bubblewrap ist ein Baukasten, keine allein schon sichere Sandbox: relevante Grenzen hängen von der konkreten Betriebssystem- und Mount-Konfiguration ab. Für Redmi/Termux nicht geprüft. | https://github.com/containers/bubblewrap/blob/main/SECURITY.md ; Lizenz: https://github.com/containers/bubblewrap/blob/main/COPYING |
| Fortsetzung auf Android | Termux warnt vor Prozessabbrüchen unter Android 12+. Persistente Zwischenstände und keine blinden Aktionswiederholungen sind daher nötig. | https://github.com/termux/termux-app |

## Bezug zum vorhandenen V13

- Vorhanden: Textchat, ToolSpec/ToolRegistry, aufrufbezogene Vorschau und
  Zustimmung, ActionIntent/CorollaryCopy und ein persistenter Transaktionspfad.
  Das bestehende Beispielwerkzeug ist eine lokale Notiz, keine PC-Steuerung.
- Gegenprüfung: Das bisherige Notizwerkzeug folgt Links außerhalb seines
  vorgesehenen Ordners. Außerdem können zwei gleichzeitige `approve`-Aufrufe
  einen Effekt doppelt auslösen. Ein Notaus kann einen gerade zwischen Prüfung
  und Start befindlichen Effekt nicht sicher zurückholen. Vor realen neuen
  Werkzeugen benötigen diese Grenzen konkrete Abhilfe und Tests.
- Der vorhandene `ToolStep`-Weg ist für einige englische Formulierungen
  regelbasiert. Das ist noch keine freie Planung durch das Modell.
- Zielpfad: zuerst den vorhandenen Textkern schneller nutzbar machen; getrennt
  eine simulierte, typisierte PC-Aktion mit Vorschau, bewusster Zustimmung,
  Rückmeldung und Neustartverhalten testen. Danach echte, separat freizugebende
  Adapter/Transporte mit ausdrücklicher Ziel-/Rechtebindung integrieren. Die
  Simulation ist kein Beweis für GUI-, Terminal- oder Modellfähigkeiten.

## Offene Nachweise

Quellbindung und sichere Zielidentität, widerrufbare Benutzerzustimmung,
At-most-once-Effekte auch bei Konkurrenz/Crash, klares `UNKNOWN` nach unklarem
Abbruch, Notaus-Grenzen, Grenzen und Logs ohne private Inhalte sowie End-to-End-
Messungen auf echten Geräten. Ein bereits laufender fremder Effekt ist nicht
generell rücknehmbar. Keines dieser Punkte öffnet die bestehenden Lern-/B3-Tore.
