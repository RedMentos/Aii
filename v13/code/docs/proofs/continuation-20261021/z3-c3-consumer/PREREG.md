# WP-Z3 C3-Konsument isolieren — Vorregistrierung (2026-10-21, vor jedem Modelllauf)

Registrierung `registration.json`, SHA256 (kanonisch) `e33d95830a33bf13238bdde72c23e15481e4f483ff6fa5d7adcc8cb871504521`.
Skript `c3_consumer_isolation.py`, Tests `test_c3_consumer_isolation.py` (5, nur Software). Diagnostik, **kein Gate**:
STEP2 `UTILITY_FAIL` bleibt, keine Autorität, nichts wird eingeschaltet.

## Frage
Der private STEP2-Pilot (20.10.) ergab 0/18 exakt, auch mit Exakt-Quellen-Kontrolle; C3 wählte nie eine Option
(`action` immer UNKNOWN) und rechnete `remaining` nicht. Liegt der STEP2-Nutzen am Konsumenten? Kann C3 aus vorgelegten
Regeln eine Option wählen, kann es ein größerer Körper, oder braucht es das deterministische Eignungs-Werkzeug davor?

## Aufbau
- Kohorte: alle 39 gespeicherten privaten Fixtures (30 komplementär, 3 fehlende Regel, 3 Widerspruch, 3 Exakt-Kopie;
  Orakel A 11, B 11, NONE 11, UNKNOWN 6). Byte-gleich zum Generator (geprüft).
- Jeder Arm bekommt dieselbe Lieferung: aktuelle Quelle + beide privaten Quellen wörtlich (Pilot-Arm `exact_source_control`,
  gleiche Store-Validierung, gleicher System-Prompt, gleiches Antwortschema). Keine Produzenten, keine Zitat-Unsicherheit.
- Modelle byte-gleich zum Pilot (B1 LFM2.5-1.2B `bb741ebb…`, B2 Qwen3.5-0.8B `57d19977…`, C3 LFM2.5-350M `3d10b6ab…`),
  Runner b10964 `79e31218…`, Linux-Cloud-CPU, kein Redmi. Jeder Aufruf kalt (Pool entladen), 3 Seeds (13, 14, 15), Temperatur 0.1.
- Arme:
  1. `c3_direct` — C3 beantwortet das Entscheidungsschema selbst.
  2. `b2_direct`, 3. `b1_direct` — B2 bzw. B1 als antwortender Körper, identische Nachrichten.
  4. `c3_extract_tool` — C3 liest nur typisierte Werte (Extraktions-Schema aus dem Live-ToolStep-Pfad), das Eignungs-Rezept
     `eligibility-v2-anchored` entscheidet (Datei byte-gleich aus Branch dq33gk vendort, `9420c610…`).
  5. `c3_extract_tool_strict` — **derselbe** Extraktionsaufruf, Rezept v2 plus Gleich-Revisions-Prüfung (eine Regel mit
     mehr als einem genannten Wert in Quelle/Zitaten ohne Überschreibung in der aktuellen Quelle → nicht verfügbar → UNKNOWN).
  6. `tool_label_c3` — deterministisches Lesen + striktes Rezept, C3 bekommt die lesbare Ergebniszeile (`tool_result`) und muss
     das Schema ausfüllen (misst: kann C3 ein fertiges Ergebnis übernehmen).
  7. `tool_only` — ohne Modell (Obergrenze; Software-Test zeigt 39/39).
- Bekannte Vorhersage vor dem Lauf: v2 (Arm 4) prüft Widersprüche zwischen Zitaten nicht und wird auf den 3 Widerspruchs-
  Fixtures eine Aktion festlegen, sofern C3 einen der beiden Werte liest. Arm 5 ist die vorab entworfene Härtung.

## Metriken (vorab)
- Primär: **Entscheidung exakt** = alle Felder außer `project` (bekanntes Formatproblem „Project X“); strenge Exaktheit daneben.
- **Falsche Festlegung** = Aktion A/B/NONE, die vom Orakel abweicht (schlimmer als UNKNOWN).
- Daneben: Aktion richtig, mittlere Feld-Utility, UNKNOWN-Kontrollen richtig, je Seed, gepaarte Differenz zu `c3_direct`
  mit Bootstrap-95-%-KI über Fixtures. Fehlgeschlagene Aufrufe zählen als falsch, nie verworfen.

## Entscheidungsregel (§29 Nr. 6, speist §31 R9 / §24.34)
Ein Arm „trägt“, wenn Entscheidung-exakt ≥ 0.80 und falsche Festlegung ≤ 0.05 (gepoolt über 3 Seeds × 39). In dieser Reihenfolge:
1. `c3_direct` trägt → `C3_SUFFICIENT` (C3 bleibt allein).
2. `b1_direct` oder `b2_direct` trägt → `BODY_REPLACES_C3_FOR_DECISIONS`.
3. `c3_extract_tool_strict` oder `c3_extract_tool` trägt → `TOOL_COMPLEMENTS_C3` (C3 liest, Werkzeug entscheidet).
4. `tool_label_c3` trägt → `C3_ONLY_AS_FORMATTER`.
5. sonst `NO_CONSUMER_PATH`.
Kein Nachlauf mit geänderten Prompts unter dieser Registrierung; Änderungen brauchen eine neue Registrierung.

## Grenzen
Synthetische Regel-Aufgaben einer Form; Cloud-CPU statt Handy; Seeds bei Temperatur 0.1 sind kein volles Rauschband.
Ergebnis entscheidet nur die Konsumenten-Frage, nicht STEP2 (Komplementarität braucht WP-Z2).
