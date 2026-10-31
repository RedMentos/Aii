"""Synthetic ZIP tamper controls for W7S raw attestation; no native runs."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import verify_w7s_native_zip as audit
from tests import test_verify_w7s_full_gates as fixtures


class W7SNativeZipAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.W7SFullGateReplayTests(
            "test_complete_nine_row_w1_w7_raw_replay")
        self.fixture.setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.zip = self.root / "original.zip"
        self.members = self.make_members()
        self.write()

    def tearDown(self):
        self.tmp.cleanup()
        self.fixture.tearDown()

    def make_members(self):
        pins = dict(audit.REQUIRED_PINS)
        members = {
            "HEAD.txt": (audit.EXPECTED_HEAD + "\n").encode(),
            "PINS.txt": "".join(f"{sha} {name}\n"
                                for name, sha in pins.items()).encode(),
            "PINS_RAW.log": "".join(f"{sha} {sha} {name}\n"
                                    for name, sha in pins.items()).encode(),
            "RESULT.json": self.fixture.result.read_bytes(),
            "EXTRA.log": b"CRCMARKER123",
        }
        for stage in audit.STAGES:
            members[stage + "_EXIT.txt"] = b"0\n"
        for arm in audit.gates.base.ARMS:
            for seed in audit.gates.base.SEEDS:
                name = f"work/{arm}-{seed}-RESULT.json"
                members[name] = (
                    self.fixture.work / f"{arm}-{seed}-RESULT.json").read_bytes()
        return members

    def write(self, extras=()):
        sums = "".join(
            f"{hashlib.sha256(value).hexdigest()}  ./{name}\n"
            for name, value in sorted(self.members.items()))
        with zipfile.ZipFile(self.zip, "w", compression=zipfile.ZIP_STORED) as z:
            for name, data in self.members.items():
                z.writestr(name, data)
            z.writestr("SHA256SUMS", sums.encode())
            for name, data in extras:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    z.writestr(name, data)

    def test_synthetic_zip_pass_is_not_native_proof(self):
        result = audit.audit(self.zip)
        self.assertEqual(result["status"],
                         "W7S_RAWZIP_SELF_CONSISTENT_SHADOW")
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["redmi_measured"])
        self.assertTrue(result["w1_w7_raw_replay"])

    def test_stage_red_is_not_waived(self):
        self.members["REALFILE_EXIT.txt"] = b"1\n"
        self.write()
        with self.assertRaisesRegex(ValueError, "STAGE_RED"):
            audit.audit(self.zip)

    def test_source_head_tamper_refused(self):
        self.members["HEAD.txt"] = b"0" * 40
        self.write()
        with self.assertRaisesRegex(ValueError, "HEAD_IDENTITY"):
            audit.audit(self.zip)

    def test_manifest_hash_tamper_refused(self):
        self.write()
        # Rebuild archive with an intentionally stale manifest.
        with zipfile.ZipFile(self.zip) as z:
            manifest = z.read("SHA256SUMS")
        self.members["EXTRA.log"] = b"DIFFERENT123"
        with zipfile.ZipFile(self.zip, "w", compression=zipfile.ZIP_STORED) as z:
            for name, data in self.members.items():
                z.writestr(name, data)
            z.writestr("SHA256SUMS", manifest)
        with self.assertRaisesRegex(ValueError, "SHA256_EXTRA"):
            audit.audit(self.zip)

    def test_crc_tamper_refused(self):
        data = self.zip.read_bytes()
        self.assertIn(b"CRCMARKER123", data)
        self.zip.write_bytes(data.replace(b"CRCMARKER123", b"CRCMARKER999", 1))
        with self.assertRaises((zipfile.BadZipFile, ValueError)):
            audit.audit(self.zip)

    def test_duplicate_member_refused(self):
        self.write(extras=(("HEAD.txt", b"duplicate"),))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_MEMBER"):
            audit.audit(self.zip)

    def test_path_traversal_refused(self):
        self.write(extras=(("../outside.txt", b"no"),))
        with self.assertRaisesRegex(ValueError, "PATH_TRAVERSAL"):
            audit.audit(self.zip)

    def test_missing_row_refused(self):
        self.members.pop("work/balanced_slot-601-RESULT.json")
        self.write()
        with self.assertRaisesRegex(ValueError, "ROW_MISSING"):
            audit.audit(self.zip)

    def test_forged_w7_gate_refused(self):
        r = json.loads(self.members["RESULT.json"])
        r["balanced_slot_w7"]["W7a_both_world_action_gain"] = True
        self.members["RESULT.json"] = json.dumps(r).encode()
        self.write()
        with self.assertRaisesRegex(ValueError, "W7_GATES"):
            audit.audit(self.zip)


if __name__ == "__main__":
    unittest.main()
