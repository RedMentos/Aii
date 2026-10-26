"""Run494 primary-source custom license metadata adversarial checks (no network)."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run492_pinned_hf_metadata as M


def card(role):
    spec = M.SPECS[role]
    if spec["license"] == "lfm1.0":
        meta = {"license": "other", "license_name": "lfm1.0", "license_link": "LICENSE"}
        tags = ["license:other"]
    else:
        meta = {"license": "apache-2.0"}
        tags = ["license:apache-2.0"]
    return {
        "id": spec["repo"], "sha": spec["revision"], "private": False,
        "gated": False, "cardData": meta, "tags": tags,
        "siblings": [{"rfilename": spec["file"], "size": spec["size"],
                      "lfs": {"sha256": spec["sha256"], "size": spec["size"]}}],
    }


class NamedCustomLicense(unittest.TestCase):
    def test_exact_named_custom_license_matches_both_liquid_roles(self):
        for role in ("B1_DETAIL", "C3_LANGUAGE"):
            with self.subTest(role=role):
                result = M.verify_model(role, card(role), "a" * 64)
                self.assertEqual(result["license_metadata"], "lfm1.0")
                self.assertIsNone(result["license_accepted_by_user"])

    def test_exact_apache_remains_accepted(self):
        self.assertEqual(M.verify_model("B2_GIST", card("B2_GIST"), "a" * 64)["license_metadata"], "apache-2.0")

    def test_custom_license_must_have_exact_name_and_link(self):
        for mutate in [
            lambda d: d["cardData"].pop("license_name"),
            lambda d: d["cardData"].update(license_name="other"),
            lambda d: d["cardData"].update(license_link="UNVERIFIED"),
            lambda d: d["cardData"].pop("license_link"),
            lambda d: d["cardData"].update(license="apache-2.0"),
        ]:
            d = card("B1_DETAIL")
            mutate(d)
            with self.subTest(meta=d["cardData"]), self.assertRaisesRegex(ValueError, "MODEL_LICENSE_METADATA_CHANGED"):
                M.verify_model("B1_DETAIL", d, "a" * 64)

    def test_conflicting_tag_cannot_override_model_card(self):
        for role in ("B1_DETAIL", "B2_GIST"):
            d = card(role)
            d["tags"] = ["license:lfm1.0" if role == "B1_DETAIL" else "license:other"]
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, "MODEL_LICENSE_TAG_CONFLICT"):
                M.verify_model(role, d, "a" * 64)

    def test_tags_alone_cannot_override_missing_or_wrong_card(self):
        d = card("B1_DETAIL")
        d["cardData"] = {"license": "other"}
        d["tags"] = ["license:lfm1.0"]
        with self.assertRaisesRegex(ValueError, "MODEL_LICENSE_METADATA_CHANGED"):
            M.verify_model("B1_DETAIL", d, "a" * 64)

    def test_missing_lfs_still_fails_closed(self):
        d = card("B1_DETAIL")
        del d["siblings"][0]["lfs"]
        with self.assertRaisesRegex(ValueError, "MODEL_LFS_SHA256_UNAVAILABLE"):
            M.verify_model("B1_DETAIL", d, "a" * 64)

    def test_no_network_three_model_audit_preserves_negative_gates(self):
        by_repo = {spec["repo"]: role for role, spec in M.SPECS.items()}
        result = M.audit(lambda spec: (card(by_repo[spec["repo"]]), "f" * 64))
        self.assertEqual(set(result["models"]), set(M.SPECS))
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(result["b3_l1"], "FAIL")
        self.assertIs(result["native_executed"], False)
        self.assertIs(result["runner_verified"], False)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertIsNone(result["license_accepted_by_user"])


if __name__ == "__main__":
    unittest.main()
