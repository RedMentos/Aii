# Redmi-Ressourcen-Modi GREEN / YELLOW / ORANGE / RED (Canon §97.2)

Stand 2026-10-12, Thread „Nächste offene Pakete N“. Modul `v13/resource_modes.py`, Guard `v13/resources.ResourceGuard`,
Tests `tests/test_resource_modes.py` (10), volle Suite 1298 grün (Linux, Software-Test).

## Was vorher war

Drei widersprüchliche Tabellen: `effort.RESOURCE_MODE` (PRESSURE → RED), `bodies.PRESSURE_MODE` und
`scheduler.RESOURCE_MODE` (PRESSURE → YELLOW). Kein ORANGE, keine stufenweise Wirkung: jede Abweichung von
NORMAL schaltete alle Beobachter ab, Replay und Schatten-Lernen liefen bis CRITICAL weiter.

## Jetzt

| Modus | Auslöser (BOOT) | Wirkung |
|---|---|---|
| GREEN | darüber | volle Beobachter-Abdeckung |
| YELLOW | MemAvailable < 3 × `minimum_free_mb` oder Temp ≥ Limit − 6 °C | Beobachter-Zeit × 0,6, Fokus-Zyklen ≤ 2, Memory-Top-k × 0,5, Replay × 0,5, ein Post-Commit-Körper |
| ORANGE | < 2 × Boden oder ≥ Limit − 3 °C (= altes PRESSURE) | höchstens ein Beobachter-Körper + JEF (Effort-Decke `one`, andere Körper werden ausgelagert, C3 bleibt), Schatten-Lernen pausiert (alle 9 Lern-Jobs), kein Replay/Traum, nur Sleep C |
| RED | < Boden oder ≥ Limit (= altes CRITICAL) | kein Beobachter, kein Replay, kein Lernen; OOM-/Hitze-Reflex, der Turn wird wie bisher abgelehnt |

In jedem Modus unangetastet: Antwort-Governor, Regeln, Provenance-Log, Cancel (`resource_modes.PRESERVED`).

- **Eine Tabelle:** alle Stellen lesen `resource_modes` (`as_mode`, `mode_of`, `policy`, `allows`, `scaled`, `cap_roles`).
  Die alten Guard-Zustände bleiben das Drahtformat: GREEN/YELLOW → NORMAL (RECOVERY direkt nach ORANGE/RED),
  ORANGE → PRESSURE, RED → CRITICAL. YELLOW ist für alte `=='NORMAL'`-Prüfungen unsichtbar und wirkt nur über die neuen Abfragen.
- **Hysterese:** eine strengere Stufe wird erst verlassen, wenn ihre Schwelle um 5 % RAM bzw. 1 °C unterschritten ist.
- **Schwellen am Gerät gemessen:** `:resources calibrate` misst die RSS der residenten Beobachter-Körper (beide nötig)
  und setzt ORANGE = Boden + größter Körper × 1,15, YELLOW = Boden + beide × 1,15. Status `DEVICE_MEASURED` nur unter
  Android/Termux, sonst `HOST_MEASURED_NOT_REDMI`. Profil liegt im Store (`RESOURCE_MODE_PROFILE`), überlebt Neustarts;
  `:resources reset` kehrt zu BOOT zurück. Temperatur-Schwellen bleiben BOOT, bis eine Drossel-Messung am Gerät existiert.
- **Sichtbar:** `:resources` zeigt Snapshot + Modus, Gründe, Policy, Profil; jeder Turn loggt `resource_mode`.

## Bewusste Verhaltensänderungen

- PRESSURE heißt jetzt ORANGE: ein Beobachter-Körper statt keiner; Age-Rechte/Budgets für ORANGE eigen
  (kein Traum, kein Replay, keine Exploration/Werkzeug-Lernen) statt der RED-Werte, die `effort` vorher nutzte.
- RECOVERY sperrt die Beobachter nicht mehr (Hysterese übernimmt das Flattern); der Scheduler wertet RECOVERY als YELLOW.
- `:replay` wird in YELLOW halbiert und in ORANGE/RED mit Limits abgelehnt.

## Grenzen

Alle Faktoren (0,6 / 0,5 / 1,15 / 5 %) sind BOOT-Werte, keine Messung. RED lehnt den Turn weiter ab statt einen
JEF-Sicherheitspfad zu fahren: unter dem RAM-Boden riskiert auch ein C3-Forward den OOM. Redmi-Kalibrierung und
Messung, ob ORANGE mit einem Körper tatsächlich unter dem Boden bleibt, sind WP-R.

## Nachtrag WP-N17: Observer-Scheduling (§22.2.4) und §73-RSS-Budget

Modul `v13/observer_schedule.py`, Tests `tests/test_observer_schedule.py` (9, inkl. echter Turn mit Fixture-Körpern), volle Suite 1307 grün.

- **Regler `observer_schedule`** (`:observers <WERT>`, Standard `A_THEN_B_SEQUENTIAL` = bisheriges Verhalten): `B_THEN_A_SEQUENTIAL`;
  `ALWAYS_BOTH_ASYNC` (beide Vor-Antwort-Pässe gleichzeitig, nur wenn AG13-Residenz an ist und der Modus zwei Körper erlaubt, sonst
  sequenziell mit Grund `ASYNC_NEEDS_TWO_RESIDENT_BODIES`; parallele Pässe starten ohne Peer-Nachricht, danach liegen beide für Re-entry vor);
  `JEF_FIRST_THEN_BOTH` (JEF antwortet zuerst, die geplanten Körper laufen nach dem Commit); `SAMPLED_OBSERVER` (deterministisch je Event,
  Anteil `observer_sample_rate`, ausgelassene Events auch ohne Post-Commit-Pass); `ON_DEMAND_REENTRY` (kein Erstpass, Körper nur auf
  Re-entry-Anfrage der Fokusschleife). Offers behalten Rolle, Provenance und Gültigkeit; jeder Turn loggt `observer_schedule`.
- **§73-RSS-Budget:** V13s eigene Summe aus PSS (sonst RSS) über Hauptprozess + Runner. Über 3000 MB (untere Grenze von
  `total_RSS_soft_budget`) → YELLOW, über 3800 MB (`total_RSS_hard_backoff`) → ORANGE, gleiche Hysterese. Nur unter Android aktiv
  (`rss_status BOOT_REDMI_TARGET`); auf anderen Hosts aus (`OFF_NOT_ANDROID`), damit Cloud-Läufe großer Körper nicht von Handy-Zielen gedrosselt werden.
- **Grenze:** ob parallele Pässe auf dem Snapdragon 732G schneller sind oder nur RAM kosten, misst erst der Redmi (WP-R); §73 sagt „sequential first“, daher der Standard.
