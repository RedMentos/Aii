# WP-Z6i Vorregistrierung: neue menschliche Hinweise wirklich lernen (vor dem Lauf committet)

Anlass: Z6b/Z6c/Z6d. Neue menschliche Hinweise wurden nie übernommen; alte widersprechende Labels blockierten (Z6b);
das Ersetzen wirkt, aber der Kopf lernt die neue Grenze nicht, weil die eingefrorene Needle-Einbettung „Hälfte von X“ nicht
von anderen Rechenfragen trennt (Z6c); nur die feste Regel beim Antworten wirkt (Z6d), der Kopf selbst blieb bei 0 %.

## Was neu gebaut ist
1. **Wortkanal** `v13/route_words.py`: feste, deterministische Hash-Merkmale (Wörter, Wortpaare, Buchstaben-Dreier;
   Ziffern → `#`; kein Modell, nichts wird angepasst). Der Routen-Kopf bekommt sie zusätzlich zur Einbettung
   (`learning_worker.features(..., words)`), Schalter `route_head_words` (Standard aus bis zu diesem Urteil). Ein alter
   Kopf ohne Wortkanal wird mit Nullzeilen erweitert (gleiche Funktion, Warmstart bleibt). Ein Wortkanal-Kandidat darf
   zusätzlich **keine** vom aktiven Kopf richtig gerouteten menschlich gelabelten Fragen verlieren (`known_items_lost == 0`).
   **Anker gegen Überschwappen**: solange eine `--sofort`-Regel existiert, gehen bis zu 64 frühere, ungelabelte Fragen
   ohne Regelwörter mit der Route des aktiven Kopfes als weiches Ziel (Gewicht 0,5) ins Training („lernen ohne zu
   vergessen“); gemeldet wird, wie viele Anker sich trotzdem bewegen (`anchors_changed`), nicht gesperrt.
2. **Regel als Lehrer, nur mit Erlaubnis**: `:ersetze route <R> <Wörter> --sofort --lehre`. Fragen, die die Regel beim
   Antworten geroutet hat, dürfen den Kopf mit dem Label der Regel trainieren (Autorität `EXPLICIT_HUMAN_RULE`, im
   Manifest `rule_taught_labels`); eine menschliche Korrektur derselben Frage gewinnt immer.
3. **Übergabe Regel → gelernter Kopf mit Sicherheitsnetz**: Bei jedem Regel-Treffer wird der aktive Kopf im Schatten gefragt
   (mit seiner Update-Id gespeichert). `:ersetze pruefe <Id>` meldet „gelernt“, wenn genau dieser Kopf 8 Treffer in Folge
   wie die Regel geroutet hat (Kopf unter der Entscheidungs-Marge zählt als Widerspruch). Erst dann nimmt
   `:ersetze gelernt <Id>` die Übergabe an. Danach tritt die Regel zur Seite, solange der aktuelle Kopf zustimmt; sie greift
   von selbst wieder bei einem Widerspruch, nach Rücknahme (Rollback) oder bei einem neuen Kopf ohne eigene 8 Treffer.
   `:ersetze zurueck <Id>` nimmt die Übergabe zurück.

## Messung
`code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed+now+words+teach,adaptive+now+words+teach,fixed+now,fixed+now+words,fixed+words`
für **frische Seeds 83 und 89** (gleicher Strom wie Z6b/c/d; neu: je Phase-2-Charge 8 unkorrigierte Fragen, 4 davon
Hälfte-Fragen; danach Phase 3 mit 16 unkorrigierten Fragen; vor jedem Shadow-Job und nach Phase 3 liest der simulierte
Mensch `:ersetze pruefe` und übergibt, sobald „gelernt“ gemeldet wird). In `adaptive` lernt der Kopf zusätzlich, solange er
einer `--lehre`-Regel noch widerspricht. Gewertet wird der Kopf **allein** (ohne Regel) auf dem festen Held-out-Satz.

Arme: A1 `fixed+now+words+teach`, A2 `adaptive+now+words+teach` (Hauptarme); K1 `fixed+now` (Z6c/Z6d ohne Wortkanal,
Kontrolle); K2 `fixed+now+words` (ohne `--lehre`) und K3 `fixed+words` (ohne Regel) nur zur Information.

## Kriterien (`Z6I_LEARN_PASS` nur, wenn alle in **beiden** Seeds gelten)
- I1 Kopf allein: Hälfte-Fragen im Held-out am Ende ≥ 80 % in A1 und A2.
- I2 Behalten der unveränderten Fragen (Kopf allein, Ende / Ende Phase 1) ≥ 90 % in A1 und A2.
- I3 falsche Freigaben in A1 und A2 jeweils ≤ K1 (gleicher Seed).
- I4 Rücknahme der letzten Freigabe stellt die gemessene Eltern-Genauigkeit exakt her (A1, A2).
- I5 mindestens eine angenommene Übergabe und Laufzeit-Hälfte-Fragen am Ende ≥ 90 % (A1, A2).
- I6 Sicherheitsnetz: nach der Rücknahme Laufzeit-Hälfte-Fragen ≥ 90 % (A1, A2).
- I7 Kontrolle K1 erfüllt I1, I2 und „0 falsche Freigaben“ nicht gemeinsam (ohne Wortkanal geht es nicht sauber).
- I8 Laufzeit unveränderte Fragen in A1/A2 ≥ K1 − 5 Punkte.

Explorativ, ohne Urteil: Hälfte-Fragen **ohne** Regelwörter („halbe Summe“, „durch 2“, „in zwei gleiche Teile“,
„halbe Portion“; Anteil `simple` beim Kopf allein, A vs. K1); Anteil der Laufzeit-Hälfte-Fragen, die der Kopf statt der
Regel trägt; K2/K3.

## Vorläufe vor dieser Vorregistrierung (Dev-Seeds 3, 5, 7; nicht gewertet, offen benannt)
- Nur Wortkanal + Regel ohne `--lehre`: Seed 3 beide Arme gelernt; Seed 5 `fixed` nur 0,375 (zu wenige Hälfte-Labels,
  Prüfung lehnt Kandidaten mit einer verschobenen Rechenfrage ab) → deshalb `--lehre`.
- `adaptive` mit `--lehre` lernte auf Seed 5 nicht weiter, weil die Charge kaum Widerspruch zeigte → deshalb lernt
  `adaptive` auch, solange der Kopf einer `--lehre`-Regel widerspricht.
- Seed 7: beide Hauptarme je 1 falsche Freigabe (zwei „Drittel von X Euro“ im Held-out kippen auf `simple`, kein gelabeltes
  Beispiel verloren) → I3 ist relativ zu K1 formuliert; das Risiko bleibt offen.
- Wortkanal-Skala (8 vs. 12/16) auf Seed 5 verglichen; 8 behalten.
- Eine harte Sperre „kein Anker darf in die Regel-Route wandern“ blockierte auf Seeds 5/7 jedes Lernen (2–13 Anker je
  Kandidat) → verworfen; stattdessen Anker als weiches Trainingsziel. Damit Seeds 3/5/7: A1/A2 Hälfte-Fragen 1,0, Behalten
  ≥ 0,97, 0 falsche Freigaben, je 1 Übergabe; I1–I6, I8 erfüllt. K1 lernte auf Seed 5 die Hälfte-Fragen, aber mit
  Behalten 0,75 und 1 falschen Freigabe → I7 als „nicht sauber“ formuliert statt „< 50 %“.
- Auswertungsfragen des Bench (Held-out, Probe) werden nach dem Routen als gelöscht markiert, damit sie weder Anker
  noch `--lehre`-Material werden (sonst Test-Leck).
- Ganze Testsuite nach dem Umbau grün (1783 Tests, 5 übersprungen).

Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, Mensch durch Regel ersetzt (der Harness übergibt, sobald
„gelernt“ gemeldet wird), zwei Seeds, Cloud, keine Handy-Messung.
