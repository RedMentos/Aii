package com.redmentos.v14.companion;

import android.content.Context;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

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
        assertTrue(first.insertPending(ACTION_ID, "{\"capability\":\"launch_app\"}",
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
        assertEquals("PENDING_USER_APPROVAL", first.get(ACTION_ID).status);
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
}
