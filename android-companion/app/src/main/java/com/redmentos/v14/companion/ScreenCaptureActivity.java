package com.redmentos.v14.companion;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.projection.MediaProjectionConfig;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

/** Visible, user-initiated OS consent entry point. One consent token creates one frame only. */
public final class ScreenCaptureActivity extends Activity {
    private static final int REQUEST_CAPTURE = 1401;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!CompanionProvider.isEnabled(this)
                || !CapabilityRegistry.isCurrentTermuxTrusted(this)
                || ProjectionFrameStore.hasFrame(android.os.SystemClock.elapsedRealtime())) {
            Toast.makeText(this, "Pair and enable the companion; discard any pending frame before another capture", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        if (manager == null) {
            Toast.makeText(this, "MediaProjection is unavailable", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        Intent consent;
        if (Build.VERSION.SDK_INT >= 34) {
            // Do not silently broaden capture to an app/window chosen by an external caller.
            consent = manager.createScreenCaptureIntent(
                    MediaProjectionConfig.createConfigForDefaultDisplay());
        } else {
            consent = manager.createScreenCaptureIntent();
        }
        startActivityForResult(consent, REQUEST_CAPTURE);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_CAPTURE) {
            finish();
            return;
        }
        if (resultCode != RESULT_OK || data == null) {
            Toast.makeText(this, "Screen capture was not approved", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }
        try {
            Intent service = new Intent(this, MediaProjectionCaptureService.class);
            service.setAction(MediaProjectionCaptureService.ACTION_CAPTURE);
            service.putExtra(MediaProjectionCaptureService.EXTRA_RESULT_CODE, resultCode);
            service.putExtra(MediaProjectionCaptureService.EXTRA_RESULT_DATA, data);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(service);
            else startService(service);
            Toast.makeText(this, "Capturing one frame; no continuous recording", Toast.LENGTH_LONG).show();
        } catch (RuntimeException e) {
            Toast.makeText(this, "Could not start one-shot capture: " + e.getClass().getSimpleName(),
                    Toast.LENGTH_LONG).show();
        }
        finish();
    }
}
