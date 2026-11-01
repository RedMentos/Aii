# Werkzeug-Vorhersage lernt aus eigenen Aufrufen — Ergebnis NOT_CONFIRMED

Stand 2026-10-13, Thread „Nächste offene Pakete M“, Linux-Cloud (nicht Redmi). Vorregistriert `f4a3c82` vor dem Lauf. 610 Live-Aufrufe, alle SCORED, 38 min.

**Befund: Lernen hilft auf neuen Fällen, würde aber die gelernte Welt beschädigen. Das Retentions-Gate hat deshalb jede Anpassung abgelehnt.**

| Welt | Gewinn auf Erfahrungs-Halteteil (angepasst / gemessen) | Retention (angepasst / gemessen, Gate ≤ 1.02) | Ergebnis |
|---|---|---|---|
| calc_counter (160 Aufrufe 1000..9999) | .11–.48 | 1.46–2.10 | alle 4 Handlungen abgelehnt |
| note_edit (90 Aufrufe freie Notizen) | .61–.67 | 1.53–3.27 | alle 3 Handlungen abgelehnt |

- Der verankerte Ridge-Rest lernt die neue Region gut: auf dem neuesten Viertel der Erfahrung sinkt der Fehler auf 11–67 %. Er verschiebt dabei aber die eine lineare Abbildung, und der Fehler in der alten Welt (Test-Partition des Kandidaten, Encoder dieses Geräts) steigt auf das 1,5- bis 3,3-Fache. Das ist klassisches Vergessen durch Interferenz.
- Da keine Handlung angepasst wurde, sind die Test-Vorhersagen identisch mit den gemessenen (Quotient 1.0). Das Gate hat wie vorgesehen das Vergessen verhindert, es gab aber keinen Lerngewinn.
- Gemessener Kandidat auf den frischen Testfällen, Anteil an der besten Kontrolle: Rechnen außerhalb der Welt .30–.82, in der Welt .10–.20; freie Notizen .62–.83, Vokabular .05–.09.

Folgerung: Ein einzelner globaler linearer Rest kann alte und neue Region nicht gleichzeitig tragen. Ein nächster Versuch muss neu vorregistriert werden. Kandidaten:
- Wiederholung alter Trainingspaare beim Neu-Anpassen. Dafür fehlen auf dem Gerät die alten Ziel-Taps; sie müssten mitgeliefert werden.
- Ein getrennter Rest pro Region, gesteuert über das Kompetenz-Signal. Bei Notizen trennt es sauber, bei Zahlen nicht.

Dateien: `preregistration.json`, `plan.json`, `learn.json` (je Handlung Raster, Halteteil, Retention), `report.json`, `rows.json` (alle 610 Aufrufe).
