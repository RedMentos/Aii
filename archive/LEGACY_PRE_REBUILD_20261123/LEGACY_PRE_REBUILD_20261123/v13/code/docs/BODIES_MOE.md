# WP-N11 Zwei echte Körper-Hälften (Stand 2026-10-09)

Nutzerwunsch: B1 und B2 sind verschiedene Modelle („zwei verschiedene MoE-Hälften“).

## Was jetzt läuft
- **B1_DETAIL** = LFM2.5-1.2B (`models.json` Schlüssel `body`), **B2_GIST** = Qwen3.5-0.8B (`gist`). `bodies.distinct_bodies()` prüft die installierten SHA256-Werte.
- **`v13/bodies.py` (BodyFabric)**: wird in `Runtime.__init__` angehängt (`runtime.bodies`).
  - AG0: installierte Modelle werden zu Slots (`agi/slots.py`). `ModelManager.path_for` fragt `router` → ein Kandidat im RAMP bekommt seinen Anteil der Turns (Schlüssel = Event-ID, `begin_turn` in `_turn`).
  - AG13: die zwei Körper sind die „Experten“. `RunnerPool.get` fragt `fabric.admit`; Körper werden nur geladen, wenn der Wake-Plan sie ruft, bleiben resident im Budget `body_residency_mb` (Default 1800, BOOT-Schätzung) und werden nach Nutzen verdrängt. C3 ist gepinnt (wie Router/Shared). Druck: PRESSURE → 60 % Budget, CRITICAL → nie zwei Körper gleichzeitig. `body_residency_mb=0` = alter Ein-Prozess-Pool.
  - Eigener Zustand `WP_N11_BODY_RESIDENCY`; der generische AG13-Zustand bleibt frei für einen echten MoE-Körper.
- **RunnerPool** (`runners.py`): mehrere Generate-Runner gleichzeitig (`resident`), Tap/Causal-Stream bleiben exklusiv; `unload(role=None)`, `resident_roles()`.
- **B2-Offer**: `cognition.offer_schema(tokens)` begrenzt Stringlängen auf das Observer-Budget (~2,2 Zeichen/Token), damit Qwen sein JSON schließt statt abgeschnitten und verworfen zu werden.
- **B2-Tap**: `runners.TAP_SPECS['gist']=('qwen35.result_norm.final.v1',1024)`, geprüft auf b10964 (wiederholbar, 1024 dim). `predictor_worker` nimmt 1024 oder 2048 (ein Prädiktor je Körper).
- Tests: `tests/test_bodies.py` (8).

## Grenzen
- Kein Körper ist ein sparse MoE-Netz; „Experten“ = ganze Körper. Echter MoE-Körper bleibt WP-N11-Rest (MobileMoE gesperrt).
- RAM-Größen sind aus Dateigröße geschätzt; Redmi-RSS/PSS mit zwei residenten Körpern muss am Handy gemessen werden (WP-R).

## Messungen
Siehe `bench-results/step2-two-body-20261009/` und ROADMAP WP-N11.
