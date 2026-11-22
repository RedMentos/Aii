package com.redmentos.v14.companion;

import org.json.JSONObject;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.security.MessageDigest;
import java.util.Arrays;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class ProjectionFrameStoreTest {
    private static JSONObject receipt(byte[] frame, String token) throws Exception {
        JSONObject body = new JSONObject()
                .put("schema", "v14.android-ui-frame-receipt/1")
                .put("frame_token", token)
                .put("frame_bytes", frame.length)
                .put("frame_sha256", Canonical.hex(MessageDigest.getInstance("SHA-256").digest(frame)))
                .put("raw_capture_persisted", false)
                .put("action_authority", false)
                .put("learning_authority", false);
        return new JSONObject().put("body", body).put("key_id", "test").put("signature", "fixture-only");
    }

    @After public void clearStore() {
        ProjectionFrameStore.clear();
    }

    @Test public void frameIsAvailableOnceAndReceiptRemainsOnlyUntilExpiry() throws Exception {
        byte[] frame = new byte[]{1, 2, 3, 4};
        String token = "a".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 100L);

        JSONObject ready = ProjectionFrameStore.status(101L);
        assertEquals("FRAME_READY", ready.getString("status"));
        assertEquals("content://" + CompanionProvider.AUTHORITY + "/ui-frame/" + token,
                ready.getString("frame_uri"));
        assertEquals(ProjectionFrameStore.TTL_MS - 1L, ready.getLong("expires_in_ms"));

        assertArrayEquals(new byte[]{1, 2, 3, 4}, ProjectionFrameStore.consume(token, 102L));
        assertNull(ProjectionFrameStore.consume(token, 103L));
        JSONObject consumed = ProjectionFrameStore.status(104L);
        assertEquals("FRAME_CONSUMED", consumed.getString("status"));
        assertFalse(consumed.has("frame_uri"));
        assertTrue(consumed.has("receipt"));
        assertEquals("EXPIRED", ProjectionFrameStore.status(100L + ProjectionFrameStore.TTL_MS)
                .getString("status"));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(100L + ProjectionFrameStore.TTL_MS + 1L)
                .getString("status"));
    }

    @Test public void wrongTokenDoesNotConsumeTheFrame() throws Exception {
        byte[] frame = new byte[]{5, 6, 7};
        String token = "b".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 200L);
        assertNull(ProjectionFrameStore.consume("c".repeat(32), 201L));
        assertEquals("FRAME_READY", ProjectionFrameStore.status(202L).getString("status"));
        assertArrayEquals(frame, ProjectionFrameStore.consume(token, 203L));
    }

    @Test public void clearZeroesCallerOwnedFrameBytesAndRevokesReceipt() throws Exception {
        byte[] frame = new byte[]{9, 8, 7};
        ProjectionFrameStore.publish(frame, receipt(frame, "d".repeat(32)), 300L);
        ProjectionFrameStore.clear();
        assertTrue(Arrays.equals(new byte[]{0, 0, 0}, frame));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(301L).getString("status"));
    }

    @Test public void oversizedAndAuthorityBearingFramesAreRejected() throws Exception {
        byte[] frame = new byte[]{1, 2};
        JSONObject bad = receipt(frame, "e".repeat(32));
        bad.getJSONObject("body").put("learning_authority", true);
        try {
            ProjectionFrameStore.publish(frame, bad, 400L);
            fail("learning authority must be rejected");
        } catch (SecurityException expected) {
            assertTrue(expected.getMessage().contains("authority"));
        }
        byte[] oversized = new byte[ProjectionFrameStore.MAX_FRAME_BYTES + 1];
        try {
            ProjectionFrameStore.publish(oversized, receipt(frame, "f".repeat(32)), 401L);
            fail("oversized frame must be rejected");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("invalid one-shot frame"));
        }
    }
}
