"""Laboratory Age gate adapter for a staged V13 runtime.

Not earned maturity. An owner-selected ACTIVE laboratory stage exercises the
implemented Age 0..5 capability/learning/tool gates *during the lab run* without
modifying the official developmental Age or evidence ledger. Stages 6..10 do
not invent nonexistent stage-6+ code; they exercise the fullest implemented
stage-5 gate set. Resources, hard prohibitions, explicit tool-call approval,
structural lock and RECORD_ONLY learning persistence remain independent gates.

The release builder injects this controller into the staged copy of age.py.
The frozen source/old phone updater are intentionally left unchanged.
"""
from __future__ import annotations

from .age import AgeControl, RIGHTS, RIGHT_CAPABILITY
from .lab_age import read


class LaboratoryAgeControl(AgeControl):
    """AgeControl with *virtual* feature gates, never virtual evidence."""

    def _laboratory(self):
        return read(self.s.home)

    def simulated_stage(self):
        setting = self._laboratory()
        if setting["mode"] != "active":
            return None
        return min(setting["stage"], 5)

    def ceiling(self, capability="system", st=None):
        # Used by the real AgeControl.allowed/may/rights/budgets paths, not
        # just as a fake dashboard report. Stage 0 disables the override.
        real = super().ceiling(capability, st)
        virtual = self.simulated_stage()
        if virtual is None or virtual == 0:
            return real
        if capability != "system":
            state = st if st is not None else self.state()[0]
            if capability not in state["capabilities"]:
                # No invented modality/organ.
                return real
        return max(real, virtual)

    def view(self):
        from .lab_age import view as lab_view
        official = super().view()
        lab = lab_view(self.s.home, official_stage=official["system_stage"])
        rights = self.rights()
        official["laboratory"] = dict(
            lab,
            effective_implemented_stage=self.simulated_stage(),
            effective_gate_rights=rights["granted"],
            effective_rights_count=len(rights["granted"]),
            official_age_unchanged=True,
            real_learning_mode=self.cfg.get("learning_mode", "UNKNOWN"),
            # This adapter removes *Age* learning prohibitions, not independent
            # record-only persistence policy. Never claim model learning works.
            learning_commit_blocked_by_record_only=(
                self.cfg.get("learning_mode") == "RECORD_ONLY"),
        )
        return official

    def rights(self, resource_mode="GREEN", user_permissions=None):
        output = super().rights(resource_mode, user_permissions)
        lab = self._laboratory()
        output["lab_mode"] = lab["mode"]
        output["lab_stage"] = lab["stage"]
        output["lab_effective_implemented_stage"] = self.simulated_stage()
        output["official_stage"] = self.system_stage()
        output["test_only"] = self.simulated_stage() is not None
        output["learning_commit_allowed"] = self.cfg.get("learning_mode") == "APPROVED_COMMIT"
        return output
