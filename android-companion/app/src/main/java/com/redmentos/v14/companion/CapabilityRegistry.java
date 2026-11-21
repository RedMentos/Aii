package com.redmentos.v14.companion;

import android.content.Context;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

final class CapabilityRegistry {
    private CapabilityRegistry() {}

    static JSONObject snapshot(Context context) throws Exception {
        boolean enabled = context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE)
                .getBoolean("enabled", false);
        JSONArray items = new JSONArray();
        items.put(item("launch_app", enabled ? "READY_WITH_PER_ACTION_CONSENT" : "OFF_STOP_SWITCH",
                "Explicit foreground approval; dispatch is not foreground observation"));
        items.put(item("observe_ui", "OFF_NOT_IMPLEMENTED", "No AccessibilityService or UI-tree provider"));
        items.put(item("screen_capture", "OFF_NOT_IMPLEMENTED", "No MediaProjection consent flow"));
        items.put(item("tap", "OFF_NOT_IMPLEMENTED", "Accessibility fallback is not implemented"));
        items.put(item("swipe", "OFF_NOT_IMPLEMENTED", "Accessibility fallback is not implemented"));
        items.put(item("type_text", "OFF_NOT_IMPLEMENTED", "Accessibility fallback is not implemented"));
        items.put(item("back", "OFF_NOT_IMPLEMENTED", "Accessibility fallback is not implemented"));
        JSONObject result = new JSONObject();
        result.put("schema", "v14.android-capability-registry/1");
        result.put("android_api", Build.VERSION.SDK_INT);
        result.put("enabled", enabled);
        result.put("capabilities", items);
        result.put("network_enabled", false);
        result.put("shell_enabled", false);
        result.put("model_authority", false);
        return result;
    }

    private static JSONObject item(String id, String status, String reason) throws Exception {
        JSONObject value = new JSONObject();
        value.put("capability", id);
        value.put("status", status);
        value.put("reason", reason);
        return value;
    }
}
