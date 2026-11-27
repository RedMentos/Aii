"""Tests for safe, explicit UCI archive extraction (no network in CI)."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from experiments.m1.download_uci import (
    DATASET_LICENSE,
    EXPECTED_MEMBER,
    download_dataset,
    extract_dataset_archive,
)


class UciDownloaderTests(unittest.TestCase):
    def _archive(self, path: Path, entries: dict[str, bytes]) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, payload in entries.items():
                bundle.writestr(name, payload)

    def test_extracts_only_expected_member_and_records_hashes(self):
        payload = b"Date;Time;Global_active_power\n16/12/2006;17:24:00;4.216\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "uci.zip"
            destination = root / EXPECTED_MEMBER
            self._archive(archive, {
                "README.txt": b"metadata",
                f"folder/{EXPECTED_MEMBER}": payload,
            })
            result = extract_dataset_archive(
                archive, destination, source_url="https://archive.ics.uci.edu/test.zip"
            )
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(result["file_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            sidecar = Path(result["provenance_path"])
            provenance = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(provenance["file_sha256"], result["file_sha256"])
            self.assertEqual(provenance["license"], DATASET_LICENSE)
            self.assertEqual(provenance["source_url"], "https://archive.ics.uci.edu/test.zip")
            self.assertEqual(sorted(p.name for p in root.iterdir()), sorted([
                "uci.zip", EXPECTED_MEMBER, EXPECTED_MEMBER + ".provenance.json"
            ]))

    def test_rejects_path_traversal_in_any_archive_member(self):
        payload = b"safe data"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unsafe.zip"
            self._archive(archive, {
                EXPECTED_MEMBER: payload,
                "../escape.txt": b"must not be written",
            })
            with self.assertRaisesRegex(ValueError, "unsafe ZIP member path"):
                extract_dataset_archive(archive, root / EXPECTED_MEMBER)
            self.assertFalse((root / EXPECTED_MEMBER).exists())
            self.assertFalse((root.parent / "escape.txt").exists())

    def test_rejects_duplicate_expected_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "duplicate.zip"
            self._archive(archive, {
                EXPECTED_MEMBER: b"one",
                f"nested/{EXPECTED_MEMBER}": b"two",
            })
            with self.assertRaisesRegex(ValueError, "exactly one"):
                extract_dataset_archive(archive, root / EXPECTED_MEMBER)

    def test_refuses_overwrite_without_explicit_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.zip"
            destination = root / EXPECTED_MEMBER
            self._archive(archive, {EXPECTED_MEMBER: b"first"})
            extract_dataset_archive(archive, destination)
            with self.assertRaises(FileExistsError):
                extract_dataset_archive(archive, destination)
            self.assertEqual(destination.read_bytes(), b"first")
            self._archive(archive, {EXPECTED_MEMBER: b"second"})
            extract_dataset_archive(archive, destination, force=True)
            self.assertEqual(destination.read_bytes(), b"second")

    def test_download_rejects_non_uci_host_before_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "archive.ics.uci.edu"):
                download_dataset(directory, source_url="https://example.com/data.zip")

    def test_rejects_non_zip_and_missing_dataset_member(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            not_zip = root / "not.zip"
            not_zip.write_bytes(b"not a zip")
            with self.assertRaises(zipfile.BadZipFile):
                extract_dataset_archive(not_zip, root / EXPECTED_MEMBER)
            archive = root / "missing.zip"
            self._archive(archive, {"README.txt": b"no dataset"})
            with self.assertRaisesRegex(ValueError, "exactly one"):
                extract_dataset_archive(archive, root / EXPECTED_MEMBER)


if __name__ == "__main__":
    unittest.main()
