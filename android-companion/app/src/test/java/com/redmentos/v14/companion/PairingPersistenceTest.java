package com.redmentos.v14.companion;

import org.junit.Test;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class PairingPersistenceTest {
    private static final String FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Test public void onlyReportsPairingWhenTheDurableWriterCommits() {
        AtomicBoolean called = new AtomicBoolean(false);
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        AtomicReference<String> packageSeen = new AtomicReference<>();
        AtomicReference<String> fingerprintSeen = new AtomicReference<>();
        assertTrue(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            called.set(true);
            packageSeen.set(pkg);
            fingerprintSeen.set(digest);
            return true;
        }, () -> rolledBack.set(true)));
        assertTrue(called.get());
        assertEquals("com.termux", packageSeen.get());
        assertEquals(FINGERPRINT, fingerprintSeen.get());
        assertFalse(rolledBack.get());

        called.set(false);
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            called.set(true);
            return false;
        }, () -> rolledBack.set(true)));
        assertTrue(called.get());
        assertTrue(rolledBack.get());
    }

    @Test public void failedCommitRestoresPreviousInMemoryPairing() {
        AtomicReference<String> inMemoryPairing = new AtomicReference<>("previous-package:previous-digest");
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            inMemoryPairing.set(pkg + ":" + digest);
            return false;
        }, () -> {
            inMemoryPairing.set("previous-package:previous-digest");
            rolledBack.set(true);
        }));
        assertTrue(rolledBack.get());
        assertEquals("previous-package:previous-digest", inMemoryPairing.get());
    }

    @Test public void writerExceptionsRestorePreviousInMemoryPairing() {
        AtomicReference<String> inMemoryPairing = new AtomicReference<>("previous");
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            inMemoryPairing.set("uncommitted");
            throw new IllegalStateException("simulated storage failure");
        }, () -> inMemoryPairing.set("previous")));
        assertEquals("previous", inMemoryPairing.get());
    }

    @Test public void rejectsInvalidPackageFingerprintOrMissingWriterBeforePersistence() {
        AtomicBoolean called = new AtomicBoolean(false);
        AtomicBoolean rolledBack = new AtomicBoolean(false);
        PairingPersistence.Writer writer = (pkg, digest) -> {
            called.set(true);
            return true;
        };
        PairingPersistence.Rollback rollback = () -> rolledBack.set(true);
        assertFalse(PairingPersistence.persist("com.attacker", FINGERPRINT, writer, rollback));
        assertFalse(PairingPersistence.persist("com.termux", "not-a-fingerprint", writer, rollback));
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT.toUpperCase(), writer, rollback));
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, null, rollback));
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, writer, null));
        assertFalse(called.get());
        assertFalse(rolledBack.get());
    }

    @Test public void rollbackExceptionsStillFailClosed() {
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT,
                (pkg, digest) -> false,
                () -> { throw new IllegalStateException("simulated rollback failure"); }));
    }
}
