package com.redmentos.v14.companion;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.app.Activity;
import android.content.Context;
import android.graphics.Point;
import android.graphics.Rect;
import android.os.Process;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.widget.Button;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Exercises the actual MainActivity view tree and click listeners around an
 * externally controlled process-death boundary.
 *
 * GitHub's TCG-backed headless emulator can resume the Activity without
 * granting WindowManager input focus. We therefore do not pretend that a
 * programmatic click is a physical touch: the test requires the real target
 * Button and status TextView to be attached, shown and intersecting the
 * display, then invokes that Button's actual OnClickListener with
 * View.performClick(). Physical touch injection remains a separate gate.
 */
@RunWith(AndroidJUnit4.class)
public final class CompanionLifecycleInstrumentedTest {
    private static final String STOPPED =
            "STOPPED (restart requires explicit re-enable)";
    private static final String ENABLED = "ENABLED FOR THIS PROCESS";
    private static final String TOGGLE = "Enable / Stop companion";

    private Context targetContext() {
        return InstrumentationRegistry.getInstrumentation().getTargetContext();
    }

    private static void recordTargetProcess(Activity activity, String marker) {
        if (!"qa-process-first.pid".equals(marker)
                && !"qa-process-restart.pid".equals(marker)) {
            throw new AssertionError("target process marker is not allowlisted");
        }
        File file = new File(activity.getFilesDir(), marker);
        try (FileOutputStream stream = new FileOutputStream(file, false)) {
            String identity = Process.myPid() + "|" + Process.getStartElapsedRealtime();
            stream.write(identity.getBytes(StandardCharsets.US_ASCII));
            stream.getFD().sync();
        } catch (IOException error) {
            throw new AssertionError("failed to persist target process identity", error);
        }
    }

    /**
     * getGlobalVisibleRect() returns root-view coordinates. Its Point offset
     * is the target view origin in that same coordinate space; do not compare
     * it with getLocationOnScreen(), which uses the physical-screen origin.
     */
    private static boolean centerWithinVisibleRootRect(
            Rect visible, Point viewOriginInRoot, int width, int height) {
        if (visible == null || viewOriginInRoot == null || width <= 0 || height <= 0) {
            return false;
        }
        int centerX = viewOriginInRoot.x + width / 2;
        int centerY = viewOriginInRoot.y + height / 2;
        return visible.contains(centerX, centerY);
    }

    private static boolean centerIsVisible(
            View view, Rect visible, Point viewOriginInRoot) {
        return centerWithinVisibleRootRect(
                visible, viewOriginInRoot, view.getWidth(), view.getHeight());
    }

    private static void assertOnDisplay(View view, String description) {
        assertNotNull(description + " is missing from MainActivity", view);
        assertTrue(description + " is not attached to the window", view.isAttachedToWindow());
        assertTrue(description + " is not shown", view.isShown());
        Rect visible = new Rect();
        Point viewOriginInRoot = new Point();
        assertTrue(description + " has no visible display rectangle",
                view.getGlobalVisibleRect(visible, viewOriginInRoot));
        assertTrue(description + " is fully clipped", visible.width() > 0 && visible.height() > 0);
        assertTrue(description + " center is outside the visible display rectangle",
                centerIsVisible(view, visible, viewOriginInRoot));
    }

    private static void scrollIntoDisplayIfNeeded(View view, String description) {
        Rect visible = new Rect();
        Point viewOriginInRoot = new Point();
        if (view.getGlobalVisibleRect(visible, viewOriginInRoot)
                && visible.width() > 0 && visible.height() > 0
                && centerIsVisible(view, visible, viewOriginInRoot)) {
            return;
        }

        ScrollView scroll = null;
        ViewParent parent = view.getParent();
        while (parent instanceof View) {
            if (parent instanceof ScrollView) {
                scroll = (ScrollView) parent;
                break;
            }
            parent = ((View) parent).getParent();
        }
        assertNotNull(description + " is outside the viewport and has no ScrollView ancestor", scroll);
        assertTrue(description + " has not been laid out", view.isLaidOut());
        assertTrue("ScrollView has not been laid out", scroll.isLaidOut());
        Rect descendant = new Rect(0, 0, view.getWidth(), view.getHeight());
        scroll.offsetDescendantRectToMyCoords(view, descendant);
        // Center the target rather than aligning only its bottom. This also
        // handles a partially visible TextView whose center is still clipped.
        int targetY = Math.max(0, descendant.centerY() - scroll.getHeight() / 2);
        scroll.scrollTo(scroll.getScrollX(), targetY);
        assertTrue(description + " remained outside the viewport after scrolling",
                view.getGlobalVisibleRect(visible, viewOriginInRoot));
        assertTrue(description + " is still fully clipped after scrolling",
                visible.width() > 0 && visible.height() > 0);
        assertTrue(description + " center remained outside the visible display rectangle",
                centerIsVisible(view, visible, viewOriginInRoot));
    }

    private static TextView findText(View view, String expected) {
        if (view instanceof TextView) {
            CharSequence value = ((TextView) view).getText();
            if (value != null && value.toString().contains(expected)) {
                return (TextView) view;
            }
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                TextView found = findText(group.getChildAt(i), expected);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static Button findButton(View view, String label) {
        if (view instanceof Button
                && label.contentEquals(((Button) view).getText())) {
            return (Button) view;
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                Button found = findButton(group.getChildAt(i), label);
                if (found != null) return found;
            }
        }
        return null;
    }

    private void assertVisibleState(ActivityScenario<MainActivity> scenario, String expected) {
        scenario.onActivity(activity -> {
            assertFalse("MainActivity unexpectedly finished", activity.isFinishing());
            TextView status = findText(
                    activity.getWindow().getDecorView(), expected);
            scrollIntoDisplayIfNeeded(status, "status text " + expected);
            assertOnDisplay(status, "status text " + expected);
        });
    }

    private void clickVisibleToggle(ActivityScenario<MainActivity> scenario) {
        scenario.onActivity(activity -> {
            Button toggle = findButton(
                    activity.getWindow().getDecorView(), TOGGLE);
            assertNotNull("Enable / Stop companion button is missing", toggle);
            scrollIntoDisplayIfNeeded(toggle, "Enable / Stop companion button");
            assertOnDisplay(toggle, "Enable / Stop companion button");
            assertTrue("Enable / Stop companion button is disabled", toggle.isEnabled());
            assertTrue("actual companion toggle listener did not run", toggle.performClick());
        });
    }

    private boolean persistedEnabled() {
        return targetContext()
                .getSharedPreferences("v14-companion", Context.MODE_PRIVATE)
                .getBoolean("enabled", true);
    }

    private static void assertRootCoordinateVisibilityPredicate() {
        Rect visibleRoot = new Rect(0, 0, 320, 480);
        Point viewOriginInRoot = new Point(20, 40);
        assertTrue(centerWithinVisibleRootRect(
                visibleRoot, viewOriginInRoot, 80, 40));

        Rect clippedBeforeCenter = new Rect(0, 0, 320, 50);
        assertFalse(centerWithinVisibleRootRect(
                clippedBeforeCenter, viewOriginInRoot, 80, 40));
    }

    @Test
    public void testVisibleStopButtonPersistsOff() {
        // The host driver invokes this exact method by name; keep the
        // coordinate-space positive/negative assertions on the executed path.
        assertRootCoordinateVisibilityPredicate();
        try (ActivityScenario<MainActivity> scenario =
                     ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(activity ->
                    recordTargetProcess(activity, "qa-process-first.pid"));
            assertVisibleState(scenario, STOPPED);
            assertFalse("a fresh process must start stopped", persistedEnabled());

            clickVisibleToggle(scenario);
            assertVisibleState(scenario, ENABLED);
            assertTrue("the explicit Enable click must persist enabled=true",
                    persistedEnabled());

            clickVisibleToggle(scenario);
            assertVisibleState(scenario, STOPPED);
            assertFalse("the explicit Stop click must persist enabled=false",
                    persistedEnabled());
        }
    }

    @Test
    public void testProviderStartupAfterProcessDeathRemainsStopped() {
        try (ActivityScenario<MainActivity> scenario =
                     ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(activity ->
                    recordTargetProcess(activity, "qa-process-restart.pid"));
            assertVisibleState(scenario, STOPPED);
            assertFalse("provider startup after process death must revoke the grant",
                    persistedEnabled());
        }
    }
}
