# Episoden, Gedächtnisgraph, Aufnahme/Vergessen (WP-N8) — 2026-10-09

Blueprint A1, §9.3–9.5, §48.15, §51.2. Code `v13/episodes.py`, Tests `tests/test_episodes.py` (10), Befehl `:episodes`.

## Ereignisgrenzen (§9.3, §48.15)
Nach jeder fertigen Runde (`runtime._turn`, im `finally`) wird entschieden, ob eine neue Episode beginnt. Signale:
Kontextwechsel (Kosinus des schon berechneten Abruf-Vektors aus WP-H, sonst Wortüberlappung), Vorhersagefehler
(`PredictionOutcome`: latenter Weltfehler oder Zeitfehler), Zielwechsel (`active_task`), Routenwechsel, Quellenwechsel,
Nutzerkorrektur, Fehlschlag, Pause (≥ 30 min, harte Grenze). Score = Noisy-OR mit den §51.2-Gewichten; Grenze ab 0,30.
Überraschung allein (0,25) schneidet nie. Jede Grenze speichert ihren Signalvektor, damit die Grenz-Politik später lernen kann.
Voller Sleep schließt offene Episoden. Kein zusätzlicher Modellaufruf.

## Kausaler Gedächtnisgraph (§9.4)
Kanten mit Evidenzklasse: TEMPORAL (Abfolge), CORRELATIONAL (gemeinsam abgerufen, im Turn abgerufen),
CAUSAL (nur mit Eingriff: eigene Aktion mit beobachtetem Ergebnis, menschliche Korrektur), HYPOTHESIS (Sleep-B-Traum, Lehrer).
Zählen macht aus Korrelation nie Kausalität, Hypothesen werden nie durch Wiederholung befördert.
`relation(a,b)`, `causes()`, `effects()`, `related_memories()` (assoziative Ausbreitung für spätere Abruf-Nutzung).

## Aufnahme und Vergessen (§9.5)
Geschlossene Episoden bekommen einen Aufnahme-Score (Korrektur, Fehlschläge, Abrufe, Länge) und die Stufe
`FAST_EPISODIC` oder `SEMANTIC_STAGING_CANDIDATE` (ab 0,5). Erinnerungen haben eine Stärke, die bei Abruf wächst und
mit Halbwertszeit 30 Tage zerfällt; `:episodes forgetting` schlägt schwache vor, gelöscht wird nur per `:forget`.
`:forget` entfernt auch Kanten und Stärke.

## Speicher und Datenschutz
Nur `states` (IDs, Hashes, Zahlen, keine Texte); kein Schema-Umbau. Telemetrie ohne Inhalt.

## Offen / Übergabe
- Erledigt 2026-10-10 (Pakete C): `consolidation.stage` stellt Indizes, deren Erfahrungen in `SEMANTIC_STAGING_CANDIDATE`-Episoden liegen, zuerst (Feld `episode_staging_support` im Request).
- Erledigt 2026-10-10 (Pakete C): assoziativer Abruf `Episodes.spread` nach `Memory.recall` (Hook `episodes.recall_turn` in `runtime._turn`). Nachbarn über CORRELATIONAL/CAUSAL-Kanten mit Zählung ≥ 2, höchstens 2, Score 0,6 × Eltern-Score, Wert + SourceRef über `Memory.candidate` neu geprüft. Standard SHADOW (nur `meta.associative_shadow`), `:episodes spread on|shadow|off`. Per Ausbreitung geholte Erinnerungen stärken ihre eigene Kante nie (`associative_ids`).
- Erledigt 2026-10-10 (Pakete A): A1 innerhalb eines Textes.
  - `episodes.text_segments` zerlegt einen Text in Satz- und Zeilen-Einheiten.
  - Geschnitten wird, wo das Noisy-OR der §51.2-BOOT-Gewichte ≥ 0,5 erreicht. Signale: fester Chunk-Prior .40, semantische Grenze (Absatz/Zeile/Satz) .25, Themenwechsel (lexikalisch) .35, Frage↔Aussage .30, Prosa↔Liste/Code .30.
  - Ein Segment ist nie kürzer als 25 % und nie länger als 150 % der Zielbreite. Zu lange Sätze teilt `gist.group`, ohne exakte Spans zu schneiden.
  - Verlustfrei: Die Segmente kacheln den Text und behalten ihre SourceRef. Jedes trägt Grund, Score und Signale.
  - Schalter `segment_mode`:
    - `percept` (Standard): PerceptPacket und A4-Aufmerksamkeit bekommen Ereignissegmente.
    - `all`: zusätzlich die B1/B2-Quellsicht.
    - `fixed`: das alte Verhalten.
  - Tests `tests/test_text_segments.py`.
- Gelernte Grenz-Politik (A1.learn_gain) und gelernte Aufnahme: Daten werden gesammelt, Lerner fehlt.

## WP-U10 Fast Episodic: zweites Mal besser für Routen (§9.1)

Hat ein Mensch bei einer Anfrage die Route korrigiert, gilt diese Korrektur beim nächsten sehr ähnlichen Anfragetext sofort als Routen-Vorschlag. Auf die prozedurale Konsolidierung mit ≥ 3 Bestätigungen wird nicht gewartet.

**Ähnlich heißt:** `memory.relevance` ≥ 0,6, entitätsbewusst. Ein anderes „Projekt X“ ergibt 0. Gelöschte Quellen zählen nicht.

**Herkunft:** Der Vorschlag trägt Erinnerungs-, Event- und Quellen-ID.

**Reihenfolge:** Die prozedurale Route (`consolidation.route`) gewinnt weiterhin.

**Modi** (`:episodes route [off|shadow|active]`):
- `shadow` (Standard): Der Vorschlag steht in `meta.route.episodic_route`, die Route bleibt beim Scaffold.
- `active`: Der Vorschlag wird als Route übernommen.
- `off`: Es wird kein Vorschlag erzeugt.

**Tests:** `tests/test_episodic_route.py`.
