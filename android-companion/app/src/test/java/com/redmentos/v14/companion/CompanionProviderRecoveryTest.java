package com.redmentos.v14.companion;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowApplication;

import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class CompanionProviderRecoveryTest {
    private static final String CHANNEL = "v14-action-approval";
    private Context context;

    @Before public void resetBefore() {
        context = RuntimeEnvironment.getApplication();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        context.deleteDatabase("v14-companion.db");
        ShadowApplication shadow = org.robolectric.Shadows.shadowOf(
                (android.app.Application) context);
        shadow.grantPermissions(Manifest.permission.POST_NOTIFICATIONS);
    }

    @After public void resetAfter() {
        CompanionProvider.setEnabled(context, false);
        context.deleteDatabase("v14-companion.db");
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.cancelAll();
    }

    private static String actionId(char ch) {
        return String.valueOf(ch).repeat(32);
    }

    private static void insertPending(CompanionDb db, String id, long nowMillis) {
        assertTrue(db.insertPending(
                id,
                "{\"schema\":\"v14.android-action-request/1\",\"fixture\":true}",
                "com.example.app",
                nowMillis + 60_000L));
    }

    private void postApprovalNotification(String id) {
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        assertNotNull(manager);
        manager.createNotificationChannel(new NotificationChannel(
                CHANNEL, "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        Notification notification = new Notification.Builder(context, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentTitle("V14 action needs approval")
                .setContentText("Fixture action — tap to review")
                .build();
        manager.notify(CompanionProvider.approvalNotificationTag(id), 0, notification);
    }

    private boolean hasApprovalNotification(String id) {
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return false;
        for (android.service.notification.StatusBarNotification active : manager.getActiveNotifications()) {
            if (id.equals(active.getTag())
                    && active.getNotification() != null
                    && CHANNEL.equals(active.getNotification().getChannelId())) {
                return true;
            }
        }
        return false;
    }

    @Test public void executingReceiptFailureRecoversAfterRestartWithoutRedispatch() {
        long now = System.currentTimeMillis();
        String id = actionId('a');
        CompanionDb db = new CompanionDb(context);
        insertPending(db, id, now);
        postApprovalNotification(id);
        assertTrue(CompanionProvider.setEnabled(context, true));

        AtomicInteger externalDispatches = new AtomicInteger();
        assertEquals("DISPATCHED", CompanionProvider.claimAndDispatch(
                context, db, id, () -> now, externalDispatches::incrementAndGet));
        assertEquals(1, externalDispatches.get());
        assertEquals("EXECUTING", db.get(id).status);

        AtomicInteger failedSigningAttempts = new AtomicInteger();
        assertFalse(CompanionProvider.recoverClaimedAction(
                context, db, id, now,
                (action, status, localConsent, issuedAt) -> {
                    failedSigningAttempts.incrementAndGet();
                    assertEquals("EXECUTING", action.status);
                    assertEquals("OUTCOME_UNKNOWN", status);
                    assertTrue(localConsent);
                    throw new IllegalStateException("injected Keystore failure");
                }));
        assertEquals(1, failedSigningAttempts.get());
        assertEquals("EXECUTING", db.get(id).status);
        assertNull(db.get(id).receiptJson);
        assertEquals(1, externalDispatches.get());
        assertTrue("notification must remain while the claimed action has no durable receipt",
                hasApprovalNotification(id));
        assertEquals(0, CompanionProvider.reconcileApprovalNotifications(
                context, db, System.currentTimeMillis()));
        assertTrue(hasApprovalNotification(id));

        db.close();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        CompanionDb restarted = new CompanionDb(context);
        AtomicInteger recoveryReceipts = new AtomicInteger();
        assertEquals(1, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    recoveryReceipts.incrementAndGet();
                    assertEquals("EXECUTING", action.status);
                    assertEquals("OUTCOME_UNKNOWN", status);
                    assertTrue(localConsent);
                    return "{\"fixture_receipt\":\"signed-unknown\"}";
                }));
        assertEquals(1, recoveryReceipts.get());
        assertEquals("OUTCOME_UNKNOWN", restarted.get(id).status);
        assertNotNull(restarted.get(id).receiptJson);
        assertEquals("receipt recovery must never repeat the external action",
                1, externalDispatches.get());
        assertFalse("notification is removed only after receipt persistence",
                hasApprovalNotification(id));

        assertEquals(0, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    fail("durable receipt must make recovery idempotent");
                    return "";
                }));
        assertEquals(1, externalDispatches.get());
        restarted.close();
    }

    @Test public void denyingReceiptFailureRecoversAsDenialWithoutExecution() {
        long now = System.currentTimeMillis();
        String id = actionId('b');
        CompanionDb db = new CompanionDb(context);
        insertPending(db, id, now);
        assertTrue(db.claimForDenial(id, now));

        AtomicInteger dispatches = new AtomicInteger();
        assertFalse(CompanionProvider.recoverClaimedAction(
                context, db, id, now,
                (action, status, localConsent, issuedAt) -> {
                    assertEquals("DENYING", action.status);
                    assertEquals("USER_DENIED", status);
                    assertFalse(localConsent);
                    throw new IllegalStateException("injected signing failure");
                }));
        assertEquals(0, dispatches.get());
        assertEquals("DENYING", db.get(id).status);
        assertNull(db.get(id).receiptJson);

        db.close();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        CompanionDb restarted = new CompanionDb(context);
        AtomicInteger receipts = new AtomicInteger();
        assertEquals(1, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    receipts.incrementAndGet();
                    assertEquals("DENYING", action.status);
                    assertEquals("USER_DENIED", status);
                    assertFalse(localConsent);
                    return "{\"fixture_receipt\":\"denied\"}";
                }));
        assertEquals(1, receipts.get());
        assertEquals("USER_DENIED", restarted.get(id).status);
        assertNotNull(restarted.get(id).receiptJson);
        assertEquals(0, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    fail("denial receipt must make recovery idempotent");
                    return "";
                }));
        assertEquals(0, dispatches.get());
        restarted.close();
    }

    @Test public void recoveryDoesNotAcceptDifferentDurableReceiptFromAnotherFinalizer() {
        long now = System.currentTimeMillis();
        String id = actionId('e');
        CompanionDb db = new CompanionDb(context);
        insertPending(db, id, now);
        postApprovalNotification(id);
        assertTrue(CompanionProvider.setEnabled(context, true));
        AtomicInteger externalDispatches = new AtomicInteger();
        assertEquals("DISPATCHED", CompanionProvider.claimAndDispatch(
                context, db, id, () -> now, externalDispatches::incrementAndGet));
        String otherReceipt = "{\"fixture_receipt\":\"other-finalizer\"}";
        String issuedReceipt = "{\"fixture_receipt\":\"this-finalizer\"}";
        assertFalse(CompanionProvider.recoverClaimedAction(
                context, db, id, now,
                (action, status, localConsent, issuedAt) -> {
                    assertEquals("EXECUTING", action.status);
                    assertEquals("OUTCOME_UNKNOWN", status);
                    assertTrue(localConsent);
                    assertTrue(db.finishClaimed(id, "EXECUTING", "OUTCOME_UNKNOWN", otherReceipt));
                    return issuedReceipt;
                }));
        assertEquals("OUTCOME_UNKNOWN", db.get(id).status);
        assertEquals(otherReceipt, db.get(id).receiptJson);
        assertEquals("a mismatched durable receipt must not be treated as this recovery",
                1, externalDispatches.get());
        assertTrue("the approval surface remains until this recovery verifies its own receipt",
                hasApprovalNotification(id));
        db.close();
    }

    @Test public void recoveryDoesNotTreatReceiptOnNonterminalClaimAsCompleted() {
        long now = System.currentTimeMillis();
        String id = actionId('f');
        CompanionDb db = new CompanionDb(context);
        insertPending(db, id, now);
        postApprovalNotification(id);
        assertTrue(db.claimForExecution(id, now));
        String strayReceipt = "{\"fixture_receipt\":\"nonterminal\"}";
        db.finish(id, "EXECUTING", "EXECUTING", strayReceipt);
        assertFalse(CompanionProvider.recoverClaimedAction(
                context, db, id, now,
                (action, status, localConsent, issuedAt) -> {
                    fail("a nonterminal row with a receipt must not be re-finalized");
                    return "";
                }));
        assertEquals("EXECUTING", db.get(id).status);
        assertEquals(strayReceipt, db.get(id).receiptJson);
        assertTrue(hasApprovalNotification(id));
        db.close();
    }

    @Test public void sqliteReceiptWriteFailureRecoversAfterRestartWithoutRedispatch() {
        long now = System.currentTimeMillis();
        String executingId = actionId('c');
        String denyingId = actionId('d');
        CompanionDb db = new CompanionDb(context);
        insertPending(db, executingId, now);
        insertPending(db, denyingId, now);
        postApprovalNotification(executingId);
        postApprovalNotification(denyingId);
        assertTrue(CompanionProvider.setEnabled(context, true));

        AtomicInteger externalDispatches = new AtomicInteger();
        assertEquals("DISPATCHED", CompanionProvider.claimAndDispatch(
                context, db, executingId, () -> now, externalDispatches::incrementAndGet));
        assertTrue(db.claimForDenial(denyingId, now));
        assertEquals("EXECUTING", db.get(executingId).status);
        assertEquals("DENYING", db.get(denyingId).status);

        db.getWritableDatabase().execSQL(
                "CREATE TRIGGER fail_recovery_receipt BEFORE UPDATE ON actions "
                        + "WHEN NEW.status IN ('OUTCOME_UNKNOWN','USER_DENIED') "
                        + "BEGIN SELECT RAISE(ABORT, 'injected SQLite receipt failure'); END");

        AtomicInteger failedReceiptIssues = new AtomicInteger();
        assertEquals(0, CompanionProvider.recoverClaimedActions(
                context, db, now,
                (action, status, localConsent, issuedAt) -> {
                    failedReceiptIssues.incrementAndGet();
                    if (executingId.equals(action.actionId)) {
                        assertEquals("EXECUTING", action.status);
                        assertEquals("OUTCOME_UNKNOWN", status);
                        assertTrue(localConsent);
                    } else {
                        assertEquals(denyingId, action.actionId);
                        assertEquals("DENYING", action.status);
                        assertEquals("USER_DENIED", status);
                        assertFalse(localConsent);
                    }
                    return "{\"fixture_receipt\":\"sqlite-write-failure\"}";
                }));
        assertEquals(2, failedReceiptIssues.get());
        assertEquals("EXECUTING", db.get(executingId).status);
        assertEquals("DENYING", db.get(denyingId).status);
        assertNull(db.get(executingId).receiptJson);
        assertNull(db.get(denyingId).receiptJson);
        assertEquals("the external action is never retried", 1, externalDispatches.get());
        assertTrue(hasApprovalNotification(executingId));
        assertTrue(hasApprovalNotification(denyingId));
        assertEquals(0, CompanionProvider.reconcileApprovalNotifications(
                context, db, System.currentTimeMillis()));
        assertTrue(hasApprovalNotification(executingId));
        assertTrue(hasApprovalNotification(denyingId));

        db.getWritableDatabase().execSQL("DROP TRIGGER fail_recovery_receipt");
        db.close();
        CompanionProvider.resetProcessStateForProviderStartup(context);
        CompanionDb restarted = new CompanionDb(context);
        AtomicInteger recoveredReceiptIssues = new AtomicInteger();
        assertEquals(2, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    recoveredReceiptIssues.incrementAndGet();
                    if (executingId.equals(action.actionId)) {
                        assertEquals("EXECUTING", action.status);
                        assertEquals("OUTCOME_UNKNOWN", status);
                        assertTrue(localConsent);
                        return "{\"fixture_receipt\":\"unknown-after-sqlite-failure\"}";
                    }
                    assertEquals(denyingId, action.actionId);
                    assertEquals("DENYING", action.status);
                    assertEquals("USER_DENIED", status);
                    assertFalse(localConsent);
                    return "{\"fixture_receipt\":\"denied-after-sqlite-failure\"}";
                }));
        assertEquals(2, recoveredReceiptIssues.get());
        assertEquals("OUTCOME_UNKNOWN", restarted.get(executingId).status);
        assertEquals("USER_DENIED", restarted.get(denyingId).status);
        assertNotNull(restarted.get(executingId).receiptJson);
        assertNotNull(restarted.get(denyingId).receiptJson);
        assertEquals(1, externalDispatches.get());
        assertFalse(hasApprovalNotification(executingId));
        assertFalse(hasApprovalNotification(denyingId));

        assertEquals(0, CompanionProvider.recoverClaimedActions(
                context, restarted, now,
                (action, status, localConsent, issuedAt) -> {
                    fail("durable SQLite recovery must be idempotent");
                    return "";
                }));
        assertEquals(1, externalDispatches.get());
        restarted.close();
    }

}
