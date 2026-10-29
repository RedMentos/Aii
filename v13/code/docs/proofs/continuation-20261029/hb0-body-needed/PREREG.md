# WP-HB0 Vorregistrierung: Aufgaben, bei denen die Teilmodelle nötig sind (2026-10-29)

Herkunft: `v13/diagnose/URSACHENANALYSE_HIRNAEHNLICHKEIT_20261029.md`, Ursache G und Schritt P0.

## Frage
Gibt es Aufgaben, bei denen ein Zusammenspiel der Teilmodelle (B1 Detail, B2 Überblick, C3 Entscheider) überhaupt Platz zum Gewinnen hat?
Frühere Bänke hatten das nicht: Das Orakel "perfektes Wecken" löste nur 45 gegen 42 von 60 (R4), C3 allein reichte.

## Aufgaben (Skript `scripts/hb0_body_needed_tasks.py gen`, Saat 20261029)
152 erzeugte englische Texte von 10 800 bis 12 000 Zeichen (rund 3000 Token, länger als das C3-Fenster von 2048 Token).
Vier Familien mit je 38 Aufgaben: D verstreute Aufzählung (alle Bestellmengen eines Projekts nennen, alle müssen vorkommen), S Änderungskette (aktueller Wert nach mehreren Neufestsetzungen), G globaler Vergleich (größter Zuwachs), C späte Korrektur (Tag und Grund).
Anpassung vor dem gewerteten Lauf: Im Probelauf (8 Aufgaben, nicht gewertet) konnte selbst B1 mit den Goldsätzen keine Summe bilden. Deshalb wurden D und S von Rechenaufgaben auf Aufzählung und Ersetzungskette umgestellt. Rechnen übernimmt im System das Rechen-Werkzeug, das hier nicht geprüft wird.
Die Goldsätze (die nötigen Sätze) kennt der Erzeuger. Bewertung nur per Regex auf die Endantwort.

## Arme (alle Temperatur 0)
`c3_head`, `c3_tail` (C3 sieht Anfang oder Ende), `c3_rag` (C3 mit den Sätzen höchster Wortüberlappung zur Frage),
`b1_long`, `b2_long` (Körper liest alles allein, Fenster 8192), `or_c3`, `or_b1` (Orakel: nur die Goldsätze),
`pipe` (B1 zieht pro Abschnitt Zeilen, B2 schreibt Überblick, C3 antwortet).

## Entscheidungsregel (vor dem Lauf festgelegt)
- `C3_BEST` = bester der drei C3-Arme ohne Körper (`c3_head`, `c3_tail`, `c3_rag`).
- **Aufgabensatz geeignet (HB0_BODY_ROOM)**, wenn gleichzeitig:
  1. `C3_BEST` löst höchstens 50 Prozent (76 von 152),
  2. das Orakel der Körper `or_b1` löst mindestens 15 Aufgaben mehr als `C3_BEST` (Plan: 15 von 150),
  3. die Lücke steckt in mindestens zwei der vier Familien (je Familie Orakel minus `C3_BEST` ≥ 4).
- **Hinweis auf nutzbaren Weg**, wenn zusätzlich `pipe` > `C3_BEST` um mindestens 15 (Rauschband: gleiche Konfiguration zweimal, gepaarter Vorzeichentest p < 0,05).
- Ist `b1_long` ≥ `pipe`, gilt: Ein größeres Modell, das alles liest, reicht. Dann ist das Argument für das Zusammenspiel der Teile hier nicht gezeigt, und das wird so berichtet.
- Ergibt sich HB0_BODY_ROOM nicht, wird der Aufgabensatz nicht für P2 benutzt und der Befund berichtet, was fehlt.

## Grenzen
Erzeugte Texte, Regex-Bewertung, rohe Modelle über llama-server ohne die V13-Laufzeit (kein Wake, keine Stores).
`pipe` ist eine einfache Text-Pipeline, kein Maß für die spätere gelernte Kopplung.
Pilot auf 8 Aufgaben nur zum Prüfen des Gerüsts, nicht gewertet.
