package com.redmentos.v14.companion;

import android.content.Context;
import android.os.ParcelFileDescriptor;

import org.json.JSONObject;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.security.MessageDigest;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class CompanionProviderFramePipeTest {
    private static JSONObject receipt(byte[] frame, String token) throws Exception {
        JSONObject body = new JSONObject()
                .put("schema", "v14.android-ui-frame-receipt/1")
                .put("frame_token", token)
                .put("frame_bytes", frame.length)
                .put("frame_sha256", Canonical.hex(MessageDigest.getInstance("SHA-256").digest(frame)))
                .put("raw_capture_persisted", false)
                .put("action_authority", false)
                .put("learning_authority", false);
        return new JSONObject().put("body", body).put("key_id", "test")
                .put("signature", "fixture-only");
    }

    @After public void reset() {
        Context context = RuntimeEnvironment.getApplication();
        CompanionProvider.setEnabled(context, false);
        ProjectionFrameStore.clear();
    }

    @Test public void companionStopClosesAnAlreadyOpenedOneShotFramePipe() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        assertTrue(CompanionProvider.setEnabled(context, true));
        byte[] frame = new byte[2 * 1024 * 1024];
        Arrays.fill(frame, (byte) 9);
        String token = "a".repeat(32);
        ProjectionFrameStore.publish(frame, receipt(frame, token), 100L);

        ParcelFileDescriptor readEnd = CompanionProvider.openFramePipe(context, token, 101L);
        assertTrue(readEnd.getFileDescriptor().valid());
        assertEquals(1, ProjectionFrameStore.activeReadCountForTest());

        assertTrue(CompanionProvider.setEnabled(context, false));

        assertFalse(readEnd.getFileDescriptor().valid());
        assertTrue(Arrays.equals(new byte[frame.length], frame));
        assertEquals(0, ProjectionFrameStore.activeReadCountForTest());
    }

    @Test public void concurrentStopAndOpenNeverLeavesAUsablePipeAfterStop() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        for (int attempt = 0; attempt < 16; attempt++) {
            final int iteration = attempt;
            assertTrue(CompanionProvider.setEnabled(context, true));
            byte[] frame = new byte[256 * 1024];
            Arrays.fill(frame, (byte) 5);
            String token = String.format("%032x", iteration + 1);
            ProjectionFrameStore.publish(frame, receipt(frame, token), 200L + iteration);

            CountDownLatch ready = new CountDownLatch(2);
            CountDownLatch start = new CountDownLatch(1);
            AtomicReference<ParcelFileDescriptor> opened = new AtomicReference<>();
            AtomicReference<Throwable> openFailure = new AtomicReference<>();
            AtomicReference<Throwable> stopFailure = new AtomicReference<>();

            Thread opener = new Thread(() -> {
                ready.countDown();
                try {
                    if (!start.await(2, TimeUnit.SECONDS)) throw new IllegalStateException("race start timeout");
                    opened.set(CompanionProvider.openFramePipe(context, token, 201L + iteration));
                } catch (Throwable failure) {
                    openFailure.set(failure);
                }
            }, "v14-frame-open-race");
            Thread stopper = new Thread(() -> {
                ready.countDown();
                try {
                    if (!start.await(2, TimeUnit.SECONDS)) throw new IllegalStateException("race start timeout");
                    CompanionProvider.setEnabled(context, false);
                } catch (Throwable failure) {
                    stopFailure.set(failure);
                }
            }, "v14-frame-stop-race");
            opener.start();
            stopper.start();
            assertTrue(ready.await(2, TimeUnit.SECONDS));
            start.countDown();
            opener.join(3_000L);
            stopper.join(3_000L);

            assertFalse("open thread must settle", opener.isAlive());
            assertFalse("stop thread must settle", stopper.isAlive());
            assertNull(stopFailure.get());
            assertFalse(CompanionProvider.isEnabled(context));
            assertEquals(0, ProjectionFrameStore.activeReadCountForTest());
            ParcelFileDescriptor readEnd = opened.get();
            if (readEnd != null) {
                assertFalse("stop must revoke a pipe opened just before it", readEnd.getFileDescriptor().valid());
            } else {
                assertTrue("open must fail when stop wins the gate", openFailure.get() instanceof Exception);
            }
            assertTrue(Arrays.equals(new byte[frame.length], frame));
        }
    }
}
