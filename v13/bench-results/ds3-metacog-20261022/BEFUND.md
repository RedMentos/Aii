# WP-DS3 Befund: kalibrierte Unsicherheit wählt antworten / nachrechnen / „unsicher“ (2026-10-22)

**Verdikt: NOT_SUPPORTED (H2 Nutzen verfehlt).** H1, H3, H4 PASS. Vorregistrierung `PREREG.md`/`PREREG.json` (Commit 7b931be, vor dem Lesen der frischen Läufe), Bericht `report.json`, frische Aufnahmen `fresh/` (Seeds 31 + 37, 120 Aufgaben, echte C3 LFM2.5-350M, Cloud-CPU).

| Politik | richtig | falsch | „unsicher“ | Punkte (λ=1) | Punkte (λ=2) |
|---|---|---|---|---|---|
| C3 allein | 82 | 38 | 0 | 44 | 6 |
| immer Rezept (R4 Teil 5) | 107 | 13 | 0 | 94 | 81 |
| **DS3** | 106 | 11 | 3 | **95** | 84 |

- H1 PASS: Die Unsicherheit trägt auf frischen Aufgaben (AUROC 0,78 für „Antwort falsch“), der AG9-Kalibrierer aus den Entwicklungsdaten ist gut kalibriert (ECE 0,076).
- H2 FAIL: nur +1 Punkt statt ≥ +5; falsche Antworten 11 statt 13 (0,85 ×, gefordert ≤ 0,7 ×).
- H3 PASS: 2 von 3 „unsicher“-Fällen wären sonst falsch gewesen.
- H4 PASS: nur eine richtige Antwort verloren.

**Lesart.** Das Werkzeug (Modell liest Zahlen, festes Rezept rechnet) hat die meisten Fehler schon beseitigt (38 → 13). Von den 13 Restfehlern sind nur wenige unsicher: Die meisten falschen Antworten sind *selbstsicher* falsch (z. B. richtige Differenz, aber falsche Stadt genannt; bei „compare“ 6 von 9 Restfehlern). Ziffern-Unsicherheit sieht solche Fehler nicht, weil sie im Namen und nicht in der Zahl stecken. „Unsicher sagen“ wirkt also in die richtige Richtung, ist aber zu selten, um messbar zu nützen.

**Folge (Vorschlag, eigene Vorregistrierung nötig).** (1) Unsicherheit auch für Namen-Tokens messen, nicht nur für Ziffern; (2) die Antwort gegen das Rezept-Ergebnis prüfen (nennt die Antwort den vom Rezept bestimmten größten Posten?) — eine feste Gegenprobe statt Gefühl; (3) für WP-SAFE2 „nachfragen statt raten“ bleibt SHADOW. Keine Laufzeit-Änderung.

**Grenzen.** Generierte englische Aufgaben, Regex-Prüfung, „unsicher“ als Enthaltung gewertet (das Modell formuliert es nicht), Entwicklungsdaten mit älterem Laufzeit-Stand (Thread K, 13.10.), frische Läufe mit Stand Branch hmopsm (22.10.); kein Handy.
