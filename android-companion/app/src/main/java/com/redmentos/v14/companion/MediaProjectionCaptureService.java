package com.redmentos.v14.companion;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.WindowManager;
import android.view.WindowMetrics;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicBoolean;

public final class MediaProjectionCaptureService extends Service {
    static final String ACTION_CAPTURE = "com.redmentos.v14.companion.CAPTURE_ONE_FRAME";
    static final String ACTION_DISCARD = "com.redmentos.v14.companion.DISCARD_FRAME";
    static final String EXTRA_RESULT_CODE = "result_code";
    static final String EXTRA_RESULT_DATA = "result_data";
    private static final String CHANNEL = "v14-screen-capture";
    private static final int NOTIFICATION_ID = 1402;
    private static final int MAX_PIXELS = 4_000_000;
    private static final long CAPTURE_TIMEOUT_MS = 5_000L;

    private HandlerThread workerThread;
    private Handler worker;
    private MediaProjection projection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private MediaProjection.Callback projectionCallback;
    private final AtomicBoolean frameClaimed = new AtomicBoolean(false);
    private volatile boolean captureComplete;
    private int captureWidth;
    private int captureHeight;
    private int sourceWidth;
    private int sourceHeight;
    private long captureStartElapsed;

    @Override public void onCreate() {
        super.onCreate();
        workerThread = new HandlerThread("v14-media-projection-one-shot");
        workerThread.start();
        worker = new Handler(workerThread.getLooper());
        ensureChannel();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_DISCARD.equals(intent.getAction())) {
            CompanionProvider.clearScreenFrame();
            stopCapture(true);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (intent == null || !ACTION_CAPTURE.equals(intent.getAction())) {
            CompanionProvider.clearScreenFrame();
            stopCapture(true);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (!CompanionProvider.isEnabled(this)
                || !CapabilityRegistry.isCurrentTermuxTrusted(this)
                || ProjectionFrameStore.hasFrame(SystemClock.elapsedRealtime())) {
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        int resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED);
        Intent resultData = Build.VERSION.SDK_INT >= 33
                ? intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent.class)
                : intent.getParcelableExtra(EXTRA_RESULT_DATA);
        if (resultCode != Activity.RESULT_OK || resultData == null) {
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        try {
            startCaptureForeground();
            beginProjection(resultCode, resultData);
            worker.postDelayed(() -> {
                if (!captureComplete) failCapture("capture timeout");
            }, CAPTURE_TIMEOUT_MS);
        } catch (Exception e) {
            failCapture(e.getClass().getSimpleName());
        }
        return START_NOT_STICKY;
    }

    private void startCaptureForeground() {
        Notification notification = buildNotification("Capturing one approved screen frame");
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private void beginProjection(int resultCode, Intent resultData) throws Exception {
        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        if (manager == null) throw new IllegalStateException("MediaProjection manager unavailable");
        projection = manager.getMediaProjection(resultCode, resultData);
        if (projection == null) throw new SecurityException("MediaProjection consent token rejected");

        WindowManager windowManager = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        if (windowManager == null) throw new IllegalStateException("window manager unavailable");
        int densityDpi = Math.max(1, getResources().getConfiguration().densityDpi);
        if (Build.VERSION.SDK_INT >= 30) {
            WindowMetrics metrics = windowManager.getMaximumWindowMetrics();
            Rect bounds = metrics.getBounds();
            sourceWidth = Math.max(1, bounds.width());
            sourceHeight = Math.max(1, bounds.height());
        } else {
            DisplayMetrics metrics = new DisplayMetrics();
            Display display = windowManager.getDefaultDisplay();
            if (display == null) throw new IllegalStateException("default display unavailable");
            display.getRealMetrics(metrics);
            sourceWidth = Math.max(1, metrics.widthPixels);
            sourceHeight = Math.max(1, metrics.heightPixels);
        }
        double scale = Math.min(1.0,
                Math.sqrt((double) MAX_PIXELS / ((double) sourceWidth * sourceHeight)));
        captureWidth = Math.max(1, (int) Math.floor(sourceWidth * scale));
        captureHeight = Math.max(1, (int) Math.floor(sourceHeight * scale));
        imageReader = ImageReader.newInstance(captureWidth, captureHeight, PixelFormat.RGBA_8888, 2);
        imageReader.setOnImageAvailableListener(this::onImageAvailable, worker);
        projectionCallback = new MediaProjection.Callback() {
            @Override public void onStop() {
                if (!captureComplete) failCapture("OS projection revoked");
            }

            @Override public void onCapturedContentResize(int width, int height) {
                // This is a one-frame snapshot. Abort on rotation/resize instead of
                // reusing a stale surface or creating a second virtual display.
                if (!captureComplete && (width != sourceWidth || height != sourceHeight)) {
                    failCapture("display resized during one-shot capture");
                }
            }
        };
        projection.registerCallback(projectionCallback, worker);
        virtualDisplay = projection.createVirtualDisplay(
                "V14-OneShot-Screen-Frame",
                captureWidth,
                captureHeight,
                densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(),
                null,
                worker);
        if (virtualDisplay == null) throw new IllegalStateException("virtual display unavailable");
        captureStartElapsed = SystemClock.elapsedRealtime();
    }

    private void onImageAvailable(ImageReader reader) {
        if (captureComplete || !frameClaimed.compareAndSet(false, true)) return;
        Image image = null;
        Bitmap padded = null;
        Bitmap cropped = null;
        Bitmap scaled = null;
        byte[] bytes = null;
        try {
            image = reader.acquireLatestImage();
            if (image == null) {
                frameClaimed.set(false);
                return;
            }
            long frameEndElapsed = SystemClock.elapsedRealtime();
            int width = image.getWidth();
            int height = image.getHeight();
            if (width != captureWidth || height != captureHeight
                    || (long) width * height > MAX_PIXELS) {
                throw new IllegalStateException("captured frame geometry changed");
            }
            Image.Plane[] planes = image.getPlanes();
            if (planes == null || planes.length != 1) {
                throw new IllegalStateException("unexpected RGBA plane count");
            }
            Image.Plane plane = planes[0];
            ByteBuffer buffer = plane.getBuffer().duplicate();
            int pixelStride = plane.getPixelStride();
            int rowStride = plane.getRowStride();
            if (pixelStride != 4 || rowStride < width * pixelStride
                    || rowStride % pixelStride != 0) {
                throw new IllegalStateException("unsupported RGBA row geometry");
            }
            int paddedWidth = rowStride / pixelStride;
            padded = Bitmap.createBitmap(paddedWidth, height, Bitmap.Config.ARGB_8888);
            padded.copyPixelsFromBuffer(buffer);
            cropped = Bitmap.createBitmap(padded, 0, 0, width, height);
            Bitmap source = cropped;
            int quality = 82;
            for (int attempt = 0; attempt < 3; attempt++) {
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                if (!source.compress(Bitmap.CompressFormat.JPEG, quality, output)) {
                    throw new IllegalStateException("JPEG compression failed");
                }
                bytes = output.toByteArray();
                if (bytes.length <= ProjectionFrameStore.MAX_FRAME_BYTES) break;
                Arrays.fill(bytes, (byte) 0);
                bytes = null;
                if (attempt == 0) {
                    quality = 65;
                } else {
                    scaled = Bitmap.createScaledBitmap(source,
                            Math.max(1, source.getWidth() * 3 / 4),
                            Math.max(1, source.getHeight() * 3 / 4), true);
                    source = scaled;
                    quality = 55;
                }
            }
            if (bytes == null || bytes.length < 1
                    || bytes.length > ProjectionFrameStore.MAX_FRAME_BYTES) {
                throw new IllegalStateException("compressed frame exceeds byte limit");
            }
            org.json.JSONObject receipt = UIFrameReceiptFactory.create(
                    bytes, source.getWidth(), source.getHeight(),
                    captureStartElapsed, frameEndElapsed, new ReceiptSigner());
            ProjectionFrameStore.publish(bytes, receipt, frameEndElapsed);
            bytes = null; // ownership transferred to the one-shot in-memory store
            captureComplete = true;
            releaseProjection();
            updateNotification("One frame ready for paired Termux; expires in 20 seconds");
            worker.postDelayed(() -> {
                CompanionProvider.clearScreenFrame();
                stopForeground(true);
                stopSelf();
            }, ProjectionFrameStore.TTL_MS);
        } catch (Exception e) {
            failCapture(e.getClass().getSimpleName());
        } finally {
            if (image != null) image.close();
            if (bytes != null) Arrays.fill(bytes, (byte) 0);
            if (scaled != null && !scaled.isRecycled()) scaled.recycle();
            if (cropped != null && !cropped.isRecycled()) cropped.recycle();
            if (padded != null && !padded.isRecycled()) padded.recycle();
        }
    }

    private void failCapture(String reason) {
        if (captureComplete) return;
        captureComplete = true;
        CompanionProvider.clearScreenFrame();
        updateNotification("Screen frame not available: " + reason);
        releaseProjection();
        stopForeground(true);
        stopSelf();
    }

    private void releaseProjection() {
        if (virtualDisplay != null) {
            virtualDisplay.release();
            virtualDisplay = null;
        }
        if (imageReader != null) {
            imageReader.setOnImageAvailableListener(null, null);
            imageReader.close();
            imageReader = null;
        }
        if (projection != null) {
            if (projectionCallback != null) projection.unregisterCallback(projectionCallback);
            projectionCallback = null;
            projection.stop();
            projection = null;
        }
    }

    private void stopCapture(boolean clearFrame) {
        if (clearFrame) CompanionProvider.clearScreenFrame();
        captureComplete = true;
        releaseProjection();
        stopForeground(true);
    }

    static void discard(Context context) {
        CompanionProvider.clearScreenFrame();
        Intent intent = new Intent(context, MediaProjectionCaptureService.class);
        intent.setAction(ACTION_DISCARD);
        try { context.startService(intent); }
        catch (RuntimeException ignored) {}
    }

    private void ensureChannel() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.createNotificationChannel(new NotificationChannel(
                CHANNEL, "V14 one-shot screen capture", NotificationManager.IMPORTANCE_LOW));
    }

    private Notification buildNotification(String text) {
        Intent discard = new Intent(this, MediaProjectionCaptureService.class);
        discard.setAction(ACTION_DISCARD);
        PendingIntent pending = PendingIntent.getService(this, 1402, discard,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentTitle("V14 one-shot screen capture")
                .setContentText(text)
                .setOngoing(true)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Discard", pending)
                .build();
    }

    private void updateNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.notify(NOTIFICATION_ID, buildNotification(text));
    }

    @Override public void onDestroy() {
        CompanionProvider.clearScreenFrame();
        stopCapture(true);
        if (workerThread != null) {
            workerThread.quitSafely();
            workerThread = null;
        }
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
