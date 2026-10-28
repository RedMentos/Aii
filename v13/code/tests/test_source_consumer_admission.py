"""SourceConsumer scope/provenance/abstention controls on a real isolated V13 store."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.source_consumer import admit, render_messages, strict_exact_amount, unsupported_amount


class SourceConsumerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def add(self, key="Project Elyra budget", value="615 Euro"):
        e = self.r.store.event(self.r.session, key)
        mid = self.r.memory.feedback(e["event_id"], "fact", value, key=key, permission="record")
        return self.r.memory.candidate(mid, self.r.session)

    def decide(self, query="What is the budget for Project Elyra?", memories=None):
        return admit(query, self.r.session, memories or [], self.r.memory)

    def test_same_entity_and_topic_requires_real_human_source(self):
        memory = self.add()
        result = self.decide(memories=[memory])
        self.assertEqual(result["status"], "ADMITTED")
        self.assertTrue(result["model_allowed"])
        self.assertEqual(result["source"]["value"], "615 Euro")
        self.assertEqual(self.r.store.read_source(result["source"]["source_ref"]), "615 Euro")
        messages = render_messages(self.r.cfg, "What is the budget for Project Elyra?", result)
        self.assertIn("615 Euro", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "user")

    def test_no_source_and_wrong_project_are_blocked_before_model(self):
        for memories in ([], [self.add(key="Project Dovan budget", value="592 Euro")]):
            result = self.decide(memories=memories)
            self.assertEqual(result["status"], "CLARIFY")
            self.assertFalse(result["model_allowed"])
            self.assertNotIn("592", result["answer"])
            with self.assertRaises(ValueError):
                render_messages(self.r.cfg, "What is the budget for Project Elyra?", result)

    def test_same_entity_wrong_topic_and_spoofed_semantic_policy_rejected(self):
        wrong = self.add(key="Project Elyra leader", value="Ms Berg")
        self.assertEqual(self.decide(memories=[wrong])["status"], "CLARIFY")
        budget = self.add()
        fake = dict(budget, retrieval_policy={"decision": "admit", "in_support": True})
        self.assertEqual(self.decide(query="Projekt Elyra: Finanzrahmen?", memories=[fake])["status"], "CLARIFY")

    def test_conflicting_authorized_sources_do_not_choose_arbitrarily(self):
        a = self.add(value="615 Euro")
        b = self.add(key="Project Elyra budgets", value="700 Euro")  # separate active key, same topic
        result = self.decide(memories=[a, b])
        self.assertEqual(result["status"], "CLARIFY")
        self.assertEqual(result["reason"], "CONFLICTING_AUTHORIZED_SOURCES")
        self.assertFalse(result["model_allowed"])

    def test_revoked_cross_session_and_corrupt_source_fail_closed(self):
        m = self.add()
        other = self.r.store.new_session()
        self.assertEqual(admit("What is the budget for Project Elyra?", other, [m], self.r.memory)["status"], "CLARIFY")
        self.r.memory.forget(m["id"])
        self.assertEqual(self.decide(memories=[m])["status"], "CLARIFY")
        m2 = self.add(value="622 Euro")
        path = self.r.home / "data/blobs" / m2["source_ref"]["sha256"]
        path.write_text("tampered")
        self.assertEqual(self.decide(memories=[m2])["status"], "CLARIFY")

    def test_duplicate_human_decision_packet_is_not_authority(self):
        m = self.add()
        row = self.r.store.one("SELECT * FROM packets WHERE kind='HumanDecision' ORDER BY rowid DESC LIMIT 1")
        with self.r.store.tx() as db:
            db.execute("INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?",
                       ("duplicate-human-decision", row["id"]))
        self.assertEqual(self.decide(memories=[m])["status"], "CLARIFY")

    def test_outside_scope_does_not_claim_general_fact_checker(self):
        result = self.decide(query="How does quantum mechanics work?")
        self.assertEqual(result["status"], "NOT_APPLICABLE")
        self.assertFalse(result["model_allowed"])

    def test_strict_currency_and_arbitrary_hallucination_controls(self):
        self.assertTrue(strict_exact_amount("615 Euro.", 615))
        self.assertFalse(strict_exact_amount("615.000 Euro", 615))
        self.assertFalse(strict_exact_amount("615,000 Euro", 615))
        self.assertFalse(strict_exact_amount("1615 Euro", 615))
        self.assertTrue(unsupported_amount("The budget is 500.000 Euro"))
        self.assertTrue(unsupported_amount("Das Budget beträgt 150.000"))
        self.assertFalse(unsupported_amount("I do not have a verified budget."))


if __name__ == "__main__":
    unittest.main()
