# Keep DTOs used by Gson via reflection
-keep class com.expressonly.kisattendance.data.api.dto.** { *; }
-keepattributes Signature
-keepattributes *Annotation*

# Retrofit
-dontwarn retrofit2.**
-keepattributes Exceptions

# OkHttp / Okio
-dontwarn okhttp3.**
-dontwarn okio.**

# Kotlin metadata
-keep class kotlin.Metadata { *; }
