# WP-KL3b Vorregistrierung: strenge Toleranz außer bei überstimmten Labels (vor dem Lauf committet)

Anlass: KL3 (`KL3_FAIR_GATE_FAIL`, nur L3): zwei kurze falsche Freigaben direkt nach der Verschiebung (3/32
unveränderte Fragen gekippt). Vermutete Ursache: Toleranz „ein Element je Route“ auch für Routen ohne überstimmte Labels.
Änderung: `route_gate_outvoted=2` = wie 1, aber die Ein-Element-Toleranz gilt nur für Routen mit mindestens einem
überstimmten Label; sonst streng `retention_max_delta` (0,02). Sonst unverändert.
Messung: `code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed,fixed+lex+rec+cv+ov,fixed+lex+rec+cv+ovs,adaptive+lex+rec+cv+ovs`,
frische Seeds S = 113, 127, 131; Ausgabe `v13/bench-results/kl3b-strict-gate-20261027/kl3b-seed<S>.json`.
Kriterien: L1–L6 aus KL3 unverändert, auf den Armen fixed+lex+rec+cv+ovs und adaptive+lex+rec+cv+ovs, in allen drei
Seeds (`KL3B_STRICT_GATE_PASS`). Beschreibend: Vergleich mit +ov, unnötige Freigaben, half_novel/detail_near.
Grenzen wie KL1.
