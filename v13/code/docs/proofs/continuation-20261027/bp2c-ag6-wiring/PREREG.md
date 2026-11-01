# WP-BP2c Vorregistrierung: Ortsanker + Subspace im echten AG6-Lernweg auf C3 350M, Q4-Gate (Blueprint §14.5, §21, §29 Nr. 18)

**Vorabüberlegung (Nutzerregel 27.10.).** Vorstufen vorhanden: AG6-Pipeline (Batch -> Trainer -> Gate auf dem echten llama.cpp-Q4-Pfad, `scripts/ag6_live_bench.py`), die neuen Bausteine sind opt-in eingehängt
(`:growth trainer cfg locality_gen=2 lora_subspace=minor`, Tests grün), Effekt auf B1 fp32 belegt (BP2a/b). **Offen/unklar:** Der Live-Standard (anchor_weight 8, nur FFN, `bench-results/ag6-live-20261010`) wurde auf Leck 0
getrimmt, aber mit Nah-Fragen, deren Personen auch Trainingsanker waren (Tauschwörter). Neu messen wir mit **nie trainierten Personen** (`gate_held_out`). Platz für Gewinn nur, wenn der Standard dort leckt; ist das Leck dort schon <= 0,15,
heißt das Urteil BP2C_NO_ROOM (ehrlich, kein Gewinn zu zeigen). Sichtbar ab 0,25 Punkten Leck (8 Fakten, 2 Seeds -> 16 Leckfragen je Arm; plus Tauschwort-Fragen). Fehlt noch (vermerkt): Handy, echte Nutzerfakten statt erfundener.

**Arme** (echte Pipeline, C3 LFM2.5-350M Q4, 8 erfundene Fakten aus `lora_bench.FACTS`, Seeds 1, 2 über `seed`; alle Arme mit `gate_held_out=true`, damit gleiche Prüffragen):
live = heutiger LoraTrainer | body0 = BodyJepaTrainer ohne Zusätze (Kontrolle: trennt Schleife von Zusätzen) | gen = `locality_gen=2` | gen_minor = `locality_gen=2` + `lora_subspace=minor`.
**Kriterien** (Mittel beider Seeds, bester der Arme gen/gen_minor gegen live): K1 Leck (Q4-Pfad, alle Nah-Fragen) <= live - 0,25; K2 gelernt >= live - 0,125; K3 Vergessen (Allgemeinfragen) nicht schlechter als live; K4 Gate-Status PENDING_USER in beiden Seeds.
Urteil: BP2C_PASS (K1-K4); BP2C_NO_ROOM (live Leck <= 0,15); BP2C_FAIL sonst. Standard bleibt unverändert; Nutzer entscheidet über `:growth trainer cfg`.
