# WP-BP8: Age-Wiederöffnen mit unabhängigem Rauschsignal (G-AGE-REOPEN-001), Stand 2026-10-27

## Voraussetzungsprüfung
- Schwäche von `noise_aware` (2026-10-10): Das Rauschband ist die MAD der **Kompetenz selbst**, also zirkulär. Ein echter Kompetenzverlust weitet das Band mit und wird teils als Rauschen gelesen. Folge in der Messung vom 10.10.: Zielwechsel langsamer (0,079 gegen 0,053 bei boot).
- Fehlte: ein Rauschsignal, das **nicht** aus der beurteilten Zahl stammt. Gebaut: `age.record(..., metrics['noise_signal'])`, die Streuung einer Wiederholungsmessung desselben Nachweises (zwei unabhängige Hälften derselben Prüfmenge). `noise_aware` nimmt das Signal, sobald es ≥ 4 Nachweise gibt, sonst die alte MAD. Kein neuer Schalter, `age_plasticity_policy` bleibt `boot | stable_reopen | noise_aware`.
- Echtes Gewichts-Lernen (BP2) gibt es noch nicht. Deshalb läuft die Messung auf dem §99-Aufbau (lineare Lerner, synthetischer Strom, echte `AgeControl`), ergänzt um eine **verrauschte Messung** der Kompetenz mit zwei Wiederholungshälften. Das ist Software-Evidenz. Der Anschluss an den BP2-Messaufbau (echtes Training) bleibt offen; der Eingang `noise_signal` ist dafür schon da.

## Vorab-Registrierung (vor dem ersten Lauf, `scripts/bp8_age_reopen.py`, Seeds 401–405)
Strom wie `ablation99.age_stream` (learn 0–400, noisy 400–1000, shift 1000–1500). Alle 50 Schritte ein Nachweis: Kompetenz = 1 − normierter Fehler auf 24 Prüfpunkten mit dem Etiketten-Rauschen der Phase, zwei Hälften à 12; `noise_signal` = |Hälfte A − Hälfte B| / 2.
Arme: `boot`, `stable_reopen`, `noise_mad` (noise_aware ohne Signal), `noise_indep` (noise_aware mit Signal), `no_reopen`, `fixed_conservative` (0,45), `fixed_permissive` (1,0).
Kriterien (Mittel über 5 Seeds, alle müssen gelten, keine Schwellenänderung nach dem Lauf; A = noise_indep, B = boot, C = noise_mad):
1. Fehler in der noisy-Phase: A ≤ 0,85 · B.
2. Fehler in der shift-Phase: A ≤ 1,10 · B.
3. Schritte bis Fehler < 0,1 nach dem Zielwechsel: A ≤ 1,25 · B.
4. Falsche Herabstufungen in der noisy-Phase: A ≤ min(B, C).
5. Fehler in der shift-Phase: A ≤ C.
6. Age hilft gegenüber festen Werten: A noisy-Fehler ≤ fixed_conservative und A shift-Fehler ≤ 1,25 · fixed_permissive.
Wenn alle gelten: `BP8_AGE_REOPEN_SOFTWARE_PASS`. Das schließt G-AGE-REOPEN-001 **nicht**; das Gate bleibt offen, bis dasselbe mit echtem Gewichts-Training (BP2) gemessen ist. Standard `noise_aware` bleibt Nutzerentscheidung (2026-10-22 entschieden).
