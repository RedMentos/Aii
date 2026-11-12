package v13.companion

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager

/**
 * Android-only implementation of LaunchPlatform. This file must be compiled in an Android
 * application module, not in the host-JVM policy test. No arbitrary intent extras or URIs.
 *
 * Caller must be the isolated companion app with a trusted local consent surface.
 * Android package visibility rules apply; a missing launch intent is a denial.
 */
class AndroidPackageLauncher(private val context: Context) : LaunchPlatform {
    override fun isLaunchable(packageName: String): Boolean =
        launchIntent(packageName) != null

    override fun launchPackage(packageName: String): Boolean {
        val intent = launchIntent(packageName) ?: return false
        return try {
            context.startActivity(intent)
            // Android accepted the launch request; app foreground state is NOT verified.
            true
        } catch (_: RuntimeException) {
            false
        }
    }

    private fun launchIntent(packageName: String): Intent? {
        if (!AppLaunchCapability.validPackage(packageName)) return null
        val candidate = context.packageManager.getLaunchIntentForPackage(packageName) ?: return null
        val component = candidate.component ?: return null
        if (component.packageName != packageName) return null
        return Intent(Intent.ACTION_MAIN).apply {
            setComponent(component)
            addCategory(Intent.CATEGORY_LAUNCHER)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }
}
