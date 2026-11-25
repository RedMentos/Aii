package com.redmentos.v14.companion;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

final class Canonical {
    private Canonical() {}

    static String requestDigest(String capability, String target) throws Exception {
        final String json;
        if ("launch_app".equals(capability)) {
            json = "{\"args\":{\"package\":" + quote(target)
                    + "},\"capability\":\"launch_app\"}";
        } else if ("open_url".equals(capability)) {
            if (!isSafeHttpsUrl(target)) throw new IllegalArgumentException("unsafe HTTPS URL");
            json = "{\"args\":{\"url\":" + quote(target)
                    + "},\"capability\":\"open_url\"}";
        } else {
            throw new IllegalArgumentException("unsupported capability");
        }
        return hex(MessageDigest.getInstance("SHA-256").digest(json.getBytes(StandardCharsets.UTF_8)));
    }

    static boolean isSafeHttpsUrl(String value) {
        if (value == null || value.length() < 9 || value.length() > 2048
                || !value.startsWith("https://") || value.indexOf('\\') >= 0
                || value.matches(".*%(?![0-9A-Fa-f]{2}).*")) return false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c <= 0x20 || c >= 0x7f) return false;
        }
        try {
            URI uri = new URI(value);
            String authority = uri.getRawAuthority();
            String host = uri.getHost();
            int port = uri.getPort();
            return "https".equals(uri.getScheme())
                    && authority != null && !authority.isEmpty()
                    && host != null && host.length() <= 253
                    && uri.getRawUserInfo() == null
                    && (port == -1 || port == 443)
                    && !authority.endsWith(":")
                    && authority.indexOf('%') < 0;
        } catch (URISyntaxException invalid) {
            return false;
        }
    }

    static String httpsHost(String value) {
        if (!isSafeHttpsUrl(value)) throw new IllegalArgumentException("unsafe HTTPS URL");
        try {
            return new URI(value).getHost().toLowerCase(Locale.ROOT);
        } catch (URISyntaxException impossibleAfterValidation) {
            throw new IllegalArgumentException("unsafe HTTPS URL", impossibleAfterValidation);
        }
    }

    static String osPermissionStatus(String capability) {
        if ("launch_app".equals(capability)) return "NOT_REQUIRED_FOR_LAUNCH_APP";
        if ("open_url".equals(capability)) return "NOT_REQUIRED_FOR_OPEN_URL";
        throw new IllegalArgumentException("unsupported capability");
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
