# WP-Z5c: Aktualitäts-Term für Notizen in der Fokus-Koalition (G-FOCAL-CAPACITY-003), 2026-10-21

Vorregistrierung: `PREREGISTRATION.md` (vor dem Lauf committet, Nachtrag nach Probelauf, Regeln unverändert). Code: Schalter
`focal_note_recency` (`v13/config.py`, **Standard 0 = aus**), `note_slot`/`note_versions` in `v13/focal.py`. Skript
`code/scripts/z5c_recency.py`, Tests `code/tests/test_z5c_recency.py` (9, ohne Modell). Rohdaten `z5c.json`, Protokoll `run.log`.

Aufbau: Z5b-Aufgaben, **3 Aufgaben-Saaten (11 = Z5b, 12, 13) × 2 Läufe × 60 = 360 Turns**, Notizen in realer Reihenfolge
gespeichert, Live-Turn mit Schalter an, Koalition ohne Term kontrafaktisch aus denselben Kandidaten (Wieder-Aufnahme-Treue
360/360), Antworten im selben Turn an dasselbe Organ (Wiedergabe-Treue 100 %). Platzgrenze bindet 360/360 (9 Kandidaten, 4 Plätze).

## Der Term wirkt im Mechanismus …

| gemessen (ohne Modell-Urteil) | mit Term | ohne Term |
|---|---|---|
| update: neueste Budget-Notiz in der Koalition | **1,00** | 0,90 |
| update: veraltete Versionen in der Koalition | **0,00** | 0,95 |
| combine: benötigte Notizen in der Koalition | **0,75** | 0,63 |
| combine: veraltete Version in der Koalition | **0,00** | 0,96 |
| correction: Korrektur in der Koalition | 0,89 | 0,89 |

Die Koalition unterscheidet sich in 257 von 360 Turns.

## … aber nicht in den Antworten

| Arm | bestanden (360) | Saat 11 / 12 / 13 | Kontext (Zeichen) |
|---|---|---|---|
| shipped_live (Notizen immer in der Antwort) | 107 | 35 / 38 / 34 | 2010 |
| coalition_recency | 93 | 28 / 32 / 33 | 1556 |
| coalition_plain | 90 | 31 / 26 / 33 | 1415 |
| full_context | 97 (von 357) | 32 / 31 / 34 | 2730 |
| retrieval_only | 98 | 31 / 30 / 37 | 559 |
| no_context | 64 | 20 / 17 / 27 | 0 |

Gepaart (Vorzeichentest), `coalition_recency` nur / Kontrolle nur: vs. coalition_plain **24:21 p = 0,77** (Vorsprung 0,5 je Lauf);
vs. full_context **30:35 p = 0,62** (−0,8); vs. retrieval_only 55:60 p = 0,71; vs. no_context 48:19 p = 0,0005; vs. shipped 25:37 p = 0,16.
Rauschband (shipped_live zwischen den zwei Läufen einer Saat) = 2. 5 Wiedergaben übersprangen wegen Kontextfenster (full_context 3, shipped 2).

Nach Art (recency / plain / full / retrieval / none): update 0,28 / 0,31 / **0,48** / 0,39 / 0; correction 0,14 / 0,14 / 0,08 / **0,47** / 0;
distract 0,61 / 0,54 / 0,52 / 0,23 / **0,71**; combine überall 0.

**Verdikt (vorregistrierte Regeln):** „Term hilft“ **FAIL**, „schlägt Voll-Kontext“ **FAIL**, nicht schlechter als Retrieval: ja.
Eigenschaft 4 nicht neu gemessen → **G-FOCAL-CAPACITY-003 bleibt PARTIAL.** Schalter bleibt aus.

## Befunde
1. Die Vorhersage „hilft bei update“ trifft im Mechanismus zu, in den Antworten **nicht**: Bei `update` ist die Koalition mit Term
   *schlechter* als Voll-Kontext (3:21, p = 0,0003, nachträglich je Art, nicht vorregistriert), obwohl sie immer die richtige
   und nie eine veraltete Notiz enthält.
2. Grund liegt hinter der Koalition, beim antwortenden Organ: Bei schmaler Koalition (2 Notizen + 2 Angebote) antwortet es in
   33 von 82 update-Turns nur „2“ (Voll-Kontext: 12 von 90). Die Frage lautet „laut der neuesten Budget-Notiz“; steht nur eine
   Budget-Notiz da, findet das kleine Modell offenbar keinen Bezug. Das ist eine Deutung aus den Ausgaben, kein Test.
3. `correction` ändert der Term wie vorhergesagt nicht (Korrektur gegen die Zahl in der Nachricht hat keinen Notiz-Zwilling).
   Retrieval bleibt dort mit 0,47 am besten, wie in Z5b.
4. `distract` profitiert leicht von jeder Koalition (0,61 vs. 0,52 Voll-Kontext, n. s.); ohne Kontext ist am besten.
5. Die Koalition spart weiter Kontext (−43 % gegenüber Voll-Kontext), ohne messbaren Verlust gepoolt.

## Abweichungen und Grenzen
- Zwei Container-Neustarts (der erste Versuch brach nach 13 Aufgaben ab, `run_crash1_container_restart.log`; danach Zwischenspeicher
  je Aufgabe). In Saat 13 Lauf 1 wurden einige Aufgaben nach einem Neustart in einem neuen Home fortgesetzt (Aufgaben sind
  unabhängige Sitzungen, `history_turns = 0`). Keine Regeländerung.
- Die kontrafaktische Koalition ersetzt nur die letzte Aufnahme; frühere Zyklen und Re-entry liefen mit Schalter an.
- Generierte englische Aufgaben derselben Vorlagen, Monatsnamen im Schlüssel als Versionsmerkmal, Regex auf der Endantwort,
  lexikalischer Recall, gierige Dekodierung, Cloud-CPU statt Redmi.

## Nächster Schritt (neu vorzuregistrieren)
Nicht die Koalition, sondern die Darstellung: veraltete Versionen nicht wegwerfen, sondern als „ersetzt durch …“ markiert in
den Kontext geben (Ersetzungs-Kette sichtbar), oder die Frage-Bezüge („neueste Notiz“) beim Antworten auflösen. Vorher prüfen,
woher die „2“-Antworten kommen (Körper-Angebote im Kontext lesen).
