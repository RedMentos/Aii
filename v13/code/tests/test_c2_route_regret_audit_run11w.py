"""Run11W stdlib archive/score tamper tests; no native or gate claims."""
from __future__ import annotations

import hashlib
import io
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from scripts import c2_route_regret_audit_run11w as a
from scripts import c2_body_observer_closed_run11r as r
from scripts import c2_body_disjoint_paired181_run11v as v


def synthetic_zip(root, *, bad_inner=False, traversal=False,
                  symlink=False, duplicate=False):
    p = Path(root) / "sample.zip"
    members = {"HEAD.txt": b"f" * 40 + b"\n",
               ("../escape" if traversal else "pilot/dummy.txt"): b"synthetic"}
    lines = [hashlib.sha256(value).hexdigest() + "  " + key
             for key, value in sorted(members.items())]
    if bad_inner:
        lines[0] = "0" * 64 + "  HEAD.txt"
    members["SHA256SUMS"] = ("\n".join(lines) + "\n").encode()
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in members.items():
            if symlink and name == "pilot/dummy.txt":
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, value)
            else:
                z.writestr(name, value)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("HEAD.txt", members["HEAD.txt"])
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


class RouteRegretRun11W(unittest.TestCase):
    def test_source_prompt_exact_both_frozen_cohorts(self):
        for fixture in r.FIXTURES:
            self.assertEqual(a.source_prompt(fixture), r.prompt(fixture))
        for fixture in v.FIXTURES:
            self.assertEqual(a.source_prompt(fixture), v.prompt(fixture))

    def test_frozen_arm_identity_and_no_gates(self):
        self.assertEqual(a.ARMS, r.ARMS)
        self.assertEqual(a.ARMS, v.ARMS)
        self.assertEqual(a.SCHEMA, "v13.c2_body.route_regret.readonly.v1")
        self.assertIn("comparative_utility_proven", a.NEGATIVE)

    def test_valid_archive_sha_crc_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d)
            z, got, entries, inner = a._load_zip(path, sha, "f" * 40)
            self.assertEqual(got, sha)
            self.assertEqual(entries, 3)
            self.assertEqual(inner, 2)
            z.close()

    def test_wrong_original_zip_hash_or_head_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_HASH_CHANGED"):
                a._load_zip(path, "0" * 64, "f" * 40)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_HEAD_CHANGED"):
                a._load_zip(path, sha, "e" * 40)

    def test_changed_inner_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d, bad_inner=True)
            with self.assertRaisesRegex(ValueError, "ZIP_INNER_HASH_CHANGED"):
                a._load_zip(path, sha, "f" * 40)

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d, traversal=True)
            with self.assertRaisesRegex(ValueError, "ZIP_UNSAFE_MEMBER"):
                a._load_zip(path, sha, "f" * 40)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d, symlink=True)
            with self.assertRaisesRegex(ValueError, "ZIP_UNSAFE_MEMBER"):
                a._load_zip(path, sha, "f" * 40)

    def test_duplicate_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = synthetic_zip(d, duplicate=True)
            with self.assertRaisesRegex(ValueError, "ZIP_DUPLICATE_COUNT_OR_CRC"):
                a._load_zip(path, sha, "f" * 40)

    def test_boolean_score_and_sum_must_match(self):
        self.assertEqual(a._score({"score": {"a": True, "b": False,
                                             "correct": 1, "out_of": 2}}, "score"), 1)
        for value in (
            {"a": 1, "b": False, "correct": 1, "out_of": 2},
            {"a": True, "b": True, "correct": 1, "out_of": 2},
            {"a": True, "b": False, "correct": 1, "out_of": 3},
        ):
            with self.assertRaisesRegex(ValueError, "SCORE_TYPE_OR_SUM_INVALID"):
                a._score({"score": value}, "score")

    def test_unregistered_seed_or_score_slot_fails_before_file(self):
        kw = dict(sha256="0" * 64, head="f" * 40,
                  schema="v13.c2_body.observer_closed.seed163.v1",
                  fixture_sha256="040e073bc1c544883a5d809d0883d6493366a8f241816c7e6dbefd30c87eaead",
                  score_slot="secondary_score")
        with self.assertRaisesRegex(ValueError, "SEED_UNREGISTERED"):
            a.audit("/nonexistent.zip", seed=999, **kw)
        with self.assertRaisesRegex(ValueError, "FROZEN_SCORE_SLOT_CHANGED"):
            a.audit("/nonexistent.zip", seed=163, **{**kw, "score_slot": "score"})
        with self.assertRaisesRegex(ValueError, "SCHEMA_UNREGISTERED"):
            a.audit("/nonexistent.zip", seed=163, **{**kw, "schema": "wrong"})
        with self.assertRaisesRegex(ValueError, "FIXTURE_PIN_CHANGED"):
            a.audit("/nonexistent.zip", seed=163, **{**kw, "fixture_sha256": "0" * 64})


if __name__ == "__main__":
    unittest.main()
