# §99-Ablation: Event-Segmentierung in einem Text (WP-N8 A1, §51.2) — **PARTIAL** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_event_segments.py`, Vorregistrierung `preregistration.json` (Commit `11869cc`, vor dem Lauf gepusht), Rohdaten `report.json`.
Texte aus den eingefrorenen Themensätzen `bench-results/jepa-ablation-20261010/sentences.json` (16 Themen): je Text 3 Themen × 3–5 Sätze, 40 Texte je Saat, 5 Saaten. Echtes, unverändertes `episodes.text_segments` (Breite 240).
Primärmaß: Grenz-F1 (Schnitt genau am ersten Satz des neuen Themas, Leerraum übersprungen) auf `flat` (Themen nur durch Leerzeichen getrennt).

| Bedingung | event | feste 240 Zeichen | gleich viele Schnitte, gleichmäßig | gleich viele, zufällig | event gewinnt (fest / gleichm. / zufällig) |
|---|---|---|---|---|---|
| flat | .263 | .010 | **.279** | .246 | 5 / 2 / 4 |
| para (Leerzeile zwischen Themen) | .513 | .012 | **.649** | .464 | 5 / 0 / 4 |

- Event-Segmente schneiden an Satzgrenzen und schlagen deshalb feste Blöcke klar und zufällige Satzgrenzen knapp.
- Sie schlagen aber **nicht** gleichmäßig verteilte Satzgrenzen mit gleicher Schnittzahl, nicht einmal, wenn eine Leerzeile die Themen trennt.
- Ursache: Der Längen-Prior (`fixed_chunk_prior` .40) plus Satzende (.25) erreicht allein die Schwelle .5. Es wird also vor allem nach Länge geschnitten (≈ 4 Schnitte bei 2 echten Grenzen); der lexikalische Themenwechsel trägt wenig bei, und selbst das Absatzsignal geht in den vielen Längenschnitten unter.
- Folge: Für Themen-Grenzen ist A1 heute kaum besser als „nach Länge an Satzenden schneiden“. Kandidat für später (getrennt vorregistrieren): höhere Schwelle oder geringerer Längen-Prior, sodass Absatz/Themenwechsel nötig sind; oder Einbettungs-Distanz statt lexikalischer Verschiebung.
- Grenze: kurze synthetische Themenmischungen aus einem Korpus, nur lexikalische Signale, Breite 240.
