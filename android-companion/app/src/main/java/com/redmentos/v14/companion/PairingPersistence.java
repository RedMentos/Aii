package com.redmentos.v14.companion;

/** Checked persistence for the user-approved Termux caller identity. */
final class PairingPersistence {
    interface Writer {
        boolean commit(String packageName, String certificateSha256);
    }

    interface Rollback {
        void restore();
    }

    private PairingPersistence() {}

    static boolean persist(String packageName, String certificateSha256,
                           Writer writer, Rollback rollback) {
        if (!"com.termux".equals(packageName)
                || certificateSha256 == null
                || !certificateSha256.matches("[0-9a-f]{64}")
                || writer == null || rollback == null) {
            return false;
        }
        try {
            if (writer.commit(packageName, certificateSha256)) return true;
        } catch (RuntimeException ignored) {
            // A writer may have changed in-memory preferences before disk I/O failed.
        }
        try {
            rollback.restore();
        } catch (RuntimeException ignored) {
            // The caller still receives failure; it must never display pairing success.
        }
        return false;
    }
}
