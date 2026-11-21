package com.redmentos.v14.companion;

import android.util.Base64;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

final class Canonical {
    private Canonical() {}

    static String requestDigest(String capability, String packageName) throws Exception {
        if (!"launch_app".equals(capability)) throw new IllegalArgumentException("unsupported capability");
        String json = "{\"args\":{\"package\":" + JSONObject.quote(packageName)
                + "},\"capability\":\"launch_app\"}";
        return hex(MessageDigest.getInstance("SHA-256").digest(json.getBytes(StandardCharsets.UTF_8)));
    }

    static String json(JSONObject object) throws Exception {
        List<String> keys = new ArrayList<>();
        for (java.util.Iterator<String> it = object.keys(); it.hasNext();) keys.add(it.next());
        Collections.sort(keys);
        StringBuilder out = new StringBuilder("{");
        boolean first = true;
        for (String key : keys) {
            if (!first) out.append(',');
            first = false;
            out.append(JSONObject.quote(key)).append(':');
            Object value = object.get(key);
            if (value instanceof String) out.append(JSONObject.quote((String) value));
            else if (value instanceof Boolean || value instanceof Number) out.append(value.toString());
            else throw new IllegalArgumentException("receipt values must be scalar");
        }
        return out.append('}').toString();
    }

    static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) out.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
        return out.toString();
    }

    static byte[] base64(String value) {
        return Base64.decode(value, Base64.DEFAULT);
    }
}
