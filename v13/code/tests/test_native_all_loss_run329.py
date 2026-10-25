"""Run329 synthetic/source-only all-token compatibility and fail-closed negative tests."""
from pathlib import Path
import tempfile
import unittest

from scripts import prepare_native_answer_epoch_run319 as E
from scripts import prepare_native_all_loss_run329 as A

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
ORIGINAL = SCRIPTS / "native_answer_finetune.cpp"
PATCH = SCRIPTS / "patches/native-answer-epoch-checkpoint-run319.patch"


def source_in(root):
    out = root / "run319"
    E.prepare(ORIGINAL, PATCH, out)
    return out / "scripts/native_answer_finetune.cpp"


class Run329SourceOnly(unittest.TestCase):
    def test_registered_original_unchanged_and_prepared_hash(self):
        with tempfile.TemporaryDirectory() as td:
            source = source_in(Path(td))
            self.assertEqual(E.digest(ORIGINAL), E.ORIGINAL_SHA256)
            self.assertEqual(A.digest(source), A.RUN319_PREPARED_SHA)

    def test_patch_preserves_original_answer_only_and_checkpoint_controls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = source_in(root)
            before = src.read_bytes()
            out = root / "all.cpp"
            receipt = A.prepare(src, out)
            code = out.read_text()
            self.assertEqual(src.read_bytes(), before)
            self.assertEqual(receipt["status"], "SOURCE_PREPARED_NO_NATIVE_TRAINING")
            self.assertEqual(receipt["loss_mode_default"], "answer")
            self.assertIn('const bool loss_all =', code)
            self.assertIn('kind[k + 1] == ANSWER ? tokens[k + 1] : -1', code)
            self.assertIn('V13_EPOCH_CHECKPOINT', code)
            self.assertIn('V13_EPOCH_CHECKPOINTS', code)
            self.assertFalse(receipt["native_training_executed"])

    def test_all_token_mode_labels_every_next_token(self):
        with tempfile.TemporaryDirectory() as td:
            src = source_in(Path(td)); code = A.transform(src.read_text())
            self.assertIn('labels[i*n_ctx + j] = loss_all ? tokens[k + 1]', code)
            self.assertIn('n_supervised += loss_all || kind[k + 1] == ANSWER;', code)

    def test_unknown_mode_rejected_and_default_not_changed(self):
        with tempfile.TemporaryDirectory() as td:
            src = source_in(Path(td)); code = A.transform(src.read_text())
            self.assertIn('V13_LOSS_MODE must be all or answer', code)
            self.assertIn('const bool loss_all = loss_mode_env &&', code)
            self.assertIn('std::strcmp(loss_mode_env, "answer") != 0', code)

    def test_all_mode_rejects_answer_and_kl_control_spans(self):
        with tempfile.TemporaryDirectory() as td:
            src = source_in(Path(td)); code = A.transform(src.read_text())
            self.assertIn('params.prompt.find_first_of(std::string(', code)
            self.assertIn('all-token loss refuses answer/KL span markers', code)

    def test_reject_modified_run319_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = source_in(root)
            src.write_bytes(src.read_bytes() + b"\n// modified\n")
            with self.assertRaisesRegex(ValueError, "SHA drift"):
                A.prepare(src, root / "all.cpp")

    def test_refuse_output_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = source_in(root)
            out = root / "all.cpp"; out.write_text("do not overwrite")
            with self.assertRaises(FileExistsError):
                A.prepare(src, out)
            self.assertEqual(out.read_text(), "do not overwrite")

    def test_refuse_symlinked_prepared_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = source_in(root)
            link = root / "alias.cpp"; link.symlink_to(src)
            with self.assertRaisesRegex(ValueError, "SHA drift"):
                A.prepare(link, root / "all.cpp")

    def test_missing_or_duplicated_patch_anchor_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = source_in(Path(td)); original = src.read_text()
            anchor = A.TRANSFORMS[0][0]
            for code in (original.replace(anchor, ""), original + anchor):
                with self.subTest(duplicate=code.endswith(anchor)), self.assertRaisesRegex(ValueError, "anchor"):
                    A.transform(code)

    def test_deterministic_patched_candidate_hash(self):
        hashes = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); src = source_in(root); out = root / "all.cpp"
                A.prepare(src, out)
                hashes.append(A.digest(out))
        self.assertEqual(hashes[0], hashes[1])

    def test_no_model_or_gate_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = source_in(root)
            result = A.prepare(src, root / "all.cpp")
            self.assertFalse(result["model_weights_published"])
            self.assertEqual(result["gates"]["STEP2"], "UTILITY_FAIL")
            self.assertEqual(result["gates"]["B3_L1"], "FAIL")
            self.assertEqual(result["gates"]["Body_JEPA"], "UNAVAILABLE")
            self.assertEqual(result["gates"]["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
