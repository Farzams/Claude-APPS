pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "LinuxPad"
include(":app")
// Termux:X11's X server and renderer (GPL-3.0), fetched by tools/fetch-termux-x11.sh
include(":x11-lorie")
include(":shell-loader:stub")
project(":x11-lorie").projectDir = file("third_party/termux-x11/lorie")
project(":shell-loader:stub").projectDir = file("third_party/termux-x11/shell-loader/stub")
