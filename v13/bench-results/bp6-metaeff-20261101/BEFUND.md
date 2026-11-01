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

## FS4 Selbstvorhersage mit echtem Vorhersager (2026-11-01)
**Vorabüberlegung:** Daten da (150 Werkzeug-Aufgaben, vorher/nachher richtig), Verbraucher wäre „Werkzeug nur rufen, wenn es nötig ist“, Gewinn nur sichtbar, wenn der Zustand mehr verrät als der Fragetext. Frage: „Ändert das Rechenwerkzeug, ob meine Antwort stimmt?“ Vorhersager: kleine logistische Regression auf den Konfidenz-Merkmalen des ersten Durchgangs (Zustand), Kontrolle: nur Fragetext. Je Seed ausgelassen (leave-one-seed-out), Vorhersage vor der Nachprüfung.

**Ergebnis: NO_SELF_ADVANTAGE.** Änderungsrate 0,507 (Grundrate-Treffer 0,507), Zustand 0,527, nur Fragetext 0,460, perm_p 0,17. Der Zustand sagt nicht vorher, ob das Werkzeug etwas ändert. Passt zu DS3b: Fehler sind selbstsicher, die Sicherheit trägt dafür kaum Information (nur Ziffern-Mindestwert trennt richtig/falsch, aber das ist eine andere Frage). Kein Beleg für Selbstwissen; das Ziel „ändert sich die Antwort“ mischt zudem beide Richtungen (65 falsch→richtig, nur 11 richtig→falsch). Nächste mögliche Fassung: nur „wird das Werkzeug mir helfen“ (falsch→richtig) mit Ziffern-Konfidenz; erst sinnvoll mit eigener Vorregistrierung.
Code: `v13/agi/selfpredictor.py`, `scripts/bp6_selfpredict_ds3b.py`, Bericht `selfpredict.json`.

### FS4b enger: „Hilft mir das Werkzeug?“ (falsch→richtig), 2026-11-01
**Vorabüberlegung:** Gewinn sichtbar höchstens als Kostenersparnis (Werkzeug weglassen, wo es nichts bringt), denn Genauigkeit liefert „immer Werkzeug“ schon. Nach DS3b ist das fast dieselbe Frage wie „bin ich falsch“, also wenig Neues; billig genug zum Mitnehmen. Maßstab wie vorher (Treffer bei Schwelle 0,5 gegen beide Kontrollen +0,05, perm_p<.05), Schwelle nicht nachträglich verändert.
**Ergebnis: NO_SELF_ADVANTAGE.** Hilfe-Rate 0,433, Grundrate-Treffer 0,567, Zustand 0,540, Text 0,480; die Rangfolge trägt schwach (perm_p 0,046), aber nicht genug, um bei Schwelle 0,5 die Grundrate zu schlagen. Kein Beleg für Selbstwissen, keine Konfidenz-Weiche fürs Werkzeug empfohlen. Aufruf: `FS4_TARGET=help python scripts/bp6_selfpredict_ds3b.py …`. pytest installiert, `test_agi_metaeff.py` 5 grün.
