# Befund WP-Z6 §24.25 Observer-Pass-Nutzen (2026-10-26)

Vorregistriert in `2266dc4` (vor dem Lauf gepusht). 75 Aufgaben, Saat 59, 5 Arme, echte Modelle, Cloud-CPU.
Daten `v13/bench-results/z6-observer-utility-20261026/` (z6obs.json, run.log).

## Urteil nach Regel: `ADAPTIVE_PREFERRED`, aber kein Beobachter-Arm schlägt „keiner“
- O1 Always-Pass schlägt keinen: **nein** (AB 40 vs. none 48; 8:16, p = 0,15).
- O2 adaptive billiger und nicht schlechter als AB: **ja** (36 vs. 40, 6:10, p = 0,45; 6,9 s statt 11,5 s).
- O3 Always-Pass schadet nicht signifikant: **ja** (p = 0,15).

| Arm | bestanden/75 | Zeit bis FINAL | Zusatz vs. none | summary | long | notes | compare | correction |
|---|---|---|---|---|---|---|---|---|
| none | **48** | 1,7 s | – | 8 | 15 | 14 | 4 | 7 |
| A (nur B1) | 42 | 6,6 s | +4,9 s | 5 | 15 | 9 | 8 | 5 |
| B (nur B2) | 35 | 6,6 s | +4,9 s | 8 | 15 | 10 | 2 | 0 |
| AB (immer beide) | 40 | 11,5 s | +9,9 s | 7 | 15 | 8 | 7 | 3 |
| adaptive | 36 | 6,9 s | +5,2 s | 11 | 15 | 6 | 4 | 0 |

Gepaart gegen none: A 9:15 (p = 0,31), B 3:16 (**p = 0,004**), AB 8:16 (p = 0,15), adaptive 6:18 (**p = 0,023**).

## Was die Beobachter sehen, und was davon ankommt
- Konflikt-Erkennung (summary/notes/correction, 45): B 45/45, AB 45/45, adaptive 41/45, A 29/45.
- Korrektur gesehen: in allen Beobachter-Armen nennt ein Angebot 15/15 den neuen Tag. In der Antwort übernommen:
  none 7/15, A 5, AB 3, B 0, adaptive 0.
- Unnötig: auf allen 48 Aufgaben, die none schon besteht, liefen in jedem Beobachter-Arm Beobachter (48/48).
- Zweiter Versuch (Re-entry) selten: 4–6 je Arm, kein messbarer Vorteil.
- Gewinn nur bei compare (Rechnen mit drei Werten): A 8 und AB 7 statt 4.

## Was das heißt
Die Beobachter erkennen Widersprüche und Korrekturen fast immer, aber C3 macht aus ihren Angeboten schlechtere
Antworten (notes 14 → 6–10, correction 7 → 0–5). Der Engpass ist nicht das Erkennen, sondern die Übernahme in die
Antwort; das passt zu WP-Z3 (`NO_CONSUMER_PATH`) und zur Werkzeug-Entscheidung vorn (22.10.), wo erst eine feste
Übernahme half. Der Always-Pass rechtfertigt seinen Preis hier nicht (+9,9 s je Antwort, kein Gewinn). „adaptive“ gewinnt
das Urteil nur, weil es billiger als AB ist; gegen none verliert es signifikant. Die gelernte Beobachter-Frequenz
(jefbridge) senkt nur die Zeit und zählt fast jedes Angebot als „nützlich“ (Antwort-Abdeckung), sie misst also nicht,
ob die Antwort besser wird.

## Folgen (nicht Teil des Urteils)
- Kein Standardwechsel in diesem Paket. Vorschlag für ein neues Paket: Beobachter nur bei Bedarf (z. B. Rechnen/Vergleich
  oder wenn der C3-Entwurf unsicher ist) und Angebote nur als feste, geprüfte Zeile übernehmen statt als freien Kontext.
- Das Nutzen-Signal der Beobachter-Frequenz sollte „Antwort richtig“ sein, nicht „Antwort deckt Angebot ab“.

## Grenzen
Generierte englische Aufgaben, Regex-Prüfung, ein Seed, deterministische Dekodierung, Cloud statt Redmi. Energie, Wärme,
Speicherbandbreite, Page-Faults nicht gemessen (Handy). Konflikt-Erkennung per Wortliste auf den Angeboten.
