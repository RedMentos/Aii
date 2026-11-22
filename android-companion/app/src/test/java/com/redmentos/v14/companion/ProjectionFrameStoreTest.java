package com.redmentos.v14.companion;

import org.json.JSONObject;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.security.MessageDigest;
import java.util.Arrays;
import java.io.IOException;
import java.io.OutputStream;
import java.io.Closeable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

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

        FrameReadLease lease = ProjectionFrameStore.consumeLease(token, 102L);
        assertNotNull(lease);
        assertEquals(4, lease.frameLengthForTest());
        assertEquals(1, ProjectionFrameStore.activeReadCountForTest());
        assertNull(ProjectionFrameStore.consumeLease(token, 103L));
        JSONObject consumed = ProjectionFrameStore.status(104L);
        assertEquals("FRAME_CONSUMED", consumed.getString("status"));
        assertFalse(consumed.has("frame_uri"));
        assertTrue(consumed.has("receipt"));
        assertEquals("EXPIRED", ProjectionFrameStore.status(100L + ProjectionFrameStore.TTL_MS)
                .getString("status"));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(100L + ProjectionFrameStore.TTL_MS + 1L)
                .getString("status"));
        assertTrue(lease.isCancelledForTest());
        assertTrue(lease.isZeroizedForTest());
        assertEquals(0, ProjectionFrameStore.activeReadCountForTest());
    }

    @Test public void wrongTokenDoesNotConsumeTheFrame() throws Exception {
        byte[] frame = new byte[]{5, 6, 7};
        String token = "b".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 200L);
        assertNull(ProjectionFrameStore.consumeLease("c".repeat(32), 201L));
        assertEquals("FRAME_READY", ProjectionFrameStore.status(202L).getString("status"));
        FrameReadLease lease = ProjectionFrameStore.consumeLease(token, 203L);
        assertNotNull(lease);
        ProjectionFrameStore.clear();
        assertTrue(lease.isZeroizedForTest());
    }

    @Test public void clearZeroesCallerOwnedFrameBytesAndRevokesReceipt() throws Exception {
        byte[] frame = new byte[]{9, 8, 7};
        ProjectionFrameStore.publish(frame, receipt(frame, "d".repeat(32)), 300L);
        ProjectionFrameStore.clear();
        assertTrue(Arrays.equals(new byte[]{0, 0, 0}, frame));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(301L).getString("status"));
    }

    @Test public void clearCancelsBlockedWriterAndZeroizesConsumedFrame() throws Exception {
        byte[] frame = new byte[1024 * 1024];
        Arrays.fill(frame, (byte) 7);
        String token = "a".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 500L);
        FrameReadLease lease = ProjectionFrameStore.consumeLease(token, 501L);
        assertNotNull(lease);

        BlockingOutputStream output = new BlockingOutputStream();
        AtomicBoolean readerClosed = new AtomicBoolean(false);
        Closeable reader = () -> readerClosed.set(true);
        lease.start(reader, output);
        assertTrue("writer should enter the blocked no-reader path",
                output.entered.await(2, TimeUnit.SECONDS));
        assertTrue(lease.isWriterAliveForTest());

        ProjectionFrameStore.clear();

        assertTrue("revocation should unblock the writer",
                lease.awaitWriterExitForTest(2_000L));
        assertTrue(lease.isCancelledForTest());
        assertTrue(lease.isZeroizedForTest());
        assertTrue(readerClosed.get());
        assertEquals(0L, output.closed.getCount());
        assertEquals(0, ProjectionFrameStore.activeReadCountForTest());
        assertTrue(Arrays.equals(new byte[frame.length], frame));
    }

    @Test public void cancelZeroizesFrameBeforeAStalledPipeCloseReturns() throws Exception {
        byte[] frame = new byte[32 * 1024];
        Arrays.fill(frame, (byte) 6);
        String token = "b".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 600L);
        FrameReadLease lease = ProjectionFrameStore.consumeLease(token, 601L);
        assertNotNull(lease);

        SlowCloseOutputStream output = new SlowCloseOutputStream();
        lease.start(() -> {}, output);
        assertTrue(output.writeEntered.await(2, TimeUnit.SECONDS));

        Thread revoker = new Thread(ProjectionFrameStore::clear, "v14-frame-revoker");
        revoker.start();
        assertTrue(output.closeEntered.await(2, TimeUnit.SECONDS));
        assertTrue("buffer must be zero before descriptor close completes",
                Arrays.equals(new byte[frame.length], frame));

        output.allowClose.countDown();
        revoker.join(2_000L);
        assertFalse(revoker.isAlive());
        assertTrue(lease.awaitWriterExitForTest(2_000L));
        assertTrue(lease.isZeroizedForTest());
    }

    private static final class SlowCloseOutputStream extends OutputStream {
        final CountDownLatch writeEntered = new CountDownLatch(1);
        final CountDownLatch closeEntered = new CountDownLatch(1);
        final CountDownLatch allowClose = new CountDownLatch(1);

        @Override public void write(int value) throws IOException {
            write(new byte[]{(byte) value}, 0, 1);
        }

        @Override public void write(byte[] bytes, int offset, int length) throws IOException {
            writeEntered.countDown();
            try {
                allowClose.await();
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IOException("test writer interrupted", interrupted);
            }
            throw new IOException("test pipe closed");
        }

        @Override public void close() throws IOException {
            closeEntered.countDown();
            try {
                allowClose.await();
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IOException("test close interrupted", interrupted);
            }
        }
    }

    private static final class BlockingOutputStream extends OutputStream {
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch closed = new CountDownLatch(1);

        @Override public void write(int value) throws IOException {
            write(new byte[]{(byte) value}, 0, 1);
        }

        @Override public void write(byte[] bytes, int offset, int length) throws IOException {
            entered.countDown();
            try {
                if (!closed.await(3, TimeUnit.SECONDS)) {
                    throw new IOException("test writer timed out");
                }
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IOException("test writer interrupted", interrupted);
            }
            throw new IOException("test pipe closed");
        }

        @Override public void close() {
            closed.countDown();
        }
    }

    @Test public void oversizedAndAuthorityBearingFramesAreRejected() throws Exception {
        byte[] frame = new byte[]{1, 2};
        for (String flag : new String[]{"learning_authority", "action_authority", "raw_capture_persisted"}) {
            JSONObject bad = receipt(frame, "e".repeat(32));
            bad.getJSONObject("body").put(flag, true);
            try {
                ProjectionFrameStore.publish(frame, bad, 400L);
                fail(flag + " must be rejected");
            } catch (SecurityException expected) {
                assertTrue(expected.getMessage().contains("authority"));
            }
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
