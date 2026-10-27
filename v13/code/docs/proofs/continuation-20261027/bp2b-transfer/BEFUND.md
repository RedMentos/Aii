# WP-BP2b Befund: erzeugte Ortsanker + Übertragung auf andere Formulierungen — `BP2B_PASS`

Vorregistrierung `PREREG.md` (Commit vor der Messung). Roh: `bench-results/bp2b-transfer-20261027/` (2 Seeds, 16 Fakten je Seed, B1 LFM2.5-1.2B fp32, 30 Schritte). Code: `v13/locality_gen.py` (Anker aus der Frage selbst, kein Modell, 6 Tests), `scripts/bp2b_transfer.py`.
Der Generator hat für alle 16 Fakten je 2 Anker erzeugt (32, keine Frage ohne Muster).

| Arm (Mittel; Seed1/Seed2) | gelernt | Umformulierung | Leck A (Messfragen aus BP2a) | **Leck B (neue Formulierung, neue Personen)** | Allgemeinfragen |
|---|---|---|---|---|---|
| ce = heutiger Weg | 1,00 | 0,95 | 0,75 (0,81/0,69) | **0,75** (0,81/0,69) | 0,84 (0,75/0,94) |
| hand_both (Handanker + minor) | 1,00 | 0,91 | 0,16 (0,19/0,12) | **0,09** (0,12/0,06) | 1,00 |
| gen_both (erzeugte Anker + minor) | 1,00 | 0,92 (0,91/0,94) | 0,16 (0,12/0,19) | **0,06** (0,12/0,00) | 1,00 |

K1 Leck A <= ce - 0,25: 0,16 gegen 0,75 **erfüllt**. K2 Leck B <= ce - 0,25: 0,06 gegen 0,75 **erfüllt**. K3 gelernt 1,0, Umformulierung 0,92 >= 0,85, Allgemeinfragen 1,0 >= ce **erfüllt**. K4 erzeugt (0,16) <= Hand (0,16) + 0,15 **erfüllt**. -> `BP2B_PASS`.

Aussage: Die BP2a-Wirkung hängt nicht an Handlisten. Aus der Lernfrage selbst erzeugte Personen-Tausch-Anker (Freund, Mutter, Vater, Chef, Cousin, Onkel, Kollege, Nachbar, Oma, Sohn) halten das Lecken so niedrig wie von Hand geschriebene, und die Wirkung trägt auf andere Formulierungen und nie trainierte Personen (Freundin, Frau, Neffe, Stiefbruder, Enkelin, Schwester): Leck 0,75 -> 0,06, Allgemeinwissen unverändert.
Grenzen: 2 Seeds, 16 Leckfragen je Arm (eine Frage = 0,06); der Generator kennt nur Ich-Fragen mit "my <Nomen>" oder Hilfsverb (do/did/am/have/was/should/can/will I); andere Fragearten ergeben keinen Anker (gemeldet, nicht erfunden); Leck B wurde auf Fragen zu **anderen Personen** gemessen, nicht auf andere Fakten-Arten (Orte, Daten ohne Personen); erfundene Kurzfakten; fp32-Master, nicht Q4/Handy; Subspace-Effekt bei 350M (C3) nicht gemessen.
Folge: Schalter sind noch nicht im Alltagsweg (AG6) verdrahtet. Nächstes (WP-BP2c): in den AG6-Lernweg einhängen (`locality_gen.anchors_for` + `lora_subspace=minor` hinter dem Tor, SHADOW), mit dem Tor-Test am echten Lernauftrag, plus Quant-Pfad; Tor-Schwellen unverändert.
