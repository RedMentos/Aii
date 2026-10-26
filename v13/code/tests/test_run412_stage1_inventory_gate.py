"""Run412 synthetic adversarial report contract; no native model execution."""
import copy
import unittest

import run412_stage1_inventory_gate as gate


def fixture():
    models = [
        {"path": gate.MODEL_PREFIX + f"role{i}/model{i}.gguf",
         "size": 1000 + i, "sha256": "a" * 64,
         "registered_roles": ["body"]} for i in range(7)]
    binaries = [gate.BIN_PREFIX + f"build/file{i:03d}" for i in range(63)]
    return {
        "status": "FILTERED_STAGE1_VERIFIED_NO_PROMOTION", "errors": [],
        "original_zip_sha256": gate.ORIGINAL_ZIP_SHA256,
        "members_verified": 107, "rows_verified": 42, "remaining_arms": 8,
        "native": {"completed": ["O_s20"], "rows_verified": 42, "remaining_arms": 8},
        "all_member_sha_checked": True, "zip_crc_checked": True,
        "original_raw_retained_external": True, "native_inference_started": False,
        "redmi_measured": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "jepa_weight": 0,
        "omitted_registered_models": models,
        "omitted_unlisted_in_manifest": [m["path"] for m in models],
        "unlisted_binary_members": binaries,
        "unlisted_binary_hashes": {
            name: {"sha256": "b" * 64, "bytes": 123,
                   "provenance": "ORIGINAL_ZIP_SHA_ONLY_NOT_EXECUTED"}
            for name in binaries},
    }


class Run412InventoryGateTests(unittest.TestCase):
    def test_valid_synthetic_contract_remains_nonpromoting(self):
        result = gate.verify(fixture())
        self.assertEqual(result["unlisted_binary_members"], 63)
        self.assertEqual(result["native_rows"], 42)
        self.assertFalse(result["canonical_gate_pass"])

    def test_historical_64_bin_prediction_is_not_the_observed_63(self):
        d = fixture()
        extra = gate.BIN_PREFIX + "build/extra"
        d["unlisted_binary_members"].append(extra)
        d["unlisted_binary_hashes"][extra] = {
            "sha256": "b" * 64, "bytes": 12,
            "provenance": "ORIGINAL_ZIP_SHA_ONLY_NOT_EXECUTED"}
        with self.assertRaisesRegex(ValueError, "OBSERVED_MEMBER_PARTITION_MISMATCH"):
            gate.verify(d)

    def test_invalid_report_variants_fail_closed(self):
        def edits():
            yield "red_status", lambda d: d.update(status="FILTERED_STAGE1_RED_PRESERVED")
            yield "red_errors", lambda d: d["errors"].append("failed")
            yield "original_zip", lambda d: d.update(original_zip_sha256="c" * 64)
            yield "members", lambda d: d.update(members_verified=108)
            yield "rows", lambda d: d.update(rows_verified=41)
            yield "remaining", lambda d: d.update(remaining_arms=7)
            yield "native_rows", lambda d: d["native"].update(rows_verified=41)
            yield "native_scope", lambda d: d["native"].update(completed=["O_s20", "P_s20"])
            yield "member_sha", lambda d: d.update(all_member_sha_checked=False)
            yield "crc", lambda d: d.update(zip_crc_checked=False)
            yield "original_retained", lambda d: d.update(original_raw_retained_external=False)
            yield "native_started", lambda d: d.update(native_inference_started=True)
            yield "redmi", lambda d: d.update(redmi_measured=True)
            yield "promoted", lambda d: d.update(canonical_gate_pass=True)
            yield "step2", lambda d: d.update(step2_exit="PASS")
            yield "jepa", lambda d: d.update(jepa_weight=0.1)
            yield "missing_bin", lambda d: d["unlisted_binary_members"].pop()
            yield "missing_hash", lambda d: d["unlisted_binary_hashes"].pop(next(iter(d["unlisted_binary_hashes"])))
            yield "bin_wrong_digest", lambda d: next(iter(d["unlisted_binary_hashes"].values())).update(sha256="oops")
            yield "bin_wrong_provenance", lambda d: next(iter(d["unlisted_binary_hashes"].values())).update(provenance="NATIVE_EXECUTED")
            yield "bin_zero_bytes", lambda d: next(iter(d["unlisted_binary_hashes"].values())).update(bytes=0)
            yield "model_missing", lambda d: d["omitted_registered_models"].pop()
            yield "model_missing_role", lambda d: d["omitted_registered_models"][0].update(registered_roles=[])
            yield "model_false_digest", lambda d: d["omitted_registered_models"][0].update(sha256="bad")
            yield "model_bool_size", lambda d: d["omitted_registered_models"][0].update(size=True)
            yield "model_unlisted_mismatch", lambda d: d["omitted_unlisted_in_manifest"].pop()
            yield "binary_path_escape", lambda d: d["unlisted_binary_members"].__setitem__(0, gate.BIN_PREFIX + "../bad")
            yield "model_path_escape", lambda d: d["omitted_registered_models"][0].update(path=gate.MODEL_PREFIX + "../bad")
            yield "duplicate_bin", lambda d: d["unlisted_binary_members"].__setitem__(1, d["unlisted_binary_members"][0])
            yield "duplicate_model", lambda d: d["omitted_registered_models"][1].update(path=d["omitted_registered_models"][0]["path"])
        for name, edit in edits():
            with self.subTest(name=name):
                d = copy.deepcopy(fixture())
                edit(d)
                with self.assertRaises((ValueError, TypeError)):
                    gate.verify(d)

    def test_reject_unexpected_zip_identity_even_if_report_rewritten(self):
        d = fixture()
        d["original_zip_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_IDENTITY_MISMATCH"):
            gate.verify(d, "c" * 64)

    def test_no_mutation_of_input(self):
        d = fixture()
        before = copy.deepcopy(d)
        gate.verify(d)
        self.assertEqual(d, before)


if __name__ == "__main__":
    unittest.main()
