# WP-N3 JEF ↔ Gehirn lernen (§3.4.2–3.4.7, L4.3, L4.4, G3C, §24.25–24.26)

Code: `v13/jefbridge.py` · Tests: `tests/test_jefbridge.py` (8) · Befehl: `:jef [status|last|shadow|active|query|outcome <Event> <0..1>]`

- **JEF_BROADCAST_CACHE** (Paket `JEFBroadcastCache`, jeder Turn nach dem C1-Broadcast): state_version, goal/executive
  latent, Fokus-Slot-Refs, Constraints, letzte Aktionsabsicht, Corollary-Sicht (WP-N9), Unsicherheit, Körperzustand,
  Quellenzeiger. Die GGUF-Runner haben kein auslesbares JEF-KV, darum sind die Latents **gehashte symbolische Vektoren**
  (32 Dim., so markiert), keine nativen Latents.
- **JEF2B-Brücke**: pro Body ein gelerntes Feld-Gate. SHADOW: B bekommt genau das bisherige `executive_broadcast`.
  ACTIVE: Zusatzfelder (`jef_broadcast` in der B-Anfrage); unbekannte Felder werden pro Event deterministisch zu 50 %
  erkundet, damit Nutzen(mit) − Nutzen(ohne) messbar ist; ein Feld bleibt dauerhaft, wenn es ≥ 0,05 hilft
  (§24.26: schlechte Brücke fällt auf). Veralteter Broadcast (state_version) wird nie benutzt.
- **Offer-Nutzen (L4.4)**: logistisches Online-Modell über 12 Merkmale (Body, Konfidenz, Unsicherheit, Re-entry-Wunsch,
  Belege, Zielbezug, Koalition, Inquisitions-Urteil …). Labels: Antwortabdeckung des Offers (intern, schwach) und
  Bewertungen (`:note`, implizites Lob/Kritik → `inputs.record_rating` → `on_rating`, stark). Im Schatten wird die
  gelernte JEF-Entscheidung (IGNORE/INCORPORATE_*/QUERY_*) neben die Scaffold-Entscheidung geschrieben
  (`JEFBridgeTurn`, Übereinstimmungsquote in `:jef`). ACTIVE: der Wert verschiebt den Fokus-`utility`-Term in
  `focal.py` um max. ±0,25.
- **Top-down-Query (§3.4.7)**: Wert gezielter Re-entries je (Auslöser conflict/uncertain/calm, Ziel B1/B2) → strukturierter
  QUERY_PACKET-Vorschlag (target, desired_scale fine/gist/mixed, evidence_need, conflict_to_resolve, Budget).
- **Observer-Pass-Nutzen (§24.25)**: je Modus none/A/B/AB nützliche und unnötige Offers pro Turn, Konfliktrate,
  Observer-Latenz — Grundlage für eine gelernte Observer-Frequenz.
- WP-N10-Pfade: `jef_offer_utility`, `jef_topdown_query`, `jef_broadcast_bridge` (Art control).

## Offen
- Echte A/B-Brücken auf nativen Zuständen (JEF2A/JEF2B-Projektoren) brauchen lesbare Latents (WP-I/WP-F).
- `recommend_query` steuert die Re-entry-Wahl in `focal.py` noch nicht (nur Vorschlag); nach genug Daten einhängen.
- Adaptive Observer-Frequenz an WP-D (Effort) koppeln, wenn die Statistik trägt.

## Nachtrag 2026-10-10 (Pakete A): Query-Ziel in der Fokusschleife + Observer-Frequenz an WP-D

- **Query-Ziel:** `FocalLoop._jef_target` → `JEFBridge.query_target(view, heuristic)`.
  - Läuft nur, wenn das Gerüst ohnehin einen Re-entry will (Ziel gesetzt, Queries übrig). Es erzeugt nie einen zusätzlichen.
  - Der gelernte Vorschlag (§3.4.7) steht immer als `jef_query` im FocalCycle-Paket und in der Trajektorie.
  - Er ersetzt das BOOT-Ziel nur, wenn alle drei Bedingungen gelten:
    - `:jef active` ist eingeschaltet.
    - Beide Ziele haben je ≥ 3 Belege für den aktuellen Auslöser (conflict, uncertain oder calm).
    - Der Vorschlag weicht vom BOOT-Ziel ab.
  - `BOTH` behält das Gerüstziel.
- **Observer-Frequenz:** `JEFBridge.observer_scale(wake)` passt die Observer-Zeit an.
  - Grundlage ist der Anteil nützlicher Offers je Observer-Modus (A, B oder AB) ab `OBS_MIN_N` = 8 Turns.
  - Daraus wird ein Faktor in [0,5; 1] auf die Observer-Zeit des Effort-Plans (`observer_scale`).
  - Der Faktor senkt nur, er erhöht nie. Er wirkt nur in `:jef active`; sonst steht er nur in `meta['jef_observer']`.
- Tests `FocalHookTests` in `tests/test_jefbridge.py`. Der Nutzen braucht einen Modelllauf (WP-N12, §24.25).
