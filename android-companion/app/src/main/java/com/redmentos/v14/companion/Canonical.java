package com.redmentos.v14.companion;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

final class Canonical {
    private Canonical() {}

    static String requestDigest(String capability, String packageName) throws Exception {
        if (!"launch_app".equals(capability)) throw new IllegalArgumentException("unsupported capability");
        String json = "{\"args\":{\"package\":" + quote(packageName)
                + "},\"capability\":\"launch_app\"}";
        return hex(MessageDigest.getInstance("SHA-256").digest(json.getBytes(StandardCharsets.UTF_8)));
    }

    static String json(Map<String, Object> values) {
        List<String> keys = new ArrayList<>(values.keySet());
        Collections.sort(keys);
        StringBuilder out = new StringBuilder("{");
        boolean first = true;
        for (String key : keys) {
            if (!first) out.append(',');
            first = false;
            out.append(quote(key)).append(':');
            Object value = values.get(key);
            if (value instanceof String) out.append(quote((String) value));
            else if (value instanceof Boolean || value instanceof Number) out.append(value.toString());
            else throw new IllegalArgumentException("receipt values must be scalar");
        }
        return out.append('}').toString();
    }

    private static String quote(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\b': out.append("\\b"); break;
                case '\f': out.append("\\f"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20 || c > 0x7e) {
                        out.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        return out.append('"').toString();
    }

    static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) out.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
        return out.toString();
    }
}
