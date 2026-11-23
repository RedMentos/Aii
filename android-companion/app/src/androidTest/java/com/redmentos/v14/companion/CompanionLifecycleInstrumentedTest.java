package com.redmentos.v14.companion;

import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.assertion.ViewAssertions.matches;
import static androidx.test.espresso.matcher.ViewMatchers.isDisplayed;
import static androidx.test.espresso.matcher.ViewMatchers.withText;
import static org.hamcrest.Matchers.containsString;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;

import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Exercises the actual MainActivity controls without depending on Android
 * System-UI accessibility dumps. The host process separately kills the app
 * between these two test methods and starts the instrumentation again.
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

    private void assertVisibleState(String expected) {
        onView(withText(containsString(expected))).check(matches(isDisplayed()));
    }

    private boolean persistedEnabled() {
        return targetContext()
                .getSharedPreferences("v14-companion", Context.MODE_PRIVATE)
                .getBoolean("enabled", true);
    }

    @Test
    public void testVisibleStopButtonPersistsOff() {
        try (ActivityScenario<MainActivity> ignored =
                     ActivityScenario.launch(MainActivity.class)) {
            assertVisibleState(STOPPED);
            assertFalse("a fresh process must start stopped", persistedEnabled());

            onView(withText(TOGGLE)).check(matches(isDisplayed())).perform(
                    androidx.test.espresso.action.ViewActions.click());
            assertVisibleState(ENABLED);
            assertTrue("the explicit Enable tap must persist enabled=true",
                    persistedEnabled());

            onView(withText(TOGGLE)).check(matches(isDisplayed())).perform(
                    androidx.test.espresso.action.ViewActions.click());
            assertVisibleState(STOPPED);
            assertFalse("the explicit Stop tap must persist enabled=false",
                    persistedEnabled());
        }
    }

    @Test
    public void testProviderStartupAfterProcessDeathRemainsStopped() {
        try (ActivityScenario<MainActivity> ignored =
                     ActivityScenario.launch(MainActivity.class)) {
            assertVisibleState(STOPPED);
            assertFalse("provider startup after process death must revoke the grant",
                    persistedEnabled());
        }
    }
}
