pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        // ⚠️ IPOTESI: il Meta Wearables Device Access Toolkit (DAT) per Android
        // non è su Maven Central/jcenter pubblico al momento della scrittura.
        // Va aggiunto il repository Maven indicato nella Developer Preview una
        // volta ottenuto l'accesso su wearables.developer.meta.com. Esempio
        // placeholder, DA VERIFICARE con la doc ufficiale:
        // maven { url = uri("https://artifactory.meta.com/wearables-dat") }
    }
}

rootProject.name = "rayban-display-agent"
include(":app")
