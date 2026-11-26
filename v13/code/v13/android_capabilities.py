"""Strict typed parser for the Android companion's native capability inventory.

The companion is the source of capability availability. Termux validates the
complete signed-transport snapshot before any dispatch; unknown, missing or
authority-escalated entries fail closed. A READY entry is still only an
advertisement: each action requires the existing local and Android UI consent.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass


SCHEMA = "v14.android-capability-registry/1"
CAPABILITY_IDS = (
    "launch_app",
    "audio_capture",
    "observe_ui",
    "screen_capture",
    "tap",
    "swipe",
    "type_text",
    "back",
)
_TOP_FIELDS = frozenset({
    "schema",
    "android_api",
    "enabled",
    "termux_paired",
    "capabilities",
    "network_enabled",
    "shell_enabled",
    "model_authority",
})
_ITEM_FIELDS = frozenset({
    "capability",
    "status",
    "reason",
    "provider",
    "per_action_consent",
    "android_os_permission_required",
    "result_observed",
    "learning_authority",
})
_READY = "READY_WITH_PER_ACTION_CONSENT"
_READY_SESSION_OS = "READY_WITH_PER_SESSION_OS_CONSENT"
_OFF_STOP = "OFF_STOP_SWITCH"
_OFF_UNPAIRED = "OFF_TERMUX_NOT_PAIRED"
_OFF_NOT_IMPLEMENTED = "OFF_NOT_IMPLEMENTED"


class CapabilityRegistryError(ValueError):
    """The companion capability inventory is malformed or authority-escalated."""


@dataclass(frozen=True)
class Capability:
    capability: str
    status: str
    reason: str
    provider: str
    per_action_consent: bool
    android_os_permission_required: bool
    result_observed: bool
    learning_authority: bool


@dataclass(frozen=True)
class CapabilityRegistry:
    android_api: int
    enabled: bool
    termux_paired: bool
    capabilities: tuple[Capability, ...]
    network_enabled: bool
    shell_enabled: bool
    model_authority: bool

    @classmethod
    def parse(cls, raw: object) -> "CapabilityRegistry":
        if not isinstance(raw, Mapping) or set(raw) != _TOP_FIELDS:
            raise CapabilityRegistryError("registry top-level schema mismatch")
        if raw["schema"] != SCHEMA:
            raise CapabilityRegistryError("unsupported registry schema")
        api = raw["android_api"]
        if type(api) is not int or not 1 <= api <= 100:
            raise CapabilityRegistryError("invalid Android API level")
        for key in (
            "enabled",
            "termux_paired",
            "network_enabled",
            "shell_enabled",
            "model_authority",
        ):
            if type(raw[key]) is not bool:
                raise CapabilityRegistryError("invalid boolean: " + key)
        if raw["network_enabled"] or raw["shell_enabled"] or raw["model_authority"]:
            raise CapabilityRegistryError("companion hard boundary is not closed")

        items = raw["capabilities"]
        if not isinstance(items, list) or len(items) != len(CAPABILITY_IDS):
            raise CapabilityRegistryError("capability inventory size mismatch")

        by_id: dict[str, Capability] = {}
        for item in items:
            if not isinstance(item, Mapping) or set(item) != _ITEM_FIELDS:
                raise CapabilityRegistryError("capability entry schema mismatch")
            cap_id = item["capability"]
            if type(cap_id) is not str or cap_id not in CAPABILITY_IDS or cap_id in by_id:
                raise CapabilityRegistryError("unknown or duplicate capability")
            status = item["status"]
            if type(status) is not str or status not in {
                _READY,
                _READY_SESSION_OS,
                _OFF_STOP,
                _OFF_UNPAIRED,
                _OFF_NOT_IMPLEMENTED,
            }:
                raise CapabilityRegistryError("unknown capability status")
            reason = item["reason"]
            provider = item["provider"]
            if type(reason) is not str or not reason or len(reason) > 512:
                raise CapabilityRegistryError("invalid capability reason")
            if type(provider) is not str or not provider or len(provider) > 96:
                raise CapabilityRegistryError("invalid capability provider")
            for key in (
                "per_action_consent",
                "android_os_permission_required",
                "result_observed",
                "learning_authority",
            ):
                if type(item[key]) is not bool:
                    raise CapabilityRegistryError("invalid capability boolean: " + key)
            by_id[cap_id] = Capability(
                capability=cap_id,
                status=status,
                reason=reason,
                provider=provider,
                per_action_consent=item["per_action_consent"],
                android_os_permission_required=item["android_os_permission_required"],
                result_observed=item["result_observed"],
                learning_authority=item["learning_authority"],
            )

        if set(by_id) != set(CAPABILITY_IDS):
            raise CapabilityRegistryError("capability inventory incomplete")

        launch = by_id["launch_app"]
        expected_status = (
            _OFF_UNPAIRED
            if not raw["termux_paired"]
            else (_READY if raw["enabled"] else _OFF_STOP)
        )
        if (
            launch.status != expected_status
            or launch.provider != "PACKAGE_MANAGER_LAUNCH_INTENT"
            or launch.per_action_consent is not True
            or launch.android_os_permission_required is not False
            or launch.result_observed is not False
            or launch.learning_authority is not False
        ):
            raise CapabilityRegistryError("launch_app contract mismatch")

        screen_capture = by_id["screen_capture"]
        media_projection_present = screen_capture.provider == "MEDIA_PROJECTION_ONE_SHOT"
        if media_projection_present:
            expected_capture_status = (
                _OFF_UNPAIRED
                if not raw["termux_paired"]
                else (_READY_SESSION_OS if raw["enabled"] else _OFF_STOP)
            )
            if (
                screen_capture.status != expected_capture_status
                or screen_capture.per_action_consent is not True
                or screen_capture.android_os_permission_required is not True
                or screen_capture.result_observed is not True
                or screen_capture.learning_authority is not False
            ):
                raise CapabilityRegistryError("screen_capture contract mismatch")
        elif screen_capture.provider != "NONE":
            raise CapabilityRegistryError("screen_capture provider mismatch")

        for cap_id in CAPABILITY_IDS[1:]:
            if cap_id == "screen_capture" and media_projection_present:
                continue
            capability = by_id[cap_id]
            expected_os_permission = cap_id == "audio_capture"
            if (
                capability.status != _OFF_NOT_IMPLEMENTED
                or capability.provider != "NONE"
                or capability.per_action_consent is not False
                or capability.android_os_permission_required is not expected_os_permission
                or capability.result_observed is not False
                or capability.learning_authority is not False
            ):
                raise CapabilityRegistryError(
                    "unimplemented capability is not fail-closed: " + cap_id
                )

        return cls(
            android_api=api,
            enabled=raw["enabled"],
            termux_paired=raw["termux_paired"],
            capabilities=tuple(by_id[name] for name in CAPABILITY_IDS),
            network_enabled=raw["network_enabled"],
            shell_enabled=raw["shell_enabled"],
            model_authority=raw["model_authority"],
        )

    def capability(self, name: str) -> Capability | None:
        return next((item for item in self.capabilities if item.capability == name), None)

    def require_ready(self, name: str) -> Capability:
        """Validate advertised availability only; never request OS consent or dispatch an action."""
        capability = self.capability(name)
        expected_status = {
            "launch_app": _READY,
            "screen_capture": _READY_SESSION_OS,
        }.get(name)
        if (
            capability is None
            or expected_status is None
            or capability.status != expected_status
            or not self.enabled
            or not self.termux_paired
        ):
            raise CapabilityRegistryError(
                "companion must be paired and enabled and capability ready: " + name
            )
        if name == "launch_app" and (
            capability.per_action_consent is not True
            or capability.android_os_permission_required is not False
            or capability.result_observed is not False
            or capability.learning_authority is not False
        ):
            raise CapabilityRegistryError("launch_app authority contract mismatch")
        if name == "screen_capture" and (
            capability.per_action_consent is not True
            or capability.android_os_permission_required is not True
            or capability.result_observed is not True
            or capability.learning_authority is not False
        ):
            raise CapabilityRegistryError("screen_capture authority contract mismatch")
        return capability

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "android_api": self.android_api,
            "enabled": self.enabled,
            "termux_paired": self.termux_paired,
            "capabilities": [asdict(item) for item in self.capabilities],
            "network_enabled": self.network_enabled,
            "shell_enabled": self.shell_enabled,
            "model_authority": self.model_authority,
        }
