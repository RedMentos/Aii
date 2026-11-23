package com.redmentos.v14.companion;

import org.junit.Before;
import org.junit.Test;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class PairingPersistenceTest {
    private static final String FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Before public void resetTrustToKnownGoodState() {
        assertEquals(PairingPersistence.Result.PERSISTED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT,
                        (pkg, digest) -> true, () -> false));
    }

    @Test public void onlyReportsPairingWhenTheDurableWriterCommits() {
        AtomicBoolean called = new AtomicBoolean(false);
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        AtomicReference<String> packageSeen = new AtomicReference<>();
        AtomicReference<String> fingerprintSeen = new AtomicReference<>();
        assertEquals(PairingPersistence.Result.PERSISTED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT, (pkg, digest) -> {
                    called.set(true);
                    packageSeen.set(pkg);
                    fingerprintSeen.set(digest);
                    return true;
                }, () -> {
                    rolledBack.set(true);
                    return true;
                }));
        assertTrue(called.get());
        assertEquals("com.termux", packageSeen.get());
        assertEquals(FINGERPRINT, fingerprintSeen.get());
        assertFalse(rolledBack.get());
        assertTrue(PairingPersistence.isTrustAvailable());
    }

    @Test public void failedCommitRestoresPreviousInMemoryPairing() {
        AtomicReference<String> inMemoryPairing =
                new AtomicReference<>("previous-package:previous-digest");
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        assertEquals(PairingPersistence.Result.RESTORED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT, (pkg, digest) -> {
                    inMemoryPairing.set(pkg + ":" + digest);
                    return false;
                }, () -> {
                    inMemoryPairing.set("previous-package:previous-digest");
                    rolledBack.set(true);
                    return true;
                }));
        assertTrue(rolledBack.get());
        assertEquals("previous-package:previous-digest", inMemoryPairing.get());
        assertTrue(PairingPersistence.isTrustAvailable());
    }

    @Test public void writerExceptionsRestorePreviousInMemoryPairing() {
        AtomicReference<String> inMemoryPairing = new AtomicReference<>("previous");
        assertEquals(PairingPersistence.Result.RESTORED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT, (pkg, digest) -> {
                    inMemoryPairing.set("uncommitted");
                    throw new IllegalStateException("simulated storage failure");
                }, () -> {
                    inMemoryPairing.set("previous");
                    return true;
                }));
        assertEquals("previous", inMemoryPairing.get());
        assertTrue(PairingPersistence.isTrustAvailable());
    }

    @Test public void failedRollbackLeavesProcessTrustRevoked() {
        assertEquals(PairingPersistence.Result.UNTRUSTED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT,
                        (pkg, digest) -> false,
                        () -> { throw new IllegalStateException("simulated rollback failure"); }));
        assertFalse(PairingPersistence.isTrustAvailable());
    }

    @Test public void rejectsInvalidPackageFingerprintOrMissingWriterBeforePersistence() {
        AtomicBoolean called = new AtomicBoolean(false);
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        PairingPersistence.Writer writer = (pkg, digest) -> {
            called.set(true);
            return true;
        };
        PairingPersistence.Rollback rollback = () -> {
            rolledBack.set(true);
            return true;
        };
        assertEquals(PairingPersistence.Result.INVALID,
                PairingPersistence.persistWithStatus("com.attacker", FINGERPRINT, writer, rollback));
        assertEquals(PairingPersistence.Result.INVALID,
                PairingPersistence.persistWithStatus("com.termux", "not-a-fingerprint", writer, rollback));
        assertEquals(PairingPersistence.Result.INVALID,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT.toUpperCase(), writer, rollback));
        assertEquals(PairingPersistence.Result.INVALID,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT, null, rollback));
        assertEquals(PairingPersistence.Result.INVALID,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT, writer, null));
        assertFalse(called.get());
        assertFalse(rolledBack.get());
        assertTrue(PairingPersistence.isTrustAvailable());
    }

    @Test public void providerAdmissionWaitsForPairingWriteAndSeesFailedLatch() throws Exception {
        CountDownLatch writerEntered = new CountDownLatch(1);
        CountDownLatch releaseWriter = new CountDownLatch(1);
        AtomicReference<PairingPersistence.Result> result = new AtomicReference<>();
        Thread pairing = new Thread(() -> result.set(PairingPersistence.persistWithStatus(
                "com.termux", FINGERPRINT,
                (pkg, digest) -> {
                    writerEntered.countDown();
                    try {
                        if (!releaseWriter.await(2, TimeUnit.SECONDS)) {
                            throw new IllegalStateException("test writer timed out");
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        throw new IllegalStateException(e);
                    }
                    return false;
                }, () -> false)));
        pairing.start();
        assertTrue(writerEntered.await(2, TimeUnit.SECONDS));

        AtomicBoolean admitted = new AtomicBoolean(true);
        CountDownLatch providerStarted = new CountDownLatch(1);
        Thread provider = new Thread(() -> {
            providerStarted.countDown();
            admitted.set(PairingPersistence.withTrustedPairing(() -> true));
        });
        provider.start();
        assertTrue(providerStarted.await(2, TimeUnit.SECONDS));

        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
        while (provider.getState() != Thread.State.BLOCKED && System.nanoTime() < deadline) {
            Thread.yield();
        }
        assertEquals("provider check must wait behind the in-flight pairing write",
                Thread.State.BLOCKED, provider.getState());

        releaseWriter.countDown();
        pairing.join(2000);
        provider.join(2000);
        assertFalse("pairing worker must finish", pairing.isAlive());
        assertFalse("provider check must finish", provider.isAlive());
        assertEquals(PairingPersistence.Result.UNTRUSTED, result.get());
        assertFalse("provider must observe the revoked trust latch", admitted.get());
    }
}
