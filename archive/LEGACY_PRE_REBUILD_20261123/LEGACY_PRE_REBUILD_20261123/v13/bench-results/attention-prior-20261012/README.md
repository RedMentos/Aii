# §99-Ablation: gelernter Attention-Nutzen-Prior (§4B.4) — **SUPPORTED_SYNTHETIC** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_attention_prior.py`, Vorregistrierung `preregistration.json` (Commit `0e31425`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echtes, unverändertes `attention.Attention` auf frischem SQLite-Store: Anfragen, Zulassung unter Budget, Ergebnis-Meldung und Prior je (Grund, Ziel). 300 Ereignisse × 8 Anfragen, Budget für 3. Versteckter Nutzen je Schlüssel gleichverteilt in [−1, 1], Ergebnis = Nutzen + Rauschen 0,3.
Primärmaß: mittlerer versteckter Nutzen der gewährten Anfragen in der zweiten Hälfte. Regel (vorab): „hilft“ nur, wenn ACTIVE (gelernter Prior genutzt) SHADOW (nur Gerüst) in ≥ 4/5 Saaten auf beiden Strömen schlägt.

| Strom | Gerüst (SHADOW) | gelernt (ACTIVE) | zufällig | Orakel | ACTIVE > SHADOW |
|---|---|---|---|---|---|
| blind (Priorität ohne Information) | .042 | **.160** | .049 | .599 | 5/5 |
| informiert (Priorität teils informativ) | .384 | **.471** | .042 | .600 | 5/5 |

- Der gelernte Prior hebt den Nutzen der Zulassung in beiden Strömen in jeder Saat.
- Er bleibt weit unter dem Orakel: Der Prior darf den Score nur um höchstens 25 % verschieben (`LEARNED_MAX`). Ohne informative Priorität holt er nur ein Viertel des möglichen Abstands.
- Grenze: synthetischer Anfrage-Strom, versteckter Nutzen nur je (Grund, Ziel), keine echten Modell-Anfragen. ACTIVE braucht weiter die ausdrückliche Nutzerfreigabe (`:attention active`); die Gain-Modulation (Salienz/Vorsicht) ist hier nicht geprüft.
