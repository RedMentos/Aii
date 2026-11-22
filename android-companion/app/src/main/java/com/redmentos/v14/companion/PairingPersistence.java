package com.redmentos.v14.companion;

/** Checked persistence for the user-approved Termux caller identity. */
final class PairingPersistence {
    interface Writer {
        boolean commit(String packageName, String certificateSha256);
    }

    private PairingPersistence() {}

    static boolean persist(String packageName, String certificateSha256, Writer writer) {
        if (!"com.termux".equals(packageName)
                || certificateSha256 == null
                || !certificateSha256.matches("[0-9a-f]{64}")
                || writer == null) {
            return false;
        }
        try {
            return writer.commit(packageName, certificateSha256);
        } catch (RuntimeException ignored) {
            return false;
        }
    }
}
