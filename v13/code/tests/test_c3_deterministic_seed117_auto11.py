"""Frozen seed117 novel-source property study: narrow deterministic parser only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as cli
from v13.agi import listarith_de_deterministic_source_candidate as parser
from v13.agi import listarith_de_closedworld_candidate as closedworld

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "specs/c3_deterministic_seed117_manifest.json"
SHA = "8a9a35a1f12f992327c49f8efdfeb1fdcec2e945794fd36c5fe37930137332b2"


def generated():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["schema"] == "v13.c3.deterministic.seed117.manifest.v1"
    assert m["seed"] == 117 and m["count"] == 128
    assert m["source_texts_sha256"] == SHA
    rng = random.Random(117)
    rows = []
    for i in range(128):
        n = rng.randint(3, 6)
        names = rng.sample(m["names"], n)
        nums = [rng.randint(-99, 99) for _ in range(n)]
        label = m["labels"][i % 4]
        op = "total" if i % 2 == 0 else "difference_max_min"
        question = m["questions"][i % 2]
        text = (f"{label}: " +
                ", ".join(f"{name} {num}" for name, num in zip(names, nums)) +
                ". " + question)
        expected = sum(nums) if op == "total" else max(nums) - min(nums)
        values = [{"name": name, "number": num}
                  for name, num in zip(names, nums)]
        rows.append((text, label, names, nums, question, expected, op, values))
    assert hashlib.sha256("\n".join(r[0] for r in rows).encode()).hexdigest() == SHA
    return rows


def mutations(row):
    text, label, names, nums, q, _, _, _ = row
    first = f"{names[0]} {nums[0]}"
    second = f"{names[1]} {nums[1]}"
    return [
        text.replace(first, f"{names[0]} 1.5", 1),
        text.replace(second, f"{names[0].lower()} {nums[1]}", 1),
        text.replace(f"{label}:", f"{label} 2026:", 1),
        text.replace(", ", "; ", 1),
        text.replace(q, "Wie viele Einträge?", 1),
        text.replace(". " + q, ", Gesamt 123. " + q, 1),
        text.replace(first, f"{names[0]} 09", 1),
        text.replace(". " + q, " " + q, 1),
        text.replace(q, q[:-1] + " 2026?", 1),
        text.replace(q, "Bitte nicht summieren?", 1),
    ]


class DeterministicSeed117(unittest.TestCase):
    def test_128_new_sources_exact_and_closedworld_correct(self):
        rows = generated()
        self.assertEqual(len(rows), 128)
        self.assertEqual(len({r[0] for r in rows}), 128)
        for i, row in enumerate(rows):
            text, _, _, _, _, expected, op, values = row
            with self.subTest(index=i):
                raw = parser.extract(text)
                self.assertEqual(json.loads(raw)["values"], values)
                closed = closedworld.evaluate(text, raw)
                self.assertEqual(closed["status"], "SHADOW_RESULT")
                self.assertEqual(closed["operation"], op)
                self.assertEqual(closed["value"], expected)
                self.assertEqual(closed["input_count"], len(values))

    def test_1280_fixed_mutations_abstain_without_wrong_emissions(self):
        rows = generated()
        total = 0
        for i, row in enumerate(rows):
            for j, mutated in enumerate(mutations(row)):
                with self.subTest(index=i, mutation=j):
                    total += 1
                    try:
                        raw = parser.extract(mutated)
                    except ValueError:
                        continue
                    result = closedworld.evaluate(mutated, raw)
                    self.assertEqual(result["status"], "SHADOW_ABSTAIN")
        self.assertEqual(total, 1280)

    def test_12_new_sources_via_operator_cli_no_native_or_tool(self):
        rows = generated()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, row in enumerate(rows[:12]):
                source = root / f"source-{i}.txt"
                out = root / f"out-{i}.json"
                source.write_text(row[0], encoding="utf-8")
                with patch.object(cli, "_native_one",
                                  side_effect=AssertionError("NATIVE_FORBIDDEN")):
                    summary = cli.run(source, out, deterministic=True)
                report = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(summary["status"], "SHADOW_RESULT")
                self.assertEqual(report["closedworld"]["value"], row[5])
                self.assertFalse(report["native_attempted"])
                self.assertFalse(report["external_action_authority"])
                self.assertFalse(report["step2_gate_promoted"])
                self.assertFalse(report["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
