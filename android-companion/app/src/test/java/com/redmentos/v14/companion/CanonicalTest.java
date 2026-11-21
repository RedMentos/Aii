package com.redmentos.v14.companion;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public final class CanonicalTest {
    @Test public void launchAppDigestMatchesPythonCanonicalJson() throws Exception {
        assertEquals("0e1b8771ccce5e24b8dcfd99466b6e553413dc684f3ef3cd4c3da52ad52d6b15",
                Canonical.requestDigest("launch_app", "com.example.app"));
    }
}
