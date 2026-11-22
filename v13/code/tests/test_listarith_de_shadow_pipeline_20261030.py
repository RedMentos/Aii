"""Software-only tests for unwired German typed-list arithmetic pipeline."""
import json
import unittest

from v13.agi.listarith_de_shadow_pipeline import (
    AUTHORITY, UnsafeRead, evaluate, parse_typed, verify_name_number_bindings,
)


def raw(*pairs):
    return json.dumps({"values": [{"name": n, "number": v} for n, v in pairs]},
                      ensure_ascii=False)


class GermanShadowPipelineTest(unittest.TestCase):
    def assert_result(self, text, values, operation, value):
        got = evaluate(text, raw(*values))
        self.assertEqual(got["status"], "SHADOW_RESULT", got)
        self.assertEqual((got["operation"], got["value"]), (operation, value))
        self.assertEqual(got["authority"], AUTHORITY)
        self.assertFalse(got["live_tool_execution"])
        self.assertFalse(got["external_action_authority"])
        self.assertFalse(got["step2_gate_promoted"])
        self.assertFalse(got["b3_promoted"])
        self.assertFalse(got["body_jepa_available"])
        self.assertEqual(got["jepa_weight"], 0)
        self.assertFalse(got["redmi_measured"])
        self.assertFalse(got["whole_system_complete"])

    def assert_abstain(self, text, raw_json, reason=None):
        got = evaluate(text, raw_json)
        self.assertEqual(got["status"], "SHADOW_ABSTAIN", got)
        self.assertIsNone(got["value"])
        if reason:
            self.assertIn(reason, got["reason"])
        return got

    def test_total_simple(self):
        self.assert_result("Apfel 14; Birne 26. Wie hoch ist die Summe?",
                           [("Apfel", 14), ("Birne", 26)], "total", 40)

    def test_total_date_not_read_as_item(self):
        self.assert_result("2026 wurden für Kiefer 18 Euro und für Fichte 31 Euro notiert. Was ergibt das zusammen?",
                           [("Kiefer", 18), ("Fichte", 31)], "total", 49)

    def test_total_multiline(self):
        self.assert_result("Liste:\nEins = 4\nZwei = 6\nDrei = 8\nWie viel insgesamt?",
                           [("Eins", 4), ("Zwei", 6), ("Drei", 8)], "total", 18)

    def test_signed_parenthesized(self):
        self.assert_result("Zahlenblock: Saphir (+12), Rubin (+7), Opal (+5). Addiere.",
                           [("Saphir", 12), ("Rubin", 7), ("Opal", 5)], "total", 24)

    def test_negative_signed(self):
        self.assert_result("Temperaturen: Morgen −3, Mittag 9, Abend 2. Wie groß ist die Summe?",
                           [("Morgen", -3), ("Mittag", 9), ("Abend", 2)], "total", 8)

    def test_max_min_difference(self):
        self.assert_result("Nord 17; Süd 9; Ost 22. Wie groß ist der Unterschied zwischen dem höchsten und dem niedrigsten Wert?",
                           [("Nord", 17), ("Süd", 9), ("Ost", 22)], "difference_max_min", 13)

    def test_wrong_header_name_rejected(self):
        self.assert_abstain("Temperaturen: Morgen -3, Mittag 9, Abend 2. Wie groß ist die Summe?",
                            raw(("temperaturen", -3), ("Mittag", 9), ("Abend", 2)),
                            "NAME_NUMBER_NOT_ADJACENT")

    def test_invented_number_rejected(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe?",
                            raw(("Apfel", 14), ("Birne", 99)), "NAME_NUMBER_NOT_ADJACENT")

    def test_invented_name_rejected(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe?",
                            raw(("Mango", 14), ("Birne", 26)), "NAME_NUMBER_NOT_ADJACENT")

    def test_reuse_same_source_span_rejected(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe?",
                            raw(("Apfel", 14), ("Apfel", 14)), "SOURCE_SPAN_REUSED")

    def test_distinct_duplicate_spans_allowed(self):
        self.assert_result("Apfel 14; Apfel 14; Birne 26. Summe?",
                           [("Apfel", 14), ("Apfel", 14), ("Birne", 26)], "total", 54)

    def test_substring_name_not_accepted(self):
        self.assert_abstain("Apfelmus 14; Birne 26. Summe?",
                            raw(("Apfel", 14), ("Birne", 26)), "NAME_NUMBER_NOT_ADJACENT")

    def test_meta_claim_abstains(self):
        self.assert_abstain("Rot 108; Blau 27; Grün 15. Summe: 150. Ist die genannte Summe richtig?",
                            raw(("Rot", 108), ("Blau", 27), ("Grün", 15)),
                            "OPERATION_NEGATED_OR_META")

    def test_count_question_abstains(self):
        self.assert_abstain("Apfel 14; Birne 26. Wie viele Werte stehen hier?",
                            raw(("Apfel", 14), ("Birne", 26)), "OPERATION_")

    def test_negated_sum_abstains(self):
        self.assert_abstain("Apfel 14; Birne 26. Bitte keine Summe bilden.",
                            raw(("Apfel", 14), ("Birne", 26)), "OPERATION_NEGATED_OR_META")

    def test_aggregate_claim_never_used_as_item(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe: 40. Bitte addiere.",
                            raw(("Apfel", 14), ("Birne", 26), ("Summe", 40)),
                            "AGGREGATE_AS_INPUT")

    def test_json_duplicate_keys_rejected(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe?",
                            '{"values":[{"name":"Apfel","number":14},{"name":"Birne","number":26}],"values":[]}',
                            "DUPLICATE_JSON_KEY")

    def test_nested_duplicate_keys_rejected(self):
        self.assert_abstain("Apfel 14; Birne 26. Summe?",
                            '{"values":[{"name":"Apfel","name":"Birne","number":14},{"name":"Birne","number":26}]}',
                            "DUPLICATE_JSON_KEY")

    def test_invalid_schema_rejected(self):
        for s in ('{"values":[{"name":"Apfel","number":true},{"name":"Birne","number":26}]}',
                  '{"values":[{"name":"Apfel","number":14.0},{"name":"Birne","number":26}]}',
                  '{"values":[{"name":"Apfel","number":14},{"name":"Birne","number":26}],"x":1}',
                  '{"values":[{"name":"Apfel","number":14}]}',
                  '{"values":[{"name":"Apfel","number":14},{"name":"Birne","number":NaN}]}'):
            with self.subTest(s=s):
                self.assert_abstain("Apfel 14; Birne 26. Summe?", s)

    def test_no_live_or_model_import(self):
        self.assertEqual(AUTHORITY, "SHADOW_ONLY")
        self.assertTrue(verify_name_number_bindings("Apfel 14; Birne 26",
                                                    parse_typed(raw(("Apfel", 14), ("Birne", 26)))))


if __name__ == "__main__":
    unittest.main()
