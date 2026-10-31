"""Run117AG adversarial mutation tests on immutable original native ZIP.

Requires exact original ZIP from GitHub Actions. No native model execution.
"""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import zipfile

from scripts.run117ag_independent_native_audit import audit

ORIGINAL = Path(os.environ.get(
    "V13_RUN117AF_ORIGINAL_ZIP", "/mnt/data/run117af-original-native.zip"))
SHA = "1082b64fe8d5a8ed3f8026c5913e9712f51217f75d5544b762924016f9bfc888"


def mutate_zip(data, modify):
    with zipfile.ZipFile(BytesIO(data)) as z:
        files = {name:z.read(name) for name in z.namelist()}
    report = json.loads(files["NATIVE_CASE/report.json"])
    modify(report)
    files["NATIVE_CASE/report.json"] = (
        json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode()
    files["SHA256SUMS"] = "".join(
        sha256(content).hexdigest()+"  ./"+name+"\n"
        for name,content in sorted(files.items()) if name!="SHA256SUMS"
    ).encode()
    out=BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():
            z.writestr(name,content)
    return out.getvalue()


class OriginalNativeMutation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=ORIGINAL.read_bytes()
        assert sha256(cls.raw).hexdigest()==SHA

    def test_original_passes(self):
        self.assertEqual(
            audit(self.raw,expected_sha=SHA)["status"],
            "INDEPENDENT_ORIGINAL_NATIVE_STRUCTURAL_PASS")

    def test_forged_score_rejected_after_outer_rehash(self):
        def mutate(report):
            item=report["rows"][0]["arms"][0]
            item["score"]["correct"]=1-item["score"]["correct"]
        tampered=mutate_zip(self.raw,mutate)
        with self.assertRaisesRegex(ValueError,"NATIVE_SCORE_FORGERY_RED"):
            audit(tampered,expected_sha=None)

    def test_forged_body_truth_rejected_after_outer_rehash(self):
        def mutate(report):
            item=next(a for a in report["rows"][0]["arms"]
                      if a["arm"]=="B1B2_JEF_CONTEXTOS")
            payload=json.loads(item["messages"][1]["content"])
            payload["body_hypotheses_are_facts"]=True
            item["messages"][1]["content"]=json.dumps(
                payload,sort_keys=True,separators=(",",":"))
            item["messages_sha256"]=sha256(json.dumps(
                item["messages"],sort_keys=True,
                separators=(",",":")).encode()).hexdigest()
        tampered=mutate_zip(self.raw,mutate)
        with self.assertRaisesRegex(ValueError,"COMBINED_BODY_BOUNDARY_RED"):
            audit(tampered,expected_sha=None)

    def test_forged_source_ref_rejected_after_outer_rehash(self):
        def mutate(report):
            item=report["rows"][0]["arms"][0]
            payload=json.loads(item["messages"][1]["content"])
            payload["policy"]["source_ref"]["sha256"]="0"*64
            item["messages"][1]["content"]=json.dumps(
                payload,sort_keys=True,separators=(",",":"))
            item["messages_sha256"]=sha256(json.dumps(
                item["messages"],sort_keys=True,
                separators=(",",":")).encode()).hexdigest()
        tampered=mutate_zip(self.raw,mutate)
        with self.assertRaisesRegex(ValueError,"SOURCE_REF_RED"):
            audit(tampered,expected_sha=None)


if __name__=="__main__":
    unittest.main()
