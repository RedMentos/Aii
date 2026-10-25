"""Run291 model-free preregistration and prompt-binding checks."""
import hashlib
import unittest

from v13.prompts import TEXT
from scripts.run291_memory_prompt_probe import (
    SUFFIX, SUFFIX_SHA256, configure_arm, summarize,
)


class Run291MemoryPromptProbe(unittest.TestCase):
    def test_suffix_bytes_and_baseline_unchanged(self):
        original = TEXT["en"]["system"]
        self.assertEqual(hashlib.sha256(SUFFIX.encode()).hexdigest(), SUFFIX_SHA256)
        saved = configure_arm("baseline")
        self.assertEqual(saved, original)
        self.assertEqual(TEXT["en"]["system"], original)

    def test_candidate_is_ephemeral_append_only(self):
        original = TEXT["en"]["system"]
        try:
            saved = configure_arm("source_first")
            self.assertEqual(saved, original)
            self.assertEqual(TEXT["en"]["system"], original + SUFFIX)
            self.assertEqual(TEXT["de"]["system"].startswith("Du bist V13"), True)
        finally:
            TEXT["en"]["system"] = original

    def test_unknown_arm_rejected_without_mutation(self):
        original = TEXT["en"]["system"]
        with self.assertRaises(ValueError):
            configure_arm("auto_promote")
        self.assertEqual(TEXT["en"]["system"], original)

    @staticmethod
    def fixture(with_suffix):
        system = "Native system prompt" + (SUFFIX if with_suffix else "")
        return {
            "status": "MEMORY_RETRIEVAL_PARTIAL",
            "checks": {
                "native_language_exact_source_delivery": True,
                "native_detail_exact_source_delivery": True,
                "native_language_answer_uses_human_source": True,
                "native_detail_answer_uses_human_source": False,
                "same_entity_wrong_topic_rejected": True,
                "different_entity_rejected": True,
                "different_session_rejected": True,
            },
            "native_generation_calls": [
                {"phase": "NATIVE_ANSWER", "role": role, "completed": True,
                 "messages": [{"role": "system", "content": system}]}
                for role in ("C3_LANGUAGE", "B1_DETAIL")
            ],
        }

    def test_baseline_and_candidate_binding(self):
        for arm, suffix in (("baseline", False), ("source_first", True)):
            with self.subTest(arm=arm):
                result = summarize(arm, self.fixture(suffix), 2, {})
                self.assertTrue(result["diagnostic_valid"])
                self.assertFalse(result["all_existing_checks_pass"])
                self.assertFalse(result["native_detail_answer_uses_human_source"])
                self.assertEqual(result["integration_exit"], 2)

    def test_missing_role_or_unbound_source_is_not_valid(self):
        d = self.fixture(True)
        d["native_generation_calls"].pop()
        self.assertFalse(summarize("source_first", d, 2, {})["diagnostic_valid"])
        d = self.fixture(True)
        d["checks"]["native_detail_exact_source_delivery"] = False
        self.assertFalse(summarize("source_first", d, 2, {})["diagnostic_valid"])
        d = self.fixture(False)
        self.assertFalse(summarize("source_first", d, 2, {})["diagnostic_valid"])


if __name__ == "__main__":
    unittest.main()
