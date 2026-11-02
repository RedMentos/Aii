# WP-BP8b PREREG: Age-Wiederöffnen mit unabhängigem Rauschsignal an ECHTEM Gewichts-Lernen (G-AGE-REOPEN-001, echter Teil)

Festgelegt VOR jeder Messung (nur Smoke, 2 Fenster, keine Auswertung).

**Vorabüberlegung (Nutzerregel).** Die Software-Messungen v1/v2 (Thread a667fm) fielen durch am Zielkonflikt "Rauschen dämpfen / echten Wechsel schnell öffnen" auf einem linearen Lerner; sie sagten
selbst, der Anschluss an echtes Lernen fehle. Jetzt da: BP2 (Adapter-Lernweg auf B1), das unabhängige Rauschsignal (`age.record(metrics['noise_signal'])`, zwei Prüfhälften), die echte `AgeControl`, und neu
`v13/lora_session.py` (Lernen in kleinen Fenstern, Schrittgröße = Basis-lr x Plastizität, Kompetenz = Token-Treffer bei Teacher-Forcing). Verbraucher der Plastizität ist die echte Schrittgröße des Adapters.
Platz für Gewinn: sichtbar nur, wenn das Etiketten-Rauschen die Kompetenz auf A messbar senkt (Arm fixed_permissive vs fixed_conservative) und der Zielwechsel schnell erholt werden muss; das wird
mit den festen Armen mitgemessen. Wenn fixed_permissive und fixed_conservative in der Rausch-Phase weniger als 0,10 Fehler auseinanderliegen, ist die Phase nicht trennscharf (`BP8b_NO_SIGNAL`).
Grenzen vorab: 6 Fakten x 2 Fragen = 12 Prüfpunkte (6 je Hälfte), nur 6 Fenster je Phase; Unterschiede unter ~0,10 sind Rauschen. Das ist eine Stichprobe, keine Statistik über Wochen.

**Aufbau.** Pro Seed (1, 2, 3): learn (6 Fenster, Fakten A mit wahren Antworten) -> noisy (6 Fenster, A wahr + 6 Fragen B mit in jedem Fenster neu zufällig FALSCHEN Antworten) -> shift (6 Fenster, der Mensch
korrigiert A: neue Antworten). 2 Schritte je Fenster, lr 1e-3 x Plastizität, KL-Anker wie BJ1. Kompetenz nach jedem Fenster auf der AKTUELLEN Wahrheit von A (shift: neue Antworten).
Arme: `boot` | `noise_mad` (noise_aware ohne Signal) | `noise_indep` (noise_aware mit Signal) | `fixed_permissive` (1,0) | `fixed_conservative` (0,45).

**Kriterien** (Mittel über 3 Seeds; A = noise_indep, B = boot, C = noise_mad; Fehler = 1 - Kompetenz):
1. noisy-Fehler A <= 0,85 x B. 2. shift-Fehler A <= 1,10 x B. 3. Fenster bis shift-Fehler < 0,2: A <= B + 1. 4. shift-Fehler A <= C.
5. noisy-Fehler A <= 1,10 x fixed_conservative. 6. shift-Fehler A <= 1,25 x fixed_permissive.
Urteil `BP8b_REAL_PASS` nur bei allen sechs; sonst `BP8b_REAL_FAIL` und es bleibt stehen. G-AGE-REOPEN-001 gilt erst nach Wiederholung auf frischen Seeds als geschlossen; Standard `noise_aware` bleibt Nutzerentscheidung.

## Nachtrag A1 (nach dem Smoke, vor jeder Wertung)
Der Smoke (2 Fenster je Phase, 1 Schritt, Seed 99, noise_indep) zeigt: die 6 Fakten sind schon nach 1-2 Fenstern gelernt (Fehler .22 -> .05), und das Etiketten-Rauschen aus B drückt die Kompetenz auf A kaum (Fehler .05-.08 in der Rausch-Phase). Damit ist unsicher, ob die Rausch-Phase trennscharf ist. Darum zuerst NUR die beiden festen Arme auf Seed 1 (ca. 45 Min): Liegt der Rausch-Phasen-Fehler von fixed_permissive nicht mindestens 0,10 über fixed_conservative, gilt vorab `BP8b_NO_SIGNAL` und die Age-Arme laufen nicht (kein Platz für Gewinn). Sonst laufen alle fünf Arme auf den Seeds 1-3 wie oben. Keine Parameter werden geändert.
