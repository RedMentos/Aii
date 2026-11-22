"""Run117AT independent original native ZIP and adversarial tamper tests."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import warnings
import zipfile
from scripts.run117at_independent_original_native_c3_audit import (
    OUTER_SHA, audit_bytes, score,
)

def repack(original, edits=None, duplicate=None):
    with zipfile.ZipFile(BytesIO(original)) as z:
        members={p:z.read(p) for p in z.namelist()}
    members.update(edits or {})
    members["SHA256SUMS"]="".join(
        sha256(raw).hexdigest()+"  ./"+name+"\n"
        for name,raw in sorted(members.items()) if name!="SHA256SUMS"
    ).encode()
    out=BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in members.items():
            z.writestr(name,raw)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore",UserWarning)
                z.writestr(duplicate,members[duplicate])
    return out.getvalue()

def change_report(original,edit):
    with zipfile.ZipFile(BytesIO(original)) as z:
        report=json.loads(z.read("NATIVE_CASE/report.json"))
    edit(report)
    return repack(original,{"NATIVE_CASE/report.json":
        (json.dumps(report,sort_keys=True)+"\n").encode()})

class IndependentNativeC3Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=os.environ.get("RUN117AT_ORIGINAL")
        if not p or not Path(p).is_file():
            raise RuntimeError("RUN117AT_ORIGINAL_ZIP_REQUIRED")
        cls.raw=Path(p).read_bytes()

    def expect_red(self,raw,code):
        with self.assertRaisesRegex(ValueError,"RUN117AT_"+code+"_RED"):
            audit_bytes(raw,expected_outer=sha256(raw).hexdigest())

    def test_original_twelve_native_calls_zero_utility(self):
        r=audit_bytes(self.raw)
        self.assertEqual(sha256(self.raw).hexdigest(),OUTER_SHA)
        self.assertEqual(r["native_c3_calls"],12)
        self.assertEqual(r["source_files_verified"],2328)
        self.assertEqual(r["scores"],{"NO_PRIOR":0,"EXACT_SOURCE":0})
        self.assertEqual(r["valid_json"],{"NO_PRIOR":6,"EXACT_SOURCE":6})
        self.assertFalse(r["model_weights_rehashed"])
        self.assertFalse(r["step2_promoted"])

    def test_outer_sha_tamper(self):
        with self.assertRaisesRegex(ValueError,"RUN117AT_OUTER_SHA_RED"):
            audit_bytes(self.raw+b"forged")

    def test_manifest_hash_tamper(self):
        with zipfile.ZipFile(BytesIO(self.raw)) as z:
            original=z.read("HEAD.txt")
        self.expect_red(repack(self.raw,{"HEAD.txt":original+b"tamper"}),"HEAD")

    def test_duplicate_zip_member(self):
        self.expect_red(repack(self.raw,duplicate="HEAD.txt"),"ZIP_MEMBERS")

    def test_forged_native_correctness(self):
        self.expect_red(change_report(self.raw,lambda r:
            r["rows"][0]["arms"][0]["score"].update(correct=1)),"FORGED_SCORE")

    def test_nonreaped_native_process(self):
        self.expect_red(change_report(self.raw,lambda r:
            r["rows"][0]["arms"][0].update(process_reaped=False)),"NATIVE_FINAL")

    def test_forged_source_ref(self):
        self.expect_red(change_report(self.raw,lambda r:
            r["rows"][0]["source_refs"][0].update(char_start=0)),"SOURCE_REF")

    def test_swapped_arm_order(self):
        self.expect_red(change_report(self.raw,lambda r:
            r["rows"][0]["arms"].reverse()),"ARM_ORDER")

    def test_typed_jef_answer_leak(self):
        def edit(r):
            item=r["rows"][0]["arms"][0]
            p=json.loads(item["messages"][1]["content"])
            p["typed_jef_candidate"]={"choice":"A","remaining":30}
            item["messages"][1]["content"]=json.dumps(p,sort_keys=True)
            item["messages_sha256"]=sha256(json.dumps(item["messages"],
                sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        self.expect_red(change_report(self.raw,edit),"PROMPT_AUTHORITY")

    def test_forged_learning_authority(self):
        self.expect_red(change_report(self.raw,lambda r:
            r.update(learning_authority=1)),"NATIVE_GATES")

    def test_invalid_json_and_duplicate_score(self):
        self.assertEqual(score('{"choice":"B","choice":"A","remaining":30}',
            {"choice":"A","remaining":30})["valid_json"],False)
        self.assertEqual(score('{"choice":"A","remaining":true}',
            {"choice":"A","remaining":1})["correct"],0)
        self.assertEqual(score('{"choice":"A","remaining":30}',
            {"choice":"A","remaining":30})["correct"],1)

if __name__=="__main__":
    unittest.main()
