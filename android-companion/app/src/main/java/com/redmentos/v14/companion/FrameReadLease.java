package com.redmentos.v14.companion;

import java.io.Closeable;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Revocable owner of one consumed frame and its one-shot pipe.
 *
 * Binder may duplicate the read descriptor for the paired Termux process. Closing
 * this process's descriptor cannot recall bytes already delivered or buffered for
 * that remote descriptor. Revocation therefore guarantees no further writes,
 * zeroizes the in-process source array, closes the provider's descriptor and
 * requires the downstream UIObservationLease to remain active through C3 use.
 */
final class FrameReadLease {
    private final byte[] frame;
    private final AtomicBoolean cancelled = new AtomicBoolean(false);
    private final AtomicBoolean started = new AtomicBoolean(false);
    private final CountDownLatch writerExited = new CountDownLatch(1);
    private volatile Closeable reader;
    private volatile OutputStream writer;
    private volatile Thread worker;

    FrameReadLease(byte[] frame) {
        if (frame == null || frame.length == 0) {
            throw new IllegalArgumentException("frame read lease requires nonempty bytes");
        }
        this.frame = frame;
    }

    void start(Closeable readerEnd, OutputStream writerEnd) {
        if (readerEnd == null || writerEnd == null) {
            throw new IllegalArgumentException("frame pipe ends are required");
        }
        if (!started.compareAndSet(false, true)) {
            throw new IllegalStateException("frame pipe writer is one-shot");
        }
        synchronized (this) {
            if (cancelled.get()) {
                closeQuietly(writerEnd);
                closeQuietly(readerEnd);
                writerExited.countDown();
                throw new IllegalStateException("frame pipe was revoked before start");
            }
            reader = readerEnd;
            writer = writerEnd;
        }
        Thread thread = new Thread(() -> {
            OutputStream output = writer;
            try {
                if (!cancelled.get()) {
                    output.write(frame);
                    output.flush();
                }
            } catch (IOException ignored) {
                // Reader disconnect, pipe close or revocation is terminal; never retry a frame.
            } finally {
                closeQuietly(output);
                Arrays.fill(frame, (byte) 0);
                writerExited.countDown();
            }
        }, "v14-one-shot-frame-pipe");
        thread.setDaemon(true);
        worker = thread;
        if (cancelled.get()) {
            writerExited.countDown();
            throw new IllegalStateException("frame pipe was revoked before writer start");
        }
        try {
            thread.start();
        } catch (RuntimeException failure) {
            writerExited.countDown();
            cancel();
            throw failure;
        }
        if (cancelled.get()) {
            throw new IllegalStateException("frame pipe was revoked during writer start");
        }
    }

    void cancel() {
        if (!cancelled.compareAndSet(false, true)) return;
        // Erase the in-process screenshot bytes before descriptor close can block.
        // A concurrent writer may emit a partial/zeroed stream; the signed hash rejects it.
        Arrays.fill(frame, (byte) 0);
        closeQuietly(writer);
        closeQuietly(reader);
        Thread thread = worker;
        if (thread != null && thread != Thread.currentThread()) thread.interrupt();
        if (!started.get()) writerExited.countDown();
        ProjectionFrameStore.release(this);
    }

    private static void closeQuietly(Closeable value) {
        if (value == null) return;
        try {
            value.close();
        } catch (IOException ignored) {
            // Revocation is best-effort at the descriptor boundary; bytes are still zeroized.
        }
    }

    int frameLengthForTest() {
        return frame.length;
    }

    boolean isCancelledForTest() {
        return cancelled.get();
    }

    boolean isZeroizedForTest() {
        for (byte value : frame) {
            if (value != 0) return false;
        }
        return true;
    }

    boolean isWriterAliveForTest() {
        Thread thread = worker;
        return thread != null && thread.isAlive();
    }

    boolean awaitWriterExitForTest(long timeoutMillis) throws InterruptedException {
        return writerExited.await(timeoutMillis, TimeUnit.MILLISECONDS);
    }
}
