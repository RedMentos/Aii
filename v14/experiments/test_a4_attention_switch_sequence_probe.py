import copy
import hashlib
import json
import pytest

from a4_attention_switch_sequence_probe import evaluate, main


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def make_receipt(index, session, trial, goal, start, salience, caution, interrupt):
    source_id = f"audio:{session}:{trial}:{index}"
    source = {"source_id": source_id, "sha256": sha(source_id), "char_start": 0,
              "char_end": 0, "modality": "audio/pcm16le"}
    gains = {"perceptual": 0.55, "callosum": 0.4 + 0.01*index, "workspace": 0.6,
             "focal": 0.65 + 0.01*index, "action": 0.55 - 0.01*index}
    return {
        "schema_version": "1.0", "producer_component": "A4_AUDIO",
        "packet_id": f"a4-{session}-{trial}-{index}", "event_id": f"event-{session}-{trial}-{index}",
        "brain_generation_id": "gen-1", "percept_packet_id": f"a5-{session}-{trial}-{index}",
        "source_ref": source, "provenance": [source], "start_ms": start, "end_ms": start+400,
        "finality": "FINAL", "score_vector": {"kind": "A4_CONTROL_SCORE_NOT_AAD",
        "salience": salience, "caution": caution, "gains": gains, "interrupt": interrupt,
        "interrupt_reason": "external_interrupt" if interrupt else None, "truth_authority": 0},
        "learning_authority": False, "action_authority": False, "truth_authority": 0,
    }


def dataset(evidence_class="SYNTHETIC_FIXTURE", label_kind="OBSERVED_ATTENDED_STATE"):
    rows = []
    for session in ("s1", "s2"):
        for goal in ("COMPREHENSION", "IDENTIFICATION"):
            trial = f"{session}-{goal}"
            # A transition occurs after the third window. A4 scores rise before it.
            values = [(0.1,0.1,False),(0.15,0.1,False),(0.85,0.7,True),
                      (0.2,0.1,False),(0.1,0.1,False),(0.1,0.1,False)]
            for i,(sal,caut,interrupt) in enumerate(values):
                start = i*1000
                before = "STATE_A" if i < 3 else "STATE_B"
                after = "STATE_B" if i >= 2 else "STATE_A"
                switch_at = start+500 if i == 2 else None
                outcome_id = f"observer:{session}:{trial}:{i}"
                receipt = make_receipt(i,session,trial,goal,start,sal,caut,interrupt)
                rows.append({
                    "evidence_class": evidence_class,
                    "a4_receipt": receipt,
                    "outcome": {
                        "source_ref": {"source_id": outcome_id, "sha256": sha(outcome_id),
                                        "char_start":0,"char_end":0,"modality":{
                                            "TARGET_CUE":"attention/target-cue",
                                            "EEG_DECODER_ESTIMATE":"attention/eeg-decoder-estimate",
                                            "OBSERVED_ATTENDED_STATE":"attention/attended-state"
                                        }[label_kind]},
                        "timebase_source_ref": copy.deepcopy(receipt["source_ref"]),
                        "brain_generation_id":"gen-1",
                        "session_id":session,"trial_id":trial,"goal_id":goal,
                        "label_kind":label_kind,"state_before":before,"state_after":after,
                        "next_switch_at_ms":switch_at,
                        "observed_at_ms":(start+800 if switch_at is not None else start+1400),
                        "learning_authority":False,"action_authority":False,
                    },
                })
    return rows


def test_a4_sequence_probe_detects_pre_switch_salience_and_reports_scope():
    result = evaluate(dataset(), horizon_ms=1000, history_ms=1500, permutations=40)
    assert result["schema"] == "v14.a4-attention-switch-sequence-probe/1"
    assert result["sample_count"] == 24
    assert result["session_count"] == 2 and result["goal_count"] == 2
    assert result["label_scope"] == "SEPARATELY_OBSERVED_ATTENDED_STATE"
    assert result["mean_auc_by_feature"]["salience_now"] == 1.0
    assert result["switch_lead_ms"]["mean"] == 100.0
    assert result["interrupt_operating_point"]["false_positive_rate"] == 0.0
    assert result["negative_controls"]["salience_now"]["zero_score_auc"] == 0.5
    assert result["training_performed"] is False
    assert result["policy_changed"] is False
    assert result["learning_authority"] is False and result["action_authority"] is False


def test_instruction_and_eeg_decoder_labels_keep_distinct_evidence_scope():
    result = evaluate(dataset(label_kind="TARGET_CUE"), horizon_ms=1000, history_ms=1500, permutations=20)
    assert result["label_scope"] == "INSTRUCTION_TARGET_ONLY_NOT_OBSERVED_ATTENTION"
    result = evaluate(dataset(label_kind="EEG_DECODER_ESTIMATE"), horizon_ms=1000, history_ms=1500, permutations=20)
    assert result["label_scope"] == "MODEL_ESTIMATED_ATTENDED_STATE_NOT_GROUND_TRUTH"


def test_rejects_same_source_and_unfinalized_receipts():
    rows = dataset()
    rows[0]["outcome"]["source_ref"] = copy.deepcopy(rows[0]["a4_receipt"]["source_ref"])
    rows[0]["outcome"]["source_ref"]["modality"] = "attention/attended-state"
    with pytest.raises(ValueError, match="independent source"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[0]["a4_receipt"]["finality"] = "PROVISIONAL"
    with pytest.raises(ValueError, match="FINAL"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_rejects_timebase_mismatch_and_generation_mismatch():
    rows = dataset()
    rows[0]["outcome"]["timebase_source_ref"]["sha256"] = sha("other-audio")
    with pytest.raises(ValueError, match="timebase"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[0]["outcome"]["brain_generation_id"] = "other-generation"
    with pytest.raises(ValueError, match="generation"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_rejects_authority_leak_and_raw_audio():
    rows = dataset()
    rows[0]["a4_receipt"]["learning_authority"] = True
    with pytest.raises(PermissionError):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[0]["a4_receipt"]["pcm"] = b"secret"
    with pytest.raises(ValueError, match="raw audio"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_rejects_censored_stable_outcome_instead_of_calling_it_no_switch():
    rows = dataset()
    rows[0]["outcome"]["observed_at_ms"] = rows[0]["a4_receipt"]["end_ms"] + 100
    with pytest.raises(ValueError, match="censored"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_rejects_future_label_leak_and_mixed_evidence_classes():
    rows = dataset()
    rows[0]["outcome"]["observed_at_ms"] = rows[0]["a4_receipt"]["end_ms"] - 1
    with pytest.raises(ValueError, match="observed after"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[-1]["evidence_class"] = "OBSERVED_LOCAL"
    with pytest.raises(ValueError, match="do not mix"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_requires_two_sessions_two_goals_and_both_classes_per_stratum():
    rows = dataset()
    with pytest.raises(ValueError, match="two disjoint sessions"):
        evaluate([r for r in rows if r["outcome"]["session_id"] == "s1"],
                 horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    for r in rows:
        r["outcome"]["goal_id"] = "ONE_GOAL"
    with pytest.raises(ValueError, match="two goal strata"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_rejects_aad_posterior_relabeling_duplicate_ids_and_horizon_leak():
    rows = dataset()
    rows[0]["a4_receipt"]["score_vector"]["kind"] = "ATTENDED_STREAM_PROBABILITY"
    with pytest.raises(ValueError, match="NOT_AAD"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[1]["a4_receipt"]["packet_id"] = rows[0]["a4_receipt"]["packet_id"]
    with pytest.raises(ValueError, match="duplicate"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)
    rows = dataset()
    rows[0]["outcome"]["observed_at_ms"] = rows[0]["a4_receipt"]["end_ms"] + 1001
    with pytest.raises(ValueError, match="horizon"):
        evaluate(rows, horizon_ms=1000, history_ms=1500, permutations=5)


def test_cli_requires_observed_data_unless_synthetic_flag_is_explicit(tmp_path, capsys):
    path = tmp_path / "records.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in dataset()) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="OBSERVED_LOCAL is required"):
        main(["--input", str(path), "--horizon-ms", "1000", "--history-ms", "1500", "--permutations", "5"])
    assert main(["--input", str(path), "--horizon-ms", "1000", "--history-ms", "1500",
                 "--permutations", "5", "--allow-synthetic"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["evidence_class"] == "SYNTHETIC_FIXTURE"
    assert output["policy_changed"] is False
