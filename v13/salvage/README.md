# Salvage aus der Übergabe (Sichtung 2026-10-09)

Nur Referenz-Kopien. Nichts hier wird importiert oder getestet. Wer etwas zurück nach `code/` holt, macht das mit Test und Ledger-Eintrag.
Details und Begründung: `../SICHTUNG.md`.

| Ordner | Quelle | Prio | Wozu |
|---|---|---|---|
| body_train_port/ | burst5 (06.10.) `v13/body_training.py` + Test + Proof | A, zurückholen | Fail-closed-Vertrag für nativen Body-Train-Port (WP-I/S6). Ging bei den Recoveries 07.–09.10. unbemerkt verloren. Requantizer-Pflicht braucht Ausnahme für FP32-Slices (`token_embd_norm`). |
| native_capability_profile/ | burst5 `verification.py` Z. 33–50, `operator.py` Z. 176–177, `world.py` Z. 136 | A | Gemeinsames Fähigkeitsprofil für `:self`/`:doctor`/`:world`. `:capability` ist heute von `age.py` belegt, also neuer Befehl z. B. `:native`. |
| executive_implicit_task/ | burst5 `executive.py` Z. 78–83 + Test `test_implicit_task_tracks_current_turn_but_explicit_task_persists` + Beleg-JSON | A, Bugfix | Aktuell `code/v13/executive.py:96`: erste Nutzerfrage bleibt für immer `active_task` und landet in jedem nativen Kontext. |
| step2_task_score/ | burst5 `scripts/analyze_step2_proof.py` (`task_score`) + Test | A | Aufgabengebundene STEP2-Bewertung für WP-G. |
| burst5_branch/latest_to_burst5.diff | diff aktueller Stand → burst5 (nur v13/ und tests/) | Referenz | Zeilen mit `+` existierten in burst5 und fehlen heute. Viel Rauschen, weil der aktuelle Stand sonst weiter ist. |
| v10_starter/ | `V13_v10.zip` starter | B | Eligibility mit TTL/Versionsbindung, Inferenz vor Training, Admissions-Checkliste für Modellpaare. |
| ijepa_torch_ref/ | `03_WORK_STATUS/code (26).py`, `(27).py` | B | Maskiertes JEPA + EMA-Target + VICReg mit Kovarianzterm (für WP-S4). torch, nur Vorlage. |
| kl_topk_overflow/ | `inquisition_rsi.py` Z. 685–760 (`opd_step`) | B | Top-k + Overflow-Bin-KL, passt zu Drift-Gate WP-S5 mit llama-server-Logprobs. |
| lora_slow_merge_moe_ref/ | `V13_Brain_complete_v1.1/v13_brain.py` Z. 176–235, 252–330 | B | Langsamer LoRA→Basis-Merge, SparseMoE-Losses. Achtung: Training dort sieht Zukunftstokens. |
| rule_proposals/ | `V13_Termux_v11/v13term/store.py` Z. 41–100, 251–300 | B | Regelvorschläge mit Digest/Stale-Check, nur Owner entscheidet (Age-Fähigkeit `propose_config_changes`). |
