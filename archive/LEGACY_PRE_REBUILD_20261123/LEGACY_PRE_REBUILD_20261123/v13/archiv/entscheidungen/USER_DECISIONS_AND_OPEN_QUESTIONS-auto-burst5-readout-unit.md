# V13 — offene Arbeit, 2026-09-29

## USER_DECISION_REQUIRED

Keine Entscheidung nötig, um die vorhandenen Pfade mit STARTEN.sh/TESTEN.sh auszuführen.

## RESEARCH_NEEDED / IMPLEMENTATION_NOT_COMPLETE

- Vollständiger Restumfang: docs/REMAINING_IMPLEMENTATION.md. Insbesondere lokale A/B-JEPA/EMA, A3/B3-Projectors, C-Wake/Halt-Readouts sind jetzt im Unit-Pfad implementiert, aber ihr nativer Real-Weight-Lifecycle ist noch unbewiesen; weiter fehlen allgemeine Confidence-/Output-Adapter, lokale A/B-JEPA/EMA, A3/B3-Projectors und Semantic-/Skill-Konsolidierung.
- C3-Paarvergleich mit echten Gewichten ist ausgeführt; breitere deutsche Qualität und semantische B1/B2-Komplementarität sind dadurch nicht nachgewiesen.

## HARD_BLOCKER

- Aktuelle Redmi-Thermal-/Energie-/RSS-Messung und langfristige Retention fehlen. Historisches SMOKE_PASS bleibt erhalten.
- MobileMoE-S-QAT verlangt Zugang. Öffentlicher Config-Abruf am 2026-09-29: HTTP 401; siehe docs/research/mobilemoe-access-20260929.json. Zusätzlich fehlen native Android-Train-/Tap-/Injection-Nachweise. Diese sind nicht allein durch Zugang gelöst.

## CAN_DECIDE_AUTONOMOUSLY

- Vorhandene funktionierende Pfade erhalten, validierte Lernziele und ihre tatsächlichen Consumer ergänzen, fehlende Funktionen nicht als bloße Proof-Lücken ausgeben.
- STEP8–11 bleiben entsprechend SSOT nach dem Stabilitäts-Gate; Age wird nicht automatisch erhöht.
