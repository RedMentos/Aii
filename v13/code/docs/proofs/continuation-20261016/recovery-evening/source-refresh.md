# Quellenabgleich am Abend des 2026-10-16

Der neu sichtbare Branch `claude/project-thread-hiczvw` steht auf `a895487f1b8edda600dcd8098cb7f6a92bfbecfa`. Er enthält **keinen neuen Arbeitsstand** gegenüber M `1941d07` oder dem gesicherten K/M-Integrationsstand `3af7ea8`: Sein HEAD ist ein direkter historischer Vorfahr beider Referenzen. Deshalb ist keine Übernahme nötig.

## Exakt geprüft

- Live-`git ls-remote` bestätigt `a895487…`; Autor- und Commitdatum sind **2026-10-11 02:05:20 UTC**, Betreff „Add V13 project files (code, docs, roadmap) for handoff“. Elterncommit `c513c00ddff492d6a3a37ba4f21a0abf628b3aa1`.
- `git merge-base --is-ancestor a895487… <Referenz>` liefert für beide Referenzen Erfolg; jeweilige Merge-Base ist `a895487…` selbst. Ein nur abweichender Importzeitpunkt wird damit nicht als neue Implementierung behandelt.
- Alle 744 damaligen Pfade existieren in beiden Referenzen. Gegen M sind 705 bytegleich und 39 inzwischen geändert; M besitzt 1246 zusätzliche Pfade. Gegen unseren gesicherten Stand sind 701 bytegleich und 43 inzwischen geändert; unser Stand besitzt 1326 zusätzliche Pfade. Der alte Branch enthält **0 exklusive Pfade**.
- Für Runtime/Skripte/Tests/Spezifikationen: gegen M 315 identische und 28 inzwischen geänderte Pfade; gegen unseren Stand 311 identische und 32 geänderte. Keiner ist ein exklusiver Kandidatenpfad. Blob-IDs und sämtliche geänderten Pfade stehen in `source-refresh-comparison.json`.

## Übergaben richtig einordnen

`HANDOFF_CURRENT.md` existiert auf diesem alten Stand noch nicht. `UEBERGABE_FUER_ANDERE_KI.md` trägt den 11.10., nennt rund 940 Tests und Dream-Lauf 2 als offen. `ROADMAP.md` endet nach WP-U10; dessen Ende und der alte BUILD_STATE beschreiben den damaligen Stand. Sie ersetzen **nicht** die spätere vollständige Dream2-v3-Auswertung, die aufgehobene SourceHandoff-Sperre oder die bereits gesicherte aktuelle Integration. Die dauerhaft abgelegten fünf Nutzerentscheidungen bleiben inhaltlich enthalten.

Fortsetzung bleibt am eigenen Integrationsstand: vollständige aktuelle Tests und native Parität sind bereits separat gesichert; eine teilweise erhobene Lernkohorte darf nicht als abgeschlossener Lernnachweis gelten. Aktive Claude-Unterhaltungen oder ihr Fertigstatus sind durch diesen Quellenabgleich nicht beobachtbar. STEP2- und B3-Negativgates werden nicht geändert.

Nur Leseprüfung durchgeführt; keine Runtime-Änderung, kein Checkout/Reset/Merge, keine Modellinferenz. Diese Notiz und die Vergleichsdatei sind die einzigen von diesem Review geschriebenen Dateien.
