pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        // Il Meta Wearables Device Access Toolkit (gruppo com.meta.wearable) è
        // pubblicato su Maven Central: nessun repository extra o token richiesto.
        // Verificato in facebook/meta-wearables-dat-android (AGENTS.md, 2026-10-22).
        mavenCentral()
    }
}

rootProject.name = "rayban-display-agent"
include(":app")
