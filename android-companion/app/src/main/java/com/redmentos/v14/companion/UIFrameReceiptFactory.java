package com.redmentos.v14.companion;

import android.os.Build;

import org.json.JSONObject;

import java.security.MessageDigest;
import java.security.SecureRandom;

/** Signed receipt for one user-approved MediaProjection frame; never grants action or learning authority. */
final class UIFrameReceiptFactory {
    private UIFrameReceiptFactory() {}

    static JSONObject create(byte[] frame, int width, int height,
                             long startElapsedMs, long endElapsedMs,
                             ReceiptFactory.Signer signer) throws Exception {
        if (frame == null || frame.length < 1 || frame.length > ProjectionFrameStore.MAX_FRAME_BYTES
                || width < 1 || height < 1 || (long) width * height > 4_000_000L
                || startElapsedMs < 0 || endElapsedMs <= startElapsedMs
                || endElapsedMs - startElapsedMs > 5_000L || signer == null) {
            throw new IllegalArgumentException("invalid MediaProjection frame receipt input");
        }
        JSONObject key = signer.publicKeyInfo();
        long issuedAt = System.currentTimeMillis() / 1000L;
        String nonce = randomHex(16);
        JSONObject body = new JSONObject();
        body.put("schema", "v14.android-ui-frame-receipt/1");
        body.put("nonce", nonce);
        body.put("frame_token", randomHex(16));
        body.put("source_id", "ui-" + nonce);
        body.put("capture_session_id", "mp-" + nonce);
        body.put("consent_receipt_ref", "mp-" + nonce);
        body.put("capture_method", "MEDIA_PROJECTION");
        body.put("capture_scope", "FULL_DISPLAY");
        body.put("api_level", Build.VERSION.SDK_INT);
        body.put("clock", "ELAPSED_REALTIME");
        body.put("event_kind", "SCREEN_FRAME_AVAILABLE");
        body.put("start_ms", startElapsedMs);
        body.put("end_ms", endElapsedMs);
        body.put("finality", "FINAL");
        body.put("action_authority", false);
        body.put("learning_authority", false);
        body.put("raw_capture_persisted", false);
        body.put("frame_sha256", Canonical.hex(MessageDigest.getInstance("SHA-256").digest(frame)));
        body.put("frame_bytes", frame.length);
        body.put("frame_width", width);
        body.put("frame_height", height);
        body.put("frame_format", "image/jpeg");
        body.put("issued_at", issuedAt);
        body.put("expires_at", issuedAt + 30L);
        body.put("key_storage_status", key.getString("key_storage_status"));
        body.put("key_id", key.getString("key_id"));
        return signer.sign(body);
    }

    private static String randomHex(int bytes) {
        byte[] value = new byte[bytes];
        new SecureRandom().nextBytes(value);
        return Canonical.hex(value);
    }
}
