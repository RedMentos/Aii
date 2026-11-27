package com.redmentos.v14.companion;

import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.security.MessageDigest;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class UIFrameReceiptFactoryTest {
    private static final String KEY_ID = "b".repeat(64);

    private static final class FakeSigner implements ReceiptFactory.Signer {
        @Override public JSONObject publicKeyInfo() throws Exception {
            return new JSONObject()
                    .put("key_id", KEY_ID)
                    .put("key_storage_status", "ANDROID_KEYSTORE_SOFTWARE_BACKED");
        }

        @Override public JSONObject sign(JSONObject body) throws Exception {
            return new JSONObject().put("body", body).put("key_id", KEY_ID).put("signature", "fixture-only");
        }
    }

    @Test public void receiptBindsExactFrameAndNeverGrantsAuthority() throws Exception {
        byte[] frame = new byte[]{1, 2, 3, 4, 5};
        JSONObject envelope = UIFrameReceiptFactory.create(frame, 2, 2, 100L, 125L, new FakeSigner());
        JSONObject body = envelope.getJSONObject("body");
        assertEquals("v14.android-ui-frame-receipt/1", body.getString("schema"));
        assertEquals(KEY_ID, envelope.getString("key_id"));
        assertEquals(KEY_ID, body.getString("key_id"));
        assertEquals(Canonical.hex(MessageDigest.getInstance("SHA-256").digest(frame)),
                body.getString("frame_sha256"));
        assertEquals(frame.length, body.getInt("frame_bytes"));
        assertEquals(2, body.getInt("frame_width"));
        assertEquals(2, body.getInt("frame_height"));
        assertEquals("image/jpeg", body.getString("frame_format"));
        assertEquals("MEDIA_PROJECTION", body.getString("capture_method"));
        assertEquals("FULL_DISPLAY", body.getString("capture_scope"));
        assertEquals("SCREEN_FRAME_AVAILABLE", body.getString("event_kind"));
        assertEquals("ELAPSED_REALTIME", body.getString("clock"));
        assertFalse(body.getBoolean("raw_capture_persisted"));
        assertFalse(body.getBoolean("action_authority"));
        assertFalse(body.getBoolean("learning_authority"));
        assertEquals("ui-" + body.getString("nonce"), body.getString("source_id"));
        assertEquals("mp-" + body.getString("nonce"), body.getString("capture_session_id"));
        assertEquals("mp-" + body.getString("nonce"), body.getString("consent_receipt_ref"));
        assertEquals(30L, body.getLong("expires_at") - body.getLong("issued_at"));
    }

    @Test public void invalidDimensionsAndIntervalsFailClosed() throws Exception {
        byte[] frame = new byte[]{1};
        try {
            UIFrameReceiptFactory.create(frame, 3000, 2000, 100L, 125L, new FakeSigner());
            fail("more than four megapixels");
        } catch (IllegalArgumentException expected) {}
        try {
            UIFrameReceiptFactory.create(frame, 1, 1, 100L, 5101L, new FakeSigner());
            fail("capture interval too long");
        } catch (IllegalArgumentException expected) {}
    }
}
