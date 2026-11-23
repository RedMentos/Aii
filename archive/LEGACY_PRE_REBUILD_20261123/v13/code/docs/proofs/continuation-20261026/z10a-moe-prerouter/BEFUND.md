# WP-Z10a Befund: §24.19 Shared-Pre-Router-Vergessen — `Z10A_PRE_ROUTER_REPLICATED` (Fenster 8–9)

Vorregistriert in `PREREG.md` (vor dem Lauf committet und gepusht). Daten `v13/bench-results/z10a-moe-prerouter-20261026/`
(z10a.json, run.log). EuroMoE-2.6B-A0.6B @ 96e19829, HF transformers 4.57.3 fp32, Cloud-CPU, 4,3 h, RSS 13,6 GB.
Kalibrierung identisch zu N11 (Router-KL p95 0,0222, Flip 0,165).

Je Seed eigene 16 erfundene Fakten; Alt-Verlust-Zuwachs (nats) auf den 48 EN/DE-Texten:

| Fenster | Seed | shared | router | experts | all | experts/shared | Restauration shared (all) |
|---|---|---|---|---|---|---|---|
| 8–9 | 13 | +2,74 | +0,02 | +0,37 | +5,71 | 0,14 | 94 % |
| 8–9 | 21 | +5,89 | +0,03 | +0,33 | +1,17 | 0,06 | 78 % |
| 8–9 | 34 | +5,45 | +0,02 | +0,43 | +4,64 | 0,08 | 93 % |
| 16–17 | 13 | +0,68 | +0,01 | +0,11 | +0,50 | 0,16 | 95 % |
| 16–17 | 21 | +0,84 | +0,01 | +0,22 | +0,46 | 0,27 | 91 % |
| 16–17 | 34 | +0,65 | +0,02 | +0,16 | +0,40 | 0,25 | 94 % |

Experten lernen die neuen Fakten in allen Läufen auf 8–9 % des Startverlusts (11–15 Schritte), Router allein lernt kaum
(auf ~80 %).

Kriterien Fenster 8–9: R1 `PRE_ROUTER_BOTTLENECK` 3/3 PASS, R2 experts ≤ 0,2 × shared 3/3 PASS, R3 Restauration ≥ 50 %
3/3 PASS → **`Z10A_PRE_ROUTER_REPLICATED`**. Fenster 16–17: R1 3/3, R3 3/3, R2 nur 1/3 (0,16 / 0,27 / 0,25) →
**verallgemeinert nicht voll**: in den späten Schichten ist das Vergessen insgesamt viel kleiner (shared +0,65 bis
+0,84 statt +2,7 bis +5,9) und der Vorteil der Experten-Updates schrumpft auf etwa das 4- bis 6-Fache statt 7- bis 18-Fache.

Bedeutung: Der N11-Befund war ein Einzellauf; jetzt ist er mit drei verschiedenen Faktenmengen bestätigt. Für STEP6C
heißt das: neue Fakten nur in Experten (Router eingefroren) lernen, geteilte Teile vor dem Router nicht anfassen; in
frühen Schichten ist das am wichtigsten. §24.19 hat damit eine echte Messung (in `specs/benchmarks.json` steht es
weiter als NOT_IMPLEMENTED, weil Specs eingefroren sind; Laufzeit-Verdrahtung des MoE fehlt weiterhin).
Grenzen: HF fp32 statt llama.cpp/Handy, ein Körper, erfundene Fakten, ein Lernverfahren (Adam 3e-4, 25 Schritte).
