# WP-Z8b Vorregistrierung: Wiederöffnen-Test für G-AGE-REOPEN-001

Geschrieben und committet **vor** dem ersten Lauf (2026-10-22, Thread „Offene Ziel-Pakete Z6 bis Z12“).

## Frage
Blueprint §16.1/§95.3: stabile reife Fähigkeiten werden weniger plastisch; neue Domänen oder wiederholte Fehler dürfen
die Pfade wieder öffnen. §100 Gate G-AGE-REOPEN-001 „Age stages with hysteresis and re-open“ braucht dafür Code, echten
Zustandspfad, Persistenz/Neustart, Test, Telemetrie, Ablations-Basis und Grenzen. Die Nutzerentscheidung vom 22.10.
(`age_plasticity_policy = noise_aware`) ließ genau diesen Test offen. Die alte WP-AB-Messung hatte keine Neustart-Prüfung,
keinen Arm „gleiche Policy ohne Wiederöffnen“ und keine Phase nach dem Umlernen (schließt es sich wieder?).

## Aufbau
Echtes `AgeControl` auf echtem `Store` (SQLite) steuert die Lernrate eines NLMS-Lerners (Helfer aus `v13/ablation99.py`).
Strom pro Seed: learn 0–600 (Ziel w) → noisy 600–1000 (10 % feindliche Labels, mehr Rauschen) → shift 1000–1600 (neues
Ziel w2) → settle 1600–2200 (w2, normal). Alle 50 Schritte ein Nachweis an `AgeControl.record` (wie WP-AB).
Seeds 101–120 (20, frisch; WP-AB nutzte 13–17). Arme: `noise_aware` (Standard), `noise_no_reopen` (gleiche Policy,
Neuheit und wiederholte Fehler fest 0), `boot`, `stable_reopen`, `fixed_conservative` (.45), `fixed_permissive` (1.0),
`noise_aware_restart` (wie `noise_aware`, bei t=1300 Store geschlossen und AgeControl neu von der Platte geöffnet).

## Kriterien (alle müssen gelten → `Z8_AGE_REOPEN_PASS`, sonst `Z8_AGE_REOPEN_FAIL` mit Angabe, was fehlte)
- K1 öffnet bei echtem Wechsel: mittlere Plastizität Schritte 1000–1100 ≥ 1,25 × Schritte 500–600, in ≥ 16/20 Seeds.
- K2 Öffnen hilft: Fehler Schritte 1000–1250 von `noise_aware` kleiner als `noise_no_reopen` in ≥ 15/20 Seeds **und** im Mittel ≥ 10 % kleiner.
- K3 kein falsches Öffnen durch Rauschen: Median über Seeds von Plastizität(noisy) / Plastizität(500–600) ≤ 1,25.
- K4 schließt nach dem Umlernen wieder: Median von Plastizität(2100–2200) / Plastizität(1000–1100) ≤ 0,8.
- K5 Neustart: `noise_aware_restart` in allen Seeds in allen Werten gleich `noise_aware`.
- K6 kein Stufen-Flattern unter Rauschen: Median der Stufenwechsel in der noisy-Phase ≤ 2.
Telemetrie: Zahl der `age_transition`-Ereignisse im Store wird je Lauf mitgeschrieben (beschreibend).
Beschreibend, ohne Schwelle: Fehler je Phase aller Arme (Ablations-Basis fixed/boot/stable_reopen).

## Grenzen (vorab)
Synthetischer linearer Strom, kein Sprachmodell, keine Handy-Messung. Ein PASS heißt: der echte Age-Zustandspfad
öffnet/schließt wie im Blueprint beschrieben und übersteht Neustart; er heißt nicht, dass Age echte Modelle stabiler macht.
Ein FAIL bleibt FAIL; keine nachträgliche Schwelle.
