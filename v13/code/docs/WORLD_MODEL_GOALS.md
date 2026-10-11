# WP-T8 World-Model und Ziele (§7.2, §7.2.1, §7.2.2, §20.3, §6.6)

## Control-grounded World Model (`v13/world_model.py`)
Ein kleines CPU-Modell über V13s eigene, beobachtete digitale Übergänge (actions mit Forecast + Outcome, Route aus der ActionSelection).
- **Zustand s:** log Eingabelänge, Ressourcendruck, Tageszeit (sin/cos).
- **Aktion a:** C5-Route simple|detail|gist|both.
- **Folge y:** log Dauer, Erfolg (FINAL), log Ausgabelänge.

Vier getrennte Ziele (§7.2.1), jeweils auf einem gehashten 1-aus-4-Hold-out gemessen:
- **forward** (s, a) → y: Ridge, Bootstrap-Ensemble aus 5 Fits; deren Streuung ist die Modell-Uneinigkeit.
- **inverse** (s, y) → a: Genauigkeit gegen die Mehrheitsbaseline, ausdrücklich „kein kausaler Beleg“.
- **state-align** latent → y: Linear-Probe, sobald gelernte latente Weltvorhersagen mitgespeichert sind; sonst UNAVAILABLE statt erfundener Latents.
- **outcome:** Vorhersage gegen tatsächliche Folge (MAE je Ziel, mit Baseline).

## Coverage und Counterfactual-Konfidenz (§7.2.2)
`counterfactual(s, a)` und `for_event(event, a)` liefern:
- Vorhersage und Stützung: Anzahl Beispiele dieser Aktion, OOD-Abstand in Einheiten des mittleren Nächster-Nachbar-Abstands (in_support ≤ 2).
- Ensemble-Streuung, Ursache SELF_CAUSED, Autorität HYPOTHESIS.
- Konfidenz = (1 − e^(−n/8)) · e^(−max(0, OOD − 2)) / (1 + Streuung/0,25).
- Unter 0,5 oder außerhalb der Stützung lautet das Label SIMULATION_UNCERTAIN. Ein Counterfactual wird nie REAL.

Sleep B ordnet Routen-Alternativen jetzt nach dieser Konfidenz statt nach Tabellenreihenfolge. Die Replay-Priorität ist 0,2 · (0,25 + 0,75 · Konfidenz); ohne Weltmodell bleibt sie bei 0,2. Die Hypothese trägt den Counterfactual-Befund mit.

## Ziele und Neugier im Lauf (§20.3, §6.6)
- **`agi.live.goal_turn`** (nach jedem Turn):
  - Ein ungelöster Turn (nicht FINAL oder mit Rückfrage beantwortet) wird ein offenes **USER**-Ziel, eines je Event.
  - Ein späterer FINAL-Turn zum gleichen Thema (Relevanz ≥ 0,5) schließt es.
  - Nach 7 Tagen wird es aufgegeben.
  - Eigene SELF-Ziele bleiben Age-gegated (`choose_learning_goals`).
- **Neugier:** beobachtet je Turn den Fehler der Routen-Region (grounded error, sonst Erfolg/Rückfrage).
- **`learn_medium`** passt das Weltmodell neu an und lässt die Neugier eine Übungsregion wählen. Das geht nur mit Age-Recht `active_info_search` und Explorationsbudget; bei Age 0 also nie. Die Übung läuft dann als SELF-`growth_practice` über den Scheduler.

Tests: `tests/test_world_model.py` (6).
