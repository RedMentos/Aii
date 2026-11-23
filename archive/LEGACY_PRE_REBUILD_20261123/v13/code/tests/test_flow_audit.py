import json
import os
import sqlite3
import zlib

from v13.contracts import packet
from v13.flow_audit import audit_event, audit_latest, audit_latest_completed, main
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


def _session_id(home, event_id):
    conn = sqlite3.connect(home / "data" / "db" / "brain.sqlite3")
    try:
        row = conn.execute("SELECT session_id FROM events WHERE id=?", (event_id,)).fetchone()
        if not row:
            raise AssertionError("fixture event missing")
        return row[0]
    finally:
        conn.close()


def test_full_b1_b2_c4_c3_path_is_reported_without_private_text(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    report = audit_event(home, event_id, session_id=_session_id(home, event_id))

    assert report["read_only"] is True
    assert report["private_text_returned"] is False
    assert report["bodies"]["roles"] == ["B1_DETAIL", "B2_GIST"]
    assert report["bodies"]["query_binding_status"] == "PASS"
    assert all(x["query_role_match"] is True for x in report["bodies"]["offers"])
    assert all(x["prompt_token_source"] == "NATIVE_TOKENIZE_RECEIPT" for x in report["bodies"]["offers"])
    assert all(x["evidence_level"] == "SYNTHETIC_FIXTURE" for x in report["bodies"]["offers"])
    assert report["c4"]["status"] == "PASS"
    assert report["c4"]["consumed_roles"] == ["B1_DETAIL", "B2_GIST"]
    assert report["c3"]["context_binding_status"] == "PASS"
    assert report["c3"]["status"] == "CONTEXT_PRESENT_SEMANTIC_USE_UNVERIFIED"
    assert report["c3"]["semantic_use_status"] == "UNVERIFIED"
    assert report["c3"]["source_bound_roles"] == ["B1_DETAIL", "B2_GIST"]
    assert "C3_SEMANTIC_USE_UNVERIFIED" in report["warnings"]
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
    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["c4"]["status"] == "FAIL"
    assert report["c3"]["status"] == "FAIL"
    assert "B1_B2_NOT_BOTH_CONSUMED_BY_C4" in report["warnings"]
    assert "B1_B2_NOT_BOTH_SOURCE_BOUND_IN_C3_CONTEXT" in report["warnings"]


def test_audit_latest_and_read_only_database(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        session_id = conn.execute(
            "SELECT session_id FROM events WHERE id=?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    before = db.read_bytes()
    report = audit_latest(home, session_id=session_id)
    after = db.read_bytes()
    assert report["event_id"] == event_id
    assert before == after


def test_audit_reads_live_store_while_runtime_lock_is_held(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        session = store.new_session("live Store fixture")
        event = store.event(session, "LIVE_PRIVATE_USER_TEXT_SENTINEL")
        store.message(
            session, event["event_id"], "assistant", "LIVE_PRIVATE_ASSISTANT_SENTINEL",
            status="FINAL", metadata={"runner": {"role": "C3_LANGUAGE", "status": "FINAL"}},
        )

        # Store still owns its coordinator lock and keeps the WAL connection open.
        # The audit must read the persisted turn without constructing another Store.
        report = audit_event(home, event["event_id"], session_id=session)
        assert report["event_id"] == event["event_id"]
        assert report["assistant_status"] == "FINAL"
        assert report["read_only"] is True
        assert report["private_text_returned"] is False
        assert "LIVE_PRIVATE_USER_TEXT_SENTINEL" not in json.dumps(report)
        assert "LIVE_PRIVATE_ASSISTANT_SENTINEL" not in json.dumps(report)
        assert store.one("SELECT id FROM events WHERE id=?", (event["event_id"],)) is not None
    finally:
        store.close()


def test_missing_event_fails_closed(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    try:
        audit_event(home, "evt_missing", session_id=_session_id(home, event_id))
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

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
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

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
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

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["source_integrity"]["invalid_refs"] == 0
    assert report["source_integrity"]["valid_refs"] >= 2


def test_session_scoped_latest_and_cross_session_rejection(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        session_id = conn.execute(
            "SELECT session_id FROM events WHERE id=?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    store = Store(home)
    try:
        other_session = store.new_session("other chat")
        other_event = store.event(other_session, "OTHER_PRIVATE_TEXT_SENTINEL")
    finally:
        store.close()

    before = db.read_bytes()
    report = audit_latest(home, session_id=session_id)
    assert report["event_id"] == event_id
    assert "OTHER_PRIVATE_TEXT_SENTINEL" not in json.dumps(report)
    try:
        audit_event(home, other_event["event_id"], session_id=session_id)
    except KeyError:
        pass
    else:
        raise AssertionError("cross-session event must be hidden")
    assert db.read_bytes() == before


def test_session_scoped_cli_accepts_session_id(tmp_path, capsys):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        session_id = conn.execute(
            "SELECT session_id FROM events WHERE id=?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    assert main(["--home", str(home), "--session-id", session_id, "--compact"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["event_id"] == event_id
    assert report["private_text_returned"] is False



def test_c4_requires_focal_item_to_retain_offer_source_refs(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        event_packet = json.loads(
            conn.execute("SELECT packet FROM events WHERE id=?", (event_id,)).fetchone()[0]
        )
        focal_rows = conn.execute(
            "SELECT id,payload FROM packets WHERE event_id=? AND kind='FocalItem'",
            (event_id,),
        ).fetchall()
        for row_id, raw in focal_rows:
            item = json.loads(raw)
            if item.get("source_kind") == "B1_DETAIL":
                item["source_refs"] = [event_packet["source_ref"]]
                conn.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(item), row_id))
        conn.commit()
    finally:
        conn.close()

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["c4"]["status"] == "PARTIAL"
    assert report["c4"]["consumed_roles"] == ["B2_GIST"]
    assert report["c3"]["context_binding_status"] == "PARTIAL"
    assert report["c3"]["status"] == "PARTIAL_CONTEXT"



def test_c4_rejects_focal_item_with_wrong_source_role(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        focal_rows = conn.execute(
            "SELECT id,payload FROM packets WHERE event_id=? AND kind='FocalItem'",
            (event_id,),
        ).fetchall()
        for row_id, raw in focal_rows:
            item = json.loads(raw)
            if item.get("source_kind") == "B1_DETAIL":
                item["source_kind"] = "B2_GIST"
                conn.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(item), row_id))
        conn.commit()
    finally:
        conn.close()

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["c4"]["status"] == "PARTIAL"
    assert report["c4"]["consumed_roles"] == ["B2_GIST"]
    assert report["c3"]["context_binding_status"] == "PARTIAL"


def test_c4_rejects_non_active_focal_item(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        focal_rows = conn.execute(
            "SELECT id,payload FROM packets WHERE event_id=? AND kind='FocalItem'",
            (event_id,),
        ).fetchall()
        for row_id, raw in focal_rows:
            item = json.loads(raw)
            if item.get("source_kind") == "B1_DETAIL":
                item["state_type"] = "REACTIVATABLE"
                conn.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(item), row_id))
        conn.commit()
    finally:
        conn.close()

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["c4"]["status"] == "PARTIAL"
    assert report["c4"]["consumed_roles"] == ["B2_GIST"]


def test_c4_uses_only_the_latest_focal_cycle(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        event_packet = json.loads(
            conn.execute("SELECT packet FROM events WHERE id=?", (event_id,)).fetchone()[0]
        )
        offers = [
            json.loads(raw)
            for (raw,) in conn.execute(
                "SELECT payload FROM packets WHERE event_id=? AND kind='OfferPacket' ORDER BY created,id",
                (event_id,),
            ).fetchall()
        ]
        b2_id = next(item["packet_id"] for item in offers if item.get("role") == "B2_GIST")
    finally:
        conn.close()

    store = Store(home)
    try:
        store.add_packet(
            "FocalCycle",
            packet(
                "FocalCycle", "C4_FOCAL", event_id, event_packet["brain_generation_id"],
                [event_packet["source_ref"]], cycle=1, decision="INCORPORATE_B",
                coalition=[b2_id], signals={}, budget={},
            ),
        )
    finally:
        store.close()

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["c4"]["status"] == "PARTIAL"
    assert report["c4"]["consumed_roles"] == ["B2_GIST"]


def test_source_blob_symlink_is_rejected_without_following(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        sha = conn.execute("SELECT hash FROM sources ORDER BY id LIMIT 1").fetchone()[0]
    finally:
        conn.close()

    blob = home / "data" / "blobs" / sha
    original = blob.read_bytes()
    external = tmp_path / "outside-source.txt"
    external.write_bytes(original)
    blob.unlink()
    blob.symlink_to(external)

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["source_integrity"]["invalid_refs"] >= 1
    assert report["source_integrity"]["valid_refs"] >= 1
    assert "outside-source" not in json.dumps(report)


def test_source_blob_non_regular_entry_is_rejected(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        sha = conn.execute("SELECT hash FROM sources ORDER BY id LIMIT 1").fetchone()[0]
    finally:
        conn.close()

    blob = home / "data" / "blobs" / sha
    blob.unlink()
    blob.mkdir()

    report = audit_event(home, event_id, session_id=_session_id(home, event_id))
    assert report["source_integrity"]["invalid_refs"] >= 1


def test_explicit_event_selector_is_unscoped_but_sanitized(tmp_path, capsys):
    home = tmp_path / "runtime"
    first_event = _fixture(home)
    first_session = _session_id(home, first_event)

    store = Store(home)
    try:
        other_session = store.new_session("other chat")
        other_event = store.event(other_session, "OTHER_PRIVATE_TEXT_SENTINEL")
    finally:
        store.close()

    # An explicit event ID is a deliberate local selector and may select any
    # session. The report must still contain metadata only, never source/chat text.
    report = audit_event(home, other_event["event_id"])
    assert report["event_id"] == other_event["event_id"]
    assert report["read_only"] is True
    assert report["private_text_returned"] is False
    rendered = json.dumps(report)
    for private_value in (
        "OTHER_PRIVATE_TEXT_SENTINEL",
        "PRIVATE_USER_TEXT_SENTINEL",
        "PRIVATE_BODY_EVIDENCE_SENTINEL",
        "PRIVATE_OFFER_TEXT_SENTINEL",
        "PRIVATE_ASSISTANT_TEXT_SENTINEL",
    ):
        assert private_value not in rendered

    # Supplying a session ID opts into strict session binding.
    try:
        audit_event(home, other_event["event_id"], session_id=first_session)
    except KeyError:
        pass
    else:
        raise AssertionError("explicit event with a wrong supplied session must be hidden")

    assert main([
        "--home", str(home), "--event-id", other_event["event_id"], "--compact",
    ]) == 0
    cli_report = json.loads(capsys.readouterr().out)
    assert cli_report["event_id"] == other_event["event_id"]
    assert "OTHER_PRIVATE_TEXT_SENTINEL" not in json.dumps(cli_report)

    assert main([
        "--home", str(home), "--event-id", other_event["event_id"],
        "--session-id", first_session, "--compact",
    ]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error"] == "KeyError"


def test_readonly_audit_rejects_symlinked_database(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    real_db = db.with_name("brain.real.sqlite3")
    db.rename(real_db)
    db.symlink_to(real_db.name)
    try:
        audit_latest(home, session_id=_session_id(home, event_id))
    except PermissionError:
        pass
    else:
        raise AssertionError("symlinked Store database must be rejected")


def test_readonly_audit_rejects_hardlinked_database(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    alias = db.with_name("brain.alias.sqlite3")
    os.link(db, alias)
    try:
        audit_latest(home, session_id=_session_id(home, event_id))
    except PermissionError:
        pass
    else:
        raise AssertionError("hardlinked Store database must be rejected")
    finally:
        alias.unlink(missing_ok=True)


def test_readonly_audit_rejects_writable_data_ancestor(tmp_path):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    data_dir = home / "data"
    original_mode = data_dir.stat().st_mode & 0o7777
    os.chmod(data_dir, original_mode | 0o002)
    try:
        audit_latest(home, session_id=_session_id(home, event_id))
    except PermissionError:
        pass
    else:
        raise AssertionError("world-writable Store ancestor must be rejected")
    finally:
        os.chmod(data_dir, original_mode)


def test_latest_event_audit_requires_explicit_session_with_multiple_chats(tmp_path, capsys):
    home = tmp_path / "runtime"
    event_id = _fixture(home)
    db = home / "data" / "db" / "brain.sqlite3"
    conn = sqlite3.connect(db)
    try:
        session_id = conn.execute(
            "SELECT session_id FROM events WHERE id=?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    store = Store(home)
    try:
        other_session = store.new_session("other chat")
        store.event(other_session, "OTHER_PRIVATE_TEXT_SENTINEL")
    finally:
        store.close()

    try:
        audit_latest(home)
    except ValueError as exc:
        assert "session_id" in str(exc)
    else:
        raise AssertionError("latest-event audit must not choose across chat sessions")

    assert main(["--home", str(home), "--compact"]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error"] == "ValueError"
    assert main(["--home", str(home), "--session-id", session_id, "--compact"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["event_id"] == event_id
    assert "OTHER_PRIVATE_TEXT_SENTINEL" not in json.dumps(report)


def test_latest_completed_audit_ignores_newer_pending_event_across_sessions(tmp_path):
    home = tmp_path / "runtime"
    completed_event_id = _fixture(home)
    store = Store(home)
    try:
        pending_session = store.new_session("new active chat without an answer")
        store.event(pending_session, "PENDING_PRIVATE_TEXT_SENTINEL")
    finally:
        store.close()

    db = home / "data" / "db" / "brain.sqlite3"
    before = db.read_bytes()
    report = audit_latest_completed(home)
    after = db.read_bytes()

    assert report is not None
    assert report["event_id"] == completed_event_id
    assert report["assistant_status"] == "FINAL"
    assert report["read_only"] is True
    assert report["private_text_returned"] is False
    assert "PENDING_PRIVATE_TEXT_SENTINEL" not in json.dumps(report)
    assert before == after


def test_latest_completed_audit_returns_none_without_assistant_turn(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        session = store.new_session("pending only")
        store.event(session, "PENDING_ONLY_PRIVATE_TEXT")
    finally:
        store.close()
    assert audit_latest_completed(home) is None


def test_unsafe_model_path_and_non_enum_status_are_not_returned():
    from v13.flow_audit import _safe_metrics

    safe = _safe_metrics({
        "role": "B1_DETAIL", "status": "FINAL", "actual_model": "LFM2.5-1.2B",
        "prompt_tokens": 12, "generated_tokens": 3,
    })
    assert safe["actual_model"] == "LFM2.5-1.2B"
    unsafe = _safe_metrics({
        "role": "B1_DETAIL", "status": "PRIVATE_ERROR /home/user/model.gguf",
        "actual_model": "/data/data/com.termux/files/home/models/private.gguf",
    })
    assert "actual_model" not in unsafe
    assert "status" not in unsafe
