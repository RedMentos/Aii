package com.redmentos.v14.companion;

import android.content.Context;

import org.json.JSONObject;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.security.MessageDigest;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class MediaProjectionCaptureGateTest {
    private static final String FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private static final String ROTATED_FINGERPRINT =
            "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";
    private Context context;

    @Before public void setUp() {
        context = RuntimeEnvironment.getApplication();
        CompanionProvider.setEnabled(context, false);
        ProjectionFrameStore.clear();
        assertEquals(PairingPersistence.Result.PERSISTED,
                PairingPersistence.persistWithStatus(
                        "com.termux", FINGERPRINT, (pkg, digest) -> true, () -> false));
        assertTrue(context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString("paired_package", "com.termux")
                .putString("paired_cert_sha256", FINGERPRINT)
                .commit());
    }

    @After public void tearDown() {
        CompanionProvider.setEnabled(context, false);
        ProjectionFrameStore.clear();
    }

    private static CaptureSessionGate claimedFrame() {
        CaptureSessionGate gate = new CaptureSessionGate();
        assertTrue(gate.begin());
        assertTrue(gate.activate());
        assertTrue(gate.claimFrame());
        return gate;
    }

    private static JSONObject receipt(byte[] frame, String token) throws Exception {
        JSONObject body = new JSONObject()
                .put("schema", "v14.android-ui-frame-receipt/1")
                .put("frame_token", token)
                .put("frame_bytes", frame.length)
                .put("frame_sha256", Canonical.hex(
                        MessageDigest.getInstance("SHA-256").digest(frame)))
                .put("raw_capture_persisted", false)
                .put("action_authority", false)
                .put("learning_authority", false);
        return new JSONObject().put("body", body).put("key_id", "test")
                .put("signature", "fixture-only");
    }

    private boolean publish(CaptureSessionGate gate, byte[] frame, String token,
                            CapabilityRegistry.CertificateDigestReader reader) throws Exception {
        return CompanionProvider.publishScreenFrameIfAuthorized(
                context, gate, frame, receipt(frame, token), 101L, reader);
    }

    @Test public void stopWinsTheActualProviderGateBeforePublication() throws Exception {
        assertTrue(CompanionProvider.setEnabled(context, true));
        CaptureSessionGate gate = claimedFrame();
        byte[] frame = new byte[]{1, 2, 3, 4};
        String token = "a".repeat(32);
        CountDownLatch publisherReady = new CountDownLatch(1);
        AtomicBoolean published = new AtomicBoolean(true);
        Thread publisher = new Thread(() -> {
            publisherReady.countDown();
            try {
                published.set(publish(gate, frame, token, (ctx, pkg) -> {
                    assertTrue(Thread.holdsLock(CompanionProvider.ACTION_GATE_LOCK));
                    assertEquals("com.termux", pkg);
                    return FINGERPRINT;
                }));
            } catch (Exception failure) {
                throw new AssertionError(failure);
            }
        }, "v14-frame-publish-stop-race");

        synchronized (CompanionProvider.ACTION_GATE_LOCK) {
            publisher.start();
            assertTrue(publisherReady.await(2, TimeUnit.SECONDS));
            assertTrue(CompanionProvider.setEnabled(context, false));
        }
        publisher.join(2_000L);
        assertFalse("publisher must settle", publisher.isAlive());
        assertFalse("disabled provider must reject a late frame", published.get());
        assertEquals("NO_FRAME", ProjectionFrameStore.status(102L).getString("status"));
        CompanionProvider.completeScreenFrameSession(gate, true);
    }

    @Test public void stopClearsAFrameWhenPublicationWinsTheSameGateFirst() throws Exception {
        assertTrue(CompanionProvider.setEnabled(context, true));
        CaptureSessionGate gate = claimedFrame();
        byte[] frame = new byte[]{9, 8, 7};
        String token = "b".repeat(32);

        assertTrue(publish(gate, frame, token, (ctx, pkg) -> FINGERPRINT));
        assertEquals("FRAME_READY", ProjectionFrameStore.status(102L).getString("status"));
        assertTrue(gate.isComplete());

        assertFalse("already-completed gate reports no new state transition",
                CompanionProvider.completeScreenFrameSession(gate, true));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(102L).getString("status"));
        assertTrue(CompanionProvider.setEnabled(context, false));
    }

    @Test public void currentTermuxSignerIsRecheckedAtPublication() throws Exception {
        assertTrue(CompanionProvider.setEnabled(context, true));
        CaptureSessionGate gate = claimedFrame();
        byte[] frame = new byte[]{5, 6, 7};
        String token = "c".repeat(32);

        assertFalse(publish(gate, frame, token, (ctx, pkg) -> ROTATED_FINGERPRINT));
        assertEquals("NO_FRAME", ProjectionFrameStore.status(102L).getString("status"));
        CompanionProvider.completeScreenFrameSession(gate, true);
    }
}
