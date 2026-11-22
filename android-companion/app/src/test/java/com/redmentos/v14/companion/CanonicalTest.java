package com.redmentos.v14.companion;

import org.junit.Test;
import java.util.HashMap;
import java.util.Map;
import static org.junit.Assert.assertEquals;

public final class CanonicalTest {
    @Test public void launchAppDigestMatchesPythonCanonicalJson() throws Exception {
        assertEquals("0e1b8771ccce5e24b8dcfd99466b6e553413dc684f3ef3cd4c3da52ad52d6b15",
                Canonical.requestDigest("launch_app", "com.example.app"));
    }

    @Test public void receiptJsonUsesSortedPythonCompatibleAsciiEncoding() {
        Map<String, Object> values = new HashMap<>();
        values.put("c", 3L);
        values.put("b", "x\n\u00e9");
        values.put("a", true);
        assertEquals("{\"a\":true,\"b\":\"x\\n\\u00e9\",\"c\":3}", Canonical.json(values));
    }
}
