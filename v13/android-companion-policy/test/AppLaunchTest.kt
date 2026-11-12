package v13.companion

fun main() {
    var launches = 0
    var resolvable = true
    val platform = object : LaunchPlatform {
        override fun isLaunchable(packageName: String) = resolvable
        override fun launchPackage(packageName: String): Boolean { launches++; return true }
    }
    val cap = AppLaunchCapability(setOf("org.example.app"), platform)
    check(!cap.execute("org.example.other"))
    check(!cap.execute("org.example.app;rm -rf /"))
    check(!cap.execute("https://example.org"))
    check(!cap.execute("org.example.app\n"))
    check(!cap.execute("org.example.app/.Activity"))
    check(!cap.execute("org.exämple.app"))
    check(launches == 0)
    resolvable = false
    check(!cap.execute("org.example.app"))
    check(launches == 0)
    resolvable = true
    check(cap.execute("org.example.app"))
    check(launches == 1)
    for (bad in listOf("com", "1com.app", "com..app", "com.-app", "com.app ", "com.app/other")) {
        check(!AppLaunchCapability.validPackage(bad))
    }
    println("PASS app launch contract: allowlist, parser, resolver, dispatch")
}
