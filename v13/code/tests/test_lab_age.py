"""Synthetic, read/write boundary tests for independent laboratory Age 0–10."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

from v13 import lab_age, effort
from v13.age import AgeControl
from v13.lab_age_runtime import LaboratoryAgeControl
from v13.config import initialize
from v13.store import Store
from test_goal_wake_atomicity_20261121 import GoalWakeAtomicityTests
from v13.agi.curiosity import Curiosity
from v13.agi.goals import GoalStore, MAX_DEPTH
from v13.agi.base import learning_limit


class LabAgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.age = AgeControl(self.store, self.cfg)
        self.lab = LaboratoryAgeControl(self.store, self.cfg)

    def test_initially_owner_requested_level_ten_active_and_official_age_zero(self):
        v = lab_age.view(self.home, official_stage=self.age.system_stage())
        self.assertEqual(v["stage"], 10)
        self.assertEqual(v["mode"], "active")
        self.assertTrue(v["feature_test_requested"])
        self.assertFalse(v["compute_requested"])
        self.assertFalse(v["config_persisted"])
        self.assertTrue(v["test_only"])
        self.assertEqual(self.age.view()["system_stage"], 0)
        current = effort.age_limits(self.lab)
        self.assertEqual(current["stage"], 0)
        # Runtime compute is independent of Age; the default X10 lab exposes test rights only.
        self.assertEqual(current["focal_depth"], 3)
        self.assertEqual(current["autonomous_effort_max"], "max")
        self.assertTrue(current["tools"])
        self.assertTrue(current["deliberation"])
        self.assertTrue(current["long_loops"])
        self.assertTrue(current["lab_feature_test_requested"])
        self.assertFalse(current["lab_compute_active"])
        self.assertEqual(current["lab_compute_gate"], "NOT_A_COMPUTE_SETTING")

    def test_active_level_ten_does_not_change_compute_or_earned_permissions(self):
        lab_age.save(self.home, mode="active", stage=10)
        limits = effort.age_limits(self.lab)
        self.assertEqual(limits["stage"], 0)
        self.assertEqual(limits["lab_stage"], 10)
        self.assertTrue(limits["lab_feature_test_requested"])
        self.assertFalse(limits["lab_compute_active"])
        self.assertEqual(limits["autonomous_effort_max"], "max")
        self.assertEqual(limits["focal_depth"], 3)
        self.assertTrue(limits["tools"])
        self.assertTrue(limits["deliberation"])
        self.assertTrue(limits["long_loops"])
        self.assertFalse(self.age.may("simple_tool_choice"))  # official Age remains 0
        self.assertTrue(self.lab.may("simple_tool_choice"))
        self.assertFalse(self.lab.may("body_swap"))  # structural lock still wins
        status = self.lab.rights()
        self.assertEqual(status["official_stage"], 0)
        self.assertEqual(status["lab_effective_implemented_stage"], 5)
        self.assertTrue(status["test_only"])
        self.assertTrue(status["experiment_feature_rights_only"])
        self.assertFalse(self.lab.allowed("simple_tool_choice", hard_rule_block=True))
        self.assertFalse(self.lab.allowed("simple_tool_choice", user_permissions={"direct_route"}))
        self.assertFalse(self.lab.may("long_loops", resource_mode="RED"))
        self.lab.lock_structural(False)
        self.assertTrue(self.lab.may("body_swap"))
        self.assertEqual(self.age.view()["system_stage"], 0)
        hard = effort.signals("Vergleiche A und B für mein Budget", "both",
                              {"source": "BOOT_SCAFFOLD", "scaffold": "both"})
        plan = effort.decide("max", hard, age=limits, cfg={"max_reentry":2,"focal_slots":4})
        self.assertEqual(plan["age_stage"], 0)
        self.assertEqual(plan["lab_stage"], 10)
        self.assertEqual(plan["focal_cycles"], 3)
        self.assertTrue(plan["verify"])
        self.assertEqual(plan["tool_steps"], 1)

    def test_off_and_shadow_return_earned_age_limits(self):
        for mode in ("off", "shadow"):
            lab_age.save(self.home, mode=mode, stage=10)
            a = effort.age_limits(self.lab)
            self.assertFalse(a["lab_compute_active"])
            self.assertEqual(a["focal_depth"], 3)
            self.assertEqual(a["autonomous_effort_max"], "max")
            self.assertFalse(a["tools"])
            self.assertFalse(a["deliberation"])
            self.assertFalse(a["long_loops"])
        lab_age.save(self.home, mode="active", stage=0)
        self.assertFalse(effort.age_limits(self.lab)["lab_compute_active"])

    def test_resource_guard_does_not_change_lab_feature_selection(self):
        lab_age.save(self.home, mode="active", stage=10)
        observed = effort.age_limits(self.lab, "CRITICAL")
        self.assertFalse(observed["lab_compute_active"])
        self.assertEqual(observed["lab_compute_gate"], "NOT_A_COMPUTE_SETTING")
        self.assertTrue(observed["lab_feature_test_requested"])
        self.assertEqual(observed["focal_depth"], 3)
        self.assertEqual(observed["autonomous_effort_max"], "max")
        self.assertTrue(observed["tools"])
        self.assertFalse(observed["long_loops"])  # RED resource mode still blocks long loops

    def test_invalid_or_symlink_configuration_fails_closed(self):
        path = self.home / "config/lab-age.json"
        path.write_text('{"schema":"v13.lab-age/1","stage":10,"mode":"invalid"}')
        self.assertEqual(lab_age.read(self.home)["mode"], "off")
        path.unlink()
        external = self.home / "external.json"
        external.write_text("private")
        path.symlink_to(external)
        self.assertEqual(lab_age.read(self.home)["mode"], "off")
        with self.assertRaises(ValueError):
            lab_age.save(self.home, mode="active", stage=10)
        self.assertEqual(external.read_text(), "private")

    def test_out_of_bounds_and_bad_types_rejected(self):
        for x in (11, -1, 4.5, True, "10"):
            with self.assertRaises(ValueError):
                lab_age.save(self.home, stage=x)
        with self.assertRaises(ValueError):
            lab_age.save(self.home, mode="unlock_permissions")
        self.assertFalse((self.home / "config/lab-age.json").exists())

    def test_lab_rights_are_testable_without_promoting_official_age(self):
        for level in (0, 3, 7, 10):
            with self.subTest(level=level):
                lab_age.save(self.home, mode="active", stage=level)
                green = effort.age_limits(self.lab, "GREEN")
                red = effort.age_limits(self.lab, "CRITICAL")
                self.assertEqual(green["stage"], 0)
                self.assertEqual(green["lab_stage"], level)
                self.assertEqual(red["lab_stage"], level)
                self.assertEqual(red["stage"], 0)
                self.assertFalse(green["lab_compute_active"])
                self.assertEqual(green["lab_feature_test_requested"], level > 0)
                self.assertFalse(red["lab_compute_active"])
                self.assertEqual(green["tools"], level >= 1)
                self.assertEqual(red["tools"], level >= 1)
                self.assertEqual(green["long_loops"], level >= 3)
                self.assertFalse(red["long_loops"])  # resource veto is independent
                self.assertFalse(self.lab.may("body_swap"))  # structural lock is independent
                self.assertFalse(self.age.may("simple_tool_choice"))
                self.assertEqual(self.lab.may("simple_tool_choice"), level >= 1)
                self.assertFalse(self.lab.may("long_loops", resource_mode="RED"))
                self.assertEqual(self.cfg["learning_mode"], "RECORD_ONLY")

    def test_config_persists_reversible_with_private_permissions(self):
        result = lab_age.save(self.home, mode="active", stage=7)
        self.assertEqual(result["mode"], "active")
        self.assertEqual(lab_age.read(self.home)["stage"], 7)
        self.assertTrue(lab_age.view(self.home)["config_persisted"])
        self.assertEqual((self.home / "config/lab-age.json").stat().st_mode & 0o077, 0)
        lab_age.save(self.home, mode="off")
        self.assertFalse(effort.age_limits(self.lab)["lab_compute_active"])
        self.assertEqual(self.age.view()["system_stage"], 0)


    def test_explicit_shadow_learning_is_scoped_and_never_commits(self):
        lab_age.save(self.home, mode="active", stage=10)
        trial = lab_age.LabConfig(self.cfg, self.home)
        self.assertEqual(trial["learning_mode"], "RECORD_ONLY")
        with trial.shadow_training():
            self.assertEqual(trial["learning_mode"], "SHADOW_UPDATE")
        self.assertEqual(trial["learning_mode"], "RECORD_ONLY")

    def test_sleep_replay_batch_is_resource_limited_not_age_limited(self):
        from unittest.mock import Mock
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                cycle = runtime.sleep.cycle
                cycle.age.budgets = Mock(side_effect=AssertionError("Age must not supply replay budgets"))
                policy = cycle.policy()
                seen = {}
                def fake_sleep_a(st, policy_value, n, cancel, deadline, resource, **kwargs):
                    seen["n"] = n
                    return {"phase": "SLEEP_A", "status": "DONE", "selected": 0}
                cycle.sleep_a = fake_sleep_a
                report = cycle.run("wake", resource=lambda: "GREEN", origin="AUTO")
                self.assertEqual(seen["n"], policy["wake_batch"])
                self.assertEqual(report["replay_budget"], policy["wake_batch"])
                cycle.age.budgets.assert_not_called()
            finally:
                runtime.close()

    
    def test_curiosity_uses_graded_learning_right_not_runtime_compute_budget(self):
        class AlwaysExplore:
            def random(self):
                return 0.0

        curiosity = Curiosity(self.store, self.age, rng=AlwaysExplore())
        curiosity.observe("math", 0.4)
        self.assertEqual(learning_limit(self.age, "exploration_rate", 0.0, capability="tool"), 0.0)
        self.assertIsNone(curiosity.choose(origin="SELF"))
        self.assertFalse(curiosity.report()["autonomous"])
        self.assertEqual(curiosity.choose(origin="USER"), "math")

        lab_age.save(self.home, mode="active", stage=10)
        lab = LaboratoryAgeControl(self.store, self.cfg)
        lab_curiosity = Curiosity(self.store, lab, rng=AlwaysExplore())
        lab_curiosity.observe("math", 0.4)
        self.assertGreater(learning_limit(lab, "exploration_rate", 0.0, capability="tool"), 0.0)
        self.assertEqual(lab_curiosity.choose(origin="SELF"), "math")
        self.assertTrue(lab_curiosity.report()["autonomous"])
        self.assertEqual(self.age.system_stage(), 0)

    def test_growth_practice_resource_guard_is_independent_of_lab_age(self):
        from v13.scheduler import EventScheduler

        lab_age.save(self.home, mode="active", stage=10)
        lab = LaboratoryAgeControl(self.store, self.cfg)
        self.assertTrue(lab.may("active_info_search"))
        self.assertFalse(lab.may("active_info_search", resource_mode="RED"))
        scheduler = EventScheduler(self.store, self.cfg, age=lab)
        scheduler.post("TIMER", origin="SYSTEM", action="growth_practice")

        self.assertIsNone(scheduler.next(idle=True, resource_state="PRESSURE"))
        self.assertIsNone(scheduler.next(idle=True, resource_state="CRITICAL"))
        event = scheduler.next(idle=True, resource_state="NORMAL")
        self.assertEqual(event["action"], "growth_practice")
        self.assertEqual(lab.system_stage(), 0)

    def test_goal_tree_depth_uses_a_named_right_not_focal_depth_budget(self):
        goals = GoalStore(self.store, self.age)
        system_root = goals.add("system root", origin="SYSTEM")
        system_child = goals.add("system child", origin="SYSTEM", parent=system_root)
        with self.assertRaises(ValueError):
            goals.add("system grandchild", origin="SYSTEM", parent=system_child)

        user_parent = goals.add("user root", origin="USER")
        for index in range(1, MAX_DEPTH):
            user_parent = goals.add(f"user child {index}", origin="USER", parent=user_parent)
        with self.assertRaises(ValueError):
            goals.add("user too deep", origin="USER", parent=user_parent)
        with self.assertRaises(PermissionError):
            goals.add("self root", origin="SELF")

        lab_age.save(self.home, mode="active", stage=10)
        lab = LaboratoryAgeControl(self.store, self.cfg)
        self.assertGreaterEqual(learning_limit(lab, "goal_depth", 1), MAX_DEPTH - 1)
        lab_goals = GoalStore(self.store, lab)
        self_parent = lab_goals.add("self root", origin="SELF")
        for index in range(1, MAX_DEPTH):
            self_parent = lab_goals.add(f"self child {index}", origin="SELF", parent=self_parent)
        with self.assertRaises(ValueError):
            lab_goals.add("self too deep", origin="SELF", parent=self_parent)
        self.assertEqual(lab_goals.get(self_parent)["origin"], "SELF")
        self.assertEqual(self.age.system_stage(), 0)

    def test_repository_wide_age_budget_consumer_inventory_is_closed(self):
        code_root = Path(__file__).resolve().parents[1]
        legacy_fields = {
            "autonomous_effort_max", "focal_depth", "dream_seconds",
            "replay_items", "context_edit_tokens", "exploration_rate", "own_loops",
        }
        expected_budget_attributes = {
            ("v13/age.py", "view", "self.budgets"),
            ("v13/lab_age_runtime.py", "budgets", "real.budgets"),
        }
        budget_attributes = []
        helper_calls = []
        helper_imports = []
        learning_limit_calls = []
        field_reads = []

        def dotted(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return dotted(node.value) + "." + node.attr
            return "<dynamic>"

        def enclosing_owner(node, parent_map):
            # Transaction/Store callbacks are nested implementation details.
            # Attribute a rights read to the public method that owns the callback.
            current = node
            owner = None
            while current in parent_map:
                current = parent_map[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    owner = current.name
            return owner or "<module>"

        # Negative control: nested callbacks belong to their enclosing method,
        # while an unrelated closure stays attributed to its own outer owner.
        probe = ast.parse(
            """
class GoalStore:
    def add(self):
        def f(st):
            return learning_limit('goal_depth')
        return f(None)
def unrelated():
    def f(st):
        return learning_limit('unrelated')
    return f(None)
"""
        )
        probe_parents = {}
        for parent in ast.walk(probe):
            for child in ast.iter_child_nodes(parent):
                probe_parents[child] = parent
        probe_calls = [
            node for node in ast.walk(probe)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "learning_limit"
        ]
        self.assertEqual(
            {enclosing_owner(node, probe_parents) for node in probe_calls},
            {"add", "unrelated"},
        )

        scan_roots = (code_root / "v13", code_root / "scripts")
        for scan_root in scan_roots:
            for path in sorted(scan_root.rglob("*.py")):
                relative = path.relative_to(code_root)
                if "__pycache__" in relative.parts:
                    continue
                try:
                    source = path.read_text(encoding="utf-8")
                    tree = ast.parse(source, filename=str(relative))
                except (OSError, SyntaxError) as exc:
                    self.fail(f"Could not audit {relative}: {type(exc).__name__}")
                parents = {}
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        parents[child] = parent

                def enclosing_function(node):
                    current = node
                    while current in parents:
                        current = parents[current]
                        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            return current.name
                    return "<module>"

                field_source = relative.as_posix() != "v13/age.py"
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute) and node.attr == "budgets":
                        budget_attributes.append(
                            (relative.as_posix(), enclosing_function(node), dotted(node))
                        )
                    if isinstance(node, ast.Call):
                        if "agi" in relative.parts and isinstance(node.func, ast.Name) and node.func.id == "budget":
                            helper_calls.append((relative.as_posix(), node.lineno))
                        if isinstance(node.func, ast.Name) and node.func.id == "learning_limit":
                            learning_limit_calls.append(
                                (relative.as_posix(), enclosing_owner(node, parents))
                            )
                        if field_source and (
                                isinstance(node.func, ast.Name) and node.func.id in {"getattr", "hasattr"}
                                and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)
                                and node.args[1].value in legacy_fields):
                            field_reads.append((relative.as_posix(), node.lineno, node.args[1].value))
                        if field_source and (
                                isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "pop"}
                                and node.args and isinstance(node.args[0], ast.Constant)
                                and node.args[0].value in legacy_fields):
                            field_reads.append((relative.as_posix(), node.lineno, node.args[0].value))
                    if field_source and isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                        if node.slice.value in legacy_fields:
                            field_reads.append((relative.as_posix(), node.lineno, node.slice.value))
                    if isinstance(node, ast.ImportFrom) and node.module:
                        is_agi_base = node.module.endswith("agi.base") or (
                            "agi" in relative.parts and node.module.endswith("base")
                        )
                        if is_agi_base and any(alias.name == "budget" for alias in node.names):
                            helper_imports.append((relative.as_posix(), node.lineno))
                    if field_source and isinstance(node, ast.Attribute) and node.attr in legacy_fields:
                        field_reads.append((relative.as_posix(), node.lineno, node.attr))

        self.assertEqual(
            set(budget_attributes), expected_budget_attributes,
            "Age budgets must be reporting/delegation only; inspect every new .budgets use",
        )
        self.assertEqual(helper_calls, [], "Legacy agi.base.budget() must have no runtime callers")
        self.assertEqual(helper_imports, [], "Runtime modules must not import the legacy budget helper")
        self.assertEqual(field_reads, [], "No runtime module may read a physical Age budget field")
        self.assertEqual(
            set(learning_limit_calls),
            {
                ("v13/agi/curiosity.py", "choose"),
                ("v13/agi/curiosity.py", "report"),
                ("v13/agi/goals.py", "add"),
            },
            "Only Curiosity and GoalStore may consume graded developmental learning/planning rights",
        )

        base_tree = ast.parse((code_root / "v13/agi/base.py").read_text(encoding="utf-8"))
        learning_limit = next(
            node for node in ast.walk(base_tree)
            if isinstance(node, ast.FunctionDef) and node.name == "learning_limit"
        )
        mapping_expr = next(
            node.value for node in ast.walk(learning_limit)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "source" for target in node.targets)
        )
        mapping = mapping_expr.func.value if (
            isinstance(mapping_expr, ast.Call)
            and isinstance(mapping_expr.func, ast.Attribute)
            and mapping_expr.func.attr == "get"
        ) else mapping_expr
        self.assertIsInstance(mapping, ast.Dict)
        self.assertEqual(
            {
                key.value: value.value
                for key, value in zip(mapping.keys, mapping.values)
                if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)
            },
            {"exploration_rate": "exploration_rate", "goal_depth": "focal_depth"},
            "Only graded exploration and goal-tree depth are developmental rights, not compute budgets",
        )


if __name__ == "__main__":
    unittest.main()
