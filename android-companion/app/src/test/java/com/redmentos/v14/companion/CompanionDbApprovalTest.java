package com.redmentos.v14.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.database.Cursor;
import android.content.Intent;
import android.service.notification.StatusBarNotification;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class CompanionDbApprovalTest {
    private static final String ACTION_ID = "a".repeat(32);
    private static final long NOW = 1_000_000L;
    private Context context;
    private CompanionDb first;
    private CompanionDb second;

    @Before public void setUp() {
        context = RuntimeEnvironment.getApplication();
        context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE).edit().clear().commit();
        context.deleteDatabase("v14-companion.db");
        first = new CompanionDb(context);
        second = new CompanionDb(context);
        first.getWritableDatabase();
        second.getWritableDatabase();
    }

    @After public void tearDown() {
        if (first != null) first.close();
        if (second != null) second.close();
        if (context != null) context.deleteDatabase("v14-companion.db");
    }

    private void insertPending(long expiresAt) {
        insertPending(ACTION_ID, expiresAt);
    }

    private void insertPending(String actionId, long expiresAt) {
        assertTrue(first.insertPending(actionId, "{\"capability\":\"launch_app\"}",
                "com.example.app", expiresAt));
    }

    @Test public void concurrentApproveAndDenyHaveExactlyOneWinner() throws Exception {
        insertPending(NOW + 10_000L);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> approve = pool.submit(() -> {
                ready.countDown();
                assertTrue(start.await(5, TimeUnit.SECONDS));
                return first.claimForExecution(ACTION_ID, NOW);
            });
            Future<Boolean> deny = pool.submit(() -> {
                ready.countDown();
                assertTrue(start.await(5, TimeUnit.SECONDS));
                return second.claimForDenial(ACTION_ID, NOW);
            });
            assertTrue(ready.await(5, TimeUnit.SECONDS));
            start.countDown();
            boolean approved = approve.get(5, TimeUnit.SECONDS);
            boolean denied = deny.get(5, TimeUnit.SECONDS);
            assertNotEquals("exactly one decision must win", approved, denied);
            String expected = approved ? "EXECUTING" : "DENYING";
            assertEquals(expected, first.get(ACTION_ID).status);
            assertFalse(first.claimForExecution(ACTION_ID, NOW));
            assertFalse(second.claimForDenial(ACTION_ID, NOW));
        } finally {
            pool.shutdownNow();
        }
    }

    @Test public void expiredActionCannotBeApprovedOrDenied() {
        insertPending(NOW);
        assertFalse(first.claimForExecution(ACTION_ID, NOW));
        assertFalse(second.claimForDenial(ACTION_ID, NOW));
        assertTrue(first.expire(ACTION_ID, NOW));
        assertEquals("EXPIRED", first.get(ACTION_ID).status);
        assertFalse(first.expire(ACTION_ID, NOW));
    }

    @Test public void pendingReadExpiresOldRowsAndReturnsOnlyLiveActions() {
        String liveId = "b".repeat(32);
        insertPending(ACTION_ID, NOW);
        insertPending(liveId, NOW + 1L);
        List<String> expired = new ArrayList<>();
        List<CompanionDb.Action> pending = first.pending(NOW, expired);
        assertEquals(1, pending.size());
        assertEquals(liveId, pending.get(0).actionId);
        assertEquals(List.of(ACTION_ID), expired);
        assertEquals("EXPIRED", first.get(ACTION_ID).status);
        assertEquals("PENDING_USER_APPROVAL", first.get(liveId).status);
        assertEquals(0, first.expirePending(NOW));
    }

    @Test @Config(sdk = 32)
    public void expiredAndCancelledApprovalsClearOnlyTheirOwnNotifications() {
        String liveId = "b".repeat(32);
        insertPending(ACTION_ID, NOW);
        insertPending(liveId, NOW + 1L);
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(
                "v14-action-approval", "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        Notification notification = new Notification.Builder(context, "v14-action-approval")
                .setSmallIcon(android.R.drawable.ic_menu_view).build();
        manager.notify(CompanionProvider.approvalNotificationTag(ACTION_ID), 0, notification);
        manager.notify(CompanionProvider.approvalNotificationTag(liveId), 0, notification);
        assertTrue(hasApprovalNotification(manager, ACTION_ID));
        assertTrue(hasApprovalNotification(manager, liveId));

        List<String> expired = new ArrayList<>();
        first.pending(NOW, expired);
        for (String actionId : expired) {
            CompanionProvider.cancelApprovalNotification(context, actionId);
        }
        assertFalse(hasApprovalNotification(manager, ACTION_ID));
        assertTrue(hasApprovalNotification(manager, liveId));

        assertTrue(first.cancel(liveId));
        CompanionProvider.cancelApprovalNotification(context, liveId);
        assertFalse(hasApprovalNotification(manager, liveId));
    }

    @Test public void cancellationWaitsForSubmitNotificationPublicationAndClearsIt() throws Exception {
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(
                "v14-action-approval", "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        Notification notification = new Notification.Builder(context, "v14-action-approval")
                .setSmallIcon(android.R.drawable.ic_menu_view).build();
        CountDownLatch inserted = new CountDownLatch(1);
        CountDownLatch publishNotification = new CountDownLatch(1);
        CountDownLatch cancelStarted = new CountDownLatch(1);
        CountDownLatch cancelFinished = new CountDownLatch(1);
        AtomicBoolean cancelled = new AtomicBoolean(false);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> submit = pool.submit(() -> {
                synchronized (CompanionProvider.ACTION_GATE_LOCK) {
                    insertPending(ACTION_ID, NOW + 10_000L);
                    inserted.countDown();
                    try {
                        if (!publishNotification.await(5, TimeUnit.SECONDS)) {
                            throw new AssertionError("notification publication release timed out");
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        throw new IllegalStateException(e);
                    }
                    manager.notify(CompanionProvider.approvalNotificationTag(ACTION_ID),
                            0, notification);
                }
            });
            assertTrue(inserted.await(5, TimeUnit.SECONDS));
            Future<?> cancel = pool.submit(() -> {
                cancelStarted.countDown();
                cancelled.set(CompanionProvider.cancelAction(context, first, ACTION_ID));
                cancelFinished.countDown();
            });
            assertTrue(cancelStarted.await(5, TimeUnit.SECONDS));
            assertFalse("cancel must wait until submit has published its notification",
                    cancelFinished.await(100, TimeUnit.MILLISECONDS));
            publishNotification.countDown();
            submit.get(5, TimeUnit.SECONDS);
            cancel.get(5, TimeUnit.SECONDS);
            assertTrue(cancelled.get());
            assertEquals("CANCELLED", first.get(ACTION_ID).status);
            assertFalse("a cancelled action must not leave a stale approval notification",
                    hasApprovalNotification(manager, ACTION_ID));
        } finally {
            publishNotification.countDown();
            pool.shutdownNow();
        }
    }

    private boolean hasApprovalNotification(NotificationManager manager, String actionId) {
        for (StatusBarNotification notification : manager.getActiveNotifications()) {
            if (actionId.equals(notification.getTag()) && notification.getId() == 0) return true;
        }
        return false;
    }

    @Test public void signedReceiptWindowStartsAtDecisionTimeNotRequestDeadline() {
        long requestExpirySeconds = 1_030L;
        long issuedAtSeconds = 1_029L; // approval claim won just before request expiry
        long receiptExpirySeconds = ConsentActivity.receiptExpiresAt(issuedAtSeconds);
        assertTrue(issuedAtSeconds < requestExpirySeconds);
        assertEquals(1_089L, receiptExpirySeconds);
        assertEquals(60L, receiptExpirySeconds - issuedAtSeconds);
    }

    @Test public void stopBeforeApprovalClaimPreventsDispatch() {
        insertPending(NOW + 10_000L);
        CompanionProvider.setEnabled(context, false);
        AtomicBoolean dispatched = new AtomicBoolean(false);
        String result = CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, () -> dispatched.set(true));
        assertEquals("COMPANION_STOPPED", result);
        assertFalse(dispatched.get());
        assertEquals("PENDING_USER_APPROVAL", first.get(ACTION_ID).status);
    }

    @Test public void stopWaitsUntilClaimedDispatchReturns() throws Exception {
        insertPending(NOW + 10_000L);
        CompanionProvider.setEnabled(context, true);
        CountDownLatch dispatchEntered = new CountDownLatch(1);
        CountDownLatch releaseDispatch = new CountDownLatch(1);
        CountDownLatch stopStarted = new CountDownLatch(1);
        CountDownLatch stopFinished = new CountDownLatch(1);
        AtomicReference<String> result = new AtomicReference<>();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> approval = pool.submit(() -> result.set(CompanionProvider.claimAndDispatch(
                    context, first, ACTION_ID, () -> NOW, () -> {
                        dispatchEntered.countDown();
                        try {
                            if (!releaseDispatch.await(5, TimeUnit.SECONDS)) {
                                throw new AssertionError("dispatch release timed out");
                            }
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            throw new IllegalStateException(e);
                        }
                    })));
            assertTrue(dispatchEntered.await(5, TimeUnit.SECONDS));
            Future<?> stop = pool.submit(() -> {
                stopStarted.countDown();
                CompanionProvider.setEnabled(context, false);
                stopFinished.countDown();
            });
            assertTrue(stopStarted.await(5, TimeUnit.SECONDS));
            assertFalse("stop must wait while a claimed dispatch is inside the gate",
                    stopFinished.await(100, TimeUnit.MILLISECONDS));
            releaseDispatch.countDown();
            approval.get(5, TimeUnit.SECONDS);
            stop.get(5, TimeUnit.SECONDS);
            assertTrue(stopFinished.await(5, TimeUnit.SECONDS));
            assertEquals("DISPATCHED", result.get());
            assertEquals("EXECUTING", first.get(ACTION_ID).status);
            assertFalse(context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE)
                    .getBoolean("enabled", true));
        } finally {
            releaseDispatch.countDown();
            pool.shutdownNow();
        }
    }

    @Test public void executionClaimSurvivesRestartAndCannotBeRetried() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForExecution(ACTION_ID, NOW));
        first.close();
        first = new CompanionDb(context);
        assertFalse(first.claimForExecution(ACTION_ID, NOW));
        assertFalse(second.claimForDenial(ACTION_ID, NOW));
        first.finish(ACTION_ID, "EXECUTING", "DISPATCHED_UNVERIFIED", "{\"signed\":true}");
        assertEquals("DISPATCHED_UNVERIFIED", first.get(ACTION_ID).status);
        assertEquals("{\"signed\":true}", first.receipt(ACTION_ID));
    }

    @Test public void terminalDenialCanOnlyFinishItsOwnClaim() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForDenial(ACTION_ID, NOW));
        try {
            first.finish(ACTION_ID, "EXECUTING", "DISPATCHED_UNVERIFIED", "{}");
            fail("dispatch finalizer must not consume a denial claim");
        } catch (IllegalStateException expected) {
            assertEquals("DENYING", first.get(ACTION_ID).status);
        }
        first.finish(ACTION_ID, "DENYING", "USER_DENIED", "{\"signed\":true}");
        assertEquals("USER_DENIED", first.get(ACTION_ID).status);
        assertFalse(second.claimForExecution(ACTION_ID, NOW));
    }

    @Test public void cancellationWinsBeforeEitherDecisionAndCannotBeReversed() {
        insertPending(NOW + 10_000L);
        assertTrue(first.cancel(ACTION_ID));
        assertFalse(second.claimForExecution(ACTION_ID, NOW));
        assertFalse(second.claimForDenial(ACTION_ID, NOW));
        assertEquals("CANCELLED", first.get(ACTION_ID).status);
    }
    @Test public void companionDatabaseHasNoRawPcmOrAudioBlobStorage() {
        try (Cursor c = first.getReadableDatabase().rawQuery(
                "SELECT name,sql FROM sqlite_master WHERE type='table'", null)) {
            while (c.moveToNext()) {
                String name = c.getString(0).toLowerCase(Locale.ROOT);
                String sql = c.isNull(1) ? "" : c.getString(1).toLowerCase(Locale.ROOT);
                assertFalse(name.contains("pcm") || name.contains("audio"));
                assertFalse(sql.contains("pcm16") || sql.contains("raw_audio")
                        || sql.contains("audio_blob") || sql.contains("audio_bytes"));
            }
        }
    }

    @Test public void sharedUidCallerIsRejected() {
        assertTrue(CompanionProvider.isOnlyPairedPackage(
                new String[]{"com.termux"}, "com.termux"));
        assertFalse(CompanionProvider.isOnlyPairedPackage(
                new String[]{"com.termux", "com.example.shared"}, "com.termux"));
        assertFalse(CompanionProvider.isOnlyPairedPackage(null, "com.termux"));
    }

    @Test public void approvalIntentAndNotificationIdentityUseFullActionIdDespiteHashCollision() {
        String first = "8b50c53de5d8694493a2e5e7f318bc9c";
        String second = "a2389bc938b7d225cd80af126908e600";
        assertEquals(first.hashCode(), second.hashCode());
        Intent firstIntent = CompanionProvider.approvalIntent(context, first);
        Intent secondIntent = CompanionProvider.approvalIntent(context, second);
        assertFalse(firstIntent.filterEquals(secondIntent));
        assertNotEquals(firstIntent.getData(), secondIntent.getData());
        assertNotEquals(CompanionProvider.approvalNotificationTag(first),
                CompanionProvider.approvalNotificationTag(second));
    }

    @Test public void approvalNotificationTagRejectsMalformedActionIds() {
        try {
            CompanionProvider.approvalNotificationTag("not-an-action-id");
            fail("malformed notification identity must be rejected");
        } catch (IllegalArgumentException expected) {
            assertEquals("invalid action id", expected.getMessage());
        }
    }

}
