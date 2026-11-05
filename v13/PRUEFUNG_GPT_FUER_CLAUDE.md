# Gegenprüfung von Claudes Stand – 2026-11-05

## Zwischenstand: BP5, BP8 und BP9

**Grundlage:** `claude/project-thread-ggf5qt` auf
`7f0158d223fefe5bb218ddccab6bf79dbbc44fb7`; zum Umfang des offenen PR #1587
wird dessen Basis `ee0777682ae286a8e41a17fe63a6e914117d2745` herangezogen.
Dies ist keine Aussage, dass parallele Claude-Zweige darin enthalten sind.
Der Hauptzweig ist älter und wird nicht überschrieben.

**Geprüft:** Auf dem unveränderten HEAD lief in `v13/code` unter Python 3.12
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python3 -m unittest discover -s tests`:
1881 Tests OK, 14 übersprungen. Das ist ein Softwaretest, kein Modell-,
Android- oder Nutzennachweis.
`python3 v13/code/scripts/public_repo_privacy_scan.py --base ee0777682ae286a8e41a17fe63a6e914117d2745 --head 7f0158d223fefe5bb218ddccab6bf79dbbc44fb7 --no-worktree`: CLEAN.
Die Prüfung deckt damit den Umfang von PR #1587 ab; sie behauptet keine
vollständige Durchsicht aller älteren oder parallelen Zweige.

**Befunde:**

1. `b3pair.precheck` kann bei NaN und unplausiblen Genauigkeiten `GO` melden.
   Der dortige SCALAR-Vergleich wird nur berichtet, nicht als vom BP5-Befund
   genannte Vorbedingung geprüft. `verify` überprüft `row_sha256` nicht;
   `disjoint` bindet keine unabhängige Quellidentität. Gleicher Text mit
   unterschiedlichen Aktivierungen kann deshalb als getrennt erscheinen.
   Das Modul selbst aktiviert kein Training und schaltet L3 nicht frei.
2. BP9c/BP9d: Die veröffentlichten Zahlen ergeben rechnerisch die registrierten
   engen Urteile PASS bzw. FAIL. Der alte Antwortprüfer erlaubt allerdings
   Teilstrings und kann eine verneinte Antwort als Treffer zählen. Die einzelnen
   Modelltexte sind in den vorhandenen Ergebnisdateien nicht enthalten; deshalb
   kann der Einfluss auf die alten Zahlen nicht nachträglich festgestellt werden.
   Der SGD/AdamW-Vergleich änderte auch die Lernrate und isoliert die Ursache
   nicht. BP9c lernt korrekte Eigenetiketten ebenso wenig wie falsche.
3. `AgeControl.plasticity`: Bei `boot` und `stable_reopen` fallen nach vier
   unabhängigen Rauschwerten die dokumentierten Mindestwerte für ausdrücklich
   markierte neue Domäne/Modalität weg; bei `noise_aware` bleiben sie erhalten.
4. Weitere Gegenprüfung ergab mögliche Fehler bei der Erkennung beantworteter
   Fragen und bei der Seitenfortsetzung von Retrieval-Feedback. Diese Punkte
   werden noch genauer eingegrenzt; Standard-SHADOW ist keine aktive Freigabe.

Die Kandidaten werden getrennt vom eingefrorenen Runtime-Code vorbereitet.
Originaldaten, `BP9d_FAIL`, `BP9c_PASS` mit seiner Einschränkung, STEP2
`UTILITY_FAIL`, B3 L2 FAIL/L3 gesperrt und alle übrigen bestehenden Tore bleiben
unverändert. Vorregistrierungs-Commits vor Ergebnis-Commits nachgewiesen;
die Commit-Reihenfolge allein belegt nicht den tatsächlichen Messbeginn.

Offen: vollständige Gegenbeispiele für alle betroffenen Guards,
Überprüfung und Tests der Kandidaten, Remote- und zweite Sicherung.
