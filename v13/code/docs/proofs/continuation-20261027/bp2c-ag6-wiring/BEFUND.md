# WP-BP2c Befund: Ortsanker + Subspace im echten AG6-Lernweg, C3 LFM2.5-350M, Q4-Tor — `BP2C_FAIL` (strenge Vorregistrierung), aber klarer Teilgewinn

Vorregistrierung `PREREG.md` (vor der Messung committet). Roh: `bench-results/bp2c-ag6-wiring-20261027/`. Echte Pipeline `scripts/ag6_live_bench.py` (Runtime -> `:growth trainer` -> Job -> Trainer -> Q4-Tor auf dem llama.cpp-Runner), 8 erfundene Fakten, 2 Seeds, alle Arme mit `gate_held_out=true` (28 Nah-Fragen: Tauschwörter des Lernwegs + nie trainierte Personen).
Verdrahtung: `v13/agi/trainers.py` (`set_lora_cfg` mit `locality_gen`, `lora_subspace`, `jepa_*`, `gate_held_out`; Standard unverändert), `BodyJepaTrainer` mit SDFT, Tor-Auswertung, erzeugten Ankern; 3 neue Tests in `tests/test_agi_trainers.py`.

| Arm (Mittel; Seed1/Seed2) | Leck am Q4-Tor | Vergessen (Rate) | KL zur Basis | Tor |
|---|---|---|---|---|
| live = heutiger LoraTrainer | **0,52** (0,54/0,50) | 0 / 0 | 0,014 / 0,015 | FAIL (Spezifität) |
| body0 = neuer Trainer ohne Zusätze | 0,34 (0,32/0,36) | 0 / 0,03 | 0,015 / 0,011 | FAIL |
| **gen** = erzeugte Anker (`locality_gen=2`) | **0,20** (0,21/0,18) | 0 / 0,03 | 0,014 / 0,015 | FAIL |
| gen_minor = + Subspace | 0,29 (0,32/0,25) | 0,03 / **0,10** | 0,070 / **0,100** | FAIL (Drift, Vergessen, Spezifität) |

Alle Arme lernen 8/8. Tor-Schwellen unverändert (Leck <= Basis + 0,2, KL <= 0,05, Vergessen <= 0,02).
**Urteil nach Vorregistrierung:** K1 (Leck <= live - 0,25): gen 0,20 gegen 0,52 **erfüllt**. K2 gelernt **erfüllt**. K3 Vergessen nicht schlechter als live: gen vergisst in Seed 2 eine von 30 Allgemeinfragen („Gas, das Pflanzen aufnehmen“) **nicht erfüllt**. K4 Tor-Status PENDING_USER in beiden Seeds: **nicht erfüllt** (alle FAIL). -> `BP2C_FAIL`.
**Was es heißt:** Der heutige Alltagsweg lässt neue Fakten auf nie trainierte Personen durchschlagen (0,52, weit über der Tor-Schwelle 0,2); das fiel bisher nur nicht auf, weil das Tor mit denselben Tauschwörtern prüfte, die der Weg auch trainiert. Erzeugte Anker senken das auf 0,20 (Seed 2 sogar 0,18 = unter der Schwelle). Es fehlen 2 von 28 Fragen (Seed 1: 0,214) und im Seed 2 eine Allgemeinfrage, die auch der neue Trainer ohne Zusätze vergisst (die Schleife mit Gesamtbatch statt Einzelschritten ist nicht neutral: body0 0,34 gegen live 0,52 zeigt, dass ein Teil des Gewinns an der Schleife hängt).
**Subspace Tuning (FS2) schadet bei 350M:** KL 0,07-0,10 (Tor 0,05), Vergessen bis 0,10, Leck nicht besser als gen. Entgegen dem Befund auf 1,2B (BP2a, dort Vergessen 0,84 -> 1,00). Die Forschung hatte gewarnt, dass die Wirkung mit der Größe wächst; hier bestätigt. -> `lora_subspace=minor` nur für große Körper (B1/B2) erwägen, nicht für C3 350M.
Grenzen: 2 Seeds, 8 erfundene Fakten, Cloud-CPU, kein Handy. Standard unverändert (Opt-in).
Nächstes (WP-BP2d, neue Seeds, vorab festgelegt): `locality_gen=4` (mehr Anker je Fakt) gegen gen2 und live, Ziel: Tor-Durchgang in beiden Seeds.
