# Befund WP-Z2g: Aktualitäts-Wächter auf frischen Episoden bestätigt (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `9954346b`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 6 Läufe × 70 Zeilen (CQ/CQP × Seeds 26–28),
alle RECORDED, kein Abbruch, kein Neustart. `b2_context_chars` = 1536 in beiden Armen.

## Ergebnis laut Vorregistrierung: `Z2G_GUARD_CONFIRMED`
- Gültigkeit erfüllt: Kickoff-Notiz in **100 %** der B2-Angebote im Kontext (beide Arme); ohne Wächter **24** falsche Festlegungen (≥ 5 nötig).
- Konsistenz: Wächter-aus reproduziert die aufgezeichnete Werkzeug-Aktion in **allen** Zeilen mit Extraktion.

| alle 420 Zeilen | exakt | falsch festgelegt | UNKNOWN |
|---|---|---|---|
| ohne Wächter | 8 | **24** | 388 |
| **mit Wächter** | 8 | **0** | 412 |

| je Typ (aus → an, falsch) | REVISED 14 → 0 | TWICE 10 → 0 | CONFIRM 0 → 0 (0 Fehlverwerfungen, 7 exakt bleiben exakt) |
|---|---|---|---|
| je Arm (aus → an, falsch) | CQ 1 → 0 | CQP 23 → 0 | |

Keine einzige richtige Entscheidung verloren. Auch die doppelt geänderte Regel (TWICE: B2 zitiert die mittlere Änderung) fängt der Wächter.

## Was das Ergebnis nicht sagt (ehrlich)
- **Fast alles ist UNKNOWN.** Exakt nur 8/420, davon 7 in CONFIRM. Bei REVISED/TWICE müsste B2 die unveränderten Regeln aus dem Kickoff **und** die
  Änderung aus der Statusnotiz liefern; mit zwei Zeiger-Plätzen gelingt das kaum (B2-Regelquote CQ .017, CQP .125). Der Wächter macht das System
  sicher, nicht nützlich. Werkzeug-Nutzen `both_exact`: CQ .483, CQP .586 (b1_only .49/.51).
- Der Zeiger macht alte Regeln sichtbarer (überholte Werte in Zitaten CQ 6, CQP 39 Zeilen) — ohne Wächter wäre er auf solchen Aufgaben unsicher.
- Historie im Replay stammt aus den Episoden (so, wie die Sitzung sie behalten hätte); der Live-Aufrufer muss sie selbst übergeben.

## Empfehlung
- Wächter ist bestätigt; im Werkzeug ist er an, sobald der Aufrufer `history` übergibt (leer = aus, bisheriges Verhalten). STEP2-Läufe mit größerem
  B2-Budget sollen ihn ab jetzt immer benutzen.
- Schalter bleiben aus (`b2_quote_select` aus, `b2_context_chars` live 768), bis B2 alle aktuellen Regeln liefern kann.
- Nächstes Paket **WP-Z2h**: B2 darf aus mehr als zwei Sätzen wählen (Zeiger-Plätze 2 → 4) bzw. eine Regel-Notiz ganz übernehmen, gemessen mit
  Wächter an, auf LONG/REVISED/TWICE; Ziel: exakte Entscheidungen hoch bei weiter 0 falsch.

Daten: `code/bench-results/step2-z2g-recency-20261026/` (z2g_result.json, Zusammenfassungen mit Paaren je Zeile, Werkzeug-Replays, Log, SHA256SUMS);
volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2g-recency-20261026/`.
