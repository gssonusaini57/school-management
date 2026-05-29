# Keep DTOs used by Gson via reflection (field names MUST survive R8 — Gson maps
# JSON keys to field names). NOTE: this package must match the app package; if the
# package is ever renamed, update this line too, or release-build (de)serialization
# silently breaks (login → HTTP 422).
-keep class in.kisschool.data.api.dto.** { *; }
-keepattributes Signature
-keepattributes *Annotation*

# Belt-and-suspenders: keep any @SerializedName field by its JSON name even if its
# class is obfuscated, in any package.
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Retrofit
-dontwarn retrofit2.**
-keepattributes Exceptions

# OkHttp / Okio
-dontwarn okhttp3.**
-dontwarn okio.**

# Kotlin metadata
-keep class kotlin.Metadata { *; }
