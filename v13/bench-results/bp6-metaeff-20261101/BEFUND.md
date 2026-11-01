# WP-BP6 / FS3: meta_i auf echten DS3b-Aufnahmen (2026-11-01)

**Vorabüberlegung:** Daten da (300 echte C3-Antworten, Seeds 41/43/47/53/59, LFM2.5-350M), Verbraucher da (Enthalten-Regel `abstain_utility`), sichtbarer Gewinn laut DS3b groß (Ziffern-Konfidenz AUROC 0,84). Also sinnvoll. Gegenprobe-Teile von BP6 (Wecken, Denktiefe, Angebote) bleiben zurückgestellt, weil sie BP1 (C3 verwertet Angebote) brauchen.

**Frage:** Sagt `meta_i` voraus, welche Konfidenzquelle sich beim Enthalten lohnt? (Vorregistriert vor dem Lauf: Rangfolge meta_i soll mit Rangfolge Enthalten-Gewinn übereinstimmen.)

| Quelle | meta_i | AUROC2 | ECE | Enthalten-Gewinn |
|---|---|---|---|---|
| Ziffern-Mindestwert | 0,359 | 0,877 | 0,073 | 17,8 |
| mittlere Wahrscheinlichkeit | 0,188 | 0,758 | 0,129 | 2,3 |
| Anteil sichere Token | 0,155 | 0,747 | 0,180 | 2,1 |
| kleinster Tokenwert | 0,151 | 0,729 | 0,393 | 0,0 |
| 10. Perzentil | 0,111 | 0,719 | 0,248 | 1,4 |

202 von 300 richtig. **Ergebnis:** die Ränge stimmen bis auf das Paar „kleinster Tokenwert / 10. Perzentil“ (beide praktisch ohne Nutzen) überein; die beste Quelle ist mit Abstand die Ziffern-Konfidenz, wie DS3b gefunden hatte. meta_i leistet hier also mehr als ECE allein (ECE sieht „kleinster Tokenwert“ nur als schlecht kalibriert, meta_i als schwach trennend). Aussage nur: Messgröße ist brauchbar, nicht dass sie das Paper-Maß ist (nur Abstract gelesen). Nur eine Aufgabenart, nur ein Modell.

Skript: `code/scripts/bp6_metaeff_ds3b.py`, Bericht `report.json`, Eingaben `in/` (Kopien der öffentlichen DS3b-Aufnahmen).
