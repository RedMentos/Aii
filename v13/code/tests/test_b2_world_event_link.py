"""Run73 source-bound B2 ↔ World read-only digital event integration tests."""
import copy
import hashlib
import json
import sqlite3
import unittest
from unittest import mock

from v13 import b2_world_event_link as link


class Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE events(id TEXT PRIMARY KEY,session_id TEXT,generation_id TEXT,
                                source_id TEXT,packet TEXT,created REAL);
            CREATE TABLE packets(id TEXT PRIMARY KEY,kind TEXT,event_id TEXT,
                                 generation_id TEXT,payload TEXT,created REAL);
            CREATE TABLE actions(id TEXT PRIMARY KEY,event_id TEXT,status TEXT,
                                 outcome TEXT,expected TEXT,kind TEXT,corollary_id TEXT);
            CREATE TABLE messages(id TEXT PRIMARY KEY,event_id TEXT,role TEXT,status TEXT,text TEXT);
            CREATE TABLE sources(id TEXT PRIMARY KEY,hash TEXT,deleted INTEGER);
        """)
        self.texts = {}
        self.queries = []
        self.reads = []

    def one(self, sql, args=()):
        return next(iter(self.rows(sql, args)), None)

    def rows(self, sql, args=()):
        self.queries.append(sql)
        assert sql.lstrip().upper().startswith("SELECT"), sql
        return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def source(self, ident, text):
        sha = hashlib.sha256(text.encode()).hexdigest()
        self.db.execute("INSERT INTO sources VALUES (?,?,0)", (ident, sha))
        self.texts[ident] = text
        return {"source_id": ident, "sha256": sha, "char_start": 0,
                "char_end": len(text), "modality": "text"}

    def read_source(self, ref):
        self.reads.append(ref["source_id"])
        row = self.db.execute("SELECT hash,deleted FROM sources WHERE id=?",
                              (ref["source_id"],)).fetchone()
        if (row is None or row["deleted"] or row["hash"] != ref["sha256"]):
            raise ValueError("source revoked")
        text = self.texts[ref["source_id"]]
        if hashlib.sha256(text.encode()).hexdigest() != row["hash"]:
            raise ValueError("source tampered")
        if not 0 <= ref["char_start"] <= ref["char_end"] <= len(text):
            raise ValueError("invalid span")
        return text[ref["char_start"]:ref["char_end"]]

    def put(self, table, values):
        n = {"events": 6, "packets": 6, "actions": 7, "messages": 5}[table]
        self.db.execute("INSERT INTO "+table+" VALUES ("+",".join("?" for _ in range(n))+")",
                        values)

    def packet(self, packet_id, kind, payload, created):
        self.put("packets", (packet_id, kind, "evt1", "gen1",
                             json.dumps(payload), created))


def fixture():
    s = Store()
    src = s.source("src1", "Project Aquila: decide using earlier rules.")
    out = s.source("out1", "Selected option A with no external tool.")
    env = {"event_id": "evt1", "brain_generation_id": "gen1",
           "source_ref": src, "authority": "AUTHORITATIVE"}
    s.put("events", ("evt1", "session1", "gen1", "src1", json.dumps(env), 1.))
    offer = {"packet_id": "b2p1", "event_id": "evt1",
             "brain_generation_id": "gen1", "role": "B2_GIST",
             "model_revision": "b2-rev1", "provenance": [src],
             "offer": {"summary": "UNTRUSTED_HYPOTHESIS"}}
    s.packet("b2p1", "OfferPacket", offer, 2.)
    expected = {"forecast": {"profile": {"role": "C3_LANGUAGE"}}}
    actual = {"role": "C3_LANGUAGE",
              "self_candidate_hash": hashlib.sha256(s.texts["out1"].encode()).hexdigest()}
    s.put("actions", ("act1", "evt1", "FINAL", json.dumps(actual),
                      json.dumps(expected), "local_answer", "cor1"))
    s.put("messages", ("msg1", "evt1", "assistant", "FINAL", s.texts["out1"]))
    intent = {"packet_id": "intent1", "event_id": "evt1",
              "brain_generation_id": "gen1", "action_id": "act1",
              "permission": "local_text_only", "action_type": "local_answer"}
    s.packet("intent1", "ActionIntent", intent, 2.5)
    corollary = {"packet_id": "cor1", "event_id": "evt1",
                 "brain_generation_id": "gen1", "action_id": "act1",
                 "self_caused": True, "expected": expected}
    s.packet("cor1", "CorollaryCopy", corollary, 3.)
    world = {"packet_id": "world1", "event_id": "evt1",
             "brain_generation_id": "gen1", "source_ref": src,
             "outcome_source_ref": out, "provenance": [src, out],
             "action_id": "act1", "action_role": "C3_LANGUAGE",
             "corollary_packet_id": "cor1", "teacher_truth_authority": False,
             "external_world_observation": False, "semantic_success": None}
    s.packet("world1", "WorldTransition", world, 4.)
    s.db.commit()
    return s


def check(s):
    return link.link(s, "evt1", "session1", "gen1", "b2-rev1")


class Run73SourceBoundDigitalLink(unittest.TestCase):
    def setUp(self):
        self.s = fixture()
        self.addCleanup(self.s.db.close)

    def assert_abstain(self, result):
        self.assertTrue(result["status"].startswith("ABSTAIN_"), result)
        self.assertEqual(result["authority"], "SHADOW_NO_AUTHORITY")
        self.assertIsNone(result["action_id"])
        self.assertFalse(result["semantic_coupling_proven"])
        self.assertFalse(result["b2_hypothesis_is_truth"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(result["jepa_weight"], 0)

    def edit(self, kind, packet_id, mutate):
        row = self.s.one("SELECT payload FROM packets WHERE id=?", (packet_id,))
        obj = json.loads(row["payload"])
        mutate(obj)
        self.s.db.execute("UPDATE packets SET payload=? WHERE id=?",
                          (json.dumps(obj), packet_id))

    def test_valid_same_event_link_is_readonly_and_non_authoritative(self):
        before = self.s.db.total_changes
        result = check(self.s)
        self.assertEqual(result["status"], "SHADOW_SOURCE_BOUND_DIGITAL_LINK")
        self.assertEqual(result["b2_offer_packet_id"], "b2p1")
        self.assertEqual(result["world_transition_packet_id"], "world1")
        self.assertEqual(result["action_id"], "act1")
        self.assertEqual(result["action_role"], "C3_LANGUAGE")
        self.assertEqual(result["source_ref"]["source_id"], "src1")
        self.assertEqual(result["outcome_source_ref"]["source_id"], "out1")
        self.assertFalse(result["semantic_coupling_proven"])
        self.assertFalse(result["native_executed"])
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(self.s.db.total_changes, before)
        self.assertTrue(self.s.queries)
        self.assertTrue(all(q.lstrip().upper().startswith("SELECT") for q in self.s.queries))
        self.assertGreaterEqual(self.s.reads.count("src1"), 2)
        self.assertGreaterEqual(self.s.reads.count("out1"), 2)

    def test_b1_and_b2_offers_coexist_on_normal_two_body_turn(self):
        original = self.s.one("SELECT payload FROM packets WHERE id='b2p1'")
        src = json.loads(original["payload"])["provenance"][0]
        b1 = {"packet_id": "b1p1", "event_id": "evt1",
              "brain_generation_id": "gen1", "role": "B1_DETAIL",
              "model_revision": "b1-rev1", "provenance": [src],
              "offer": {"summary": "separate detail hypothesis"}}
        self.s.packet("b1p1", "OfferPacket", b1, 2.1)
        result = check(self.s)
        self.assertEqual(result["status"], "SHADOW_SOURCE_BOUND_DIGITAL_LINK")
        self.assertEqual(result["b2_offer_packet_id"], "b2p1")
        self.assertEqual(result["authority"], "SHADOW_NO_AUTHORITY")
        self.assertFalse(result["semantic_coupling_proven"])

    def test_wrong_session_generation_model_abstain(self):
        for args in (("wrong", "gen1", "b2-rev1"),
                     ("session1", "wrong", "b2-rev1"),
                     ("session1", "gen1", "wrong")):
            with self.subTest(args=args):
                self.assert_abstain(link.link(self.s, "evt1", *args))

    def test_foreign_or_forged_b2_packet_abstains(self):
        for change in (lambda p: p.update(role="B1_DETAIL"),
                       lambda p: p.update(event_id="foreign"),
                       lambda p: p.update(provenance=[]),
                       lambda p: p.update(model_revision="other"),
                       lambda p: p.update(brain_generation_id="other")):
            with self.subTest(change=repr(change)):
                s = fixture()
                try:
                    row = s.one("SELECT payload FROM packets WHERE id='b2p1'")
                    p = json.loads(row["payload"]); change(p)
                    s.db.execute("UPDATE packets SET payload=? WHERE id='b2p1'",
                                 (json.dumps(p),))
                    self.assert_abstain(check(s))
                finally:
                    s.db.close()

    def test_event_source_and_authority_changes_abstain(self):
        for change in (lambda p: p.update(authority="MODEL"),
                       lambda p: p.update(source_ref={"source_id": "other"}),
                       lambda p: p.update(brain_generation_id="other")):
            s = fixture()
            try:
                row = s.one("SELECT packet FROM events WHERE id='evt1'")
                p = json.loads(row["packet"]); change(p)
                s.db.execute("UPDATE events SET packet=? WHERE id='evt1'",
                             (json.dumps(p),))
                self.assert_abstain(check(s))
            finally:
                s.db.close()

    def test_source_tombstone_and_tamper_abstain(self):
        for ident in ("src1", "out1"):
            for mode in ("tombstone", "tamper"):
                with self.subTest(ident=ident, mode=mode):
                    s = fixture()
                    try:
                        if mode == "tombstone":
                            s.db.execute("UPDATE sources SET deleted=1 WHERE id=?", (ident,))
                        else:
                            s.texts[ident] += " changed"
                        self.assert_abstain(check(s))
                    finally:
                        s.db.close()

    def test_nonfinal_action_and_outcome_mismatch_abstain(self):
        self.s.db.execute("UPDATE actions SET status='CANCELLED' WHERE id='act1'")
        self.assert_abstain(check(self.s))
        self.s.db.execute("UPDATE actions SET status='FINAL',outcome=? WHERE id='act1'",
                          (json.dumps({"role": "C3_LANGUAGE",
                                       "self_candidate_hash": "0"*64}),))
        self.assert_abstain(check(self.s))

    def test_corollary_or_intent_absent_or_forged_abstain(self):
        self.s.db.execute("DELETE FROM packets WHERE id='cor1'")
        self.assert_abstain(check(self.s))
        self.s.db.execute("ROLLBACK")
        self.s = fixture()
        self.s.db.execute("DELETE FROM packets WHERE id='intent1'")
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.edit("ActionIntent", "intent1", lambda p: p.update(permission="external"))
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.edit("CorollaryCopy", "cor1", lambda p: p.update(self_caused=False))
        self.assert_abstain(check(self.s))

    def test_forged_world_role_and_outcome_ref_abstain(self):
        self.edit("WorldTransition", "world1", lambda p: p.update(action_role="B1_DETAIL"))
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.edit("WorldTransition", "world1", lambda p: p.update(outcome_source_ref=p["source_ref"]))
        self.assert_abstain(check(self.s))

    def test_future_offer_and_multiple_packets_abstain(self):
        self.s.db.execute("UPDATE packets SET created=5 WHERE id='b2p1'")
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.s.packet("b2p2", "OfferPacket", json.loads(
            self.s.one("SELECT payload FROM packets WHERE id='b2p1'")["payload"]) |
            {"packet_id": "b2p2"}, 2.2)
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.s.packet("world2", "WorldTransition", json.loads(
            self.s.one("SELECT payload FROM packets WHERE id='world1'")["payload"]) |
            {"packet_id": "world2"}, 4.2)
        self.assert_abstain(check(self.s))

    def test_source_changed_between_selection_and_final_read_abstains(self):
        original = self.s.read_source
        calls = {"n": 0}
        def race(ref):
            text = original(ref)
            if ref["source_id"] == "src1":
                calls["n"] += 1
                if calls["n"] >= 2:
                    return "modified-after-selection"
            return text
        with mock.patch.object(self.s, "read_source", side_effect=race):
            self.assert_abstain(check(self.s))

    def test_invalid_scope_and_scan_limits_raise(self):
        for bad in (None, True, "", "x"*129):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    link.link(self.s, bad, "session1", "gen1", "b2-rev1")
        for limit in (0, True, 33, -1):
            with self.assertRaises(ValueError):
                link.link(self.s, "evt1", "session1", "gen1", "b2-rev1",
                          scan_limit=limit)

    def test_malformed_json_and_missing_final_message_abstain(self):
        self.s.db.execute("UPDATE packets SET payload='{bad' WHERE id='world1'")
        self.assert_abstain(check(self.s))
        self.s = fixture()
        self.s.db.execute("DELETE FROM messages WHERE id='msg1'")
        self.assert_abstain(check(self.s))


if __name__ == "__main__":
    unittest.main()
