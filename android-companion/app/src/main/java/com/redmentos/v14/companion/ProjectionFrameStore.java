package com.redmentos.v14.companion;

import android.net.Uri;

import org.json.JSONObject;

import java.security.MessageDigest;
import java.util.Arrays;

/** One-shot in-memory frame handoff. No screenshot bytes are written to disk or SQLite. */
final class ProjectionFrameStore {
    static final int MAX_FRAME_BYTES = 8 * 1024 * 1024;
    static final long TTL_MS = 20_000L;
    private static final Object LOCK = new Object();

    private static byte[] frame;
    private static JSONObject receipt;
    private static String token;
    private static long expiresAtElapsed;

    private ProjectionFrameStore() {}

    static void publish(byte[] bytes, JSONObject signedReceipt, long nowElapsed) throws Exception {
        if (bytes == null || bytes.length < 1 || bytes.length > MAX_FRAME_BYTES
                || signedReceipt == null || nowElapsed < 0) {
            throw new IllegalArgumentException("invalid one-shot frame");
        }
        JSONObject body = signedReceipt.getJSONObject("body");
        String nextToken = body.getString("frame_token");
        String digest = Canonical.hex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if (!"v14.android-ui-frame-receipt/1".equals(body.getString("schema"))
                || !nextToken.matches("[0-9a-f]{32}")
                || body.getInt("frame_bytes") != bytes.length
                || !digest.equals(body.getString("frame_sha256"))
                || body.getBoolean("raw_capture_persisted")
                || body.getBoolean("action_authority")
                || body.getBoolean("learning_authority")) {
            throw new SecurityException("frame receipt does not bind the exact non-authoritative bytes");
        }
        synchronized (LOCK) {
            clearLocked();
            frame = bytes;
            receipt = new JSONObject(signedReceipt.toString());
            token = nextToken;
            expiresAtElapsed = nowElapsed + TTL_MS;
        }
    }

    static JSONObject status(long nowElapsed) throws Exception {
        synchronized (LOCK) {
            if (frame == null) return response("NO_FRAME");
            if (nowElapsed < 0 || nowElapsed >= expiresAtElapsed) {
                clearLocked();
                return response("EXPIRED");
            }
            JSONObject out = response("FRAME_READY");
            out.put("receipt", new JSONObject(receipt.toString()));
            out.put("frame_uri", "content://" + CompanionProvider.AUTHORITY + "/ui-frame/" + token);
            out.put("expires_in_ms", expiresAtElapsed - nowElapsed);
            return out;
        }
    }

    static byte[] consume(String requestedToken, long nowElapsed) {
        synchronized (LOCK) {
            if (frame == null || token == null || requestedToken == null
                    || !token.equals(requestedToken) || nowElapsed < 0
                    || nowElapsed >= expiresAtElapsed) {
                if (frame != null && nowElapsed >= expiresAtElapsed) clearLocked();
                return null;
            }
            byte[] result = frame;
            frame = null;
            receipt = null;
            token = null;
            expiresAtElapsed = 0L;
            return result;
        }
    }

    static void clear() {
        synchronized (LOCK) { clearLocked(); }
    }

    static boolean hasFrame(long nowElapsed) {
        synchronized (LOCK) {
            if (frame != null && nowElapsed >= expiresAtElapsed) clearLocked();
            return frame != null;
        }
    }

    private static JSONObject response(String status) throws Exception {
        JSONObject out = new JSONObject();
        out.put("status", status);
        out.put("learning_authority", false);
        out.put("action_authority", false);
        return out;
    }

    private static void clearLocked() {
        if (frame != null) Arrays.fill(frame, (byte) 0);
        frame = null;
        receipt = null;
        token = null;
        expiresAtElapsed = 0L;
    }
}
