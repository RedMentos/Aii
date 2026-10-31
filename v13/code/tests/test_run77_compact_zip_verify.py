"""Synthetic ZIP attack tests; no native/model or scientific claim."""
import io
import unittest
import zipfile

from scripts import run77_compact_zip_verify as verifier


def archive(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, payload in members:
            z.writestr(name, payload)
    return buf.getvalue()


class CompactZipTests(unittest.TestCase):
    def test_empty_zip_cannot_pass(self):
        result = verifier.audit_zip(archive([]))
        self.assertEqual(result["status"], "COMPACT_EVIDENCE_RED")
        self.assertIn("REQUIRED_EVIDENCE_MISSING", result["findings"])

    def test_path_traversal_rejected(self):
        result = verifier.audit_zip(archive([
            ("../private.txt", "do not extract"),
            ("report.json", "{}"),
        ]))
        self.assertIn("UNSAFE_ZIP_MEMBER", result["findings"])

    def test_duplicate_names_rejected(self):
        result = verifier.audit_zip(archive([
            ("report.json", "{}"), ("report.json", "[]"),
        ]))
        self.assertIn("DUPLICATE_ZIP_MEMBER", result["findings"])

    def test_unmanifested_bytes_rejected(self):
        content = b"synthetic"
        result = verifier.audit_zip(archive([
            ("HEAD.txt", content), ("SHA256SUMS", ""),
        ]))
        self.assertIn("UNHASHED_MEMBERS_RED", result["findings"])

    def test_bad_manifest_digest_rejected(self):
        result = verifier.audit_zip(archive([
            ("HEAD.txt", "abc"),
            ("SHA256SUMS", "0" * 64 + "  ./HEAD.txt\n"),
        ]))
        self.assertIn("SHA_MANIFEST_MISMATCH_RED", result["findings"])

    def test_non_zip_and_oversize_fail_closed(self):
        result = verifier.audit_zip(b"not a zip")
        self.assertEqual(result["status"], "COMPACT_ZIP_INVALID_RED")
        result = verifier.audit_zip(b"x" * (verifier.MAX_ZIP_BYTES + 1))
        self.assertEqual(result["status"], "COMPACT_ZIP_OVERSIZE_RED")


if __name__ == "__main__":
    unittest.main()
