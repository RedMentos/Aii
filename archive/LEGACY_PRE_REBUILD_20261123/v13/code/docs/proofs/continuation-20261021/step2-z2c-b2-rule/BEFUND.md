# Befund WP-Z2d: B2 liefert das Regel-Zitat (2026-10-21)

Paketname im ROADMAP **WP-Z2d** (im Code/Prereg „z2c“; umbenannt, weil Thread „B1-Frage als Schalter“ parallel WP-Z2c vergab).

Vorregistrierung `PREREG.md` (Commit `8cc006d`, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, **kein Redmi**. Modelle frisch über
`v13.bootstrap` installiert (B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M, llama.cpp b10964, wie Z2/Z2b). 9 Läufe × 70 Zeilen = 630 Zeilen,
alle RECORDED; Werkzeug-Replay je Lauf. Seeds 17/18/19 (neu). CI = 95 %, Cluster-Bootstrap über Episoden.

## Ursache (vor dem Lauf, auf den Z2b-Daten)
B2 *kennt* die alte Regel oft, liefert sie aber nicht als exaktes Zitat: von 384 B2-Angeboten (RULE/SPLIT, aktuelle Runde) trugen 115 die volle
Regel; 110 scheiterten an einer **Umschreibung oder kaputten Kopie des richtigen Satzes**, 65 zitierten den aktuellen Aufgabentext.
Die strenge Zitatprüfung verwirft Umschreibungen zu Recht, also kam die Regel nie bei C3 an. Details `z2b_b2_diagnosis.json`.

## Ergebnis: `Z2C_B2_RULE_QUOTE_FIXED` (Zeiger), Anker nur teilweise
| Arm | B2-Regelquote (96 Zeilen) | Differenz zu CQ [CI] | Urteil |
|---|---|---|---|
| CQ (Kontrolle, Schalter aus) | **.167** (Seeds .09/.22/.19) | — | — |
| CQA anchor | .542 (.69/.50/.44) | +.375 [+.146, +.615] | `B2_RULE_QUOTE_IMPROVED_PARTIAL` (< .60) |
| **CQP pointer** | **.969** (.94/.97/1.00) | **+.802 [+.688, +.906]** | **`B2_RULE_QUOTE_FIXED`** |
Sicherheit in allen Armen: **0** Zeilen mit falschem Regelwert in B2-Zitaten, **0** falsch festgelegte Entscheidungen im Werkzeug-Replay,
alle Angebote mit Frage, Modus in jedem Seed benutzt (Anker 35/26/23 verankerte Zitate, Zeiger 63/64/64 gewählte Nummern; abgelehnte B2-Zitate CQ s17 34 → Anker 6–11 → Zeiger 0), keine Strukturfehler.

## Sekundär: was das für STEP2 bedeutet (Werkzeug-Nutzen, Mittel Seeds 17–19)
| | b1_only | b2_only | both_exact | same_policy_dual | prompt_only_dual | exakte Entscheidungen both_exact |
|---|---|---|---|---|---|---|
| CQ | .592 | .194 | .575 | .572 | .525 | 6/30 |
| CQA | .597 | .233 | .728 | .592 | .550 | 16/30 |
| **CQP** | .581 | .278 | **.881** | .586 | .536 | **27/30** (SPLIT 15/18) |
- CQP `both_exact` − CQ +.306 [+.219, +.383]; − bester Einzelkörper (b1_only) **+.300 [+.214, +.378]**, in jedem Seed größer (.842/.875/.925).
  Damit fällt erstmals **Z2b-Kriterium 1** (zwei Körper schlagen den besten Einzelkörper). Anker: +.131 [+.053, +.217], ebenfalls erfüllt.
- Explorativ (nicht vorregistriert, gleiche Rechnung wie Z2b): CQP gewinnt je Körper eine Episode in 3/3 Seeds (Krit. 2 ✓),
  schlägt `same_policy_dual` +[.19, .38] (Krit. 4a ✓) und `prompt_only_dual` desselben Arms +[.26, .41]; **Kriterium 3 (komplementäre
  Fehlerprofile) bleibt ✗**, weil b2_only die Regelfelder ohne Optionswerte nie richtig haben kann (in Z2b schon als zu streng für diese
  Fixtures benannt, nicht nachträglich geändert). Die Ein-Körper-Kontrolle (DQ mit Zeiger) und §99 sind **nicht gemessen**.
- Kosten: B2-Prompt im Mittel 781 statt ~580 Tokens (+~35 %, die nummerierten Sätze).

## Wie der Zeiger wirkt (offen genannt)
- B2 wählte in 72/96 Angeboten einen Satz, der selbst einen Regelwert enthält; in 93/96 einen Regelsatz oder die Kopfzeile der Kickoff-Notiz.
  Die vorhandene Zitat-Erweiterung (`offer_quote_context_chars` 200) macht daraus die ganze ~96-Zeichen-Notiz. Bei längeren Regel-Notizen
  trägt eine gewählte Kopfzeile die Regel nicht mehr mit — das ist für diese Fixtures günstig und nicht allgemein belegt.
- Starke Positions-Neigung: Nummer 1 (erster Satz der aktuellen Aufgabe) wurde in 66/96 Angeboten mitgewählt (harmlos, kostet aber einen der
  zwei Plätze).
- Anker: hilft genau bei der Umschreibung, nicht beim Zitieren des Aufgabentexts; wirft Umschreibungen mit erfundenen Zahlen („5,00“) korrekt weg.

## Empfehlung
- Gate-Lage: STEP2 bleibt formal `UTILITY_FAIL` (Kriterium 3 ✗, Ein-Körper-Kontrolle offen), `canonical_gate_pass=false`. Schalter
  `b2_quote_select` bleibt im Live-Code **aus**, bis der Nutzer entscheidet.
- Kandidat für den Live-Pfad: `b2_quote_select=pointer` zusammen mit `offer_quote_context_chars=200`, `b2_offer_body_state=false`,
  `offer_quote_min_chars=90` (alle bisher aus). Vorher: (1) Live-`analyst_context` muss erweiterte Zitate annehmen (heute wirft er
  „Consumer quote differs“, der STEP2-Harness baut seinen Kontext selbst und ist davon nicht betroffen); (2) Handy-Kosten der +200 Tokens messen.
- Nächstes Paket (neu vorregistrieren): Zeiger mit Ein-Körper-Kontrolle (D/DQ) und frischen Episoden mit längeren Regel-Notizen und
  geänderten Regeln (Revision im aktuellen Text), damit der Effekt nicht an der Fixture-Form hängt.

Daten: `code/bench-results/step2-z2c-b2-rule-20261021/` (z2c_result.json, Zusammenfassungen, Werkzeug-Replays, Diagnose, Log, SHA256SUMS);
volle STEP2-Berichte (je ~3,5 MB) im Projektordner `v13/bench-results/step2-z2c-b2-rule-20261021/`.
