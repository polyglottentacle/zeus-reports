plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.zeus.raybandisplay"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.zeus.raybandisplay"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0-skeleton"
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
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // ⚠️ IPOTESI — non verificato: coordinate Maven reali del Meta Wearables
    // Device Access Toolkit (DAT) non confermate in questo ambiente (richiede
    // accesso alla Developer Preview su wearables.developer.meta.com).
    // Sostituire con la dipendenza ufficiale, es.:
    // implementation("com.meta.wearables:dat-sdk:<versione>")
}
