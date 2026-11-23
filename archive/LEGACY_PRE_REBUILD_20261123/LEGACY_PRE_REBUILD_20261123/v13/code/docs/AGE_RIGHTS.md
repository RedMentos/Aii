# WP-T2 Age-Rechte überall (§3.3.0 C0, §17.4, §17.5)

- `age.RIGHT_CAPABILITY`: Fähigkeit, deren Stufe ein Recht regelt (Decke = min(System, Fähigkeit)). Nicht gelistete Rechte folgen der Systemstufe.
- `AgeControl.may(right, resource_mode)`: Recht an seiner Fähigkeit. `AgeControl.rights(mode)`: Sicht für ExecState.
- `executive.permission_flags(control, cfg, resource_state)`: `age`, `age_by_capability`, `rights`, `resource_mode`, `user_stage_cap`, `learning_mode`; `external_tool_execution` nur mit `simple_tool_choice` (tool ≥ 1); `native_body_training` nur mit `raw_body_attempt` (body_port ≥ 2) und `learning_mode=APPROVED_COMMIT`.
- Wer fragt Age ab: effort.age_limits (deliberation=language, tools=tool, long_loops=language) → Fokusschleife/Inquisition und C5; gist (`adaptive_gist_grouping`, language ≥ 2, sonst feste Gruppengröße der Stufe; feiner werden ist immer erlaubt); attention (language-Stufe); cognition (Age-Hülle im Executive-Broadcast, nur wenn über Age 0, kann nichts erweitern); sleep/scheduler/agi.age_allows über `may`.
- Nachweise: `agi/maturity.feed(g, origin, key)` schreibt einen Nachweis für System + jede gemessene Fähigkeit (language/routing_skill: AG12-Lauf; memory_skill: Retention als Kompetenz; tool: Erfolgsquote eigener Tool-Aufrufe). Nach jeder vollen Nacht (`after_sleep`) und live nach Turns (`turn_feed`, höchstens 1/h und nur bei neuer Erfahrung). Ohne Messung (vision, audio, social, body_port) kein Nachweis, Stufe bleibt 0.
- BUILD_CEILING bleibt 0: Nachweise erzeugen bis STEP7 nur Vorschläge, keine Beförderung.
- Test: `tests/test_age_rights.py` („Age-Stufe ändert erlaubte Pfade“).
