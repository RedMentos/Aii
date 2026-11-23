# WP-T17: §99 „Dream hilft“ – Lauf 1 (2026-10-10, vorläufig)

Script `code/scripts/dream_ablation_bench.py`. C3 = LFM2.5-230M-Master (torch fp32), LoRA r8 auf allen Zielmodulen.
Phase A lernt 4 erfundene Fakten (A), Phase B lernt 4 weitere (B) plus Wiederholung je Arm, Stopp bei CE ≤ 0,05.
Träume = Umformulierungen der A-Fragen, von C3 (LFM2.5-350M, Temperatur 1) geschrieben (`dreams.json`, `gen_dreams.py`).
Anker-Prüfung (Sleep-B-Analog): Umformulierung bleibt nur, wenn sie das Quell-Objekt nennt; Eval-Fragen ausgeschlossen.

Nach Phase B, Seeds 13 / 21:

| Arm | A exakt | A Paraphrase | B exakt | Proben (Basis 0,83) | Near-Miss-Leck |
|---|---|---|---|---|---|
| keine Wiederholung | 1,0 / 1,0 | 0,50 / 0,75 | 1,0 / 1,0 | 0,67 / 0,83 | 0,8 / 1,0 |
| exaktes Replay | 1,0 / 1,0 | 0,75 / 0,75 | 1,0 / 1,0 | 0,75 / 0,75 | 1,0 / 1,0 |
| Traum, geprüft, Quell-Antwort | 1,0 / 1,0 | 0,25 / 0,50 | 0,75 / 0,75 | 0,50 / 0,42 | 0,8 / 0,8 |
| Traum, Selbst-Antwort (ohne Prüfung) | 0,75 / 0,75 | 0,75 / 0,75 | 1,0 / 1,0 | 0,83 / 0,83 | 0,8 / 0,6 |
| Traum, Anker-Prüfung durchgefallen | 1,0 / 1,0 | 0,75 / 1,0 | 0,75 / 0,75 | **0,25 / 0,33** | 1,0 / 1,0 |

Vorläufiger Befund:
- In diesem Aufbau vergisst Phase B die A-Fakten gar nicht (A exakt bleibt 1,0 ohne Wiederholung). Schutz vor Vergessen ist so nicht messbar; gemessen sind nur die Kosten.
- Ungeprüfte Träume mit Quell-Antwort (Anker durchgefallen) zerstören allgemeines Wissen (Proben 0,25–0,33). Die Sleep-B-Prüfung verhindert genau diesen Schaden.
- Auch geprüfte Träume kosten Proben (0,42–0,50) und B-Lernen; der lexikalische Anker ist zu grob (z. B. „What kind of cat did you adopt?“ → „Mitzi“).
- Selbst-Antwort-Träume sind am harmlosesten (Proben 0,83), kosten aber exakten A-Abruf.
- **„Dream hilft“: nicht belegt;** ungeprüfte Träume schaden messbar.

Offen: Lauf 2 mit Vergessens-Druck (`--b-steps 40 --seeds 13,21,34`) wurde für die Pause abgebrochen und ist nicht gelaufen.
