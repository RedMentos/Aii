# WP-N9 Selbstmodell, Körpergefühl, Corollary-Rückkopplung (§7.3–7.5, §20.2, §20.4, §85.7, §24.28)

Code: `v13/selfmodel.py` · Tests: `tests/test_selfmodel.py` (18) · Befehl: `:self …` (nacktes `:self` zeigt weiter den F3-`self_state`)

## Teile
- **Selbstmodell §7.3** (`:self model`): eine strukturierte Sicht über Vorhandenes: Bodies/Revisionen, Skills (AG4), Tools
  (AG10), Rechte, Body-Fähigkeiten (WP-N7), Memory-Gesundheit, Kalibrierung, Lernstatus (WP-N10), Age je Fähigkeit,
  Ressourcen, Teacher-Abhängigkeit, offene Ziele (AG3), Grenzen. Nur lesend; jeder Teil fällt weich auf UNAVAILABLE.
  Gespeichert unter `SELF_MODEL_N9:<Session>`.
- **Körpergefühl §7.4** (`:self body`): RAM-Druck, Hitze, Akku, Speicher, Latenz-Belastung, Fehlerlast → Signale 0..1,
  Gefühl calm/loaded/strained und Modulationen (compute_scale, context_budget_scale → WP-N7-Budget, dream/learning
  erlaubt, sleep_pressure). Jeder Turn schreibt `interoception` in die Antwort-Metadaten.
  Eigene Last wird nur in der **Salienz** gedämpft (Corollary-Dämpfung wie biologisch), die Sicherheit
  (`ResourceGuard`) liest immer die Rohwerte.
- **Corollary §7.5/§85.7**: vor jedem Dispatch ein `SelfCorollary`-Paket (Absicht, vorhergesagte Beobachtungen inkl.
  Dauer aus der F4-Prognose, Unsicherheit, Kausalhypothese, erwartete Kosten, Rechte-Schnappschuss). Nach dem
  Ergebnis: `SelfWorldAttribution` SELF / EXTERNAL / MIXED / UNCLEAR mit Residuum; Abweichung → WP-N10-Modulator
  `world_prediction_error` auf Pfad `world_predictor`. Die sechs G-SELF-WORLD-005-Fälle + „ohne Corollary schlechter“
  sind Unit-Tests. B1/B2 bekommen eine kurze `self_corollary`-Sicht in ihre Anfrage (Selbstzustand, kein Fakt).
- **Self-Messaging §20.4**: Arten finding/open_goal/error/memory; Relevanz ≥ 0,6, max. 3/Stunde, 10 min Abstand,
  Duplikate 24 h unterdrückt, `:pause selfedit` hält an. Ungefragt zustellen erst mit Age-Recht `self_initiative`
  (Age 4); darunter HELD (`:self messages`). Wiederholte Fehler im Turn erzeugen einen solchen Vorschlag.
- **Self-Edit §20.2**: nur Vorschläge (`propose_edit`), Freigabe `:self edit approve <Id>`. Context-Policy wird über
  WP-N7 angewandt und ist rücknehmbar (`:self edit rollback <Id>`); safe_config geht in die AG8-Sandbox; andere Ziele
  (Memory, World Notebook, Replay, Routing, Skill-Metadaten, Translator-Gate) werden für ihre Besitzer freigegeben.
  Ohne Dialog nur mit Age-Recht `safe_self_edit_without_dialog` (Age 3) und nur Context-Policy. Harte Regeln nie.

## Offen
- Echte Interozeption auf dem Redmi (Akku/Temperatur-Pfade unter Termux) messen (WP-R).
- Weitere Aktionsarten (Tools, WP-K) sollen `issue/observe` mit eigenen Kanälen nutzen.
- Wer Self-Edits für Replay/Routing/Skills tatsächlich übernimmt: Besitzer der Module (Status APPROVED_FOR_OWNER).
