import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.jetbrains.kotlin.android)
}

val localProperties = Properties().apply {
    val file = rootDir.resolve("local.properties")
    if (file.exists()) {
        file.inputStream().use { load(it) }
    }
}

android {
    namespace = "com.zeus.raybandisplay"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.zeus.raybandisplay"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.2.0-skeleton"

        // Meta Wearables Device Access Toolkit — credenziali dal Wearables
        // Developer Center. In Developer Mode possono restare vuote ("0"):
        // vedi rayban_display/README.md e local.properties.example.
        manifestPlaceholders["mwdat_application_id"] =
            localProperties.getProperty("mwdat_application_id", "0")
        manifestPlaceholders["mwdat_client_token"] =
            localProperties.getProperty("mwdat_client_token", "0")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.lifecycle.runtime.ktx)

    implementation(libs.okhttp)
    implementation(libs.okhttp.logging.interceptor)
    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.moshi)
    implementation(libs.moshi.kotlin)
    implementation(libs.kotlinx.coroutines.android)

    // Meta Wearables Device Access Toolkit (verificato su Maven Central,
    // com.meta.wearable, v1.0.1 — facebook/meta-wearables-dat-android).
    implementation(libs.mwdat.core)
    implementation(libs.mwdat.display)
    implementation(libs.mwdat.speech)
    implementation(libs.mwdat.mockdevice)
}
