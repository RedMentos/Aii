# Werkzeug-Vorhersage: Kompetenz-Signal vor dem Effekt

Stand 2026-10-13, Thread „Nächste offene Pakete M“, Linux-Cloud (nicht Redmi). Vorregistriert `8b15627` vor dem Lauf.

**Ergebnis: COMPETENCE_SIGNAL_NOT_CONFIRMED.** Notizen bestehen, Rechnen nicht.

| Welt | AUROC | In-Welt markiert | Außer-Welt markiert | Gate |
|---|---|---|---|---|
| note_edit (Vokabular vs. freie Notizen) | 1.00 | 3 % | 100 % | PASS |
| calc_counter (1..999 vs. 1000..9999) | .96 | 3 % | **37 %** (Gate ≥ 80 %) | FAIL |

- Signal: mittlerer Kosinus-Abstand des Kontext-Taps zu den 5 nächsten Trainingskontexten, Schwelle = 99. Perzentil der Kalibrierungs-Partition (keine Test- oder Live-Daten). Je 30 frische Zustände je Arm, 420 Aufrufe durch den Live-Pfad, alle SCORED, Live-Check auf diesem Plan erneut LIVE_PATH_CONFIRMED.
- Bei Zahlen trennt der Abstand gut (Median .009 vs .033), aber die Schwelle (.035) liegt zu hoch: vierstellige Zähler wirken für den Tap fast wie dreistellige. Keine Schwellen-Änderung auf diesen Daten (Regel).
- Nur Bericht: markierte Aufrufe sind tatsächlich schlechter (geometr. Mittel Vorhersage/beste Kontrolle: Notizen .07 unmarkiert vs .66 markiert, Rechnen .22 vs .55). Außer-Welt-Rechnen `quarter` erneut 1,18 (schlechter als die Kontrolle).
- Median 3,5 s je Aufruf, Tap-Prozess-Spitze ~1 GB.

Was jetzt gilt: jede SHADOW-Vorhersage trägt `competence` (Abstand, Schwelle, `in_domain`); nichts liest es. Für Notizen ist es ein brauchbarer Vorab-Hinweis, für Zahlen außerhalb 1..999 nicht. Eine neue Schwelle oder ein zahlbewusstes Merkmal (z. B. die bereits deterministisch bekannte Wertgrenze `in_world_range`) braucht einen neuen, vorregistrierten Lauf.

Dateien: `preregistration.json`, `plan.json`, `report.json`, `live-report.json`, `rows.json` (alle 420 Aufrufe mit Abstand und Fehlern).
