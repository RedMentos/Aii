# §99-Ablation: gelernter Halte-Multiplikator des Workspace (WP-U8 L3-B4) — **SUPPORTED_SYNTHETIC nach Regel, Effekt praktisch null** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_workspace_hold.py`, Vorregistrierung `preregistration.json` (Commit `17e1cba`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echtes `workspace_learn` (observe/decay_factor/Modus) auf SQLite; der Workspace drumherum ist Harness-Code nach `focal.Workspace` (Zerfall × 0,6 × Multiplikator, gedeckelt auf den bisherigen Zerfall; Drop unter 0,05; Kapazität 6).
3 neue Einträge je Turn; Wieder-Bedarf je Turn versteckt nach Art: MEMORY .45, B1 .20, B2 .04, bis 8 Turns. Primärmaß: Wiederherstellungs-Verluste in der zweiten Hälfte (400 Turns).

| Arm | Verluste (2. Hälfte) | nützlich gehalten | umsonst gehalten |
|---|---|---|---|
| gelernt (ACTIVE) | **778,8** | 322,4 | 877,6 |
| SHADOW (fester Zerfall) | 782,0 | 319,2 | 880,8 |
| vertauschte Multiplikatoren | 784,6 | 316,6 | 883,4 |
| alles maximal halten (1,5) | 782,0 | 319,2 | 880,8 |

Siege von 5: SHADOW 4, vertauscht 5, alles halten 4 → nach Regel SUPPORTED_SYNTHETIC.

- Der Lerner findet die richtige Reihenfolge (Endmultiplikator MEMORY 1,1–1,37 > B1 0,92–1,07 > B2 0,79–0,86).
- **Der Effekt ist aber praktisch null:** 0,4 % weniger Verluste.
- Ursache ist strukturell: Neue Einträge kommen mit Zerfall 1 an, der Multiplikator kann den Zerfall gehaltener Slots nur bremsen (Deckel = bisheriger Zerfall). Unter Kapazitätsdruck verdrängen frische Einträge deshalb fast immer die gehaltenen. „Alles halten“ ist darum identisch mit SHADOW.
- Folge: Soll das Halten etwas bringen, muss der Multiplikator in die Zulassung (Priorität beim Behalten) eingehen, nicht nur in den Zerfall. Das wäre ein neuer, getrennt vorregistrierter Kandidat.
- Grenze: Harness-Workspace (Behalten nach Zerfall, nicht nach voller Priorität wie `focal.Workspace.save`), synthetische Wiederbedarfs-Raten.
