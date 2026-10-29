# Weltmodell am Handy ansehen — nur lesen

Die folgenden Befehle funktionieren in der lokalen Termux-Konsole von V13, **nicht** als normale Chatfrage. Sie verändern keine Regeln, trainieren kein Modell und starten keine Werkzeuge.

`:worldmodel status` zeigt, ob das kleine Weltmodell schon aus beobachteten **eigenen V13-Aktionen** angepasst wurde. `NOT_FITTED` bedeutet: Es gibt noch kein solches Modell. `FITTED` bedeutet **nicht**, dass seine Vorhersagen zuverlässig sind.

`:worldmodel event <Event-ID> detail` fragt: *Was würde das Weltmodell für die Route „detail“ bei diesem bereits gespeicherten Ereignis erwarten?* Erlaubte Routen: `simple`, `detail`, `gist`, `both`. Die Event-ID muss zum aktuell geöffneten Chat gehören. Fehlende und fremde IDs werden gleich abgelehnt.

Jede Vorhersage bleibt **HYPOTHESIS / SELF_CAUSED**: eine unsichere Simulation von V13s eigener Rechenzeit/Antwortlänge, keine bewiesene Wirkung und keine Aussage über die Außenwelt. `SIMULATION_UNCERTAIN` bedeutet, dass das Modell dafür keine ausreichende Stützung hat. Dieser Befehl passt das Weltmodell **nicht** neu an. Das bestehende `:world` bleibt unverändert.

**Stand:** review-only Kandidat in PR #1141; nicht als auf dem Redmi installiert behaupten. Age0 bleibt RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0; keine neuen Lernrechte.
