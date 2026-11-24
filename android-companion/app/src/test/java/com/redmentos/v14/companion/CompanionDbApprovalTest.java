package com.redmentos.v14.companion;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.database.Cursor;
import android.content.Intent;
import android.service.notification.StatusBarNotification;

import org.json.JSONObject;

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
import java.util.concurrent.atomic.AtomicInteger;
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

    private static final String TEST_RECEIPT_KEY_ID = "b".repeat(64);

    private static final class FakeReceiptSigner implements ReceiptFactory.Signer {
        @Override public JSONObject publicKeyInfo() throws Exception {
            return new JSONObject()
                    .put("key_id", TEST_RECEIPT_KEY_ID)
                    .put("key_storage_status", "ANDROID_KEYSTORE_SOFTWARE_BACKED");
        }

        @Override public JSONObject sign(JSONObject body) throws Exception {
            return new JSONObject()
                    .put("body", body)
                    .put("key_id", TEST_RECEIPT_KEY_ID)
                    .put("signature", "test-only");
        }
    }

    private void insertValidPending(String actionId, long expiresAt) throws Exception {
        String packageName = "com.example.app";
        String digest = Canonical.requestDigest("launch_app", packageName);
        JSONObject args = new JSONObject().put("package", packageName);
        JSONObject request = new JSONObject()
                .put("schema", "v14.android-action-request/1")
                .put("action_id", actionId)
                .put("capability", "launch_app")
                .put("args", args)
                .put("digest", digest)
                .put("expires_at", expiresAt / 1000.0)
                .put("companion_local_consent_required", true)
                .put("android_os_permission_required", false)
                .put("permission_bypass", false)
                .put("model_authority", false)
                .put("local_approval", "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION");
        assertTrue(first.insertPending(actionId, request.toString(), packageName, expiresAt));
    }

    private static CompanionProvider.ReceiptIssuer receiptIssuer(AtomicInteger issued) {
        ReceiptFactory.Signer signer = new FakeReceiptSigner();
        return (action, status, localConsent, nowMillis) -> {
            issued.incrementAndGet();
            return ReceiptFactory.create(action, signer, status, localConsent, nowMillis).toString();
        };
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

    @Test public void expiryCleanupWaitsForSubmitNotificationPublication() throws Exception {
        String expiringId = "c".repeat(32);
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(
                "v14-action-approval", "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        Notification notification = new Notification.Builder(context, "v14-action-approval")
                .setSmallIcon(android.R.drawable.ic_menu_view).build();
        CountDownLatch inserted = new CountDownLatch(1);
        CountDownLatch publishNotification = new CountDownLatch(1);
        CountDownLatch pendingStarted = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> submit = pool.submit(() -> {
                synchronized (CompanionProvider.ACTION_GATE_LOCK) {
                    insertPending(expiringId, NOW);
                    inserted.countDown();
                    try {
                        if (!publishNotification.await(5, TimeUnit.SECONDS)) {
                            throw new AssertionError("notification publication release timed out");
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        throw new IllegalStateException(e);
                    }
                    manager.notify(CompanionProvider.approvalNotificationTag(expiringId),
                            0, notification);
                }
            });
            assertTrue(inserted.await(5, TimeUnit.SECONDS));
            Future<List<CompanionDb.Action>> pending = pool.submit(() -> {
                pendingStarted.countDown();
                return CompanionProvider.pendingActions(context, first, NOW);
            });
            assertTrue(pendingStarted.await(5, TimeUnit.SECONDS));
            try {
                pending.get(100, TimeUnit.MILLISECONDS);
                fail("expiry cleanup must wait until submit has published its notification");
            } catch (java.util.concurrent.TimeoutException expected) {
                // The shared action gate is still held by submit.
            }
            publishNotification.countDown();
            submit.get(5, TimeUnit.SECONDS);
            assertTrue(pending.get(5, TimeUnit.SECONDS).isEmpty());
            assertEquals("EXPIRED", first.get(expiringId).status);
            assertFalse("expiry cleanup must remove the notification posted by submit",
                    hasApprovalNotification(manager, expiringId));
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

    @Test public void providerProcessRestartStartsStoppedEvenWhenPreferenceWasEnabled() {
        insertPending(NOW + 10_000L);
        assertTrue(CompanionProvider.setEnabled(context, true));
        assertTrue(CompanionProvider.isEnabled(context));

        // ContentProvider.onCreate invokes this on every new app process. The
        // prior process's persisted ON value is not an active session grant.
        assertTrue(CompanionProvider.resetProcessStateForProviderStartup(context));
        assertFalse(CompanionProvider.isEnabled(context));
        assertFalse(context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE)
                .getBoolean("enabled", true));

        AtomicBoolean dispatched = new AtomicBoolean(false);
        String result = CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, () -> dispatched.set(true));
        assertEquals("COMPANION_STOPPED", result);
        assertFalse(dispatched.get());
        assertEquals("PENDING_USER_APPROVAL", first.get(ACTION_ID).status);
    }

    @Test public void failedStopCommitFailsClosedAndBlocksDispatch() {
        insertPending(NOW + 10_000L);
        assertTrue(CompanionProvider.setEnabled(context, true));
        assertTrue(CompanionProvider.isEnabled(context));

        boolean committed = CompanionProvider.setEnabled(context, false, (target, enabled) -> false);
        assertFalse(committed);
        // The stale persisted ON value deliberately remains, but this process
        // has already dropped its session grant and cannot dispatch.
        assertTrue(context.getSharedPreferences(CompanionProvider.PREFS, Context.MODE_PRIVATE)
                .getBoolean("enabled", false));
        assertFalse(CompanionProvider.isEnabled(context));

        AtomicBoolean dispatched = new AtomicBoolean(false);
        String result = CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, () -> dispatched.set(true));
        assertEquals("COMPANION_STOPPED", result);
        assertFalse(dispatched.get());
        assertEquals("PENDING_USER_APPROVAL", first.get(ACTION_ID).status);
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

    @Test public void executingRecoveryWritesUnknownReceiptOnceAndNeverRedispatches() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForExecution(ACTION_ID, NOW));
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = (action, status, consent, now) -> {
            issued.incrementAndGet();
            assertEquals("EXECUTING", action.status);
            assertEquals("OUTCOME_UNKNOWN", status);
            assertTrue(consent);
            return "{\"status\":\"OUTCOME_UNKNOWN\",\"local_consent\":true}";
        };
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        CompanionDb.Action recovered = first.get(ACTION_ID);
        assertEquals("OUTCOME_UNKNOWN", recovered.status);
        assertTrue(recovered.receiptJson.contains("OUTCOME_UNKNOWN"));
        assertFalse(first.claimForExecution(ACTION_ID, NOW));
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals(1, issued.get());
    }

    @Test public void denialRecoveryWritesSignedDenialShapeWithoutConsent() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForDenial(ACTION_ID, NOW));
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = (action, status, consent, now) -> {
            issued.incrementAndGet();
            assertEquals("DENYING", action.status);
            assertEquals("USER_DENIED", status);
            assertFalse(consent);
            return "{\"status\":\"USER_DENIED\",\"local_consent\":false}";
        };
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals("USER_DENIED", first.get(ACTION_ID).status);
        assertEquals(1, issued.get());
    }

    @Test public void failedReceiptRecoveryKeepsClaimAndNotificationForRetry() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForExecution(ACTION_ID, NOW));
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(
                "v14-action-approval", "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        Notification notification = new Notification.Builder(context, "v14-action-approval")
                .setSmallIcon(android.R.drawable.ic_menu_view).build();
        manager.notify(CompanionProvider.approvalNotificationTag(ACTION_ID), 0, notification);
        CompanionProvider.ReceiptIssuer broken = (action, status, consent, now) -> {
            throw new IllegalStateException("simulated Keystore failure");
        };
        assertFalse(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, broken));
        assertEquals("EXECUTING", first.get(ACTION_ID).status);
        assertNull(first.get(ACTION_ID).receiptJson);
        assertEquals("notification reconciliation must retain a claimed action with no receipt",
                0, CompanionProvider.reconcileApprovalNotifications(context, first, NOW));
        assertTrue(hasApprovalNotification(manager, ACTION_ID));
        CompanionProvider.ReceiptIssuer repaired = (action, status, consent, now) ->
                "{\"status\":\"OUTCOME_UNKNOWN\",\"local_consent\":true}";
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, repaired));
        assertEquals("OUTCOME_UNKNOWN", first.get(ACTION_ID).status);
        assertFalse(hasApprovalNotification(manager, ACTION_ID));
    }


    @Test public void executingReceiptRetriesAfterSqliteCommitFailureAndRestartWithoutRedispatch() throws Exception {
        insertValidPending(ACTION_ID, NOW + 10_000L);
        assertTrue(CompanionProvider.setEnabled(context, true));
        AtomicInteger dispatches = new AtomicInteger();
        assertEquals("DISPATCHED", CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, dispatches::incrementAndGet));
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = receiptIssuer(issued);

        first.getWritableDatabase().execSQL(
                "CREATE TRIGGER fail_exec_receipt BEFORE UPDATE OF status ON actions "
                        + "WHEN NEW.action_id='" + ACTION_ID + "' AND NEW.status='OUTCOME_UNKNOWN' "
                        + "BEGIN SELECT RAISE(ABORT, 'simulated SQLite receipt commit failure'); END");
        assertFalse(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals("EXECUTING", first.get(ACTION_ID).status);
        assertNull(first.get(ACTION_ID).receiptJson);
        assertEquals(1, issued.get());
        assertEquals(1, dispatches.get());

        // Process-death boundary: the claimed state survives, but the runtime
        // starts OFF. Startup recovery may only create the unknown receipt.
        first.close();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        first = new CompanionDb(context);
        first.getWritableDatabase().execSQL("DROP TRIGGER IF EXISTS fail_exec_receipt");
        assertEquals(1, CompanionProvider.recoverClaimedActions(context, first, NOW, issuer));

        CompanionDb.Action recovered = first.get(ACTION_ID);
        assertEquals("OUTCOME_UNKNOWN", recovered.status);
        JSONObject envelope = new JSONObject(recovered.receiptJson);
        JSONObject body = envelope.getJSONObject("body");
        assertEquals("OUTCOME_UNKNOWN", body.getString("status"));
        assertTrue(body.getBoolean("local_consent"));
        assertFalse(body.getBoolean("observed"));
        assertEquals(ACTION_ID, body.getString("action_id"));
        assertEquals(Canonical.requestDigest("launch_app", "com.example.app"), body.getString("digest"));
        assertEquals(TEST_RECEIPT_KEY_ID, body.getString("key_id"));
        assertEquals("test-only", envelope.getString("signature"));
        assertEquals(2, issued.get());

        assertTrue(CompanionProvider.setEnabled(context, true));
        assertEquals("NOT_CLAIMED", CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, dispatches::incrementAndGet));
        assertEquals("a recovered action must never be dispatched a second time", 1, dispatches.get());
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals("a durable receipt is returned idempotently, not re-signed", 2, issued.get());
        CompanionProvider.setEnabled(context, false);
    }

    @Test public void denialReceiptRetriesAfterSqliteCommitFailureAndRestartWithoutConsent() throws Exception {
        insertValidPending(ACTION_ID, NOW + 10_000L);
        assertTrue(first.claimForDenial(ACTION_ID, NOW));
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = receiptIssuer(issued);

        first.getWritableDatabase().execSQL(
                "CREATE TRIGGER fail_denial_receipt BEFORE UPDATE OF status ON actions "
                        + "WHEN NEW.action_id='" + ACTION_ID + "' AND NEW.status='USER_DENIED' "
                        + "BEGIN SELECT RAISE(ABORT, 'simulated SQLite denial receipt commit failure'); END");
        assertFalse(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals("DENYING", first.get(ACTION_ID).status);
        assertNull(first.get(ACTION_ID).receiptJson);
        assertEquals(1, issued.get());

        first.close();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        first = new CompanionDb(context);
        first.getWritableDatabase().execSQL("DROP TRIGGER IF EXISTS fail_denial_receipt");
        assertEquals(1, CompanionProvider.recoverClaimedActions(context, first, NOW, issuer));

        CompanionDb.Action recovered = first.get(ACTION_ID);
        assertEquals("USER_DENIED", recovered.status);
        JSONObject envelope = new JSONObject(recovered.receiptJson);
        JSONObject body = envelope.getJSONObject("body");
        assertEquals("USER_DENIED", body.getString("status"));
        assertFalse(body.getBoolean("local_consent"));
        assertFalse(body.getBoolean("observed"));
        assertEquals(ACTION_ID, body.getString("action_id"));
        assertEquals(TEST_RECEIPT_KEY_ID, body.getString("key_id"));
        assertEquals("test-only", envelope.getString("signature"));
        assertEquals(2, issued.get());

        assertFalse(first.claimForExecution(ACTION_ID, NOW));
        assertFalse(first.claimForDenial(ACTION_ID, NOW));
        assertTrue(CompanionProvider.setEnabled(context, true));
        AtomicInteger dispatches = new AtomicInteger();
        assertEquals("NOT_CLAIMED", CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, dispatches::incrementAndGet));
        assertEquals(0, dispatches.get());
        assertTrue(CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
        assertEquals("a durable denial is not signed again", 2, issued.get());
        CompanionProvider.setEnabled(context, false);
    }

    @Test public void notificationReconciliationRemovesCommittedReceiptAndPreservesLiveApproval() {
        String liveId = "b".repeat(32);
        insertPending(ACTION_ID, NOW + 10_000L);
        insertPending(liveId, NOW + 20_000L);
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

        // Model the crash window: SQLite has the terminal receipt, but the
        // process died before cancelling the already-published notification.
        assertTrue(first.claimForExecution(ACTION_ID, NOW));
        first.finish(ACTION_ID, "EXECUTING", "OUTCOME_UNKNOWN", "{\"signed\":true}");
        assertTrue(hasApprovalNotification(manager, ACTION_ID));

        assertEquals(1, CompanionProvider.reconcileApprovalNotifications(context, first, NOW));
        assertFalse(hasApprovalNotification(manager, ACTION_ID));
        assertTrue("a still-pending action keeps its approval notification",
                hasApprovalNotification(manager, liveId));
        assertEquals("OUTCOME_UNKNOWN", first.get(ACTION_ID).status);
        assertEquals(0, CompanionProvider.reconcileApprovalNotifications(context, first, NOW));
        assertTrue(hasApprovalNotification(manager, liveId));
    }

    @Test public void claimedReceiptRecoverySurvivesDatabaseReopen() {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForDenial(ACTION_ID, NOW));
        first.close();
        first = new CompanionDb(context);
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = (action, status, consent, now) -> {
            issued.incrementAndGet();
            return "{\"status\":\"USER_DENIED\",\"local_consent\":false}";
        };
        assertEquals(1, CompanionProvider.recoverClaimedActions(context, first, NOW, issuer));
        assertEquals("USER_DENIED", first.get(ACTION_ID).status);
        assertEquals(1, issued.get());
    }

    @Test public void concurrentReceiptRecoveryHasOneDurableWinner() throws Exception {
        insertPending(NOW + 10_000L);
        assertTrue(first.claimForExecution(ACTION_ID, NOW));
        AtomicInteger issued = new AtomicInteger();
        CompanionProvider.ReceiptIssuer issuer = (action, status, consent, now) -> {
            issued.incrementAndGet();
            return "{\"status\":\"OUTCOME_UNKNOWN\",\"local_consent\":true}";
        };
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> left = pool.submit(() ->
                    CompanionProvider.recoverClaimedAction(context, first, ACTION_ID, NOW, issuer));
            Future<Boolean> right = pool.submit(() ->
                    CompanionProvider.recoverClaimedAction(context, second, ACTION_ID, NOW, issuer));
            assertTrue(left.get(5, TimeUnit.SECONDS));
            assertTrue(right.get(5, TimeUnit.SECONDS));
            assertEquals(1, issued.get());
            assertEquals("OUTCOME_UNKNOWN", first.get(ACTION_ID).status);
            assertNotNull(first.get(ACTION_ID).receiptJson);
        } finally {
            pool.shutdownNow();
        }
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

    @Test public void exceptionAfterDispatchAttemptIsRecordedAsUnknown() {
        insertPending(NOW + 10_000L);
        assertTrue(CompanionProvider.setEnabled(context, true));
        AtomicBoolean attempted = new AtomicBoolean(false);
        String result = CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, () -> {
                    attempted.set(true);
                    throw new IllegalStateException("simulated framework dispatch uncertainty");
                });
        assertTrue(attempted.get());
        assertEquals("OUTCOME_UNKNOWN", result);
        assertEquals("EXECUTING", first.get(ACTION_ID).status);
        assertFalse(first.claimForExecution(ACTION_ID, NOW));
    }

    @Test public void absentLaunchIntentIsDefiniteFailureWithoutExternalDispatch() {
        insertPending(NOW + 10_000L);
        assertTrue(CompanionProvider.setEnabled(context, true));
        AtomicBoolean externalDispatch = new AtomicBoolean(false);
        String result = CompanionProvider.claimAndDispatch(
                context, first, ACTION_ID, () -> NOW, () -> {
                    throw new CompanionProvider.DispatchNotAttemptedException();
                });
        assertFalse(externalDispatch.get());
        assertEquals("FAILED_TO_DISPATCH", result);
        assertEquals("EXECUTING", first.get(ACTION_ID).status);
        assertFalse(first.claimForExecution(ACTION_ID, NOW));
    }

    @Test public void dispatchResultMapsToTruthfulReceiptStatus() {
        assertEquals("DISPATCHED_UNVERIFIED",
                CompanionProvider.receiptStatusForDispatchResult("DISPATCHED"));
        assertEquals("FAILED_TO_DISPATCH",
                CompanionProvider.receiptStatusForDispatchResult("FAILED_TO_DISPATCH"));
        assertEquals("OUTCOME_UNKNOWN",
                CompanionProvider.receiptStatusForDispatchResult("OUTCOME_UNKNOWN"));
        assertEquals("OUTCOME_UNKNOWN",
                CompanionProvider.receiptStatusForDispatchResult("unexpected"));
    }


}
