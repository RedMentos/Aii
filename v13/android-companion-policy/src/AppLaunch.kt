package v13.companion

/** Android adapter must resolve the package via PackageManager and launch an explicit, exported launch intent. */
interface LaunchPlatform {
    fun isLaunchable(packageName: String): Boolean
    fun launchPackage(packageName: String): Boolean
}

/** Deliberately does not accept URLs, components, shell commands or arbitrary Intent strings. */
class AppLaunchCapability(
    allowedPackages: Set<String>,
    private val platform: LaunchPlatform
) : NativeCapability {
    private val allowlist = allowedPackages.toSet()
    init { require(allowlist.all(::validPackage)) }

    override fun execute(target: String): Boolean {
        if (!validPackage(target) || target !in allowlist) return false
        if (!platform.isLaunchable(target)) return false
        return platform.launchPackage(target)
    }

    companion object {
        fun validPackage(value: String): Boolean {
            if (value.length !in 3..200 || value.any { it.code > 127 }) return false
            val parts = value.split('.')
            if (parts.size < 2) return false
            return parts.all { part ->
                part.isNotEmpty() && part.length <= 63 &&
                    (part[0] in 'a'..'z' || part[0] in 'A'..'Z') &&
                    part.all { it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' || it == '_' }
            }
        }
    }
}
