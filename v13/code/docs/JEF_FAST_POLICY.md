# WP-T1 JEF-Steuerung (§3.3.0–3.3.3, §3.4.7, §4.4, G4) — Übergabe

Code `v13/fastpolicy.py` plus kleine Haken in `learning.py`, `readout_worker.py`, `memory.py`, `cognition.py`, `focal.py`, `runtime.py`, `effort.py`, `config.py`, `operator.py`. Tests `tests/test_fastpolicy.py` (13). Befehl `:fastpolicy [status|focus on|off|measure]`.

## Fast-Köpfe neben route/wake/halt
- Neue Köpfe: `skill` (none|skill), `memory` (skip|recall|deep), `channel` (NO_MESSAGE|SOURCE_EXACT|CONTROL|SYMBOLIC). Sie nutzen dasselbe eingefrorene C2-Embedding der Event-Quelle wie `wake`, einmal berechnet und geteilt.
- Gleicher Weg wie wake: Jeder Turn loggt eine `ExecutiveDecision` mit Scaffold-Baseline. `:feedback memory deep --learn` labelt sie, danach folgen `:learn memory`, das Held-out-Gate (Kalibrierung, Support, Genauigkeit ≥ Scaffold) und `:approve`. Ohne freigegebenen Kopf gilt immer die Baseline.
- Wirkung eines freigegebenen Kopfs, begrenzt:
  - `memory`: `skip` = kein Abruf. `deep` = top_k + 2 (höchstens 8) und der C2-Memory-Key als zusätzlicher Cue.
  - `skill`: darf eine Skill-Route nur abwählen (zurück zur vorherigen Route), nie eine erfinden.
  - `channel`: wählt den B3-Kanal, außer die Callosum-Politik (WP-J) ist ACTIVE und hat schon entschieden.
- Labels sind keine Fakten-Erinnerungen. `memory.recall` liest nur fact/style/preference.

## C2 als strukturiertes Paket
- `C2ExecutivePacket` pro Turn (nicht bei direkten Ausgaben) mit den Feldern route, tool (Name, Argumente, Konfidenz), memory_key und answer_type. Jedes Feld trägt seine Quelle.
- BOOT-Parser zuerst. Ein natives Needle-Feld zählt nur, wenn BOOT leer ist und das Feld gültig ist (bekanntes Werkzeug, bekannter Antwort-Typ).
- `truth_authority` 0: Das Werkzeug läuft weiter über IH-H29, der Key ist nur ein Cue, der Antwort-Typ ein Hinweis.
- `specs/control_tools.json` ist bewusst unverändert. Neue Felder im Needle-Schema würden die freigegebene `control_calibration` (tools_sha256) ungültig machen und den C2-Bench-Vergleich brechen. Das ist eine Nutzer-Entscheidung.

## Top-down-Frage bei Re-entry
- Bei jedem Re-entry baut `focal` eine Frage an B1/B2 (`jef_query` im Body-Prompt und im QueryPacket). Arten:
  - RESOLVE_CONFLICT: zitiert beide Sichten.
  - RESOLVE_UNCERTAINTY
  - VERIFY_PEER
  - FILL_GAP
- Die Frage ist eine Frage, keine Tatsache.
- Modi: `on`, `off` oder `measure` (Standard, wechselt je Event per Hash). Je Arm wird gezählt, ob das Re-entry-Offer in die Koalition kam und ob die Trajektorie stabil blieb (`:fastpolicy`).
- Echte Wirkung braucht echte Modelle. Das ist ein Teil von WP-T3 (Pakete A) und lässt sich dort mit `:fastpolicy focus on/off` vergleichen.

## Zielgerichtetes Re-entry
- `DEEP_FOCAL` plant jetzt bis zu 2 Re-entries (`max_reentry` Standard 2, Bereich 0–3). FOCAL_TARGETED bleibt bei 1.
- Weiter geht es nur, solange das neue Offer selbst noch ein Re-entry braucht (oder die Inquisition ein Ziel nennt).
- Abbruch, sobald ein Re-entry-Offer fast gleich dem vorigen desselben Bodys ist (Abstand < 0,15, `stable_stop`).
- Budget kommt aus WP-D (Effort-Kosten je Re-entry) und Age: Bei Age 0 erlaubt die Fokustiefe 1 nur einen Zyklus, also ein Re-entry.

## Offen
- Echte Labels des Nutzers für die neuen Köpfe. Ohne sie bleibt alles beim Scaffold.
- Fokus-Wirkung mit echten Modellen messen (WP-T3).
- Needle-Schema mit typisierten Feldern (siehe oben, Nutzer-Entscheidung).
