# WP-Z10a Vorregistrierung: §24.19 Shared-Pre-Router-Vergessen, echte Wiederholung (vor dem Lauf committet)

Anlass: WP-N11 (12.10.) fand auf EuroMoE-2.6B-A0.6B „Vergessen entsteht vor dem Router“ (Restauration shared holt 81 %
zurück; Experten-Updates 17× weniger Vergessen). Damals waren die drei Seeds identisch (gleiche Faktenmenge, volle
Batch) → effektiv **ein** Lauf, nur Fenster Schichten 8–9. §24.19 steht in `specs/benchmarks.json` als NOT_IMPLEMENTED.

Aufbau: `code/scripts/moe_router_bench.py --parts calib,update --fresh-facts --windows "8,9;16,17" --seeds 13,21,34
--steps 25`, Körper `utter-project/EuroMoE-2.6B-A0.6B-Instruct-2512 @ 96e19829` (fp32, HF transformers 4.57.3 wie
N11, Cloud-CPU). Je Seed eine **eigene** Menge von 16 erfundenen Fakten (`fresh_facts(seed)`); Alt-Aufgabe die 48
EN/DE-Texte. Arme shared / router / experts / all je Fenster; Restaurations-Ablation im Arm all.

Kriterien je Fenster (Urteil `Z10A_PRE_ROUTER_REPLICATED` nur wenn R1–R3 im Fenster 8–9 gelten; Fenster 16–17 wird mit
denselben Regeln als „verallgemeinert ja/nein“ berichtet):
- R1 Arm all bekommt das Monitor-Urteil `PRE_ROUTER_BOTTLENECK` in ≥ 2/3 Seeds.
- R2 Arm experts: Alt-Verlust-Zuwachs ≤ 0,2 × der von Arm shared in 3/3 Seeds, und neue Fakten auf ≤ 20 % des
  Startverlusts gelernt.
- R3 Restauration shared holt im Arm all ≥ 50 % des Vergessens zurück in ≥ 2/3 Seeds.
Sonst `Z10A_PRE_ROUTER_NOT_REPLICATED` mit Angabe. Keine Nachbesserung nach dem Lauf.
Grenzen: HF fp32 statt llama.cpp/Handy, ein Körper, erfundene Fakten, 25 Schritte Adam lr 3e-4. Verdrahtung des
MoE als B1/B2 in der Runtime ist nicht Teil dieses Teilpakets.
