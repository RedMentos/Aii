"""BP1 prospective dataset: synthetic unit tests, no C3 optimizer or native inference."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import bp1_consumer_dataset as D
from scripts import gist_utility_bench as G


def fake():
    rows=G.make()
    report={"gist":[]}
    for index,row in enumerate(rows):
        report["gist"].append({"index":index,"kind":row["kind"],
            "content":json.dumps({"summary":"B2 untrusted synthetic suggestion",
                                  "quotes":[D.source_quote(row),"invented source quotation"]})})
    return report,rows


class BP1ConsumerDatasetTests(unittest.TestCase):
    def test_source_disjoint_training_and_paired_holdout(self):
        report,rows=fake()
        train,heldout,diag=D.make_dataset(report,rows)
        self.assertEqual(len(train)+len(heldout)//2,36)
        self.assertEqual(len(diag),36)
        self.assertEqual(sum(d["b2_quotes_dropped"] for d in diag),36)
        self.assertFalse({r["source_project"] for r in train}&{r["source_project"] for r in heldout})
        self.assertEqual({r["arm"] for r in train},{"offer"})
        self.assertEqual({r["arm"] for r in heldout},set(D.ARMS))
        self.assertTrue(all("invented source quotation" not in r["prompt"] for r in train+heldout))
        for r in train+heldout:
            src=rows[int(r["row_id"].split("-")[1])]["text"]
            target=json.loads(r["target"])
            self.assertIn(target["evidence_quote"],src)
            self.assertTrue(D.exact(target["evidence_quote"],target["answer"]))
            self.assertEqual(D.sha(src.encode()),r["source_sha256"])

    def test_no_offer_arm_has_no_b2_summary(self):
        report,rows=fake()
        _,heldout,_=D.make_dataset(report,rows)
        for row in heldout:
            if row["arm"]=="no_offer":
                self.assertIn("No B2 offer supplied",row["prompt"])
                self.assertNotIn("B2 untrusted synthetic suggestion",row["prompt"])
            else:
                self.assertIn("B2 untrusted synthetic suggestion",row["prompt"])

    def test_duplicate_json_keys_fail_closed(self):
        report,rows=fake()
        report["gist"][0]["content"]='{"summary":"a","summary":"b","quotes":[]}'
        with self.assertRaises(ValueError):
            D.make_dataset(report,rows)

    def test_missing_source_key_fails_closed(self):
        report,rows=fake()
        rows[0]=dict(rows[0],key="IMPOSSIBLE_NEW_VALUE")
        with self.assertRaises(ValueError):
            D.make_dataset(report,rows)

    def test_wrong_native_report_hash_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.json"
            p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"SHA256"):
                D.verified_input(p)

    def test_duplicate_row_index_rejected(self):
        report,rows=fake()
        report["gist"][0]["index"]=1
        with self.assertRaises(ValueError):
            D.make_dataset(report,rows)

    def test_split_overlap_rejected(self):
        report,rows=fake()
        with patch.object(D,"HELDOUT_PROJECTS",D.TRAIN_PROJECTS):
            with self.assertRaises(ValueError):
                D.make_dataset(report,rows)

    def test_exclusive_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"train.jsonl"
            D.exclusive(p,b"original")
            with self.assertRaises(FileExistsError):
                D.exclusive(p,b"replacement")
            self.assertEqual(p.read_bytes(),b"original")


if __name__=="__main__":
    unittest.main()
