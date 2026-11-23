package com.redmentos.v14.companion;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.graphics.Rect;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;

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

    private static void assertOnDisplay(View view, String description) {
        assertNotNull(description + " is missing from MainActivity", view);
        assertTrue(description + " is not attached to the window", view.isAttachedToWindow());
        assertTrue(description + " is not shown", view.isShown());
        Rect visible = new Rect();
        assertTrue(description + " has no visible display rectangle",
                view.getGlobalVisibleRect(visible));
        assertTrue(description + " is fully clipped", visible.width() > 0 && visible.height() > 0);
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
            assertOnDisplay(status, "status text " + expected);
        });
    }

    private void clickVisibleToggle(ActivityScenario<MainActivity> scenario) {
        scenario.onActivity(activity -> {
            Button toggle = findButton(
                    activity.getWindow().getDecorView(), TOGGLE);
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

    @Test
    public void testVisibleStopButtonPersistsOff() {
        try (ActivityScenario<MainActivity> scenario =
                     ActivityScenario.launch(MainActivity.class)) {
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
            assertVisibleState(scenario, STOPPED);
            assertFalse("provider startup after process death must revoke the grant",
                    persistedEnabled());
        }
    }
}
