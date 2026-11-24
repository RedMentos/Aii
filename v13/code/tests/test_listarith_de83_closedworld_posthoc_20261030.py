"""Software-only integrity tests for original seed83 ZIP posthoc replay."""
from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
import stat
import unittest
import zipfile

from scripts.listarith_de83_closedworld_original_posthoc import (
    EXPECTED_INNER_HASHES, ORIGINAL_ZIP_SHA256, _safe_name, audit_zip_bytes,
    verified_members,
)


def zip_bytes(extra=None, tamper_hash=False, missing_raw=False):
    entries = {}
    for i in range(24 if not missing_raw else 23):
        entries["pilot/raw/%02d_D83-%02d.json" % (i, i + 1)] = b"{}"
    for i in range(48 - len(entries)):
        entries["evidence/file%02d.txt" % i] = str(i).encode()
    if extra is not None:
        entries.update(extra)
    lines = []
    for name, data in sorted(entries.items()):
        digest = hashlib.sha256(data).hexdigest()
        if tamper_hash and name == sorted(entries)[0]:
            digest = "0" * 64
        lines.append(digest + "  ./" + name)
    entries["SHA256SUMS"] = ("\n".join(lines) + "\n").encode()
    b = BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return b.getvalue()


class Original83PosthocIntegrity(unittest.TestCase):
    def test_pins_are_historical_not_new_native(self):
        self.assertEqual(len(ORIGINAL_ZIP_SHA256), 64)
        self.assertEqual(EXPECTED_INNER_HASHES, 48)

    def test_valid_closed_manifest(self):
        data = zip_bytes()
        members = verified_members(data, hashlib.sha256(data).hexdigest())
        self.assertEqual(len(members), 49)
        self.assertEqual(sum(n.startswith("pilot/raw/") for n in members), 24)

    def test_wrong_original_outer_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA256_MISMATCH"):
            verified_members(zip_bytes())

    def test_inner_hash_tamper_rejected(self):
        data = zip_bytes(tamper_hash=True)
        with self.assertRaisesRegex(ValueError, "INNER_HASH_MISMATCH"):
            verified_members(data, hashlib.sha256(data).hexdigest())

    def test_missing_native_row_rejected(self):
        data = zip_bytes(missing_raw=True)
        with self.assertRaisesRegex(ValueError, "NATIVE_RAW_ROW_COUNT_RED"):
            verified_members(data, hashlib.sha256(data).hexdigest())

    def test_extra_member_not_in_manifest_rejected(self):
        data = zip_bytes(extra={"extra.txt": b"bad"})
        with self.assertRaisesRegex(ValueError, "INNER_HASH_COUNT_RED"):
            verified_members(data, hashlib.sha256(data).hexdigest())

    def test_traversal_and_absolute_path_rejected(self):
        b = BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("../evil.txt", "x")
            z.writestr("SHA256SUMS", "")
        data = b.getvalue()
        with self.assertRaisesRegex(ValueError, "ZIP_UNSAFE_PATH"):
            verified_members(data, hashlib.sha256(data).hexdigest())
        info = zipfile.ZipInfo("/tmp/evil")
        with self.assertRaisesRegex(ValueError, "ZIP_UNSAFE_PATH"):
            _safe_name(info)

    def test_symlink_rejected(self):
        info = zipfile.ZipInfo("pilot/raw/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaisesRegex(ValueError, "ZIP_SYMLINK_REJECTED"):
            _safe_name(info)

    def test_no_fake_native_report(self):
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA256_MISMATCH"):
            audit_zip_bytes(zip_bytes())


if __name__ == "__main__":
    unittest.main()
