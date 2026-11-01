# Handy-Pfad mit Lern-Prüfung, Cloud-Trockenlauf (2026-10-13, Thread M)

`V13_HOME=<installiertes Home> bash TESTEN_TOOLFORECAST.sh --with-learning` gegen ein gefälschtes installiertes Home in der Cloud (Linux x86, nicht Redmi).
- Tap-Werkzeug gegen gepinntes b10964 neu gebaut (aktuelle Quelle), Parität PASS (133 s).
- Live-Prüfung 245/245 LIVE_PATH_CONFIRMED, Median 3,5 s je Aufruf, Tap-Spitze 925 MB.
- Lern-Prüfung mit festem Plan `specs/tool_forecast/learning-plan.json` (= vorregistrierte Runde 2): **CONTINUAL_LEARNING_CONFIRMED**, 610/610, 37 min.
  - Verschobene Fälle: Rechnen .54–.74, Notizen .69–.88 des gemessenen Fehlers.
  - In-Welt exakt 1.00.
- Das ist eine zweite Wiederholung mit einem anderen Encoder-Build als der vorregistrierte Lauf (dort 0.3.36-Rebuild), mit praktisch gleichen Zahlen.

Am Redmi offen: derselbe Befehl, Bericht `~/v13/exports/tool-forecast-*/report.json` hochladen.
