# AG12-Body-Solver und AG1-Lehrer-Backends (Pakete D, 2026-10-09)

## AG12: echte Bodies lösen die Allgemeinheits-Suite
Code `v13/agi/solver.py`, Tests `tests/test_agi_solver.py`, Messskript `scripts/ag12_body_bench.py`.

- Solver `c3`, `b1`, `b2` (ein Body) und `v13` (B1+B2+C3 zusammen). Nur installierte Rollen nehmen teil.
- Jede Aufgabe geht als eine Nachricht mit festem Systemsatz an den Body, Antwort unter JSON-Grammatik
  `{"answer": ...}`. Dadurch ist das Herausziehen der Antwort exakt, und der Runner liefert Token-Logprobs
  für die Antwortspanne (`runners.generate(..., confidence_field='answer')`). Konfidenz = unwahrscheinlichstes
  Antwort-Token (bestes Fehlersignal aus WP-KAL2), sonst Mittelwert.
- `v13` stimmt ab wie die JEF zwischen Offers: Punktzahl je Antwort = Summe der Konfidenzen, Endkonfidenz =
  Punktzahl / Anzahl Bodies. Das ist bewusst nicht der volle Live-Turn: der würde die Holdout-Aufgaben ins
  Gedächtnis schreiben und damit den Test verbrauchen.
- Keine Schreibzugriffe auf Events/Gedächtnis, keine Werkzeuge (Test prüft das).
- `batch()`: ein Body beantwortet alle 88 Aufgaben, dann der nächste. Am Handy ist meist nur ein Body im RAM.
- Kurven und Vergessen werden pro Solver geführt (`generality.run(..., solver_name=)`, `curve(axis, solver)`),
  sonst sähe ein schwacher B2-Lauf nach einem starken v13-Lauf wie Vergessen aus.
- AG9: nach jedem vollständigen Lauf gehen (Konfidenz, richtig) je Aufgabe an den Kalibrierer `ag12:<solver>`
  (nur Zahlen, keine Aufgabentexte).
- Planung: nach voller Nacht, wenn fällig (monatlich), läuft `v13` automatisch (`after_sleep`).

Bedienung: `:growth eval run c3|b1|b2|v13` (läuft, sobald nichts anderes läuft), `:growth eval`,
`:growth eval curve <Solver> [overall|seen|unseen|planning_depth|forgetting|ece]`.

## Erste Messung (Cloud, 2026-10-10, `bench-results/ag12-bodies-20261010/`)
| Solver | gesamt | gesehen | ungesehen | ECE | Zeit (88 Aufg.) |
|---|---|---|---|---|---|
| c3 (LFM2.5-230M) | .22 | .28 | .17 | .18 | 56 s |
| b1 (LFM2.5-1.2B) | .17 | .17 | .17 | .22 | 140 s |
| b2 (Qwen3.5-0.8B) | .35 | .53 | .23 | .11 | 149 s |
| v13 (B1+B2+C3) | .34 | .53 | .21 | .07 | 215 s |
Rechnen geht (Addition/Multiplikation bis .92), Folgen nur bei B2; Wort umdrehen, Buchstaben sortieren, Weg im Gitter (Planungstiefe) 0 bei allen.
Die Abstimmung hebt die Genauigkeit nicht über den besten Body, kalibriert aber am besten.

## AG1: Lehrer-Backends
Code `v13/agi/teacher_backends.py`.

- `local`: Rolle TEACHER im Runner-Pool (importiertes größeres GGUF oder `use_reference` eines Bodys);
  braucht `:teacher on`.
- `claude`: Claude über das offizielle Anthropic-Python-SDK (`pip install anthropic`), Modell `claude-opus-5-5`,
  Effort `high`, serverseitiger Fallback bei Ablehnung. Art `cloud`: läuft erst nach `:growth teacher cloud on`
  (die Frage verlässt dann das Handy). Schlüssel aus `V13_SECRET_ANTHROPIC_API_KEY` oder der SDK-eigenen
  Auflösung. Ohne SDK: ehrliche Meldung `Unavailable`.
- Reihenfolge: lokal zuerst; Claude nur, wenn erlaubt und kein lokaler Lehrer da ist.
- Spuren bleiben `REFERENCE_NOT_FACT`; der Distillations-Datensatz prüft weiter gegen AG12-Holdout (Test).

Bedienung: `:growth teacher`, `:growth teacher ask <Frage>`, `:growth teacher run [local|claude]`,
`:growth teacher cloud on|off`, `:growth teacher dataset`.

## AG6: echter Trainer im Nacht-Job (`v13/agi/trainers.py`)
- `:growth trainer` zeigt Wahl und was fehlt; `:growth trainer lora|sparse|none|auto [Master-Ordner]` (HF-Ordner des C3, Hash wird gepinnt).
- auto: LoRA, wenn Master, torch+transformers+peft+gguf, llama-server und C3-GGUF da sind und Master = installierter C3 (Breite/Tiefe); sonst ehrlich NO_TRAINER.
- LoRA wirkt nach Freigabe im Chat-Runner (`--lora-scaled`); Sparse-Memory nur über den nativen Hook.
- Nacht-Job `growth_consolidate`: stage → Trainer → Gate (Behalten, Vergessen, KL, Lernen, Spezifität) → Nutzer-Anfrage. Nichts wird von selbst aktiv.
- Echter Lauf `bench-results/ag6-live-20261010/`: 8/8 gelernt, Leck .33, 1/12 vergessen, KL .107 → GATE_FAIL.
- Danach Sweep (`bench-results/ag6-live-20261010/SWEEP.md`): Live-Standard jetzt lr 3e-4, Anker-Gewicht 8, nur FFN (w1–w3), 48 Anker, 32 Probes → Gate bestanden mit zwei Seeds (8/8, 0 vergessen, Leck 0, KL ≤ .014). Pro Gerät anpassbar: `:growth trainer cfg lr=2e-4 anchor_weight=6 targets=["w1","w3"]`, `:growth trainer cfg reset`. Messen: `scripts/ag6_live_bench.py --master <Ordner> --out <Ordner> --cfg '{...}' --tag=-name` (verwirft seinen Batch danach).

## Offen
- AG9-Abstain im Live-Turn (`agi/live.py`, Pakete B) stellt noch keine Lehrer-Anfrage (SELF, ab Age 3).
- Lehrer-Datensatz in den WP-S6-Trainer (AG6) einspeisen.
- Deutsch-Kurve (gleiche Aufgabenlogik) erst als späterer Lerntest.
