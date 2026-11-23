package com.redmentos.v14.companion;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
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
    interface CertificateDigestReader {
        String read(Context context, String packageName) throws Exception;
    }

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
                unavailable("audio_capture",
                        "No one-shot visible AudioRecord provider; capture remains disabled", true),
                unavailable("observe_ui", "No AccessibilityService or UI-tree provider"),
                unavailable("screen_capture", "No MediaProjection consent flow"),
                unavailable("tap", "Accessibility fallback is not implemented"),
                unavailable("swipe", "Accessibility fallback is not implemented"),
                unavailable("type_text", "Accessibility fallback is not implemented"),
                unavailable("back", "Accessibility fallback is not implemented")
        ));
    }

    private static Capability unavailable(String id, String reason) {
        return unavailable(id, reason, false);
    }

    private static Capability unavailable(String id, String reason, boolean osPermissionRequired) {
        return new Capability(id, "OFF_NOT_IMPLEMENTED", reason, "NONE",
                false, osPermissionRequired, false, false);
    }

    static boolean isCurrentTermuxTrusted(Context context) {
        return isCurrentTermuxTrusted(context, CompanionProvider::packageCertificateDigest);
    }

    static boolean isCurrentTermuxTrusted(Context context, CertificateDigestReader reader) {
        if (context == null || reader == null) return false;
        return PairingPersistence.withTrustedPairing(() -> {
            try {
                SharedPreferences prefs =
                        context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE);
                String packageName = prefs.getString("paired_package", "");
                String storedDigest = prefs.getString("paired_cert_sha256", "");
                if (!"com.termux".equals(packageName) || !isSha256(storedDigest)) return false;

                // A stored preference is only a claim. Verify the signer of the
                // currently installed package before advertising caller trust.
                String installedDigest = reader.read(context, packageName);
                if (!isSha256(installedDigest)) return false;
                return MessageDigest.isEqual(
                        storedDigest.getBytes(StandardCharsets.US_ASCII),
                        installedDigest.getBytes(StandardCharsets.US_ASCII));
            } catch (Exception unavailable) {
                // Missing/unreadable/re-signed Termux must fail closed in status.
                return false;
            }
        });
    }

    private static boolean isSha256(String value) {
        return value != null && value.matches("[0-9a-f]{64}");
    }

    static JSONObject snapshot(Context context) throws Exception {
        return snapshot(context, CompanionProvider::packageCertificateDigest);
    }

    static JSONObject snapshot(Context context, CertificateDigestReader reader) throws Exception {
        boolean enabled = CompanionProvider.isEnabled(context);
        boolean paired = isCurrentTermuxTrusted(context, reader);

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
