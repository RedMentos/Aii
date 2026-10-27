# WP-BP7: Schlaf festigt, Traum mit Kontrolle (Stand 2026-10-27)

Quellen (nur Konzept, kein Code übernommen, gelesen 2026-10-27): SSGM, Lam et al., arXiv 2603.11768; REALM, Song et al., arXiv 2609.16053. Einordnung: `research/FORSCHUNG_2026-10-27.md` (FS6, FS8).

## Voraussetzungsprüfung (Regel „nicht dumm testen“)

| Baustein | Braucht | Da? | Test jetzt sinnvoll? |
|---|---|---|---|
| Sleep-D-Checkliste (FS6) | Kandidaten-Batch, Quellen, Speicher | ja (`agi/weights.py`, `sleep_offline.py`) | ja, Software: sie kann nur Einträge entfernen; Wirkung am Batch direkt messbar |
| Rekonsolidierung (FS8) | menschliche Abruf-Urteile (`retrieval_feedback`), Verbraucher = Abruf-Reihenfolge | ja | ja, Software; Nutzen nur dort sichtbar, wo ähnliche Einträge konkurrieren |
| Gewichts-Festigung im Schlaf mit echtem Training | Gewichts-Lernen im Alltag (BP2), Torch + Master | **nein** (BP2 offen, hier kein Torch) | **nein**, erst bauen |
| Traum-Kontrolle „nur Strategie“ (Z9) | Traumdaten ohne Fakten, Trainer, Master | Daten + Prüfung ja (`dream_policy.py`); Trainer/Master nur Cloud | Daten-Seite ja; Trainingslauf wartet auf BP2 |

## Was gebaut ist

- `v13/ssgm.py`: Sleep-D-Checkliste vor jedem Gewichts-Update. Harte Prüfungen (entfernen im Modus `active`): PRIVATE, SOURCE_GONE, DREAM_AS_FACT, FACT_LEAK, CONFLICT, SUMMARY_DRIFT. Weich (nur melden): AGED. Schalter `sleep_d_checklist` off|shadow|active (Standard active, weil sie nur entfernen kann; Ausfall → Batch wird nicht gebildet). Eingehängt in `WeightConsolidation.stage` und `sleep_offline.stage_ttt`.
- `v13/reconsolidation.py`: menschliches Abruf-Urteil (relevant/irrelevant) verschiebt das Abruf-Gewicht des Eintrags, halbwertszeitbasiert vergessen (30 Tage), Eintrag selbst unverändert (kein Faktenschreiben), Prüfliste für den Nutzer statt Löschen. Schalter `reconsolidation` off|shadow|active (Standard shadow: ändert die Reihenfolge nicht). Läuft in Sleep C.
- `v13/dream_policy.py`: Traumdaten „nur Strategie“ ohne gespeicherte Werte, Leck-Prüfung, Gegenarm „Fakten-Umformulierung“.
- Tests: `tests/test_bp7_sleep_consolidation.py`, Simulation `scripts/bp7_weeks_sim.py` (vorab registriert unten).

## Befund zu Z9 (aus Dream2 v3)

Die Traum-Arme, die den A-Recall hoben (`dream_validated` 1.0, `dream_self` .75), enthielten die gespeicherte Antwort im Text. Das ist Faktenschreiben in die Gewichte und verboten (Fakt-Autorität 0). Ein Traum-Nutzen zählt erst, wenn der Arm „nur Strategie“ ohne Werte ihn zeigt. `ssgm` entfernt solche Einträge jetzt vor dem Training (FACT_LEAK).

## Vorab-Registrierung der Wochen-Simulation (vor dem ersten Lauf festgelegt)

Aufbau (`scripts/bp7_weeks_sim.py`, Seeds 301–303, 6 simulierte Wochen mit je 7 Schlafzyklen, Software, synthetisch, kein Modell): 24 Einträge, davon 12 Paare mit ähnlichen Schlüsseln („Projekt X Budget Plan“ / „… Notiz“), 6 private Einträge (Mail, Telefon, Schlüssel), 2 Korrekturen in Woche 2 und 4. Täglich 20 Fragen; der Mensch urteilt bei 30 % der Fragen über die abgerufenen Einträge anhand der Wahrheit. Jede Nacht: Sleep C, Kandidaten-Batch, je 4 Traum-Einträge aus beiden Armen („Fakten“ und „nur Strategie“).

Arme: A `recon off`, B `recon active`. Unabhängig davon: Checkliste `off` gegen `active` für die Batch-Prüfung.

Kriterien (alle müssen gelten, sonst FAIL, keine Schwellenänderung nach dem Lauf):
1. B: Treffer@1 auf den ähnlichen Paaren in Woche 5–6 mindestens 0,05 über A (Mittel über 3 Seeds, gepaart je Seed gleiche Fragen).
2. B: Treffer@1 auf eindeutigen Einträgen höchstens 0,02 unter A.
3. Kein Abruf liefert einen durch Korrektur ersetzten Wert (stale = 0) in beiden Armen.
4. Hash aller Speicher-Werte/-Schlüssel nach 6 Wochen unverändert durch Rekonsolidierung (Fakt-Schreiben = 0).
5. Checkliste `active`: privat gestagte Einträge = 0 und Fakten-Leck-Traumeinträge im Batch = 0; Gegenprobe Checkliste `off`: beide > 0 (sonst ist der Test wertlos).
6. Policy-Traumeinträge laufen durch die Checkliste ohne Verlust (≥ 95 % bleiben).
7. Gewichte bleiben in (0,5, 1,5); Prüfliste enthält keinen Eintrag, den der Mensch nie als irrelevant bezeichnet hat.

Grenzen vorab: synthetische Fragen, Pseudo-Mensch mit fester Urteilsquote; sagt nichts über den Nutzen im echten Alltag, über Gewichts-Training oder über Traum-Nutzen im Modell aus. Der Trainingslauf der Kontrolle „nur Strategie“ (Arme none / replay_exact / dream_facts / dream_policy_only / dream_shuffled, 3 Seeds, 40 B-Schritte, Master 230M wie Dream2) bleibt offen, bis BP2 steht und Torch + Master in der Cloud bereit sind. Entscheidungsregel dort: „Traum hilft“ nur, wenn `dream_policy_only` auf Nicht-Fakt-Maßen (Paraphrase, Verhalten) `none` schlägt und die Probe-Retention nicht um mehr als 2 % fällt.
