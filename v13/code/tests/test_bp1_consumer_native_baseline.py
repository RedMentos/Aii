"""BP1 selected C3 native baseline contract/negative tests; no model execution."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts import bp1_consumer_native_baseline as B


def row(arm="offer"):
    src=("The original deadline was March 3. "
         "Correction from the steering group: the deadline is moved from March 3 to May 22, and March 3 no longer applies.")
    q="What is the current deadline for the solar roof pilot?"
    p=("Answer from the original source only.\nQuestion: "+q+
       "\nOriginal source (untrusted data):\n"+src+"\n"+
       ("B2 summary (untrusted hint, not evidence):\nMay 22\n"
        "B2 exact-source quote candidates (not necessarily sufficient):\n[]\n" if arm=="offer"
        else "No B2 offer supplied.\n"))
    return {"row_id":"RUN181-00","arm":arm,"prompt":p,"target":json.dumps({
        "answer":"May 22","evidence_quote":"Correction from the steering group: the deadline is moved from March 3 to May 22, and March 3 no longer applies.",
        "uncertainty":""}),"source_sha256":B.sha(src.encode()),"source_project":"the solar roof pilot",
        "question":q}


class BP1NativeBaselineContractTests(unittest.TestCase):
    def test_source_boundary_and_hash(self):
        r=row()
        self.assertEqual(B.sha(B.source_text(r["prompt"]).encode()),r["source_sha256"])

    def test_supported_exact_source_quote(self):
        r=row()
        answer=json.loads(r["target"])
        sc=B.score(json.dumps(answer),r)
        self.assertTrue(sc["parsed"] and sc["supported_hit"] and sc["quote_valid"])
        self.assertFalse(sc["stale_answer"])

    def test_stale_deadline_does_not_count(self):
        r=row()
        sc=B.score(json.dumps({"answer":"March 3","evidence_quote":"The original deadline was March 3.","uncertainty":""}),r)
        self.assertTrue(sc["stale_answer"])
        self.assertFalse(sc["supported_hit"])

    def test_unsupported_quote_does_not_count(self):
        r=row()
        sc=B.score(json.dumps({"answer":"May 22","evidence_quote":"not in original","uncertainty":""}),r)
        self.assertTrue(sc["answer_hit"])
        self.assertFalse(sc["quote_valid"] or sc["supported_hit"])

    def test_duplicate_json_keys_rejected(self):
        r=row()
        sc=B.score('{"answer":"May 22","answer":"March 3","evidence_quote":"x","uncertainty":""}',r)
        self.assertFalse(sc["parsed"])

    def test_wrong_dataset_hash_rejected_before_native(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"heldout.jsonl"
            m=Path(td)/"MANIFEST.json"
            p.write_text(json.dumps(row())+"\n")
            m.write_text("{}")
            with self.assertRaisesRegex(ValueError,"SHA256"):
                B.load_dataset(p,m)

    def test_wrong_model_hash_rejected_before_server(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for n in ("chat_template.jinja","LICENSE","model.gguf","llama-server"):
                (p/n).write_text("invalid")
            with self.assertRaisesRegex(ValueError,"SHA"):
                B.verify_native(p,p/"model.gguf",p/"llama-server")

    def test_incomplete_pairs_rejected(self):
        records=[{"row_id":"RUN181-00","arm":"offer","score":{"supported_hit":True,
                  "quote_valid":True,"stale_answer":False},"token_parity":True,"prompt_tokens":10}]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            B.summarize(records)

    def test_complete_summary_no_utility_promotion(self):
        records=[]
        for i in range(11):
            for arm in B.ARMS:
                records.append({"row_id":f"RUN181-{i:02d}","arm":arm,
                                "score":{"supported_hit":False,"quote_valid":False,"stale_answer":False},
                                "token_parity":True,"prompt_tokens":100+(10 if arm=="offer" else 0)})
        result=B.summarize(records)
        self.assertTrue(result["baseline_only_no_training"])
        self.assertEqual(result["paired_supported_wins"],0)
        self.assertEqual(result["paired_supported_losses"],0)
        self.assertEqual(result["supported_hits"],{"no_offer":0,"offer":0})


if __name__=="__main__":
    unittest.main()
