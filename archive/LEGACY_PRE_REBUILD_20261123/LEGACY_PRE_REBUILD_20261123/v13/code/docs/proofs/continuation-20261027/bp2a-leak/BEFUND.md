# WP-BP2a Befund: Gewichts-Lernen ohne Lecken — `BP2A_PASS` (Evidenz für das AG6-Tor, nichts aktiviert)

Vorregistrierung `PREREG.md` (Commit 3f36ce23, vor der Messung). Roh: `bench-results/bp2a-leak-20261027/` (2 Seeds, je 16 Fakten, 30 Schritte, B1 LFM2.5-1.2B fp32-Master, greedy). Code: `v13/body_jepa.py` (`minor_subspace_init`), `scripts/bp2a_leak.py`, 9 Tests.
Einstell-Vorlauf (Seed 99, 8 Fakten, nicht im Urteil): minor lernt schon bei Lernrate 5e-4 (gelernt 1,0) -> 5e-4 für alle Arme.

| Arm (Mittel aus 2 Seeds; Seed1/Seed2) | gelernt | Umformulierung | Leck (andere Personen) | Allgemeinfragen (Basis 1,00) |
|---|---|---|---|---|
| ce = heutiger Weg | 1,00 | 0,95 (1,00/0,91) | **0,75** (0,81/0,69) | 0,84 (0,75/0,94) |
| locality (+32 Nah-Trainingsfragen, KL zur Basis) | 1,00 | 0,88 (0,97/0,78) | **0,19** (0,19/0,19) | 0,91 (0,88/0,94) |
| minor (nur kleinste Singulärrichtungen, FS2) | 1,00 | 0,97 (0,97/0,97) | 0,84 (0,81/0,88) | **1,00** (1,00/1,00) |
| both | 1,00 | 0,91 (0,88/0,94) | **0,16** (0,19/0,12) | **1,00** (1,00/1,00) |

Kriterien: K1 Leck bester Arm <= ce - 0,25: both 0,16 gegen 0,75 (-0,59) **erfüllt**. K2 gelernt >= 0,9 und Umformulierung >= 0,85: both 1,00 / 0,91 (beide Seeds >= 0,875) **erfüllt**. K3 Allgemeinfragen >= ce: 1,00 gegen 0,84 **erfüllt**. K4 beide Seeds gleiche Richtung **erfüllt**. -> `BP2A_PASS`.

Wer macht was (je Arm einzeln): **Ortsanker senken das Lecken** (0,75 -> 0,19); sie kosten etwas Umformulierung (0,95 -> 0,88, Seed 2 bis 0,78). **Subspace Tuning (FS2) stoppt das Vergessen** (Allgemeinfragen 0,84 -> 1,00, Basis-Niveau; ohne Ortsanker aber kein Effekt aufs Lecken). Zusammen: Lecken fast weg, kein Vergessen, Umformulierung 0,91. Das Vergessen-Beispiel aus BJ1 („Hauptstadt Italiens: Trompe“) tritt in beiden Subspace-Armen nicht mehr auf.

Grenzen (ehrlich): nur 2 Seeds, 16 Leck- und 16 Allgemeinfragen je Arm (eine Frage = 0,06); die Nah-Trainingsfragen haben dieselbe Frageform wie die Messfragen, nur andere Personen -> Übertragung auf andere Formulierungen/Aufgaben nicht gezeigt; erfundene kurze Fakten; fp32-Master, nicht Q4/Handy; der Subspace-Effekt bei 1,2B ist belegt, bei C3 350M offen (Forschung sagt: Wirkung wächst mit Größe). Die Ortsanker brauchen pro Fakt zwei Nah-Fragen; im Alltag müssen sie erzeugt werden (Vorschlag: aus der Frage selbst durch Personentausch, `LoraTrainer.locality_prompts` macht das heute nur für „my <Nomen>“ mit 2 Tauschwörtern und war hier unwirksam: ce-Arm hatte sie an und leckte 0,75).
Folge: Der Alltags-Lernweg (AG6) soll Ortsanker aus einem größeren, formulierungsvielfältigen Tauschsatz erzeugen und optional `lora_subspace=minor` nutzen; Schalter bleiben aus, bis das am AG6-Tor (Tor-Schwellen unverändert) und am quantisierten Pfad bestätigt ist. Nächstes: WP-BP2b Tauschsatz-Generator + andere Formulierungen/Aufgaben als Held-out (Übertragung), Q4-Pfad; danach JEPA mit Gegenbeispiel-Term (BJ1-Folge).
