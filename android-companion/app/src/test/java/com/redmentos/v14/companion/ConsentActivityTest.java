package com.redmentos.v14.companion;

import android.content.Intent;
import android.net.Uri;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class ConsentActivityTest {
    private static final String URL = "https://example.com/path?q=1";

    @Test public void openUrlBuildsOnlyBrowsableHttpsActionView() {
        Intent intent = ConsentActivity.buildOpenUrlIntent(URL, URL);
        assertEquals(Intent.ACTION_VIEW, intent.getAction());
        assertEquals(Uri.parse(URL), intent.getData());
        assertTrue(intent.hasCategory(Intent.CATEGORY_BROWSABLE));
    }

    @Test public void urlValidatorRejectsNonHttpsCredentialsAndUnsafeAuthorities() {
        assertTrue(Canonical.isSafeHttpsUrl(URL));
        assertTrue(Canonical.isSafeHttpsUrl("https://example.com:443/a"));
        assertFalse(Canonical.isSafeHttpsUrl("http://example.com"));
        assertFalse(Canonical.isSafeHttpsUrl("javascript:alert(1)"));
        assertFalse(Canonical.isSafeHttpsUrl("intent://example.com/#Intent;scheme=https;end"));
        assertFalse(Canonical.isSafeHttpsUrl("file:///etc/passwd"));
        assertFalse(Canonical.isSafeHttpsUrl("https://user:pass@example.com/"));
        assertFalse(Canonical.isSafeHttpsUrl("https://example.com:444/"));
        assertFalse(Canonical.isSafeHttpsUrl("https://example.com:/"));
        assertFalse(Canonical.isSafeHttpsUrl("https://example.com/a b"));
        assertFalse(Canonical.isSafeHttpsUrl("https://example.com/%zz"));
        assertFalse(Canonical.isSafeHttpsUrl("https://example.com\\\\@evil.test"));
        assertFalse(Canonical.isSafeHttpsUrl("https://éxample.com/"));
    }

    @Test public void openUrlDigestMatchesSortedPythonEnvelope() throws Exception {
        String canonical = "{\\"args\\":{\\"url\\":\\"https://example.com/path?q=1\\"},\\"capability\\":\\"open_url\\"}";
        String expected = Canonical.hex(MessageDigest.getInstance("SHA-256")
                .digest(canonical.getBytes(StandardCharsets.UTF_8)));
        assertEquals(expected, Canonical.requestDigest("open_url", URL));
    }

    @Test public void changedTargetCannotBeUsedForApprovalIntent() {
        try {
            ConsentActivity.buildOpenUrlIntent(URL, "https://attacker.example/");
            fail("changed target accepted");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("target changed"));
        }
    }
}
