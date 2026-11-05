plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }

android {
    namespace = "app.linuxpad"
    compileSdk = 36
    ndkVersion = "28.2.13676358"

    defaultConfig {
        applicationId = "app.linuxpad"
        minSdk = 30            // Android 11+; the target tablet runs Android 14
        targetSdk = 34
        versionCode = (System.getenv("APP_VERSION_CODE") ?: "1").toInt()
        versionName = "0.1.${System.getenv("APP_VERSION_CODE") ?: "0"}"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")   // sideloaded builds: the debug key is fine
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures { compose = true }
    packaging { jniLibs { useLegacyPackaging = true } }   // PRoot must be extracted to disk to be executable
}

dependencies {
    implementation(project(":x11-lorie"))
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.apache.commons:commons-compress:1.26.2")   // tar reader (pure Java)
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")                      // android.jar only has stubs in unit tests
}
