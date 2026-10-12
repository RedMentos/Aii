# G13 Langlauf-Soak 2026-10-12 (Linux, Fixture-Sprecher)

`python scripts/longrun_soak.py --home <tmp> --days 7 --turns 4` nach dem Wake-Replay-Fix. Ergebnis `report.json`:
**PASS**, 7/7 Tage, 28 Fakten alle abrufbar, voller Schlaf jede Nacht DONE, Wake-Priorität korrekt, Neustart-Weckung korrekt,
DB 4,5 → 8,2 MB, Prozess-RSS 51 → 65 MB. Befund WARN `REPLAY_BACKLOG_GROWS` (4 → 24 fällig, Age-0-Budget).
Vor dem Fix: ab Tag 2 kein voller Schlaf mehr (Burn-out durch Wach-Replays), siehe `docs/LONGRUN_SOAK.md`.
Evidenzstufe: Linux-Softwaretest, keine Redmi-Messung.
