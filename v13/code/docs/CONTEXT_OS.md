# WP-N7 Context OS + Cache-Policy (§8.3–8.6, §9.1, §74, G6/G6B, R6)

Code: `v13/context_os.py` · Tests: `tests/test_context_os.py` (17) · Messung: `scripts/context_cache_bench.py` · Befehl: `:ctxos`

## Was es tut
Jede Antwort bekommt einen **ContextPlan** (Paket `ContextPlan`) über die Schichten aus §8.3:
EXACT_PINNED (System/Regeln, nie komprimiert) · RAW_HISTORY · COMPRESSED · SOURCE_LINKS · ACTIVE_VIEW (Erinnerungen)
· HYPOTHESES (B1/B2-Angebote) · LATENT_STATE (Aufgabenkontext) · MEMORY_POINTERS (warme IDs) · ARCHIVE.

- **Quelle bleibt unverändert** (§8.3): Kompression ist abgeleiteter Text mit Verweis auf die Quelle, extraktiv
  (erster Satz) und behält **jede exakte Spanne** (Zahlen, Code, Zitate, URLs). Fehlt eine Spanne oder wird es nicht
  kürzer, bleibt der Turn RAW.
- **Exact-Restore** (§8.4): Zahlen, Code, wörtlich/exakt, Quellenkritik oder offener Konflikt aus der Inquisition
  (CONTESTED/VIOLATION/SOURCE_LOSS) heben den Exaktheitsbedarf; ab Schwelle `1 − CTX.reconstruct_disposable_cache`
  werden passende ältere Turns (Überdeckung ≥ `1 − CTX.long_context_block_index`) RAW wiederhergestellt.
- **Budget**: Zeichenbudget aus `context_tokens − answer_tokens` (3 Zeichen/Token, BOOT). Reihenfolge unter Druck:
  ungepinnte alte Turns komprimieren → als Zeiger auslagern → gepinnte komprimieren → Zeiger. Der neueste Turn wird nie
  ausgelagert. Der Runner kürzt danach weiter exakt auf Tokens (Fallback wie bisher).
- **Exact-Recall-Messung**: Anteil der exakten Spannen im Fenster, die im Modellblick bleiben (`span_recall`).
- **Cache als Kontrollaktion** (§8.5): Layout `stable_prefix` lässt System + Verlauf byte-gleich und schiebt die
  wechselnden Schichten hinter den Verlauf (eigene User-Nachricht direkt vor der Frage). Damit kann llama.cpp
  (`cache_prompt`, Slot 0) den KV-Zustand wiederverwenden: „Re-entry statt Re-prefill“. Braucht die Body-Fähigkeit
  `consecutive_user` (G6B, nie angenommen): `:ctxos probe <Rolle>` prüft das Chat-Template echt, sonst bleibt es legacy.
  Jeder Plan schätzt die Präfix-Wiederverwendung für beide Layouts; nach der Antwort werden echte `cache_n/prompt_n`
  gemessen.
- **Warm/activity-silent Memory** (§9.1): benutzte Erinnerungen werden warm (zerfällt ×0,6 pro Ereignis); passende
  warme Erinnerungen, die der Abruf nicht brachte, werden billig reaktiviert (max. 2, Quelle/Hash geprüft,
  gelöschte nie).
- **Lernen** (§8.4 „lernbar“): Prior je Entscheidung (compress/restore) aus `:ctxos outcome <Event> <0..1>`;
  läuft SHADOW, ACTIVE nur per `:ctxos learned active` (max. ±0,25). Jeder Plan berührt die WP-N10-Spur
  `context_policy` (Art `control`); gemessene Cache-Wiederverwendung → Kosten-Modulator (nur wenn angewendet).
- **Regler §74** (`CTX.*`): Erhöhen der riskanten Regler (bzw. Senken von `exact_recent_pin`) wird abgelehnt, solange
  Exact Recall nicht stabil ist (≥ 0,98 über ≥ 20 Pläne).

## Messung 2026-10-09 (Cloud, llama.cpp b10964, `bench-results/context-cache-20261009/report.json`)
6-Turn-Gespräch mit wechselndem Kontextblock, Turns 1–5, neu vorgefüllte Tokens gegenüber legacy:

| Body | stable_prefix | append_only | Prefill-ms legacy → append_only |
|---|---|---|---|
| C3 LFM2.5-230M | −18 % | **−62 %** | 786 → 435 |
| B2 Qwen3.5-0.8B | −4 % | **−44 %** | 3624 → 2074 |
| B1 LFM2.5-1.2B | −7 % | **−56 %** | 3499 → 2056 |

Grund: alle drei Bodies sind hybrid/rekurrent (Conv bzw. DeltaNet). llama.cpp kann deren Zustand nicht auf ein
beliebiges Präfix zurückspulen, nur fortsetzen. Darum ist **`append_only`** jetzt Standard-Layout: der gespeicherte
Transkript-Verlauf + die festgeschriebene Antwort + neuer Kontextblock + Frage, also nur eine Verlängerung. Passt das
nicht (anderer Systemteil, anderes letztes Event, Budget voll), baut es einmal neu (`stable_prefix`). Prefill pro Turn
bleibt so konstant (~75 Tokens) statt zu wachsen. Nachteil: alte Kontextblöcke bleiben im Verlauf sichtbar (als
„reference material“ markiert), bis das Budget einen Neuaufbau erzwingt. Alle drei Templates bestehen die Probe.

## Modi
SHADOW (Standard, Age 0): Plan + Schätzungen werden geloggt, das Modell sieht exakt den alten Kontext (byte-gleich, Test).
ACTIVE: `:ctxos active` (explizit vom Nutzer) gibt den geplanten Kontext an den Runner, inkl. warmer Reaktivierung.

## Befehle
`:ctxos` Status · `:ctxos last` letzter Plan · `:ctxos shadow|active` · `:ctxos learned shadow|active` ·
`:ctxos layout legacy|stable_prefix|append_only` · `:ctxos knob <Name> <0..1>` · `:ctxos capability <Rolle> on|off` ·
`:ctxos probe <Rolle>` (lädt das Modell) · `:ctxos outcome <Event> <0..1>`

## Grenzen / offen
- Kein Patchen nativer Attention/KV-Geometrie (§8.5, §8.6.6); §8.6-Primitiven bleiben Forschung.
- Der RunnerPool hält nur ein Modell; wenn Beobachter (B1/B2) laufen, geht der C3-Cache sowieso verloren. Der Gewinn
  zeigt sich bei direkten C3-Turns.
- Ausgabe-Adapter (WP-I) lernt auf `messages`; im ACTIVE-Layout ändert sich dessen Eingabe → vor ACTIVE neu prüfen.
- Ratings aus WP-V5 rufen `outcome` noch nicht automatisch auf.
