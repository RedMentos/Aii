"""Run97: JEF-to-Body ACTIVE cache requires intact source and parent lineage.

Real Runtime/SQLite packet/source mutations. Explicit human ACTIVE is set only
inside tests. No native models, no Age promotion, no fact/learning authority.
"""
import json

from tests.test_jefbridge import Base


class JEFCacheLineageRun97(Base):
    def prepare(self):
        event = self.event("Compare 08:15 and 09:40")
        broadcast = self.broadcast(event)
        cache = self.j.broadcast_cache(event, broadcast, body={"pressure": "NORMAL"})
        self.j._mutate(
            lambda st: st["fields"].__setitem__(
                "B1_DETAIL|body_state",
                {"with": [4., 5], "without": [1., 5]},
            )
        )
        self.j.set_mode("ACTIVE", "EXPLICIT_HUMAN")
        self.assertIn("body_state", self.j.bridge_view("B1_DETAIL", event, 1)[1])
        return event, broadcast, cache

    def corrupt(self, packet_id, mutate):
        row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (packet_id,))
        data = json.loads(row["payload"])
        mutate(data)
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload=? WHERE id=?",
                      (json.dumps(data), packet_id))

    def test_deleted_original_source_blocks_active_jef_body_fields(self):
        event, _, _ = self.prepare()
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (event["source_ref"]["source_id"],))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_missing_parent_broadcast_blocks_active_bridge(self):
        event, broadcast, _ = self.prepare()
        with self.r.store.tx() as c:
            c.execute("DELETE FROM packets WHERE id=?", (broadcast["packet_id"],))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_forged_generation_inside_cache_payload_is_rejected(self):
        event, _, cache = self.prepare()
        self.corrupt(cache["packet_id"],
                     lambda p: p.__setitem__("brain_generation_id", "foreign"))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_forged_source_hash_inside_cache_provenance_is_rejected(self):
        event, _, cache = self.prepare()
        self.corrupt(cache["packet_id"],
                     lambda p: p["provenance"][0].__setitem__("sha256", "0" * 64))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_parent_state_version_mismatch_is_rejected(self):
        event, broadcast, _ = self.prepare()
        self.corrupt(broadcast["packet_id"],
                     lambda p: p.__setitem__("state_version", 2))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_tampered_original_blob_digest_blocks_active_bridge(self):
        event, _, _ = self.prepare()
        blob = self.r.store.home / "data/blobs" / event["source_ref"]["sha256"]
        blob.write_bytes(b"tampered after capture")
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))

    def test_non_body_role_cannot_receive_active_extra_fields(self):
        event, _, _ = self.prepare()
        self.j._mutate(
            lambda st: st["fields"].__setitem__(
                "C3_LANGUAGE|body_state",
                {"with": [4., 5], "without": [1., 5]},
            )
        )
        self.assertEqual(self.j.bridge_view("C3_LANGUAGE", event, 1), ({}, []))

    def test_malformed_cache_json_fails_closed_not_exception(self):
        event, _, cache = self.prepare()
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload='{' WHERE id=?",
                      (cache["packet_id"],))
        self.assertEqual(self.j.bridge_view("B1_DETAIL", event, 1), ({}, []))


if __name__ == "__main__":
    import unittest
    unittest.main()
