# WP-DS3b Befund: Namen-Unsicherheit + feste Gegenprobe Antwort ↔ Werkzeug (2026-10-22)

**Verdikt (vorregistriert): NOT_SUPPORTED wegen H1** (Namen-Unsicherheit hilft nicht). **H2, H3, H4 PASS**: die feste Gegenprobe trägt.
Vorregistrierung `PREREG.md`/`PREREG.json` (Commit 8de2994, vor dem Lesen der frischen Läufe), Bericht `report.json`, Aufnahmen `dev/` (Seeds 41, 43) und `fresh/` (Seeds 47, 53, 59; 180 Aufgaben; echte C3 LFM2.5-350M, Cloud-CPU, Laufzeit Branch hmopsm).

| Politik (frisch, 180 Aufgaben) | richtig | falsch | „unsicher“ | Punkte λ=1 | λ=2 | streng: falsch / Punkte |
|---|---|---|---|---|---|---|
| C3 allein | 122 | 58 | 0 | 64 | 6 | 59 / 62 |
| immer Rezept (Basis) | 155 | 25 | 0 | 130 | 105 | 39 / 102 |
| nur Ziffern-Unsicherheit (DS3) | 155 | 23 | 2 | 132 | 109 | 37 / 104 |
| Ziffern + Namen | 154 | 22 | 4 | 132 | 110 | 35 / 106 |
| Gegenprobe allein | 150 | 7 | 23 | 143 | 136 | 16 / 125 |
| **ds3b (Hauptpolitik)** | 149 | **6** | 25 | **143** | 137 | 14 / 127 |
| Gegenprobe + feste Antwort aus Werkzeug (nur berichtet) | 171 | 9 | 0 | 162 | 153 | 18 / 144 |

- **H1 FAIL** (wie vorhergesagt): AUROC Ziffern+Namen 0,79 gegen nur Ziffern 0,84. Die falschen Städtenamen werden vom kleinen Modell *mit hoher Sicherheit* gewählt; Token-Wahrscheinlichkeit misst hier kein Wissen.
- **H2 PASS**: Gegenprobe schlägt bei 23 von 90 Werkzeug-Aufgaben an, 18 davon wären falsch gewesen (78 %); sie findet 18 von 21 falschen Werkzeug-Antworten (86 %). Gründe: falsche größte Stadt 13, Ergebnis fehlt 8, falsche Summe nicht als falsch benannt 2.
- **H3 PASS**: +13 Punkte (143 gegen 130, gefordert +7), falsche Antworten 25 → 6 (0,24 ×), 86 % beantwortet.
- **H4 PASS**: 6 richtige Antworten verloren (erlaubt 9).

**Lesart.** Selbstsichere Fehler sieht man nicht an der Unsicherheit, sondern nur durch eine **unabhängige Probe**: das Rechenwerkzeug kennt den größten Posten, also kann eine feste Regel die Antwort damit vergleichen. Das ist Metakognition durch Nachprüfen statt durch Gefühl. Die Namen-Unsicherheit wird nicht weiter verfolgt.
**Streng gewertet** (auch falsche „kleinste Stadt“ oder falsche Zahl zu einer Stadt zählt als Fehler) hat die Basis 39 statt 25 Fehler: die Bench-Regex ist nachsichtig. Die Gegenprobe senkt auch diese auf 14.
**Kosten:** „unsicher“ fällt fast nur bei den Vergleichsaufgaben (21 von 45). Die nur berichtete Variante „bei Fehlschlag die feste Werkzeug-Antwort geben“ (162 Punkte, keine Enthaltung) ist die naheliegende nächste Stufe, braucht aber eine eigene Vorregistrierung, weil der feste Satz zur Bench-Prüfung passt.

**Folge (Vorschlag).** Gegenprobe als SHADOW-Schalter in die Laufzeit (`toolstep`), Standard **aus**; Handy-Messung vor `active`. Danach eigene Vorregistrierung für „Werkzeug-Antwort statt raten“ auf frischen Seeds (61+) und auf einer zweiten Aufgabenart.

**Grenzen.** Generierte englische R4-Aufgaben (4 Arten), Regex-Prüfung, Gegenprobe ist auf „Summe“ und „größter minus kleinster“ zugeschnitten, Wortlaute an früheren R4-Läufen geschrieben; „unsicher“ als Enthaltung gewertet; Cloud-CPU, kein Handy; keine Laufzeit-Änderung.
