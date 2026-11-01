# WP-BP8c PREREG: Age-Wiederöffnen an echtem Lernen, zweiter Aufbau mit Widerspruch (G-AGE-REOPEN-001, echter Teil)

Festgelegt VOR jeder Messung dieses Aufbaus. Nachfolger von WP-BP8b (`BP8b_NO_SIGNAL`: Rauschen auf ANDEREN Fragen schadet nicht, Wechsel in 1 Fenster erholt). Kein Wiederholen, sondern die dort benannte neue Idee.

**Vorabüberlegung (Nutzerregel).** Der Bau steht (`lora_session.py`, `bp8_real_age.py`, echte `AgeControl`, unabhängiges Rauschsignal). Platz für Gewinn entsteht nur bei einem echten Zielkonflikt: Rauschen verlangt kleine Schritte, ein Wechsel gegen eine
starke Gewohnheit verlangt große. Dazu 1. Widerspruch auf DENSELBEN Fragen (je Fenster bekommt jeder Fakt von A mit 40 % einen zufällig falschen Etikett), 2. Gewohnheit stärker einprägen (8 statt 6 Lernfenster), 3. Wechsel auf neue Antworten.
Trennschärfe-Vortest (vor den Age-Armen, nur feste Arme, Seed 1): fixed_permissive (1,0) und fixed_conservative (0,45). Es muss ein Zielkonflikt sichtbar sein, sonst dominiert ein fester Wert und Age hat nichts zu steuern:
(a) noisy-Fehler permissive - conservative >= 0,10, UND (b) shift-Phase: conservative schlechter als permissive, nämlich mehr Fenster bis Fehler < 0,2 (>= +1 Fenster) oder shift-Fehler >= 0,10 höher.
Fehlt (a) oder (b): `BP8c_NO_SIGNAL`, Age-Arme laufen nicht.

**Aufbau.** Seeds 1, 2, 3. Fenster: learn 8, noisy 8 (40 % Widerspruch auf A, Kompetenz gegen die WAHREN Antworten), shift 8 (neue Antworten für A). 2 Schritte je Fenster, lr 1e-3 x Plastizität, KL-Anker wie BJ1.
Aufruf: `--windows 8 --learn-windows 8 --noise-frac 0.4 --steps-per-window 2`. Arme: `boot` | `noise_mad` | `noise_indep` | `fixed_permissive` | `fixed_conservative`.

**Kriterien** (Mittel über 3 Seeds; A = noise_indep, B = boot, C = noise_mad; Fehler = 1 - Kompetenz), unverändert aus BP8b:
1. noisy-Fehler A <= 0,85 x B. 2. shift-Fehler A <= 1,10 x B. 3. Fenster bis shift-Fehler < 0,2: A <= B + 1. 4. shift-Fehler A <= C.
5. noisy-Fehler A <= 1,10 x fixed_conservative. 6. shift-Fehler A <= 1,25 x fixed_permissive.
Urteil `BP8c_REAL_PASS` nur bei allen sechs, sonst `BP8c_REAL_FAIL`. Bei PASS gilt G-AGE-REOPEN-001 (echter Teil) als erfüllt erst nach Wiederholung auf frischen Seeds 4-6 und Nutzer-Freigabe; `noise_aware` bleibt Standard laut Entscheidung 22.10. (Nutzer entscheidet über Änderungen).
Grenzen: 6 Fakten, 12 Prüfpunkte, 3 Seeds, B1 fp32, erfundene Fakten, kein Handy; Unterschiede unter ~0,10 sind Rauschen.
