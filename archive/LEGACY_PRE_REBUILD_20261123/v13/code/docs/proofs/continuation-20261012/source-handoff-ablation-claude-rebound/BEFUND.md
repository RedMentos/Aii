# 16-Fall-Source-Handoff-Ablation — Befund (Claude, 2026-10-12)

Status **RECORDED_DIAGNOSIS**: 16/16 Zeilen, 0 strukturelle Fehler, echte B2 (Qwen3.5-0.8B) und C3 (LFM2.5-350M) FINAL, alle Prozesse beendet, Artefakte während des Laufs unverändert. Preregistrierung `07f7f7bc…89e0` (Neubindung von `4cfaddad…b1d0` vor der ersten Inferenz, nur Runner-/Bibliotheks-Hashes anders, siehe `rebinding-before-inference.json`). Report SHA256 `b8c748c5d6ca3762a488c132446164e272a2086fcb89e49f7aaae2ba67386beb`. Linux-Cloud (4 CPU, ohne 8-GiB-Cgroup), kein Redmi-Nachweis, `canonical_gate_pass=false`.

| Arm | mittl. strikter Nutzen | exakte Entscheidungen | Zeilen mit Zitat aus früherer Quelle |
|---|---|---|---|
| baseline | 0.5625 | 0/4 | 0/4 |
| state_off | 0.3958 | 0/4 | 0/4 |
| semantics_only | 0.5625 | 0/4 | 0/4 |
| full_candidate | 0.5208 | 0/4 | 0/4 |

## Kernbefund
- **In keinem Arm gelangt ein Zitat aus der früheren Quelle zum Konsumenten.** B2 hat die frühere Quelle als `context_source_ref` (1/1 in allen Zeilen), zitiert aber nur den aktuellen Text (z. B. „Project Mira“). Budget/Deadline/Local-Regel aus der früheren Quelle fehlen deshalb in allen Armen.
- Folge: C3 antwortet in allen 16 Zeilen `action: NONE`; Unterschiede zwischen den Armen sind Rauschen in Rechenfeldern (z. B. `remaining`), keine Wirkung des Source-Handoffs. `state_off` verliert durch eine ungültige Entitätszuordnung (Lumen).
- Der Kandidat (`full_candidate`) bringt damit **keinen messbaren Vorteil**; die Hypothese „Body-State verdrängt Quellenwissen“ ist nicht die Hauptursache. Engpass ist das Zitieren der früheren Quelle durch den Produzenten.
- Korrupt-Kontrolle (Tessera): kein korruptes Zitat zugestellt (trivial, da gar keins zugestellt).

## Was das für die Umsetzung ändert
- Kein Integrationsgrund für den full_candidate-Prompt allein. Nächster Kandidat muss die Übergabe der früheren Regeln selbst sichern (z. B. exakte Regel-Spans der früheren Quelle als verifizierte Zitate unabhängig vom B2-Text, oder B2-Aufgabe „zitiere Regeln aus früheren Quellen“), separat preregistriert.
- STEP2 UTILITY_FAIL bleibt. Die Freigabe der eingefrorenen 121 Quellen ist damit aus Sicht dieser Ablation erreicht (Kohorte abgeschlossen).
