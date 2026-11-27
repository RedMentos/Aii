package com.redmentos.v14.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class AudioCaptureDefaultOffTest {
    @Test public void companionDoesNotRequestMicrophonePermission() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        PackageInfo info = context.getPackageManager().getPackageInfo(
                context.getPackageName(), PackageManager.GET_PERMISSIONS);
        String[] requested = info.requestedPermissions == null
                ? new String[0] : info.requestedPermissions;
        List<String> permissions = Arrays.asList(requested);

        assertTrue("manifest fixture must be read", permissions.contains(Manifest.permission.POST_NOTIFICATIONS));
        assertFalse("microphone capture must remain disabled by default",
                permissions.contains(Manifest.permission.RECORD_AUDIO));
        assertFalse("no microphone foreground service may be declared",
                permissions.contains("android.permission.FOREGROUND_SERVICE_MICROPHONE"));
    }
}
