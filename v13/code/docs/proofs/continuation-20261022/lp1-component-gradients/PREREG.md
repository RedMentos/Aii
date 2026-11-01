# WP-LP1 Vorregistrierung: Erreicht der latente Lernterm die trainierbaren Teile, und nützt er?

Stand 2026-10-22, vor jedem Modelllauf committet. Plan aus GPT/Codex PR #29 (`LEARNING_PATH_AUDIT_20261022.md`,
„Nächstes abgegrenztes Lernpaket“ Punkte 1–4), hier am vorhandenen C3-Trainer, weil B1/B2 heute keinen Trainingsport haben.

## Frage
Der Trainer (`v13/lora_trainer.py`) besitzt einen latenten Zusatzterm (`jepa_weight`): Kosinus zwischen dem letzten
Prompt-Zustand und dem eingefrorenen mittleren Basis-Zustand der Zielantwort. In allen 14 archivierten Läufen war er 0.
Erreicht sein Gradient die LoRA-Parameter in messbarem Umfang, und verbessert er bei gleichem Budget etwas gegenüber
(a) CE+KL allein und (b) einem falsch zugeordneten Ziel?

## Aufbau (fest)
- Modell: HF-Master `LiquidAI/LFM2.5-350M` (fp32, Torch CPU), wie AG6. Kein llama.cpp, kein Q4: Messung auf dem Master
  (Grenze: nicht der ausgelieferte Pfad).
- Daten: die 8 erfundenen Fakten aus `scripts/lora_bench.py` (`FACTS`), Anker `ANCHORS` (32), Prüfungen `PARAPHRASES` (6),
  `NEAR_MISS` (5), `PROBES` (11). Nichts davon ist neu erfunden; alle Listen liegen seit 10.10. im Git.
- LoRA wie Live-Standard `agi/trainers.LIVE_LORA`: rank 8, alpha 16, lr 3e-4, Ziele w1–w3, KL-Anker 8, 16 Anker je Schritt.
- **Gleiches Budget:** genau 30 Schritte je Lauf, kein früher Abbruch. Eingaben über `_encode` mit Promptgrenzen-Schutz
  (Paar ohne Prompt-Token wird abgelehnt; bei diesen Fakten tritt das nicht auf, max_tokens 160).
- Arme: `CE` (jepa 0) · `JEPA_OK` (jepa 1.0, Ziel = eigenes Item, Trainer-Definition) · `JEPA_WRONG` (jepa 1.0, Ziel
  eines anderen Items, feste Ableitung: Item k bekommt Ziel von Item (k+1) mod 8).
- Saaten 13, 7, 21 → 9 Läufe.
- Komponenten-Gradienten: in Schritt 1, 10, 20, 30 auf dem vollen Batch getrennt rückwärts: CE, KL (gleiche Anker-Auswahl),
  JEPA (in CE nur gemessen, Gewicht 0 im Update). Gemeldet: L2-Norm je Komponente über alle LoRA-Parameter, Anteil
  JEPA = ‖g_J‖·w / (‖g_CE‖+‖g_KL‖·w_KL+‖g_J‖·w), Kosinus(g_CE, g_J).

## Ergebnisgrößen (nach dem Training, greedy, 24 Token)
- `learned`: Treffer auf den 8 Trainingsfragen; `para`: Treffer auf 6 Umformulierungen (Hauptgröße Nutzen);
  `leak`: Treffer auf 5 Fast-Fragen (kleiner = besser); `forgot`: Proben, die die Basis richtig hatte und danach falsch;
  `kl_probe`: mittlere KL zur Basis auf den Proben; `cos_after`: latente Kosinusmetrik.

## Hypothesen und Urteil (fest, vor dem Lauf)
- **H1 (Erreichbarkeit):** in `JEPA_OK` ist der JEPA-Anteil in Schritt 1 ≥ 0,05 in mindestens 2 von 3 Saaten.
  Sonst `LP1_TERM_DOES_NOT_REACH`.
- **H2 (Nutzen):** über 3 Saaten summiert `para(JEPA_OK) ≥ para(CE) + 2` **und** `para(JEPA_OK) ≥ para(JEPA_WRONG) + 2`,
  bei `forgot(JEPA_OK) ≤ forgot(CE) + 1` und `leak(JEPA_OK) ≤ leak(CE) + 1`.
- Urteil: H1 und H2 → `LP1_JEPA_HELPS`; H1 ohne H2, aber JEPA_OK schlechter als CE um ≥ 2 in `para` oder `forgot`
  → `LP1_JEPA_HURTS`; sonst → `LP1_NO_ATTRIBUTABLE_GAIN`. Ein höherer `cos_after` allein zählt nie als Nutzen.
- Kein Gate-Aufstieg, keine Aktivierung, egal wie das Ergebnis ausfällt. FAIL bleibt FAIL.

## Grenzen
8 Fakten sind wenig; das Urteil gilt für diesen Aufbau. Kein Predictor, kein EMA-Ziel (der vollständige geplante
Body-JEPA-Pfad ist ein eigenes Paket, sobald B1/B2 trainierbar sind). Master statt Q4-Pfad.
