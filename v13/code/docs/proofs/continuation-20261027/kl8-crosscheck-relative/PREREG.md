# WP-KL8 Vorregistrierung: Gegenprobe der relativen Prüfung (Branch h02m13) nur aus Korrekturen (vor dem Lauf committet)

Frage: Lernt der führende Weg (Wort-Kanal `route_head_words` + `route_head_gate=relative`, Z6I2_PASS) die geänderte
Vorliebe auch ohne menschliche Regel und ohne `--lehre`, also nur aus Routen-Korrekturen wie in der KL-Reihe?
Code unverändert von `origin/claude/project-thread-h02m13` (bc0703f4), eigener Arbeitsbaum; Bench dort:
`code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed,fixed+words+rel,adaptive+words+rel`
(kein `+now`, kein `+teach`, kein `+sup`), Seeds S = 107, 109, 113 (von h02m13 nicht benutzt).
Ausgabe `v13/bench-results/kl8-crosscheck-relative-20261027/kl8-seed<S>.json` (in diesem Branch abgelegt).

Kriterien (`KL8_RELATIVE_ONLY_CORRECTIONS_PASS` nur wenn in allen drei Seeds, beide Arme `+words+rel`):
R1 Kopf selbst am Ende ≥ 80 % Hälfte-Fragen (`final_half_items`); R2 Behalten ≥ 90 % (`retention_unchanged`);
R3 keine falsche Freigabe; R4 Rücknahme exakt; R5 Kontrolle fixed < 50 %.
Beschreibend: Korrekturen bis Hälfte ≥ 80 %, Vergleich mit den KL-Armen. Grenzen wie KL1.
