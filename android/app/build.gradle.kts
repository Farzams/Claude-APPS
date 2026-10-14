plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "app.pdftoolkit.mobile"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
        targetSdk = 34
        versionCode = (System.getenv("APP_VERSION_CODE") ?: "1").toInt()
        versionName = "0.1.${System.getenv("APP_VERSION_CODE") ?: "0"}"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Two apps from one project: the LaTeX editor with the offline TeX engine (large) and the PDF tools (small)
    flavorDimensions += "product"
    productFlavors {
        create("latex") { dimension = "product"; applicationId = "app.pdftoolkit.latex" }
        create("pdf") { dimension = "product"; applicationId = "app.pdftoolkit.pdf" }
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
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    androidResources { noCompress += listOf("data", "wasm", "ttf") }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    val bom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(bom)
    androidTestImplementation(bom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.uiautomator:uiautomator:2.3.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    // PDF tools app: page editing, merging, encryption (PdfBox) and picking a folder (DocumentFile)
    "pdfImplementation"("com.tom-roush:pdfbox-android:2.0.27.0")
    "pdfImplementation"("androidx.documentfile:documentfile:1.0.1")
}
