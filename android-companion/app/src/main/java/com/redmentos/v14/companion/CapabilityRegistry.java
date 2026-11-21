package com.redmentos.v14.companion;

import android.content.Context;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Typed inventory of native Android capabilities.
 *
 * A capability is advertised as ready only when its provider exists and the
 * companion's own stop/pairing state permits it. The only implemented
 * capability is an explicitly approved PackageManager launch intent. It does
 * not observe foreground state and never grants model or learning authority.
 */
final class CapabilityRegistry {
    private CapabilityRegistry() {}

    static final class Capability {
        final String id;
        final String status;
        final String reason;
        final String provider;
        final boolean perActionConsent;
        final boolean androidOsPermissionRequired;
        final boolean resultObserved;
        final boolean learningAuthority;

        Capability(
                String id,
                String status,
                String reason,
                String provider,
                boolean perActionConsent,
                boolean androidOsPermissionRequired,
                boolean resultObserved,
                boolean learningAuthority) {
            this.id = id;
            this.status = status;
            this.reason = reason;
            this.provider = provider;
            this.perActionConsent = perActionConsent;
            this.androidOsPermissionRequired = androidOsPermissionRequired;
            this.resultObserved = resultObserved;
            this.learningAuthority = learningAuthority;
        }
    }

    static String launchStatus(boolean paired, boolean enabled) {
        if (!paired) return "OFF_TERMUX_NOT_PAIRED";
        return enabled ? "READY_WITH_PER_ACTION_CONSENT" : "OFF_STOP_SWITCH";
    }

    static List<Capability> entries(boolean paired, boolean enabled) {
        return Collections.unmodifiableList(Arrays.asList(
                new Capability(
                        "launch_app",
                        launchStatus(paired, enabled),
                        "Explicit foreground approval; dispatch is not foreground observation",
                        "PACKAGE_MANAGER_LAUNCH_INTENT",
                        true,
                        false,
                        false,
                        false),
                unavailable("observe_ui", "No AccessibilityService or UI-tree provider"),
                unavailable("screen_capture", "No MediaProjection consent flow"),
                unavailable("tap", "Accessibility fallback is not implemented"),
                unavailable("swipe", "Accessibility fallback is not implemented"),
                unavailable("type_text", "Accessibility fallback is not implemented"),
                unavailable("back", "Accessibility fallback is not implemented")
        ));
    }

    private static Capability unavailable(String id, String reason) {
        return new Capability(id, "OFF_NOT_IMPLEMENTED", reason, "NONE",
                false, false, false, false);
    }

    static JSONObject snapshot(Context context) throws Exception {
        android.content.SharedPreferences prefs =
                context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE);
        boolean enabled = prefs.getBoolean("enabled", false);
        boolean paired = "com.termux".equals(prefs.getString("paired_package", ""))
                && !prefs.getString("paired_cert_sha256", "").isEmpty();

        JSONArray items = new JSONArray();
        for (Capability capability : entries(paired, enabled)) {
            items.put(item(capability));
        }

        JSONObject result = new JSONObject();
        result.put("schema", "v14.android-capability-registry/1");
        result.put("android_api", Build.VERSION.SDK_INT);
        result.put("enabled", enabled);
        result.put("termux_paired", paired);
        result.put("capabilities", items);
        result.put("network_enabled", false);
        result.put("shell_enabled", false);
        result.put("model_authority", false);
        return result;
    }

    private static JSONObject item(Capability capability) throws Exception {
        JSONObject value = new JSONObject();
        value.put("capability", capability.id);
        value.put("status", capability.status);
        value.put("reason", capability.reason);
        value.put("provider", capability.provider);
        value.put("per_action_consent", capability.perActionConsent);
        value.put("android_os_permission_required", capability.androidOsPermissionRequired);
        value.put("result_observed", capability.resultObserved);
        value.put("learning_authority", capability.learningAuthority);
        return value;
    }
}
