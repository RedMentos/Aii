"""Software-only integrity tests for read-only original ZIP posthoc replay."""
import hashlib
import io
import unittest
import warnings
import zipfile

from scripts.listarith_de_seed79_native_posthoc_replay import verified_files


def archive(files, manifest=None):
    payload = dict(files)
    if manifest is None:
        manifest = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                           for name, data in sorted(payload.items()))
    payload["SHA256SUMS"] = manifest.encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in payload.items():
            z.writestr(name, data)
    return stream.getvalue()


class PosthocZipIntegrityTests(unittest.TestCase):
    def test_valid_closed_archive(self):
        data = archive({"A.txt": b"abc", "B.txt": b"xyz"})
        files, digest, count = verified_files(data, hashlib.sha256(data).hexdigest())
        self.assertEqual(count, 2)
        self.assertEqual(files["A.txt"], b"abc")
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_outer_sha_mismatch(self):
        with self.assertRaisesRegex(ValueError, "ZIP_SHA256_MISMATCH"):
            verified_files(archive({"A": b"abc"}), "0" * 64)

    def test_inner_hash_mismatch(self):
        data = archive({"A": b"changed"}, hashlib.sha256(b"original").hexdigest() + "  A\n")
        with self.assertRaisesRegex(ValueError, "INNER_HASH_RED"):
            verified_files(data)

    def test_extra_unmanifested_member(self):
        data = archive({"A": b"abc", "B": b"def"},
                       hashlib.sha256(b"abc").hexdigest() + "  A\n")
        with self.assertRaisesRegex(ValueError, "INNER_COVERAGE_RED"):
            verified_files(data)

    def test_duplicate_manifest_line(self):
        line = hashlib.sha256(b"abc").hexdigest() + "  A\n"
        with self.assertRaisesRegex(ValueError, "INNER_MANIFEST_DUPLICATE_OR_HASH"):
            verified_files(archive({"A": b"abc"}, line + line))

    def test_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "ZIP_UNSAFE_PATH"):
            verified_files(archive({"../secret": b"abc"}))

    def test_duplicate_zip_entry_rejected(self):
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr("A", b"abc")
                z.writestr("A", b"abc")
                z.writestr("SHA256SUMS", hashlib.sha256(b"abc").hexdigest() + "  A\n")
        with self.assertRaisesRegex(ValueError, "ZIP_DUPLICATE_NAME"):
            verified_files(stream.getvalue())


if __name__ == "__main__":
    unittest.main()
