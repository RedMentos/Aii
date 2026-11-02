# WP-BP8c BEFUND: Age-Wiederöffnen an echtem Lernen mit Widerspruch: `BP8c_NO_SIGNAL` (kein Zielkonflikt, Age-Arme nicht gelaufen)

Vorregistrierung `PREREG.md` (vor jeder Zahl). Roh: `bench-results/bp8c-real-age-20261101/bp8c-seed1-fixed-arms.json`. B1, Seed 1, nur feste Arme (Vortest), 8+8+8 Fenster, 40 % falsche Etiketten auf denselben Fragen.

| Arm | learn-Fehler | noisy-Fehler (gegen wahre Antworten) | shift-Fehler | Fenster bis Fehler < 0,2 |
|---|---|---|---|---|
| fixed_permissive (1,0) | .048 | **.100** | .041 | 1 |
| fixed_conservative (0,45) | .067 | **.051** | .045 | 1 |

Vortest: (a) noisy-Fehler permissive - conservative >= 0,10: gemessen **0,049**, nicht erfüllt. (b) conservative im Wechsel schlechter (>= +1 Fenster oder >= 0,10): gemessen **0 Fenster, 0,004**, nicht erfüllt. Urteil nach Regel: `BP8c_NO_SIGNAL`.

## Was es zeigt
- Große Schritte leiden unter dem Widerspruch erkennbar (Fehler verdoppelt von .05 auf .10), aber nur halb so stark wie die geforderte Trennschärfe. Der Teil (a) des Zielkonflikts ist angedeutet, nicht erreicht.
- Der Wechsel gegen die Gewohnheit kostet bei kleinen Schritten nichts: beide Arme erholen sich in einem Fenster (Fehler < 0,2). Ein Zielkonflikt entsteht nicht, weil der echte Adapter mit 2 Schritten je Fenster auch bei lr 0,45e-3 schnell umlernt. Ein fester kleiner Wert genügt hier: die Age-Regel hat nichts zu steuern.
- Damit zwei Aufbauten (BP8b, BP8c) auf echtem B1 ohne Zielkonflikt. Der Zielkonflikt der Software-Läufe (lineare Lerner) existiert beim echten Adapter-Lernen in dieser Größenordnung nicht oder braucht Bedingungen, die vor der Messung nicht begründbar sind (mehr als 40 % falsche Etiketten, die den Nutzer nicht darstellen; kleinere Lernrate, die das Lernen verlangsamt). Weiteres Drehen an Parametern bis ein Konflikt entsteht wäre Anpassen des Tests an das gewünschte Ergebnis.
- G-AGE-REOPEN-001 bleibt offen, wird aber von mir nicht weiter über Parameter-Aufbauten gesucht. Offen für den Nutzer: Entweder die Wiederöffnungsregel bleibt als Schutz bei harten Wechseln (Software gemessen, `noise_aware` Standard) oder das Tor wird mit echten Nutzungsdaten auf dem Handy bewertet (Alltagsverlauf mit echten Korrekturen).
Grenzen: 1 Seed, 12 Prüfpunkte, Kompetenz als Teacher-Forcing-Treffer (Decke ~0,97), B1 fp32.
