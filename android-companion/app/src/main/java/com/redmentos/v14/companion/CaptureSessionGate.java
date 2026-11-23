package com.redmentos.v14.companion;

/** Monotonic one-shot state for one MediaProjection service instance. */
final class CaptureSessionGate {
    private enum State { NEW, STARTING, ACTIVE, FRAME_CLAIMED, COMPLETE }
    private State state = State.NEW;

    synchronized boolean begin() {
        if (state != State.NEW) return false;
        state = State.STARTING;
        return true;
    }

    synchronized boolean activate() {
        if (state != State.STARTING) return false;
        state = State.ACTIVE;
        return true;
    }

    synchronized boolean claimFrame() {
        if (state != State.ACTIVE) return false;
        state = State.FRAME_CLAIMED;
        return true;
    }

    synchronized boolean releaseFrameClaim() {
        if (state != State.FRAME_CLAIMED) return false;
        state = State.ACTIVE;
        return true;
    }

    synchronized boolean canPublish() {
        return state == State.FRAME_CLAIMED;
    }

    synchronized boolean completeFrame() {
        if (state != State.FRAME_CLAIMED) return false;
        state = State.COMPLETE;
        return true;
    }

    synchronized boolean complete() {
        if (state == State.COMPLETE) return false;
        state = State.COMPLETE;
        return true;
    }

    synchronized boolean isComplete() {
        return state == State.COMPLETE;
    }
}
