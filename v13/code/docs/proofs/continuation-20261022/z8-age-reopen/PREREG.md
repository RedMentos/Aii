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

---
## Nachtrag vor Lauf 2 (WP-Z8c, geschrieben nach Lauf 1, vor Lauf 2): Kandidat `noise_aware_v2`
Lauf 1 (Seeds 101–120) ergab `Z8_AGE_REOPEN_FAIL` (nur K2 verfehlt, siehe BEFUND.md). Diagnose: die Rausch-Dämpfung von
`noise_aware` dämpft auch das Wiederöffnen (Neuheits-Boden und Fehler-Bonus werden mit dem in der noisy-Phase hoch
geschätzten Rauschen multipliziert). Kandidat, nur im Skript als Unterklasse (keine Produktänderung):
(a) Neuheits-Boden (.8) und neue Modalität (1.0) wirken **nach** der Dämpfung; (b) ab `PERSISTENT_ERRORS` (2) Fehlschlägen
in Folge ist der Fehler-Bonus ungedämpft (anhaltende Fehler sind kein Rauschen). Arme zusätzlich `v2`, `v2_no_reopen`, `v2_restart`.
Frische Seeds 201–220. Kriterien K1–K6 unverändert, angewandt auf `v2` (K2 gegen `v2_no_reopen`, K5 gegen `v2_restart`), plus
- K7 Rausch-Vorteil bleibt: Fehler noisy-Phase von `v2` im Mittel höchstens 10 % über `noise_aware` (gleiche Seeds).
`Z8C_V2_PASS` nur wenn K1–K7 gelten; dann Empfehlung, `noise_aware` im Produkt so zu ändern (eigener Schritt). Sonst `Z8C_V2_FAIL`.
Lauf 1 bleibt FAIL, unabhängig vom Ergebnis von Lauf 2.
