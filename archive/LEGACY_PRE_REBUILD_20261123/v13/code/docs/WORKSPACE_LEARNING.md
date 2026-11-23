# WP-U8 B4 Workspace-Stabilitäts-Lernschleife (L3-B4, §8.1)

Der Workspace (`focal.Workspace`) lernt kein Wissen. Er lernt je Quellenart (B1_DETAIL, B2_GIST, MEMORY), wie lange sich das Halten eines Slots lohnt (`v13/workspace_learn.py`).

**Nach jedem Turn** (`Workspace.save`):
- **Refresh:** Ein gehaltener Slot (aus einem früheren Turn) wird wieder ACTIVE → nützlich (1). Wird er nicht aufgenommen → verschwendet (0). Daraus wird der gleitende Mittelwert `v_refresh` gebildet.
- **Wiederherstellung:** Ein neu aufgenommener Slot, dessen Inhalt vorher aus dem Workspace geflogen war, zählt als Verlust (1), andere neue Slots als 0. Daraus wird `r_restore` gebildet.
- **Quellenverlust:** Ein Slot, dessen Quelle nicht mehr lesbar ist, wird gezählt und nie gehalten (`L_B4_SOURCE_LOSS` gesperrt hoch).

**Multiplikator:** Ab 10 Beobachtungen je Art gilt m = 1 + 0,5 · (v_refresh − 0,5) + 0,5 · r_restore, begrenzt auf [0,5; 1,5].
- **SHADOW** (Standard): Der Wert wird nur protokolliert.
- **ACTIVE**: nur per `:workspace active` (Mensch). Dann multipliziert `Workspace.load` den Zerfall pro Turn dieser Art mit m. Der Zerfall steigt nie über den alten Wert.

**Grenzen:**
- Die Gewichte L_B4_ADMISSION und L_B4_REFRESH sind im Blueprint als [TUNE] ohne Wert angegeben; hier gilt BOOT 0,5.
- L_B4_BINDING hat noch keine gelernte Nutzung.

**Befehle:** `:workspace [status|shadow|active]`.
**Tests:** `tests/test_workspace_learn.py` (4).
