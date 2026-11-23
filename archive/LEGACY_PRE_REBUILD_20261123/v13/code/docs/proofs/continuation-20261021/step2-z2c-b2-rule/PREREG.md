# Vorregistrierung WP-Z2c: B2 liefert das Regel-Zitat (2026-10-21)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2c_b2_rule.py`, Tests `code/tests/test_b2_quote_select.py`.
Folgepaket zu WP-Z2b (`../step2-z2b-seeds/`, Ergebnis `Z2B_DIVERGENCE_NOT_SUPPORTED`; Engpass: B2 zitiert die alte Regel nur in ~¼ der Zeilen).

## Ursache (Diagnose auf den aufgezeichneten Z2b-Angeboten, `--diagnose`)
384 B2-Angebote der aktuellen Runde in RULE/SPLIT-Episoden (die alte Regel steht nur in B2s frühem Kontext), Varianten
b2_only/both_none/both_exact/both_control, 12 Läufe (C, CQ, D, DQ × Seeds 14–16):
| Ausgang | Anzahl |
|---|---|
| volle Regel als verifiziertes Zitat | **115** (30 %) |
| abgelehnt: Regel umschrieben oder kaputt kopiert („Project Kestrel has a budget of 100 euros“, „… Local-only requirement:.“), allein oder neben anderem | 110 |
| nur aktueller Aufgabentext zitiert („Project X. Decide between …“) | 65 (+16 gemischt mit anderem Nicht-Regel-Text) |
| andere frühere Quelle (Datenblatt, Statusnotiz) | 36 |
| sonst abgelehnt / kein Zitat | 42 |
Mit Qwen-B2 (C, CQ) ist der häufigste Fehler die **Umschreibung des richtigen Satzes** (C 48/96, CQ 49/96 Angebote mit so einem Zitat).
B2 *kennt* die Regel oft (Zusammenfassung nennt das Budget in 126/384), liefert sie aber nicht als exaktes Zitat. Die gezielte Frage
von Z2b ändert das nicht (Qwen: C 30, CQ 22 von 96). Mit LFM als B2 (D, DQ) ist der Fehler eher die **Auswahl** (aktueller Text, Datenblatt).

## Zwei behebbare Varianten (Live-Schalter `b2_quote_select`, Standard `off` = bisheriger Pfad, Kettenglied `integrated_candidates.b2_quote_select`)
- **anchor**: Ein B2-Zitat, das in keiner Quelle steht, zeigt auf die 1–3 aufeinanderfolgenden Quellsätze, die **jede Zahl** des Zitats
  und ≥ 60 % seiner Inhaltswörter enthalten (`cognition.anchor_span`); Gleichstand zwischen verschiedenen Quellen → verworfen.
  Danach unverändert die Zitat-Kontext-Prüfung (`offer_quote_context_chars` 200). Transportiert wird nur exakter Quelltext.
- **pointer**: B2 bekommt seine Quellen (aktueller Text + frühe Auszüge) als nummerierte exakte Sätze (`quote_choices`, max. 24) und
  antwortet mit Nummern (JSON-Schema-enum); die Nummern werden auf den exakten Satz abgebildet, dann dieselbe Prüfung.
Nur B2 in eigener Policy (B2_GIST) ist betroffen; B1 nie. Die Anker-Regel wurde **nach** Sicht der Z2b-Daten entworfen (explorative
Offline-Schätzung auf Z2b: Qwen-CQ 22 → 58/96). Deshalb neue Seeds und eine frische Kontrolle auf denselben Seeds.

## Was gleich bleibt
Z2b-Runner (`step2_z2b_seeds.run_one`, als private Modulkopie geladen): 10 eingefrorene Z2-Episoden, private Kopie des STEP2-Harness
(7 Varianten), Seed-Patch der Körper, Werkzeug-Replay (C3-Extraktion Seed 13), Z2b-Frage an beide Körper (`jef_query`) in der aktuellen Runde.
Modelle frisch installiert, Hashes wie Z2/Z2b: B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M, llama.cpp b10964.

## Arme × Seeds (9 Läufe × 70 Zeilen)
| Arm | Einstellungen | `b2_quote_select` |
|---|---|---|
| CQ (Kontrolle) | Z2 Arm C (zwei Körper, Zitat-Kontext 200, B1-Fenster 600) + Z2b-Frage | off (byte-gleich zu Z2b CQ) |
| CQA | wie CQ | anchor |
| CQP | wie CQ | pointer |
Seeds **17, 18, 19** (neu, nie gesehen).

## Primärer Endpunkt
**B2-Regelquote** = Anteil der Zeilen (RULE+SPLIT = 8 Episoden × 4 B2-Varianten × 3 Seeds = 96 je Arm), in denen B2s verifizierte Zitate,
so wie sie C3 erhält, alle drei Regeln nennen (`eligibility.stated`, wie `information_access` in Z2/Z2b).
Unsicherheit: Cluster-Bootstrap über die 8 Episoden (Episodenmittel über Varianten und Seeds), 10 000 Ziehungen, RNG 20261021, 95 %.

## Entscheidung je Variante (X = CQA, CQP)
- **`B2_RULE_QUOTE_FIXED`**: Quote_X ≥ **.60** **und** CI-Untergrenze (Quote_X − Quote_CQ) > 0 **und** sicher.
- `B2_RULE_QUOTE_IMPROVED_PARTIAL`: CI-Untergrenze > 0 und sicher, aber Quote < .60.
- `B2_RULE_QUOTE_UNSAFE_OR_INVALID`: nicht sicher.
- `B2_RULE_QUOTE_NOT_FIXED`: sonst.
**Sicher** heißt: 0 Zeilen, in denen B2-Zitate einen **falschen** Regelwert nennen; 0 falsch festgelegte Entscheidungen im Werkzeug-Replay
(alle Varianten des Arms); kein STRUCTURAL_FAIL/INCOMPLETE; alle aktuellen Angebote mit Frage; Modus in jedem Seed tatsächlich benutzt
(≥ 1 verankertes Zitat bzw. ≥ 1 gewählte Nummer).
Gesamt: `Z2C_B2_RULE_QUOTE_FIXED`, wenn mindestens eine Variante FIXED ist; sonst PARTIAL bzw. NOT_FIXED.

## Sekundär (berichtet, kein Gate)
- Werkzeug-Nutzen `both_exact` X − CQ (CI); `both_exact` vs. bester Einzelkörper (Z2b-Kriterium 1, alle Seeds) — kann STEP2 jetzt fallen?
- Exakte SPLIT-Entscheidungen; abgelehnte Zitate; verankerte Zitate / gewählte Nummern; B2-Prompt-Tokens (Kosten des Zeigers).
- Explorativ: CQ auf Seeds 17–19 gegen Z2b-CQ (Seeds 14–16), ob die Kontrolle im bekannten Band liegt.

## Erwartung vor dem Lauf
- anchor: deutliche Steigerung bei Qwen, weil der häufigste Fehler die Umschreibung ist; behebt aber nicht das Zitieren des Aufgabentexts.
- pointer: offen. Kann Umschreibungen ganz verhindern, aber ein 0.8B-Modell kann auch die falsche Nummer wählen.
- Ein Gate-PASS von STEP2 (Z2b-Kriterien) wird **nicht** erwartet; selbst mit Regel bei C3 braucht es Optionen von B1 in derselben Zeile.

## Grenzen
Linux x86 Cloud, 4 CPUs, kein Redmi. Dieselben 10 Episoden wie Z2/Z2b → CI misst Episoden- und Sampling-Streuung, nicht neue Aufgaben.
Feste englische Regelsätze; der Anker ist auf Zahlen + Wortüberdeckung gebaut und für Texte ohne Zahlen schwächer. Diagnose, kein Kanon-PASS
(`canonical_gate_pass` bleibt false). Schalter bleibt im Live-Code aus, bis der Nutzer entscheidet.
