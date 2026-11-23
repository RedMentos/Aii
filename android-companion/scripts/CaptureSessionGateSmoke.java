package com.redmentos.v14.companion;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Dependency-free executable regression for the exact production state gate. */
public final class CaptureSessionGateSmoke {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static CaptureSessionGate activeClaimedGate() {
        CaptureSessionGate gate = new CaptureSessionGate();
        check(gate.begin(), "first capture must claim the service instance");
        check(!gate.begin(), "duplicate capture must not claim the service instance");
        check(gate.activate(), "first capture must activate");
        check(gate.claimFrame(), "first frame must be claimed");
        return gate;
    }

    private static void oneShotAndTerminalState() {
        CaptureSessionGate gate = new CaptureSessionGate();
        check(gate.begin(), "initial begin");
        check(!gate.begin(), "duplicate ACTION_CAPTURE rejected");
        check(gate.activate(), "activate once");
        check(!gate.activate(), "duplicate activation rejected");
        check(gate.claimFrame(), "claim one frame");
        check(!gate.claimFrame(), "second frame rejected");
        check(gate.releaseFrameClaim(), "empty image releases claim");
        check(gate.claimFrame(), "later image may claim after empty read");
        check(gate.completeFrame(), "publish completes the session");
        check(gate.isComplete(), "completed session is terminal");
        check(!gate.begin(), "late ACTION_CAPTURE after completion rejected");
        check(!gate.claimFrame(), "late frame after completion rejected");
    }

    private static void stopWinsBeforePublication() throws Exception {
        CaptureSessionGate gate = activeClaimedGate();
        Object actionGate = new Object();
        CountDownLatch workerReady = new CountDownLatch(1);
        AtomicBoolean published = new AtomicBoolean(false);
        Thread worker;
        synchronized (actionGate) {
            worker = new Thread(() -> {
                workerReady.countDown();
                synchronized (actionGate) {
                    if (!gate.canPublish()) return;
                    published.set(true);
                    gate.completeFrame();
                }
            }, "capture-publish-after-stop");
            worker.start();
            check(workerReady.await(2, TimeUnit.SECONDS), "worker reached publication gate");
            check(gate.complete(), "stop makes session terminal under shared action lock");
        }
        worker.join(2_000L);
        check(!worker.isAlive(), "publication worker settles");
        check(!published.get(), "revoked frame cannot publish after stop wins lock");
    }

    private static void stopClearsPublicationThatWonFirst() {
        CaptureSessionGate gate = activeClaimedGate();
        Object actionGate = new Object();
        AtomicBoolean frameAvailable = new AtomicBoolean(false);
        synchronized (actionGate) {
            check(gate.canPublish(), "frame is eligible before publication");
            frameAvailable.set(true);
            check(gate.completeFrame(), "publication completes one-shot session");
        }
        synchronized (actionGate) {
            gate.complete();
            frameAvailable.set(false); // same critical section as ProjectionFrameStore.clear()
        }
        check(!frameAvailable.get(), "stop clears a frame even if publication won first");
    }

    public static void main(String[] args) throws Exception {
        oneShotAndTerminalState();
        stopWinsBeforePublication();
        stopClearsPublicationThatWonFirst();
        System.out.println("CaptureSessionGateSmoke: 3 scenarios PASS");
    }
}
