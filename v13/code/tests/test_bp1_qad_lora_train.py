"""BP1 QAD LoRA train-only driver: fake trainer, no optimizer or model execution."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import bp1_qad_lora_train as L
from scripts import bp1_qad_token_budget as B


def rows():
    return [{"row_id":f"RUN181-{i:02d}","arm":"offer","prompt":f"Source for project {i}",
             "target":json.dumps({"answer":f"Code{i}","evidence_quote":f"Code{i}","uncertainty":""}),
             "answer_keys":[f"Code{i}"]} for i in range(25)]


def audit():
    return {"schema":B.SCHEMA,"train_sha256":B.TRAIN_SHA,"source_revision":B.REVISION,
            "heldout_targets_used":False,"native_c3_training_executed":False,
            "max_total_tokens":747,"summary":{"1024":{"truncated_rows":0}},
            "tokenizer_files_sha256":{"tokenizer.json":L.TOKENIZER_SHA,
                                      "chat_template.jinja":L.TEMPLATE_SHA},
            "qad_master_sha256_metadata_only":L.MASTER_SHA}


class FakeTrainer:
    instances = []
    fail = False
    def __init__(self, model, work, **kwargs):
        self.model, self.work, self.kwargs = model, Path(work), kwargs
        FakeTrainer.instances.append(self)

    def fit(self, items, base_generation):
        self.items, self.generation = items, base_generation
        if FakeTrainer.fail:
            raise RuntimeError("injected training failure")
        self.work.mkdir(parents=True, exist_ok=True)
        path = self.work / "adapter.gguf"
        path.write_bytes(b"fake adapter")
        return {"artifact":str(path),"hash":"f"*64,"metrics":{"steps":2}}


class DriverTests(unittest.TestCase):
    def setUp(self):
        FakeTrainer.instances = []
        FakeTrainer.fail = False
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.master = self.root / "qad"
        self.master.mkdir()
        for name in ("model.safetensors","tokenizer.json","chat_template.jinja"):
            (self.master / name).write_bytes(b"fake")
        self.audit = self.root / "TOKEN_BUDGET.json"
        self.audit.write_text(json.dumps(audit()))
        self.out = self.root / "out"

    def fake_sha(self, path):
        name = Path(path).name
        return {"model.safetensors":L.MASTER_SHA,"tokenizer.json":L.TOKENIZER_SHA,
                "chat_template.jinja":L.TEMPLATE_SHA,"adapter.gguf":"f"*64}[name]

    def run(self, *, execute_native=False, owner_confirmed=False, trainer_factory=FakeTrainer):
        with patch.object(B,"load_train",return_value=(rows(),B.TRAIN_SHA)), \
             patch.object(L,"sha",side_effect=self.fake_sha), \
             patch.object(L,"TOKEN_AUDIT_SHA",hashlib.sha256(self.audit.read_bytes()).hexdigest()):
            return L.run(self.root/"train_offer.jsonl",self.audit,self.master,self.out,
                         execute_native=execute_native,owner_confirmed=owner_confirmed,
                         trainer_factory=trainer_factory)

    def test_1024_context_and_no_jepa_or_activation(self):
        self.assertEqual(L.CFG["max_tokens"],1024)
        self.assertEqual(L.CFG["max_steps"],2)
        self.assertEqual(L.CFG["jepa_weight"],0)
        self.assertFalse(L.GATES["adapter_activated"])

    def test_preflight_never_starts_trainer(self):
        result = self.run()
        self.assertEqual(result["status"],"PREFLIGHT_ONLY_NO_OPTIMIZER")
        self.assertEqual(len(FakeTrainer.instances),0)
        self.assertTrue((self.out/"PREFLIGHT.json").is_file())
        self.assertFalse((self.out/"TRAIN_RECEIPT.json").exists())

    def test_native_fake_trainer_never_activates(self):
        result = self.run(execute_native=True,owner_confirmed=True)
        self.assertEqual(result["status"],"NATIVE_LORA_UNAPPROVED_UNEVALUATED")
        self.assertEqual(len(FakeTrainer.instances),1)
        self.assertEqual(len(FakeTrainer.instances[0].items),25)
        self.assertEqual(FakeTrainer.instances[0].kwargs["cfg"]["max_tokens"],1024)
        self.assertEqual(result["adapter_sha256"],"f"*64)
        self.assertFalse(result["adapter_activated"])
        self.assertFalse(result["heldout_targets_used"])

    def test_native_requires_explicit_owner(self):
        with self.assertRaises(PermissionError):
            self.run(execute_native=True,owner_confirmed=False)
        self.assertEqual(len(FakeTrainer.instances),0)
        self.assertFalse((self.out/"TRAIN_RECEIPT.json").exists())

    def test_bad_audit_sha_fails_before_model(self):
        with patch.object(B,"load_train",return_value=(rows(),B.TRAIN_SHA)):
            with self.assertRaisesRegex(ValueError,"closed QAD token audit"):
                L.run(self.root/"train_offer.jsonl",self.audit,self.master,self.out)
        self.assertFalse(self.out.exists())

    def test_invalid_audit_overflow_rejected(self):
        data = audit();data["summary"]["1024"]["truncated_rows"] = 1
        with self.assertRaisesRegex(ValueError,"1024-token"):
            L.validate_audit(data)

    def test_wrong_tokenizer_hash_rejected(self):
        data = audit();data["tokenizer_files_sha256"]["tokenizer.json"] = "0"*64
        with self.assertRaisesRegex(ValueError,"tokenizer/template"):
            L.validate_audit(data)

    def test_missing_adapter_is_failure_not_promotion(self):
        class Missing(FakeTrainer):
            def fit(self, items, base_generation):
                return {"artifact":"/not/a/real/adapter.gguf","hash":"f"*64}
        with self.assertRaisesRegex(ValueError,"did not produce"):
            self.run(execute_native=True,owner_confirmed=True,trainer_factory=Missing)
        self.assertTrue((self.out/"FAILED.json").exists())
        self.assertFalse((self.out/"TRAIN_RECEIPT.json").exists())

    def test_failed_optimizer_keeps_checkpoint_and_negative_gates(self):
        FakeTrainer.fail = True
        with self.assertRaisesRegex(RuntimeError,"injected"):
            self.run(execute_native=True,owner_confirmed=True)
        failure = json.loads((self.out/"FAILED.json").read_text())
        self.assertFalse(failure["adapter_activated"])
        self.assertEqual(failure["gates"]["jepa_weight"],0)

    def test_wrong_train_arm_rejected(self):
        data = rows();data[0]["arm"]="no_offer"
        with self.assertRaisesRegex(ValueError,"invalid train-only"):
            L.make_items(data)

    def test_duplicate_row_rejected(self):
        data = rows();data[1]["row_id"]=data[0]["row_id"]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            L.make_items(data)


if __name__ == "__main__":
    unittest.main()
