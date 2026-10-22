# §99-Ablation: Reflex-Sicherung bei wiederholten Body-Fehlern (WP-F §5.3) — **SUPPORTED_SYNTHETIC** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_reflex_breaker.py`, Vorregistrierung `preregistration.json` (Commit `e86c6cc`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echter `reflex.Reflex` (3 Fehler in 600 s → 120 s gesperrt, ein Erfolg öffnet wieder) mit simulierter Uhr; Ablauf wie in `runtime.py`. Ein Body, ein Aufruf alle ~30 s, 24 h je Saat, 5 Saaten.
Kosten je Runde: fehlgeschlagener Aufruf 1,0; übersprungener Aufruf (nur C3) 0,3; erfolgreicher 0.

| Strom | Sicherung | nie sperren | Body nie rufen | zufällig sperren (gleiche Zahl) | Sicherung gewinnt (nie / nie rufen / zufällig) |
|---|---|---|---|---|---|
| Ausfälle (2 h gesund, 10 min Ausfall) | **.058** (116 Fehler, 166 gesperrt) | .090 (257 Fehler) | .300 | .102 | 5 / 5 / 5 |
| wackelig (25 % Fehler, keine Ausfälle) | .253 | **.249** | .300 | .250 | 0 / 5 / 1 |

- Bei echten Ausfällen spart die Sicherung gut die Hälfte der vergeblichen Aufrufe, die Kosten sinken um ≈ 36 % → SUPPORTED_SYNTHETIC.
- Bei zufälligen, unabhängigen Fehlern bringt sie nichts und kostet minimal (+.004 je Runde): Drei Fehler in Folge sagen dann nichts über den nächsten Aufruf.
- Grenze: synthetischer Fehlerprozess, ein Body, angenommene Kosten, BOOT-Schwellen. Die Reflexe `imminent_timeout` und `critical_resource` sind hier nicht getestet.
