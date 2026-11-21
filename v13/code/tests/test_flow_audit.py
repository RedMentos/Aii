import json
import sqlite3
import zlib

from v13.contracts import packet
from v13.flow_audit import audit_event, audit_latest
from v13.store import Store


def _fixture(home, *, include_c4=True, include_context=True):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        session = store.new_session("flow audit fixture")
        event = store.event(session, "PRIVATE_USER_TEXT_SENTINEL")
        evidence = store.source("PRIVATE_BODY_EVIDENCE_SENTINEL", "BODY_EVIDENCE")
        eid = event["event_id"]
        generation = event["brain_generation_id"]
        store.add_packet(
            "PerceptPacket",
            packet("PerceptPacket", "A5_PERCEPTION", eid, generation,
                   [event["source_ref"]], source_ref=event["source_ref"],
                   segments=[], modality="audio"),
        )
        offers = []
        query_ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            query = packet("QueryPacket", "C2_CONTROL", eid, generation,
                           [event["source_ref"]], target_role=role,
                           goal="source-bound evidence", source_refs=[event["source_ref"]])
            store.add_packet("QueryPacket", query)
            query_ids[role] = query["packet_id"]
            offer = packet(
                "OfferPacket", role, eid, generation, [event["source_ref"]],
                role=role, based_on_state_version=0,
                deadline_monotonic_ns=2**63 - 1,
                evidence_refs=[evidence],
                offer={"summary": "PRIVATE_OFFER_TEXT_SENTINEL"},
                confidence=0.9, query_packet_id=query_ids[role],
            )
            offer["native_metrics"] = {
                "role": role, "status": "FINAL", "actual_model": "fixture-" + role,
                "prompt_tokens": 41, "generated_tokens": 7, "ttft_s": 0.2,
                "duration_s": 0.5, "synthetic": True,
                "native_offer_prompt_receipt": {
                    "prompt_tokens": 41, "native_completion_http_200": True,
                    "native_template_submitted": True,
                    "native_attention_or_semantic_use_proven": False,
                },
            }
            store.add_packet("OfferPacket", offer)
            offers.append(offer)

        ids = [offer["packet_id"] for offer in offers]
        if include_c4:
            store.add_packet(
                "FocalCycle",
                packet("FocalCycle", "C4_FOCAL", eid, generation,
                       [event["source_ref"]], cycle=0, decision="INCORPORATE_AB",
                       coalition=ids, signals={}, budget={}),
            )
            for offer in offers:
                store.add_packet(
                    "FocalItem",
                    packet(
                        "FocalItem", "C4_FOCAL", eid, generation,
                        offer["provenance"], item_id=offer["packet_id"],
                        source_kind=offer["role"], source_refs=offer["evidence_refs"],
                        fact_hypothesis_status="HYPOTHESIS", state_type="ACTIVE",
                        salience=0.8, uncertainty=0.2, priority=0.9,
                        admission="LEGACY_FIRST_N",
                    ),
                )

        store.add_packet(
            "ActionSelection",
            packet("ActionSelection", "C5_ACTION", eid, generation,
                   [event["source_ref"]],
                   selected={"action_type": "ANSWER", "role": "C3_LANGUAGE"},
                   candidates=[], suppressed=[{"role": "B1_DETAIL"}, {"role": "B2_GIST"}],
                   permission_class="LOCAL_ONLY"),
        )
        store.add_packet(
            "MessagePacket",
            packet("MessagePacket", "B3_CALLOSUM", eid, generation,
                   [event["source_ref"]], channel="SYMBOLIC", sender="B1_DETAIL",
                   receiver="B2_GIST", source_refs=[evidence],
                   content={"offer_packet_id": ids[0]}),
        )
        store.add_packet(
            "LatentTapPacket",
            packet("LatentTapPacket", "B1_DETAIL", eid, generation,
                   [event["source_ref"]], role="B1_DETAIL",
                   source_ref=event["source_ref"], tap_id="tap-fixture",
                   model_revision="fixture-revision", token_ids=[1, 2],
                   feature_path="fixture/tap.bin", feature_sha256="a" * 64,
                   shape=[2, 4]),
        )

        metadata = {
            "selected_offer_ids": ids,
            "focal": {"coalition": ids},
            "context_source_refs": [event["source_ref"], evidence] if include_context else [],
            "runner": {
                "role": "C3_LANGUAGE", "status": "FINAL", "actual_model": "fixture-c3",
                "prompt_tokens": 89, "generated_tokens": 11, "ttft_s": 0.3,
                "duration_s": 0.8, "synthetic": True,
                "native_offer_prompt_receipt": {
                    "prompt_tokens": 89, "native_completion_http_200": True,
                    "native_template_submitted": True,
                    "native_attention_or_semantic_use_proven": False,
                },
                "CAN_LATENT_TAP": False, "CAN_LATENT_INJECT": False,
                "CAN_TRAIN_BODY": False,
            },
            "model_revision": "fixture-c3-revision",
        }
        store.message(
            session, eid, "assistant", "PRIVATE_ASSISTANT_TEXT_SENTINEL",
            status="FINAL", metadata=metadata,
        )
        return eid
    finally:
        store.close()


def test_full_b1_b2_c4_c3_path_is_reported_without_private_text(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    report = audit_event(home, event_id)

    assert report["read_only"] is True
    assert report["private_text_returned"] is False
    assert report["bodies"]["roles"] == ["B1_DETAIL", "B2_GIST"]
    assert report["bodies"]["query_binding_status"] == "PASS"
    assert all(x["query_role_match"] is True for x in report["bodies"]["offers"])
    assert all(x["prompt_token_source"] == "NATIVE_TOKENIZE_RECEIPT" for x in report["bodies"]["offers"])
    assert all(x["evidence_level"] == "SYNTHETIC_FIXTURE" for x in report["bodies"]["offers"])
    assert report["c4"]["status"] == "PASS"
    assert report["c4"]["consumed_roles"] == ["B1_DETAIL", "B2_GIST"]
    assert report["c3"]["status"] == "PASS"
    assert report["c3"]["source_bound_roles"] == ["B1_DETAIL", "B2_GIST"]
    assert report["c3"]["prompt_tokens"] == 89
    assert report["c3"]["native_completion_http_200"] is True
    assert report["c3"]["native_template_submitted"] is True
    assert report["c3"]["native_attention_or_semantic_use_proven"] is False
    assert report["c3"]["can_latent_inject"] is False
    assert report["evidence_level"] == "SYNTHETIC_FIXTURE"
    assert report["latent"]["native_injection_proven"] is False
    assert report["latent"]["status"] == "TAP_ONLY"
    encoded = json.dumps(report, ensure_ascii=False)
    assert "PRIVATE_USER_TEXT_SENTINEL" not in encoded
    assert "PRIVATE_BODY_EVIDENCE_SENTINEL" not in encoded
    assert "PRIVATE_OFFER_TEXT_SENTINEL" not in encoded
    assert "PRIVATE_ASSISTANT_TEXT_SENTINEL" not in encoded


def test_missing_c4_or_c3_context_is_not_promoted_to_pass(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home, include_c4=False, include_context=False)
    report = audit_event(home, event_id)
    assert report["c4"]["status"] == "FAIL"
    assert report["c3"]["status"] == "FAIL"
    assert "B1_B2_NOT_BOTH_CONSUMED_BY_C4" in report["warnings"]
    assert "B1_B2_NOT_BOTH_SOURCE_BOUND_IN_C3_CONTEXT" in report["warnings"]


def test_audit_latest_and_read_only_database(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    before = db.read_bytes()
    report = audit_latest(home)
    after = db.read_bytes()
    assert report["event_id"] == event_id
    assert before == after


def test_missing_event_fails_closed(tmp_path):
    home = tmp_path / "runtime"
    _fixture(home)
    try:
        audit_event(home, "evt_missing")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown event must fail closed")


def test_invalid_source_ref_is_reported_without_exposing_it(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT id,metadata FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        metadata = json.loads(row[1])
        metadata["context_source_refs"].append({
            "source_id": "src_missing_private",
            "sha256": "0" * 64,
            "char_start": 0,
            "char_end": 1,
            "modality": "text",
        })
        conn.execute("UPDATE messages SET metadata=? WHERE id=?", (json.dumps(metadata), row[0]))
        conn.commit()
    finally:
        conn.close()

    report = audit_event(home, event_id)
    assert report["source_integrity"]["invalid_refs"] >= 1
    assert "SOURCE_REF_INTEGRITY_INCOMPLETE" in report["warnings"]
    assert "src_missing_private" not in json.dumps(report)


def test_query_role_mismatch_is_reported(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        query_rows = conn.execute(
            "SELECT payload FROM packets WHERE event_id=? AND kind='QueryPacket'",
            (event_id,),
        ).fetchall()
        query_ids = {
            payload["target_role"]: payload["packet_id"]
            for (raw,) in query_rows
            for payload in [json.loads(raw)]
        }
        offer_rows = conn.execute(
            "SELECT id,payload FROM packets WHERE event_id=? AND kind='OfferPacket'",
            (event_id,),
        ).fetchall()
        for row_id, raw in offer_rows:
            payload = json.loads(raw)
            if payload["role"] == "B1_DETAIL":
                payload["query_packet_id"] = query_ids["B2_GIST"]
                conn.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(payload), row_id))
        conn.commit()
    finally:
        conn.close()

    report = audit_event(home, event_id)
    assert report["bodies"]["query_binding_status"] == "PARTIAL"
    assert any(
        item["role"] == "B1_DETAIL" and item["query_role_match"] is False
        for item in report["bodies"]["offers"]
    )


def test_compressed_source_blob_is_verified_streamingly(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        sha = conn.execute("SELECT hash FROM sources ORDER BY id LIMIT 1").fetchone()[0]
    finally:
        conn.close()
    blob = home / "data" / "blobs" / sha
    raw = blob.read_bytes()
    blob.with_name(sha + ".z").write_bytes(zlib.compress(raw))
    blob.unlink()

    report = audit_event(home, event_id)
    assert report["source_integrity"]["invalid_refs"] == 0
    assert report["source_integrity"]["valid_refs"] >= 2
