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
4. Retrieval-Reconsolidation: Bei 512 verwaisten Bewertungen oder 512 gleichen
   Zeitstempeln können nachfolgende gültige Bewertungen dauerhaft hinter der
   Seitengrenze liegen. Die Sortierung kann im ausdrücklich aktiven Modus dann
   veraltete Bewertungen verwenden; Standard-SHADOW ändert die Reihenfolge nicht.
   Außerdem ist die Wirkung von Feedback mit `permission=record` auf die
   ausdrücklich aktive Sortierung gesondert gegen die Nutzungsregeln zu prüfen.
5. `hypothesis_stale`: Im optionalen aktiven Modus genügt eine spätere finale
   Antwort wie „Ich weiß es nicht“, damit die Frage als beantwortet verschwindet.
6. Die Sleep-D-Checkliste erkennt manche privaten Angaben (z. B. Telefonnummern
   in Inlandsform) nicht und die Traum-Faktenprüfung betrachtet nur die 1024
   neuesten aktiven Fakten. Ein fehlerhafter expliziter Moduswert kann Filterung
   umgehen. Die Vorfilter dürfen daher nicht als vollständiger Schutz gelten.
   Das Gegenbeispiel zeigte nur einen Staging-Kandidaten, kein Training.
7. `world_jepa_slots.confidence` prüft das Aktionsformat im Gegensatz zur
   Kalibrierung nicht; `collapse_stats` wirft für einen zulässigen eindimensionalen
   Latentraum. Beides betrifft hier unverbundene SHADOW-Diagnostik.
8. BP8-Rauschmessung: Die angeblich unabhängigen Hälften enthalten systematisch
   Originale bzw. Paraphrasen. Ein Unterschied zwischen diesen Formaten kann
   als Rauschen erscheinen. Für die schon als NO_SIGNAL dokumentierten BP8b/c
   wurde dadurch kein nachgewiesener Ergebniswechsel behauptet.
9. Das bestehende `sandbox_note` folgt Links: Ein manipulierter Ordner kann
   Schreibzugriffe umleiten, ein Dateilink kann schon im Preview fremden Inhalt
   offenlegen. Zwei konkurrierende `ToolRegistry.approve`-Aufrufe können dieselbe
   Freigabe zweimal ausführen. Ein Notaus kann eine bereits zwischen Prüfung und
   Start befindliche Aktion nicht sicher rückgängig machen. Gegenproben fanden
   ausschließlich in temporären Testordnern bzw. mit Speicherzähler statt.

**Isolierte Kandidaten:**

- `code/scripts/b3pair_integrity_candidate.py` prüft getrennt rekonstruierte
  Manifeste, identische Quellen über Aktivierungswechsel hinweg, zwei Saaten,
  gültige Messwerte und konservativ L1 > SCALAR. Pro Kohorte sind mindestens
  3000 verschiedene Quellgruppen nötig; bei der Gegenprüfung wäre die bloße
  Wiederholung einer Quelle zunächst durchgekommen, was nun abgefangen wird.
  Die Aufrufer müssen dieselben stabilen Quellgruppen-IDs und einen externen
  HMAC-Schlüssel vertrauenswürdig bereitstellen. Der Kandidat rechnet die
  Genauigkeiten nicht aus Rohvorhersagen nach, beweist keine Signifikanz und
  ersetzt keines der L2-/L3-Tore.
- `code/scripts/age_reopen_candidate.py` erhält bei expliziter Neuheitsmeldung
  die Grenzwerte für alle drei Policies. Keine Änderung von Rechten oder Zustand.
- `code/scripts/strict_answer_auditor_candidate.py` bewertet nur einen engen
  JSON-Vertrag mit genauem Aliasabgleich für künftige Versuche. `MATCH` beweist
  lediglich diese Übereinstimmung; Aliase müssen stimmen und Rohantworten für
  eine unabhängige Nachprüfung separat sicher aufbewahrt werden. Hashes sind
  keine Anonymisierung. Alte Ergebnisse wurden damit nicht neu ausgewertet.
- `code/scripts/reconsolidation_pagination_candidate.py` hält einen getrennten,
  explizit verarbeiteten Rückmeldungszustand mit Fortsetzung über Seiten und
  Neustarts. 21 Tests mit echtem SQLite einschließlich bestehender Schlaf-Tests
  bestanden. Die Liste wächst; spätere Löschung bereits übernommener Feedbacks
  wird noch nicht abgeglichen. Keine Migration oder aktive Recall-Änderung.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python3 -m unittest -v test_b3pair test_b3pair_integrity_candidate test_age_reopen_candidate test_age test_bp8_real_age test_lora_session test_strict_answer_auditor_candidate`:
49 Tests OK. Die Kandidaten sind nicht mit der Runtime verbunden.

Originaldaten, `BP9d_FAIL`, `BP9c_PASS` mit seiner Einschränkung, STEP2
`UTILITY_FAIL`, B3 L2 FAIL/L3 gesperrt und alle übrigen bestehenden Tore bleiben
unverändert. Vorregistrierungs-Commits vor Ergebnis-Commits nachgewiesen;
die Commit-Reihenfolge allein belegt nicht den tatsächlichen Messbeginn.

Offen: weitere Gegenbeispiele für alle betroffenen Guards, tatsächliche
Vorhersagen und Quellbelege für neue Messungen, Integration erst nach Review;
Notiz-/Freigabe-Kandidaten und erste praktische Start-/Harness-Schritte werden
bearbeitet. Zweite Sicherung auf dem bestehenden Drive am 2026-11-05 mit
`storageQuotaExceeded` gescheitert; dort wurde kein Erfolg behauptet.
