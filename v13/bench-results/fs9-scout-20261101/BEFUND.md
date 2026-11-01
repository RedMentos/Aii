# WP-FS9 Späher-Sonden Befund (2026-11-01)
**Verdikt (wie vorab festgelegt): NO_SCOUT_GAIN.** 300 DS3b-Aufgaben, 33 % falsch. Hidden States von LFM2.5-350M (Prompt-Näherung), Leave-one-seed-out, 32 Hauptkomponenten, logistisch.
| Vorhersage „B1 wird falsch“ | AUROC gesamt | innerhalb der Aufgabenarten |
|---|---|---|
| nur Aufgabenart | 0,875 | – |
| Fragetext-Merkmale (Länge, Zahlen, Art) | 0,855 | 0,29 bis 0,40 (unter Zufall) |
| Sonde letzter Token, Ende | 0,867 | 0,45 bis 0,69 |
| Sonde letzter Token, Mitte | 0,865 | 0,28 bis 0,59 |
| Sonde Mittel, Ende / Mitte | 0,850 / 0,835 | meist < 0,5 |
Referenz nach dem Erzeugen: Ziffern-Konfidenz 0,877.

**Lesart.** Fast die ganze Trennschärfe kommt davon, welche **Aufgabenart** es ist (Rechenaufgaben richtig, Namen-Aufgaben falsch). Innerhalb einer Art liegen die Sonden bei Zufall; 300 Beispiele und 32 Komponenten sind wenig, aber es gibt kein Anzeichen für ein Zustandssignal darüber hinaus. Für den Router heißt das: Aufgabenart als Merkmal reicht und ist billig; Sonden-Ausbau nicht lohnend, solange keine größere und innerhalb-der-Art ausgewogene Datenbasis da ist. Grenzen: Prompt-Format der Aufnahmen unbekannt, ein Modell, eine Sondenfamilie, Ansicht (Schicht/Pooling) wurde nach Ergebnis gewählt (mit 4 Ansichten, Urteil gilt trotzdem für alle). Hidden-States-Datei (4,9 MB) nicht abgelegt; Skript `scripts/bp_fs9_scout_probe.py` erzeugt sie neu (torch+transformers nötig).
